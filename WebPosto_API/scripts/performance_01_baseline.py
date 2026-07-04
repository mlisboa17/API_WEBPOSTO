"""
PERFORMANCE-01 — Baseline instrumentado (cold start, dados reais).

Uso:
  python scripts/performance_01_baseline.py
"""

from __future__ import annotations

import asyncio
import json
import sys
import uuid
from datetime import date, timedelta
from pathlib import Path
from time import perf_counter

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.core.config import load_core_config
from src.core.webposto_credentials import list_webposto_credentials
from src.gateway.webposto_client import WebPostoClient
from src.services.decision_discovery.detectors.fuel_revenue_detector import FuelRevenueDetector
from src.services.decision_discovery.discovery_engine import DecisionDiscoveryEngine
from src.services.performance.performance_tracer import PerformanceTracer, set_active_tracer
from src.services.tenant_discovery_service import TenantDiscoveryService
from src.utils import permission_cache as perm_cache_module


def _period() -> tuple[str, str]:
    end = date(2026, 7, 3)
    start = date(2026, 6, 26)
    return start.isoformat(), end.isoformat()


def _install_webposto_hooks(tracer: PerformanceTracer) -> None:
    original_call = WebPostoClient.call_endpoint
    original_discover = WebPostoClient.discover_permissions

    async def traced_discover_permissions(self, force: bool = False):
        t0 = perf_counter()
        cache_hit = (
            not force
            and perm_cache_module.is_cache_fresh(self.config.permission_ttl_seconds)
            and all(k in perm_cache_module.get_permissions() for k in WebPostoClient.__dict__.get("ENDPOINTS", {}))
        )
        # ENDPOINTS is module-level
        from src.gateway import webposto_client as wpc

        if not force and perm_cache_module.is_cache_fresh(self.config.permission_ttl_seconds):
            cached = perm_cache_module.get_permissions()
            if all(key in cached for key in wpc.ENDPOINTS):
                cache_hit = True

        result = await original_discover(self, force=force)
        duration_ms = int((perf_counter() - t0) * 1000)
        fp = self._fingerprint(self._api_keys[0]) if self._api_keys else None
        tracer.record(
            "permission_probe",
            duration_ms,
            metadata={
                "credential_fingerprint": fp,
                "cache_hit": cache_hit,
                "cache_miss": not cache_hit,
                "endpoints_checked": len(wpc.ENDPOINTS),
            },
            cache_hit=cache_hit,
            cache_miss=not cache_hit,
            requests_count=0 if cache_hit else len(wpc.ENDPOINTS),
        )
        return result

    async def traced_call_endpoint(self, endpoint_key: str, params=None):
        from src.gateway import webposto_client as wpc

        path = wpc.ENDPOINTS.get(endpoint_key, endpoint_key)
        period_start = (params or {}).get("dataInicial")
        period_end = (params or {}).get("dataFinal")
        empresa = (params or {}).get("empresaCodigo")
        fp = self._fingerprint(self._api_keys[0]) if self._api_keys else None
        t0 = perf_counter()
        response = await original_call(self, endpoint_key, params)
        duration_ms = int((perf_counter() - t0) * 1000)
        tracer.record_webposto_request(
            tenant_id=str(empresa) if empresa is not None else None,
            empresa_codigo=str(empresa) if empresa is not None else None,
            endpoint=path,
            period_start=str(period_start) if period_start else None,
            period_end=str(period_end) if period_end else None,
            duration_ms=duration_ms,
            status=getattr(getattr(response, "error", None), "status", 200) if not response.success else 200,
            credential_fingerprint=fp,
        )
        return response

    WebPostoClient.call_endpoint = traced_call_endpoint
    WebPostoClient.discover_permissions = traced_discover_permissions


async def run_baseline() -> dict:
    analysis_id = str(uuid.uuid4())
    tracer = PerformanceTracer(analysis_id)
    token = set_active_tracer(tracer)
    data_inicial, data_final = _period()

    perm_cache_module.permission_cache["last_check"] = None
    perm_cache_module.permission_cache["permissions"] = {}

    _install_webposto_hooks(tracer)

    total_t0 = perf_counter()

    with tracer.span("config_load"):
        config = load_core_config()

    with tracer.span("credential_discovery"):
        credentials = list_webposto_credentials()

    with tracer.span("tenant_discovery"):
        discovery = await TenantDiscoveryService().discover_tenants()

    engine = DecisionDiscoveryEngine()
    engine.register_detector(FuelRevenueDetector())

    with tracer.span("discovery_engine_setup"):
        pass

    async with tracer.span(
        "multi_tenant_discovery",
        metadata={"tenant_count": len(discovery.tenants_discovered)},
    ):
        result = await engine.discover_all_tenants(
            tenants=discovery.tenants_discovered,
            data_inicial=data_inicial,
            data_final=data_final,
            top_n=5,
            analysis_id=analysis_id,
        )

    with tracer.span("analysis_proof_build"):
        proof = {
            "tenant_count": len([r for r in result.tenant_records if r.status == "ANALYZED"]),
            "tenant_ids": [r.tenant_id for r in result.tenant_records if r.status == "ANALYZED"],
        }

    with tracer.span("http_serialization"):
        payload = json.dumps({"analysis_proof": proof})

    total_ms = int((perf_counter() - total_t0) * 1000)
    tracer.record("total_pipeline", total_ms)

    summary = tracer.summarize()
    summary["period"] = {"start": data_inicial, "end": data_final}
    summary["credentials_detected"] = len(credentials)
    summary["tenants_discovered"] = len(discovery.tenants_discovered)
    summary["tenant_records"] = [
        {
            "tenant_id": r.tenant_id,
            "tenant_name": r.tenant_name,
            "execution_time_ms": r.execution_time_ms,
            "status": r.status,
        }
        for r in result.tenant_records
    ]
    summary["config"] = {
        "permission_ttl_seconds": config.permission_ttl_seconds,
        "timeout_seconds": config.timeout_seconds,
    }

    set_active_tracer(None)
    return summary


def main() -> None:
    summary = asyncio.run(run_baseline())
    out_dir = ROOT / "docs" / "performance"
    out_dir.mkdir(parents=True, exist_ok=True)
    json_path = out_dir / "PERFORMANCE_01_BASELINE_RAW.json"
    json_path.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    print(f"\nSaved: {json_path}")


if __name__ == "__main__":
    main()
