"""Snapshot F03 — Cash Operations (TTL 300s, stale-while-revalidate)."""
from __future__ import annotations

import asyncio
from datetime import datetime
from typing import Any

from src.services.cash_operations_service import CashOperationsService
from src.services.multiselect_utils import empresa_snapshot_suffix
from src.services.snapshot_store import SnapshotStore

CASH_OPERATIONS_SNAPSHOT_TTL_SECONDS = 300.0

SNAPSHOT_KEYS = ("alerts", "risk", "operators", "pdvs", "turns", "summary")


class CashOperationsSnapshotService:
    def __init__(
        self,
        operations: CashOperationsService | None = None,
        output_dir: str = "snapshots/cash_operations",
        ttl_seconds: float = CASH_OPERATIONS_SNAPSHOT_TTL_SECONDS,
    ) -> None:
        self._ops = operations or CashOperationsService()
        self._store = SnapshotStore(output_dir, ttl_seconds)
        self._running: set[str] = set()
        self._lock = asyncio.Lock()

    @staticmethod
    def _suffix(data_inicial: str, data_final: str, empresa_codigo: str | int | None) -> str:
        return f"{data_inicial}:{data_final}:{empresa_snapshot_suffix(empresa_codigo)}"

    @classmethod
    def key(cls, domain: str, data_inicial: str, data_final: str, empresa_codigo: str | int | None) -> str:
        return f"cash:{domain}:{cls._suffix(data_inicial, data_final, empresa_codigo)}"

    @classmethod
    def master_key(cls, data_inicial: str, data_final: str, empresa_codigo: str | int | None) -> str:
        return f"cash:operations:all:{cls._suffix(data_inicial, data_final, empresa_codigo)}"

    def get_slice(
        self,
        domain: str,
        data_inicial: str,
        data_final: str,
        empresa_codigo: str | int | None = None,
    ) -> dict[str, Any]:
        key = self.key(domain, data_inicial, data_final, empresa_codigo)
        stored, expired = self._store.load_stale(key)
        if stored:
            return {
                "fromSnapshot": True,
                "stale": expired,
                "lastUpdated": stored.get("lastUpdated"),
                "ttlSeconds": self._store.ttl_seconds,
                "data": stored.get("data"),
                "snapshotKey": key,
            }
        return {
            "fromSnapshot": False,
            "stale": True,
            "lastUpdated": None,
            "ttlSeconds": self._store.ttl_seconds,
            "data": None,
            "snapshotKey": key,
        }

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
                "lastUpdated": stored.get("lastUpdated"),
                "ttlSeconds": self._store.ttl_seconds,
                "operations": stored.get("operations"),
                "snapshotKey": key,
            }
        return {
            "fromSnapshot": False,
            "stale": True,
            "lastUpdated": None,
            "ttlSeconds": self._store.ttl_seconds,
            "operations": None,
            "snapshotKey": key,
        }

    async def collect(
        self,
        data_inicial: str,
        data_final: str,
        empresa_codigo: str | int | None = None,
    ) -> dict[str, Any]:
        resp = await self._ops.build(data_inicial, data_final, empresa_codigo)
        if not resp.success or not resp.data:
            return {
                "lastUpdated": datetime.now().isoformat(timespec="seconds"),
                "operations": None,
                "error": resp.error,
            }

        data = resp.data
        ts = datetime.now().isoformat(timespec="seconds")
        suffix_args = (data_inicial, data_final, empresa_codigo)

        slices = {
            "summary": data.get("summary"),
            "alerts": data.get("alerts"),
            "risk": data.get("riskScore"),
            "operators": data.get("operators"),
            "pdvs": data.get("pdvs"),
            "turns": data.get("turns"),
        }
        for domain, slice_data in slices.items():
            self._store.save(
                self.key(domain, *suffix_args),
                {"lastUpdated": ts, "data": slice_data, "snapshotKey": self.key(domain, *suffix_args)},
            )

        master = {
            "lastUpdated": ts,
            "operations": data,
            "snapshotKey": self.master_key(*suffix_args),
        }
        self._store.save(self.master_key(*suffix_args), master)
        return master

    async def get_or_collect(
        self,
        data_inicial: str,
        data_final: str,
        empresa_codigo: str | int | None = None,
    ) -> tuple[dict[str, Any] | None, bool]:
        """Retorna payload e flag stale; dispara refresh se expirado."""
        master = self.get_master(data_inicial, data_final, empresa_codigo)
        stale = master.get("stale", True)
        if master.get("operations"):
            if stale:
                asyncio.create_task(self.refresh_background(data_inicial, data_final, empresa_codigo))
            return master.get("operations"), stale

        collected = await self.collect(data_inicial, data_final, empresa_codigo)
        return collected.get("operations"), False

    async def refresh_background(
        self,
        data_inicial: str,
        data_final: str,
        empresa_codigo: str | int | None = None,
    ) -> None:
        key = self.master_key(data_inicial, data_final, empresa_codigo)
        async with self._lock:
            if key in self._running:
                return
            self._running.add(key)
        try:
            await self.collect(data_inicial, data_final, empresa_codigo)
        finally:
            async with self._lock:
                self._running.discard(key)
