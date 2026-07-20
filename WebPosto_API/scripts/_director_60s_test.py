"""One-off director 60-second visual test (measure only)."""
from __future__ import annotations

import json
import sys
import urllib.request
from pathlib import Path

from playwright.sync_api import sync_playwright

BASE = "http://127.0.0.1:8040"
URL = f"{BASE}/app/financial?view=owner-diretoria&dataInicial=2026-06-05&dataFinal=2026-07-04"
OUT = Path(__file__).resolve().parents[1] / "docs" / "validation" / "DIRECTOR_60_SECOND_TEST.json"

QUESTIONS = [
    ("tenants_analyzed", "Quantos postos foram analisados?"),
    ("priority_tenant", "Qual posto precisa da minha atenção?"),
    ("money_involved", "Quanto dinheiro está envolvido?"),
    ("main_problem", "Qual é o principal problema?"),
    ("why_happened", "Por que isso aconteceu?"),
    ("what_to_do", "O que devo fazer agora?"),
    ("already_forwarded", "Existe algo que eu já encaminhei?"),
    ("forwarding_state", "Qual o estado desse encaminhamento?"),
]


def fetch_json(path: str) -> dict:
    with urllib.request.urlopen(f"{BASE}{path}", timeout=30) as resp:
        return json.load(resp)


def score_question(key: str, page_text: str, api: dict) -> str:
    text = page_text.lower()
    top5 = api.get("top5") or {}
    follow = api.get("follow") or {}
    data = (top5.get("data") or {})
    decisions = data.get("top_5_decisions") or []
    observations = data.get("observations") or []
    proof = top5.get("analysis_proof") or {}
    tenants = proof.get("tenants") or []
    follow_items = ((follow.get("data") or {}).get("items") or [])

    if key == "tenants_analyzed":
        if str(len(tenants)) in page_text or "3 postos" in text:
            return "PASS"
        if proof.get("tenant_count"):
            return "PARTIAL"
        return "FAIL"
    if key == "priority_tenant":
        if decisions and any((d.get("tenant_name") or "").lower() in text for d in decisions):
            return "PASS"
        if "priorit" in text or "decis" in text:
            return "PARTIAL"
        return "FAIL"
    if key == "money_involved":
        if "r$" in text or "impacto" in text or "valor" in text:
            return "PARTIAL" if not decisions else "PASS"
        return "FAIL"
    if key == "main_problem":
        if decisions and any((d.get("action") or {}).get("title", "").lower()[:12] in text for d in decisions):
            return "PASS"
        if "observa" in text or "análise" in text or "analise" in text:
            return "PARTIAL"
        return "FAIL"
    if key == "why_happened":
        if "confian" in text or "baseline" in text or "comportamento" in text:
            return "PARTIAL"
        return "FAIL"
    if key == "what_to_do":
        if "abrir decis" in text or "entender" in text:
            return "PARTIAL"
        return "FAIL"
    if key == "already_forwarded":
        if follow_items and ("acompanh" in text or "confer" in text or "solicit" in text):
            return "PARTIAL"
        if follow_items:
            return "FAIL"
        return "FAIL"
    if key == "forwarding_state":
        if follow_items and any((i.get("review_responsible") or "").lower() in text for i in follow_items):
            return "PARTIAL"
        if follow_items and "marcio" in text:
            return "PARTIAL"
        return "FAIL"
    return "FAIL"


def main() -> int:
    api = {
        "top5": fetch_json("/api/v1/owner-action-center/top5?dataInicial=2026-06-05&dataFinal=2026-07-04"),
        "follow": fetch_json("/api/v1/executive/follow-ups"),
    }

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        page.goto(URL, wait_until="domcontentloaded", timeout=60000)
        page.wait_for_timeout(12000)
        try:
            page.wait_for_function("() => window.__LOGOS_APP_READY === true", timeout=60000)
        except Exception:
            pass
        page.wait_for_timeout(3000)
        page_text = page.inner_text("body")
        screenshot_path = Path(__file__).resolve().parents[1] / "docs" / "validation" / "DIRECTOR_60_SECOND_TEST.png"
        page.screenshot(path=str(screenshot_path), full_page=True)
        browser.close()

    results = []
    for key, question in QUESTIONS:
        results.append({
            "id": key,
            "question": question,
            "score": score_question(key, page_text, api),
        })

    payload = {
        "test": "Director 60 second test",
        "url": URL,
        "runtime_frontend": "WebPosto_API/frontend",
        "api_base": BASE,
        "boot_ready": "__LOGOS_APP_READY" in page_text or "Diretoria" in page_text,
        "api_snapshot": {
            "analysis_status": api["top5"].get("analysis_status"),
            "monitoring_state": api["top5"].get("monitoring_state"),
            "decisions_count": len((api["top5"].get("data") or {}).get("top_5_decisions") or []),
            "observations_count": len((api["top5"].get("data") or {}).get("observations") or []),
            "follow_up_count": len(((api["follow"].get("data") or {}).get("items") or [])),
        },
        "questions": results,
        "scores": {
            "PASS": sum(1 for r in results if r["score"] == "PASS"),
            "PARTIAL": sum(1 for r in results if r["score"] == "PARTIAL"),
            "FAIL": sum(1 for r in results if r["score"] == "FAIL"),
        },
    }
    OUT.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(payload, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
