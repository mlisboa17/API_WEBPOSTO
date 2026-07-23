"""
Motor 4 — Daily Actions Engine

Generates the Top 5 daily decisions by combining:
- Money at Risk findings
- Recoverable Money findings
- Growth Opportunities

Each decision must answer:
- Why did it appear?
- Why is it ranked here?
- How much money is involved?
- What should I do?
- How long will it take?
- What's the confidence?
"""

import logging
from datetime import datetime, timedelta
from typing import List, Optional, Dict, Any, Tuple, TYPE_CHECKING
from dataclasses import dataclass

from .schemas import (
    DailyDecision, DecisionAction, MoneyAtRiskFinding, 
    RecoverableMoneyFinding, GrowthOpportunity,
    ActionPriority, ActionType, ConfidenceLevel
)
from .priority_engine import PriorityEngine

if TYPE_CHECKING:
    from src.services.decision_execution.feedback import ExecutionFeedbackService

logger = logging.getLogger(__name__)


@dataclass
class RawDecisionCandidate:
    """Internal class to hold decision candidates before processing."""
    source_type: str  # "risk", "recovery", "opportunity"
    source_finding: Any  # MoneyAtRiskFinding, RecoverableMoneyFinding, or GrowthOpportunity
    action: DecisionAction
    financial_value: float
    urgency_score: float
    confidence_score: float


