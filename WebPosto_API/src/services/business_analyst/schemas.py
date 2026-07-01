"""
Schemas para Business Analyst
Define estruturas de dados para relatórios executivos
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from typing import Any, Literal


ScoreClassification = Literal["EXCELENTE", "SAUDAVEL", "ATENCAO", "RISCO", "CRITICO"]
RiskLevel = Literal["CRITICO", "ALTO", "MEDIO", "BAIXO"]
OpportunityPotential = Literal["ALTO", "MEDIO", "BAIXO"]


@dataclass(frozen=True)
class BusinessHealthScore:
    """Score de saúde do negócio"""
    
    overall_score: float  # 0-100
    classification: ScoreClassification
    
    # Componentes do score (0-100 cada)
    revenue_score: float
    cash_flow_score: float
    inventory_score: float
    delinquency_score: float
    growth_score: float
    alerts_score: float
    divergence_score: float
    
    # Metadados
    tenant: str
    period_start: str
    period_end: str
    calculated_at: str
    
    def to_dict(self) -> dict[str, Any]:
        """Converte para dicionário"""
        return {
            "overall_score": round(self.overall_score, 2),
            "classification": self.classification,
            "components": {
                "revenue": round(self.revenue_score, 2),
                "cash_flow": round(self.cash_flow_score, 2),
                "inventory": round(self.inventory_score, 2),
                "delinquency": round(self.delinquency_score, 2),
                "growth": round(self.growth_score, 2),
                "alerts": round(self.alerts_score, 2),
                "divergence": round(self.divergence_score, 2),
            },
            "metadata": {
                "tenant": self.tenant,
                "period_start": self.period_start,
                "period_end": self.period_end,
                "calculated_at": self.calculated_at,
            },
        }


@dataclass(frozen=True)
class BusinessRisk:
    """Risco identificado"""
    
    risk_id: str
    title: str
    description: str
    level: RiskLevel
    impact: str  # Descrição do impacto
    recommended_action: str
    detected_at: str
    
    def to_dict(self) -> dict[str, Any]:
        """Converte para dicionário"""
        return {
            "risk_id": self.risk_id,
            "title": self.title,
            "description": self.description,
            "level": self.level,
            "impact": self.impact,
            "recommended_action": self.recommended_action,
            "detected_at": self.detected_at,
        }


@dataclass(frozen=True)
class BusinessOpportunity:
    """Oportunidade identificada"""
    
    opportunity_id: str
    title: str
    description: str
    potential: OpportunityPotential
    estimated_impact: str  # Ex: "R$ 5.000/mês"
    recommended_action: str
    detected_at: str
    
    def to_dict(self) -> dict[str, Any]:
        """Converte para dicionário"""
        return {
            "opportunity_id": self.opportunity_id,
            "title": self.title,
            "description": self.description,
            "potential": self.potential,
            "estimated_impact": self.estimated_impact,
            "recommended_action": self.recommended_action,
            "detected_at": self.detected_at,
        }


@dataclass(frozen=True)
class RecommendedAction:
    """Ação recomendada"""
    
    action_id: str
    title: str
    description: str
    priority: Literal["CRITICA", "ALTA", "MEDIA", "BAIXA"]
    category: str  # Ex: "FINANCEIRO", "OPERACIONAL", "COMERCIAL"
    estimated_effort: str  # Ex: "5 minutos", "1 hora"
    expected_result: str
    
    def to_dict(self) -> dict[str, Any]:
        """Converte para dicionário"""
        return {
            "action_id": self.action_id,
            "title": self.title,
            "description": self.description,
            "priority": self.priority,
            "category": self.category,
            "estimated_effort": self.estimated_effort,
            "expected_result": self.expected_result,
        }


@dataclass(frozen=True)
class DailyExecutiveReport:
    """Relatório executivo diário"""
    
    tenant: str
    period: str
    generated_at: str
    
    health_score: BusinessHealthScore
    summary: str  # Resumo executivo em texto
    
    # Dados financeiros
    revenue_today: Decimal
    revenue_vs_yesterday: Decimal
    expenses_today: Decimal
    cash_flow_today: Decimal
    
    # Alertas
    critical_alerts: list[dict[str, Any]]
    
    # Análise
    risks: list[BusinessRisk]
    opportunities: list[BusinessOpportunity]
    recommended_actions: list[RecommendedAction]
    
    def to_dict(self) -> dict[str, Any]:
        """Converte para dicionário"""
        return {
            "success": True,
            "tenant": self.tenant,
            "period": self.period,
            "generated_at": self.generated_at,
            "health_score": self.health_score.to_dict(),
            "summary": self.summary,
            "financial": {
                "revenue_today": str(self.revenue_today),
                "revenue_vs_yesterday": str(self.revenue_vs_yesterday),
                "expenses_today": str(self.expenses_today),
                "cash_flow_today": str(self.cash_flow_today),
            },
            "critical_alerts": self.critical_alerts,
            "risks": [r.to_dict() for r in self.risks],
            "opportunities": [o.to_dict() for o in self.opportunities],
            "recommended_actions": [a.to_dict() for a in self.recommended_actions],
        }


@dataclass(frozen=True)
class WeeklyExecutiveReport:
    """Relatório executivo semanal"""
    
    tenant: str
    period_start: str
    period_end: str
    generated_at: str
    
    health_score: BusinessHealthScore
    summary: str
    
    # Comparações
    improvements: list[str]  # O que melhorou
    deteriorations: list[str]  # O que piorou
    
    # Dados semanais
    revenue_week: Decimal
    revenue_vs_last_week: Decimal
    expenses_week: Decimal
    
    # Análise
    risks_week: list[BusinessRisk]
    opportunities_week: list[BusinessOpportunity]
    recommended_actions: list[RecommendedAction]
    
    # Previsão
    forecast_next_week: dict[str, Any]
    
    def to_dict(self) -> dict[str, Any]:
        """Converte para dicionário"""
        return {
            "success": True,
            "tenant": self.tenant,
            "period_start": self.period_start,
            "period_end": self.period_end,
            "generated_at": self.generated_at,
            "health_score": self.health_score.to_dict(),
            "summary": self.summary,
            "trends": {
                "improvements": self.improvements,
                "deteriorations": self.deteriorations,
            },
            "financial": {
                "revenue_week": str(self.revenue_week),
                "revenue_vs_last_week": str(self.revenue_vs_last_week),
                "expenses_week": str(self.expenses_week),
            },
            "risks": [r.to_dict() for r in self.risks_week],
            "opportunities": [o.to_dict() for o in self.opportunities_week],
            "recommended_actions": [a.to_dict() for a in self.recommended_actions],
            "forecast_next_week": self.forecast_next_week,
        }


@dataclass(frozen=True)
class ReportPayloads:
    """Payloads formatados para diferentes canais"""
    
    telegram_markdown: str
    discord_embed: dict[str, Any]
    email_html: str
    
    def to_dict(self) -> dict[str, Any]:
        """Converte para dicionário"""
        return {
            "success": True,
            "payloads": {
                "telegram": {
                    "format": "markdown",
                    "content": self.telegram_markdown,
                },
                "discord": {
                    "format": "embed",
                    "content": self.discord_embed,
                },
                "email": {
                    "format": "html",
                    "content": self.email_html,
                },
            },
        }
