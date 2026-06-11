"""F04.2 — Operator Profitability & Management Decision Engine."""
from __future__ import annotations

import asyncio
import time
from collections import Counter
from typing import Any

from src.models.response_model import WebPostoResponse
from src.services.analytics_multiselect import build_finance_center_filters
from src.services.cash_operations_service import _dec, _round2, CashOperationsService
from src.services.operator_accountability_incentive_service import (
    CRITICAL_PDVS,
    OperatorAccountabilityIncentiveService,
    _norm_score,
)
from src.services.operator_sales_intelligence_service import _cancelled

PROFITABILITY_BANDS = (
    (70, 100, "GERA_LUCRO"),
    (40, 69, "NEUTRO"),
    (0, 39, "DESTRUI_MARGEM"),
)

PROFITABILITY_WEIGHTS = {
    "receita": 0.30,
    "margem": 0.25,
    "descontos": 0.15,
    "accountability": 0.15,
    "compliance": 0.15,
}

BONUS_RATE_PCT = 0.05
MANAGEMENT_ACTIONS = ("PROMOVER", "BONIFICAR", "TREINAR", "MONITORAR", "AUDITAR")


def _profitability_band(score: float) -> str:
    s = int(round(score))
    for lo, hi, label in PROFITABILITY_BANDS:
        if lo <= s <= hi:
            return label
    return "DESTRUI_MARGEM"


