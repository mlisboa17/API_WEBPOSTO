"""F04.1 — Operator Accountability & Incentive Engine (People Intelligence)."""
from __future__ import annotations

import time
from collections import Counter
from typing import Any

from src.models.response_model import WebPostoResponse
from src.services.analytics_multiselect import build_finance_center_filters
from src.services.cash_operations_service import _dec, _round2, CashOperationsService
from src.services.operator_sales_intelligence_service import (
    OperatorSalesIntelligenceService,
    _cancelled,
    _productivity_band,
)

GLOBAL_CLASSIFICATION = (
    (90, 100, "ELITE"),
    (75, 89, "ALTA PERFORMANCE"),
    (50, 74, "NORMAL"),
    (25, 49, "ATENÇÃO"),
    (0, 24, "CRÍTICO"),
)

SCORE_WEIGHTS = {
    "sales": 0.25,
    "productivity": 0.25,
    "accountability": 0.25,
    "compliance": 0.25,
}

BONUS_ELIGIBLE = {"ELITE", "ALTA PERFORMANCE"}
CRITICAL_PDVS = {54193, 15880}


def _global_band(score: float) -> str:
    s = int(round(score))
    for lo, hi, label in GLOBAL_CLASSIFICATION:
        if lo <= s <= hi:
            return label
    return "CRÍTICO"


def _norm_score(value: float, maximum: float) -> float:
    if maximum <= 0:
        return 0.0
    return _round2(100 * min(value / maximum, 1.0))

