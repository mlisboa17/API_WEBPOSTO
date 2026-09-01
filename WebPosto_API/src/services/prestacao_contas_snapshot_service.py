"""Snapshot F03.4-B — Prestação de Contas (TTL 300s)."""
from __future__ import annotations

import asyncio
from datetime import datetime
from typing import Any

from src.services.multiselect_utils import empresa_snapshot_suffix
from src.services.prestacao_contas_intelligence_service import PrestacaoContasIntelligenceService
from src.services.snapshot_store import SnapshotStore

PRESTACAO_SNAPSHOT_TTL = 300.0


class PrestacaoContasSnapshotService:
    def __init__(
        self,
        service: PrestacaoContasIntelligenceService | None = None,
        output_dir: str = "snapshots/prestacao_contas",
        ttl_seconds: float = PRESTACAO_SNAPSHOT_TTL,
    ) -> None:
        self._svc = service or PrestacaoContasIntelligenceService()
        self._store = SnapshotStore(output_dir, ttl_seconds)
        self._running: set[str] = set()
        self._lock = asyncio.Lock()

    @classmethod
    def master_key(cls, data_inicial: str, data_final: str, empresa_codigo: str | int | None, centro_custo: str | None = None) -> str:
        return f"prestacao:all:{data_inicial}:{data_final}:{empresa_snapshot_suffix(empresa_codigo)}:{(centro_custo or 'todos').upper()}"

    def get_master(
        self,
        data_inicial: str,
        data_final: str,
        empresa_codigo: str | int | None = None,
        centro_custo: str | None = None,
    ) -> dict[str, Any]:
        key = self.master_key(data_inicial, data_final, empresa_codigo, centro_custo)
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
        centro_custo: str | None = None,
    ) -> dict[str, Any]:
        resp = await self._svc.build(data_inicial, data_final, empresa_codigo, centro_custo)
        ts = datetime.now().isoformat(timespec="seconds")
        if not resp.success or not resp.data:
            return {"lastUpdated": ts, "payload": None, "error": resp.error}
        master = {"lastUpdated": ts, "payload": resp.data, "snapshotKey": self.master_key(data_inicial, data_final, empresa_codigo, centro_custo)}
        self._store.save(self.master_key(data_inicial, data_final, empresa_codigo, centro_custo), master)
        return master

    async def get_or_collect(
        self,
        data_inicial: str,
        data_final: str,
        empresa_codigo: str | int | None = None,
        centro_custo: str | None = None,
    ) -> tuple[dict[str, Any] | None, bool, bool]:
        master = self.get_master(data_inicial, data_final, empresa_codigo, centro_custo)
        if master.get("payload"):
            if master.get("stale"):
                asyncio.create_task(self.refresh_background(data_inicial, data_final, empresa_codigo, centro_custo))
            return master.get("payload"), master.get("stale", False), True
        collected = await self.collect(data_inicial, data_final, empresa_codigo, centro_custo)
        return collected.get("payload"), False, False

    async def refresh_background(
        self,
        data_inicial: str,
        data_final: str,
        empresa_codigo: str | int | None = None,
        centro_custo: str | None = None,
    ) -> None:
        key = self.master_key(data_inicial, data_final, empresa_codigo, centro_custo)
        async with self._lock:
            if key in self._running:
                return
            self._running.add(key)
        try:
            await self.collect(data_inicial, data_final, empresa_codigo, centro_custo)
        finally:
            async with self._lock:
                self._running.discard(key)
