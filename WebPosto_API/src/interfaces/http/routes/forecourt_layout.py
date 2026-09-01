"""FORECOURT-CONFIG-01A — API de configuração operacional da pista.

Prefix: /api/v1/executive/forecourt-layout
"""

from __future__ import annotations

import logging
from typing import Optional

from fastapi import APIRouter, HTTPException, Query

from src.services.forecourt_layout_service import (
    ForecourtValidationError,
    LayoutCreateDTO,
    LayoutUpdateDTO,
    get_forecourt_layout_service,
)

LOGGER = logging.getLogger(__name__)

router = APIRouter(
    prefix="/api/v1/executive/forecourt-layout",
    tags=["Executive Forecourt Layout"],
)


def _err(exc: ForecourtValidationError) -> HTTPException:
    status = 403 if exc.code == "TENANT_FORBIDDEN" else 400
    if exc.code in {"LAYOUT_NOT_FOUND", "NO_ACTIVE_LAYOUT", "NOZZLE_NOT_MAPPED"}:
        status = 404
    return HTTPException(status_code=status, detail={"code": exc.code, "message": str(exc)})


@router.get("")
async def list_layouts(
    station_id: Optional[int] = Query(None, alias="stationId"),
    empresaCodigo: Optional[int] = Query(None),
) -> dict:
    sid = station_id if station_id is not None else empresaCodigo
    try:
        rows = get_forecourt_layout_service().list_layouts(sid)
        return {"success": True, "data": rows, "namespace": "executive"}
    except ForecourtValidationError as exc:
        raise _err(exc) from exc


@router.post("/seed/casa-caiada")
async def seed_casa_caiada(
    force: bool = Query(False, description="Recria piloto mesmo se já existir"),
) -> dict:
    """Seed auditável do piloto Casa Caiada (dados em data/forecourt_seed_casa_caiada.json)."""
    try:
        seeded = get_forecourt_layout_service().seed_casa_caiada_pilot(force=force)
        return {"success": True, "data": seeded, "namespace": "executive"}
    except ForecourtValidationError as exc:
        raise _err(exc) from exc


@router.post("/seed/posto-real")
async def seed_posto_real(
    force: bool = Query(False, description="Recria piloto mesmo se já existir"),
) -> dict:
    """Seed auditável Posto Doze/Real — 22 bicos (data/forecourt_seed_posto_real.json)."""
    try:
        seeded = get_forecourt_layout_service().seed_posto_real_pilot(force=force)
        return {"success": True, "data": seeded, "namespace": "executive"}
    except ForecourtValidationError as exc:
        raise _err(exc) from exc


@router.get("/active")
async def get_active_layout(
    station_id: int = Query(..., alias="stationId"),
) -> dict:
    try:
        svc = get_forecourt_layout_service()
        layout = svc.get_active_layout(station_id)
        if not layout:
            raise ForecourtValidationError(
                "NO_ACTIVE_LAYOUT", f"Nenhum layout ACTIVE para station_id={station_id}"
            )
        return {
            "success": True,
            "data": {**layout, "summary": svc.layout_summary(layout)},
            "namespace": "executive",
        }
    except ForecourtValidationError as exc:
        raise _err(exc) from exc


@router.get("/resolve")
async def resolve_nozzle_chain(
    station_id: int = Query(..., alias="stationId"),
    nozzle_id: int = Query(..., alias="nozzleId", ge=1),
    layout_id: Optional[str] = Query(None, alias="layoutId"),
) -> dict:
    """BICO → POSIÇÃO → ORIENTAÇÃO → BOMBA → ILHA → COORDENADAS."""
    try:
        resolved = get_forecourt_layout_service().resolve_nozzle(
            station_id, nozzle_id, layout_id=layout_id
        )
        return {"success": True, "data": resolved.model_dump(), "namespace": "executive"}
    except ForecourtValidationError as exc:
        raise _err(exc) from exc


@router.get("/{layout_id}")
async def get_layout(
    layout_id: str,
    requester_station_id: Optional[int] = Query(None, alias="requesterStationId"),
) -> dict:
    try:
        layout = get_forecourt_layout_service().get_layout(
            layout_id, requester_station_id=requester_station_id
        )
        return {"success": True, "data": layout, "namespace": "executive"}
    except ForecourtValidationError as exc:
        raise _err(exc) from exc


@router.post("")
async def create_layout(body: LayoutCreateDTO) -> dict:
    try:
        created = get_forecourt_layout_service().create_layout(body)
        return {"success": True, "data": created, "namespace": "executive"}
    except ForecourtValidationError as exc:
        raise _err(exc) from exc
    except Exception as exc:
        LOGGER.exception("forecourt-layout create falhou: %s", exc)
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@router.put("/{layout_id}")
async def update_layout(layout_id: str, body: LayoutUpdateDTO) -> dict:
    try:
        updated = get_forecourt_layout_service().update_layout(layout_id, body)
        return {"success": True, "data": updated, "namespace": "executive"}
    except ForecourtValidationError as exc:
        raise _err(exc) from exc


@router.post("/{layout_id}/activate")
async def activate_layout(
    layout_id: str,
    requester_station_id: Optional[int] = Query(None, alias="requesterStationId"),
) -> dict:
    try:
        activated = get_forecourt_layout_service().activate_layout(
            layout_id, requester_station_id=requester_station_id
        )
        return {"success": True, "data": activated, "namespace": "executive"}
    except ForecourtValidationError as exc:
        raise _err(exc) from exc


@router.post("/{layout_id}/archive")
async def archive_layout(layout_id: str) -> dict:
    try:
        archived = get_forecourt_layout_service().archive_layout(layout_id)
        return {"success": True, "data": archived, "namespace": "executive"}
    except ForecourtValidationError as exc:
        raise _err(exc) from exc


@router.post("/{layout_id}/validate")
async def validate_layout(layout_id: str) -> dict:
    try:
        result = get_forecourt_layout_service().validate_forecourt_layout(layout_id)
        return {"success": True, "data": result, "namespace": "executive"}
    except ForecourtValidationError as exc:
        raise _err(exc) from exc
