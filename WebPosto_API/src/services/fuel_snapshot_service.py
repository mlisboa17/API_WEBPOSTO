from __future__ import annotations

import asyncio
from datetime import datetime
from typing import Any

from src.services.executive_snapshot_service import build_snapshot_key
from src.services.fuel_aggregate import aggregate_fuel_executive_payload
from src.services.fuel_analytics_service import FuelAnalyticsFilters, FuelAnalyticsService
from src.services.fuel_kpi_engine import FuelKpiEngine
from src.services.multiselect_utils import parse_empresa_codigos
from src.services.snapshot_store import SnapshotStore

FUEL_SNAPSHOT_TTL_SECONDS = 15 * 60


class FuelSnapshotService:
    def __init__(
        self,
        fuel_analytics: FuelAnalyticsService,
        fuel_kpi_engine: FuelKpiEngine,
        output_dir: str = "snapshots/fuel",
        ttl_seconds: float = FUEL_SNAPSHOT_TTL_SECONDS,
    ) -> None:
        self._fuel_analytics = fuel_analytics
        self._fuel_kpi_engine = fuel_kpi_engine
        self._store = SnapshotStore(output_dir, ttl_seconds)
        self._running: set[str] = set()
        self._lock = asyncio.Lock()

    def get_snapshot(
        self,
        data_inicial: str,
        data_final: str,
        empresa_codigo: str | int | None = None,
    ) -> dict[str, Any]:
        key = build_snapshot_key(data_inicial, data_final, empresa_codigo)
        stored = self._store.load(key)
        if stored:
            return {
                "fromSnapshot": True,
                "lastUpdated": stored.get("lastUpdated"),
                "fuel": stored.get("fuel"),
                "warnings": stored.get("warnings") or [],
            }
        return {
            "fromSnapshot": False,
            "lastUpdated": None,
            "fuel": None,
            "warnings": [],
        }

    async def collect(
        self,
        data_inicial: str,
        data_final: str,
        empresa_codigo: str | int | None = None,
    ) -> dict[str, Any]:
        warnings: list[str] = []
        empresa_codes = parse_empresa_codigos(empresa_codigo)

        if len(empresa_codes) > 1:
            payloads: list[dict[str, Any]] = []
            for code in empresa_codes:
                filters = FuelAnalyticsFilters(
                    data_inicial=data_inicial,
                    data_final=data_final,
                    empresa_codigo=code,
                )
                resp = await self._fuel_analytics.get_fuel_summary(filters)
                if resp.success and resp.data:
                    payloads.append(resp.data)
                else:
                    warnings.append(f"fuel:{code}: {resp.error or 'falha'}")
            if not payloads:
                fuel_data = None
            else:
                merged = payloads[0]
                for extra in payloads[1:]:
                    for field in ("filiais", "detalhes", "combustiveis"):
                        merged.setdefault(field, [])
                        merged[field] = list(merged.get(field) or []) + list(extra.get(field) or [])
                    merged["litrosTotal"] = float(merged.get("litrosTotal") or 0) + float(extra.get("litrosTotal") or 0)
                merged = aggregate_fuel_executive_payload(merged, empresa_codes)
                merged["kpis"] = self._fuel_kpi_engine.build(merged)
                fuel_data = {"success": True, "data": merged, "error": None}
        else:
            single_code = empresa_codes[0] if empresa_codes else None
            filters = FuelAnalyticsFilters(
                data_inicial=data_inicial,
                data_final=data_final,
                empresa_codigo=single_code,
            )
            resp = await self._fuel_analytics.get_fuel_summary(filters)
            if resp.success:
                payload = resp.data or {}
                payload["kpis"] = self._fuel_kpi_engine.build(payload)
                fuel_data = {"success": True, "data": payload, "error": None}
            else:
                warnings.append(f"fuel: {resp.error or 'falha'}")
                fuel_data = None

        return {
            "lastUpdated": datetime.now().isoformat(timespec="seconds"),
            "fuel": fuel_data,
            "warnings": warnings,
        }

    async def refresh(
        self,
        data_inicial: str,
        data_final: str,
        empresa_codigo: str | int | None = None,
    ) -> dict[str, Any]:
        key = build_snapshot_key(data_inicial, data_final, empresa_codigo)
        async with self._lock:
            if key in self._running:
                return {"status": "already_running", "key": key}
            self._running.add(key)
        try:
            collected = await self.collect(data_inicial, data_final, empresa_codigo)
            if collected.get("fuel") is not None:
                self._store.save(key, collected)
            return {
                "status": "completed",
                "key": key,
                "lastUpdated": collected.get("lastUpdated"),
                "warnings": collected.get("warnings") or [],
            }
        finally:
            async with self._lock:
                self._running.discard(key)

    def start_refresh_background(
        self,
        data_inicial: str,
        data_final: str,
        empresa_codigo: str | int | None = None,
    ) -> dict[str, Any]:
        key = build_snapshot_key(data_inicial, data_final, empresa_codigo)
        if key in self._running:
            return {"status": "already_running", "key": key}

        async def _runner() -> None:
            await self.refresh(data_inicial, data_final, empresa_codigo)

        try:
            loop = asyncio.get_running_loop()
            loop.create_task(_runner())
            return {"status": "started", "key": key}
        except RuntimeError:
            return {"status": "already_running", "key": key}
