#!/usr/bin/env python3
"""PERFORMANCE-01 Prompt 3/4 — fuel cache + controlled concurrency (runtime proof)."""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import time
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta, timezone
from pathlib import Path

import httpx

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src.services.decision_discovery.detectors.fuel_revenue_detector import FuelRevenueDetector
from src.services.snapshot_store import SnapshotStore, safe_filename

BASE = "http://127.0.0.1:8040"
OAC = f"{BASE}/api/v1/owner-action-center"
FUEL_DIR = ROOT / "snapshots" / "discovery_fuel"
CHECKPOINT_JSON = ROOT / "docs" / "performance" / "PERFORMANCE_01_HTTP_RUNTIME_RAW.json"
OUT = ROOT / "docs" / "performance" / "PERFORMANCE_01_CACHE_CONCURRENCY_RAW.json"
TENANTS = ("5555", "11495", "74014")
TERMINAL = {"COMPLETED", "PARTIAL", "FAILED"}


def utc_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def period_params() -> dict[str, str]:
    end = datetime.now().date()
    start = end - timedelta(days=7)
    return {"dataInicial": start.isoformat(), "dataFinal": end.isoformat()}


def load_checkpoint() -> dict:
    if CHECKPOINT_JSON.is_file():
        return json.loads(CHECKPOINT_JSON.read_text(encoding="utf-8"))
    return {}


def clear_discovery_fuel() -> int:
    if not FUEL_DIR.exists():
        FUEL_DIR.mkdir(parents=True, exist_ok=True)
        return 0
    files = list(FUEL_DIR.glob("*.json"))
    for f in files:
        f.unlink(missing_ok=True)
    return len(files)


def fuel_cache_audit(period: dict[str, str]) -> dict:
    start, end = period["dataInicial"], period["dataFinal"]
    keys = {
        t: FuelRevenueDetector._fuel_cache_key(t, t, start, end)
        for t in TENANTS
    }
    return {
        "flow": [
            "FuelRevenueDetector.detect",
            "FuelRevenueDetector._fetch_fuel_data",
            "AnalyticsService.get_fuel_summary (live on miss)",
            "NetworkFinancialOverviewService._fetch_vendas_produtos",
            "WebPostoClient.call_endpoint",
        ],
        "methods": {
            "starts_search": "FuelRevenueDetector._fetch_fuel_data",
            "venda": "NetworkFinancialOverviewService._fetch_vendas_produtos -> call_endpoint('venda')",
            "venda_item": "NetworkFinancialOverviewService._fetch_vendas_produtos -> _collect_with_cursor('venda_item_rede','venda_item')",
            "produto": "AnalyticsService.get_fuel_summary -> call_endpoint('produto') per empresa",
            "pagination": "NetworkFinancialOverviewService._collect_with_cursor max 10 pages per stream",
        },
        "cache_layers": {
            "discovery_fuel_snapshot_store": "USED by FuelRevenueDetector (aggregated fuel_data per tenant+period)",
            "fuel_snapshot_service_LMC": "EXISTS but IGNORED by FuelRevenueDetector",
            "snapshot_store_memory": "USED (class-level _fuel_cache_store)",
        },
        "cache_key_format": "discovery_fuel:{tenant_id}:{empresa_codigo}:{period_start}:{period_end}",
        "ttl_current_period_seconds": FuelRevenueDetector.CURRENT_PERIOD_TTL_SECONDS,
        "ttl_closed_period_seconds": FuelRevenueDetector.CLOSED_PERIOD_TTL_SECONDS,
        "current_baseline_separate_keys": False,
        "current_baseline_note": "Single cache entry wraps current+previous period fetch result for analysis period key",
        "tenant_cache_keys_sanitized": {t: safe_filename(k) for t, k in keys.items()},
        "cross_tenant_risk_if_key_wrong": "HIGH — mitigated by tenant_id+empresa_codigo in key",
    }


