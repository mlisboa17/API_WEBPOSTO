"""Sprint 7 — Análise Financeira Consolidada das Unidades.

GET /api/v1/executive/units-performance
GET /api/v1/executive/units-performance/{unidade_id}
"""

from __future__ import annotations

import logging
from typing import Optional

from fastapi import APIRouter, Query

from src.services.units_performance_service import (
    DEFAULT_LIMITE_ATENCAO,
    DEFAULT_META_MARGEM,
    get_units_performance_service,
)
from src.utils.filial_normalizer import resolve_empresa_codigo

LOGGER = logging.getLogger(__name__)

router = APIRouter(
    prefix="/api/v1/executive",
    tags=["Executive Units Performance"],
)


@router.get("/units-performance")
async def get_units_performance(
    data_inicio: Optional[str] = Query(
        None, alias="data_inicio", pattern=r"^\d{4}-\d{2}-\d{2}$"
    ),
    data_fim: Optional[str] = Query(
        None, alias="data_fim", pattern=r"^\d{4}-\d{2}-\d{2}$"
    ),
    dataInicial: Optional[str] = Query(None, pattern=r"^\d{4}-\d{2}-\d{2}$"),
    dataFinal: Optional[str] = Query(None, pattern=r"^\d{4}-\d{2}-\d{2}$"),
    meta_margem_pct: float = Query(DEFAULT_META_MARGEM, ge=0, le=100),
    limite_atencao_pct: float = Query(DEFAULT_LIMITE_ATENCAO, ge=0, le=100),
) -> dict:
    start = data_inicio or dataInicial
    end = data_fim or dataFinal
    try:
        data = await get_units_performance_service().build_network(
            start,
            end,
            meta_margem_pct=meta_margem_pct,
            limite_atencao_pct=limite_atencao_pct,
        )
        return {"success": True, "data": data, "namespace": "executive"}
    except Exception as exc:
        LOGGER.exception("units-performance falhou: %s", exc)
        return {
            "success": False,
            "data": {
                "success": False,
                "unidades": [],
                "rede": {},
                "mensagem": str(exc),
            },
            "namespace": "executive",
        }


@router.get("/units-performance/{unidade_id}")
async def get_unit_performance_detail(
    unidade_id: int,
    data_inicio: Optional[str] = Query(None, pattern=r"^\d{4}-\d{2}-\d{2}$"),
    data_fim: Optional[str] = Query(None, pattern=r"^\d{4}-\d{2}-\d{2}$"),
    dataInicial: Optional[str] = Query(None, pattern=r"^\d{4}-\d{2}-\d{2}$"),
    dataFinal: Optional[str] = Query(None, pattern=r"^\d{4}-\d{2}-\d{2}$"),
    meta_margem_pct: float = Query(DEFAULT_META_MARGEM, ge=0, le=100),
    limite_atencao_pct: float = Query(DEFAULT_LIMITE_ATENCAO, ge=0, le=100),
) -> dict:
    emp = resolve_empresa_codigo(unidade_id) or unidade_id
    start = data_inicio or dataInicial
    end = data_fim or dataFinal
    try:
        data = await get_units_performance_service().build_unit_detail(
            int(emp),
            start,
            end,
            meta_margem_pct=meta_margem_pct,
            limite_atencao_pct=limite_atencao_pct,
        )
        return {"success": bool(data.get("success", True)), "data": data, "namespace": "executive"}
    except Exception as exc:
        LOGGER.exception("units-performance detail falhou id=%s: %s", unidade_id, exc)
        return {
            "success": False,
            "data": {"success": False, "unidade_id": unidade_id, "mensagem": str(exc)},
            "namespace": "executive",
        }
