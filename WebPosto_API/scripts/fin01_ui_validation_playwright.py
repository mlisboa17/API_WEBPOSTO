#!/usr/bin/env python3
"""FIN-01 — validação visual headless (Playwright)."""

from __future__ import annotations

import json
import sys
from pathlib import Path

from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "docs" / "validation" / "FIN_01_UI_VALIDATION.json"
BASE = "http://127.0.0.1:8040/app/financial"


def main() -> int:
    results: dict = {}
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()

        page.goto(f"{BASE}?view=financial-review-inbox", wait_until="networkidle", timeout=60000)
        page.wait_for_timeout(4000)
        body = page.inner_text("body")
        results["inbox"] = {
            "has_conferencias": "Conferências" in body,
            "has_posto_doze": "POSTO DOZE FILIAL II" in body,
            "has_7951": "7.951" in body or "7951" in body,
            "has_aguardando": "Aguardando an" in body,
            "has_open_button": page.locator(".fin-open-review").count() > 0,
        }

        page.locator(".fin-open-review").first.click()
        page.wait_for_function(
            "document.querySelectorAll('table tbody tr').length >= 13",
            timeout=120000,
        )
        detail_body = page.inner_text("body")
        results["detail"] = {
            "rows": page.locator("table tbody tr").count(),
            "has_posto": "POSTO DOZE FILIAL II" in detail_body,
            "has_responsavel_msg": "aguardando respons" in detail_body.lower()
            or "não atribuído" in detail_body.lower()
            or "nao atribuido" in detail_body.lower(),
            "has_itens_section": "itens para conferir" in detail_body.lower(),
        }
        results["ui_pass"] = all(
            [
                results["inbox"]["has_conferencias"],
                results["inbox"]["has_posto_doze"],
                results["inbox"]["has_7951"],
                results["inbox"]["has_open_button"],
                results["detail"]["rows"] == 13,
                results["detail"]["has_itens_section"],
            ]
        )
        browser.close()

    OUT.write_text(json.dumps(results, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(results, ensure_ascii=False, indent=2))
    return 0 if results.get("ui_pass") else 1


if __name__ == "__main__":
    sys.exit(main())
