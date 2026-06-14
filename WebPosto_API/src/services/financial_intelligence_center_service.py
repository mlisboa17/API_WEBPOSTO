"""F08.4 — Financial Intelligence Center (orquestra engines IA-1..IA-6)."""
from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from src.services.cash_flow_intelligence_service import get_cash_flow_intelligence
from src.services.financial_commitments_intelligence import get_financial_commitments_intelligence
from src.services.financial_intelligence_evidence import classify_executive_score, get_financial_intelligence_evidence
from src.services.financial_opportunity_service import get_financial_opportunity_service
from src.services.financial_risk_intelligence_service import get_financial_risk_intelligence
from src.services.financial_trend_intelligence_service import get_financial_trend_intelligence

RISK_SCORE = {"BAIXO": 95, "MODERADO": 70, "ALTO": 45, "CRÍTICO": 20}


def _score_liquidity(metrics) -> float:
    if metrics.recebimentos <= 0:
        return 40.0 if metrics.pagamentos <= 0 else 25.0
    ratio = float(metrics.recebimentos / max(metrics.pagamentos, metrics.recebimentos))
    return min(100.0, max(20.0, ratio * 100))


def _score_fluxo(cash_flow: dict[str, Any]) -> float:
    if cash_flow.get("fluxoSaudavel") and not cash_flow.get("fluxoDeteriorando"):
        return 95.0
    if cash_flow.get("fluxoSaudavel"):
        return 75.0
    if cash_flow.get("fluxoDeteriorando"):
        return 45.0
    return 30.0


def _score_receivables(commitments: dict[str, Any]) -> float:
    rec = commitments.get("receivables") or {}
    health = rec.get("health")
    if health == "SAUDÁVEL":
        return 90.0
    if health == "CONCENTRADO":
        return 55.0
    return 65.0


def _score_expenses(trends: dict[str, Any]) -> float:
    horizon = (trends.get("horizons") or {}).get("7d") or {}
    despesas = horizon.get("despesas") or {}
    cls = despesas.get("classification")
    if cls == "QUEDA":
        return 95.0
    if cls == "ESTABILIDADE":
        return 80.0
    if cls == "CRESCIMENTO":
        return 55.0
    return 70.0


def _score_risks(risk: dict[str, Any]) -> float:
    return float(RISK_SCORE.get(str(risk.get("overallLevel")), 70))


def _compute_executive_financial_score(
    *,
    liquidity: float,
    fluxo: float,
    receivables: float,
    despesas: float,
    risks: float,
) -> dict[str, Any]:
    components = {
        "liquidity": round(liquidity * 0.25, 1),
        "fluxo": round(fluxo * 0.25, 1),
        "receivables": round(receivables * 0.20, 1),
        "despesas": round(despesas * 0.15, 1),
        "risks": round(risks * 0.15, 1),
    }
    total = round(sum(components.values()), 1)
    return {
        "score": total,
        "classification": classify_executive_score(total),
        "components": components,
        "weights": {"liquidity": 25, "fluxo": 25, "receivables": 20, "despesas": 15, "risks": 15},
    }


