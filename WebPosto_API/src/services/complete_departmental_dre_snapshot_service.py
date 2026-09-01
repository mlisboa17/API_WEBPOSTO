"""Snapshot isolado da DRE completa por empresa e período.

Hot-path: RAM + disco com TTL curto (60s). Em miss quente/stale, devolve
payload anterior imediatamente e revalida em background (stale-while-revalidate)
para manter budget HTTP < 1.2s na abertura da tela.
"""
from __future__ import annotations

import asyncio
import logging
import time
from datetime import datetime, timezone
from typing import Any

from src.services.complete_departmental_dre_service import CompleteDepartmentalDreService
from src.services.snapshot_store import SnapshotStore

logger = logging.getLogger(__name__)

# Cache RAM dedicado (além do SnapshotStore) — hit sub-ms
_RAM: dict[str, tuple[float, dict[str, Any]]] = {}
_RAM_TTL_S = 60.0
_REFRESHING: set[str] = set()


def summarize_dre_payload(data: dict[str, Any]) -> dict[str, Any]:
    """Árvore resumida: totais por linha sem evidências/paginação pesadas."""
    slim_lines: list[dict[str, Any]] = []
    for row in data.get("lines") or []:
        if not isinstance(row, dict):
            continue
        slim_lines.append(
            {
                "companyCode": row.get("companyCode"),
                "companyName": row.get("companyName"),
                "department": row.get("department"),
                "revenue": row.get("revenue"),
                "cost": row.get("cost"),
                "grossMargin": row.get("grossMargin"),
                "expenses": row.get("expenses"),
                "operatingResult": row.get("operatingResult"),
                "operatingMarginPct": row.get("operatingMarginPct"),
                "status": row.get("status"),
                "missingEvidence": row.get("missingEvidence") or [],
            }
        )
    totals = {
        "revenue": _sum_money(slim_lines, "revenue"),
        "cost": _sum_money(slim_lines, "cost"),
        "grossMargin": _sum_money(slim_lines, "grossMargin"),
        "expenses": _sum_money(slim_lines, "expenses"),
        "operatingResult": _sum_money(slim_lines, "operatingResult"),
    }
    return {
        "period": data.get("period"),
        "regime": data.get("regime"),
        "regimeLabel": data.get("regimeLabel"),
        "periodLock": data.get("periodLock") or {},
        "lines": slim_lines,
        "totals": totals,
        "allReleased": bool(data.get("allReleased")),
        "consolidatedGenericResult": bool(data.get("consolidatedGenericResult")),
        "summary": True,
    }


def _sum_money(rows: list[dict[str, Any]], key: str) -> str | None:
    total = 0.0
    seen = False
    for row in rows:
        raw = row.get(key)
        if raw in (None, ""):
            continue
        try:
            total += float(raw)
            seen = True
        except (TypeError, ValueError):
            continue
    if not seen:
        return None
    return f"{total:.2f}"


class CompleteDepartmentalDreSnapshotService:
    def __init__(
        self,
        service: CompleteDepartmentalDreService,
        output_dir: str = "snapshots/complete_departmental_dre",
        ttl_seconds: float = 60.0,
    ) -> None:
        self._service = service
        self._store = SnapshotStore(output_dir, ttl_seconds)
        self._ttl = ttl_seconds

    @staticmethod
    def key(start: str, end: str, company_code: int | None, regime: str = "competencia") -> str:
        return f"complete-dre:v3:{start}:{end}:{company_code or 'network'}:{regime or 'competencia'}"

    def _ram_get(self, key: str) -> dict[str, Any] | None:
        hit = _RAM.get(key)
        if not hit:
            return None
        ts, data = hit
        if (time.monotonic() - ts) > _RAM_TTL_S:
            return None
        return data

    def _ram_set(self, key: str, data: dict[str, Any]) -> None:
        _RAM[key] = (time.monotonic(), data)

    async def get_or_collect(
        self,
        start: str,
        end: str,
        company_code: int | None = None,
        *,
        force_refresh: bool = False,
        regime: str = "competencia",
    ) -> tuple[dict[str, Any], bool, bool]:
        from src.services.dre_regime import normalize_regime

        regime_norm = normalize_regime(regime)
        key = self.key(start, end, company_code, regime_norm)

        if not force_refresh:
            ram = self._ram_get(key)
            if ram is not None:
                return ram, False, True

        stored, expired = self._store.load_stale(key)
        if stored and not force_refresh:
            data = stored["data"]
            self._ram_set(key, data)
            if expired:
                self._schedule_refresh(key, start, end, company_code, regime_norm)
                return data, True, True
            return data, False, True

        from src.services.webposto.offline_mode import (
            WebPostoOfflineBlocked,
            webposto_offline_mode,
        )

        if webposto_offline_mode():
            if stored:
                data = stored["data"]
                self._ram_set(key, data)
                return data, True, True
            raise WebPostoOfflineBlocked("DRE completa sem snapshot local")

        try:
            data = await self._service.build(start, end, company_code, regime=regime_norm)
        except Exception:
            if stored:
                logger.exception("DRE rebuild falhou — servindo snapshot stale key=%s", key)
                return stored["data"], True, True
            raise

        payload = {"lastUpdated": datetime.now(timezone.utc).isoformat(), "data": data}
        self._store.save(key, payload)
        self._ram_set(key, data)
        return data, False, False

    def _schedule_refresh(
        self,
        key: str,
        start: str,
        end: str,
        company_code: int | None,
        regime: str = "competencia",
    ) -> None:
        if key in _REFRESHING:
            return
        from src.services.webposto.offline_mode import webposto_offline_mode

        if webposto_offline_mode():
            return
        _REFRESHING.add(key)

        async def _run() -> None:
            try:
                data = await self._service.build(start, end, company_code, regime=regime)
                self._store.save(
                    key,
                    {"lastUpdated": datetime.now(timezone.utc).isoformat(), "data": data},
                )
                self._ram_set(key, data)
                logger.info("DRE revalidada em background key=%s", key)
            except Exception:
                logger.exception("DRE background refresh falhou key=%s", key)
            finally:
                _REFRESHING.discard(key)

        try:
            loop = asyncio.get_running_loop()
            loop.create_task(_run())
        except RuntimeError:
            _REFRESHING.discard(key)
