"""
Decision Discovery Router — VALUE-01

Expõe o Decision Discovery Engine via HTTP.

Endpoints disponíveis:
- GET /api/v1/discovery/top-decision - Melhor decisão do dia
- GET /api/v1/discovery/top-3 - Top 3 decisões
- GET /api/v1/discovery/top-5 - Top 5 decisões

Princípio 19: O LOGOS deve encontrar primeiro a decisão mais valiosa
antes de aumentar a quantidade de decisões apresentadas.
"""

from __future__ import annotations

from datetime import datetime, timedelta
from typing import Any, Dict

from fastapi import APIRouter, HTTPException, Query, Request

from src.services.decision_discovery import DecisionDiscoveryEngine
from src.services.decision_discovery.detectors import (
    CardReceivableDetector,
    ExpenseDetector,
    FuelRevenueDetector,
    SupplierInvoiceSpikeDetector,
)
from src.services.decision_discovery.discovery_route_helpers import (
    discover_for_scope,
    discovery_response_data,
)
from src.services.decision_discovery.discovery_scope import DiscoveryScope, DiscoveryScopeService
from src.services.decision_discovery.models import DecisionCategory
from src.services.decision_discovery.root_cause.investigators import (
    CardReceivableRootCause,
    ExpenseRootCause,
    FuelRevenueRootCause,
    SupplierInvoiceRootCause,
)
from src.services.decision_discovery.root_cause.root_cause_engine import RootCauseEngine
from src.services.decision_evidence.decision_evidence_service import DecisionEvidenceService

router = APIRouter(prefix="/api/v1/discovery", tags=["Decision Discovery"])

_evidence_service = DecisionEvidenceService()
_scope_service = DiscoveryScopeService()


def _build_root_cause_engine() -> RootCauseEngine:
    """Configura investigadores por categoria e detector."""
    engine = RootCauseEngine()
    engine.register_investigator(DecisionCategory.REVENUE, FuelRevenueRootCause())
    engine.register_investigator(DecisionCategory.COST, ExpenseRootCause())
    engine.register_investigator(DecisionCategory.CASH, CardReceivableRootCause())
    engine.register_detector_investigator(
        "SupplierInvoiceSpikeDetector",
        SupplierInvoiceRootCause(),
    )
    return engine


def _get_discovery_engine() -> DecisionDiscoveryEngine:
    """Cria e configura o Discovery Engine com detectores registrados."""
    engine = DecisionDiscoveryEngine()
    engine.register_detector(FuelRevenueDetector())
    engine.register_detector(ExpenseDetector())
    engine.register_detector(CardReceivableDetector())
    engine.register_detector(SupplierInvoiceSpikeDetector())
    return engine


async def _resolve_scope(empresa_codigo: str | None, request: Request) -> DiscoveryScope:
    return await _scope_service.resolve(empresa_codigo, request=request)


async def _run_discovery(
    *,
    data_inicial: str,
    data_final: str,
    top_n: int,
    empresa_codigo: str | None,
    request: Request,
) -> Dict[str, Any]:
    scope = await _resolve_scope(empresa_codigo, request)
    engine = _get_discovery_engine()
    result = await discover_for_scope(
        engine,
        scope,
        data_inicial=data_inicial,
        data_final=data_final,
        top_n=top_n,
    )
    return {
        "success": True,
        "data": discovery_response_data(result, top_n=top_n),
    }


@router.get("/top-decision")
async def get_top_decision(
    request: Request,
    dataInicial: str = Query(..., description="Data inicial (YYYY-MM-DD)"),
    dataFinal: str = Query(..., description="Data final (YYYY-MM-DD)"),
    empresaCodigo: str | None = Query(None, description="Código da empresa ou lista separada por vírgula"),
) -> Dict[str, Any]:
    try:
        return await _run_discovery(
            data_inicial=dataInicial,
            data_final=dataFinal,
            top_n=1,
            empresa_codigo=empresaCodigo,
            request=request,
        )
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail=f"Erro ao executar Decision Discovery Engine: {str(exc)}",
        ) from exc


