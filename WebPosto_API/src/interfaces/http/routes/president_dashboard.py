"""Cockpit 30s (Presidente) — leitura exclusiva do cache RAM (<50ms).

GET /api/v1/executive/dashboard/president
"""

from __future__ import annotations

import logging

from fastapi import APIRouter

from src.services.pista_cache_service import get_pista_cache

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/api/v1/executive/dashboard",
    tags=["Executive President Dashboard"],
)


@router.get("/president")
async def get_president_dashboard() -> dict:
    """KPIs do Cockpit 30s — 100% memória RAM (PistaSyncWorker 30s).

    Retorna `totaisDia` enriquecido (faturamentoTotal, volumetriaTotalLitros,
    qtdTotalAbastecimentos) sem qualquer chamada síncrona à Quality/WebPosto.
    """
    cache = get_pista_cache()

    if not cache.ready:
        import asyncio

        async def _warm() -> None:
            try:
                await cache.run_sync()
            except Exception as exc:
                logger.warning("president dashboard warm-up falhou: %s", exc)

        try:
            asyncio.get_running_loop().create_task(_warm())
        except RuntimeError:
            logger.debug("president warm-up ignorado (sem event loop)")

    payload = await cache.response_kpis()
    totais = payload.get("totaisDia") or {}
    return {
        "success": True,
        "namespace": "executive",
        "synthetic": False,
        "fromCache": True,
        "fonte": payload.get("fonte"),
        "ultimaSincronizacaoIso": payload.get("ultimaSincronizacaoIso"),
        "dataRef": payload.get("dataRef"),
        "latencyMs": payload.get("latencyMs", 0.0),
        "totaisDia": {
            "faturamentoTotal": float(totais.get("faturamentoTotal") or 0),
            "volumetriaTotalLitros": float(totais.get("volumetriaTotalLitros") or 0),
            "qtdTotalAbastecimentos": int(totais.get("qtdTotalAbastecimentos") or 0),
            "pvmMedio": float(totais.get("pvmMedio") or 0),
            "valorCartoesDia": float(totais.get("valorCartoesDia") or 0),
            "qtdCartoesDia": int(totais.get("qtdCartoesDia") or 0),
            "alertasCriticosRetencao": int(totais.get("alertasCriticosRetencao") or 0),
            "valorCriticoRetencao": float(totais.get("valorCriticoRetencao") or 0),
        },
        "resumoDia": payload.get("resumoDia"),
        "fraude": payload.get("fraude"),
        "syncing": payload.get("syncing"),
        "syncCount": payload.get("syncCount"),
        "observacoes": payload.get("observacoes") or [],
        "error": payload.get("error"),
    }