class FinancialIntelligenceCenterService:
    def __init__(self) -> None:
        self._evidence = get_financial_intelligence_evidence()
        self._trends = get_financial_trend_intelligence()
        self._risk = get_financial_risk_intelligence()
        self._opportunity = get_financial_opportunity_service()
        self._cash_flow = get_cash_flow_intelligence()
        self._commitments = get_financial_commitments_intelligence()

    def _collect(
        self,
        data_inicial: str | None = None,
        data_final: str | None = None,
        empresa_codigo: str | int | None = None,
    ) -> dict[str, Any]:
        trends = self._trends.analyze(data_inicial, data_final, empresa_codigo)
        risk = self._risk.detect(data_inicial, data_final, empresa_codigo)
        opportunities = self._opportunity.identify(data_inicial, data_final, empresa_codigo)
        cash_flow = self._cash_flow.analyze(data_inicial, data_final, empresa_codigo)
        commitments = self._commitments.analyze(data_inicial, data_final, empresa_codigo)

        start = trends["period"]["dataInicial"]
        end = trends["period"]["dataFinal"]
        evidence = self._evidence.load_period(start, end, empresa_codigo)
        metrics = self._evidence.compute_metrics(evidence)

        executive_score = _compute_executive_financial_score(
            liquidity=_score_liquidity(metrics),
            fluxo=_score_fluxo(cash_flow),
            receivables=_score_receivables(commitments),
            despesas=_score_expenses(trends),
            risks=_score_risks(risk),
        )

        top_risk = next((r for r in risk.get("risks") or [] if r.get("code") != "NO_MATERIAL_RISK"), risk["risks"][0])
        top_opportunity = (opportunities.get("opportunities") or [None])[0]

        cards = [
            {
                "id": "financial_score",
                "label": "Score Financeiro",
                "value": executive_score["score"],
                "detail": executive_score["classification"],
            },
            {
                "id": "overall_trend",
                "label": "Tendência",
                "value": trends.get("overallTrend"),
                "detail": f"{trends.get('snapshotsAvailable', 0)} snapshots",
            },
            {
                "id": "risk_level",
                "label": "Risco Geral",
                "value": risk.get("overallLevel"),
                "detail": top_risk.get("title"),
            },
            {
                "id": "cash_flow",
                "label": "Fluxo de Caixa",
                "value": cash_flow.get("cashFlowHealth"),
                "detail": f"R$ {cash_flow.get('currentFluxo', 0):,.2f}",
            },
            {
                "id": "opportunities",
                "label": "Oportunidades",
                "value": opportunities.get("opportunityCount", 0),
                "detail": top_opportunity.get("title") if top_opportunity else "—",
            },
            {
                "id": "commitments",
                "label": "Recebíveis/Pagáveis",
                "value": commitments["receivables"]["health"],
                "detail": f"Pagáveis: {commitments['payables']['health']}",
            },
        ]

        return {
            "generatedAt": datetime.now().isoformat(timespec="seconds"),
            "period": trends["period"],
            "empresaCodigo": empresa_codigo,
            "executiveFinancialScore": executive_score,
            "executiveCards": cards[:6],
            "trends": trends,
            "risks": risk,
            "opportunities": opportunities,
            "cashFlow": cash_flow,
            "commitments": commitments,
            "answers": {
                "receitaCrescendo": (trends["horizons"].get("7d") or {}).get("receitas", {}).get("classification") == "CRESCIMENTO",
                "despesaCrescendo": (trends["horizons"].get("7d") or {}).get("despesas", {}).get("classification") == "CRESCIMENTO",
                "fluxoSaudavel": cash_flow.get("fluxoSaudavel"),
                "principalRisco": top_risk.get("title"),
                "principalOportunidade": top_opportunity.get("title") if top_opportunity else None,
                "liquidezAdequada": _score_liquidity(metrics) >= 70,
                "recebiveisSaudaveis": commitments["receivables"]["health"] == "SAUDÁVEL",
                "pagamentosSaudaveis": commitments["payables"]["health"] == "SAUDÁVEL",
                "tendenciaFinanceira": trends.get("overallTrend"),
                "scoreFinanceiro": executive_score["score"],
                "deterioracao": cash_flow.get("fluxoDeteriorando") or risk.get("overallLevel") in {"ALTO", "CRÍTICO"},
                "concentracao": commitments.get("concentrationRelevant"),
                "inadimplenciaRelevante": commitments.get("delinquencyRelevant"),
                "oportunidadeImediata": bool(opportunities.get("opportunityCount")),
            },
            "snapshotFirst": True,
            "generativeAi": False,
        }

    def get_cockpit(
        self,
        data_inicial: str | None = None,
        data_final: str | None = None,
        empresa_codigo: str | int | None = None,
    ) -> dict[str, Any]:
        return self._collect(data_inicial, data_final, empresa_codigo)

    def get_trends(self, data_inicial: str | None = None, data_final: str | None = None, empresa_codigo: str | int | None = None) -> dict[str, Any]:
        return self._trends.analyze(data_inicial, data_final, empresa_codigo)

    def get_risks(self, data_inicial: str | None = None, data_final: str | None = None, empresa_codigo: str | int | None = None) -> dict[str, Any]:
        return self._risk.detect(data_inicial, data_final, empresa_codigo)

    def get_opportunities(self, data_inicial: str | None = None, data_final: str | None = None, empresa_codigo: str | int | None = None) -> dict[str, Any]:
        return self._opportunity.identify(data_inicial, data_final, empresa_codigo)

    def dw_row(
        self,
        data_inicial: str | None = None,
        data_final: str | None = None,
        empresa_codigo: str | int | None = None,
    ) -> dict[str, Any]:
        data = self._collect(data_inicial, data_final, empresa_codigo)
        return {
            "execution_id": str(uuid.uuid4()),
            "generated_at": data["generatedAt"],
            "empresa_codigo": empresa_codigo,
            "financial_score": data["executiveFinancialScore"]["score"],
            "risk_level": data["risks"]["overallLevel"],
            "trend": data["trends"]["overallTrend"],
            "opportunity_count": data["opportunities"]["opportunityCount"],
            "cash_flow_health": data["cashFlow"]["cashFlowHealth"],
            "period_start": data["period"]["dataInicial"],
            "period_end": data["period"]["dataFinal"],
            "lineage": True,
            "source": "financial_intelligence_center",
        }


_center: FinancialIntelligenceCenterService | None = None


def get_financial_intelligence_center() -> FinancialIntelligenceCenterService:
    global _center
    if _center is None:
        _center = FinancialIntelligenceCenterService()
    return _center
