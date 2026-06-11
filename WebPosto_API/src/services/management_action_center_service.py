"""F04.4 — Management Action Center & People Governance Intelligence."""
from __future__ import annotations

import time
from collections import Counter
from typing import Any

from src.models.response_model import WebPostoResponse
from src.services.cash_operations_service import _dec, _round2
from src.services.operator_accountability_incentive_service import CRITICAL_PDVS
from src.services.operator_accountability_incentive_snapshot_service import (
    OperatorAccountabilityIncentiveSnapshotService,
)
from src.services.operator_profitability_snapshot_service import OperatorProfitabilitySnapshotService
from src.services.store_shift_profitability_snapshot_service import StoreShiftProfitabilitySnapshotService

ACTION_TYPES = (
    "PROMOVER",
    "BONIFICAR",
    "TREINAR",
    "MONITORAR",
    "AUDITAR",
    "REALOCACAO",
    "REESTRUTURAR_PDV",
    "REVISAR_PROCESSO",
    "SEM_ACAO",
)

GOVERNANCE_BANDS = (
    "EMBAIXADOR",
    "ALTA_PERFORMANCE",
    "OPERADOR_PADRAO",
    "EM_OBSERVACAO",
    "EM_RECUPERACAO",
    "CRITICO",
)

TRAINING_CATEGORIES = ("CAIXA", "VENDAS", "CONFORMIDADE", "DESCONTOS", "PROCESSOS")

BONUS_RATE = 0.05


def _roi_norm(row: dict[str, Any]) -> float:
    pct = row.get("roiPct")
    if pct is not None:
        return float(pct)
    roi = float(row.get("roi") or 0)
    if roi <= 100:
        return roi
    return 100.0


def _risk_score(row: dict[str, Any]) -> float:
    acc = float(row.get("accountabilityScore") or 50)
    comp = float(row.get("complianceScore") or 50)
    dest = float(row.get("destruicaoMargem") or 0)
    rev = float(row.get("receitaBruta") or row.get("totalVendas") or 1)
    dest_pct = min(100.0, 100 * dest / max(rev, 1.0))
    band_penalty = {"DESTRUI_MARGEM": 30, "NEUTRO": 10, "GERA_LUCRO": 0}.get(
        str(row.get("profitabilityBand") or ""), 15
    )
    cls_penalty = 30 if row.get("globalClassification") == "CRÍTICO" else 0
    return _round2(max(0.0, min(100.0, dest_pct + band_penalty + cls_penalty + (100 - acc) * 0.3 + (100 - comp) * 0.1)))


