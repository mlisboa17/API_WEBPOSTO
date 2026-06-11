"""Snapshot D05 — Executive Coverage Recovery."""
from __future__ import annotations

from datetime import datetime
from typing import Any

from src.services.executive_coverage_recovery_service import ExecutiveCoverageRecoveryService
from src.services.multiselect_utils import empresa_snapshot_suffix
from src.services.snapshot_store import SnapshotStore

RECOVERY_SNAPSHOT_TTL_SECONDS = 300.0


class ExecutiveCoverageRecoverySnapshotService:
    def __init__(
        self,
        service: ExecutiveCoverageRecoveryService | None = None,
        output_dir: str = "snapshots/executive_coverage_recovery",
        ttl_seconds: float = RECOVERY_SNAPSHOT_TTL_SECONDS,
    ) -> None:
        self._service = service or ExecutiveCoverageRecoveryService()
        self._store = SnapshotStore(output_dir, ttl_seconds)

    @classmethod
    def master_key(cls, data_inicial: str, data_final: str, empresa_codigo: str | int | None) -> str:
        suffix = empresa_snapshot_suffix(empresa_codigo) or "authorized"
        return f"recovery:executive:{data_inicial}:{data_final}:{suffix}"

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
        self._store.save(key, {"lastUpdated": datetime.utcnow().isoformat(), "data": resp.data})
        return resp.data, False, bool(stored)

    async def collect(
        self,
        data_inicial: str,
        data_final: str,
        empresa_codigo: str | int | None,
        payload: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        if payload is None:
            resp = await self._service.build(data_inicial, data_final, empresa_codigo)
            if not resp.success:
                return {"status": "error", "error": resp.error}
            payload = resp.data
        key = self.master_key(data_inicial, data_final, empresa_codigo)
        self._store.save(key, {"lastUpdated": datetime.utcnow().isoformat(), "data": payload})
        return {"status": "ok", "key": key}