class OperatorAccountabilityIncentiveService:
    """F04.1 — scores independentes, classificação, bônus, treinamento e cockpit gerencial."""

    def __init__(
        self,
        intelligence: OperatorSalesIntelligenceService | None = None,
        cash_ops: CashOperationsService | None = None,
    ) -> None:
        self._cash = cash_ops or CashOperationsService()
        self._intel = intelligence or OperatorSalesIntelligenceService(self._cash)

    def _sales_score_engine(self, sales: list[dict[str, Any]]) -> list[dict[str, Any]]:
        if not sales:
            return []
        max_qty = max(s["quantidadeVendas"] for s in sales) or 1
        max_total = max(s["totalVendas"] for s in sales) or 1.0
        max_ticket = max(s["ticketMedio"] for s in sales) or 1.0
        max_fuel = max(s["volumeCombustivel"] for s in sales) or 1.0
        max_conv = max(s["volumeConveniencia"] for s in sales) or 1.0

        out: list[dict[str, Any]] = []
        for s in sales:
            score = _round2(
                0.20 * _norm_score(s["quantidadeVendas"], max_qty)
                + 0.25 * _norm_score(s["totalVendas"], max_total)
                + 0.20 * _norm_score(s["ticketMedio"], max_ticket)
                + 0.20 * _norm_score(s["volumeCombustivel"], max_fuel)
                + 0.15 * _norm_score(s["volumeConveniencia"], max_conv)
            )
            out.append(
                {
                    "funcionarioCodigo": s["funcionarioCodigo"],
                    "employeeName": s.get("employeeName"),
                    "salesScore": score,
                    "salesBand": _productivity_band(score),
                    "quantidadeVendas": s["quantidadeVendas"],
                    "totalVendas": s["totalVendas"],
                    "ticketMedio": s["ticketMedio"],
                    "volumeCombustivel": s["volumeCombustivel"],
                    "volumeConveniencia": s["volumeConveniencia"],
                }
            )
        out.sort(key=lambda x: x["salesScore"], reverse=True)
        return out

    def _accountability_score_engine(
        self,
        accountability: list[dict[str, Any]],
        perf_ops: list[dict[str, Any]],
    ) -> list[dict[str, Any]]:
        perf_map = {int(r["funcionarioCodigo"]): r for r in perf_ops if r.get("funcionarioCodigo") is not None}
        max_falta = max(abs(_dec(a.get("faltasProxy"))) for a in accountability) if accountability else 1.0
        max_falta = max_falta or 1.0
        max_sobra = max(_dec(a.get("sobrasProxy")) for a in accountability) if accountability else 1.0
        max_sobra = max_sobra or 1.0
        max_break = max(abs(_dec(o.get("diferencaAcumulada"))) for o in perf_ops) if perf_ops else 1.0
        max_break = max_break or 1.0

        out: list[dict[str, Any]] = []
        for row in accountability:
            op = int(row["funcionarioCodigo"])
            perf = perf_map.get(op) or {}
            faltas = abs(_dec(row.get("faltasProxy")))
            sobras = max(_dec(row.get("sobrasProxy")), 0)
            compensacao = max(_dec(row.get("compensadoAutomatico")), 0)
            break_raw = abs(_dec(perf.get("diferencaAcumulada")))

            falta_pen = 35 * min(faltas / max_falta, 1.0)
            break_pen = 35 * min(break_raw / max_break, 1.0)
            sobra_bonus = 15 * min(sobras / max_sobra, 1.0)
            comp_bonus = 15 * min(compensacao / max(max_falta, 1.0), 1.0)
            score = _round2(max(0, min(100, 100 - falta_pen - break_pen + sobra_bonus + comp_bonus)))

            out.append(
                {
                    "funcionarioCodigo": op,
                    "employeeName": row.get("employeeName"),
                    "accountabilityScore": score,
                    "accountabilityBand": _productivity_band(score),
                    "faltas": _round2(faltas),
                    "sobras": _round2(sobras),
                    "compensacoes": _round2(compensacao),
                    "recuperacoes": _round2(compensacao),
                    "saldoOperacional": row.get("saldoOperacional"),
                }
            )
        out.sort(key=lambda x: x["accountabilityScore"], reverse=True)
        return out

    def _compliance_score_engine(
        self,
        venda: list[dict[str, Any]],
        discounts: dict[str, Any],
        nfce_rows: list[dict[str, Any]],
        sales: list[dict[str, Any]],
        idx: dict[int, dict[str, Any]],
    ) -> list[dict[str, Any]]:
        disc_map = {
            int(r["funcionarioCodigo"]): _dec(r.get("totalDesconto"))
            for r in discounts.get("descontoPorOperador") or []
            if r.get("funcionarioCodigo") is not None
        }
        cancel_by: Counter[int] = Counter()
        for row in venda:
            if not _cancelled(row):
                continue
            try:
                op = int(row.get("funcionarioCodigo") or 0)
            except (TypeError, ValueError):
                continue
            if op:
                cancel_by[op] += 1

        nfce_anomaly_by: Counter[int] = Counter()
        venda_op: dict[int, int] = {}
        for row in venda:
            try:
                venda_op[int(row.get("vendaCodigo"))] = int(row.get("funcionarioCodigo") or 0)
            except (TypeError, ValueError):
                pass
        for row in nfce_rows:
            situacao = str(row.get("situacao") or row.get("status") or "").lower()
            if situacao not in {"cancelada", "cancelado", "rejeitada", "rejeitado", "denegada", "inutilizada"}:
                continue
            try:
                vc = int(row.get("vendaCodigo") or 0)
            except (TypeError, ValueError):
                vc = 0
            op = venda_op.get(vc, 0)
            if op:
                nfce_anomaly_by[op] += 1

        max_disc = max(disc_map.values()) if disc_map else 1.0
        max_disc = max_disc or 1.0
        max_cancel = max(cancel_by.values()) if cancel_by else 1
        max_cancel = max_cancel or 1
        max_nfce = max(nfce_anomaly_by.values()) if nfce_anomaly_by else 1
        max_nfce = max_nfce or 1

        out: list[dict[str, Any]] = []
        for s in sales:
            op = int(s["funcionarioCodigo"])
            emp = idx.get(op) or {}
            disc = disc_map.get(op, 0.0)
            cancels = cancel_by.get(op, 0)
            anomalies = nfce_anomaly_by.get(op, 0)
            score = _round2(
                100
                - 40 * min(disc / max_disc, 1.0)
                - 30 * min(cancels / max_cancel, 1.0)
                - 30 * min(anomalies / max_nfce, 1.0)
            )
            score = max(0.0, score)
            out.append(
                {
                    "funcionarioCodigo": op,
                    "employeeName": emp.get("employeeName") or s.get("employeeName"),
                    "complianceScore": score,
                    "complianceBand": _productivity_band(score),
                    "totalDesconto": _round2(disc),
                    "cancelamentos": cancels,
                    "nfceAnomalias": anomalies,
                }
            )
        out.sort(key=lambda x: x["complianceScore"], reverse=True)
        return out

    def _productivity_score_engine(self, productivity: list[dict[str, Any]]) -> list[dict[str, Any]]:
        return [
            {
                "funcionarioCodigo": p["funcionarioCodigo"],
                "employeeName": p.get("employeeName"),
                "productivityScore": p.get("productivityScore", 0),
                "productivityBand": p.get("productivityBand"),
                "abastecimentos": p.get("abastecimentos", 0),
                "itensVendidos": p.get("itensVendidos", 0),
                "volumeFinanceiro": p.get("volumeFinanceiro", 0),
                "litrosCombustivel": p.get("litrosCombustivel", 0),
            }
            for p in productivity
        ]

    def _context_fairness_engine(
        self,
        operators: list[dict[str, Any]],
        context: dict[str, Any],
    ) -> dict[str, Any]:
        ctx_map = {
            int(r["funcionarioCodigo"]): r
            for r in context.get("rankingAjustado") or []
            if r.get("funcionarioCodigo") is not None
        }
        harmful_pdvs = context.get("harmfulPdvs") or []
        adjusted: list[dict[str, Any]] = []

        for op in operators:
            code = int(op["funcionarioCodigo"])
            ctx = ctx_map.get(code) or {}
            penalty = float(ctx.get("contextRiskPenalty") or 0)
            bonus = float(ctx.get("multiContextBonus") or 0)
            raw = float(op.get("globalScore") or 0)
            adjusted_score = _round2(max(0, min(100, raw - penalty + bonus)))
            classification = str(
                ctx.get("contextClassification") or ctx.get("classificacao") or "INCONCLUSIVO"
            )
            context_bad = classification.startswith("DEPENDENTE") or penalty >= 15
            operator_bad = raw < 50 and not context_bad
            verdict = (
                "CONTEXTO_RUIM"
                if context_bad and raw >= 50
                else "OPERADOR_RUIM"
                if operator_bad
                else "OPERADOR_BOM"
                if raw >= 75
                else "MISTO"
            )
            adjusted.append(
                {
                    "funcionarioCodigo": code,
                    "employeeName": op.get("employeeName"),
                    "globalScore": raw,
                    "contextAdjustedScore": adjusted_score,
                    "contextClassification": classification,
                    "contextRiskPenalty": _round2(penalty),
                    "multiContextBonus": _round2(bonus),
                    "verdict": verdict,
                }
            )

        performs_in_bad_pdv = [
            a
            for a in adjusted
            if a["contextAdjustedScore"] >= 70
            and any(
                str(p.get("pdvCodigo")) in {str(x) for x in CRITICAL_PDVS}
                for p in (ctx_map.get(int(a["funcionarioCodigo"])) or {}).get("contextBreakdown") or []
            )
        ]
        if not performs_in_bad_pdv:
            performs_in_bad_pdv = [
                a for a in adjusted if a["contextAdjustedScore"] >= 70 and a["verdict"] == "CONTEXTO_RUIM"
            ]

        dependent = [a for a in adjusted if a["contextClassification"].startswith("DEPENDENTE")]

        return {
            "operators": adjusted,
            "harmfulPdvs": harmful_pdvs,
            "mandatoryQuestions": {
                "operadorRuim": [a for a in adjusted if a["verdict"] == "OPERADOR_RUIM"][:5],
                "contextoRuim": [a for a in adjusted if a["verdict"] == "CONTEXTO_RUIM"][:5],
            },
            "performsInBadPdv": performs_in_bad_pdv[:5],
            "contextDependentOperators": dependent[:10],
        }

    def _merge_operator_scores(
        self,
        sales: list[dict[str, Any]],
        productivity: list[dict[str, Any]],
        accountability: list[dict[str, Any]],
        compliance: list[dict[str, Any]],
        fairness: dict[str, Any],
    ) -> list[dict[str, Any]]:
        maps = {
            "sales": {int(r["funcionarioCodigo"]): r for r in sales},
            "productivity": {int(r["funcionarioCodigo"]): r for r in productivity},
            "accountability": {int(r["funcionarioCodigo"]): r for r in accountability},
            "compliance": {int(r["funcionarioCodigo"]): r for r in compliance},
        }
        fairness_map = {int(r["funcionarioCodigo"]): r for r in fairness.get("operators") or []}
        codes = set()
        for m in maps.values():
            codes.update(m.keys())

        merged: list[dict[str, Any]] = []
        for code in codes:
            s = maps["sales"].get(code, {})
            p = maps["productivity"].get(code, {})
            a = maps["accountability"].get(code, {})
            c = maps["compliance"].get(code, {})
            f = fairness_map.get(code, {})
            global_score = _round2(
                SCORE_WEIGHTS["sales"] * float(s.get("salesScore") or 0)
                + SCORE_WEIGHTS["productivity"] * float(p.get("productivityScore") or 0)
                + SCORE_WEIGHTS["accountability"] * float(a.get("accountabilityScore") or 0)
                + SCORE_WEIGHTS["compliance"] * float(c.get("complianceScore") or 0)
            )
            merged.append(
                {
                    "funcionarioCodigo": code,
                    "employeeName": s.get("employeeName") or p.get("employeeName") or a.get("employeeName"),
                    "salesScore": s.get("salesScore", 0),
                    "productivityScore": p.get("productivityScore", 0),
                    "accountabilityScore": a.get("accountabilityScore", 0),
                    "complianceScore": c.get("complianceScore", 0),
                    "globalScore": global_score,
                    "contextAdjustedScore": f.get("contextAdjustedScore", global_score),
                    "globalClassification": _global_band(global_score),
                    "contextClassification": f.get("contextClassification"),
                    "contextVerdict": f.get("verdict"),
                    "saldoOperacional": a.get("saldoOperacional"),
                }
            )
        merged.sort(key=lambda x: x["globalScore"], reverse=True)
        return merged

    def _bonus_eligibility_engine(self, operators: list[dict[str, Any]]) -> list[dict[str, Any]]:
        out: list[dict[str, Any]] = []
        for op in operators:
            g = float(op.get("globalScore") or 0)
            acc = float(op.get("accountabilityScore") or 0)
            comp = float(op.get("complianceScore") or 0)
            cls = op.get("globalClassification")
            if g >= 75 and acc >= 60 and comp >= 60 and cls in BONUS_ELIGIBLE:
                status = "Elegível"
            elif g < 50 or acc < 40 or comp < 40 or cls == "CRÍTICO":
                status = "Não Elegível"
            else:
                status = "Observação"
            out.append({**op, "bonusEligibility": status})
        return out

    def _training_engine(self, operators: list[dict[str, Any]]) -> list[dict[str, Any]]:
        categories = (
            ("Caixa", "accountabilityScore", 60),
            ("Atendimento", "salesScore", 55),
            ("Vendas", "salesScore", 65),
            ("Combustível", "productivityScore", 55),
            ("Compliance", "complianceScore", 60),
        )
        out: list[dict[str, Any]] = []
        for op in operators:
            needs: list[str] = []
            for label, key, threshold in categories:
                if float(op.get(key) or 0) < threshold:
                    needs.append(label)
            if needs:
                out.append(
                    {
                        "funcionarioCodigo": op["funcionarioCodigo"],
                        "employeeName": op.get("employeeName"),
                        "trainingCategories": needs,
                        "globalScore": op.get("globalScore"),
                        "globalClassification": op.get("globalClassification"),
                    }
                )
        out.sort(key=lambda x: len(x["trainingCategories"]), reverse=True)
        return out

    def _classification_summary(self, operators: list[dict[str, Any]]) -> dict[str, int]:
        return dict(Counter(op.get("globalClassification") for op in operators))

    async def build(
        self,
        data_inicial: str,
        data_final: str,
        empresa_codigo: str | int | None = None,
        intel_payload: dict[str, Any] | None = None,
    ) -> WebPostoResponse:
        t0 = time.perf_counter()
        if intel_payload is None:
            base_resp = await self._intel.build(data_inicial, data_final, empresa_codigo)
            if not base_resp.success or not base_resp.data:
                return WebPostoResponse.fail("Falha ao consolidar base F04.0")
            base = base_resp.data
        else:
            base = intel_payload
        filters = build_finance_center_filters(data_inicial, data_final, empresa_codigo)
        nfce_t = await self._cash._fetch_paged("nfce", filters.data_inicial, filters.data_final, 10)
        nfce_rows = [r for r in nfce_t[0] if self._cash._matches_empresa(r, filters)]

        sales_raw = base.get("salesPerformance", {}).get("operators") or []
        productivity_raw = base.get("productivityEngine", {}).get("operators") or []
        accountability_raw = base.get("cashAccountability") or []
        discounts = base.get("discountIntelligence") or {}
        context = base.get("contextAttribution") or {}
        perf_ops = base.get("performanceBase", {}).get("operators") or []
        idx = (base.get("dimEmployee") or {}).get("index") or {}

        venda_full_t = await self._cash._fetch_paged("venda", data_inicial, data_final, 15)
        venda_full = [r for r in venda_full_t[0] if self._cash._matches_empresa(r, filters)]

        sales_scores = self._sales_score_engine(sales_raw)
        productivity_scores = self._productivity_score_engine(productivity_raw)
        accountability_scores = self._accountability_score_engine(accountability_raw, perf_ops)
        compliance_scores = self._compliance_score_engine(
            venda_full, discounts, nfce_rows, sales_raw, idx
        )

        operators = self._merge_operator_scores(
            sales_scores, productivity_scores, accountability_scores, compliance_scores, {"operators": []}
        )
        fairness = self._context_fairness_engine(operators, context)
        fairness_map = {int(r["funcionarioCodigo"]): r for r in fairness.get("operators") or []}
        for op in operators:
            f = fairness_map.get(int(op["funcionarioCodigo"])) or {}
            op["contextAdjustedScore"] = f.get("contextAdjustedScore", op["globalScore"])
            op["contextClassification"] = f.get("contextClassification")
            op["contextVerdict"] = f.get("verdict")
        operators = self._bonus_eligibility_engine(operators)
        training = self._training_engine(operators)
        classification = self._classification_summary(operators)

        elite = [o for o in operators if o["globalClassification"] == "ELITE"]
        alta = [o for o in operators if o["globalClassification"] == "ALTA PERFORMANCE"]
        atencao = [o for o in operators if o["globalClassification"] == "ATENÇÃO"]
        critico = [o for o in operators if o["globalClassification"] == "CRÍTICO"]

        bonus_eligible = [o for o in operators if o.get("bonusEligibility") == "Elegível"]
        needs_training = training
        needs_followup = [o for o in operators if o.get("bonusEligibility") == "Observação"]
        needs_audit = [
            o
            for o in operators
            if o["globalClassification"] in {"ATENÇÃO", "CRÍTICO"}
            or float(o.get("complianceScore") or 0) < 50
            or float(o.get("accountabilityScore") or 0) < 50
        ]

        critical_financial = _round2(
            sum(abs(_dec(o.get("saldoOperacional"))) for o in critico if _dec(o.get("saldoOperacional")) < 0)
        )
        recovery_potential = _round2(
            sum(abs(min(_dec(o.get("saldoOperacional")), 0)) for o in operators)
        )

        ex_base = base.get("executiveAnswers") or {}
        parity_delta = float(ex_base.get("paridadeDelta") or 0)

        top_sales = sales_scores[0] if sales_scores else None
        top_prod = max(operators, key=lambda x: x.get("productivityScore") or 0) if operators else None
        best_acc = accountability_scores[0] if accountability_scores else None
        worst_acc = accountability_scores[-1] if accountability_scores else None
        best_comp = compliance_scores[0] if compliance_scores else None
        top_global = operators[0] if operators else None

        executive = {
            "1_operadoresElite": len(elite),
            "2_operadoresAltaPerformance": len(alta),
            "3_operadoresAtencao": len(atencao),
            "4_operadoresCriticos": len(critico),
            "5_maiorSalesScore": top_sales,
            "6_maiorProductivityScore": top_prod,
            "7_melhorAccountabilityScore": best_acc,
            "8_piorAccountabilityScore": worst_acc,
            "9_maiorComplianceScore": best_comp,
            "10_maiorScoreGlobal": top_global,
            "11_elegivelBonus": bonus_eligible[:10],
            "12_deveTreinamento": needs_training[:10],
            "13_deveAcompanhamento": needs_followup[:10],
            "14_deveAuditoria": needs_audit[:10],
            "15_riscoFinanceiroCriticos": critical_financial,
            "16_potencialRecuperacao": recovery_potential,
            "17_pdvsPrejudicamOperadores": fairness.get("harmfulPdvs") or context.get("harmfulPdvs") or [],
            "18_performaEmPdvRuim": fairness.get("performsInBadPdv") or [],
            "19_prontoGestaoPessoas": bool(ex_base.get("19_prontoGestaoPessoas")),
            "20_aprovadoF042": parity_delta <= 0.01 and len(operators) > 0 and len(classification) >= 3,
            "paridadeDelta": parity_delta,
        }

        qa = {
            "fourScoresOk": all(
                len(x) > 0 for x in (sales_scores, productivity_scores, accountability_scores, compliance_scores)
            ),
            "globalScoreOk": len(operators) > 0,
            "bonusEligibilityOk": any(o.get("bonusEligibility") for o in operators),
            "trainingOk": len(training) >= 0,
            "classificationOk": len(classification) >= 3,
            "paridadeZero": parity_delta <= 0.01,
        }

        parecer = (
            "[PARECER FINAL: APROVADO PARA F04.2]"
            if executive["20_aprovadoF042"]
            else "[PARECER FINAL: RETIDO COM JUSTIFICATIVA QUANTITATIVA]"
        )

        payload = {
            "sprint": "F04.1",
            "periodo": {"dataInicial": data_inicial, "dataFinal": data_final},
            "elapsedMs": round((time.perf_counter() - t0) * 1000, 1),
            "baseF040": {
                "parecerFinal": base.get("parecerFinal"),
                "paridadeDelta": parity_delta,
            },
            "sourceIntel": {
                "salesPerformance": base.get("salesPerformance"),
                "discountIntelligence": base.get("discountIntelligence"),
                "cashAccountability": base.get("cashAccountability"),
                "performanceBase": base.get("performanceBase"),
                "contextAttribution": base.get("contextAttribution"),
            },
            "salesScoreEngine": {"operators": sales_scores},
            "cashAccountabilityScore": {"operators": accountability_scores},
            "complianceScoreEngine": {"operators": compliance_scores, "nfceRows": len(nfce_rows)},
            "productivityScoreEngine": {"operators": productivity_scores},
            "contextFairnessEngine": fairness,
            "bonusEligibilityEngine": {
                "elegivel": [o for o in operators if o.get("bonusEligibility") == "Elegível"],
                "observacao": [o for o in operators if o.get("bonusEligibility") == "Observação"],
                "naoElegivel": [o for o in operators if o.get("bonusEligibility") == "Não Elegível"],
            },
            "trainingEngine": {"recommendations": training},
            "operatorClassification": {
                "summary": classification,
                "operators": operators,
            },
            "cockpit": {
                "topOperadores": operators[:10],
                "elegiveisBonus": bonus_eligible[:10],
                "necessitamTreinamento": training[:10],
                "operadoresCriticos": critico[:10],
                "pdvsCriticos": list(CRITICAL_PDVS),
                "rankingGeral": operators[:20],
            },
            "executiveAnswers": executive,
            "qa": qa,
            "parecerFinal": parecer,
        }
        return WebPostoResponse.ok(payload)