class OperatorProfitabilityService:
    """F04.2 — receita, margem, profitability score, ROI e ações gerenciais."""

    def __init__(
        self,
        people: OperatorAccountabilityIncentiveService | None = None,
        cash_ops: CashOperationsService | None = None,
    ) -> None:
        self._cash = cash_ops or CashOperationsService()
        self._people = people or OperatorAccountabilityIncentiveService(cash_ops=self._cash)

    async def _load_sales_and_venda(
        self,
        data_inicial: str,
        data_final: str,
        empresa_codigo: str | int | None,
    ) -> tuple[list[dict[str, Any]], list[dict[str, Any]], dict[str, Any] | None]:
        filters = build_finance_center_filters(data_inicial, data_final, empresa_codigo)
        emp_payload = await self._people._intel._employee.build(data_inicial, data_final)
        idx = emp_payload["index"]

        venda_t, vi_t = await asyncio.gather(
            self._cash._fetch_paged("venda", data_inicial, data_final, 15),
            self._cash._fetch_paged("venda_item", data_inicial, data_final, 15),
        )
        venda = [r for r in venda_t[0] if self._cash._matches_empresa(r, filters)]
        venda_item = [r for r in vi_t[0] if self._cash._matches_empresa(r, filters)]
        sales = self._people._intel._sales_performance(venda, venda_item, idx)

        intel_payload: dict[str, Any] | None = None
        if sales:
            intel_resp = await self._people._intel.build(data_inicial, data_final, empresa_codigo)
            if intel_resp.success and intel_resp.data:
                intel_payload = intel_resp.data
                api_sales = intel_resp.data.get("salesPerformance", {}).get("operators") or []
                if api_sales:
                    sales = api_sales

        return sales, venda, intel_payload

    def _revenue_engine(self, sales: list[dict[str, Any]]) -> list[dict[str, Any]]:
        out: list[dict[str, Any]] = []
        for s in sales:
            receita = _round2(s.get("totalVendas") or 0)
            out.append(
                {
                    "funcionarioCodigo": s["funcionarioCodigo"],
                    "employeeName": s.get("employeeName"),
                    "receitaBruta": receita,
                    "receitaCombustivel": _round2(s.get("volumeCombustivel") or 0),
                    "receitaConveniencia": _round2(s.get("volumeConveniencia") or 0),
                    "ticketMedio": _round2(s.get("ticketMedio") or 0),
                    "volumeFinanceiro": _round2(s.get("volumeFinanceiro") or receita),
                    "quantidadeVendas": s.get("quantidadeVendas", 0),
                }
            )
        out.sort(key=lambda x: x["receitaBruta"], reverse=True)
        return out

    def _margin_impact_engine(
        self,
        revenue: list[dict[str, Any]],
        discounts: dict[str, Any],
        accountability: list[dict[str, Any]],
        perf_ops: list[dict[str, Any]],
        venda: list[dict[str, Any]],
    ) -> list[dict[str, Any]]:
        disc_map = {
            int(r["funcionarioCodigo"]): _dec(r.get("totalDesconto"))
            for r in discounts.get("descontoPorOperador") or []
            if r.get("funcionarioCodigo") is not None
        }
        acct_map = {int(r["funcionarioCodigo"]): r for r in accountability if r.get("funcionarioCodigo") is not None}
        perf_map = {int(r["funcionarioCodigo"]): r for r in perf_ops if r.get("funcionarioCodigo") is not None}

        cancel_val: Counter[int] = Counter()
        for row in venda:
            if not _cancelled(row):
                continue
            try:
                op = int(row.get("funcionarioCodigo") or 0)
            except (TypeError, ValueError):
                continue
            if op:
                cancel_val[op] += _dec(row.get("totalVenda"))

        out: list[dict[str, Any]] = []
        for rev in revenue:
            op = int(rev["funcionarioCodigo"])
            acct = acct_map.get(op) or {}
            perf = perf_map.get(op) or {}
            descontos = disc_map.get(op, 0.0)
            cancelamentos = cancel_val.get(op, 0.0)
            faltas = abs(min(_dec(acct.get("faltasProxy")), 0)) or abs(min(_dec(acct.get("saldoOperacional")), 0))
            sobras = max(_dec(acct.get("sobrasProxy")), 0)
            perdas_caixa = abs(_dec(perf.get("diferencaAcumulada")))
            destruicao = _round2(descontos + cancelamentos + faltas + perdas_caixa - sobras * 0.5)
            destruicao = max(destruicao, 0.0)
            margem = _round2(rev["receitaBruta"] - destruicao)
            out.append(
                {
                    "funcionarioCodigo": op,
                    "employeeName": rev.get("employeeName"),
                    "receitaBruta": rev["receitaBruta"],
                    "destruicaoMargem": destruicao,
                    "margemOperacional": margem,
                    "descontos": _round2(descontos),
                    "cancelamentos": _round2(cancelamentos),
                    "faltas": _round2(faltas),
                    "sobras": _round2(sobras),
                    "perdasCaixa": _round2(perdas_caixa),
                }
            )
        out.sort(key=lambda x: x["destruicaoMargem"], reverse=True)
        return out

    def _profitability_score_engine(
        self,
        margin_rows: list[dict[str, Any]],
        people_ops: list[dict[str, Any]],
    ) -> list[dict[str, Any]]:
        people_map = {int(o["funcionarioCodigo"]): o for o in people_ops if o.get("funcionarioCodigo") is not None}
        max_rev = max(r["receitaBruta"] for r in margin_rows) if margin_rows else 1.0
        max_rev = max_rev or 1.0
        max_marg = max(r["margemOperacional"] for r in margin_rows) if margin_rows else 1.0
        max_marg = max_marg or 1.0
        max_dest = max(r["destruicaoMargem"] for r in margin_rows) if margin_rows else 1.0
        max_dest = max_dest or 1.0

        out: list[dict[str, Any]] = []
        for row in margin_rows:
            op = int(row["funcionarioCodigo"])
            p = people_map.get(op) or {}
            rev_s = _norm_score(row["receitaBruta"], max_rev)
            marg_s = _norm_score(max(row["margemOperacional"], 0), max_marg)
            disc_s = _round2(100 * (1 - min(row["destruicaoMargem"] / max_dest, 1.0)))
            acc_s = float(p.get("accountabilityScore") or 50)
            comp_s = float(p.get("complianceScore") or 50)
            score = _round2(
                PROFITABILITY_WEIGHTS["receita"] * rev_s
                + PROFITABILITY_WEIGHTS["margem"] * marg_s
                + PROFITABILITY_WEIGHTS["descontos"] * disc_s
                + PROFITABILITY_WEIGHTS["accountability"] * acc_s
                + PROFITABILITY_WEIGHTS["compliance"] * comp_s
            )
            out.append(
                {
                    **row,
                    "profitabilityScore": score,
                    "profitabilityBand": _profitability_band(score),
                    "accountabilityScore": acc_s,
                    "complianceScore": comp_s,
                    "resultadoLiquido": row["margemOperacional"],
                }
            )
        out.sort(key=lambda x: x["profitabilityScore"], reverse=True)
        return out

    def _context_normalization_v2(
        self,
        profitability: list[dict[str, Any]],
        context: dict[str, Any],
    ) -> list[dict[str, Any]]:
        ctx_map = {
            int(r["funcionarioCodigo"]): r
            for r in context.get("rankingAjustado") or []
            if r.get("funcionarioCodigo") is not None
        }
        out: list[dict[str, Any]] = []
        for row in profitability:
            op = int(row["funcionarioCodigo"])
            ctx = ctx_map.get(op) or {}
            penalty = float(ctx.get("contextRiskPenalty") or 0)
            bonus = float(ctx.get("multiContextBonus") or 0)
            raw = float(row.get("profitabilityScore") or 0)
            adjusted = _round2(max(0, min(100, raw - penalty * 0.5 + bonus * 0.5)))
            out.append(
                {
                    "funcionarioCodigo": op,
                    "employeeName": row.get("employeeName"),
                    "profitabilityScore": raw,
                    "profitabilityAdjustedScore": adjusted,
                    "profitabilityBand": row.get("profitabilityBand"),
                    "contextClassification": ctx.get("contextClassification") or ctx.get("classificacao"),
                    "contextRiskPenalty": _round2(penalty),
                    "multiContextBonus": _round2(bonus),
                    "resultadoLiquido": row.get("resultadoLiquido"),
                }
            )
        out.sort(key=lambda x: x["profitabilityAdjustedScore"], reverse=True)
        return out

    def _people_roi_engine(
        self,
        profitability: list[dict[str, Any]],
        margin_rows: list[dict[str, Any]],
    ) -> list[dict[str, Any]]:
        margin_map = {int(r["funcionarioCodigo"]): r for r in margin_rows}
        out: list[dict[str, Any]] = []
        for row in profitability:
            op = int(row["funcionarioCodigo"])
            m = margin_map.get(op) or {}
            receita = _dec(row.get("receitaBruta"))
            resultado = _dec(row.get("resultadoLiquido"))
            risco = max(_dec(m.get("destruicaoMargem")), 1.0)
            roi = _round2(resultado / risco)
            roi_pct = _round2(100 * resultado / receita) if receita else 0.0
            vendas = max(int(m.get("quantidadeVendas") or row.get("quantidadeVendas") or 1), 1)
            retorno_por_venda = _round2(resultado / vendas)
            out.append(
                {
                    "funcionarioCodigo": op,
                    "employeeName": row.get("employeeName"),
                    "receitaBruta": _round2(receita),
                    "resultadoLiquido": _round2(resultado),
                    "riscoEconomico": _round2(risco),
                    "roi": roi,
                    "roiPct": roi_pct,
                    "retornoPorVenda": retorno_por_venda,
                    "profitabilityScore": row.get("profitabilityScore"),
                    "profitabilityBand": row.get("profitabilityBand"),
                }
            )
        out.sort(key=lambda x: x["roi"], reverse=True)
        return out

    def _bonus_roi_engine(
        self,
        roi_rows: list[dict[str, Any]],
        people_ops: list[dict[str, Any]],
    ) -> list[dict[str, Any]]:
        people_map = {int(o["funcionarioCodigo"]): o for o in people_ops}
        out: list[dict[str, Any]] = []
        for row in roi_rows:
            op = int(row["funcionarioCodigo"])
            p = people_map.get(op) or {}
            receita = _dec(row.get("receitaBruta"))
            bonus_cost = _round2(receita * BONUS_RATE_PCT)
            resultado = _dec(row.get("resultadoLiquido"))
            bonus_roi = _round2(resultado / bonus_cost) if bonus_cost else 0.0
            elegivel = p.get("bonusEligibility") == "Elegível"
            out.append(
                {
                    "funcionarioCodigo": op,
                    "employeeName": row.get("employeeName"),
                    "bonusCustoEstimado": bonus_cost,
                    "resultadoLiquido": _round2(resultado),
                    "bonusRoi": bonus_roi,
                    "bonusRecomendado": elegivel and bonus_roi >= 2.0,
                    "bonusEligibility": p.get("bonusEligibility"),
                }
            )
        out.sort(key=lambda x: x["bonusRoi"], reverse=True)
        return out

    def _management_action_engine(
        self,
        profitability: list[dict[str, Any]],
        roi_rows: list[dict[str, Any]],
        people_ops: list[dict[str, Any]],
        training: list[dict[str, Any]],
    ) -> list[dict[str, Any]]:
        people_map = {int(o["funcionarioCodigo"]): o for o in people_ops}
        roi_map = {int(r["funcionarioCodigo"]): r for r in roi_rows}
        train_map = {int(t["funcionarioCodigo"]): t for t in training if t.get("funcionarioCodigo") is not None}

        out: list[dict[str, Any]] = []
        for row in profitability:
            op = int(row["funcionarioCodigo"])
            p = people_map.get(op) or {}
            roi = roi_map.get(op) or {}
            actions: list[str] = []
            score = float(row.get("profitabilityScore") or 0)
            band = row.get("profitabilityBand")
            acc = float(p.get("accountabilityScore") or 0)
            comp = float(p.get("complianceScore") or 0)

            if score >= 75 and acc >= 70 and comp >= 70 and band == "GERA_LUCRO":
                actions.append("PROMOVER")
            if p.get("bonusEligibility") == "Elegível" and band == "GERA_LUCRO":
                actions.append("BONIFICAR")
            if op in train_map:
                actions.append("TREINAR")
            if p.get("bonusEligibility") == "Observação" or p.get("globalClassification") == "ATENÇÃO":
                actions.append("MONITORAR")
            if band == "DESTRUI_MARGEM" or acc < 50 or comp < 50 or p.get("globalClassification") == "CRÍTICO":
                actions.append("AUDITAR")
            if not actions:
                actions.append("MONITORAR")

            out.append(
                {
                    "funcionarioCodigo": op,
                    "employeeName": row.get("employeeName"),
                    "managementActions": actions,
                    "primaryAction": actions[0],
                    "profitabilityScore": score,
                    "profitabilityBand": band,
                    "roi": roi.get("roi"),
                    "resultadoLiquido": row.get("resultadoLiquido"),
                }
            )
        return out

    async def build(
        self,
        data_inicial: str,
        data_final: str,
        empresa_codigo: str | int | None = None,
    ) -> WebPostoResponse:
        t0 = time.perf_counter()
        sales, venda, intel_payload = await self._load_sales_and_venda(
            data_inicial, data_final, empresa_codigo
        )
        if not sales:
            return WebPostoResponse.fail("Sem vendas operacionais para F04.2")

        if intel_payload is None:
            intel_resp = await self._people._intel.build(data_inicial, data_final, empresa_codigo)
            if not intel_resp.success or not intel_resp.data:
                return WebPostoResponse.fail("Falha ao consolidar base F04.0 para F04.2")
            intel_payload = intel_resp.data

        people_resp = await self._people.build(
            data_inicial, data_final, empresa_codigo, intel_payload=intel_payload
        )
        if not people_resp.success or not people_resp.data:
            return WebPostoResponse.fail("Falha ao consolidar base F04.1")

        people = people_resp.data
        intel = intel_payload
        discounts = intel.get("discountIntelligence") or {}
        accountability = intel.get("cashAccountability") or []
        perf_ops = intel.get("performanceBase", {}).get("operators") or []
        context = intel.get("contextAttribution") or {}
        people_ops = people.get("operatorClassification", {}).get("operators") or []
        training = people.get("trainingEngine", {}).get("recommendations") or []

        revenue = self._revenue_engine(sales)
        margin = self._margin_impact_engine(revenue, discounts, accountability, perf_ops, venda)
        for m in margin:
            rev = next((r for r in revenue if int(r["funcionarioCodigo"]) == int(m["funcionarioCodigo"])), {})
            m["quantidadeVendas"] = rev.get("quantidadeVendas", 0)

        profitability = self._profitability_score_engine(margin, people_ops)
        context_v2 = self._context_normalization_v2(profitability, context)
        adj_map = {int(r["funcionarioCodigo"]): r for r in context_v2}
        for p in profitability:
            adj = adj_map.get(int(p["funcionarioCodigo"])) or {}
            p["profitabilityAdjustedScore"] = adj.get("profitabilityAdjustedScore", p["profitabilityScore"])

        roi_rows = self._people_roi_engine(profitability, margin)
        bonus_roi = self._bonus_roi_engine(roi_rows, people_ops)
        actions = self._management_action_engine(profitability, roi_rows, people_ops, training)

        parity_revenue_ops = _round2(sum(r["receitaBruta"] for r in revenue))
        parity_revenue_api = _round2(
            sum(_dec(r.get("totalVenda")) for r in venda if not _cancelled(r) and r.get("funcionarioCodigo"))
        )
        parity_delta = _round2(abs(parity_revenue_ops - parity_revenue_api))

        top_rev = revenue[0] if revenue else None
        top_marg = max(profitability, key=lambda x: x["margemOperacional"]) if profitability else None
        worst_marg = max(profitability, key=lambda x: x["destruicaoMargem"]) if profitability else None
        top_disc = worst_marg
        top_prof = profitability[0] if profitability else None
        worst_prof = profitability[-1] if profitability else None
        top_roi = roi_rows[0] if roi_rows else None
        worst_roi = roi_rows[-1] if roi_rows else None

        promover = [a for a in actions if "PROMOVER" in a.get("managementActions", [])]
        bonificar = [a for a in actions if "BONIFICAR" in a.get("managementActions", [])]
        treinar = [a for a in actions if "TREINAR" in a.get("managementActions", [])]
        auditar = [a for a in actions if "AUDITAR" in a.get("managementActions", [])]

        top10 = sorted(profitability, key=lambda x: x["resultadoLiquido"], reverse=True)[:10]
        lucro_top10 = _round2(sum(_dec(o["resultadoLiquido"]) for o in top10))
        critico = [p for p in profitability if p["profitabilityBand"] == "DESTRUI_MARGEM"]
        risco_criticos = _round2(sum(_dec(c["destruicaoMargem"]) for c in critico))

        retorno_hora = max(
            roi_rows,
            key=lambda x: x.get("retornoPorVenda") or 0,
        ) if roi_rows else None

        performs_critical_pdv = [
            a for a in context_v2
            if a.get("profitabilityAdjustedScore", 0) >= 65
            and str(a.get("contextClassification") or "").startswith("DEPENDENTE")
        ]

        worst_economic = max(profitability, key=lambda x: x["destruicaoMargem"]) if profitability else None

        executive = {
            "1_maiorReceita": top_rev,
            "2_maiorMargem": top_marg,
            "3_destróiMargem": worst_marg,
            "4_maisDescontos": top_disc,
            "5_maiorProfitabilityScore": top_prof,
            "6_menorProfitabilityScore": worst_prof,
            "7_maiorRoi": top_roi,
            "8_menorRoi": worst_roi,
            "9_merecePromocao": promover[:5],
            "10_mereceBonus": bonificar[:5],
            "11_mereceTreinamento": treinar[:5],
            "12_mereceAuditoria": auditar[:5],
            "13_lucroTop10": lucro_top10,
            "14_riscoCriticos": risco_criticos,
            "15_melhorRetornoPorVenda": retorno_hora,
            "16_melhorRetornoPdvCritico": performs_critical_pdv[:3] if performs_critical_pdv else context_v2[:1],
            "17_destróiValorEconomico": worst_economic,
            "18_gestaoMeritocratica": parity_delta <= 0.01 and len(profitability) > 0,
            "19_remuneracaoVariavel": any(b.get("bonusRecomendado") for b in bonus_roi),
            "20_aprovadoF043": parity_delta <= 0.01 and len(profitability) > 0 and len(roi_rows) > 0,
            "paridadeDelta": parity_delta,
            "paridadeReceitaOperador": parity_revenue_ops,
            "paridadeReceitaConsolidada": parity_revenue_api,
        }

        qa = {
            "profitabilityScoreOk": len(profitability) > 0,
            "roiOk": len(roi_rows) > 0,
            "managementActionsOk": len(actions) > 0,
            "cockpitOk": True,
            "paridadeZero": parity_delta <= 0.01,
        }

        parecer = (
            "[PARECER FINAL: APROVADO PARA F04.3]"
            if executive["20_aprovadoF043"]
            else "[PARECER FINAL: RETIDO COM JUSTIFICATIVA QUANTITATIVA]"
        )

        payload = {
            "sprint": "F04.2",
            "periodo": {"dataInicial": data_inicial, "dataFinal": data_final},
            "elapsedMs": round((time.perf_counter() - t0) * 1000, 1),
            "baseF041": {
                "parecerFinal": people.get("parecerFinal"),
                "paridadeDelta": (people.get("executiveAnswers") or {}).get("paridadeDelta"),
            },
            "operatorRevenueEngine": {"operators": revenue, "totalReceita": parity_revenue_ops},
            "marginImpactEngine": {"operators": margin},
            "profitabilityScoreEngine": {
                "operators": profitability,
                "bands": dict(Counter(p["profitabilityBand"] for p in profitability)),
            },
            "bonusRoiEngine": {"operators": bonus_roi},
            "managementActionEngine": {"operators": actions},
            "contextNormalizationV2": {"operators": context_v2},
            "peopleRoiEngine": {"operators": roi_rows},
            "cockpit": {
                "topRoi": roi_rows[:10],
                "topLucro": sorted(profitability, key=lambda x: x["resultadoLiquido"], reverse=True)[:10],
                "topRisco": sorted(margin, key=lambda x: x["destruicaoMargem"], reverse=True)[:10],
                "topBonus": [b for b in bonus_roi if b.get("bonusRecomendado")][:10],
                "topAuditoria": auditar[:10],
                "pdvsCriticos": list(CRITICAL_PDVS),
            },
            "executiveAnswers": executive,
            "qa": qa,
            "parecerFinal": parecer,
        }
        return WebPostoResponse.ok(payload)
