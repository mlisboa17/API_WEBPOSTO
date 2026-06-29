"""
Motor 2 — Recoverable Money Engine

Identifies money that can be recovered:
- Overdue receivables (customers who owe money)
- Unbilled sales (sales not yet invoiced)
- Card reconciliation differences
- Duplicate payments
- Billing errors
- Unclaimed credits
- Negotiable expenses

Never assumes - always discovers from actual data.
"""

import logging
from datetime import datetime, timedelta
from typing import List, Optional, Dict, Any
from decimal import Decimal

from .schemas import (
    RecoverableMoneyFinding, DecisionAction, FinancialImpact, DecisionSource,
    ActionType, ActionPriority, ConfidenceLevel
)

logger = logging.getLogger(__name__)


class RecoverableMoneyEngine:
    """
    Engine to find recoverable money.
    
    Discovers:
    - Money owed by customers
    - Sales not yet captured
    - Duplicate/over payments
    - Missed revenue opportunities
    """
    
    def __init__(self):
        self.findings: List[RecoverableMoneyFinding] = []
        
    async def analyze(
        self,
        tenant_id: str,
        empresa_codigo: str,
        receivables_data: Dict[str, Any],
        sales_data: Dict[str, Any],
        card_data: Dict[str, Any],
        expense_data: Dict[str, Any]
    ) -> List[RecoverableMoneyFinding]:
        """
        Analyze data and find recoverable money.
        
        Args:
            tenant_id: Tenant identifier
            empresa_codigo: WebPosto company code
            receivables_data: Accounts receivable data
            sales_data: Sales transaction data
            card_data: Card processing data
            expense_data: Expense/payment data
            
        Returns:
            List of recoverable money findings
        """
        self.findings = []
        
        try:
            # Detect various recovery opportunities
            await self._find_overdue_receivables(tenant_id, empresa_codigo, receivables_data)
            await self._find_unbilled_sales(tenant_id, empresa_codigo, sales_data)
            await self._find_card_reconciliation_gaps(tenant_id, empresa_codigo, card_data)
            await self._find_duplicate_payments(tenant_id, empresa_codigo, expense_data)
            await self._find_billing_errors(tenant_id, empresa_codigo, sales_data)
            await self._find_unclaimed_credits(tenant_id, empresa_codigo, expense_data)
            await self._find_negotiable_expenses(tenant_id, empresa_codigo, expense_data)
            
            logger.info(
                f"RecoverableMoneyEngine: Found {len(self.findings)} recovery opportunities "
                f"for tenant {tenant_id}, empresa {empresa_codigo}"
            )
            
            return self.findings
            
        except Exception as e:
            logger.error(f"Error in RecoverableMoneyEngine.analyze: {e}")
            return []
    
    async def _find_overdue_receivables(
        self,
        tenant_id: str,
        empresa_codigo: str,
        receivables_data: Dict[str, Any]
    ):
        """Find overdue customer receivables."""
        try:
            overdue = receivables_data.get("overdue_accounts", [])
            
            if not overdue:
                return
            
            total_overdue = sum(acc.get("amount", 0) for acc in overdue)
            count = len(overdue)
            
            if total_overdue > 100:
                # Calculate oldest overdue
                oldest_days = max(
                    (datetime.utcnow() - acc.get("due_date", datetime.utcnow())).days
                    for acc in overdue
                    if acc.get("due_date")
                ) if overdue else 0
                
                # Estimate recoverability
                recovery_prob = 0.8 if oldest_days < 30 else 0.6 if oldest_days < 60 else 0.4
                
                finding = RecoverableMoneyFinding(
                    id=f"rec_overdue_{tenant_id}_{datetime.utcnow().strftime('%Y%m%d')}",
                    title=f"R$ {total_overdue:,.2f} overdue from {count} customers",
                    description=f"There are {count} customer accounts with overdue payments "
                              f"totaling R$ {total_overdue:,.2f}. Oldest is {oldest_days} days overdue. "
                              f"Estimated recovery probability: {recovery_prob*100:.0f}%.",
                    recovery_type="overdue_receivable",
                    recoverable_amount=total_overdue,
                    recovery_probability=recovery_prob,
                    recovery_timeframe_days=14 if oldest_days < 30 else 30,
                    affected_customers=count,
                    affected_transactions=len(overdue),
                    oldest_overdue_days=oldest_days,
                    action=DecisionAction(
                        id=f"act_rec_overdue_{tenant_id}",
                        type=ActionType.RECOVER,
                        priority=ActionPriority.HIGH,
                        title=f"Collect R$ {total_overdue:,.2f} from {count} customers",
                        description=f"Contact {count} overdue customers. Start with oldest. "
                                  f"Offer payment plans if needed. Document all commitments.",
                        financial_impact=FinancialImpact(
                            estimated_value=total_overdue * recovery_prob,
                            impact_type="recoverable",
                            probability=recovery_prob,
                            timeframe_days=14 if oldest_days < 30 else 30
                        ),
                        source=DecisionSource(
                            endpoint="/v1/receivables/overdue",
                            service="ReceivablesService",
                            data_timestamp=datetime.utcnow()
                        ),
                        confidence=0.85,
                        confidence_level=ConfidenceLevel.HIGH,
                        tenant_id=tenant_id,
                        empresa_codigo=empresa_codigo,
                        suggested_action="Call customers in order of oldest overdue first, offer 10% discount for immediate payment",
                        category="receivables",
                        tags=["collections", "receivables", "cash-recovery"]
                    ),
                    confidence=0.85,
                    source=DecisionSource(
                        endpoint="/v1/receivables/overdue",
                        service="ReceivablesService",
                        data_timestamp=datetime.utcnow()
                    )
                )
                self.findings.append(finding)
                
        except Exception as e:
            logger.warning(f"Error finding overdue receivables: {e}")
    
    async def _find_unbilled_sales(
        self,
        tenant_id: str,
        empresa_codigo: str,
        sales_data: Dict[str, Any]
    ):
        """Find sales that haven't been properly billed."""
        try:
            unbilled = sales_data.get("unbilled_transactions", [])
            
            if not unbilled:
                return
            
            total_unbilled = sum(t.get("amount", 0) for t in unbilled)
            count = len(unbilled)
            
            if total_unbilled > 100:
                finding = RecoverableMoneyFinding(
                    id=f"rec_unbilled_{tenant_id}_{datetime.utcnow().strftime('%Y%m%d')}",
                    title=f"R$ {total_unbilled:,.2f} in unbilled sales ({count} transactions)",
                    description=f"There are {count} sales transactions totaling "
                              f"R$ {total_unbilled:,.2f} that haven't been properly billed or invoiced. "
                              f"These need immediate billing to capture the revenue.",
                    recovery_type="unbilled_sale",
                    recoverable_amount=total_unbilled,
                    recovery_probability=0.95,  # High probability - just needs billing
                    recovery_timeframe_days=3,
                    affected_transactions=count,
                    action=DecisionAction(
                        id=f"act_rec_unbilled_{tenant_id}",
                        type=ActionType.RECOVER,
                        priority=ActionPriority.CRITICAL,
                        title=f"Bill R$ {total_unbilled:,.2f} in unbilled sales",
                        description=f"Generate invoices for {count} unbilled transactions. "
                                  f"These are confirmed sales that just need proper billing.",
                        financial_impact=FinancialImpact(
                            estimated_value=total_unbilled * 0.95,
                            impact_type="recoverable",
                            probability=0.95,
                            timeframe_days=3
                        ),
                        source=DecisionSource(
                            endpoint="/v1/sales/unbilled",
                            service="SalesService",
                            data_timestamp=datetime.utcnow()
                        ),
                        confidence=0.92,
                        confidence_level=ConfidenceLevel.VERY_HIGH,
                        tenant_id=tenant_id,
                        empresa_codigo=empresa_codigo,
                        suggested_action="Generate invoices for all unbilled transactions today",
                        category="sales",
                        tags=["billing", "sales", "revenue-recovery"]
                    ),
                    confidence=0.92,
                    source=DecisionSource(
                        endpoint="/v1/sales/unbilled",
                        service="SalesService",
                        data_timestamp=datetime.utcnow()
                    )
                )
                self.findings.append(finding)
                
        except Exception as e:
            logger.warning(f"Error finding unbilled sales: {e}")
    
    async def _find_card_reconciliation_gaps(
        self,
        tenant_id: str,
        empresa_codigo: str,
        card_data: Dict[str, Any]
    ):
        """Find gaps in card reconciliation."""
        try:
            pending_settlements = card_data.get("pending_settlements", [])
            
            if not pending_settlements:
                return
            
            total_pending = sum(s.get("amount", 0) for s in pending_settlements)
            count = len(pending_settlements)
            
            if total_pending > 500:
                # Calculate days pending
                oldest_pending = max(
                    (datetime.utcnow() - s.get("transaction_date", datetime.utcnow())).days
                    for s in pending_settlements
                    if s.get("transaction_date")
                ) if pending_settlements else 0
                
                finding = RecoverableMoneyFinding(
                    id=f"rec_card_{tenant_id}_{datetime.utcnow().strftime('%Y%m%d')}",
                    title=f"R$ {total_pending:,.2f} in pending card settlements ({count} transactions)",
                    description=f"There are {count} card transactions totaling "
                              f"R$ {total_pending:,.2f} pending settlement. "
                              f"Oldest is {oldest_pending} days old. These need reconciliation.",
                    recovery_type="card_reconciliation_gap",
                    recoverable_amount=total_pending,
                    recovery_probability=0.9,
                    recovery_timeframe_days=7,
                    affected_transactions=count,
                    action=DecisionAction(
                        id=f"act_rec_card_{tenant_id}",
                        type=ActionType.RECOVER,
                        priority=ActionPriority.HIGH,
                        title=f"Reconcile R$ {total_pending:,.2f} in card transactions",
                        description=f"Reconcile {count} pending card settlements. "
                                  f"Contact acquirer if settlements are delayed. "
                                  f"Verify all transactions have matching receipts.",
                        financial_impact=FinancialImpact(
                            estimated_value=total_pending * 0.9,
                            impact_type="recoverable",
                            probability=0.9,
                            timeframe_days=7
                        ),
                        source=DecisionSource(
                            endpoint="/v1/cards/pending",
                            service="CardReconciliationService",
                            data_timestamp=datetime.utcnow()
                        ),
                        confidence=0.88,
                        confidence_level=ConfidenceLevel.HIGH,
                        tenant_id=tenant_id,
                        empresa_codigo=empresa_codigo,
                        suggested_action="Run card reconciliation report and contact payment processor",
                        category="cards",
                        tags=["cards", "reconciliation", "settlements"]
                    ),
                    confidence=0.88,
                    source=DecisionSource(
                        endpoint="/v1/cards/pending",
                        service="CardReconciliationService",
                        data_timestamp=datetime.utcnow()
                    )
                )
                self.findings.append(finding)
                
        except Exception as e:
            logger.warning(f"Error finding card reconciliation gaps: {e}")
    
    async def _find_duplicate_payments(
        self,
        tenant_id: str,
        empresa_codigo: str,
        expense_data: Dict[str, Any]
    ):
        """Find potentially duplicate payments."""
        try:
            duplicates = expense_data.get("potential_duplicates", [])
            
            if not duplicates:
                return
            
            total_duplicates = sum(d.get("amount", 0) for d in duplicates)
            count = len(duplicates)
            
            if total_duplicates > 100:
                finding = RecoverableMoneyFinding(
                    id=f"rec_dup_{tenant_id}_{datetime.utcnow().strftime('%Y%m%d')}",
                    title=f"{count} potential duplicate payments (R$ {total_duplicates:,.2f})",
                    description=f"Found {count} transactions that appear to be duplicate payments "
                              f"totaling R$ {total_duplicates:,.2f}. These need verification.",
                    recovery_type="duplicate_payment",
                    recoverable_amount=total_duplicates,
                    recovery_probability=0.7,
                    recovery_timeframe_days=14,
                    affected_transactions=count,
                    action=DecisionAction(
                        id=f"act_rec_dup_{tenant_id}",
                        type=ActionType.RECOVER,
                        priority=ActionPriority.MEDIUM,
                        title=f"Review {count} potential duplicate payments",
                        description=f"Verify if {count} transactions are actual duplicates. "
                                  f"If confirmed, request refunds from suppliers.",
                        financial_impact=FinancialImpact(
                            estimated_value=total_duplicates * 0.7,
                            impact_type="recoverable",
                            probability=0.7,
                            timeframe_days=14
                        ),
                        source=DecisionSource(
                            endpoint="/v1/expenses/duplicates",
                            service="ExpenseAnalysisService",
                            data_timestamp=datetime.utcnow()
                        ),
                        confidence=0.75,
                        confidence_level=ConfidenceLevel.MEDIUM,
                        tenant_id=tenant_id,
                        empresa_codigo=empresa_codigo,
                        suggested_action="Review each transaction against invoices and bank statements",
                        category="expenses",
                        tags=["duplicates", "payments", "expense-review"]
                    ),
                    confidence=0.75,
                    source=DecisionSource(
                        endpoint="/v1/expenses/duplicates",
                        service="ExpenseAnalysisService",
                        data_timestamp=datetime.utcnow()
                    )
                )
                self.findings.append(finding)
                
        except Exception as e:
            logger.warning(f"Error finding duplicate payments: {e}")
    
    async def _find_billing_errors(
        self,
        tenant_id: str,
        empresa_codigo: str,
        sales_data: Dict[str, Any]
    ):
        """Find billing errors (wrong amounts, missing discounts, etc)."""
        try:
            errors = sales_data.get("billing_errors", [])
            
            if not errors:
                return
            
            total_errors = sum(e.get("difference", 0) for e in errors)
            count = len(errors)
            
            if total_errors > 50:
                finding = RecoverableMoneyFinding(
                    id=f"rec_billerr_{tenant_id}_{datetime.utcnow().strftime('%Y%m%d')}",
                    title=f"{count} billing errors (R$ {total_errors:,.2f} impact)",
                    description=f"Found {count} billing errors that resulted in under-billing "
                              f"totaling R$ {total_errors:,.2f}. These need correction.",
                    recovery_type="billing_error",
                    recoverable_amount=total_errors,
                    recovery_probability=0.85,
                    recovery_timeframe_days=7,
                    affected_transactions=count,
                    action=DecisionAction(
                        id=f"act_rec_billerr_{tenant_id}",
                        type=ActionType.RECOVER,
                        priority=ActionPriority.HIGH,
                        title=f"Correct {count} billing errors",
                        description=f"Fix billing errors and re-invoice customers. "
                                  f"Check: wrong prices, missing items, wrong quantities.",
                        financial_impact=FinancialImpact(
                            estimated_value=total_errors * 0.85,
                            impact_type="recoverable",
                            probability=0.85,
                            timeframe_days=7
                        ),
                        source=DecisionSource(
                            endpoint="/v1/sales/billing-errors",
                            service="SalesAuditService",
                            data_timestamp=datetime.utcnow()
                        ),
                        confidence=0.82,
                        confidence_level=ConfidenceLevel.HIGH,
                        tenant_id=tenant_id,
                        empresa_codigo=empresa_codigo,
                        suggested_action="Review each error and issue corrected invoices",
                        category="sales",
                        tags=["billing", "errors", "invoices"]
                    ),
                    confidence=0.82,
                    source=DecisionSource(
                        endpoint="/v1/sales/billing-errors",
                        service="SalesAuditService",
                        data_timestamp=datetime.utcnow()
                    )
                )
                self.findings.append(finding)
                
        except Exception as e:
            logger.warning(f"Error finding billing errors: {e}")
    
    async def _find_unclaimed_credits(
        self,
        tenant_id: str,
        empresa_codigo: str,
        expense_data: Dict[str, Any]
    ):
        """Find unclaimed credits from suppliers or service providers."""
        try:
            credits = expense_data.get("unclaimed_credits", [])
            
            if not credits:
                return
            
            total_credits = sum(c.get("amount", 0) for c in credits)
            count = len(credits)
            
            if total_credits > 100:
                finding = RecoverableMoneyFinding(
                    id=f"rec_credit_{tenant_id}_{datetime.utcnow().strftime('%Y%m%d')}",
                    title=f"R$ {total_credits:,.2f} in unclaimed credits ({count} items)",
                    description=f"Found {count} unclaimed credits totaling R$ {total_credits:,.2f} "
                              f"from suppliers and service providers. These need to be claimed.",
                    recovery_type="unclaimed_credit",
                    recoverable_amount=total_credits,
                    recovery_probability=0.9,
                    recovery_timeframe_days=30,
                    affected_transactions=count,
                    action=DecisionAction(
                        id=f"act_rec_credit_{tenant_id}",
                        type=ActionType.RECOVER,
                        priority=ActionPriority.MEDIUM,
                        title=f"Claim R$ {total_credits:,.2f} in credits",
                        description=f"Process {count} credit requests from suppliers. "
                                  f"Include: returns, rebates, price adjustments, promotional credits.",
                        financial_impact=FinancialImpact(
                            estimated_value=total_credits * 0.9,
                            impact_type="recoverable",
                            probability=0.9,
                            timeframe_days=30
                        ),
                        source=DecisionSource(
                            endpoint="/v1/expenses/credits",
                            service="ExpenseService",
                            data_timestamp=datetime.utcnow()
                        ),
                        confidence=0.80,
                        confidence_level=ConfidenceLevel.HIGH,
                        tenant_id=tenant_id,
                        empresa_codigo=empresa_codigo,
                        suggested_action="Contact each supplier and submit credit requests with documentation",
                        category="expenses",
                        tags=["credits", "suppliers", "expense-recovery"]
                    ),
                    confidence=0.80,
                    source=DecisionSource(
                        endpoint="/v1/expenses/credits",
                        service="ExpenseService",
                        data_timestamp=datetime.utcnow()
                    )
                )
                self.findings.append(finding)
                
        except Exception as e:
            logger.warning(f"Error finding unclaimed credits: {e}")
    
    async def _find_negotiable_expenses(
        self,
        tenant_id: str,
        empresa_codigo: str,
        expense_data: Dict[str, Any]
    ):
        """Find expenses that may be negotiable or reducible."""
        try:
            negotiable = expense_data.get("negotiable_expenses", [])
            
            if not negotiable:
                return
            
            total_negotiable = sum(n.get("potential_savings", 0) for n in negotiable)
            count = len(negotiable)
            
            if total_negotiable > 200:
                finding = RecoverableMoneyFinding(
                    id=f"rec_neg_{tenant_id}_{datetime.utcnow().strftime('%Y%m%d')}",
                    title=f"R$ {total_negotiable:,.2f} in negotiable expenses ({count} items)",
                    description=f"Found {count} expense items totaling R$ {total_negotiable:,.2f} "
                              f"that may be negotiable. Potential savings through renegotiation.",
                    recovery_type="negotiable_expense",
                    recoverable_amount=total_negotiable,
                    recovery_probability=0.5,
                    recovery_timeframe_days=60,
                    affected_transactions=count,
                    action=DecisionAction(
                        id=f"act_rec_neg_{tenant_id}",
                        type=ActionType.OPTIMIZE,
                        priority=ActionPriority.LOW,
                        title=f"Renegotiate {count} supplier contracts",
                        description=f"Renegotiate {count} expense items to reduce costs. "
                                  f"Potential monthly savings: R$ {total_negotiable:,.2f}.",
                        financial_impact=FinancialImpact(
                            estimated_value=total_negotiable * 0.5,
                            impact_type="cost_avoidance",
                            probability=0.5,
                            timeframe_days=60
                        ),
                        source=DecisionSource(
                            endpoint="/v1/expenses/analysis",
                            service="ExpenseOptimizationService",
                            data_timestamp=datetime.utcnow()
                        ),
                        confidence=0.70,
                        confidence_level=ConfidenceLevel.MEDIUM,
                        tenant_id=tenant_id,
                        empresa_codigo=empresa_codigo,
                        suggested_action="Contact suppliers and request price reviews based on volume",
                        category="expenses",
                        tags=["negotiation", "cost-reduction", "suppliers"]
                    ),
                    confidence=0.70,
                    source=DecisionSource(
                        endpoint="/v1/expenses/analysis",
                        service="ExpenseOptimizationService",
                        data_timestamp=datetime.utcnow()
                    )
                )
                self.findings.append(finding)
                
        except Exception as e:
            logger.warning(f"Error finding negotiable expenses: {e}")
    
    def get_total_recoverable(self) -> float:
        """Get total recoverable amount across all findings."""
        return sum(
            f.recoverable_amount * f.recovery_probability
            for f in self.findings
        )