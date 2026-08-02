"""Pista & Volumetria — GET /api/v1/executive/reports/fuel

D0 → cache RAM (<50ms) · D-1 → sales_daily_summary (<200ms)
"""

from __future__ import annotations

import logging
from datetime import date
from typing import Optional

from fastapi import APIRouter, Query

from src.services.fuel_volumetry_service import get_fuel_volumetry_service
from src.utils.filial_normalizer import resolve_empresa_codigo

LOGGER = logging.getLogger(__name__)

router = APIRouter(
    prefix="/api/v1/executive/reports",
    tags=["Executive Fuel Volumetry"],
)


@router.get("/fuel")
async def get_fuel_volumetry(
    dataInicial: Optional[str] = Query(None, pattern=r"^\d{4}-\d{2}-\d{2}$"),
    dataFinal: Optional[str] = Query(None, pattern=r"^\d{4}-\d{2}-\d{2}$"),
    empresaCodigo: Optional[int] = Query(None),
    filial: Optional[str] = Query(
        None, description="Alias: AP Casa Caiada, Posto VIP, Real Doze, TODAS…"
    ),
) -> dict:
    hoje = date.today().isoformat()
    start = dataInicial or hoje
    end = dataFinal or hoje
    raw = filial if filial is not None and str(filial).strip() != "" else empresaCodigo
    empresa = resolve_empresa_codigo(raw)

    LOGGER.info(
        "[Pista & Volumetria] Filial buscada: %s | ID resolvido: %s | periodo=%s..%s",
        raw if raw is not None else "TODAS",
        empresa if empresa is not None else "TODAS",
        start,
        end,
    )

    result = await get_fuel_volumetry_service().build(
        data_inicial=start,
        data_final=end,
        empresa_codigo=empresa,
    )
    payload = result.as_bloco_compat()
    return {
        "success": True,
        "data": payload,
        "fromCache": result.fromCache,
        "fonte": result.fonte,
        "latencyMs": result.latencyMs,
        "namespace": "executive",
    }
