"""
Execution Metrics Calculator | LOGOS
=====================================

Calculates execution effectiveness metrics.

Strict separation:
- Estimated Impact: Projections (before execution)
- Confirmed Impact: Verified facts (after confirmation)

Never mix the two in calculations or displays.
"""

from datetime import datetime, timedelta
from decimal import Decimal
from typing import List, Optional, Dict, Any

from .models import (
    DecisionStatus,
    ExecutionRecord,
    ExecutionMetrics,
    ExecutionSummary,
    ImpactType,
    ConfirmationResult,
)


class ExecutionMetricsCalculator:
    """
    Calculates decision execution effectiveness.
    
    Separates strictly:
    - Estimates (projections, labeled as such)
    - Confirmed (verified facts, labeled as such)
    """
    
    @classmethod
    def calculate_period_metrics(
        cls,
        records: List[ExecutionRecord],
        period_start: datetime,
        period_end: datetime,
        tenant_id: Optional[str] = None
    ) -> ExecutionMetrics:
        """
        Calculate metrics for a time period.
        
        Args:
            records: List of execution records
            period_start: Start of period
            period_end: End of period
            tenant_id: Filter by tenant (None = all)
            
        Returns:
            ExecutionMetrics with strict estimate/confirmed separation
        """
        # Filter records by period and tenant
        filtered = [
            r for r in records
            if period_start <= r.created_at <= period_end
            and (tenant_id is None or r.tenant_id == tenant_id)
        ]
        
        metrics = ExecutionMetrics(
            period_start=period_start,
            period_end=period_end,
            tenant_id=tenant_id
        )
        
        # Volume metrics
        metrics.decisions_generated = len(filtered)
        
        # By status
        presented = [r for r in filtered if r.current_status != DecisionStatus.NEW]
        executed = [r for r in filtered if r.current_status in [
            DecisionStatus.EXECUTING,
            DecisionStatus.COMPLETED,
            DecisionStatus.NOT_COMPLETED,
            DecisionStatus.PARTIAL
        ]]
        completed = [r for r in filtered if r.current_status == DecisionStatus.COMPLETED]
        not_completed = [r for r in filtered if r.current_status == DecisionStatus.NOT_COMPLETED]
        partial = [r for r in filtered if r.current_status == DecisionStatus.PARTIAL]
        expired = [r for r in filtered if r.current_status == DecisionStatus.EXPIRED]
        
        metrics.decisions_presented = len(presented)
        metrics.decisions_executed = len(executed)
        metrics.decisions_completed = len(completed)
        metrics.decisions_not_completed = len(not_completed)
        metrics.decisions_partial = len(partial)
        metrics.decisions_expired = len(expired)
        
        # Financial impact - STRICTLY SEPARATED
        # Estimated impact (from all records)
        metrics.total_estimated_impact = sum(
            (r.estimated_impact.amount for r in filtered),
            Decimal("0")
        )
        
        # Confirmed impact (only from records with confirmation)
        confirmed_records = [r for r in filtered if r.confirmed_impact is not None]
        metrics.total_confirmed_impact = sum(
            (r.confirmed_impact.amount for r in confirmed_records),
            Decimal("0")
        )
        
        # Impact by type - ONLY confirmed amounts
        for r in confirmed_records:
            impact_type = r.confirmed_impact.impact_type
            amount = r.confirmed_impact.amount
            
            if impact_type == ImpactType.RECOVERED:
                metrics.recovered_amount += amount
            elif impact_type == ImpactType.SAVED:
                metrics.saved_amount += amount
            elif impact_type == ImpactType.ADDITIONAL:
                metrics.additional_amount += amount
            elif impact_type == ImpactType.PREVENTED:
                metrics.prevented_amount += amount
        
        # Timing metrics
        exec_times = []
        resolution_times = []
        
        for r in executed:
            # Time to execute (READY → EXECUTING)
            tte = r.get_time_to_execute()
            if tte:
                exec_times.append(tte.total_seconds() / 60)  # Convert to minutes
            
            # Time to resolve (EXECUTING → terminal)
            ted = r.get_execution_duration()
            if ted:
                resolution_times.append(ted.total_seconds() / 60)
        
        if exec_times:
            metrics.avg_time_to_execute_minutes = sum(exec_times) / len(exec_times)
        
        if resolution_times:
            metrics.avg_execution_duration_minutes = sum(resolution_times) / len(resolution_times)
        
        return metrics
    
    @classmethod
    def calculate_tenant_summary(
        cls,
        records: List[ExecutionRecord],
        tenant_id: str,
        empresa_codigo: str,
        today: Optional[datetime] = None
    ) -> ExecutionSummary:
        """
        Calculate summary for tenant dashboard.
        
        Shows:
        - Pending decisions
        - Today's activity
        - This period stats
        - All time totals
        """
        if today is None:
            today = datetime.utcnow()
        
        # Filter by tenant
        tenant_records = [
            r for r in records
            if r.tenant_id == tenant_id and r.empresa_codigo == empresa_codigo
        ]
        
        summary = ExecutionSummary(
            tenant_id=tenant_id,
            empresa_codigo=empresa_codigo
        )
        
        # Pending (READY but not executed or expired)
        pending = [
            r for r in tenant_records
            if r.current_status == DecisionStatus.READY and not r.is_expired()
        ]
        summary.pending_count = len(pending)
        summary.pending_estimated_value = sum(
            (r.estimated_impact.amount for r in pending),
            Decimal("0")
        )
        
        # Urgent (priority = CRITICAL or HIGH)
        urgent = [r for r in pending if r.priority in ["CRITICAL", "HIGH"]]
        summary.urgent_count = len(urgent)
        
        # Today's activity
        today_start = today.replace(hour=0, minute=0, second=0, microsecond=0)
        today_end = today_start + timedelta(days=1)
        
        today_records = [
            r for r in tenant_records
            if r.timeline.events and today_start <= r.timeline.events[-1].timestamp < today_end
        ]
        
        summary.executed_today = len([
            r for r in today_records
            if r.current_status in [
                DecisionStatus.EXECUTING,
                DecisionStatus.COMPLETED,
                DecisionStatus.NOT_COMPLETED,
                DecisionStatus.PARTIAL
            ]
        ])
        
        summary.completed_today = len([
            r for r in today_records
            if r.current_status == DecisionStatus.COMPLETED
        ])
        
        # Confirmed value today
        summary.confirmed_today_value = sum(
            (
                r.confirmed_impact.amount
                for r in today_records
                if r.confirmed_impact is not None
            ),
            Decimal("0")
        )
        
        # This period (default: current month)
        period_start = today.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        period_records = [r for r in tenant_records if r.created_at >= period_start]
        
        summary.period_generated = len(period_records)
        summary.period_executed = len([
            r for r in period_records
            if r.current_status in [
                DecisionStatus.EXECUTING,
                DecisionStatus.COMPLETED,
                DecisionStatus.PARTIAL
            ]
        ])
        
        # Period completion rate
        executed_in_period = [
            r for r in period_records
            if r.current_status in [
                DecisionStatus.COMPLETED,
                DecisionStatus.NOT_COMPLETED,
                DecisionStatus.PARTIAL
            ]
        ]
        if executed_in_period:
            completed = len([r for r in executed_in_period if r.current_status == DecisionStatus.COMPLETED])
            summary.period_completion_rate = (completed / len(executed_in_period)) * 100
        
        # Period confirmed value
        summary.period_confirmed_value = sum(
            (
                r.confirmed_impact.amount
                for r in period_records
                if r.confirmed_impact is not None
            ),
            Decimal("0")
        )
        
        # All time
        summary.total_executed = len([
            r for r in tenant_records
            if r.current_status in [
                DecisionStatus.EXECUTING,
                DecisionStatus.COMPLETED,
                DecisionStatus.NOT_COMPLETED,
                DecisionStatus.PARTIAL
            ]
        ])
        
        summary.total_completed = len([
            r for r in tenant_records
            if r.current_status == DecisionStatus.COMPLETED
        ])
        
        summary.total_confirmed_value = sum(
            (
                r.confirmed_impact.amount
                for r in tenant_records
                if r.confirmed_impact is not None
            ),
            Decimal("0")
        )
        
        return summary
    
    @classmethod
    def format_impact_for_display(
        cls,
        estimated: Decimal,
        confirmed: Optional[Decimal],
        currency: str = "BRL"
    ) -> Dict[str, Any]:
        """
        Format impact for UI display with clear labeling.
        
        NEVER mixes estimated and confirmed values.
        Always shows both separately with labels.
        """
        display = {
            "estimated": {
                "amount": float(estimated),
                "currency": currency,
                "label": "ESTIMADO",  # Always show as estimate
                "description": "Projeção baseada em análise de dados"
            }
        }
        
        if confirmed is not None:
            display["confirmed"] = {
                "amount": float(confirmed),
                "currency": currency,
                "label": "CONFIRMADO",  # Show as confirmed fact
                "description": "Valor verificado após execução"
            }
            
            # Calculate variance
            if estimated > 0:
                variance = ((confirmed - estimated) / estimated) * 100
                display["variance"] = {
                    "percent": float(variance),
                    "direction": "higher" if variance > 0 else "lower"
                }
        else:
            display["status"] = "awaiting_confirmation"
            display["note"] = "Aguardando confirmação do resultado"
        
        return display
    
    @classmethod
    def get_impact_status_label(
        cls,
        has_confirmed: bool,
        confirmed_amount: Optional[Decimal] = None,
        estimated_amount: Optional[Decimal] = None
    ) -> str:
        """
        Get appropriate label for impact display.
        
        Ensures clear differentiation between estimate and fact.
        """
        if has_confirmed and confirmed_amount is not None:
            if estimated_amount and confirmed_amount < estimated_amount * Decimal("0.5"):
                return "CONFIRMADO (abaixo da estimativa)"
            elif estimated_amount and confirmed_amount > estimated_amount * Decimal("1.5"):
                return "CONFIRMADO (acima da estimativa)"
            else:
                return "CONFIRMADO"
        else:
            return "ESTIMADO (aguardando confirmação)"