class DailyActionsEngine:
    """
    Engine to generate daily prioritized decisions.
    
    Combines findings from all three motors into actionable,
    prioritized decisions for the owner.
    """
    
    def __init__(self, priority_engine: Optional[PriorityEngine] = None):
        self.priority_engine = priority_engine or PriorityEngine()
        self.decisions: List[DailyDecision] = []
        
    async def generate_decisions(
        self,
        tenant_id: str,
        empresa_codigo: str,
        money_at_risk: List[MoneyAtRiskFinding],
        recoverable_money: List[RecoverableMoneyFinding],
        opportunities: List[GrowthOpportunity],
        max_decisions: int = 5,
        execution_feedback: Optional["ExecutionFeedbackService"] = None,
        execution_feedback_stats: Optional[Dict[str, Dict[str, int]]] = None,
    ) -> Tuple[List[DailyDecision], List[DailyDecision]]:
        """
        Generate prioritized daily decisions.
        
        Args:
            tenant_id: Tenant identifier
            empresa_codigo: WebPosto company code
            money_at_risk: Findings from MoneyAtRiskEngine
            recoverable_money: Findings from RecoverableMoneyEngine
            opportunities: Findings from GrowthOpportunitiesEngine
            max_decisions: Maximum number of top decisions to return
            execution_feedback: EXEC-03 — optional feedback service used to
                dampen categories the owner has repeatedly rejected as
                not-a-priority/already-resolved.
            execution_feedback_stats: Precomputed stats for execution_feedback
                (see ExecutionFeedbackService.compute_stats).
            
        Returns:
            Tuple of (top_decisions, all_decisions)
        """
        self.decisions = []
        candidates: List[RawDecisionCandidate] = []
        
        try:
            # Convert all findings to decision candidates
            for finding in money_at_risk:
                candidate = self._convert_risk_to_candidate(finding)
                if candidate:
                    candidates.append(candidate)
            
            for finding in recoverable_money:
                candidate = self._convert_recovery_to_candidate(finding)
                if candidate:
                    candidates.append(candidate)
            
            for opportunity in opportunities:
                candidate = self._convert_opportunity_to_candidate(opportunity)
                if candidate:
                    candidates.append(candidate)
            
            logger.info(
                f"DailyActionsEngine: Processing {len(candidates)} candidates "
                f"for tenant {tenant_id}"
            )
            
            # Calculate priority scores for all candidates
            scored_candidates = []
            for candidate in candidates:
                dampening = 1.0
                if execution_feedback is not None:
                    dampening = execution_feedback.dampening_for_text(
                        self._category_text(candidate), execution_feedback_stats or {}
                    )

                scores = self.priority_engine.calculate_score(
                    financial_value=candidate.financial_value,
                    urgency_score=candidate.urgency_score,
                    confidence=candidate.confidence_score,
                    action_type=candidate.action.type,
                    priority=candidate.action.priority,
                    time_to_resolve=candidate.action.time_to_resolve,
                    dampening_multiplier=dampening,
                )
                
                scored_candidates.append((candidate, scores))
            
            # Sort by total score (descending)
            scored_candidates.sort(key=lambda x: x[1]["total_score"], reverse=True)
            
            # Create DailyDecision objects
            rank = 1
            for candidate, scores in scored_candidates:
                decision = self._create_daily_decision(
                    rank=rank,
                    candidate=candidate,
                    scores=scores,
                    tenant_id=tenant_id,
                    empresa_codigo=empresa_codigo
                )
                
                self.decisions.append(decision)
                rank += 1
            
            # Filter high confidence only for top decisions
            top_decisions = [
                d for d in self.decisions[:max_decisions]
                if d.confidence_score >= 0.60  # Minimum 60% confidence
            ]
            
            # If we filtered out too many, add more until we have max_decisions
            while len(top_decisions) < min(max_decisions, len(self.decisions)):
                idx = len(top_decisions)
                if idx < len(self.decisions):
                    top_decisions.append(self.decisions[idx])
                else:
                    break
            
            logger.info(
                f"DailyActionsEngine: Generated {len(top_decisions)} top decisions "
                f"from {len(self.decisions)} total"
            )
            
            return top_decisions, self.decisions
            
        except Exception as e:
            logger.error(f"Error in DailyActionsEngine.generate_decisions: {e}")
            return [], []

    @staticmethod
    def _category_text(candidate: RawDecisionCandidate) -> Optional[str]:
        """
        Extract the category/type string used to bridge a candidate with the
        EXEC-03 execution feedback signal (risk_type/recovery_type/opportunity_type).
        """
        finding = candidate.source_finding
        return (
            getattr(finding, "risk_type", None)
            or getattr(finding, "recovery_type", None)
            or getattr(finding, "opportunity_type", None)
        )

    def _convert_risk_to_candidate(
        self,
        finding: MoneyAtRiskFinding
    ) -> Optional[RawDecisionCandidate]:
        """Convert a MoneyAtRisk finding to a decision candidate."""
        try:
            # Calculate expected value
            expected_value = finding.amount_at_risk * finding.probability
            
            # Map risk type to urgency
            urgency_map = {
                "revenue_decline": 0.9,
                "expense_increase": 0.7,
                "cash_shortage": 1.0,
                "margin_compression": 0.8,
                "voucher_anomaly": 0.5,
                "overdue_receivables": 0.8,
                "card_reconciliation": 0.7,
            }
            urgency = urgency_map.get(finding.risk_type, 0.6)
            
            return RawDecisionCandidate(
                source_type="risk",
                source_finding=finding,
                action=finding.action,
                financial_value=expected_value,
                urgency_score=urgency,
                confidence_score=finding.confidence
            )
            
        except Exception as e:
            logger.warning(f"Error converting risk finding: {e}")
            return None
    
    def _convert_recovery_to_candidate(
        self,
        finding: RecoverableMoneyFinding
    ) -> Optional[RawDecisionCandidate]:
        """Convert a RecoverableMoney finding to a decision candidate."""
        try:
            # Calculate expected recoverable value
            expected_value = finding.recoverable_amount * finding.recovery_probability
            
            # Recovery is generally less urgent than risk
            # But urgency increases with age
            base_urgency = 0.7
            if finding.oldest_overdue_days:
                if finding.oldest_overdue_days > 60:
                    base_urgency = 0.95
                elif finding.oldest_overdue_days > 30:
                    base_urgency = 0.85
                elif finding.oldest_overdue_days > 14:
                    base_urgency = 0.75
            
            return RawDecisionCandidate(
                source_type="recovery",
                source_finding=finding,
                action=finding.action,
                financial_value=expected_value,
                urgency_score=base_urgency,
                confidence_score=finding.confidence
            )
            
        except Exception as e:
            logger.warning(f"Error converting recovery finding: {e}")
            return None
    
    def _convert_opportunity_to_candidate(
        self,
        opportunity: GrowthOpportunity
    ) -> Optional[RawDecisionCandidate]:
        """Convert a GrowthOpportunity to a decision candidate."""
        try:
            # Use potential profit as financial value
            expected_value = opportunity.potential_profit * opportunity.trend_strength
            
            # Opportunities are generally lower urgency than risks
            # But trending products get higher urgency
            base_urgency = 0.5
            if opportunity.trend_direction == "up":
                base_urgency = 0.6 + (opportunity.trend_strength * 0.2)
            
            return RawDecisionCandidate(
                source_type="opportunity",
                source_finding=opportunity,
                action=opportunity.action,
                financial_value=expected_value,
                urgency_score=base_urgency,
                confidence_score=opportunity.confidence
            )
            
        except Exception as e:
            logger.warning(f"Error converting opportunity: {e}")
            return None
    
    def _create_daily_decision(
        self,
        rank: int,
        candidate: RawDecisionCandidate,
        scores: Dict[str, float],
        tenant_id: str,
        empresa_codigo: str
    ) -> DailyDecision:
        """Create a DailyDecision from a scored candidate."""
        
        # Generate the "why" explanations
        why_appeared = self._generate_why_appeared(candidate)
        why_ranked = self._generate_why_ranked(candidate, scores, rank)
        money_involved = self._generate_money_involved(candidate)
        what_rule = self._generate_what_rule(candidate)
        
        # Determine decision type
        decision_type_map = {
            "risk": "risk",
            "recovery": "recovery",
            "opportunity": "opportunity"
        }
        decision_type = decision_type_map.get(candidate.source_type, "other")
        
        # Generate decision question
        decision_question = self._generate_decision_question(candidate)
        
        return DailyDecision(
            id=f"dec_{tenant_id}_{rank}_{datetime.utcnow().strftime('%Y%m%d')}",
            rank=rank,
            title=candidate.action.title,
            description=candidate.action.description,
            decision_question=decision_question,
            why_appeared=why_appeared,
            why_ranked=why_ranked,
            money_involved=money_involved,
            what_rule_triggered=what_rule,
            total_score=scores["total_score"],
            financial_impact_score=scores["financial_impact_score"],
            urgency_score=scores["urgency_score"],
            confidence_score=scores["confidence_score"],
            ease_score=scores["ease_score"],
            time_score=scores["time_score"],
            action=candidate.action,
            decision_type=decision_type,
            related_findings=[candidate.source_finding.id]
        )
    
    def _generate_why_appeared(self, candidate: RawDecisionCandidate) -> str:
        """Generate explanation of why this decision appeared."""
        if candidate.source_type == "risk":
            finding = candidate.source_finding
            return (
                f"Detected {finding.risk_type.replace('_', ' ')} with "
                f"R$ {finding.amount_at_risk:,.2f} at risk. "
                f"Current value is {abs(finding.deviation_percent):.1f}% "
                f"{'above' if finding.deviation_percent > 0 else 'below'} baseline."
            )
        elif candidate.source_type == "recovery":
            finding = candidate.source_finding
            return (
                f"Found {finding.recovery_type.replace('_', ' ')} opportunity: "
                f"R$ {finding.recoverable_amount:,.2f} recoverable with "
                f"{finding.recovery_probability*100:.0f}% probability."
            )
        elif candidate.source_type == "opportunity":
            opp = candidate.source_finding
            return (
                f"Discovered {opp.opportunity_type.replace('_', ' ')}: "
                f"{opp.affected_products[0] if opp.affected_products else 'products'} "
                f"trending {opp.trend_direction} with {opp.trend_strength*100:.0f}% strength."
            )
        return "This decision appeared based on current data analysis."
    
    def _generate_why_ranked(
        self,
        candidate: RawDecisionCandidate,
        scores: Dict[str, float],
        rank: int
    ) -> str:
        """Generate explanation of why this decision is ranked here."""
        reasons = []
        
        if scores["financial_impact_score"] >= 80:
            reasons.append("very high financial impact")
        elif scores["financial_impact_score"] >= 60:
            reasons.append("significant financial impact")
        
        if scores["urgency_score"] >= 80:
            reasons.append("urgent action required")
        elif scores["urgency_score"] >= 60:
            reasons.append("time-sensitive")
        
        if scores["confidence_score"] >= 80:
            reasons.append("high confidence data")
        
        if scores["ease_score"] >= 80:
            reasons.append("easy to execute")
        
        if not reasons:
            reasons.append("balanced priority across all factors")
        
        reason_str = ", ".join(reasons)
        
        if rank == 1:
            return f"Ranked #1 because it has {reason_str}. This should be your first priority today."
        elif rank <= 3:
            return f"Ranked #{rank} due to {reason_str}. Address after higher priority items."
        else:
            return f"Ranked #{rank} with {reason_str}. Handle when time permits."
    
    def _generate_money_involved(self, candidate: RawDecisionCandidate) -> str:
        """Generate explanation of money involved."""
        value = candidate.financial_value
        
        if candidate.source_type == "risk":
            return (
                f"R$ {value:,.2f} is at risk. This represents potential loss "
                f"if no action is taken. Acting now can prevent this loss."
            )
        elif candidate.source_type == "recovery":
            return (
                f"R$ {value:,.2f} is recoverable. This is money that can be "
                f"brought back into the business with appropriate action."
            )
        elif candidate.source_type == "opportunity":
            return (
                f"R$ {value:,.2f} potential additional profit. This represents "
                f"growth opportunity that can be captured."
            )
        return f"R$ {value:,.2f} involved in this decision."
    
    def _generate_what_rule(self, candidate: RawDecisionCandidate) -> str:
        """Generate explanation of what rule triggered this."""
        action = candidate.action
        
        return (
            f"Triggered by '{action.source.service}' analyzing "
            f"'{action.source.endpoint}'. Detection method: "
            f"{candidate.source_finding.__class__.__name__} with "
            f"confidence {candidate.confidence_score*100:.0f}%."
        )
    
    def _generate_decision_question(self, candidate: RawDecisionCandidate) -> str:
        """Generate the decision question for the owner."""
        action = candidate.action
        
        if candidate.source_type == "risk":
            return f"Will you {action.suggested_action.lower()} to prevent R$ {candidate.financial_value:,.2f} in losses?"
        elif candidate.source_type == "recovery":
            return f"Will you {action.suggested_action.lower()} to recover R$ {candidate.financial_value:,.2f}?"
        elif candidate.source_type == "opportunity":
            return f"Will you {action.suggested_action.lower()} to capture R$ {candidate.financial_value:,.2f} in additional profit?"
        
        return f"Will you take action on: {action.title}?"
    
    def get_executive_summary(
        self,
        top_decisions: List[DailyDecision],
        tenant_id: str
    ) -> str:
        """Generate an executive summary of today's decisions."""
        if not top_decisions:
            return "No critical decisions requiring attention today. Business operations appear stable."
        
        # Count by type
        risks = sum(1 for d in top_decisions if d.decision_type == "risk")
        recoveries = sum(1 for d in top_decisions if d.decision_type == "recovery")
        opportunities = sum(1 for d in top_decisions if d.decision_type == "opportunity")
        
        # Calculate totals
        total_value = sum(d.action.financial_impact.expected_value for d in top_decisions)
        
        parts = []
        
        if risks > 0:
            parts.append(f"{risks} urgent risk{'s' if risks > 1 else ''} requiring immediate attention")
        
        if recoveries > 0:
            parts.append(f"{recoveries} recovery opportunity{'ies' if recoveries > 1 else 'y'}")
        
        if opportunities > 0:
            parts.append(f"{opportunities} growth opportunity{'ies' if opportunities > 1 else 'y'}")
        
        summary = f"Today: {'; '.join(parts)}. Total value: R$ {total_value:,.2f}. Focus on #1 priority first."
        
        return summary