"""Endpoints de pista — leitura do cache RAM (<50ms) com fallback histórico D-1.

GET /api/v1/abastecimentos/pendentes
GET /api/v1/abastecimentos/baixados
GET /api/v1/abastecimentos/kpis/resumo
GET /api/v1/abastecimentos?status=...
"""

from __future__ import annotations

import logging
from datetime import date
from typing import Any

from fastapi import APIRouter, Query

from src.services.pista_cache_service import get_pista_cache
from src.services.webposto_pista_service import ListaAbastecimentosResponse
from src.utils.filial_normalizer import resolve_empresa_codigo

LOGGER = logging.getLogger(__name__)

router = APIRouter(
    prefix="/api/v1/abastecimentos",
    tags=["Abastecimentos REST v1"],
)


def _normalize_empresa(
    id_empresa: int | None,
    filial: str | None,
) -> int | None:
    """Aceita idEmpresa numérico, ordinal 1–3 ou slug/nome em `filial`."""
    raw: Any = filial if filial is not None and str(filial).strip() != "" else id_empresa
    resolved = resolve_empresa_codigo(raw)
    LOGGER.info(
        "[Pista & Volumetria] Filial buscada: %s | ID resolvido: %s",
        raw if raw is not None else "TODAS",
        resolved if resolved is not None else "TODAS",
    )
    return resolved


@router.get("/pendentes", response_model=ListaAbastecimentosResponse)
async def abastecimentos_pendentes(
    idEmpresa: int | None = Query(None, description="Código da empresa/filial ou ordinal 1–3"),
    filial: str | None = Query(
        None, description="Alias de filial (Casa Caiada, VIP, TODAS, 001…)"
    ),
    idBico: int | None = Query(None, description="Número físico do bico"),
) -> ListaAbastecimentosResponse:
    """Pista em aberto — cache RAM (worker 30s)."""
    empresa = _normalize_empresa(idEmpresa, filial)
    return await get_pista_cache().response_pendentes(
        id_empresa=empresa,
        id_bico=idBico,
    )


@router.get("/baixados", response_model=ListaAbastecimentosResponse)
async def abastecimentos_baixados(
    idEmpresa: int | None = Query(None, description="Código da empresa/filial ou ordinal 1–3"),
    filial: str | None = Query(
        None, description="Alias de filial (Casa Caiada, VIP, TODAS, 001…)"
    ),
    dataInicio: str | None = Query(None, description="YYYY-MM-DD"),
    dataFim: str | None = Query(None, description="YYYY-MM-DD"),
    pagina: int = Query(1, ge=1),
    limite: int = Query(100, ge=1, le=500),
) -> ListaAbastecimentosResponse:
    """Abastecimentos baixados — 100% cache RAM (sem Quality síncrono no GET)."""
    empresa = _normalize_empresa(idEmpresa, filial)
    hoje = str(date.today())
    start = dataInicio or hoje
    end = dataFim or hoje

    cache = get_pista_cache()
    snap = cache.get_snapshot()
    if snap.data_ref and (start != snap.data_ref or end != snap.data_ref):
        LOGGER.info(
            "pista.baixados RAM-only cache_ref=%s pedido=%s..%s empresa=%s "
            "(sem sync Quality no request path)",
            snap.data_ref,
            start,
            end,
            empresa,
        )

    return await cache.response_baixados(
        id_empresa=empresa,
        data_inicio=start,
        data_fim=end,
        pagina=pagina,
        limite=limite,
    )


@router.get("/kpis/resumo")
async def abastecimentos_kpis_resumo() -> dict[str, Any]:
    """KPIs do dia (ERR-01) — somente RAM (<50ms)."""
    cache = get_pista_cache()
    if not cache.ready:
        import asyncio

        async def _warm() -> None:
            try:
                await cache.run_sync()
            except Exception as exc:
                LOGGER.warning("pista kpis warm-up falhou: %s", exc)

        try:
            asyncio.get_running_loop().create_task(_warm())
        except RuntimeError:
            pass
    return await cache.response_kpis()


@router.get("/cache/status")
async def abastecimentos_cache_status() -> dict[str, Any]:
    """Diagnóstico do worker/cache (ops)."""
    from src.workers.pista_sync_worker import get_pista_sync_worker

    cache = await get_pista_cache().status()
    return {"cache": cache, "worker": get_pista_sync_worker().get_status()}


@router.get("", response_model=ListaAbastecimentosResponse)
async def abastecimentos_por_status(
    status: str = Query("BAIXADO", description="PENDENTE | BAIXADO"),
    idEmpresa: int | None = Query(None),
    filial: str | None = Query(None),
    idBico: int | None = Query(None),
    dataInicio: str | None = Query(None),
    dataFim: str | None = Query(None),
    pagina: int = Query(1, ge=1),
    limite: int = Query(100, ge=1, le=500),
    apenasDisponiveis: bool = Query(False),
) -> ListaAbastecimentosResponse:
    st = (status or "").strip().upper()
    if st in ("PENDENTE", "PENDENTES") or apenasDisponiveis:
        return await abastecimentos_pendentes(
            idEmpresa=idEmpresa,
            filial=filial,
            idBico=idBico,
        )
    return await abastecimentos_baixados(
        idEmpresa=idEmpresa,
        filial=filial,
        dataInicio=dataInicio,
        dataFim=dataFim,
        pagina=pagina,
        limite=limite,
    )
