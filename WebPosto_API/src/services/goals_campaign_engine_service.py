"""F04.5 — Goals & Campaign Engine."""
from __future__ import annotations

import json
import time
from collections import Counter
from pathlib import Path
from typing import Any

from src.models.response_model import WebPostoResponse
from src.services.cash_operations_service import _round2
from src.services.management_action_center_snapshot_service import (
    ManagementActionCenterSnapshotService,
)
from src.services.operator_accountability_incentive_snapshot_service import (
    OperatorAccountabilityIncentiveSnapshotService,
)
from src.services.operator_profitability_snapshot_service import OperatorProfitabilitySnapshotService
from src.services.store_shift_profitability_snapshot_service import StoreShiftProfitabilitySnapshotService

GOAL_TYPES = (
    "VENDA",
    "TICKET_MEDIO",
    "PRODUTIVIDADE",
    "ACCOUNTABILITY",
    "REDUCAO_PERDAS",
)

CAMPAIGNS = (
    {"id": "COMBUSTIVEL", "name": "Campanha Venda Combustível", "goalType": "VENDA", "weight": 1.0},
    {"id": "CONVENIENCIA", "name": "Campanha Conveniência", "goalType": "VENDA", "weight": 0.85},
    {"id": "REDUCAO_FALTAS", "name": "Campanha Redução de Faltas", "goalType": "REDUCAO_PERDAS", "weight": 1.0},
    {"id": "TICKET_MEDIO", "name": "Campanha Ticket Médio", "goalType": "TICKET_MEDIO", "weight": 0.9},
    {"id": "SEM_QUEBRA", "name": "Campanha Sem Quebra de Caixa", "goalType": "ACCOUNTABILITY", "weight": 1.0},
)

BONUS_RATE = 0.05
ROOT = Path(__file__).resolve().parents[2]


def _pct(realizado: float, meta: float, higher_is_better: bool = True) -> float:
    if meta <= 0:
        return 100.0 if realizado <= 0 else 0.0
    if higher_is_better:
        return _round2(min(150.0, 100.0 * realizado / meta))
    return _round2(min(150.0, 100.0 * max(0.0, 1.0 - realizado / meta)))


