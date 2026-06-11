from __future__ import annotations

import asyncio

from fastapi import APIRouter, Query

from src.services.prestacao_contas_intelligence_service import PrestacaoContasIntelligenceService
from src.services.prestacao_contas_snapshot_service import PrestacaoContasSnapshotService

router = APIRouter(prefix="/api/v1/prestacao-contas", tags=["Prestação de Contas"])

_service = PrestacaoContasIntelligenceService()
_snapshot = PrestacaoContasSnapshotService(_service)


@router.get("/summary")
async def prestacao_summary(
    dataInicial: str = Query(...),
    dataFinal: str = Query(...),
    empresaCodigo: str | None = Query(None),
) -> dict:
    payload, stale, hit = await _snapshot.get_or_collect(dataInicial, dataFinal, empresaCodigo)
    if not payload:
        return {"success": False, "data": None, "error": "Falha ao consolidar prestação de contas"}
    return {
        "success": True,
        "data": {
            "executive": payload.get("executive"),
            "discovery": payload.get("discovery"),
            "periodo": payload.get("periodo"),
            "performanceMs": payload.get("performanceMs"),
        },
        "snapshot": {"hit": hit, "stale": stale},
        "error": None,
    }


@router.get("/accountability")
async def prestacao_accountability(
    dataInicial: str = Query(...),
    dataFinal: str = Query(...),
    empresaCodigo: str | None = Query(None),
) -> dict:
    payload, stale, hit = await _snapshot.get_or_collect(dataInicial, dataFinal, empresaCodigo)
    if not payload:
        return {"success": False, "data": None, "error": "Falha ao consolidar accountability"}
    return {
        "success": True,
        "data": payload.get("employeeAccountability"),
        "snapshot": {"hit": hit, "stale": stale},
        "error": None,
    }


@router.get("/discovery")
async def prestacao_discovery(
    dataInicial: str = Query(...),
    dataFinal: str = Query(...),
    empresaCodigo: str | None = Query(None),
) -> dict:
    payload, stale, hit = await _snapshot.get_or_collect(dataInicial, dataFinal, empresaCodigo)
    if not payload:
        return {"success": False, "data": None, "error": "Falha ao consolidar discovery"}
    return {
        "success": True,
        "data": payload.get("discovery"),
        "snapshot": {"hit": hit, "stale": stale},
        "error": None,
    }


@router.get("/lineage")
async def prestacao_lineage(
    dataInicial: str = Query(...),
    dataFinal: str = Query(...),
    empresaCodigo: str | None = Query(None),
) -> dict:
    payload, stale, hit = await _snapshot.get_or_collect(dataInicial, dataFinal, empresaCodigo)
    if not payload:
        return {"success": False, "data": None, "error": "Falha ao consolidar linhagem"}
    return {
        "success": True,
        "data": payload.get("documentLineage"),
        "snapshot": {"hit": hit, "stale": stale},
        "error": None,
    }


@router.get("/snapshot")
async def prestacao_snapshot(
    dataInicial: str = Query(...),
    dataFinal: str = Query(...),
    empresaCodigo: str | None = Query(None),
) -> dict:
    master = _snapshot.get_master(dataInicial, dataFinal, empresaCodigo)
    if master.get("stale") and master.get("payload"):
        asyncio.create_task(_snapshot.refresh_background(dataInicial, dataFinal, empresaCodigo))
    return {"success": True, "data": master, "error": None}


@router.post("/refresh")
async def prestacao_refresh(
    dataInicial: str = Query(...),
    dataFinal: str = Query(...),
    empresaCodigo: str | None = Query(None),
) -> dict:
    asyncio.create_task(_snapshot.refresh_background(dataInicial, dataFinal, empresaCodigo))
    return {"success": True, "data": {"status": "refresh_started"}, "error": None}
