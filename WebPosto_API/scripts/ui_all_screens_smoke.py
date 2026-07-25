#!/usr/bin/env python3
"""Smoke test das telas executivas e departamentais."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUT = ROOT / "docs" / "validation" / "ALL_SCREENS_SMOKE_LATEST.json"

VIEWS = (
    "finance-center", "cash-flow", "cash-operations", "operator-performance",
    "people-intelligence", "people-roi", "operation-roi", "management-action",
    "goals-campaigns", "benchmark", "executive-scorecard", "corporate-hub",
    "executive-decision", "action-center", "cash-reconciliation",
    "owner-diretoria", "executive-follow-up", "executive-follow-up-detail",
    "decision-detail", "executive-copilot", "recommendations", "learning",
    "nfce-intelligence", "lmc-intelligence", "fiscal-intelligence",
    "fiscal-reconciliation", "fuel-governance", "non-fuel-products",
    "president-dashboard", "commercial-execution", "commercial-learning",
    "commercial-copilot", "administration", "executive-workspace",
    "financial-operations-center", "financial-intelligence", "visao-financeira",
    "financial-review-inbox", "financial-review-detail", "tesouraria",
    "produtos-vendidos",
)
OPTIONAL_SNAPSHOT_PREFIXES = (
    "/snapshots/financial/financial_sales_",
    "/snapshots/financial/financial_stock_",
)


def _screen_result(page, name: str) -> dict:
    views = page.locator('[id$="View"]:visible').count()
    headings = page.locator("h1:visible, h2:visible, h3:visible").count()
    return {
        "screen": name,
        "ok": views > 0 or headings > 0,
        "visible_views": views,
        "visible_headings": headings,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--base-url", default="http://127.0.0.1:8040")
    parser.add_argument("--start", default="2026-07-17")
    parser.add_argument("--end", default="2026-07-23")
    parser.add_argument("--output", type=Path, default=DEFAULT_OUT)
    args = parser.parse_args()

    results: list[dict] = []
    console_errors: list[str] = []
    http_errors: list[dict] = []
    current_screen = {"name": "startup"}
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(headless=True)
        page = browser.new_page(viewport={"width": 1440, "height": 900})
        page.on(
            "console",
            lambda message: console_errors.append(message.text)
            if message.type == "error"
            else None,
        )
        page.on(
            "response",
            lambda response: http_errors.append(
                {
                    "screen": current_screen["name"],
                    "status": response.status,
                    "url": response.url,
                }
            )
            if response.status >= 400
            else None,
        )
        for view in VIEWS:
            current_screen["name"] = view
            url = (
                f"{args.base_url}/app/financial?view={view}"
                f"&dataInicial={args.start}&dataFinal={args.end}"
            )
            try:
                page.goto(url, wait_until="domcontentloaded", timeout=30_000)
                page.wait_for_timeout(350)
                results.append(_screen_result(page, view))
            except Exception as exc:  # noqa: BLE001 - evidência do smoke
                results.append({"screen": view, "ok": False, "error": str(exc)})

        page.set_viewport_size({"width": 390, "height": 844})
        current_screen["name"] = "departmental-mobile"
        page.goto(
            f"{args.base_url}/app/departmental",
            wait_until="domcontentloaded",
            timeout=30_000,
        )
        page.locator("#content").wait_for(state="visible", timeout=30_000)
        overflow = page.evaluate(
            "document.documentElement.scrollWidth > document.documentElement.clientWidth"
        )
        mobile = _screen_result(page, "departmental-mobile")
        mobile["horizontal_page_overflow"] = overflow
        mobile["ok"] = mobile["ok"] and not overflow
        results.append(mobile)
        browser.close()

    payload = {
        "total": len(results),
        "passed": sum(item["ok"] for item in results),
        "failed": [item["screen"] for item in results if not item["ok"]],
        "console_errors": console_errors,
        "http_errors": http_errors,
        "optional_snapshot_misses": [
            item
            for item in http_errors
            if item["status"] == 404
            and any(prefix in item["url"] for prefix in OPTIONAL_SNAPSHOT_PREFIXES)
        ],
        "blocking_http_errors": [
            item
            for item in http_errors
            if not (
                item["status"] == 404
                and any(prefix in item["url"] for prefix in OPTIONAL_SNAPSHOT_PREFIXES)
            )
        ],
        "results": results,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    print(json.dumps(payload, ensure_ascii=False, indent=2))
    return 0 if not payload["failed"] and not payload["blocking_http_errors"] else 1


if __name__ == "__main__":
    sys.exit(main())
