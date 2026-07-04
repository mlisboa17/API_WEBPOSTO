#!/usr/bin/env python3
"""PERFORMANCE-01 — validação HTTP single-flight + fast path."""

from __future__ import annotations

import asyncio
import json
import time
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta, timezone
from pathlib import Path

import httpx

BASE = "http://127.0.0.1:8040"
OAC = f"{BASE}/api/v1/owner-action-center"
OUT = Path("docs/performance/PERFORMANCE_01_SINGLE_FLIGHT_RAW.json")
TERMINAL = {"COMPLETED", "PARTIAL", "FAILED"}


def utc_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def period_params(offset_days: int = 0) -> dict[str, str]:
    end = datetime.now().date() - timedelta(days=offset_days)
    start = end - timedelta(days=7)
    return {"dataInicial": start.isoformat(), "dataFinal": end.isoformat()}


def post_refresh(client: httpx.Client, params: dict[str, str]) -> dict:
    return client.post(f"{OAC}/analysis/refresh", params=params, timeout=15.0).json()


def concurrent_posts(client: httpx.Client, params: dict[str, str], count: int) -> list[dict]:
    def one() -> dict:
        return post_refresh(client, params)

    with ThreadPoolExecutor(max_workers=count) as pool:
        futures = [pool.submit(one) for _ in range(count)]
        return [f.result() for f in futures]


def wait_running_analysis(client: httpx.Client, params: dict[str, str], timeout_s: float = 120.0) -> str | None:
    deadline = time.time() + timeout_s
    while time.time() < deadline:
        body = post_refresh(client, params)
        if body.get("already_running"):
            return body.get("analysis_id")
        aid = body.get("analysis_id")
        if aid:
            status = client.get(f"{OAC}/analysis/status/{aid}", timeout=15.0).json().get("data") or {}
            if status.get("status") in {None, "PENDING", "RUNNING"}:
                return aid
        time.sleep(0.5)
    return None


def wait_terminal(client: httpx.Client, analysis_id: str, timeout_s: float = 900.0) -> dict:
    deadline = time.time() + timeout_s
    last: dict = {}
    while time.time() < deadline:
        r = client.get(f"{OAC}/analysis/status/{analysis_id}", timeout=15.0)
        if r.status_code == 200:
            last = r.json().get("data") or {}
            if last.get("status") in TERMINAL:
                return last
        time.sleep(2)
    return last


def sanitize_top5(payload: dict) -> dict:
    proof = payload.get("analysis_proof") or {}
    return {
        "freshness": payload.get("freshness"),
        "refresh_status": payload.get("refresh_status"),
        "analysis_id": payload.get("analysis_id"),
        "scope_key": payload.get("scope_key"),
        "tenant_count": proof.get("tenant_count"),
        "tenant_ids": proof.get("tenant_ids"),
        "has_analysis_proof": bool(proof.get("tenants") or proof.get("tenant_count")),
    }


