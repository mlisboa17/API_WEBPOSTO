"""
Owner Action Center Router — BUILD-03 / PERFORMANCE-01

Fast Daily Analysis Loop:
- GET /top5 retorna último snapshot válido imediatamente
- Refresh em background quando freshness exige
- POST /analysis/refresh dispara nova análise sem bloquear
"""

from __future__ import annotations

from datetime import datetime, timedelta

from fastapi import APIRouter, HTTPException, Query

from src.services.action_center_service import ActionCenterService
from src.services.action_center_snapshot_service import ActionCenterSnapshotService
from src.services.owner_analysis_snapshot_service import get_owner_analysis_snapshot_service
from src.services.performance.performance_metrics import performance_metrics

router = APIRouter(prefix="/api/v1/owner-action-center", tags=["Owner Action Center"])

_action_service = ActionCenterService()
_action_snapshot = ActionCenterSnapshotService(_action_service)
_owner_snapshot = get_owner_analysis_snapshot_service()


@router.get("/top5")
async def get_top5_decisions(
    dataInicial: str = Query(..., description="Data inicial (YYYY-MM-DD)"),
    dataFinal: str = Query(..., description="Data final (YYYY-MM-DD)"),
    empresaCodigo: str | None = Query(None, description="Código da empresa (opcional)"),
) -> dict:
    """Retorna análise atual via snapshot — resposta rápida (<1s target)."""
    return await _owner_snapshot.get_current_analysis(
        dataInicial,
        dataFinal,
        empresa_codigo=empresaCodigo,
        auto_refresh=True,
    )


@router.post("/analysis/refresh")
async def trigger_analysis_refresh(
    dataInicial: str = Query(..., description="Data inicial (YYYY-MM-DD)"),
    dataFinal: str = Query(..., description="Data final (YYYY-MM-DD)"),
    empresaCodigo: str | None = Query(None, description="Código da empresa (opcional)"),
) -> dict:
    """Dispara refresh em background; retorna imediatamente."""
    return await _owner_snapshot.trigger_refresh(
        dataInicial,
        dataFinal,
        empresa_codigo=empresaCodigo,
        reason="manual",
    )


@router.get("/analysis/status/{analysis_id}")
async def get_analysis_refresh_status(analysis_id: str) -> dict:
    """Progresso real de uma análise em andamento ou recém-concluída."""
    status = _owner_snapshot.get_refresh_status(analysis_id)
    if not status:
        raise HTTPException(status_code=404, detail="Análise não encontrada")
    return {"success": True, "data": status}


@router.get("/analysis/metrics")
async def get_analysis_metrics() -> dict:
    """Métricas runtime acumuladas (PERFORMANCE-01)."""
    return {"success": True, "metrics": performance_metrics.snapshot()}


@router.post("/analysis/metrics/reset")
async def reset_analysis_metrics() -> dict:
    """Zera contadores runtime (PERFORMANCE-01 medição)."""
    from src.metrics.collector import metrics_collector

    performance_metrics.reset()
    metrics_collector.reset()
    return {"success": True, "reset": True}


@router.get("/business-health")
async def get_business_health(
    dataInicial: str = Query(..., description="Data inicial (YYYY-MM-DD)"),
    dataFinal: str = Query(..., description="Data final (YYYY-MM-DD)"),
    empresaCodigo: str | None = Query(None, description="Código da empresa"),
) -> dict:
    try:
        payload, stale, hit = await _action_snapshot.get_or_collect(
            dataInicial, dataFinal, empresaCodigo
        )

        if not payload:
            return {
                "success": True,
                "data": {
                    "overall_score": 0,
                    "status": "unknown",
                    "risk_count": 0,
                    "last_update": datetime.now().isoformat(),
                    "has_sufficient_data": False,
                    "message": "Dados insuficientes para calcular health score",
                },
            }

        overall_score = 0
        status = "unknown"
        risk_count = 0

        return {
            "success": True,
            "data": {
                "overall_score": overall_score,
                "status": status,
                "risk_count": risk_count,
                "last_update": datetime.now().isoformat(),
                "has_sufficient_data": overall_score > 0,
                "message": "Dados insuficientes para calcular health score" if overall_score == 0 else None,
            },
            "snapshot": {"hit": hit, "stale": stale},
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erro ao calcular health score: {str(e)}")


@router.get("/today-summary")
async def get_today_summary(
    empresaCodigo: str | None = Query(None, description="Código da empresa"),
) -> dict:
    """Resumo de hoje — usa fast path de snapshot (não bloqueia)."""
    hoje = datetime.now().date()
    data_final = hoje.isoformat()
    data_inicial = (hoje - timedelta(days=7)).isoformat()

    decisions_response = await _owner_snapshot.get_current_analysis(
        data_inicial,
        data_final,
        empresa_codigo=empresaCodigo,
        auto_refresh=True,
    )
    health_response = await get_business_health(data_inicial, data_final, empresaCodigo)

    return {
        "success": True,
        "data": {
            "decisions": decisions_response.get("data", {}),
            "health": health_response.get("data", {}),
            "period": {"start": data_inicial, "end": data_final},
            "freshness": decisions_response.get("freshness"),
            "refresh_status": decisions_response.get("refresh_status"),
        },
    }
