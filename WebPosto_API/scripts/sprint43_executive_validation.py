#!/usr/bin/env python3
"""Smoke Sprint 43 — adoção, relatório mensal BVG, radar e homologação de webhook."""

from __future__ import annotations

import argparse
import json
import sys
import urllib.error
import urllib.request
from datetime import date


def _get(url: str, cookie: str | None = None) -> dict:
    headers = {"Accept": "application/json"}
    if cookie:
        headers["Cookie"] = cookie
    request = urllib.request.Request(url, headers=headers)
    with urllib.request.urlopen(request, timeout=15) as response:  # noqa: S310
        return json.loads(response.read().decode("utf-8"))


def _post(url: str, body: dict | None = None, cookie: str | None = None) -> dict:
    headers = {"Content-Type": "application/json", "Accept": "application/json"}
    if cookie:
        headers["Cookie"] = cookie
    payload = json.dumps(body or {}).encode("utf-8")
    request = urllib.request.Request(url, data=payload, headers=headers, method="POST")
    with urllib.request.urlopen(request, timeout=15) as response:  # noqa: S310
        return json.loads(response.read().decode("utf-8"))


def main() -> int:
    parser = argparse.ArgumentParser(description="Smoke Sprint 43 — validação executiva")
    parser.add_argument("--api", default="http://127.0.0.1:8046", help="Base URL da API")
    parser.add_argument("--cookie", default="", help="Cookie access_token (owner/admin para webhook)")
    parser.add_argument("--month", default=date.today().strftime("%Y-%m"), help="Mês YYYY-MM")
    args = parser.parse_args()
    base = args.api.rstrip("/")
    cookie = args.cookie or None
    checks: list[tuple[str, bool, str]] = []

    def record(name: str, ok: bool, detail: str = "") -> None:
        checks.append((name, ok, detail))
        status = "OK" if ok else "FAIL"
        print(f"[{status}] {name}" + (f" — {detail}" if detail else ""))

    try:
        health = _get(f"{base}/api/v1/departmental-governance/health")
        record("departmental_health", health.get("success") is True)
    except urllib.error.URLError as exc:
        record("departmental_health", False, str(exc.reason))
        print(json.dumps({"checks": checks}, ensure_ascii=False, indent=2))
        return 1

    for path, name in (
        (f"/api/v1/departmental-governance/proactive-radar", "proactive_radar"),
        (f"/api/v1/departmental-governance/proactive-notifications", "proactive_notifications"),
        (f"/api/v1/departmental-governance/proactive-value?month={args.month}", "proactive_value"),
        (f"/api/v1/departmental-governance/monthly-business-value-report?month={args.month}", "monthly_bvg_report"),
        (f"/api/v1/departmental-governance/executive-adoption/summary", "adoption_summary"),
        (f"/api/v1/departmental-governance/executive-adoption/block-review", "adoption_block_review"),
    ):
        try:
            payload = _get(f"{base}{path}", cookie=cookie)
            ok = payload.get("success") is True
            detail = ""
            if name == "monthly_bvg_report" and ok:
                data = payload.get("data") or {}
                detail = data.get("reportType", "")
                ok = data.get("governance", {}).get("validatedOnlyInTotals") is True
            record(name, ok, detail)
        except urllib.error.HTTPError as exc:
            record(name, False, f"HTTP {exc.code}")
        except urllib.error.URLError as exc:
            record(name, False, str(exc.reason))

    if cookie:
        try:
            webhook = _post(
                f"{base}/api/v1/departmental-governance/proactive-notifications/webhook-homologation",
                {},
                cookie=cookie,
            )
            data = webhook.get("data") or {}
            record(
                "webhook_homologation",
                webhook.get("success") is True and data.get("containsBusinessData") is False,
                data.get("status", ""),
            )
        except urllib.error.HTTPError as exc:
            record("webhook_homologation", False, f"HTTP {exc.code}")
    else:
        record("webhook_homologation", True, "skipped (sem cookie owner/admin)")

    failed = [name for name, ok, _ in checks if not ok]
    print(json.dumps({"passed": len(checks) - len(failed), "failed": failed}, ensure_ascii=False))
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
