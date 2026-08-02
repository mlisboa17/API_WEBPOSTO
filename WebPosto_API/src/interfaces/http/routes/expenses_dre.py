"""DRE & Despesas Classificadas — GET /api/v1/executive/reports/expenses

Path rápido: snapshots locais + receita pista (D0 RAM / D-1 DB).
"""

from __future__ import annotations

import logging
from datetime import date
from typing import Optional

from fastapi import APIRouter, Query

from src.services.expenses_dre_service import get_expenses_dre_service
from src.utils.filial_normalizer import resolve_empresa_codigo

LOGGER = logging.getLogger(__name__)

router = APIRouter(
    prefix="/api/v1/executive/reports",
    tags=["Executive Expenses DRE"],
)


@router.get("/expenses")
async def get_expenses_dre(
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
        "[DRE & Despesas] Filial buscada: %s | ID resolvido: %s | periodo=%s..%s",
        raw if raw is not None else "TODAS",
        empresa if empresa is not None else "TODAS",
        start,
        end,
    )

    result = await get_expenses_dre_service().build(
        data_inicial=start,
        data_final=end,
        empresa_codigo=empresa,
    )
    return {
        "success": True,
        "data": result.payload,
        "fromCache": result.fromCache,
        "fonte": result.fonte,
        "latencyMs": result.latencyMs,
        "namespace": "executive",
    }
