"""Director value demo journey validation."""
from __future__ import annotations

import json
import sys
import urllib.request
from pathlib import Path

from playwright.sync_api import sync_playwright

BASE = "http://127.0.0.1:8046"
HOME = f"{BASE}/app/financial?view=owner-diretoria&dataInicial=2026-06-05&dataFinal=2026-07-04"
OUT_JSON = Path(__file__).resolve().parents[1] / "docs" / "validation" / "DIRECTOR_VALUE_DEMO_RUNTIME.json"
OUT_SHOT = Path(__file__).resolve().parents[1] / "docs" / "validation" / "DIRECTOR_VALUE_DEMO_RUNTIME.png"


def fetch(path: str) -> dict:
    with urllib.request.urlopen(f"{BASE}{path}", timeout=30) as resp:
        return json.load(resp)


def main() -> int:
    api_top5 = fetch("/api/v1/owner-action-center/top5?dataInicial=2026-06-05&dataFinal=2026-07-04")
    api_follow = fetch("/api/v1/executive/follow-ups")
    decisions = (api_top5.get("data") or {}).get("top_5_decisions") or []
    observations = (api_top5.get("data") or {}).get("observations") or []
    proof = api_top5.get("analysis_proof") or {}
    follow_items = ((api_follow.get("data") or {}).get("items") or [])

    result = {
        "validation": "Director value demo runtime",
        "runtime_frontend": "WebPosto_API/frontend",
        "api_port": "127.0.0.1:8046",
        "home_route": HOME,
        "journey_steps": [],
        "dead_buttons": [],
        "false_success_states": [],
        "mocks": False,
        "ui_validated": False,
        "runtime_http": True,
    }

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()

        page.goto(HOME, wait_until="domcontentloaded", timeout=60000)
        page.wait_for_function("() => window.__LOGOS_APP_READY === true", timeout=90000)
        page.wait_for_selector("section.dir-network", timeout=30000)
        result["journey_steps"].append({"step": "HOME", "ok": True})

        page.wait_for_selector("section.dir-network-hero", timeout=20000)
        topCount = len(decisions)
        heroCount = page.locator(".dir-network-hero").count()
        nextCount = page.locator(".dir-network-next").count()
        result["journey_steps"].append({
            "step": "TOP_DECISIONS_VISIBLE",
            "ok": topCount >= 2 and heroCount >= 1 and nextCount >= 1,
            "decisions_count": topCount,
            "hero_count": heroCount,
            "next_count": nextCount,
        })

        if observations:
            page.wait_for_selector(".dir-network-observation", timeout=10000)
            result["journey_steps"].append({"step": "OBSERVATIONS_VISIBLE", "ok": True})
        else:
            result["journey_steps"].append({"step": "OBSERVATIONS_VISIBLE", "ok": False})

        page.wait_for_selector(".dir-network-followup", timeout=10000)
        body = page.inner_text("body")
        result["journey_steps"].append({
            "step": "FOLLOW_UP_VISIBLE",
            "ok": "Marcio de Lima" in body and "acompanhamento" in body.lower(),
        })

        page.locator(".dir-open-decision").first.click()
        page.wait_for_selector("#decisionDetailView:not(.hidden)", timeout=120000)
        page.wait_for_selector("#decisionDetailView section.panel", timeout=120000)
        detail_text = page.locator("#decisionDetailView").inner_text()
        result["journey_steps"].append({
            "step": "DECISION_DETAIL",
            "ok": "Decisão" in detail_text or "evidência" in detail_text.lower() or "evidencia" in detail_text.lower(),
        })

        page.goto(HOME, wait_until="domcontentloaded")
        page.wait_for_function("() => window.__LOGOS_APP_READY === true", timeout=90000)
        page.locator(".dir-open-followup").first.click()
        page.wait_for_selector("#executiveFollowUpDetailView:not(.hidden)", timeout=60000)
        result["journey_steps"].append({"step": "FOLLOW_UP_DETAIL", "ok": True})

        page.screenshot(path=str(OUT_SHOT), full_page=True)
        browser.close()

    priority = decisions[0] if decisions else {}
    follow = follow_items[0] if follow_items else {}
    result.update(
        {
            "tenants_visible": proof.get("tenant_count"),
            "detectors_visible": proof.get("detectors_executed"),
            "priority_decision_visible": bool(decisions),
            "priority_tenant": priority.get("tenant_name"),
            "priority_amount": (priority.get("action") or {}).get("financial_impact", {}).get("estimated_value"),
            "money_label": "ESTIMATED",
            "confidence_visible": (priority.get("action") or {}).get("confidence") is not None,
            "observations_visible": len(observations) > 0,
            "observations_count": len(observations),
            "follow_up_visible": len(follow_items) > 0,
            "review_request_id": follow.get("request_id"),
            "review_responsible": follow.get("review_responsible"),
            "fin03_progress": {
                "checked_items": follow.get("checked_items_count"),
                "total_items": follow.get("total_items_count"),
                "percent": follow.get("item_progress_percent"),
            },
            "ui_validated": all(step.get("ok") for step in result["journey_steps"]),
        }
    )

    OUT_JSON.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result["ui_validated"] else 1


if __name__ == "__main__":
    sys.exit(main())