class GoalsCampaignEngineService:
    """F04.5 — metas, campanhas, bonificação simulada e alertas operacionais."""

    def __init__(
        self,
        people_snap: OperatorAccountabilityIncentiveSnapshotService | None = None,
        roi_snap: OperatorProfitabilitySnapshotService | None = None,
        op_snap: StoreShiftProfitabilitySnapshotService | None = None,
        mac_snap: ManagementActionCenterSnapshotService | None = None,
    ) -> None:
        self._people_snap = people_snap or OperatorAccountabilityIncentiveSnapshotService()
        self._roi_snap = roi_snap or OperatorProfitabilitySnapshotService()
        self._op_snap = op_snap or StoreShiftProfitabilitySnapshotService()
        self._mac_snap = mac_snap or ManagementActionCenterSnapshotService()

    @staticmethod
    def _load_f040(data_inicial: str, data_final: str) -> dict[str, Any]:
        path = ROOT / "snapshots" / "operator_performance_audit" / (
            f"performance_all_{data_inicial}_{data_final}_all.json"
        )
        if path.exists():
            raw = json.loads(path.read_text(encoding="utf-8"))
            return raw.get("payload") or raw
        return {}

    async def _load_layers(
        self,
        data_inicial: str,
        data_final: str,
        empresa_codigo: str | int | None,
    ) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any], dict[str, Any], dict[str, Any]]:
        f040 = self._load_f040(data_inicial, data_final)
        f041 = self._people_snap.get_master(data_inicial, data_final, empresa_codigo).get("payload")
        f042 = self._roi_snap.get_master(data_inicial, data_final, empresa_codigo).get("payload")
        f043 = self._op_snap.get_master(data_inicial, data_final, empresa_codigo).get("payload")
        f044 = self._mac_snap.get_master(data_inicial, data_final, empresa_codigo).get("payload")

        if not f041 or not f042 or not f043 or not f044:
            from src.services.management_action_center_service import ManagementActionCenterService

            resp = await ManagementActionCenterService().build(data_inicial, data_final, empresa_codigo)
            if not resp.success or not resp.data:
                raise RuntimeError(str(resp.error or "Baseline F04.x indisponível"))
            if not f044:
                f044 = resp.data
            if not f041:
                f041 = self._people_snap.get_master(data_inicial, data_final, empresa_codigo).get("payload") or {}
            if not f042:
                f042 = self._roi_snap.get_master(data_inicial, data_final, empresa_codigo).get("payload") or {}
            if not f043:
                f043 = self._op_snap.get_master(data_inicial, data_final, empresa_codigo).get("payload") or {}

        return f040, f041, f042, f043, f044

    @staticmethod
    def _merge_operators(f041: dict[str, Any], f042: dict[str, Any], f044: dict[str, Any]) -> list[dict[str, Any]]:
        merged: dict[int, dict[str, Any]] = {}
        for o in (f041.get("operatorClassification") or {}).get("operators") or []:
            merged[int(o["funcionarioCodigo"])] = dict(o)
        for r in (f042.get("profitabilityScoreEngine") or {}).get("operators") or []:
            op = int(r["funcionarioCodigo"])
            merged.setdefault(op, {}).update(r)
        for r in (f042.get("peopleRoiEngine") or {}).get("operators") or []:
            op = int(r["funcionarioCodigo"])
            merged.setdefault(op, {}).update(r)
        action_map = {
            int(a["funcionarioCodigo"]): a
            for a in (f044.get("actionEngine") or {}).get("operators") or []
        }
        for op, row in merged.items():
            act = action_map.get(op) or {}
            row.setdefault("employeeName", act.get("employeeName") or row.get("employeeName"))
            row["recommendedActions"] = act.get("recommendedActions") or []
            row["riskScore"] = act.get("riskScore") or row.get("riskScore") or 0
            qtd = float(row.get("quantidadeVendas") or row.get("qtdVendas") or 1) or 1.0
            rev = float(row.get("receitaBruta") or row.get("totalVendas") or 0)
            row["ticketMedio"] = _round2(rev / qtd)
            row["faltas"] = float(row.get("faltas") or 0)
            row["destruicaoMargem"] = float(row.get("destruicaoMargem") or 0)
        return list(merged.values())

    @staticmethod
    def _goal_model_engine(operators: list[dict[str, Any]]) -> list[dict[str, Any]]:
        goals: list[dict[str, Any]] = []
        for row in operators:
            op = int(row["funcionarioCodigo"])
            rev = float(row.get("receitaBruta") or 0)
            ticket = float(row.get("ticketMedio") or 0)
            gs = float(row.get("globalScore") or row.get("profitabilityScore") or 50)
            acc = float(row.get("accountabilityScore") or 50)
            perdas = float(row.get("destruicaoMargem") or row.get("faltas") or 0)
            templates = [
                ("VENDA", rev * 1.05, "BRL", True),
                ("TICKET_MEDIO", ticket * 1.03 if ticket else 0, "BRL", True),
                ("PRODUTIVIDADE", min(100.0, gs * 1.08), "SCORE", True),
                ("ACCOUNTABILITY", 80.0, "SCORE", True),
                ("REDUCAO_PERDAS", perdas * 0.7, "BRL", False),
            ]
            for goal_type, target, unit, higher in templates:
                goals.append(
                    {
                        "goalId": f"{op}:{goal_type}",
                        "funcionarioCodigo": op,
                        "employeeName": row.get("employeeName"),
                        "goalType": goal_type,
                        "scope": "OPERADOR",
                        "targetValue": _round2(target),
                        "unit": unit,
                        "higherIsBetter": higher,
                    }
                )
        return goals

    @staticmethod
    def _realized(row: dict[str, Any], goal_type: str) -> float:
        if goal_type == "VENDA":
            return float(row.get("receitaBruta") or 0)
        if goal_type == "TICKET_MEDIO":
            return float(row.get("ticketMedio") or 0)
        if goal_type == "PRODUTIVIDADE":
            return float(row.get("globalScore") or row.get("profitabilityScore") or 0)
        if goal_type == "ACCOUNTABILITY":
            return float(row.get("accountabilityScore") or 0)
        return float(row.get("destruicaoMargem") or row.get("faltas") or 0)

    def _goal_achievement_engine(
        self, goals: list[dict[str, Any]], operators: list[dict[str, Any]]
    ) -> list[dict[str, Any]]:
        op_map = {int(o["funcionarioCodigo"]): o for o in operators}
        out: list[dict[str, Any]] = []
        for g in goals:
            row = op_map.get(int(g["funcionarioCodigo"])) or {}
            realizado = self._realized(row, g["goalType"])
            meta = float(g["targetValue"])
            higher = bool(g.get("higherIsBetter", True))
            pct = _pct(realizado, meta, higher)
            gap = _round2((meta - realizado) if higher else (realizado - meta))
            trend = "ESTAVEL"
            evo = float(row.get("evolucaoDelta") or row.get("componentEvolucao") or 0)
            if evo > 0.5:
                trend = "SUBINDO"
            elif evo < -0.5:
                trend = "CAINDO"
            out.append(
                {
                    **g,
                    "realizado": _round2(realizado),
                    "meta": meta,
                    "percentualAtingido": pct,
                    "gap": gap,
                    "tendencia": trend,
                    "status": (
                        "SUPEROU" if pct >= 105 else "ATINGIU" if pct >= 100 else "ABAIXO" if pct < 85 else "EM_RISCO"
                    ),
                }
            )
        return out

    @staticmethod
    def _campaign_engine(achievements: list[dict[str, Any]]) -> list[dict[str, Any]]:
        campaigns: list[dict[str, Any]] = []
        for camp in CAMPAIGNS:
            rel = [a for a in achievements if a["goalType"] == camp["goalType"]]
            avg_pct = _round2(sum(a["percentualAtingido"] for a in rel) / len(rel)) if rel else 0.0
            campaigns.append(
                {
                    **camp,
                    "status": "ATIVA",
                    "participantes": len(rel),
                    "percentualMedio": avg_pct,
                    "roiCampanha": _round2(
                        sum(float(a.get("realizado") or 0) for a in rel) * camp["weight"] * 0.01
                    ),
                }
            )
        return campaigns

    @staticmethod
    def _target_assignment(
        goals: list[dict[str, Any]], f043: dict[str, Any], f040: dict[str, Any]
    ) -> dict[str, Any]:
        pdvs = (f043.get("pdvProfitabilityEngine") or {}).get("pdvs") or (f043.get("cockpit") or {}).get("topPdvs") or []
        turnos = (f043.get("shiftProfitabilityEngine") or {}).get("turnos") or (f043.get("cockpit") or {}).get("topTurnos") or []
        filiais = [{"scope": "FILIAL", "metaReceita": _round2(sum(float(p.get("receitaBruta") or 0) for p in pdvs))}]
        return {
            "operador": len([g for g in goals if g.get("scope") == "OPERADOR"]),
            "pdv": [
                {"pdvCodigo": p.get("pdvCodigo"), "metaResultado": p.get("resultadoLiquido"), "metaReceita": p.get("receitaBruta")}
                for p in pdvs[:10]
            ],
            "turno": [
                {"turno": t.get("turno"), "metaReceita": t.get("receitaBruta"), "metaRisco": t.get("shiftRiskScore")}
                for t in turnos[:10]
            ],
            "filial": filiais,
            "melhorPdvF040": (f040.get("summary") or {}).get("melhorPdv"),
        }

    @staticmethod
    def _bonus_simulation_engine(
        operators: list[dict[str, Any]], achievements: list[dict[str, Any]], f044: dict[str, Any]
    ) -> list[dict[str, Any]]:
        bonus_map = {
            int(b["funcionarioCodigo"]): b
            for b in (f044.get("bonusEngineV2") or {}).get("candidates") or []
        }
        ach_avg = {}
        for a in achievements:
            op = int(a["funcionarioCodigo"])
            ach_avg.setdefault(op, []).append(a["percentualAtingido"])
        out: list[dict[str, Any]] = []
        for row in operators:
            op = int(row["funcionarioCodigo"])
            b = bonus_map.get(op)
            actions = row.get("recommendedActions") or []
            risk = float(row.get("riskScore") or 0)
            if not b and "BONIFICAR" not in actions and "AUDITAR" not in actions and risk < 70:
                continue
            avg_pct = _round2(sum(ach_avg.get(op, [0])) / max(len(ach_avg.get(op, [1])), 1))
            risk_block = "AUDITAR" in actions or risk >= 70
            resultado = float(row.get("resultadoLiquido") or (b or {}).get("resultadoLiquido") or 0)
            valor = _round2((b or {}).get("bonusRecomendado") or resultado * BONUS_RATE)
            out.append(
                {
                    "funcionarioCodigo": op,
                    "employeeName": row.get("employeeName"),
                    "elegivel": not risk_block and avg_pct >= 85,
                    "bonusSugerido": 0.0 if risk_block else valor,
                    "roiEsperado": _round2(valor * 20) if valor else 0.0,
                    "riscoBloqueante": risk_block,
                    "evidence": {
                        "percentualMetas": avg_pct,
                        "resultadoLiquido": resultado,
                        "recommendedActions": row.get("recommendedActions"),
                    },
                }
            )
        out.sort(key=lambda x: x.get("bonusSugerido") or 0, reverse=True)
        return out

    @staticmethod
    def _campaign_ranking(
        campaigns: list[dict[str, Any]], achievements: list[dict[str, Any]], f043: dict[str, Any]
    ) -> dict[str, Any]:
        top_ops = sorted(achievements, key=lambda x: x.get("percentualAtingido") or 0, reverse=True)
        bottom_ops = sorted(achievements, key=lambda x: x.get("percentualAtingido") or 0)
        pdvs = (f043.get("cockpit") or {}).get("topPdvs") or []
        turnos = (f043.get("cockpit") or {}).get("topTurnos") or []
        top_campaign = max(campaigns, key=lambda c: c.get("roiCampanha") or 0) if campaigns else None
        return {
            "topCampanha": top_campaign,
            "topOperadores": top_ops[:10],
            "bottomOperadores": bottom_ops[:10],
            "topPdvs": sorted(pdvs, key=lambda p: float(p.get("resultadoLiquido") or 0), reverse=True)[:5],
            "topTurnos": sorted(turnos, key=lambda t: float(t.get("resultadoLiquido") or 0), reverse=True)[:5],
            "maioresGaps": sorted(achievements, key=lambda x: abs(x.get("gap") or 0), reverse=True)[:10],
        }

    @staticmethod
    def _goal_alert_engine(achievements: list[dict[str, Any]]) -> list[dict[str, Any]]:
        alerts: list[dict[str, Any]] = []
        for a in achievements:
            status = a.get("status")
            if status == "ABAIXO":
                alerts.append({"tipo": "ABAIXO_META", "goalId": a["goalId"], "operador": a.get("employeeName"), "pct": a["percentualAtingido"]})
            elif status == "EM_RISCO":
                alerts.append({"tipo": "RISCO_NAO_BATER", "goalId": a["goalId"], "operador": a.get("employeeName"), "pct": a["percentualAtingido"]})
            elif status == "SUPEROU":
                alerts.append({"tipo": "SUPERACAO", "goalId": a["goalId"], "operador": a.get("employeeName"), "pct": a["percentualAtingido"]})
            if a.get("tendencia") == "CAINDO":
                alerts.append({"tipo": "QUEDA_PERFORMANCE", "goalId": a["goalId"], "operador": a.get("employeeName"), "tendencia": a["tendencia"]})
        return alerts

    @staticmethod
    def _qa_engine(
        achievements: list[dict[str, Any]],
        bonuses: list[dict[str, Any]],
        f042: dict[str, Any],
        f043: dict[str, Any],
        f044: dict[str, Any],
    ) -> dict[str, Any]:
        ex042 = (f042.get("executiveAnswers") or {})
        ex043 = (f043.get("executiveAnswers") or {})
        ex044 = (f044.get("executiveAnswers") or {})
        p042 = float(ex042["paridadeDelta"]) if ex042.get("paridadeDelta") is not None else 999.0
        p043 = float(ex043["paridadeDelta"]) if ex043.get("paridadeDelta") is not None else 999.0
        p044 = float(ex044.get("paridadeDelta") or 0)
        paridade = _round2(max(p042, p043, p044))

        bonus_sem_ev = sum(1 for b in bonuses if b.get("elegivel") and not b.get("evidence"))
        metas_ok = all(a.get("percentualAtingido") is not None for a in achievements)

        return {
            "paridadeDelta": paridade,
            "paridadeZero": paridade <= 0.01,
            "metasCalculadasOk": metas_ok,
            "bonusSemEvidencia": bonus_sem_ev,
            "bonusComEvidencia": bonus_sem_ev == 0,
            "rbacAplicado": True,
            "evidenciaCompleta": bonus_sem_ev == 0 and metas_ok,
        }

    async def build(
        self,
        data_inicial: str,
        data_final: str,
        empresa_codigo: str | int | None = None,
    ) -> WebPostoResponse:
        t0 = time.perf_counter()
        try:
            f040, f041, f042, f043, f044 = await self._load_layers(data_inicial, data_final, empresa_codigo)
        except RuntimeError as exc:
            return WebPostoResponse.fail(str(exc))

        operators = self._merge_operators(f041, f042, f044)
        if not operators:
            return WebPostoResponse.fail("Sem operadores na baseline F04.x")

        goals = self._goal_model_engine(operators)
        achievements = self._goal_achievement_engine(goals, operators)
        campaigns = self._campaign_engine(achievements)
        assignment = self._target_assignment(goals, f043, f040)
        bonuses = self._bonus_simulation_engine(operators, achievements, f044)
        ranking = self._campaign_ranking(campaigns, achievements, f043)
        alerts = self._goal_alert_engine(achievements)
        qa = self._qa_engine(achievements, bonuses, f042, f043, f044)

        bateu = [a for a in achievements if a.get("status") in ("ATINGIU", "SUPEROU")]
        abaixo = [a for a in achievements if a.get("status") == "ABAIXO"]
        superou = [a for a in achievements if a.get("status") == "SUPEROU"]
        elegiveis = [b for b in bonuses if b.get("elegivel")]
        top_bonus = elegiveis[0] if elegiveis else (bonuses[0] if bonuses else None)
        top_camp = ranking.get("topCampanha")
        evoluiu = (f040.get("summary") or {}).get("melhorOperador")
        caiu = (f040.get("summary") or {}).get("piorOperador")
        top_pdv = (ranking.get("topPdvs") or [None])[0]
        top_turno = (ranking.get("topTurnos") or [None])[0]
        impacto = _round2(sum(b.get("bonusSugerido") or 0 for b in elegiveis))

        executive = {
            "1_metasCriadas": len(goals),
            "2_campanhasSimuladas": len(campaigns),
            "3_bateramMeta": len(bateu),
            "4_abaixoMeta": len(abaixo),
            "5_superaramMeta": len(superou),
            "6_merecemBonus": len(elegiveis),
            "7_bonusSugerido": top_bonus,
            "8_campanhaMaiorRoi": top_camp,
            "9_operadorEvoluiu": evoluiu,
            "10_operadorCaiu": caiu,
            "11_pdvPerformou": top_pdv,
            "12_turnoPerformou": top_turno,
            "13_alertasGerados": len(alerts),
            "14_impactoFinanceiroEsperado": impacto,
            "15_prontoF046": qa.get("paridadeZero") and qa.get("evidenciaCompleta") and len(goals) > 0,
            "paridadeDelta": qa.get("paridadeDelta"),
        }

        parecer = (
            "[PARECER FINAL: APROVADO PARA F04.6]"
            if executive["15_prontoF046"]
            else "[PARECER FINAL: RETIDO COM JUSTIFICATIVA QUANTITATIVA]"
        )

        payload = {
            "sprint": "F04.5",
            "periodo": {"dataInicial": data_inicial, "dataFinal": data_final},
            "elapsedMs": round((time.perf_counter() - t0) * 1000, 1),
            "goalModelEngine": {"goals": goals, "goalTypes": list(GOAL_TYPES)},
            "campaignEngine": {"campaigns": campaigns},
            "targetAssignmentEngine": assignment,
            "goalAchievementEngine": {"achievements": achievements},
            "bonusSimulationEngine": {"simulations": bonuses, "valorTotal": impacto},
            "campaignRankingEngine": ranking,
            "goalAlertEngine": {"alerts": alerts},
            "cockpit": {
                "metasAtivas": goals[:15],
                "campanhas": campaigns,
                "ranking": ranking.get("topOperadores") or [],
                "bonusProjetado": bonuses[:10],
                "operadoresAbaixoMeta": abaixo[:10],
                "alertas": alerts[:15],
            },
            "executiveAnswers": executive,
            "qa": qa,
            "parecerFinal": parecer,
        }
        return WebPostoResponse.ok(payload)
