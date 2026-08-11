"""FR-01 — endpoint factual FuelingSettlementTrace (sem scoring)."""

from __future__ import annotations

import logging
from typing import Optional

from fastapi import APIRouter, HTTPException, Query

from src.services.fueling_settlement_trace import FuelingSettlementTrace
from src.utils.filial_normalizer import resolve_empresa_codigo

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/api/v1/executive/audit",
    tags=["FR-01 Fueling Settlement Trace"],
)


@router.get("/fueling-settlement-trace")
async def get_fueling_settlement_trace(
    data: str = Query(..., pattern=r"^\d{4}-\d{2}-\d{2}$"),
    vendaCodigo: int = Query(..., ge=1),
    empresaCodigo: Optional[int] = Query(None),
    filial_id: Optional[int] = Query(None),
) -> dict:
    """Reconstrói cadeia factual Abastecimento→Venda→Pagamentos→TEF para uma venda.

    Não calcula score de fraude (FR-02).
    """
    empresa = resolve_empresa_codigo(
        filial_id if filial_id is not None else empresaCodigo
    )
    if empresa is None:
        raise HTTPException(status_code=400, detail="empresaCodigo/filial_id obrigatório")

    from src.services.webposto_pista_service import get_pista_service

    svc = get_pista_service()
    try:
        await svc.coletar_pista_universo(
            id_empresa=int(empresa),
            data_inicio=data,
            data_fim=data,
        )
    except Exception as exc:
        logger.exception("FR-01 coletar falhou: %s", exc)
        raise HTTPException(status_code=502, detail=f"Falha ao coletar pista: {exc}") from exc

    key = (int(empresa), int(vendaCodigo))
    trace = svc.last_settlement_traces.get(key) or svc.last_settlement_traces.get(
        (0, int(vendaCodigo))
    )
    if trace is None:
        raise HTTPException(
            status_code=404,
            detail=f"Trace não encontrado para venda {vendaCodigo} em {data}",
        )
    if not isinstance(trace, FuelingSettlementTrace):
        trace = FuelingSettlementTrace.model_validate(trace)
    return {
        "success": True,
        "fonte": "FR01_FuelingSettlementTrace",
        "legacyScoreNotComputed": True,
        "trace": trace.model_dump(),
    }