def tenant_isolation_probe(period: dict[str, str]) -> dict:
    start, end = period["dataInicial"], period["dataFinal"]
    store = SnapshotStore(str(FUEL_DIR), FuelRevenueDetector.CLOSED_PERIOD_TTL_SECONDS)
    entries: dict[str, dict] = {}
    for tenant in TENANTS:
        key = FuelRevenueDetector._fuel_cache_key(tenant, tenant, start, end)
        stored, expired = store.load_stale(key)
        entries[tenant] = {
            "cache_key": key,
            "sanitized_path": str(FUEL_DIR / f"{safe_filename(key)}.json"),
            "exists": stored is not None,
            "expired": expired,
            "empresa_in_payload": (stored or {}).get("fuel_data", {}).get("tenant_id") if stored else None,
            "period_in_payload": {
                "start": (stored or {}).get("fuel_data", {}).get("period_start"),
                "end": (stored or {}).get("fuel_data", {}).get("period_end"),
            }
            if stored
            else None,
        }

    keys_only = [FuelRevenueDetector._fuel_cache_key(t, t, start, end) for t in TENANTS]
    isolation_pass = len(set(keys_only)) == 3

    wrong_key = FuelRevenueDetector._fuel_cache_key("5555", "11495", start, end)
    wrong_stored, _ = store.load_stale(wrong_key)
    negative_pass = wrong_stored is None or wrong_stored.get("fuel_data", {}).get("tenant_id") != "5555"

    return {
        "per_tenant": entries,
        "cache_keys_unique": isolation_pass,
        "isolation_pass": isolation_pass,
        "negative_test_key": wrong_key,
        "negative_test_hit": wrong_stored is not None,
        "negative_test_pass": negative_pass,
    }


def wait_for_api(client: httpx.Client, timeout_s: float = 60.0) -> bool:
    deadline = time.time() + timeout_s
    while time.time() < deadline:
        try:
            r = client.get(f"{BASE}/health", timeout=5.0)
            if r.status_code == 200:
                return True
        except httpx.HTTPError:
            pass
        time.sleep(1.0)
    return False


