"""Snapshot F07.4 — Produtos Vendidos gestão comercial."""
from __future__ import annotations

import asyncio
from datetime import datetime
from typing import Any

from src.services.multiselect_utils import empresa_snapshot_suffix
from src.services.produtos_vendidos_performance_service import ProdutosVendidosPerformanceService
from src.services.snapshot_store import SnapshotStore

NON_FUEL_TTL = 300.0


class NonFuelProductSalesSnapshotService:
    def __init__(
        self,
        service: ProdutosVendidosPerformanceService | None = None,
        output_dir: str = "snapshots/non_fuel_products",
        ttl_seconds: float = NON_FUEL_TTL,
    ) -> None:
        self._service = service or ProdutosVendidosPerformanceService()
        self._store = SnapshotStore(output_dir, ttl_seconds)
        self._running: set[str] = set()
        self._lock = asyncio.Lock()

    @staticmethod
    def _suffix(data_inicial: str, data_final: str, empresa_codigo: str | int | None) -> str:
        return f"{data_inicial}:{data_final}:{empresa_snapshot_suffix(empresa_codigo)}"

    @classmethod
    def master_key(cls, data_inicial: str, data_final: str, empresa_codigo: str | int | None) -> str:
        return f"nonfuel:products:{cls._suffix(data_inicial, data_final, empresa_codigo)}"

    async def get_or_collect(
        self,
        data_inicial: str,
        data_final: str,
        empresa_codigo: str | int | None = None,
    ) -> tuple[dict[str, Any] | None, bool, bool]:
        key = self.master_key(data_inicial, data_final, empresa_codigo)
        stored, expired = self._store.load_stale(key)
        if stored and not expired:
            return stored.get("data"), False, True
        resp = await self._service.build(data_inicial, data_final, empresa_codigo)
        if not resp.success:
            if stored:
                return stored.get("data"), True, True
            return None, False, False
        await self.collect(data_inicial, data_final, empresa_codigo, resp.data)
        return resp.data, False, bool(stored)

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
                    return {"status": "error", "error": resp.error}
                payload = resp.data
            key = self.master_key(data_inicial, data_final, empresa_codigo)
            self._store.save(key, {"lastUpdated": datetime.utcnow().isoformat(), "data": payload})
            return {"status": "ok", "key": key}
        finally:
            self._running.discard(suffix)
