"""
Owner Action Center API Routes

Exposes the Owner Intelligence Engine through REST API endpoints.
Provides the Owner Action Center functionality for LOGOS.

Endpoints:
- GET /api/v1/owner-action-center/summary — Complete action center summary
- GET /api/v1/owner-action-center/money-at-risk — Money at risk findings
- GET /api/v1/owner-action-center/recoverable — Recoverable money findings
- GET /api/v1/owner-action-center/opportunities — Growth opportunities
- GET /api/v1/owner-action-center/top5 — Top 5 daily decisions
- GET /api/v1/owner-action-center/actions — All daily decisions
- GET /api/v1/owner-action-center/business-health — Business health metrics
- POST /api/v1/owner-action-center/execute — Execute a decision action
"""

from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any

from fastapi import APIRouter, Query, HTTPException, status
from pydantic import BaseModel, Field

# Import the owner intelligence engine
from src.services.owner_intelligence import (
    OwnerIntelligenceEngine,
    OwnerActionCenterSummary,
    MoneyAtRiskFinding,
    RecoverableMoneyFinding,
    GrowthOpportunity,
    DailyDecision,
    BusinessHealthMetrics,
    EngineDataSources,
)

router = APIRouter(prefix="/api/v1/owner-action-center", tags=["Owner Action Center P03"])

# Initialize the engine
_intelligence_engine: Optional[OwnerIntelligenceEngine] = None


def get_intelligence_engine() -> OwnerIntelligenceEngine:
    """Get or create the OwnerIntelligenceEngine singleton."""
    global _intelligence_engine
    if _intelligence_engine is None:
        _intelligence_engine = OwnerIntelligenceEngine()
    return _intelligence_engine


class DateRangeParams:
    """Common date range parameters."""
    def __init__(
        self,
        dataInicial: str = Query(..., description="Start date (YYYY-MM-DD)"),
        dataFinal: str = Query(..., description="End date (YYYY-MM-DD)"),
        empresaCodigo: str = Query(..., description="WebPosto company code"),
        tenantId: Optional[str] = Query(None, description="Tenant ID (optional, defaults to empresaCodigo)"),
    ):
        self.data_inicial = dataInicial
        self.data_final = dataFinal
        self.empresa_codigo = empresaCodigo
        self.tenant_id = tenantId or empresaCodigo


class ExecuteActionRequest(BaseModel):
    """Request to execute a decision action."""
    action_id: str = Field(..., description="ID of the action to execute")
    empresa_codigo: str = Field(..., description="Company code")
    tenant_id: str = Field(..., description="Tenant ID")
    notes: Optional[str] = Field(None, description="Optional execution notes")


class ExecuteActionResponse(BaseModel):
    """Response from executing a decision action."""
    success: bool
    action_id: str
    status: str
    message: str
    executed_at: datetime


async def _collect_data_sources(params: DateRangeParams) -> EngineDataSources:
    """
    Collect data from all required sources.
    
    In production, this would call the actual services.
    For now, returns structured empty data.
    """
    # TODO: Implement actual data collection from services
    # This should call the existing services in the codebase
    
    return EngineDataSources(
        financial_overview={},
        accounts_receivable={},
        accounts_payable={},
        sales_data={},
        product_data={},
        payment_data={},
        card_data={},
        expense_data={},
        historical_data=None,
    )


@router.get("/summary", response_model=Dict[str, Any])
async def get_action_center_summary(
    dataInicial: str = Query(..., description="Start date (YYYY-MM-DD)"),
    dataFinal: str = Query(..., description="End date (YYYY-MM-DD)"),
    empresaCodigo: str = Query(..., description="WebPosto company code"),
    tenantId: Optional[str] = Query(None, description="Tenant ID (optional)"),
) -> Dict[str, Any]:
    """
    Get complete Owner Action Center summary.
    
    Returns the full action center view including:
    - Business health metrics
    - Money at risk
    - Recoverable money
    - Growth opportunities
    - Top 5 decisions
    - Executive summary
    """
    try:
        params = DateRangeParams(
            dataInicial=dataInicial,
            dataFinal=dataFinal,
            empresaCodigo=empresaCodigo,
            tenantId=tenantId
        )
        
        # Collect data from all sources
        data_sources = await _collect_data_sources(params)
        
        # Generate summary
        engine = get_intelligence_engine()
        summary = await engine.generate_action_center_summary(
            tenant_id=params.tenant_id,
            empresa_codigo=params.empresa_codigo,
            data_sources=data_sources
        )
        
        return {
            "success": True,
            "data": summary,
            "generated_at": datetime.utcnow().isoformat(),
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error generating action center summary: {str(e)}"
        )


