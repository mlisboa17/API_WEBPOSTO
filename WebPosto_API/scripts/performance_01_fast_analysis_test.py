#!/usr/bin/env python3
"""Testes runtime PERFORMANCE-01 — Fast Daily Analysis Loop."""

from __future__ import annotations

import asyncio
import json
import time
from datetime import datetime, timedelta
from pathlib import Path

import httpx

BASE = "http://127.0.0.1:8040/api/v1/owner-action-center"
OUT = Path("docs/performance/PERFORMANCE_01_FAST_ANALYSIS_RUNTIME.json")


def period() -> tuple[str, str]:
    end = datetime.now().date()
    start = end - timedelta(days=7)
    return start.isoformat(), end.isoformat()


async def timed_get(client: httpx.AsyncClient, path: str, **params) -> tuple[dict, float]:
    t0 = time.perf_counter()
    r = await client.get(f"{BASE}{path}", params=params, timeout=10.0)
    ms = (time.perf_counter() - t0) * 1000
    r.raise_for_status()
    return r.json(), ms


async def timed_post(client: httpx.AsyncClient, path: str, **params) -> tuple[dict, float]:
    t0 = time.perf_counter()
    r = await client.post(f"{BASE}{path}", params=params, timeout=10.0)
    ms = (time.perf_counter() - t0) * 1000
    r.raise_for_status()
    return r.json(), ms


async def wait_analysis(client: httpx.AsyncClient, analysis_id: str, timeout_s: float = 600) -> dict:
    deadline = time.time() + timeout_s
    last: dict = {}
    while time.time() < deadline:
        r = await client.get(f"{BASE}/analysis/status/{analysis_id}", timeout=10.0)
        if r.status_code == 404:
            await asyncio.sleep(2)
            continue
        last = r.json().get("data") or {}
        if last.get("status") in {"COMPLETED", "PARTIAL", "FAILED"}:
            return last
        await asyncio.sleep(3)
    return last


async def main() -> None:
    start, end = period()
    params = {"dataInicial": start, "dataFinal": end}
    results: dict = {
        "executed_at": datetime.now().isoformat(),
        "period": {"start": start, "end": end},
        "tests": {},
    }

    async with httpx.AsyncClient() as client:
        # TEST A — cold / no snapshot fast response
        current_a, ms_a = await timed_get(client, "/top5", **params)
        results["tests"]["A_first_open"] = {
            "current_analysis_response_ms": round(ms_a, 1),
            "freshness": current_a.get("freshness"),
            "refresh_status": current_a.get("refresh_status"),
            "analysis_id": current_a.get("analysis_id"),
        }

        analysis_id = current_a.get("analysis_id")
        if analysis_id:
            status = await wait_analysis(client, analysis_id)
            results["tests"]["A_first_open"]["final_status"] = status

        metrics = (await client.get(f"{BASE}/analysis/metrics")).json().get("metrics") or {}
        results["metrics_after_a"] = metrics

        # TEST B — second open with snapshot
        current_b, ms_b = await timed_get(client, "/top5", **params)
        results["tests"]["B_second_open"] = {
            "home_first_useful_render_proxy_ms": round(ms_b, 1),
            "current_analysis_response_ms": round(ms_b, 1),
            "freshness": current_b.get("freshness"),
            "last_analysis_at": current_b.get("last_analysis_at"),
            "has_analysis_proof": bool(current_b.get("analysis_proof")),
        }

        # TEST C — stale via force refresh while keeping snapshot visible
        trigger_c, ms_trigger = await timed_post(client, "/analysis/refresh", **params)
        current_c, ms_c = await timed_get(client, "/top5", **params)
        results["tests"]["C_stale_refreshing"] = {
            "trigger_ms": round(ms_trigger, 1),
            "current_ms": round(ms_c, 1),
            "freshness": current_c.get("freshness"),
            "refresh_status": current_c.get("refresh_status"),
            "still_has_proof": bool(current_c.get("analysis_proof")),
            "trigger": trigger_c,
        }
        if trigger_c.get("analysis_id"):
            await wait_analysis(client, trigger_c["analysis_id"])

        # TEST D — duplicate refresh
        t1, _ = await timed_post(client, "/analysis/refresh", **params)
        await asyncio.sleep(0.5)
        t2, ms_d = await timed_post(client, "/analysis/refresh", **params)
        metrics_d = (await client.get(f"{BASE}/analysis/metrics")).json().get("metrics") or {}
        results["tests"]["D_duplicate_refresh"] = {
            "first_analysis_id": t1.get("analysis_id"),
            "second_analysis_id": t2.get("analysis_id"),
            "second_already_running": t2.get("already_running"),
            "trigger_response_ms": round(ms_d, 1),
            "duplicate_analysis_count": metrics_d.get("duplicate_analysis_count"),
        }
        if t1.get("analysis_id"):
            await wait_analysis(client, t1["analysis_id"])

        # TEST E — cache isolation note (empresaCodigo per tenant in proof)
        proof = current_b.get("analysis_proof") or {}
        tenants = proof.get("tenants") or []
        results["tests"]["E_cache_isolation"] = {
            "tenants": [
                {
                    "tenant_id": t.get("tenant_id"),
                    "empresa_codigo": t.get("empresa_codigo"),
                }
                for t in tenants
            ],
        }

        # TEST F — failure (NOT EXECUTED unless injection exists)
        results["tests"]["F_refresh_failure"] = {
            "status": "NOT_EXECUTED",
            "reason": "Sem mecanismo seguro de injeção de falha disponível neste runtime",
        }

        final_metrics = (await client.get(f"{BASE}/analysis/metrics")).json().get("metrics") or {}
        results["final_metrics"] = final_metrics
        results["summary"] = {
            "HOME_FIRST_USEFUL_RENDER_MS": results["tests"]["B_second_open"]["current_analysis_response_ms"],
            "CURRENT_ANALYSIS_RESPONSE_MS": results["tests"]["B_second_open"]["current_analysis_response_ms"],
            "ANALYSIS_TRIGGER_MS": results["tests"]["C_stale_refreshing"]["trigger_ms"],
            "DUPLICATE_ANALYSIS_COUNT": final_metrics.get("duplicate_analysis_count"),
        }

    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(results, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(results["summary"], indent=2))


if __name__ == "__main__":
    asyncio.run(main())