def main() -> None:
    params = period_params()
    params_alt = period_params(offset_days=14)
    report: dict = {
        "executed_at_utc": utc_iso(),
        "test_2_posts_same_scope": {},
        "test_5_posts_same_scope": {},
        "test_different_scopes": {},
        "fast_path": {},
        "errors": [],
    }

    with httpx.Client(timeout=httpx.Timeout(30.0, connect=10.0)) as client:
        client.post(f"{OAC}/analysis/metrics/reset")

        running_id = wait_running_analysis(client, params)
        if not running_id:
            t0 = time.perf_counter()
            started = post_refresh(client, params)
            running_id = started.get("analysis_id")
            report["long_running_seed_ms"] = round((time.perf_counter() - t0) * 1000, 1)

        report["seed_analysis_id"] = running_id

        posts2 = concurrent_posts(client, params, 2)
        ids2 = {p.get("analysis_id") for p in posts2}
        report["test_2_posts_same_scope"] = {
            "responses": posts2,
            "unique_analysis_ids": len(ids2),
            "same_analysis_id": len(ids2) == 1,
            "already_running_flags": [p.get("already_running") for p in posts2],
            "pass": len(ids2) == 1 and posts2.count({"already_running": True}) >= 0,
        }
        report["test_2_posts_same_scope"]["pass"] = (
            len(ids2) == 1
            and sum(1 for p in posts2 if p.get("already_running")) >= 1
        )

        posts5 = concurrent_posts(client, params, 5)
        ids5 = {p.get("analysis_id") for p in posts5}
        report["test_5_posts_same_scope"] = {
            "responses": [{"analysis_id": p.get("analysis_id"), "already_running": p.get("already_running")} for p in posts5],
            "unique_analysis_ids": len(ids5),
            "new_jobs_created": sum(1 for p in posts5 if p.get("already_running") is False),
            "pass": len(ids5) == 1 and sum(1 for p in posts5 if p.get("already_running") is False) <= 1,
        }

        client.post(f"{OAC}/analysis/metrics/reset")
        alt_a = post_refresh(client, params_alt)
        alt_b = post_refresh(client, {**params_alt, "empresaCodigo": "5555"})
        report["test_different_scopes"] = {
            "scope_all": {"analysis_id": alt_a.get("analysis_id"), "scope_key": alt_a.get("scope_key")},
            "scope_empresa": {"analysis_id": alt_b.get("analysis_id"), "scope_key": alt_b.get("scope_key")},
            "different_analysis_ids": alt_a.get("analysis_id") != alt_b.get("analysis_id"),
            "pass": alt_a.get("analysis_id") != alt_b.get("analysis_id"),
        }

        if running_id:
            terminal = wait_terminal(client, running_id)
            report["seed_terminal_status"] = terminal.get("status")

        metrics = client.get(f"{OAC}/analysis/metrics").json().get("metrics") or {}
        report["metrics_after_tests"] = {
            "duplicate_analysis_count": metrics.get("duplicate_analysis_count"),
            "analysis_trigger_count": metrics.get("analysis_trigger_count"),
        }

        t0 = time.perf_counter()
        home = client.get(f"{OAC}/top5", params=params)
        home_ms = round((time.perf_counter() - t0) * 1000, 1)
        home_body = home.json()

        t0 = time.perf_counter()
        refresh = client.post(f"{OAC}/analysis/refresh", params=params)
        refresh_ms = round((time.perf_counter() - t0) * 1000, 1)
        refresh_body = refresh.json()

        t0 = time.perf_counter()
        post_home = client.get(f"{OAC}/top5", params=params)
        post_home_ms = round((time.perf_counter() - t0) * 1000, 1)
        post_home_body = post_home.json()

        refresh_aid = refresh_body.get("analysis_id")
        if refresh_body.get("already_running") is False and refresh_aid:
            status = client.get(f"{OAC}/analysis/status/{refresh_aid}", timeout=15.0).json().get("data") or {}
            if status.get("status") not in {"PENDING", "RUNNING"}:
                post_refresh(client, params)
                time.sleep(0.05)
        sf = concurrent_posts(client, params, 2)
        sf_ids = {x.get("analysis_id") for x in sf}
        sf_pass = len(sf_ids) == 1 and sum(1 for x in sf if x.get("already_running")) >= 1
        report["fast_path"] = {
            "HOME_RESPONSE_MS": home_ms,
            "REFRESH_TRIGGER_MS": refresh_ms,
            "POST_REFRESH_HOME_MS": post_home_ms,
            "home": sanitize_top5(home_body),
            "refresh": {
                "analysis_id": refresh_body.get("analysis_id"),
                "already_running": refresh_body.get("already_running"),
                "scope_key": refresh_body.get("scope_key"),
            },
            "post_refresh_home": sanitize_top5(post_home_body),
            "single_flight_recheck": {
                "responses": sf,
                "unique_ids": len(sf_ids),
                "pass": sf_pass,
            },
        }

    report["acceptance"] = {
        "single_flight_2": report["test_2_posts_same_scope"].get("pass"),
        "single_flight_5": report["test_5_posts_same_scope"].get("pass"),
        "different_scopes": report["test_different_scopes"].get("pass"),
        "single_flight_recheck": report["fast_path"]["single_flight_recheck"].get("pass"),
        "home_under_1s": report["fast_path"]["HOME_RESPONSE_MS"] < 1000,
        "refresh_under_1s": report["fast_path"]["REFRESH_TRIGGER_MS"] < 1000,
    }

    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(report["acceptance"], indent=2))


if __name__ == "__main__":
    main()
