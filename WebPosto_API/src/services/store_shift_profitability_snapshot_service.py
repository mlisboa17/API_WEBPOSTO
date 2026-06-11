"""Snapshot F04.3 — Store & Shift Profitability."""
from __future__ import annotations

import asyncio
from datetime import datetime
from typing import Any

from src.services.multiselect_utils import empresa_snapshot_suffix
from src.services.snapshot_store import SnapshotStore
from src.services.store_shift_profitability_service import StoreShiftProfitabilityService

OPERATION_SNAPSHOT_TTL_SECONDS = 300.0


class StoreShiftProfitabilitySnapshotService:
    def __init__(
        self,
        service: StoreShiftProfitabilityService | None = None,
        output_dir: str = "snapshots/store_shift_profitability",
        ttl_seconds: float = OPERATION_SNAPSHOT_TTL_SECONDS,
    ) -> None:
        self._service = service or StoreShiftProfitabilityService()
        self._store = SnapshotStore(output_dir, ttl_seconds)
        self._running: set[str] = set()
        self._lock = asyncio.Lock()

    @staticmethod
    def _suffix(data_inicial: str, data_final: str, empresa_codigo: str | int | None) -> str:
        return f"{data_inicial}:{data_final}:{empresa_snapshot_suffix(empresa_codigo)}"

    @classmethod
    def master_key(cls, data_inicial: str, data_final: str, empresa_codigo: str | int | None) -> str:
        return f"store:shift:profitability:all:{cls._suffix(data_inicial, data_final, empresa_codigo)}"

    def get_master(
        self,
        data_inicial: str,
        data_final: str,
        empresa_codigo: str | int | None = None,
    ) -> dict[str, Any]:
        key = self.master_key(data_inicial, data_final, empresa_codigo)
        stored, expired = self._store.load_stale(key)
        if stored:
            return {
                "fromSnapshot": True,
                "stale": expired,
                "hit": True,
                "lastUpdated": stored.get("lastUpdated"),
                "payload": stored.get("data"),
            }
        return {"fromSnapshot": False, "stale": True, "hit": False, "payload": None}

    async def get_or_collect(
        self,
        data_inicial: str,
        data_final: str,
        empresa_codigo: str | int | None = None,
    ) -> tuple[dict[str, Any] | None, bool, bool]:
        master = self.get_master(data_inicial, data_final, empresa_codigo)
        if master.get("hit") and not master.get("stale"):
            return master.get("payload"), False, True
        resp = await self._service.build(data_inicial, data_final, empresa_codigo)
        if not resp.success:
            if master.get("payload"):
                return master["payload"], True, True
            return None, False, False
        await self.collect(data_inicial, data_final, empresa_codigo, resp.data)
        return resp.data, False, master.get("hit", False)

    async def collect(
        self,
        data_inicial: str,
        data_final: str,
        empresa_codigo: str | int | None,
        payload: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        suffix = self._suffix(data_inicial, data_final, empresa_codigo)
        if suffix in self._running:
            return {"status": "already_running"}
        async with self._lock:
            if suffix in self._running:
                return {"status": "already_running"}
            self._running.add(suffix)
        try:
            if payload is None:
                resp = await self._service.build(data_inicial, data_final, empresa_codigo)
                if not resp.success:
                    return {"status": "error", "message": str(resp.error)}
                payload = resp.data
            key = self.master_key(data_inicial, data_final, empresa_codigo)
            self._store.save(key, {"data": payload, "lastUpdated": datetime.now().isoformat(timespec="seconds")})
            return {"status": "ok", "key": key}
        finally:
            self._running.discard(suffix)
