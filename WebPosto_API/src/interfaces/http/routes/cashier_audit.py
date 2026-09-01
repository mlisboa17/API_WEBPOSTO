"""Auditoria de Caixas — leitura exclusiva do cache RAM (<50ms).

GET /api/v1/executive/audit/cashier
"""

from __future__ import annotations

import logging
from typing import Optional

from fastapi import APIRouter, Query

from src.services.cashier_audit_service import get_cashier_audit_service
from src.utils.filial_normalizer import resolve_empresa_codigo

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/api/v1/executive/audit",
    tags=["Executive Cashier Audit"],
)


@router.get("/cashier")
async def get_cashier_audit(
    empresaCodigo: Optional[int] = Query(None, description="Filial ou ordinal 1–3"),
    filial: Optional[str] = Query(None, description="Alias (Casa Caiada, VIP, TODAS…)"),
    pagina: int = Query(1, ge=1),
    limite: int = Query(20, ge=1, le=100),
) -> dict:
    """Fechamentos de caixa do dia — 100% memória RAM (worker 30s)."""
    raw = filial if filial is not None and str(filial).strip() else empresaCodigo
    empresa = resolve_empresa_codigo(raw)

    svc = get_cashier_audit_service()
    store = svc.get_store()

    # Nunca bloqueia o GET: warm-up em background se cache ainda vazio
    if not store.fechamentos and not store.gerado_em:
        import asyncio

        async def _warm() -> None:
            try:
                await svc.refresh_from_pista()
            except Exception as exc:
                logger.warning("cashier audit warm-up falhou: %s", exc)

        try:
            loop = asyncio.get_running_loop()
            loop.create_task(_warm())
        except RuntimeError:
            logger.debug("cashier audit warm-up ignorado (sem event loop)")

    payload = svc.response(
        empresa_codigo=empresa,
        pagina=pagina,
        limite=limite,
    )
    return {
        "success": True,
        "data": payload.model_dump(),
        "namespace": "executive",
        "synthetic": False,
        "fromCache": True,
    }