@router.get("/top-3")
async def get_top_3_decisions(
    request: Request,
    dataInicial: str = Query(..., description="Data inicial (YYYY-MM-DD)"),
    dataFinal: str = Query(..., description="Data final (YYYY-MM-DD)"),
    empresaCodigo: str | None = Query(None, description="Código da empresa ou lista separada por vírgula"),
) -> Dict[str, Any]:
    try:
        return await _run_discovery(
            data_inicial=dataInicial,
            data_final=dataFinal,
            top_n=3,
            empresa_codigo=empresaCodigo,
            request=request,
        )
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail=f"Erro ao executar Decision Discovery Engine: {str(exc)}",
        ) from exc


@router.get("/top-5")
async def get_top_5_decisions(
    request: Request,
    dataInicial: str = Query(..., description="Data inicial (YYYY-MM-DD)"),
    dataFinal: str = Query(..., description="Data final (YYYY-MM-DD)"),
    empresaCodigo: str | None = Query(None, description="Código da empresa ou lista separada por vírgula"),
) -> Dict[str, Any]:
    try:
        return await _run_discovery(
            data_inicial=dataInicial,
            data_final=dataFinal,
            top_n=5,
            empresa_codigo=empresaCodigo,
            request=request,
        )
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail=f"Erro ao executar Decision Discovery Engine: {str(exc)}",
        ) from exc


@router.get("/debug/execution-log")
async def get_execution_log(
    request: Request,
    dataInicial: str = Query(..., description="Data inicial (YYYY-MM-DD)"),
    dataFinal: str = Query(..., description="Data final (YYYY-MM-DD)"),
    empresaCodigo: str | None = Query(None, description="Código da empresa ou lista separada por vírgula"),
) -> Dict[str, Any]:
    try:
        scope = await _resolve_scope(empresaCodigo, request)
        engine = _get_discovery_engine()
        result = await discover_for_scope(
            engine,
            scope,
            data_inicial=dataInicial,
            data_final=dataFinal,
            top_n=1,
        )
        return {
            "success": True,
            "data": {
                "execution_log": engine.get_execution_log(),
                "result": result.to_dict(),
            },
        }
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail=f"Erro ao executar Decision Discovery Engine: {str(exc)}",
        ) from exc


@router.get("/today")
async def get_today_decision(
    request: Request,
    empresaCodigo: str | None = Query(None, description="Código da empresa ou lista separada por vírgula"),
) -> Dict[str, Any]:
    hoje = datetime.now().date()
    data_final = hoje.isoformat()
    data_inicial = (hoje - timedelta(days=7)).isoformat()
    return await get_top_decision(
        request=request,
        dataInicial=data_inicial,
        dataFinal=data_final,
        empresaCodigo=empresaCodigo,
    )


@router.get("/explain/{decision_id}")
async def explain_decision(
    decision_id: str,
    request: Request,
    empresaCodigo: str | None = Query(None, description="Código da empresa ou lista separada por vírgula"),
    dataInicial: str | None = Query(None, description="Data inicial (YYYY-MM-DD)"),
    dataFinal: str | None = Query(None, description="Data final (YYYY-MM-DD)"),
) -> Dict[str, Any]:
    try:
        scope = await _resolve_scope(empresaCodigo, request)
        candidate_data = _evidence_service.find_candidate(
            decision_id,
            scope=scope,
            period_start=dataInicial,
            period_end=dataFinal,
        )
        if not candidate_data:
            if _evidence_service.candidate_exists_outside_scope(decision_id, scope):
                raise HTTPException(
                    status_code=403,
                    detail="Decisão fora do escopo corporativo autorizado",
                )
            raise HTTPException(
                status_code=404,
                detail=f"Decisão não encontrada no snapshot: {decision_id}",
            )

        _scope_service.assert_candidate_visible(scope, candidate_data)
        decision = _evidence_service.to_decision_candidate(candidate_data)
        root_cause_engine = _build_root_cause_engine()
        result = await root_cause_engine.investigate(decision)

        return {
            "success": result.success,
            "data": result.to_dict(),
            "source": "owner_analysis_snapshot",
            "decision_id": decision_id,
        }

    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail=f"Erro ao explicar decisão: {str(exc)}",
        ) from exc