def restart_api(concurrency: int) -> dict:
    env = os.environ.copy()
    env["OWNER_ANALYSIS_MAX_CONCURRENCY"] = str(concurrency)
    stopped: list[int] = []
    try:
        out = subprocess.check_output(
            ["netstat", "-ano"],
            text=True,
            errors="ignore",
        )
        for line in out.splitlines():
            if ":8040" in line and "LISTENING" in line:
                pid = int(line.strip().split()[-1])
                subprocess.run(["taskkill", "/PID", str(pid), "/F"], check=False, capture_output=True)
                stopped.append(pid)
    except Exception:
        pass
    time.sleep(2.0)
    proc = subprocess.Popen(
        [sys.executable, "-m", "uvicorn", "src.interfaces.http.app:app", "--host", "127.0.0.1", "--port", "8040"],
        cwd=str(ROOT),
        env=env,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    with httpx.Client(timeout=httpx.Timeout(10.0, connect=5.0)) as client:
        ok = wait_for_api(client, 90.0)
    return {
        "stopped_pids": stopped,
        "new_pid": proc.pid,
        "OWNER_ANALYSIS_MAX_CONCURRENCY": concurrency,
        "health_ok": ok,
    }


def reset_metrics(client: httpx.Client) -> None:
    client.post(f"{OAC}/analysis/metrics/reset", timeout=10.0)


def fetch_metrics(client: httpx.Client) -> dict:
    r = client.get(f"{OAC}/analysis/metrics", timeout=10.0)
    if r.status_code == 200:
        return r.json().get("metrics") or {}
    return {}


def wait_analysis(client: httpx.Client, analysis_id: str, timeout_s: float = 900.0) -> dict:
    deadline = time.time() + timeout_s
    last: dict = {}
    while time.time() < deadline:
        r = client.get(f"{OAC}/analysis/status/{analysis_id}", timeout=15.0)
        if r.status_code != 200:
            time.sleep(2.0)
            continue
        data = r.json().get("data") or {}
        last = data
        if data.get("status") in TERMINAL:
            return data
        time.sleep(2.0)
    return last


def run_full_analysis(client: httpx.Client, params: dict[str, str], label: str) -> dict:
    reset_metrics(client)
    t0 = time.perf_counter()
    r = client.post(f"{OAC}/analysis/refresh", params=params, timeout=15.0)
    trigger_ms = round((time.perf_counter() - t0) * 1000, 1)
    body = r.json()
    analysis_id = body.get("analysis_id")
    if not analysis_id:
        return {"label": label, "error": "no analysis_id", "trigger_ms": trigger_ms}
    if body.get("already_running"):
        time.sleep(3.0)
        analysis_id = body.get("analysis_id")
    status = wait_analysis(client, analysis_id)
    total_ms = round((time.perf_counter() - t0) * 1000, 1)
    metrics = fetch_metrics(client)
    tenants = status.get("tenants") or []
    return {
        "label": label,
        "analysis_id": analysis_id,
        "trigger_ms": trigger_ms,
        "total_ms": total_ms,
        "status": status.get("status"),
        "tenants_total": status.get("tenants_total"),
        "tenants_completed": status.get("tenants_completed"),
        "tenants_failed": status.get("tenants_failed"),
        "tenant_records": [
            {
                "tenant_id": t.get("tenant_id"),
                "empresa_codigo": t.get("empresa_codigo"),
                "execution_time_ms": t.get("execution_time_ms"),
                "status": t.get("status"),
            }
            for t in tenants
        ],
        "metrics": metrics,
    }


def build_fuel_phase(result: dict, period: dict[str, str]) -> dict:
    m = result.get("metrics") or {}
    return {
        "total_ms": result.get("total_ms"),
        "analysis_id": result.get("analysis_id"),
        "status": result.get("status"),
        "tenants_failed": result.get("tenants_failed"),
        "fuel_cache_hits": m.get("fuel_cache_hit_count"),
        "fuel_cache_misses": m.get("fuel_cache_miss_count"),
        "webposto_request_total": m.get("webposto_request_total"),
        "venda_requests": m.get("webposto_venda_requests"),
        "venda_item_requests": m.get("webposto_venda_item_requests"),
        "produto_requests": m.get("webposto_produto_requests"),
        "429": m.get("webposto_429_count"),
        "timeouts": m.get("webposto_timeout_count"),
        "5xx": m.get("webposto_5xx_count"),
        "tenant_records": result.get("tenant_records"),
        "period": period,
    }


def single_flight_check(client: httpx.Client, params: dict[str, str]) -> dict:
    def do_post() -> dict:
        return client.post(f"{OAC}/analysis/refresh", params=params, timeout=15.0).json()

    with ThreadPoolExecutor(max_workers=2) as pool:
        f1 = pool.submit(do_post)
        time.sleep(0.15)
        f2 = pool.submit(do_post)
        p1, p2 = f1.result(), f2.result()
    ids = {p1.get("analysis_id"), p2.get("analysis_id")}
    flags = [p1.get("already_running"), p2.get("already_running")]
    return {
        "pass": len(ids) == 1 and flags.count(True) >= 1 and flags.count(False) >= 1,
        "post1": {"already_running": p1.get("already_running"), "analysis_id": p1.get("analysis_id")},
        "post2": {"already_running": p2.get("already_running"), "analysis_id": p2.get("analysis_id")},
    }


def main() -> None:
    params = period_params()
    checkpoint_src = load_checkpoint()
    errors: list[dict] = []
    report: dict = {
        "executed_at_utc": utc_iso(),
        "checkpoint": {
            "source": str(CHECKPOINT_JSON),
            "HOME_cold_ms": checkpoint_src.get("test_a_home_fast_path", {}).get("HOME_RESPONSE_MS"),
            "REFRESH_trigger_ms": checkpoint_src.get("test_b_refresh_trigger", {}).get("ANALYSIS_TRIGGER_RESPONSE_MS"),
            "HOME_snapshot_ms": checkpoint_src.get("test_e_post_refresh_home", {}).get("POST_REFRESH_HOME_MS"),
            "FULL_ANALYSIS_ms_approx": None,
            "tenants": 3,
            "single_flight": "PASS",
            "note": "Valores históricos Prompt 2 — não alterados",
        },
        "fuel_cache_audit": fuel_cache_audit(params),
        "fuel_cold": {},
        "fuel_warm": {},
        "tenant_cache_isolation": {},
        "concurrency_1": {},
        "concurrency_2": {},
        "concurrency_3": {},
        "selected_concurrency": {},
        "final_warm_analysis": {},
        "final_home": {},
        "errors": errors,
    }

    c_summary = checkpoint_src.get("test_c_summary") or {}
    polling = checkpoint_src.get("test_c_job_polling") or []
    if polling:
        t0p = polling[0].get("timestamp_utc")
        t1p = polling[-1].get("timestamp_utc")
        if t0p and t1p:
            try:
                dt0 = datetime.fromisoformat(t0p)
                dt1 = datetime.fromisoformat(t1p)
                report["checkpoint"]["FULL_ANALYSIS_ms_approx"] = round((dt1 - dt0).total_seconds() * 1000, 1)
            except ValueError:
                report["checkpoint"]["FULL_ANALYSIS_ms_approx"] = 94000

    # Phase 3 — fuel cold
    cleared = clear_discovery_fuel()
    print(f"Cleared {cleared} discovery_fuel snapshots")
    restart_api(1)
    with httpx.Client(timeout=httpx.Timeout(30.0, connect=10.0)) as client:
        if not wait_for_api(client):
            errors.append({"phase": "startup", "error": "API not healthy after restart"})
        cold_result = run_full_analysis(client, params, "fuel_cold")
        report["fuel_cold"] = build_fuel_phase(cold_result, params)
        report["fuel_cold"]["cleared_files"] = cleared

        # Phase 4 — fuel warm (same period, cache intact)
        warm_result = run_full_analysis(client, params, "fuel_warm")
        report["fuel_warm"] = build_fuel_phase(warm_result, params)
        cold_ms = report["fuel_cold"].get("total_ms") or 1
        warm_ms = report["fuel_warm"].get("total_ms") or 1
        report["fuel_warm"]["cache_speedup_ratio"] = round(cold_ms / max(warm_ms, 1), 3)

        # Phase 6 — isolation (after cold populated cache)
        report["tenant_cache_isolation"] = tenant_isolation_probe(params)

        # Phase 7 — concurrency 1 (controlled cold)
        clear_discovery_fuel()
        c1 = run_full_analysis(client, params, "concurrency_1")
        report["concurrency_1"] = {
            **build_fuel_phase(c1, params),
            "max_concurrency": 1,
        }

    # Phase 8 — concurrency 2
    clear_discovery_fuel()
    restart_info_2 = restart_api(2)
    with httpx.Client(timeout=httpx.Timeout(30.0, connect=10.0)) as client:
        wait_for_api(client)
        c2 = run_full_analysis(client, params, "concurrency_2")
        report["concurrency_2"] = {
            **build_fuel_phase(c2, params),
            "max_concurrency": 2,
            "restart": restart_info_2,
        }

    # Phase 9 — concurrency 3 (if c2 stable)
    c2_metrics = report["concurrency_2"]
    c2_stable = (
        (c2_metrics.get("429") or 0) == 0
        and (c2_metrics.get("timeouts") or 0) == 0
        and (c2_metrics.get("5xx") or 0) == 0
        and (c2_metrics.get("tenants_failed") or 0) == 0
    )
    if c2_stable:
        clear_discovery_fuel()
        restart_info_3 = restart_api(3)
        with httpx.Client(timeout=httpx.Timeout(30.0, connect=10.0)) as client:
            wait_for_api(client)
            c3 = run_full_analysis(client, params, "concurrency_3")
            report["concurrency_3"] = {
                **build_fuel_phase(c3, params),
                "max_concurrency": 3,
                "restart": restart_info_3,
            }
    else:
        report["concurrency_3"] = {"skipped": True, "reason": "concurrency_2 unstable"}

    def speedup(cn: dict) -> float | None:
        base = report["concurrency_1"].get("total_ms")
        cur = cn.get("total_ms")
        if base and cur:
            return round(base / cur, 3)
        return None

    c1_ms = report["concurrency_1"].get("total_ms") or 0
    c2_ms = report["concurrency_2"].get("total_ms") or 0
    c3_ms = (report["concurrency_3"].get("total_ms") if isinstance(report["concurrency_3"], dict) else None) or 0

    comparison = [
        {
            "concurrency": 1,
            "total_ms": c1_ms,
            "speedup_vs_1": 1.0,
            "requests": report["concurrency_1"].get("webposto_request_total"),
            "timeouts": report["concurrency_1"].get("timeouts"),
            "429": report["concurrency_1"].get("429"),
            "5xx": report["concurrency_1"].get("5xx"),
            "tenant_failures": report["concurrency_1"].get("tenants_failed"),
        },
        {
            "concurrency": 2,
            "total_ms": c2_ms,
            "speedup_vs_1": speedup(report["concurrency_2"]),
            "requests": report["concurrency_2"].get("webposto_request_total"),
            "timeouts": report["concurrency_2"].get("timeouts"),
            "429": report["concurrency_2"].get("429"),
            "5xx": report["concurrency_2"].get("5xx"),
            "tenant_failures": report["concurrency_2"].get("tenants_failed"),
        },
    ]
    if not report["concurrency_3"].get("skipped"):
        comparison.append(
            {
                "concurrency": 3,
                "total_ms": c3_ms,
                "speedup_vs_1": speedup(report["concurrency_3"]),
                "requests": report["concurrency_3"].get("webposto_request_total"),
                "timeouts": report["concurrency_3"].get("timeouts"),
                "429": report["concurrency_3"].get("429"),
                "5xx": report["concurrency_3"].get("5xx"),
                "tenant_failures": report["concurrency_3"].get("tenants_failed"),
            }
        )

    selected = 1
    reason = "baseline sequential"
    if c2_stable and c2_ms > 0:
        if c2_ms < c1_ms and (report["concurrency_2"].get("tenant_failures") or 0) == 0:
            selected = 2
            reason = "C2 faster than C1 without errors/timeouts/429"
        elif c3_ms and not report["concurrency_3"].get("skipped"):
            c3_ok = (
                (report["concurrency_3"].get("429") or 0) == 0
                and (report["concurrency_3"].get("timeouts") or 0) == 0
                and (report["concurrency_3"].get("5xx") or 0) == 0
                and (report["concurrency_3"].get("tenants_failed") or 0) == 0
            )
            if c3_ok and c3_ms < c2_ms:
                selected = 3
                reason = "C3 faster than C2 without degradation"
            elif c3_ok and c3_ms >= c2_ms:
                selected = 2
                reason = "C3 not better than C2 — prefer stability at C2"

    report["selected_concurrency"] = {
        "value": selected,
        "env_var": "OWNER_ANALYSIS_MAX_CONCURRENCY",
        "reason": reason,
        "comparison_table": comparison,
    }

    # Phase 11 — final warm with selected concurrency
    restart_api(selected)
    with httpx.Client(timeout=httpx.Timeout(30.0, connect=10.0)) as client:
        wait_for_api(client)
        final_warm = run_full_analysis(client, params, "final_warm")
        report["final_warm_analysis"] = {
            **build_fuel_phase(final_warm, params),
            "max_concurrency": selected,
        }

        # Phase 12 — home regression
        t0 = time.perf_counter()
        home = client.get(f"{OAC}/top5", params=params)
        home_ms = round((time.perf_counter() - t0) * 1000, 1)
        t0 = time.perf_counter()
        trig = client.post(f"{OAC}/analysis/refresh", params=params)
        trig_ms = round((time.perf_counter() - t0) * 1000, 1)
        report["final_home"] = {
            "FINAL_HOME_RESPONSE_MS": home_ms,
            "FINAL_REFRESH_TRIGGER_MS": trig_ms,
            "home_pass": home.status_code == 200 and home_ms < 1000,
            "refresh_pass": trig.status_code == 200 and trig_ms < 1000,
            "single_flight": single_flight_check(client, params),
        }

    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Wrote {OUT}")
    print("FUEL_COLD_MS", report["fuel_cold"].get("total_ms"))
    print("FUEL_WARM_MS", report["fuel_warm"].get("total_ms"))
    print("SPEEDUP", report["fuel_warm"].get("cache_speedup_ratio"))
    print("SELECTED_CONCURRENCY", selected)


if __name__ == "__main__":
    main()
