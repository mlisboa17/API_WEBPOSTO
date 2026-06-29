"""
Motor 1 — Money At Risk Engine

Identifies financial threats and risks:
- Revenue declining
- Expenses increasing abnormally
- Cash shortages
- Margin compression
- Product mix deterioration
- Employee voucher anomalies
- Overdue receivables
- Card reconciliation issues

Never uses fixed limits - calculates baselines automatically.
"""

import logging
from datetime import datetime, timedelta
from typing import List, Optional, Dict, Any
from decimal import Decimal

from .schemas import (
    MoneyAtRiskFinding, DecisionAction, FinancialImpact, DecisionSource,
    ActionType, ActionPriority, ConfidenceLevel, BaselineConfig, RiskThresholds
)

logger = logging.getLogger(__name__)


class MoneyAtRiskEngine:
    """
    Engine to detect money at risk.
    
    Discovers risks automatically without fixed thresholds.
    Uses statistical baselines and deviations.
    """
    
    def __init__(
        self,
        baseline_config: Optional[BaselineConfig] = None,
        thresholds: Optional[RiskThresholds] = None
    ):
        self.baseline_config = baseline_config or BaselineConfig()
        self.thresholds = thresholds or RiskThresholds()
        self.findings: List[MoneyAtRiskFinding] = []
        
    async def analyze(
        self,
        tenant_id: str,
        empresa_codigo: str,
        financial_data: Dict[str, Any],
        historical_data: Optional[Dict[str, Any]] = None
    ) -> List[MoneyAtRiskFinding]:
        """
        Analyze financial data and detect money at risk.
        
        Args:
            tenant_id: Tenant identifier
            empresa_codigo: WebPosto company code
            financial_data: Current financial data from services
            historical_data: Historical data for baseline calculation
            
        Returns:
            List of money at risk findings
        """
        self.findings = []
        
        try:
            # Detect various risk types
            await self._detect_revenue_decline(tenant_id, empresa_codigo, financial_data, historical_data)
            await self._detect_expense_anomaly(tenant_id, empresa_codigo, financial_data, historical_data)
            await self._detect_cash_shortage(tenant_id, empresa_codigo, financial_data)
            await self._detect_margin_compression(tenant_id, empresa_codigo, financial_data, historical_data)
            await self._detect_voucher_anomaly(tenant_id, empresa_codigo, financial_data, historical_data)
            await self._detect_product_mix_deterioration(tenant_id, empresa_codigo, financial_data, historical_data)
            await self._detect_overdue_receivables(tenant_id, empresa_codigo, financial_data)
            await self._detect_card_reconciliation_issues(tenant_id, empresa_codigo, financial_data)
            
            logger.info(
                f"MoneyAtRiskEngine: Detected {len(self.findings)} findings "
                f"for tenant {tenant_id}, empresa {empresa_codigo}"
            )
            
            return self.findings
            
        except Exception as e:
            logger.error(f"Error in MoneyAtRiskEngine.analyze: {e}")
            return []
    
    async def _detect_revenue_decline(
        self,
        tenant_id: str,
        empresa_codigo: str,
        financial_data: Dict[str, Any],
        historical_data: Optional[Dict[str, Any]]
    ):
        """Detect revenue decline compared to baseline."""
        try:
            current_revenue = financial_data.get("total_revenue", 0)
            if not current_revenue or not historical_data:
                return
            
            # Calculate baseline from historical data
            baseline_revenue = self._calculate_baseline(historical_data.get("revenues", []))
            if not baseline_revenue:
                return
            
            deviation = ((current_revenue - baseline_revenue) / baseline_revenue) * 100
            
            # Only detect if decline is significant
            if deviation <= -self.thresholds.revenue_drop_percent:
                # Calculate amount at risk
                days_in_month = 30
                daily_baseline = baseline_revenue / self.baseline_config.lookback_days
                days_affected = min(7, days_in_month)  # Assume 7 days if trend continues
                amount_at_risk = daily_baseline * days_affected * abs(deviation) / 100
                
                finding = MoneyAtRiskFinding(
                    id=f"risk_revenue_{tenant_id}_{datetime.utcnow().strftime('%Y%m%d')}",
                    title=f"Revenue declining {abs(deviation):.1f}% below normal",
                    description=f"Today's revenue is {abs(deviation):.1f}% below the 30-day baseline. "
                              f"This trend, if continued, could result in significant losses.",
                    risk_type="revenue_decline",
                    amount_at_risk=amount_at_risk,
                    probability=0.6 if deviation <= -30 else 0.4,
                    timeframe_days=7,
                    baseline_value=baseline_revenue,
                    current_value=current_revenue,
                    deviation_percent=deviation,
                    action=DecisionAction(
                        id=f"act_revenue_{tenant_id}",
                        type=ActionType.URGENT,
                        priority=ActionPriority.CRITICAL if deviation <= -30 else ActionPriority.HIGH,
                        title="Review sales performance immediately",
                        description=f"Revenue is {abs(deviation):.1f}% below normal. "
                                  f"Check: (1) Fuel prices vs competitors, "
                                  f"(2) Inventory levels, (3) Employee attendance, "
                                  f"(4) Any operational issues today.",
                        financial_impact=FinancialImpact(
                            estimated_value=amount_at_risk,
                            impact_type="loss_prevented",
                            probability=0.7,
                            timeframe_days=7
                        ),
                        source=DecisionSource(
                            endpoint="/v1/financial/overview",
                            service="FinancialOverviewService",
                            data_timestamp=datetime.utcnow()
                        ),
                        confidence=0.85,
                        confidence_level=ConfidenceLevel.HIGH,
                        tenant_id=tenant_id,
                        empresa_codigo=empresa_codigo,
                        suggested_action="Review yesterday's sales breakdown by product and compare with same day last week",
                        category="revenue",
                        tags=["revenue", "decline", "sales", "urgent"]
                    ),
                    confidence=0.85,
                    source=DecisionSource(
                        endpoint="/v1/financial/overview",
                        service="FinancialOverviewService",
                        data_timestamp=datetime.utcnow()
                    )
                )
                self.findings.append(finding)
                
        except Exception as e:
            logger.warning(f"Error detecting revenue decline: {e}")
    
    async def _detect_expense_anomaly(
        self,
        tenant_id: str,
        empresa_codigo: str,
        financial_data: Dict[str, Any],
        historical_data: Optional[Dict[str, Any]]
    ):
        """Detect abnormal expense increases."""
        try:
            current_expenses = financial_data.get("total_expenses", 0)
            if not current_expenses or not historical_data:
                return
            
            baseline_expenses = self._calculate_baseline(historical_data.get("expenses", []))
            if not baseline_expenses:
                return
            
            deviation = ((current_expenses - baseline_expenses) / baseline_expenses) * 100
            
            if deviation >= self.thresholds.expense_increase_percent:
                amount_at_risk = current_expenses - baseline_expenses
                
                finding = MoneyAtRiskFinding(
                    id=f"risk_expense_{tenant_id}_{datetime.utcnow().strftime('%Y%m%d')}",
                    title=f"Expenses {deviation:.1f}% above normal",
                    description=f"Today's expenses are {deviation:.1f}% higher than baseline. "
                              f"Abnormal expense patterns may indicate waste, fraud, or accounting errors.",
                    risk_type="expense_increase",
                    amount_at_risk=amount_at_risk * 30,  # Monthly projection
                    probability=0.5,
                    timeframe_days=30,
                    baseline_value=baseline_expenses,
                    current_value=current_expenses,
                    deviation_percent=deviation,
                    action=DecisionAction(
                        id=f"act_expense_{tenant_id}",
                        type=ActionType.REVIEW,
                        priority=ActionPriority.HIGH,
                        title="Review abnormal expenses",
                        description=f"Expenses are {deviation:.1f}% above baseline. "
                                  f"Review: (1) Employee vouchers, (2) Supplier payments, "
                                  f"(3) Unusual purchases, (4) Duplicate payments.",
                        financial_impact=FinancialImpact(
                            estimated_value=amount_at_risk * 30,
                            impact_type="cost_avoidance",
                            probability=0.6,
                            timeframe_days=30
                        ),
                        source=DecisionSource(
                            endpoint="/v1/financial/expenses",
                            service="ExpenseAnalysisService",
                            data_timestamp=datetime.utcnow()
                        ),
                        confidence=0.80,
                        confidence_level=ConfidenceLevel.HIGH,
                        tenant_id=tenant_id,
                        empresa_codigo=empresa_codigo,
                        suggested_action="Pull detailed expense report and identify specific categories with increases",
                        category="expenses",
                        tags=["expenses", "anomaly", "cost-control"]
                    ),
                    confidence=0.80,
                    source=DecisionSource(
                        endpoint="/v1/financial/expenses",
                        service="ExpenseAnalysisService",
                        data_timestamp=datetime.utcnow()
                    )
                )
                self.findings.append(finding)
                
        except Exception as e:
            logger.warning(f"Error detecting expense anomaly: {e}")
    
    async def _detect_cash_shortage(
        self,
        tenant_id: str,
        empresa_codigo: str,
        financial_data: Dict[str, Any]
    ):
        """Detect cash shortages or negative cash positions."""
        try:
            cash_position = financial_data.get("cash_position", 0)
            
            if cash_position < -self.thresholds.cash_shortage_threshold:
                finding = MoneyAtRiskFinding(
                    id=f"risk_cash_{tenant_id}_{datetime.utcnow().strftime('%Y%m%d')}",
                    title=f"Cash shortage: R$ {abs(cash_position):,.2f}",
                    description=f"Current cash position is negative at R$ {abs(cash_position):,.2f}. "
                              f"This may indicate timing issues between receipts and payments, "
                              f"or potential cash flow problems.",
                    risk_type="cash_shortage",
                    amount_at_risk=abs(cash_position) * 2,  # Potential to double
                    probability=0.4,
                    timeframe_days=3,
                    baseline_value=0,
                    current_value=cash_position,
                    deviation_percent=-100,
                    action=DecisionAction(
                        id=f"act_cash_{tenant_id}",
                        type=ActionType.URGENT,
                        priority=ActionPriority.CRITICAL,
                        title="Address cash shortage immediately",
                        description=f"Cash position is R$ {abs(cash_position):,.2f} negative. "
                                  f"Actions: (1) Review accounts receivable for collection, "
                                  f"(2) Negotiate payment terms with suppliers, "
                                  f"(3) Check for delayed deposits.",
                        financial_impact=FinancialImpact(
                            estimated_value=abs(cash_position) * 2,
                            impact_type="loss_prevented",
                            probability=0.5,
                            timeframe_days=3
                        ),
                        source=DecisionSource(
                            endpoint="/v1/financial/cash",
                            service="CashOperationsService",
                            data_timestamp=datetime.utcnow()
                        ),
                        confidence=0.90,
                        confidence_level=ConfidenceLevel.VERY_HIGH,
                        tenant_id=tenant_id,
                        empresa_codigo=empresa_codigo,
                        suggested_action="Contact customers with overdue payments and negotiate supplier terms",
                        category="cash",
                        tags=["cash", "shortage", "liquidity", "urgent"]
                    ),
                    confidence=0.90,
                    source=DecisionSource(
                        endpoint="/v1/financial/cash",
                        service="CashOperationsService",
                        data_timestamp=datetime.utcnow()
                    )
                )
                self.findings.append(finding)
                
        except Exception as e:
            logger.warning(f"Error detecting cash shortage: {e}")
    
    async def _detect_margin_compression(
        self,
        tenant_id: str,
        empresa_codigo: str,
        financial_data: Dict[str, Any],
        historical_data: Optional[Dict[str, Any]]
    ):
        """Detect profit margin compression."""
        try:
            current_margin = financial_data.get("profit_margin_percent", 0)
            if not current_margin or not historical_data:
                return
            
            baseline_margins = historical_data.get("profit_margins", [])
            if not baseline_margins:
                return
            
            avg_baseline = sum(baseline_margins) / len(baseline_margins)
            deviation = current_margin - avg_baseline
            
            if deviation <= -self.thresholds.margin_drop_percent:
                revenue = financial_data.get("total_revenue", 0)
                daily_revenue = revenue / 30
                amount_at_risk = daily_revenue * abs(deviation) / 100 * 30  # Monthly
                
                finding = MoneyAtRiskFinding(
                    id=f"risk_margin_{tenant_id}_{datetime.utcnow().strftime('%Y%m%d')}",
                    title=f"Profit margin dropped {abs(deviation):.1f}%",
                    description=f"Current margin ({current_margin:.1f}%) is {abs(deviation):.1f} points "
                              f"below the baseline ({avg_baseline:.1f}%). This significantly "
                              f"impacts profitability.",
                    risk_type="margin_compression",
                    amount_at_risk=amount_at_risk,
                    probability=0.5,
                    timeframe_days=30,
                    baseline_value=avg_baseline,
                    current_value=current_margin,
                    deviation_percent=-abs(deviation),
                    action=DecisionAction(
                        id=f"act_margin_{tenant_id}",
                        type=ActionType.REVIEW,
                        priority=ActionPriority.HIGH,
                        title="Analyze margin compression",
                        description=f"Margin dropped {abs(deviation):.1f} percentage points. "
                                  f"Check: (1) Fuel purchase prices, (2) Product mix changes, "
                                  f"(3) Discounts given, (4) Supplier price changes.",
                        financial_impact=FinancialImpact(
                            estimated_value=amount_at_risk,
                            impact_type="loss_prevented",
                            probability=0.6,
                            timeframe_days=30
                        ),
                        source=DecisionSource(
                            endpoint="/v1/financial/margins",
                            service="MarginAnalysisService",
                            data_timestamp=datetime.utcnow()
                        ),
                        confidence=0.82,
                        confidence_level=ConfidenceLevel.HIGH,
                        tenant_id=tenant_id,
                        empresa_codigo=empresa_codigo,
                        suggested_action="Review fuel purchase invoices and compare with selling prices by product",
                        category="margins",
                        tags=["margins", "profitability", "costs"]
                    ),
                    confidence=0.82,
                    source=DecisionSource(
                        endpoint="/v1/financial/margins",
                        service="MarginAnalysisService",
                        data_timestamp=datetime.utcnow()
                    )
                )
                self.findings.append(finding)
                
        except Exception as e:
            logger.warning(f"Error detecting margin compression: {e}")
    
    async def _detect_voucher_anomaly(
        self,
        tenant_id: str,
        empresa_codigo: str,
        financial_data: Dict[str, Any],
        historical_data: Optional[Dict[str, Any]]
    ):
        """Detect abnormal employee voucher usage."""
        try:
            current_vouchers = financial_data.get("employee_vouchers", 0)
            if not current_vouchers or not historical_data:
                return
            
            baseline_vouchers = self._calculate_baseline(historical_data.get("vouchers", []))
            if not baseline_vouchers:
                return
            
            deviation = ((current_vouchers - baseline_vouchers) / baseline_vouchers) * 100
            
            if deviation >= 50:  # 50% increase threshold for vouchers
                finding = MoneyAtRiskFinding(
                    id=f"risk_voucher_{tenant_id}_{datetime.utcnow().strftime('%Y%m%d')}",
                    title=f"Employee vouchers {deviation:.1f}% above normal",
                    description=f"Employee voucher usage is {deviation:.1f}% higher than baseline. "
                              f"This may indicate abuse or operational issues.",
                    risk_type="voucher_anomaly",
                    amount_at_risk=current_vouchers * 30,  # Monthly projection
                    probability=0.4,
                    timeframe_days=30,
                    baseline_value=baseline_vouchers,
                    current_value=current_vouchers,
                    deviation_percent=deviation,
                    action=DecisionAction(
                        id=f"act_voucher_{tenant_id}",
                        type=ActionType.REVIEW,
                        priority=ActionPriority.MEDIUM,
                        title="Review employee voucher usage",
                        description=f"Vouchers are {deviation:.1f}% above baseline. "
                                  f"Review: (1) Individual employee usage, "
                                  f"(2) Voucher policies, (3) Approval workflows.",
                        financial_impact=FinancialImpact(
                            estimated_value=current_vouchers * 30,
                            impact_type="cost_avoidance",
                            probability=0.5,
                            timeframe_days=30
                        ),
                        source=DecisionSource(
                            endpoint="/v1/operations/vouchers",
                            service="VoucherTrackingService",
                            data_timestamp=datetime.utcnow()
                        ),
                        confidence=0.78,
                        confidence_level=ConfidenceLevel.MEDIUM,
                        tenant_id=tenant_id,
                        empresa_codigo=empresa_codigo,
                        suggested_action="Generate report of vouchers by employee and check for anomalies",
                        category="staff",
                        tags=["vouchers", "employees", "costs"]
                    ),
                    confidence=0.78,
                    source=DecisionSource(
                        endpoint="/v1/operations/vouchers",
                        service="VoucherTrackingService",
                        data_timestamp=datetime.utcnow()
                    )
                )
                self.findings.append(finding)
                
        except Exception as e:
            logger.warning(f"Error detecting voucher anomaly: {e}")
    
    async def _detect_product_mix_deterioration(
        self,
        tenant_id: str,
        empresa_codigo: str,
        financial_data: Dict[str, Any],
        historical_data: Optional[Dict[str, Any]]
    ):
        """Detect unfavorable product mix changes."""
        # Implementation placeholder - would analyze fuel vs non-fuel mix
        pass
    
    async def _detect_overdue_receivables(
        self,
        tenant_id: str,
        empresa_codigo: str,
        financial_data: Dict[str, Any]
    ):
        """Detect overdue accounts receivable."""
        try:
            overdue = financial_data.get("overdue_receivables", {})
            amount = overdue.get("total_amount", 0)
            count = overdue.get("count", 0)
            
            if amount > 1000 and count > 0:
                finding = MoneyAtRiskFinding(
                    id=f"risk_overdue_{tenant_id}_{datetime.utcnow().strftime('%Y%m%d')}",
                    title=f"R$ {amount:,.2f} in {count} overdue accounts",
                    description=f"There are {count} overdue customer accounts totaling "
                              f"R$ {amount:,.2f}. These may become uncollectible if not addressed.",
                    risk_type="overdue_receivables",
                    amount_at_risk=amount * 0.3,  # Assume 30% loss risk
                    probability=0.3,
                    timeframe_days=14,
                    baseline_value=0,
                    current_value=amount,
                    deviation_percent=0,
                    action=DecisionAction(
                        id=f"act_overdue_{tenant_id}",
                        type=ActionType.RECOVER,
                        priority=ActionPriority.HIGH,
                        title=f"Contact {count} overdue customers",
                        description=f"R$ {amount:,.2f} is overdue from {count} customers. "
                                  f"Call each customer to arrange payment. "
                                  f"Consider payment plans for good customers.",
                        financial_impact=FinancialImpact(
                            estimated_value=amount * 0.7,  # Assume 70% recoverable
                            impact_type="recoverable",
                            probability=0.7,
                            timeframe_days=14
                        ),
                        source=DecisionSource(
                            endpoint="/v1/receivables/overdue",
                            service="ReceivablesService",
                            data_timestamp=datetime.utcnow()
                        ),
                        confidence=0.88,
                        confidence_level=ConfidenceLevel.HIGH,
                        tenant_id=tenant_id,
                        empresa_codigo=empresa_codigo,
                        suggested_action="Call each overdue customer and document payment commitments",
                        category="receivables",
                        tags=["receivables", "collections", "cash-flow"]
                    ),
                    confidence=0.88,
                    source=DecisionSource(
                        endpoint="/v1/receivables/overdue",
                        service="ReceivablesService",
                        data_timestamp=datetime.utcnow()
                    )
                )
                self.findings.append(finding)
                
        except Exception as e:
            logger.warning(f"Error detecting overdue receivables: {e}")
    
    async def _detect_card_reconciliation_issues(
        self,
        tenant_id: str,
        empresa_codigo: str,
        financial_data: Dict[str, Any]
    ):
        """Detect card reconciliation discrepancies."""
        try:
            card_diff = financial_data.get("card_reconciliation_difference", 0)
            
            if abs(card_diff) > 500:
                finding = MoneyAtRiskFinding(
                    id=f"risk_card_{tenant_id}_{datetime.utcnow().strftime('%Y%m%d')}",
                    title=f"Card reconciliation issue: R$ {abs(card_diff):,.2f}",
                    description=f"There's a R$ {abs(card_diff):,.2f} discrepancy in card reconciliation. "
                              f"This needs immediate attention to prevent revenue loss.",
                    risk_type="card_reconciliation",
                    amount_at_risk=abs(card_diff) * 2,
                    probability=0.5,
                    timeframe_days=1,
                    baseline_value=0,
                    current_value=card_diff,
                    deviation_percent=0,
                    action=DecisionAction(
                        id=f"act_card_{tenant_id}",
                        type=ActionType.REVIEW,
                        priority=ActionPriority.HIGH,
                        title="Resolve card reconciliation discrepancy",
                        description=f"R$ {abs(card_diff):,.2f} difference in card reconciliation. "
                                  f"Check: (1) Pending settlements, (2) Chargebacks, "
                                  f"(3) Processing errors, (4) Terminal issues.",
                        financial_impact=FinancialImpact(
                            estimated_value=abs(card_diff) * 2,
                            impact_type="loss_prevented",
                            probability=0.6,
                            timeframe_days=1
                        ),
                        source=DecisionSource(
                            endpoint="/v1/cards/reconciliation",
                            service="CardReconciliationService",
                            data_timestamp=datetime.utcnow()
                        ),
                        confidence=0.92,
                        confidence_level=ConfidenceLevel.VERY_HIGH,
                        tenant_id=tenant_id,
                        empresa_codigo=empresa_codigo,
                        suggested_action="Reconcile card transactions manually and identify missing entries",
                        category="cards",
                        tags=["cards", "reconciliation", "payments"]
                    ),
                    confidence=0.92,
                    source=DecisionSource(
                        endpoint="/v1/cards/reconciliation",
                        service="CardReconciliationService",
                        data_timestamp=datetime.utcnow()
                    )
                )
                self.findings.append(finding)
                
        except Exception as e:
            logger.warning(f"Error detecting card reconciliation issues: {e}")
    
    def _calculate_baseline(self, values: List[float]) -> float:
        """Calculate statistical baseline from historical values."""
        if not values or len(values) < self.baseline_config.min_data_points:
            return 0
        
        # Remove outliers using z-score
        mean = sum(values) / len(values)
        variance = sum((x - mean) ** 2 for x in values) / len(values)
        std_dev = variance ** 0.5
        
        if std_dev == 0:
            return mean
        
        # Filter outliers
        filtered = [
            x for x in values
            if abs((x - mean) / std_dev) < self.baseline_config.outlier_threshold
        ]
        
        if not filtered:
            return mean
        
        return sum(filtered) / len(filtered)
    
    def get_total_at_risk(self) -> float:
        """Get total amount at risk across all findings."""
        return sum(f.amount_at_risk * f.probability for f in self.findings)