#!/usr/bin/env python3
"""Financial Area Recovery — QA gate investigativo (somente leitura)."""
from __future__ import annotations

import json
import urllib.error
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CLIENT = ROOT / "src" / "gateway" / "webposto_client.py"

REPORTS = [
    "ENDPOINT_MESSAGE_SOURCE_REPORT.md",
    "FINANCIAL_ROUTE_RESOLUTION_REPORT.md",
    "BACKEND_ENDPOINT_AUDIT_REPORT.md",
    "SNAPSHOT_GUARD_AUDIT_REPORT.md",
    "UX_REGRESSION_REPORT.md",
    "FINANCIAL_NAVIGATION_MAP_REPORT.md",
    "FINANCIAL_RUNTIME_TRACE_REPORT.md",
    "FINANCIAL_FIX_PROPOSAL_REPORT.md",
    "FINANCIAL_QA_REPORT.md",
    "FINANCIAL_AREA_RECOVERY_MASTER_REPORT.md",
]

BASE = "http://127.0.0.1:8050"
QUERY = "dataInicial=2026-06-01&dataFinal=2026-06-07"


def fetch_json(path: str) -> dict:
    req = urllib.request.Request(f"{BASE}{path}")
    with urllib.request.urlopen(req, timeout=15) as resp:
        return json.loads(resp.read().decode("utf-8"))


def main() -> None:
    errors: list[str] = []

    if "Endpoint bloqueado temporariamente" not in CLIENT.read_text(encoding="utf-8"):
        errors.append("mensagem esperada ausente em src/gateway/webposto_client.py")

    for name in REPORTS:
        if not (ROOT / name).exists():
            errors.append(f"relatório ausente: {name}")

    try:
        overview = fetch_json(f"/v1/financial/overview?{QUERY}")
        expenses = fetch_json(f"/v1/financial/expenses?{QUERY}&page=1&limit=5")
    except urllib.error.URLError as exc:
        errors.append(f"runtime trace indisponível: {exc}")
        overview = expenses = {}

    for label, payload in [("overview", overview), ("expenses", expenses)]:
        err = payload.get("error") or {}
        if err.get("type") != "CIRCUIT_OPEN":
            errors.append(f"{label}: esperado CIRCUIT_OPEN, obtido {err.get('type')}")
        if err.get("message") != "Endpoint bloqueado temporariamente":
            errors.append(f"{label}: mensagem inesperada")

    print("Financial Recovery QA")
    print(f"  erros: {len(errors)}")
    for err in errors:
        print(f"  - {err}")

    if errors:
        raise SystemExit(1)

    print("[PARECER FINAL: CAUSA RAIZ IDENTIFICADA]")


if __name__ == "__main__":
    main()