@router.get("/money-at-risk", response_model=Dict[str, Any])
async def get_money_at_risk(
    dataInicial: str = Query(..., description="Start date (YYYY-MM-DD)"),
    dataFinal: str = Query(..., description="End date (YYYY-MM-DD)"),
    empresaCodigo: str = Query(..., description="WebPosto company code"),
    tenantId: Optional[str] = Query(None, description="Tenant ID (optional)"),
) -> Dict[str, Any]:
    """Get money at risk findings."""
    try:
        params = DateRangeParams(
            dataInicial=dataInicial,
            dataFinal=dataFinal,
            empresaCodigo=empresaCodigo,
            tenantId=tenantId
        )
        
        data_sources = await _collect_data_sources(params)
        engine = get_intelligence_engine()
        
        # Run only money at risk engine
        findings = await engine.money_at_risk_engine.analyze(
            tenant_id=params.tenant_id,
            empresa_codigo=params.empresa_codigo,
            financial_data=data_sources.financial_overview,
            historical_data=data_sources.historical_data
        )
        
        total_at_risk = sum(f.amount_at_risk * f.probability for f in findings)
        
        return {
            "success": True,
            "data": {
                "findings": findings,
                "total_at_risk": total_at_risk,
                "count": len(findings),
            },
            "generated_at": datetime.utcnow().isoformat(),
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error analyzing money at risk: {str(e)}"
        )


@router.get("/recoverable", response_model=Dict[str, Any])
async def get_recoverable_money(
    dataInicial: str = Query(..., description="Start date (YYYY-MM-DD)"),
    dataFinal: str = Query(..., description="End date (YYYY-MM-DD)"),
    empresaCodigo: str = Query(..., description="WebPosto company code"),
    tenantId: Optional[str] = Query(None, description="Tenant ID (optional)"),
) -> Dict[str, Any]:
    """Get recoverable money findings."""
    try:
        params = DateRangeParams(
            dataInicial=dataInicial,
            dataFinal=dataFinal,
            empresaCodigo=empresaCodigo,
            tenantId=tenantId
        )
        
        data_sources = await _collect_data_sources(params)
        engine = get_intelligence_engine()
        
        # Run only recoverable money engine
        findings = await engine.recoverable_money_engine.analyze(
            tenant_id=params.tenant_id,
            empresa_codigo=params.empresa_codigo,
            receivables_data=data_sources.accounts_receivable,
            sales_data=data_sources.sales_data,
            card_data=data_sources.card_data,
            expense_data=data_sources.expense_data
        )
        
        total_recoverable = sum(f.recoverable_amount * f.recovery_probability for f in findings)
        
        return {
            "success": True,
            "data": {
                "findings": findings,
                "total_recoverable": total_recoverable,
                "count": len(findings),
            },
            "generated_at": datetime.utcnow().isoformat(),
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error analyzing recoverable money: {str(e)}"
        )


@router.get("/opportunities", response_model=Dict[str, Any])
async def get_growth_opportunities(
    dataInicial: str = Query(..., description="Start date (YYYY-MM-DD)"),
    dataFinal: str = Query(..., description="End date (YYYY-MM-DD)"),
    empresaCodigo: str = Query(..., description="WebPosto company code"),
    tenantId: Optional[str] = Query(None, description="Tenant ID (optional)"),
) -> Dict[str, Any]:
    """Get growth opportunities."""
    try:
        params = DateRangeParams(
            dataInicial=dataInicial,
            dataFinal=dataFinal,
            empresaCodigo=empresaCodigo,
            tenantId=tenantId
        )
        
        data_sources = await _collect_data_sources(params)
        engine = get_intelligence_engine()
        
        # Run only growth opportunities engine
        opportunities = await engine.growth_opportunities_engine.analyze(
            tenant_id=params.tenant_id,
            empresa_codigo=params.empresa_codigo,
            sales_data=data_sources.sales_data,
            product_data=data_sources.product_data,
            payment_data=data_sources.payment_data,
            historical_data=data_sources.historical_data
        )
        
        total_opportunity = sum(o.potential_profit for o in opportunities)
        
        return {
            "success": True,
            "data": {
                "opportunities": opportunities,
                "total_opportunity_value": total_opportunity,
                "count": len(opportunities),
            },
            "generated_at": datetime.utcnow().isoformat(),
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error analyzing opportunities: {str(e)}"
        )


