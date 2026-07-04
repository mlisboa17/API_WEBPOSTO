#!/usr/bin/env python3
"""PERFORMANCE-01 — HTTP runtime validation A/B/C/D/E."""

from __future__ import annotations

import json
import time
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta, timezone
from pathlib import Path

import httpx

BASE = "http://127.0.0.1:8040"
OAC = f"{BASE}/api/v1/owner-action-center"
OUT = Path("docs/performance/PERFORMANCE_01_HTTP_RUNTIME_RAW.json")


def utc_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def period_params() -> dict[str, str]:
    end = datetime.now().date()
    start = end - timedelta(days=7)
    return {"dataInicial": start.isoformat(), "dataFinal": end.isoformat()}


def sanitize_top5(payload: dict) -> dict:
    proof = payload.get("analysis_proof") or {}
    return {
        "success": payload.get("success"),
        "freshness": payload.get("freshness"),
        "refresh_status": payload.get("refresh_status"),
        "monitoring_state": payload.get("monitoring_state"),
        "analysis_status": payload.get("analysis_status"),
        "analysis_id": payload.get("analysis_id"),
        "last_completed_analysis_id": payload.get("last_completed_analysis_id"),
        "last_analysis_at": payload.get("last_analysis_at"),
        "snapshot_age_seconds": payload.get("snapshot_age_seconds"),
        "scope_key": payload.get("scope_key"),
        "coverage": payload.get("coverage"),
        "tenant_count": proof.get("tenant_count"),
        "tenant_ids": proof.get("tenant_ids"),
        "tenants": [
            {
                "tenant_id": t.get("tenant_id"),
                "empresa_codigo": t.get("empresa_codigo"),
                "credential_alias": t.get("credential_alias"),
                "status": t.get("status"),
            }
            for t in (proof.get("tenants") or [])
        ],
        "detectors_executed": proof.get("detectors_executed"),
        "decisions_count": (payload.get("data") or {}).get("total_decisions"),
        "observations_count": (payload.get("data") or {}).get("total_observations"),
        "has_sufficient_data": (payload.get("data") or {}).get("has_sufficient_data"),
    }


