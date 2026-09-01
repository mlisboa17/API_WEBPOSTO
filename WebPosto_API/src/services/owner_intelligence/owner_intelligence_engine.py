"""
Owner Intelligence Engine — Core Orchestrator

The heart of the LOGOS Owner Action Center.

Orchestrates:
- MoneyAtRiskEngine (Motor 1)
- RecoverableMoneyEngine (Motor 2)
- GrowthOpportunitiesEngine (Motor 3)
- DailyActionsEngine (Motor 4)

Produces the OwnerActionCenterSummary with:
- Business health metrics
- Money at risk findings
- Recoverable money findings
- Growth opportunities
- Top 5 daily decisions

Principle: Deliver decisions, not data.
"""

import logging
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, List
from dataclasses import dataclass

from src.services.decision_execution.preference_model import (
    PreferenceModelService,
    PreferenceWeightResult,
)

from .schemas import (
    OwnerActionCenterSummary,
    BusinessHealthMetrics,
    MoneyAtRiskFinding,
    RecoverableMoneyFinding,
    GrowthOpportunity,
    BaselineConfig,
    RiskThresholds,
)
from .money_at_risk import MoneyAtRiskEngine
from .recoverable_money import RecoverableMoneyEngine
from .growth_opportunities import GrowthOpportunitiesEngine
from .daily_actions import DailyActionsEngine

logger = logging.getLogger(__name__)


@dataclass
class EngineDataSources:
    """Data sources for all engines."""

    financial_overview: Dict[str, Any]
    accounts_receivable: Dict[str, Any]
    accounts_payable: Dict[str, Any]
    sales_data: Dict[str, Any]
    product_data: Dict[str, Any]
    payment_data: Dict[str, Any]
    card_data: Dict[str, Any]
    expense_data: Dict[str, Any]
    historical_data: Optional[Dict[str, Any]] = None