@router.get("/top5", response_model=Dict[str, Any])
async def get_top_5_decisions(
    dataInicial: str = Query(..., description="Start date (YYYY-MM-DD)"),
    dataFinal: str = Query(..., description="End date (YYYY-MM-DD)"),
    empresaCodigo: str = Query(..., description="WebPosto company code"),
    tenantId: Optional[str] = Query(None, description="Tenant ID (optional)"),
) -> Dict[str, Any]:
    """
    Get Top 5 daily decisions.
    
    Returns the 5 most important decisions the owner should make today,
    ranked by priority score.
    """
    try:
        params = DateRangeParams(
            dataInicial=dataInicial,
            dataFinal=dataFinal,
            empresaCodigo=empresaCodigo,
            tenantId=tenantId
        )
        
        data_sources = await _collect_data_sources(params)
        engine = get_intelligence_engine()
        
        # Run all engines
        money_at_risk = await engine.money_at_risk_engine.analyze(
            tenant_id=params.tenant_id,
            empresa_codigo=params.empresa_codigo,
            financial_data=data_sources.financial_overview,
            historical_data=data_sources.historical_data
        )
        
        recoverable_money = await engine.recoverable_money_engine.analyze(
            tenant_id=params.tenant_id,
            empresa_codigo=params.empresa_codigo,
            receivables_data=data_sources.accounts_receivable,
            sales_data=data_sources.sales_data,
            card_data=data_sources.card_data,
            expense_data=data_sources.expense_data
        )
        
        opportunities = await engine.growth_opportunities_engine.analyze(
            tenant_id=params.tenant_id,
            empresa_codigo=params.empresa_codigo,
            sales_data=data_sources.sales_data,
            product_data=data_sources.product_data,
            payment_data=data_sources.payment_data,
            historical_data=data_sources.historical_data
        )
        
        # Generate decisions
        top_5, all_decisions = await engine.daily_actions_engine.generate_decisions(
            tenant_id=params.tenant_id,
            empresa_codigo=params.empresa_codigo,
            money_at_risk=money_at_risk,
            recoverable_money=recoverable_money,
            opportunities=opportunities,
            max_decisions=5
        )
        
        # Generate executive summary
        executive_summary = engine.daily_actions_engine.get_executive_summary(
            top_5,
            params.tenant_id
        )
        
        return {
            "success": True,
            "data": {
                "top_5_decisions": top_5,
                "total_decisions": len(all_decisions),
                "executive_summary": executive_summary,
            },
            "generated_at": datetime.utcnow().isoformat(),
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error generating top 5 decisions: {str(e)}"
        )