def main() -> None:
    params = period_params()
    errors: list[dict] = []
    report: dict = {
        "executed_at_utc": utc_iso(),
        "api_process": {},
        "test_a_home_fast_path": {},
        "test_b_refresh_trigger": {},
        "test_c_job_polling": [],
        "test_d_single_flight": {},
        "test_e_post_refresh_home": {},
        "errors": errors,
        "acceptance": {},
    }

    with httpx.Client(timeout=httpx.Timeout(15.0, connect=5.0)) as client:
        health_t0 = time.perf_counter()
        health = client.get(f"{BASE}/health")
        report["api_process"] = {
            "health_status": health.status_code,
            "health_ms": round((time.perf_counter() - health_t0) * 1000, 1),
            "base_url": BASE,
        }

        # TEST A
        t0 = time.perf_counter()
        r_a = client.get(f"{OAC}/top5", params=params)
        home_ms = round((time.perf_counter() - t0) * 1000, 1)
        body_a = r_a.json() if r_a.headers.get("content-type", "").startswith("application/json") else {}
        sanitized_a = sanitize_top5(body_a)
        report["test_a_home_fast_path"] = {
            "timestamp_utc": utc_iso(),
            "http_status": r_a.status_code,
            "HOME_RESPONSE_MS": home_ms,
            "payload": sanitized_a,
            "pass": r_a.status_code == 200 and home_ms < 1000,
        }

        # TEST B
        t0 = time.perf_counter()
        r_b = client.post(f"{OAC}/analysis/refresh", params=params)
        trigger_ms = round((time.perf_counter() - t0) * 1000, 1)
        body_b = r_b.json()
        refresh_analysis_id = body_b.get("analysis_id")
        report["test_b_refresh_trigger"] = {
            "timestamp_utc": utc_iso(),
            "http_status": r_b.status_code,
            "ANALYSIS_TRIGGER_RESPONSE_MS": trigger_ms,
            "analysis_id": refresh_analysis_id,
            "refresh_status": body_b.get("refresh_status"),
            "already_running": body_b.get("already_running"),
            "scope_key": body_b.get("scope_key"),
            "reason": body_b.get("reason"),
            "pass": r_b.status_code == 200 and trigger_ms < 1000,
        }

        # TEST C — polling
        terminal = {"COMPLETED", "PARTIAL", "FAILED"}
        final_status: dict | None = None
        callback_mismatch = False
        naive_aware = False
        if refresh_analysis_id:
            deadline = time.time() + 900
            while time.time() < deadline:
                t_poll = time.perf_counter()
                try:
                    r_c = client.get(f"{OAC}/analysis/status/{refresh_analysis_id}")
                    poll_ms = round((time.perf_counter() - t_poll) * 1000, 1)
                    if r_c.status_code == 200:
                        data = r_c.json().get("data") or {}
                        entry = {
                            "timestamp_utc": utc_iso(),
                            "http_status": r_c.status_code,
                            "poll_ms": poll_ms,
                            "status": data.get("status"),
                            "tenants_total": data.get("tenants_total"),
                            "tenants_completed": data.get("tenants_completed"),
                            "tenants_failed": data.get("tenants_failed"),
                            "current_detector": data.get("current_detector"),
                            "progress_message": data.get("progress_message"),
                            "error": data.get("error"),
                        }
                        report["test_c_job_polling"].append(entry)
                        err = str(data.get("error") or "")
                        if "takes 1 positional argument but 3 were given" in err:
                            callback_mismatch = True
                        if "offset-naive and offset-aware" in err:
                            naive_aware = True
                        if data.get("status") in terminal:
                            final_status = data
                            break
                    else:
                        report["test_c_job_polling"].append(
                            {
                                "timestamp_utc": utc_iso(),
                                "http_status": r_c.status_code,
                                "body": r_c.text[:300],
                            }
                        )
                except Exception as exc:
                    errors.append({"phase": "test_c", "error": str(exc)[:300]})
                    break
                time.sleep(2)

        tenants_total = (final_status or {}).get("tenants_total")
        tenants_completed = (final_status or {}).get("tenants_completed")
        tenants_failed = (final_status or {}).get("tenants_failed")
        refresh_final = (final_status or {}).get("status")
        test_c_pass = (
            final_status is not None
            and refresh_final in terminal
            and not callback_mismatch
            and not naive_aware
            and (tenants_total != 3 or tenants_completed == 3)
        )
        report["test_c_summary"] = {
            "tenants_total": tenants_total,
            "tenants_completed_final": tenants_completed,
            "tenants_failed_final": tenants_failed,
            "refresh_final_status": refresh_final,
            "callback_mismatch": callback_mismatch,
            "naive_aware": naive_aware,
            "pass": test_c_pass,
        }

        # TEST D — only if B didn't structural fail immediately
        scope_key_b = body_b.get("scope_key")
        test_d_pass = False
        post1 = post2 = {}
        if report["test_b_refresh_trigger"].get("pass"):
            def do_post() -> tuple[float, dict]:
                t = time.perf_counter()
                resp = client.post(f"{OAC}/analysis/refresh", params=params)
                ms = round((time.perf_counter() - t) * 1000, 1)
                return ms, resp.json()

            with ThreadPoolExecutor(max_workers=2) as pool:
                f1 = pool.submit(do_post)
                time.sleep(0.15)
                f2 = pool.submit(do_post)
                ms1, post1 = f1.result()
                ms2, post2 = f2.result()

            same_scope = post1.get("scope_key") == post2.get("scope_key") == scope_key_b
            ids = {post1.get("analysis_id"), post2.get("analysis_id")}
            running_flags = [post1.get("already_running"), post2.get("already_running")]
            test_d_pass = (
                same_scope
                and len(ids) == 1
                and running_flags.count(True) >= 1
                and running_flags.count(False) >= 1
            )
            report["test_d_single_flight"] = {
                "timestamp_utc": utc_iso(),
                "post1_ms": ms1,
                "post2_ms": ms2,
                "post1": {
                    "analysis_id": post1.get("analysis_id"),
                    "already_running": post1.get("already_running"),
                    "scope_key": post1.get("scope_key"),
                    "refresh_status": post1.get("refresh_status"),
                },
                "post2": {
                    "analysis_id": post2.get("analysis_id"),
                    "already_running": post2.get("already_running"),
                    "scope_key": post2.get("scope_key"),
                    "refresh_status": post2.get("refresh_status"),
                },
                "same_scope_key": same_scope,
                "unique_analysis_ids": len(ids),
                "pass": test_d_pass,
            }
        else:
            report["test_d_single_flight"] = {"skipped": True, "reason": "test_b_failed"}

        # TEST E — post refresh home
        t0 = time.perf_counter()
        r_e = client.get(f"{OAC}/top5", params=params)
        post_refresh_ms = round((time.perf_counter() - t0) * 1000, 1)
        body_e = r_e.json()
        sanitized_e = sanitize_top5(body_e)
        snapshot_used = (
            r_e.status_code == 200
            and post_refresh_ms < 1000
            and sanitized_e.get("freshness") in {"FRESH", "STALE", "STALE_REFRESHING"}
            and bool(sanitized_e.get("analysis_id") or sanitized_e.get("last_completed_analysis_id"))
        )
        report["test_e_post_refresh_home"] = {
            "timestamp_utc": utc_iso(),
            "http_status": r_e.status_code,
            "POST_REFRESH_HOME_MS": post_refresh_ms,
            "payload": sanitized_e,
            "snapshot_used": snapshot_used,
            "pass": post_refresh_ms < 1000 and r_e.status_code == 200,
        }

        metrics = client.get(f"{OAC}/analysis/metrics")
        if metrics.status_code == 200:
            report["runtime_metrics"] = metrics.json().get("metrics")

    report["acceptance"] = {
        "home_under_1s": report["test_a_home_fast_path"].get("pass"),
        "trigger_under_1s": report["test_b_refresh_trigger"].get("pass"),
        "background_job_terminal": test_c_pass,
        "single_flight": test_d_pass if report["test_b_refresh_trigger"].get("pass") else None,
        "post_refresh_snapshot": snapshot_used,
    }

    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(report["acceptance"], indent=2))
    print("HOME_MS", report["test_a_home_fast_path"].get("HOME_RESPONSE_MS"))
    print("TRIGGER_MS", report["test_b_refresh_trigger"].get("ANALYSIS_TRIGGER_RESPONSE_MS"))
    print("POST_REFRESH_MS", report["test_e_post_refresh_home"].get("POST_REFRESH_HOME_MS"))
    print("FINAL_STATUS", report.get("test_c_summary"))


if __name__ == "__main__":
    main()
