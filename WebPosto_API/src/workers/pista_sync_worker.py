"""Worker asyncio — sincroniza pista Quality → cache RAM a cada 30s."""

from __future__ import annotations

import asyncio
import logging
from datetime import datetime
from typing import Any
from zoneinfo import ZoneInfo

from src.services.pista_cache_service import PistaCacheService, get_pista_cache

LOGGER = logging.getLogger(__name__)
TZ = ZoneInfo("America/Recife")


class PistaSyncWorker:
    """Loop silencioso: sync Quality → PistaCacheService."""

    def __init__(
        self,
        cache: PistaCacheService | None = None,
        interval_seconds: int = 30,
    ) -> None:
        self._cache = cache or get_pista_cache()
        self.interval_seconds = max(10, int(interval_seconds))
        self._task: asyncio.Task | None = None
        self.enabled = False
        self._running_job = False
        self._last_run_at: datetime | None = None
        self._last_ok = False

    def get_status(self) -> dict[str, Any]:
        return {
            "enabled": self.enabled,
            "interval_seconds": self.interval_seconds,
            "loop_running": self._task is not None and not self._task.done(),
            "job_running": self._running_job,
            "last_run_at": self._last_run_at.isoformat() if self._last_run_at else None,
            "last_ok": self._last_ok,
        }

    async def start(self) -> None:
        if self._task and not self._task.done():
            return
        self.enabled = True
        self._task = asyncio.create_task(self._loop(), name="pista-sync-worker-30s")
        LOGGER.info(
            "PistaSyncWorker iniciado interval=%ss (sync imediato + loop)",
            self.interval_seconds,
        )

    async def stop(self) -> None:
        self.enabled = False
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
            self._task = None
        LOGGER.info("PistaSyncWorker parado")

    async def run_now(self) -> dict[str, Any]:
        snap = await self._execute()
        return {
            "ok": snap.ultima_sincronizacao_iso is not None and not snap.last_error,
            "ultimaSincronizacaoIso": snap.ultima_sincronizacao_iso,
            "totalDia": snap.resumo_dia.totalAbastecimentos,
            "durationMs": snap.last_duration_ms,
            "error": snap.last_error,
        }

    async def _loop(self) -> None:
        # Aguarda discovery/permissões do client (evita envenenar cache com 401 de startup)
        try:
            await asyncio.sleep(12)
        except asyncio.CancelledError:
            raise

        first = True
        while self.enabled:
            try:
                await self._execute(force_permissions=first)
                first = False
            except asyncio.CancelledError:
                raise
            except Exception:
                LOGGER.exception("PistaSyncWorker ciclo com erro inesperado")
            try:
                await asyncio.sleep(self.interval_seconds)
            except asyncio.CancelledError:
                raise

    async def _execute(self, *, force_permissions: bool = False):
        if self._running_job:
            LOGGER.warning("PistaSyncWorker: sync anterior ainda em andamento — skip")
            return self._cache.get_snapshot()
        self._running_job = True
        try:
            snap = await self._cache.run_sync(force_permissions=force_permissions)
            self._last_run_at = datetime.now(TZ)
            self._last_ok = bool(snap.baixados or snap.pendentes)
            # Auditoria de caixas em background (bico × caixa × formas) → cache RAM
            try:
                from src.services.cashier_audit_service import get_cashier_audit_service

                await get_cashier_audit_service().refresh_from_pista()
            except Exception:
                LOGGER.exception("PistaSyncWorker: refresh cashier_audit falhou")
            # Anti-fraude cartão/TEF → cache RAM (GET só lê memória)
            try:
                from src.services.fraud_detection_engine import get_fraud_detection_engine

                await get_fraud_detection_engine().refresh_from_pista()
            except Exception:
                LOGGER.exception("PistaSyncWorker: refresh card_fraud falhou")
            return snap
        finally:
            self._running_job = False


_worker: PistaSyncWorker | None = None


def get_pista_sync_worker() -> PistaSyncWorker:
    global _worker
    if _worker is None:
        from src.infrastructure.config.settings import settings

        _worker = PistaSyncWorker(
            interval_seconds=getattr(settings, "pista_sync_interval_seconds", 30),
        )
    return _worker