@router.get("/actions", response_model=Dict[str, Any])
async def get_all_actions(
    dataInicial: str = Query(..., description="Start date (YYYY-MM-DD)"),
    dataFinal: str = Query(..., description="End date (YYYY-MM-DD)"),
    empresaCodigo: str = Query(..., description="WebPosto company code"),
    tenantId: Optional[str] = Query(None, description="Tenant ID (optional)"),
    status: Optional[str] = Query(None, description="Filter by status (pending, in_progress, completed)"),
    priority: Optional[str] = Query(None, description="Filter by priority (critical, high, medium, low)"),
) -> Dict[str, Any]:
    """Get all daily decisions/actions with optional filtering."""
    try:
        params = DateRangeParams(
            dataInicial=dataInicial,
            dataFinal=dataFinal,
            empresaCodigo=empresaCodigo,
            tenantId=tenantId
        )
        
        data_sources = await _collect_data_sources(params)
        engine = get_intelligence_engine()
        
        # Run all engines
        money_at_risk = await engine.money_at_risk_engine.analyze(
            tenant_id=params.tenant_id,
            empresa_codigo=params.empresa_codigo,
            financial_data=data_sources.financial_overview,
            historical_data=data_sources.historical_data
        )
        
        recoverable_money = await engine.recoverable_money_engine.analyze(
            tenant_id=params.tenant_id,
            empresa_codigo=params.empresa_codigo,
            receivables_data=data_sources.accounts_receivable,
            sales_data=data_sources.sales_data,
            card_data=data_sources.card_data,
            expense_data=data_sources.expense_data
        )
        
        opportunities = await engine.growth_opportunities_engine.analyze(
            tenant_id=params.tenant_id,
            empresa_codigo=params.empresa_codigo,
            sales_data=data_sources.sales_data,
            product_data=data_sources.product_data,
            payment_data=data_sources.payment_data,
            historical_data=data_sources.historical_data
        )
        
        # Generate all decisions
        top_5, all_decisions = await engine.daily_actions_engine.generate_decisions(
            tenant_id=params.tenant_id,
            empresa_codigo=params.empresa_codigo,
            money_at_risk=money_at_risk,
            recoverable_money=recoverable_money,
            opportunities=opportunities,
            max_decisions=100  # Get all
        )
        
        # Apply filters if provided
        filtered = all_decisions
        if status:
            filtered = [d for d in filtered if d.action.status.value == status]
        if priority:
            filtered = [d for d in filtered if d.action.priority.value == priority]
        
        return {
            "success": True,
            "data": {
                "actions": filtered,
                "total_count": len(all_decisions),
                "filtered_count": len(filtered),
                "filters_applied": {
                    "status": status,
                    "priority": priority,
                }
            },
            "generated_at": datetime.utcnow().isoformat(),
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error retrieving actions: {str(e)}"
        )


@router.get("/business-health", response_model=Dict[str, Any])
async def get_business_health(
    dataInicial: str = Query(..., description="Start date (YYYY-MM-DD)"),
    dataFinal: str = Query(..., description="End date (YYYY-MM-DD)"),
    empresaCodigo: str = Query(..., description="WebPosto company code"),
    tenantId: Optional[str] = Query(None, description="Tenant ID (optional)"),
) -> Dict[str, Any]:
    """Get business health metrics."""
    try:
        # Get full summary and extract health
        params = DateRangeParams(
            dataInicial=dataInicial,
            dataFinal=dataFinal,
            empresaCodigo=empresaCodigo,
            tenantId=tenantId
        )
        
        data_sources = await _collect_data_sources(params)
        engine = get_intelligence_engine()
        summary = await engine.generate_action_center_summary(
            tenant_id=params.tenant_id,
            empresa_codigo=params.empresa_codigo,
            data_sources=data_sources
        )
        
        return {
            "success": True,
            "data": summary.business_health,
            "generated_at": datetime.utcnow().isoformat(),
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error calculating business health: {str(e)}"
        )


@router.post("/execute", response_model=ExecuteActionResponse)
async def execute_action(request: ExecuteActionRequest) -> ExecuteActionResponse:
    """
    Execute a decision action.
    
    Records that the owner has taken action on a specific decision.
    """
    try:
        # TODO: Implement actual execution logic
        # This would integrate with other systems to execute the action
        
        return ExecuteActionResponse(
            success=True,
            action_id=request.action_id,
            status="in_progress",
            message=f"Action {request.action_id} has been initiated. Check back for status updates.",
            executed_at=datetime.utcnow()
        )
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error executing action: {str(e)}"
        )


@router.get("/today")
async def get_today_summary(
    empresaCodigo: str = Query(..., description="WebPosto company code"),
    tenantId: Optional[str] = Query(None, description="Tenant ID (optional)"),
) -> Dict[str, Any]:
    """
    Get today's action center summary (convenience endpoint).
    
    Uses current date as the analysis period.
    """
    today = datetime.utcnow()
    yesterday = today - timedelta(days=1)
    
    # Format dates
    data_inicial = yesterday.strftime("%Y-%m-%d")
    data_final = today.strftime("%Y-%m-%d")
    
    # Delegate to main summary endpoint
    return await get_action_center_summary(
        dataInicial=data_inicial,
        dataFinal=data_final,
        empresaCodigo=empresaCodigo,
        tenantId=tenantId
    )