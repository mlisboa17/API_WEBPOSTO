#!/usr/bin/env python3
"""FIN-02 — validação visual assign (Playwright)."""

from __future__ import annotations

import json
import sys
from pathlib import Path

from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "docs" / "validation" / "FIN_02_UI_ASSIGN_VALIDATION.json"
BASE = "http://127.0.0.1:8040/app/financial"
REQUEST_ID = "d7ff3eae-b846-4bbb-8e7b-1b49841afbf1"
RESPONSIBLE = "Marcio de Lima"


def main() -> int:
    results: dict = {}
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        url = f"{BASE}?view=financial-review-detail&requestId={REQUEST_ID}"
        page.goto(url, wait_until="networkidle", timeout=60000)
        page.wait_for_timeout(3000)

        body = page.inner_text("body")
        status_before = "Aguardando an" in body or "Atribu" in body
        results["detail_loaded"] = "POSTO DOZE FILIAL II" in body
        results["has_assign_button_or_assigned"] = (
            page.locator("#finAssignOpen").count() > 0 or "Marcio de Lima" in body
        )

        if page.locator("#finAssignOpen").count():
            page.locator("#finAssignOpen").click()
            page.wait_for_selector("#finAssignResponsibleName", timeout=5000)
            page.fill("#finAssignResponsibleName", RESPONSIBLE)
            page.locator("#finAssignConfirm").click()
            page.wait_for_function(
                "() => document.body.innerText.includes('Marcio de Lima') && "
                "(document.body.innerText.includes('Atribu') || document.body.innerText.includes('atribu'))",
                timeout=30000,
            )
            results["assign_flow_executed"] = True
        else:
            results["assign_flow_executed"] = False
            results["already_assigned"] = RESPONSIBLE in body

        final_body = page.inner_text("body")
        results["shows_responsible"] = RESPONSIBLE in final_body
        results["shows_assigned_status"] = "Atribu" in final_body
        results["ui_pass"] = results["detail_loaded"] and results["shows_responsible"]
        browser.close()

    OUT.write_text(json.dumps(results, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(results, ensure_ascii=False, indent=2))
    return 0 if results.get("ui_pass") else 1


if __name__ == "__main__":
    sys.exit(main())