class OwnerIntelligenceEngine:
    """
    Core orchestrator for the Owner Action Center.

    Coordinates all four motors to produce a complete
    Owner Action Center summary for the business owner.
    """

    def __init__(
        self,
        money_at_risk_engine: Optional[MoneyAtRiskEngine] = None,
        recoverable_money_engine: Optional[RecoverableMoneyEngine] = None,
        growth_opportunities_engine: Optional[GrowthOpportunitiesEngine] = None,
        daily_actions_engine: Optional[DailyActionsEngine] = None,
        baseline_config: Optional[BaselineConfig] = None,
        risk_thresholds: Optional[RiskThresholds] = None,
    ):
        # Initialize or use provided engines
        self.money_at_risk_engine = money_at_risk_engine or MoneyAtRiskEngine(
            baseline_config=baseline_config, thresholds=risk_thresholds
        )
        self.recoverable_money_engine = recoverable_money_engine or RecoverableMoneyEngine()
        self.growth_opportunities_engine = (
            growth_opportunities_engine or GrowthOpportunitiesEngine()
        )
        self.daily_actions_engine = daily_actions_engine or DailyActionsEngine()
        self.preference_model_service = PreferenceModelService()

        # Configuration
        self.baseline_config = baseline_config or BaselineConfig()
        self.risk_thresholds = risk_thresholds or RiskThresholds()

    async def generate_action_center_summary(
        self,
        tenant_id: str,
        empresa_codigo: str,
        data_sources: EngineDataSources,
        period_days: int = 30,
    ) -> OwnerActionCenterSummary:
        """
        Generate complete Owner Action Center summary.

        Args:
            tenant_id: Tenant identifier
            empresa_codigo: WebPosto company code
            data_sources: Data from various services
            period_days: Analysis period in days

        Returns:
            Complete OwnerActionCenterSummary
        """
        start_time = datetime.utcnow()

        try:
            logger.info(
                f"OwnerIntelligenceEngine: Generating summary for "
                f"tenant {tenant_id}, empresa {empresa_codigo}"
            )

            # Calculate period dates
            period_end = datetime.utcnow()
            period_start = period_end - timedelta(days=period_days)

            # 1. Run Motor 1: Money At Risk
            logger.debug("Running MoneyAtRiskEngine...")
            money_at_risk = await self.money_at_risk_engine.analyze(
                tenant_id=tenant_id,
                empresa_codigo=empresa_codigo,
                financial_data=data_sources.financial_overview,
                historical_data=data_sources.historical_data,
            )

            # 2. Run Motor 2: Recoverable Money
            logger.debug("Running RecoverableMoneyEngine...")
            recoverable_money = await self.recoverable_money_engine.analyze(
                tenant_id=tenant_id,
                empresa_codigo=empresa_codigo,
                receivables_data=data_sources.accounts_receivable,
                sales_data=data_sources.sales_data,
                card_data=data_sources.card_data,
                expense_data=data_sources.expense_data,
            )

            # 3. Run Motor 3: Growth Opportunities
            logger.debug("Running GrowthOpportunitiesEngine...")
            opportunities = await self.growth_opportunities_engine.analyze(
                tenant_id=tenant_id,
                empresa_codigo=empresa_codigo,
                sales_data=data_sources.sales_data,
                product_data=data_sources.product_data,
                payment_data=data_sources.payment_data,
                historical_data=data_sources.historical_data,
            )

            # 4. Calculate Business Health
            logger.debug("Calculating business health...")
            business_health = self._calculate_business_health(
                money_at_risk, recoverable_money, opportunities, data_sources.financial_overview
            )

            # 5. Run Motor 4: Generate Daily Decisions
            logger.debug("Running DailyActionsEngine...")
            execution_feedback, execution_feedback_stats = self._load_execution_feedback()
            top_5_decisions, all_decisions = await self.daily_actions_engine.generate_decisions(
                tenant_id=tenant_id,
                empresa_codigo=empresa_codigo,
                money_at_risk=money_at_risk,
                recoverable_money=recoverable_money,
                opportunities=opportunities,
                max_decisions=5,
                execution_feedback=execution_feedback,
                execution_feedback_stats=execution_feedback_stats,
            )

            # 6. Calculate totals
            money_at_risk_total = sum(f.amount_at_risk * f.probability for f in money_at_risk)
            recoverable_total = sum(
                r.recoverable_amount * r.recovery_probability for r in recoverable_money
            )
            opportunity_total = sum(o.potential_profit for o in opportunities)

            # 7. Calculate confidence average
            all_confidences = (
                [f.confidence for f in money_at_risk]
                + [r.confidence for r in recoverable_money]
                + [o.confidence for o in opportunities]
            )
            confidence_average = (
                sum(all_confidences) / len(all_confidences) if all_confidences else 0
            )

            # 8. Count actions by priority
            critical_actions = sum(
                1 for d in all_decisions if d.action.priority.value == "critical"
            )
            high_actions = sum(1 for d in all_decisions if d.action.priority.value == "high")
            immediate_attention = sum(1 for d in top_5_decisions if d.urgency_score >= 80)

            # 9. Apply preference model weights to the top 5 decisions
            preference_audit: List[Dict[str, Any]] = []
            if top_5_decisions:
                top_5_decisions, weight_results = (
                    self.preference_model_service.apply_preference_weights(
                        top_5_decisions, tenant_id=tenant_id, empresa_codigo=empresa_codigo
                    )
                )
                preference_audit = [self._audit_to_dict(r) for r in weight_results]

            # 10. Generate executive summary
            executive_summary = self.daily_actions_engine.get_executive_summary(
                top_5_decisions, tenant_id
            )

            # 10. Generate greeting
            greeting = self._generate_greeting(business_health)

            # 11. Track data sources used
            data_sources_used = self._track_data_sources(data_sources)

            # Create summary
            summary = OwnerActionCenterSummary(
                tenant_id=tenant_id,
                empresa_codigo=empresa_codigo,
                generated_at=datetime.utcnow(),
                data_period_start=period_start,
                data_period_end=period_end,
                business_health=business_health,
                money_at_risk=money_at_risk,
                money_at_risk_total=money_at_risk_total,
                recoverable_money=recoverable_money,
                recoverable_total=recoverable_total,
                opportunities=opportunities,
                opportunity_total=opportunity_total,
                top_5_decisions=top_5_decisions,
                all_decisions=all_decisions,
                executive_summary=executive_summary,
                greeting=greeting,
                total_actions=len(all_decisions),
                critical_actions=critical_actions,
                high_actions=high_actions,
                actions_requiring_immediate_attention=immediate_attention,
                confidence_average=confidence_average,
                data_sources=data_sources_used,
                preference_audit=preference_audit,
            )

            elapsed = (datetime.utcnow() - start_time).total_seconds()
            logger.info(
                f"OwnerIntelligenceEngine: Summary generated in {elapsed:.2f}s. "
                f"Found {len(money_at_risk)} risks, {len(recoverable_money)} recoveries, "
                f"{len(opportunities)} opportunities. Top 5 decisions generated."
            )

            return summary

        except Exception as e:
            logger.error(f"Error generating action center summary: {e}")
            # Return empty summary on error
            return self._create_empty_summary(tenant_id, empresa_codigo)

    @staticmethod
    def _load_execution_feedback():
        """
        EXEC-03 — load the owner's confirmed execution history (SIM/PARCIAL/NÃO)
        and precompute the per-category dampening signal for the priority engine.

        Fails soft: if the execution store is unavailable for any reason, the
        engine falls back to no dampening (behaves exactly as before EXEC-03).
        """
        try:
            from src.services.decision_execution import (
                ExecutionFeedbackService,
                ExecutionRecordStore,
            )

            feedback = ExecutionFeedbackService()
            store = ExecutionRecordStore()
            stats = feedback.compute_stats(store.list_all())
            return feedback, stats
        except Exception as e:
            logger.warning(f"ExecutionFeedbackService unavailable, skipping EXEC-03 dampening: {e}")
            return None, {}

    def _calculate_business_health(
        self,
        money_at_risk: List[MoneyAtRiskFinding],
        recoverable_money: List[RecoverableMoneyFinding],
        opportunities: List[GrowthOpportunity],
        financial_overview: Dict[str, Any],
    ) -> BusinessHealthMetrics:
        """Calculate overall business health metrics."""

        try:
            # Base score starts at 70 (neutral)
            base_score = 70.0

            # Adjust for money at risk (penalty)
            total_risk = sum(f.amount_at_risk * f.probability for f in money_at_risk)
            revenue = financial_overview.get("total_revenue", 1)  # Avoid div by zero
            risk_penalty = min(30, (total_risk / revenue) * 100 * 10) if revenue > 0 else 0

            # Adjust for recoverable money (bonus for having recovery opportunities)
            total_recoverable = sum(
                r.recoverable_amount * r.recovery_probability for r in recoverable_money
            )
            recovery_bonus = min(10, (total_recoverable / revenue) * 100 * 5) if revenue > 0 else 0

            # Adjust for opportunities (bonus)
            total_opportunity = sum(o.potential_profit for o in opportunities)
            opportunity_bonus = (
                min(10, (total_opportunity / revenue) * 100 * 10) if revenue > 0 else 0
            )

            # Calculate final score
            score = base_score - risk_penalty + recovery_bonus + opportunity_bonus
            score = max(0, min(100, score))  # Clamp 0-100

            # Determine status
            if score >= 85:
                status = "excellent"
            elif score >= 70:
                status = "good"
            elif score >= 50:
                status = "attention"
            else:
                status = "critical"

            # Calculate trend (simplified)
            recent_risks = sum(1 for f in money_at_risk if f.timeframe_days <= 7)
            trend = "stable"
            trend_percent = 0.0

            if recent_risks >= 3:
                trend = "declining"
                trend_percent = -5.0
            elif total_recoverable > total_risk * 0.5:
                trend = "improving"
                trend_percent = 3.0

            # Component scores
            revenue_health = max(0, min(100, 80 - risk_penalty * 2))
            expense_health = max(
                0, min(100, 80 - sum(1 for f in money_at_risk if "expense" in f.risk_type) * 10)
            )
            cash_health = max(
                0, min(100, 80 - sum(1 for f in money_at_risk if "cash" in f.risk_type) * 15)
            )
            margin_health = max(
                0, min(100, 80 - sum(1 for f in money_at_risk if "margin" in f.risk_type) * 10)
            )
            operational_health = max(0, min(100, 70 + recovery_bonus + opportunity_bonus))

            # Generate recommendations
            recommendations = []
            if money_at_risk:
                recommendations.append(
                    f"Address {len(money_at_risk)} active risks to improve health"
                )
            if recoverable_money:
                recommendations.append(
                    f"Recover R$ {total_recoverable:,.0f} in outstanding amounts"
                )
            if opportunities:
                recommendations.append(f"Explore {len(opportunities)} growth opportunities")

            return BusinessHealthMetrics(
                score=round(score, 1),
                status=status,
                trend=trend,
                trend_percent=trend_percent,
                revenue_health=round(revenue_health, 1),
                expense_health=round(expense_health, 1),
                cash_health=round(cash_health, 1),
                margin_health=round(margin_health, 1),
                operational_health=round(operational_health, 1),
                summary=self._generate_health_summary(
                    score, status, trend, money_at_risk, recoverable_money
                ),
                recommendations=recommendations[:3],  # Top 3
            )

        except Exception as e:
            logger.error(f"Error calculating business health: {e}")
            return BusinessHealthMetrics(
                score=50.0,
                status="attention",
                trend="stable",
                trend_percent=0.0,
                revenue_health=50.0,
                expense_health=50.0,
                cash_health=50.0,
                margin_health=50.0,
                operational_health=50.0,
                summary="Business health calculation incomplete. Please check data sources.",
                recommendations=["Verify data connections", "Review financial data"],
            )

    def _generate_health_summary(
        self,
        score: float,
        status: str,
        trend: str,
        money_at_risk: List[MoneyAtRiskFinding],
        recoverable_money: List[RecoverableMoneyFinding],
    ) -> str:
        """Generate human-readable health summary."""
        risk_count = len(money_at_risk)
        recovery_count = len(recoverable_money)

        if status == "excellent":
            return f"Business is performing excellently (score: {score:.0f}/100). {risk_count} risks under control. {recovery_count} recovery opportunities available."
        elif status == "good":
            return f"Business is in good shape (score: {score:.0f}/100). Monitor {risk_count} identified risks. {recovery_count} recoverable amounts pending."
        elif status == "attention":
            return f"Business requires attention (score: {score:.0f}/100). {risk_count} active risks need review. {recovery_count} amounts can be recovered."
        else:
            return f"CRITICAL: Business needs immediate attention (score: {score:.0f}/100). {risk_count} urgent risks. Address immediately."

    def _generate_greeting(self, business_health: BusinessHealthMetrics) -> str:
        """Generate personalized greeting based on health."""
        greetings = {
            "excellent": [
                "Bom dia! Seu posto está indo muito bem.",
                "Excelente dia! Performance está ótima.",
                "Bom dia! Tudo sob controle.",
            ],
            "good": [
                "Bom dia! Negócio em boa forma.",
                "Dia positivo! Algumas oportunidades para explorar.",
                "Bom dia! Performance estável com melhorias possíveis.",
            ],
            "attention": [
                "Bom dia. Atenção necessária em alguns pontos.",
                "Olá. Há itens que precisam da sua atenção hoje.",
                "Bom dia. Recomendo revisar as decisões priorizadas.",
            ],
            "critical": [
                "ATENÇÃO: Situação requer ação imediata.",
                "ALERTA: Problemas urgentes identificados.",
                "ATENÇÃO CRÍTICA: Revise as decisões urgentes agora.",
            ],
        }

        import random

        return random.choice(greetings.get(business_health.status, greetings["good"]))

    def _track_data_sources(self, data_sources: EngineDataSources) -> List[str]:
        """Track which data sources were used."""
        sources = []

        if data_sources.financial_overview:
            sources.append("financial_overview")
        if data_sources.accounts_receivable:
            sources.append("accounts_receivable")
        if data_sources.accounts_payable:
            sources.append("accounts_payable")
        if data_sources.sales_data:
            sources.append("sales_data")
        if data_sources.product_data:
            sources.append("product_data")
        if data_sources.payment_data:
            sources.append("payment_data")
        if data_sources.card_data:
            sources.append("card_data")
        if data_sources.expense_data:
            sources.append("expense_data")
        if data_sources.historical_data:
            sources.append("historical_data")

        return sources

    def _create_empty_summary(
        self, tenant_id: str, empresa_codigo: str
    ) -> OwnerActionCenterSummary:
        """Create empty summary for error cases."""
        now = datetime.utcnow()

        return OwnerActionCenterSummary(
            tenant_id=tenant_id,
            empresa_codigo=empresa_codigo,
            generated_at=now,
            data_period_start=now - timedelta(days=30),
            data_period_end=now,
            business_health=BusinessHealthMetrics(
                score=50.0,
                status="attention",
                trend="stable",
                trend_percent=0.0,
                revenue_health=50.0,
                expense_health=50.0,
                cash_health=50.0,
                margin_health=50.0,
                operational_health=50.0,
                summary="Unable to generate complete analysis. Please verify data connections.",
                recommendations=["Check data source connections", "Retry in a few minutes"],
            ),
            money_at_risk=[],
            money_at_risk_total=0,
            recoverable_money=[],
            recoverable_total=0,
            opportunities=[],
            opportunity_total=0,
            top_5_decisions=[],
            all_decisions=[],
            executive_summary="Analysis generation encountered an error. Please try again or contact support.",
            greeting="Bom dia. Sistema temporariamente indisponível.",
            total_actions=0,
            critical_actions=0,
            high_actions=0,
            actions_requiring_immediate_attention=0,
            confidence_average=0,
            data_sources=[],
            preference_audit=[],
        )

    @staticmethod
    def _audit_to_dict(result: "PreferenceWeightResult") -> Dict[str, Any]:
        """Serialize a PreferenceWeightResult for the API response."""
        return {
            "decision_id": result.decision_id,
            "category": result.category,
            "original_score": result.original_score,
            "adjusted_score": result.adjusted_score,
            "multiplier": result.multiplier,
            "reason": result.reason,
        }
