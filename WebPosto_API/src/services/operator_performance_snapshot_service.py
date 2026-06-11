"""Snapshot F03.4 — Operator Performance (TTL 300s, snapshot-first)."""
from __future__ import annotations

import asyncio
from datetime import datetime
from typing import Any

from src.services.multiselect_utils import empresa_snapshot_suffix
from src.services.operator_performance_service import OperatorPerformanceService
from src.services.snapshot_store import SnapshotStore

PERFORMANCE_SNAPSHOT_TTL_SECONDS = 300.0


class OperatorPerformanceSnapshotService:
    def __init__(
        self,
        performance: OperatorPerformanceService | None = None,
        output_dir: str = "snapshots/operator_performance",
        ttl_seconds: float = PERFORMANCE_SNAPSHOT_TTL_SECONDS,
    ) -> None:
        self._perf = performance or OperatorPerformanceService()
        self._store = SnapshotStore(output_dir, ttl_seconds)
        self._running: set[str] = set()
        self._lock = asyncio.Lock()

    @staticmethod
    def _suffix(data_inicial: str, data_final: str, empresa_codigo: str | int | None) -> str:
        return f"{data_inicial}:{data_final}:{empresa_snapshot_suffix(empresa_codigo)}"

    @classmethod
    def key(cls, domain: str, data_inicial: str, data_final: str, empresa_codigo: str | int | None) -> str:
        prefix = {
            "operators": "operator:performance",
            "pdvs": "pdv:performance",
            "turns": "turn:performance",
            "summary": "performance:summary",
        }.get(domain, f"performance:{domain}")
        return f"{prefix}:{cls._suffix(data_inicial, data_final, empresa_codigo)}"

    @classmethod
    def master_key(cls, data_inicial: str, data_final: str, empresa_codigo: str | int | None) -> str:
        return f"performance:all:{cls._suffix(data_inicial, data_final, empresa_codigo)}"

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
                "hit": True,
                "lastUpdated": stored.get("lastUpdated"),
                "ttlSeconds": self._store.ttl_seconds,
                "data": stored.get("data"),
                "snapshotKey": key,
            }
        return {
            "fromSnapshot": False,
            "stale": True,
            "hit": False,
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
                "hit": True,
                "lastUpdated": stored.get("lastUpdated"),
                "ttlSeconds": self._store.ttl_seconds,
                "payload": stored.get("payload"),
                "snapshotKey": key,
            }
        return {
            "fromSnapshot": False,
            "stale": True,
            "hit": False,
            "lastUpdated": None,
            "ttlSeconds": self._store.ttl_seconds,
            "payload": None,
            "snapshotKey": key,
        }

    async def collect(
        self,
        data_inicial: str,
        data_final: str,
        empresa_codigo: str | int | None = None,
        include_windows: bool = True,
    ) -> dict[str, Any]:
        resp = await self._perf.build(data_inicial, data_final, empresa_codigo, include_windows)
        if not resp.success or not resp.data:
            return {"lastUpdated": datetime.now().isoformat(timespec="seconds"), "payload": None, "error": resp.error}

        data = resp.data
        ts = datetime.now().isoformat(timespec="seconds")
        args = (data_inicial, data_final, empresa_codigo)

        slices = {
            "operators": data.get("operators"),
            "pdvs": data.get("pdvs"),
            "turns": data.get("turns"),
            "summary": data.get("summary"),
        }
        for domain, slice_data in slices.items():
            self._store.save(
                self.key(domain, *args),
                {"lastUpdated": ts, "data": slice_data, "snapshotKey": self.key(domain, *args)},
            )

        master = {"lastUpdated": ts, "payload": data, "snapshotKey": self.master_key(*args)}
        self._store.save(self.master_key(*args), master)
        return master

    async def get_or_collect(
        self,
        data_inicial: str,
        data_final: str,
        empresa_codigo: str | int | None = None,
        include_windows: bool = False,
    ) -> tuple[dict[str, Any] | None, bool, bool]:
        master = self.get_master(data_inicial, data_final, empresa_codigo)
        if master.get("payload"):
            if master.get("stale"):
                asyncio.create_task(self.refresh_background(data_inicial, data_final, empresa_codigo, include_windows))
            return master.get("payload"), master.get("stale", False), True

        collected = await self.collect(data_inicial, data_final, empresa_codigo, include_windows)
        return collected.get("payload"), False, False

    async def refresh_background(
        self,
        data_inicial: str,
        data_final: str,
        empresa_codigo: str | int | None = None,
        include_windows: bool = False,
    ) -> None:
        key = self.master_key(data_inicial, data_final, empresa_codigo)
        async with self._lock:
            if key in self._running:
                return
            self._running.add(key)
        try:
            await self.collect(data_inicial, data_final, empresa_codigo, include_windows)
        finally:
            async with self._lock:
                self._running.discard(key)
