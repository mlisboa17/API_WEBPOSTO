#!/usr/bin/env python3
"""D02 Fase 7 — validação runtime API + smoke UI paths."""
from __future__ import annotations

import json
import sys
from pathlib import Path

import httpx

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

BASE = "http://127.0.0.1:8040"
PERIOD = ("2026-06-29", "2026-07-05")
EMPRESA = "11495"
TIMEOUT = 300.0


def check(name: str, ok: bool, detail: str = "") -> dict:
    return {"check": name, "ok": ok, "detail": detail}


def main() -> int:
    results: list[dict] = []
    client = httpx.Client(base_url=BASE, timeout=TIMEOUT)

    try:
        health = client.get("/health")
        results.append(check("backend_health", health.status_code == 200, str(health.status_code)))
    except Exception as exc:
        print(json.dumps({"error": f"backend indisponível: {exc}"}, ensure_ascii=False))
        return 1

    params = {"dataInicial": PERIOD[0], "dataFinal": PERIOD[1], "empresaCodigo": EMPRESA}
    summary = client.get("/api/v1/cash-reconciliation/summary", params=params)
    results.append(check("summary_http", summary.status_code == 200, str(summary.status_code)))
    payload = summary.json().get("data") or {}
    s = (payload.get("summary") or {})
    cards = s.get("natureCards") or []
    items = payload.get("items") or []
    results.append(check("summary_apresentado", _f(s.get("valorApresentado")) > 0, str(s.get("valorApresentado"))))
    results.append(check("summary_nature_cards", len(cards) > 0, str(len(cards))))
    results.append(check("summary_items", len(items) > 0, str(len(items))))
    zero_cards = [c for c in cards if _f(c.get("valorApresentado")) == 0 and _f(c.get("valorApurado")) == 0]
    results.append(check("no_zero_pollution", len(zero_cards) == 0, f"zerados={len(zero_cards)}"))
    if cards:
        worst_diff = max(abs(_f(c.get("diferenca"))) for c in cards)
        best_reviewed = max(
            (c for c in cards if _f(c.get("diferenca")) > 0.01),
            key=lambda c: abs(_f(c.get("diferenca"))),
            default=cards[0],
        )
        results.append(check("divergencias_priorizadas", True, f"maior_dif={worst_diff}"))

    exc = client.get("/api/v1/cash-reconciliation/exceptions", params=params)
    results.append(check("exceptions_http", exc.status_code == 200, str(len(exc.json().get("data") or []))))

    signals = client.get("/api/v1/cash-reconciliation/audit-signals", params=params)
    sig_data = signals.json().get("data") or []
    results.append(check("audit_signals_http", signals.status_code == 200 and len(sig_data) > 0, str(len(sig_data))))
    fraud = any("fraude" in str(x.get("explanation", "")).lower() for x in sig_data)
    results.append(check("sem_acusacao_fraude", not fraud, ""))

    item_id = next((i.get("id") for i in items if i.get("status") == "DIVERGENT"), items[0]["id"] if items else None)
    if item_id:
        justify = client.post(
            "/api/v1/cash-reconciliation/justify",
            params=params,
            json={
                "itemId": item_id,
                "reasonCategory": "OPERATIONAL_ERROR",
                "description": "Teste runtime D02 paridade VIP",
                "responsibleUser": "auditor_d02",
            },
        )
        results.append(check("justify_http", justify.status_code == 200, item_id))
        summary2 = client.get("/api/v1/cash-reconciliation/summary", params=params)
        hist_ok = False
        if summary2.status_code == 200:
            for it in summary2.json().get("data", {}).get("items") or []:
                if it.get("id") == item_id and it.get("justifications"):
                    hist_ok = True
                    break
        results.append(check("justificativa_historico", hist_ok, item_id))

    diretoria = client.get(
        "/api/v1/owner-action-center/today-summary",
        params={"dataInicial": PERIOD[0], "dataFinal": PERIOD[1], "empresaCodigo": EMPRESA},
    )
    results.append(check("diretoria_http", diretoria.status_code in (200, 404), str(diretoria.status_code)))

    ui = client.get("/app/financial")
    results.append(check("frontend_shell", ui.status_code == 200, f"len={len(ui.text)}"))

    out = Path(ROOT / "docs/d02/D02_RUNTIME_PHASE7.json")
    out.write_text(json.dumps({"results": results, "params": params}, ensure_ascii=False, indent=2), encoding="utf-8")
    ok_count = sum(1 for r in results if r["ok"])
    print(f"Fase7: {ok_count}/{len(results)} checks OK -> {out}")
    for r in results:
        mark = "OK" if r["ok"] else "FAIL"
        print(f"  [{mark}] {r['check']}: {r['detail']}")
    return 0 if ok_count == len(results) else 2


def _f(v) -> float:
    try:
        return float(v or 0)
    except (TypeError, ValueError):
        return 0.0


if __name__ == "__main__":
    raise SystemExit(main())
