"""Agendamento noturno da consolidação híbrida — cron fixo 03:00 AM."""

from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timedelta
from typing import Any
from zoneinfo import ZoneInfo

logger = logging.getLogger(__name__)

# Cron Unix equivalente: minuto hora dia mês dia-semana
CRON_EXPR = "0 3 * * *"
CRON_HOUR = 3
CRON_MINUTE = 0
TZ = ZoneInfo("America/Recife")


class DataSyncScheduler:
    """Loop asyncio que dispara DataSyncService.sync_yesterday() às 03:00 AM."""

    def __init__(self) -> None:
        self._task: asyncio.Task | None = None
        self._running = False
        self._last_run_at: datetime | None = None
        self._last_result: dict[str, Any] | None = None
        self._next_run_at: datetime | None = None
        self.enabled = True

    @property
    def cron_expr(self) -> str:
        return CRON_EXPR

    def get_status(self) -> dict[str, Any]:
        return {
            "enabled": self.enabled,
            "cron": CRON_EXPR,
            "timezone": str(TZ),
            "hour": CRON_HOUR,
            "minute": CRON_MINUTE,
            "running_loop": self._task is not None and not self._task.done(),
            "job_running": self._running,
            "next_run_at": self._next_run_at.isoformat() if self._next_run_at else None,
            "last_run_at": self._last_run_at.isoformat() if self._last_run_at else None,
            "last_result": self._last_result,
        }

    def next_run_after(self, from_time: datetime | None = None) -> datetime:
        now = from_time or datetime.now(TZ)
        if now.tzinfo is None:
            now = now.replace(tzinfo=TZ)
        else:
            now = now.astimezone(TZ)
        candidate = now.replace(
            hour=CRON_HOUR, minute=CRON_MINUTE, second=0, microsecond=0
        )
        if candidate <= now:
            candidate = candidate + timedelta(days=1)
        return candidate

    async def start(self) -> None:
        if self._task and not self._task.done():
            return
        self.enabled = True
        self._next_run_at = self.next_run_after()
        self._task = asyncio.create_task(self._loop(), name="data-sync-scheduler-0300")
        logger.info(
            "DataSyncScheduler iniciado cron=%s next=%s",
            CRON_EXPR,
            self._next_run_at.isoformat(),
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

    async def run_now(self) -> dict[str, Any]:
        return await self._execute(trigger="manual")

    async def _loop(self) -> None:
        while self.enabled:
            self._next_run_at = self.next_run_after()
            delay = max(1.0, (self._next_run_at - datetime.now(TZ)).total_seconds())
            logger.info(
                "DataSyncScheduler aguardando %.0fs até %s (cron %s)",
                delay,
                self._next_run_at.isoformat(),
                CRON_EXPR,
            )
            try:
                await asyncio.sleep(delay)
            except asyncio.CancelledError:
                raise
            if not self.enabled:
                break
            # Proteção: só roda se ainda estamos na janela das 03:00 (±2 min)
            now = datetime.now(TZ)
            if now.hour == CRON_HOUR and now.minute <= CRON_MINUTE + 2:
                await self._execute(trigger="scheduler")
            else:
                # drift de sleep longo — recalcula e segue
                logger.warning(
                    "DataSyncScheduler wake fora da janela (%s) — reagendando",
                    now.isoformat(),
                )

    async def _execute(self, trigger: str) -> dict[str, Any]:
        if self._running:
            return {"success": False, "mensagem": "Job já em execução"}
        self._running = True
        started = datetime.now(TZ)
        try:
            from src.services.data_sync_service import get_data_sync_service

            result = await get_data_sync_service().sync_yesterday()
            payload = {
                "success": bool(result.get("success")),
                "trigger": trigger,
                "cron": CRON_EXPR,
                "started_at": started.isoformat(),
                "finished_at": datetime.now(TZ).isoformat(),
                **result,
            }
            self._last_result = payload
            self._last_run_at = datetime.now(TZ)
            logger.info(
                "DataSyncScheduler concluído trigger=%s success=%s",
                trigger,
                payload.get("success"),
            )
            return payload
        except Exception as exc:
            logger.exception("DataSyncScheduler falhou: %s", exc)
            payload = {
                "success": False,
                "trigger": trigger,
                "cron": CRON_EXPR,
                "erro": str(exc),
                "started_at": started.isoformat(),
                "finished_at": datetime.now(TZ).isoformat(),
            }
            self._last_result = payload
            self._last_run_at = datetime.now(TZ)
            return payload
        finally:
            self._running = False
            self._next_run_at = self.next_run_after()


_scheduler: DataSyncScheduler | None = None


def get_data_sync_scheduler() -> DataSyncScheduler:
    global _scheduler
    if _scheduler is None:
        _scheduler = DataSyncScheduler()
    return _scheduler