class ManagementActionCenterService:
    """F04.4 — consolida F04.1/F04.2/F04.3 em governança e ações executáveis."""

    def __init__(
        self,
        people_snap: OperatorAccountabilityIncentiveSnapshotService | None = None,
        roi_snap: OperatorProfitabilitySnapshotService | None = None,
        op_snap: StoreShiftProfitabilitySnapshotService | None = None,
    ) -> None:
        self._people_snap = people_snap or OperatorAccountabilityIncentiveSnapshotService()
        self._roi_snap = roi_snap or OperatorProfitabilitySnapshotService()
        self._op_snap = op_snap or StoreShiftProfitabilitySnapshotService()

    async def _load_layers(
        self,
        data_inicial: str,
        data_final: str,
        empresa_codigo: str | int | None,
    ) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any]]:
        f041 = self._people_snap.get_master(data_inicial, data_final, empresa_codigo).get("payload")
        f042 = self._roi_snap.get_master(data_inicial, data_final, empresa_codigo).get("payload")
        f043 = self._op_snap.get_master(data_inicial, data_final, empresa_codigo).get("payload")

        if not f041:
            from src.services.operator_accountability_incentive_service import (
                OperatorAccountabilityIncentiveService,
            )

            resp = await OperatorAccountabilityIncentiveService().build(
                data_inicial, data_final, empresa_codigo
            )
            if not resp.success or not resp.data:
                raise RuntimeError(str(resp.error or "F04.1 indisponível"))
            f041 = resp.data
        if not f042:
            from src.services.operator_profitability_service import OperatorProfitabilityService

            resp = await OperatorProfitabilityService().build(data_inicial, data_final, empresa_codigo)
            if not resp.success or not resp.data:
                raise RuntimeError(str(resp.error or "F04.2 indisponível"))
            f042 = resp.data
        if not f043:
            from src.services.store_shift_profitability_service import StoreShiftProfitabilityService

            resp = await StoreShiftProfitabilityService().build(data_inicial, data_final, empresa_codigo)
            if not resp.success or not resp.data:
                raise RuntimeError(str(resp.error or "F04.3 indisponível"))
            f043 = resp.data
        return f041, f042, f043

    @staticmethod
    def _merge_operators(f041: dict[str, Any], f042: dict[str, Any]) -> list[dict[str, Any]]:
        merged: dict[int, dict[str, Any]] = {}
        for o in (f041.get("operatorClassification") or {}).get("operators") or []:
            op = int(o["funcionarioCodigo"])
            merged[op] = dict(o)
        prof_map = {
            int(r["funcionarioCodigo"]): r
            for r in (f042.get("profitabilityScoreEngine") or {}).get("operators") or []
            if r.get("funcionarioCodigo") is not None
        }
        roi_map = {
            int(r["funcionarioCodigo"]): r
            for r in (f042.get("peopleRoiEngine") or {}).get("operators") or []
            if r.get("funcionarioCodigo") is not None
        }
        margin_map = {
            int(r["funcionarioCodigo"]): r
            for r in (f042.get("marginImpactEngine") or {}).get("operators") or []
            if r.get("funcionarioCodigo") is not None
        }
        for op, row in merged.items():
            row.update(prof_map.get(op) or {})
            row.update(roi_map.get(op) or {})
            margin = margin_map.get(op) or {}
            row.setdefault("faltas", margin.get("faltas", 0))
            row.setdefault("destruicaoMargem", margin.get("destruicaoMargem", 0))
            row.setdefault("descontos", margin.get("descontos", 0))
            row["globalScore"] = row.get("globalScore") or row.get("peopleGlobalScore") or row.get(
                "profitabilityScore"
            )
            row["riskScore"] = _risk_score(row)
        return list(merged.values())

    def _action_engine(
        self,
        operators: list[dict[str, Any]],
        f041: dict[str, Any],
        f043: dict[str, Any],
    ) -> list[dict[str, Any]]:
        fairness = f041.get("contextFairnessEngine") or {}
        performs_bad = {
            int(x.get("funcionarioCodigo"))
            for x in (fairness.get("performsInBadPdv") or [])
            if x.get("funcionarioCodigo") is not None
        }
        forensics = f043.get("criticalPdvForensics") or {}
        structural_pdvs = {
            int(p)
            for p, rep in forensics.items()
            if (rep or {}).get("problemaEstrutural")
        }
        process_pdvs = {
            int(p)
            for p, rep in forensics.items()
            if (rep or {}).get("diagnosticoPrincipal") == "PROCESSO"
        }

        out: list[dict[str, Any]] = []
        for row in operators:
            op = int(row["funcionarioCodigo"])
            gs = float(row.get("globalScore") or 0)
            acc = float(row.get("accountabilityScore") or 0)
            roi_n = _roi_norm(row)
            risk = float(row.get("riskScore") or 0)
            faltas = float(row.get("faltas") or 0)
            dest = float(row.get("destruicaoMargem") or 0)
            rev = float(row.get("receitaBruta") or row.get("totalVendas") or 0)
            critical = row.get("globalClassification") == "CRÍTICO" or row.get(
                "profitabilityBand"
            ) == "DESTRUI_MARGEM"

            actions: list[str] = []
            evidence: dict[str, Any] = {}

            if gs >= 85 and acc >= 90 and roi_n >= 80 and not critical:
                actions.append("PROMOVER")
                evidence["PROMOVER"] = {
                    "globalScore": gs,
                    "accountabilityScore": acc,
                    "roiNorm": roi_n,
                    "critical": critical,
                }

            if row.get("bonusEligibility") == "Elegível" and float(row.get("resultadoLiquido") or 0) > 0 and acc >= 80:
                actions.append("BONIFICAR")
                evidence["BONIFICAR"] = {
                    "bonusEligibility": row.get("bonusEligibility"),
                    "resultadoLiquido": row.get("resultadoLiquido"),
                    "accountabilityScore": acc,
                }

            faltas_events = int(faltas / max(rev / max(row.get("quantidadeVendas") or 1, 1), 1)) if faltas else 0
            if acc < 70 or faltas >= 3 or faltas_events >= 3:
                actions.append("TREINAR")
                evidence["TREINAR"] = {
                    "accountabilityScore": acc,
                    "faltas": faltas,
                }

            if risk >= 70 or dest > rev * 0.15 or critical:
                actions.append("AUDITAR")
                evidence["AUDITAR"] = {
                    "riskScore": risk,
                    "destruicaoMargem": dest,
                    "receitaBruta": rev,
                }

            if row.get("bonusEligibility") == "Observação" or row.get("globalClassification") == "ATENÇÃO":
                if "MONITORAR" not in actions:
                    actions.append("MONITORAR")
                evidence["MONITORAR"] = {
                    "bonusEligibility": row.get("bonusEligibility"),
                    "globalClassification": row.get("globalClassification"),
                }

            if op in performs_bad:
                actions.append("REALOCACAO")
                evidence["REALOCACAO"] = {"performsInBadPdv": True}

            for pdv in structural_pdvs:
                actions.append("REESTRUTURAR_PDV")
                evidence["REESTRUTURAR_PDV"] = {"pdvCodigo": pdv, "problemaEstrutural": True}
                break

            for pdv in process_pdvs:
                actions.append("REVISAR_PROCESSO")
                evidence["REVISAR_PROCESSO"] = {"pdvCodigo": pdv, "diagnostico": "PROCESSO"}
                break

            if not actions:
                actions.append("SEM_ACAO")
                evidence["SEM_ACAO"] = {"globalScore": gs, "riskScore": risk}

            actions = list(dict.fromkeys(actions))
            out.append(
                {
                    "funcionarioCodigo": op,
                    "employeeName": row.get("employeeName"),
                    "recommendedActions": actions,
                    "primaryAction": actions[0],
                    "evidence": evidence,
                    "globalScore": gs,
                    "accountabilityScore": acc,
                    "roiNorm": roi_n,
                    "riskScore": risk,
                    "resultadoLiquido": row.get("resultadoLiquido"),
                    "profitabilityBand": row.get("profitabilityBand"),
                    "globalClassification": row.get("globalClassification"),
                }
            )
        return out

    @staticmethod
    def _governance_engine(operators: list[dict[str, Any]], actions: list[dict[str, Any]]) -> list[dict[str, Any]]:
        action_map = {int(a["funcionarioCodigo"]): a for a in actions}
        out: list[dict[str, Any]] = []
        for row in operators:
            op = int(row["funcionarioCodigo"])
            gs = float(row.get("globalScore") or 0)
            acc = float(row.get("accountabilityScore") or 0)
            band = row.get("profitabilityBand")
            cls = row.get("globalClassification")
            act = action_map.get(op) or {}

            if gs >= 90 and acc >= 90 and band == "GERA_LUCRO":
                gov = "EMBAIXADOR"
            elif gs >= 75 or cls in {"ELITE", "ALTA PERFORMANCE"} or band == "GERA_LUCRO":
                gov = "ALTA_PERFORMANCE"
            elif cls == "CRÍTICO" or band == "DESTRUI_MARGEM" or float(row.get("riskScore") or 0) >= 75:
                gov = "CRITICO"
            elif row.get("bonusEligibility") == "Observação" or cls == "ATENÇÃO" or "MONITORAR" in act.get(
                "recommendedActions", []
            ):
                gov = "EM_OBSERVACAO"
            elif "TREINAR" in act.get("recommendedActions", []) and band == "NEUTRO":
                gov = "EM_RECUPERACAO"
            else:
                gov = "OPERADOR_PADRAO"

            out.append(
                {
                    "funcionarioCodigo": op,
                    "employeeName": row.get("employeeName"),
                    "governanceBand": gov,
                    "globalScore": gs,
                    "accountabilityScore": acc,
                    "profitabilityBand": band,
                    "primaryAction": act.get("primaryAction"),
                }
            )
        return out

    @staticmethod
    def _promotion_engine(actions: list[dict[str, Any]]) -> list[dict[str, Any]]:
        promos = [a for a in actions if "PROMOVER" in a.get("recommendedActions", [])]
        promos.sort(key=lambda x: (x.get("globalScore") or 0, x.get("roiNorm") or 0), reverse=True)
        out: list[dict[str, Any]] = []
        for p in promos:
            ev = p.get("evidence", {}).get("PROMOVER") or {}
            out.append(
                {
                    **p,
                    "motivo": "Score global, accountability e ROI acima dos limiares de promoção",
                    "evidencias": ev,
                }
            )
        return out

    @staticmethod
    def _bonus_engine_v2(operators: list[dict[str, Any]], actions: list[dict[str, Any]]) -> list[dict[str, Any]]:
        action_map = {int(a["funcionarioCodigo"]): a for a in actions}
        out: list[dict[str, Any]] = []
        for row in operators:
            op = int(row["funcionarioCodigo"])
            act = action_map.get(op) or {}
            if "BONIFICAR" not in act.get("recommendedActions", []):
                continue
            resultado = float(row.get("resultadoLiquido") or 0)
            bonus = _round2(resultado * BONUS_RATE)
            roi_esperado = _round2(resultado / bonus) if bonus else 0
            out.append(
                {
                    "funcionarioCodigo": op,
                    "employeeName": row.get("employeeName"),
                    "bonusRecomendado": bonus,
                    "resultadoLiquido": resultado,
                    "bonusRoiEsperado": roi_esperado,
                    "evidence": act.get("evidence", {}).get("BONIFICAR"),
                }
            )
        out.sort(key=lambda x: x["bonusRoiEsperado"], reverse=True)
        return out

    @staticmethod
    def _training_engine(
        operators: list[dict[str, Any]],
        actions: list[dict[str, Any]],
    ) -> list[dict[str, Any]]:
        action_map = {int(a["funcionarioCodigo"]): a for a in actions}
        out: list[dict[str, Any]] = []
        for row in operators:
            op = int(row["funcionarioCodigo"])
            act = action_map.get(op) or {}
            if "TREINAR" not in act.get("recommendedActions", []):
                continue
            categories: list[str] = []
            if float(row.get("accountabilityScore") or 0) < 70 or float(row.get("faltas") or 0) >= 3:
                categories.append("CAIXA")
            if float(row.get("complianceScore") or 100) < 70:
                categories.append("CONFORMIDADE")
            if float(row.get("descontos") or 0) > 0:
                categories.append("DESCONTOS")
            if float(row.get("totalVendas") or row.get("receitaBruta") or 0) < 100:
                categories.append("VENDAS")
            if not categories:
                categories.append("PROCESSOS")
            out.append(
                {
                    "funcionarioCodigo": op,
                    "employeeName": row.get("employeeName"),
                    "trainingCategories": categories,
                    "evidence": act.get("evidence", {}).get("TREINAR"),
                }
            )
        return out

    @staticmethod
    def _intervention_engine(f043: dict[str, Any]) -> dict[str, Any]:
        ex = f043.get("executiveAnswers") or {}
        forensics = f043.get("criticalPdvForensics") or {}
        return {
            "pdvsIntervencao": ex.get("13_pdvIntervencao") or [],
            "turnosIntervencao": ex.get("14_turnoIntervencao") or [],
            "pdvImediato": (ex.get("13_pdvIntervencao") or [{}])[0] if ex.get("13_pdvIntervencao") else None,
            "turnoImediato": ex.get("6_turnoMaiorPerdas"),
            "processosRevisar": [
                {"pdvCodigo": int(p), **(rep or {})}
                for p, rep in forensics.items()
                if (rep or {}).get("diagnosticoPrincipal") in {"PROCESSO", "PDV"}
            ],
        }

    @staticmethod
    def _timeline_engine(actions: list[dict[str, Any]]) -> list[dict[str, Any]]:
        out: list[dict[str, Any]] = []
        for act in actions:
            if act.get("primaryAction") == "SEM_ACAO":
                continue
            milestones = []
            if "TREINAR" in act.get("recommendedActions", []):
                milestones.append({"evento": "Treinamento", "prazo": "D+15"})
            milestones.append({"evento": "Reavaliação", "prazo": "D+30"})
            if "AUDITAR" in act.get("recommendedActions", []):
                milestones.append({"evento": "Auditoria", "prazo": "D+60"})
            out.append(
                {
                    "funcionarioCodigo": act["funcionarioCodigo"],
                    "employeeName": act.get("employeeName"),
                    "primaryAction": act.get("primaryAction"),
                    "milestones": milestones,
                }
            )
        return out

    @staticmethod
    def _qa_engine(
        actions: list[dict[str, Any]],
        f042: dict[str, Any],
        f043: dict[str, Any],
    ) -> dict[str, Any]:
        ex042 = f042.get("executiveAnswers") or {}
        ex043 = f043.get("executiveAnswers") or {}
        paridade_f042 = float(ex042["paridadeDelta"]) if ex042.get("paridadeDelta") is not None else 999.0
        paridade_f043 = float(ex043["paridadeDelta"]) if ex043.get("paridadeDelta") is not None else 999.0
        paridade_delta = _round2(max(paridade_f042, paridade_f043))

        sem_evidencia = 0
        falsos_positivos = 0
        for act in actions:
            primary = act.get("primaryAction")
            ev_all = act.get("evidence") or {}
            ev = ev_all.get(primary)
            if primary != "SEM_ACAO" and not ev:
                sem_evidencia += 1
            if primary == "PROMOVER" and ev:
                if not (
                    ev.get("globalScore", 0) >= 85
                    and ev.get("accountabilityScore", 0) >= 90
                    and ev.get("roiNorm", 0) >= 80
                    and not ev.get("critical")
                ):
                    falsos_positivos += 1
            if primary == "BONIFICAR" and ev:
                if ev.get("accountabilityScore", 0) < 80:
                    falsos_positivos += 1

        total_acoes = sum(
            1 for a in actions if a.get("primaryAction") and a.get("primaryAction") != "SEM_ACAO"
        )
        com_evidencia = total_acoes - sem_evidencia
        pct_evidencia = _round2(100 * com_evidencia / total_acoes) if total_acoes else 100.0

        return {
            "paridadeDelta": paridade_delta,
            "paridadeZero": paridade_delta <= 0.01,
            "acoesSemEvidencia": sem_evidencia,
            "falsosPositivos": falsos_positivos,
            "totalAcoes": total_acoes,
            "acoesComEvidenciaPct": pct_evidencia,
            "evidenciaCompleta": sem_evidencia == 0 and falsos_positivos == 0,
            "paridadeReceitaF042": ex042.get("paridadeReceitaOperador"),
            "paridadeReceitaF043": ex043.get("paridadeReceitaConsolidada"),
        }

    async def build(
        self,
        data_inicial: str,
        data_final: str,
        empresa_codigo: str | int | None = None,
    ) -> WebPostoResponse:
        t0 = time.perf_counter()
        try:
            f041, f042, f043 = await self._load_layers(data_inicial, data_final, empresa_codigo)
        except RuntimeError as exc:
            return WebPostoResponse.fail(str(exc))

        operators = self._merge_operators(f041, f042)
        if not operators:
            return WebPostoResponse.fail("Sem operadores na baseline F04.1/F04.2")

        actions = self._action_engine(operators, f041, f043)
        governance = self._governance_engine(operators, actions)
        promotions = self._promotion_engine(actions)
        bonuses = self._bonus_engine_v2(operators, actions)
        training = self._training_engine(operators, actions)
        intervention = self._intervention_engine(f043)
        timeline = self._timeline_engine(actions)
        qa = self._qa_engine(actions, f042, f043)

        action_counts = Counter()
        for a in actions:
            for t in a.get("recommendedActions") or []:
                action_counts[t] += 1

        promov = [a for a in actions if "PROMOVER" in a.get("recommendedActions", [])]
        bonus_a = [a for a in actions if "BONIFICAR" in a.get("recommendedActions", [])]
        train_a = [a for a in actions if "TREINAR" in a.get("recommendedActions", [])]
        audit_a = [a for a in actions if "AUDITAR" in a.get("recommendedActions", [])]

        gov_map = {int(g["funcionarioCodigo"]): g for g in governance}
        critico = [g for g in governance if g["governanceBand"] == "CRITICO"]
        observacao = [g for g in governance if g["governanceBand"] == "EM_OBSERVACAO"]
        recuperacao = [g for g in governance if g["governanceBand"] == "EM_RECUPERACAO"]
        maior_risco = max(actions, key=lambda x: x.get("riskScore") or 0) if actions else None

        valor_bonus = _round2(sum(b.get("bonusRecomendado") or 0 for b in bonuses))
        risco_reduzivel = _round2(
            sum(float(o.get("destruicaoMargem") or 0) for o in operators if float(o.get("riskScore") or 0) >= 70)
        )
        valor_recuperavel = _round2(risco_reduzivel * 0.3)
        impacto_esperado = _round2(
            sum(float(o.get("resultadoLiquido") or 0) for o in operators if "PROMOVER" in (gov_map.get(int(o["funcionarioCodigo"]), {}).get("primaryAction") or ""))
            + valor_bonus
        )

        executive = {
            "1_elegiveisPromocao": len(promov),
            "2_elegiveisBonus": len(bonus_a),
            "3_precisamTreinamento": len(train_a),
            "4_precisamAuditoria": len(audit_a),
            "5_principalPromocao": promotions[0] if promotions else None,
            "6_principalBonus": bonuses[0] if bonuses else None,
            "7_maiorRiscoOperacional": maior_risco,
            "8_emRecuperacao": recuperacao[:5],
            "9_emObservacao": observacao[:5],
            "10_pdvIntervencaoImediata": intervention.get("pdvImediato"),
            "11_turnoIntervencaoImediata": intervention.get("turnoImediato"),
            "12_acoesAutomaticasGeradas": qa.get("totalAcoes"),
            "13_acaoMaisRecorrente": action_counts.most_common(1)[0][0] if action_counts else "SEM_ACAO",
            "14_impactoFinanceiroEsperado": impacto_esperado,
            "15_riscoReduzivel": risco_reduzivel,
            "16_valorRecuperavel": valor_recuperavel,
            "17_gestaoMeritocratica": qa.get("paridadeZero") and qa.get("evidenciaCompleta"),
            "18_planoCarreira": len(promotions) > 0,
            "19_governancaOperacional": len(governance) > 0,
            "20_aprovadoF045": (
                qa.get("paridadeZero")
                and qa.get("evidenciaCompleta")
                and len(actions) > 0
            ),
            "paridadeDelta": qa.get("paridadeDelta"),
        }

        parecer = (
            "[PARECER FINAL: APROVADO PARA F04.5]"
            if executive["20_aprovadoF045"]
            else "[PARECER FINAL: RETIDO COM JUSTIFICATIVA QUANTITATIVA]"
        )

        payload = {
            "sprint": "F04.4",
            "periodo": {"dataInicial": data_inicial, "dataFinal": data_final},
            "elapsedMs": round((time.perf_counter() - t0) * 1000, 1),
            "baseline": {
                "f041Parecer": f041.get("parecerFinal"),
                "f042Parecer": f042.get("parecerFinal"),
                "f043Parecer": f043.get("parecerFinal"),
            },
            "actionEngine": {"operators": actions, "actionCounts": dict(action_counts)},
            "peopleGovernanceEngine": {
                "operators": governance,
                "bands": dict(Counter(g["governanceBand"] for g in governance)),
            },
            "promotionEngine": {"candidates": promotions},
            "bonusEngineV2": {"candidates": bonuses, "valorTotalBonus": valor_bonus},
            "trainingEngine": {"plans": training},
            "operationalInterventionEngine": intervention,
            "managementTimelineEngine": {"items": timeline},
            "cockpit": {
                "acoesPendentes": [a for a in actions if a.get("primaryAction") != "SEM_ACAO"][:15],
                "promocoes": promotions[:10],
                "bonificacoes": bonuses[:10],
                "treinamentos": training[:10],
                "auditorias": audit_a[:10],
                "pdvsCriticos": (f043.get("cockpit") or {}).get("pdvsCriticos") or [],
                "turnosCriticos": (f043.get("cockpit") or {}).get("turnosCriticos") or [],
            },
            "executiveAnswers": executive,
            "qa": qa,
            "parecerFinal": parecer,
        }
        return WebPostoResponse.ok(payload)
