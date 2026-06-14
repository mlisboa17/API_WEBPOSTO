#!/usr/bin/env python3
"""F08.0 — QA gate financial resilience & snapshot recovery."""
from __future__ import annotations

import json
import sys
import urllib.error
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
BASE = "http://127.0.0.1:8050"
QUERY = "dataInicial=2026-06-01&dataFinal=2026-06-07"

REQUIRED_FILES = [
    "src/services/financial_snapshot_service.py",
    "src/services/financial_resilience_service.py",
    "src/interfaces/http/routes/admin_circuit_breaker.py",
    "frontend/pages/financialOverview.js",
    "frontend/pages/financialExpenses.js",
    "dw/ddl/fact_financial_snapshot_health.sql",
    "F08_0_FINANCIAL_RESILIENCE_REPORT.md",
]

MOTOR_SERVICES = [
    "src/services/non_fuel_product_sales_service.py",
    "src/services/commercial_execution_service.py",
    "src/services/fuel_governance_service.py",
    "src/services/nfce_intelligence_service.py",
]


def fetch_json_http(path: str, method: str = "GET", body: dict | None = None) -> dict:
    data = json.dumps(body).encode("utf-8") if body else None
    req = urllib.request.Request(
        f"{BASE}{path}",
        data=data,
        headers={"Content-Type": "application/json"} if data else {},
        method=method,
    )
    with urllib.request.urlopen(req, timeout=20) as resp:
        return json.loads(resp.read().decode("utf-8"))


def run_resilience_unit_check() -> tuple[dict, dict]:
    import asyncio
    from src.gateway.webposto_client import WebPostoClient
    from src.services.financial_resilience_service import FinancialResilienceService
    from src.services.network_financial_overview_service import FinancialOverviewFilters

    async def _run() -> tuple[dict, dict]:
        client = WebPostoClient()
        client.breaker.block_endpoint("despesas_financeiro_rede", duration_seconds=3600)
        svc = FinancialResilienceService(client=client)
        filters = FinancialOverviewFilters(data_inicial="2026-06-01", data_final="2026-06-07")
        overview = await svc.get_financial_overview(filters)
        expenses = await svc.get_financial_expenses(filters, page=1, limit=10)
        return overview, expenses

    return asyncio.run(_run())


def main() -> None:
    errors: list[str] = []

    for rel in REQUIRED_FILES:
        if not (ROOT / rel).exists():
            errors.append(f"arquivo ausente: {rel}")

    fe = (ROOT / "src/interfaces/http/routes/fechamento_enterprise.py").read_text(encoding="utf-8")
    if "FinancialResilienceService" not in fe:
        errors.append("fechamento_enterprise não usa FinancialResilienceService")

    app_py = (ROOT / "src/interfaces/http/app.py").read_text(encoding="utf-8")
    if "admin_circuit_breaker" not in app_py:
        errors.append("admin_circuit_breaker não registrado em app.py")

    for rel in MOTOR_SERVICES:
        path = ROOT / rel
        if path.exists() and "financial_resilience" in path.read_text(encoding="utf-8"):
            errors.append(f"motor F03-F07 alterado indevidamente: {rel}")

    try:
        overview, expenses = run_resilience_unit_check()
        from fastapi.testclient import TestClient
        from src.interfaces.http.app import create_app

        status = TestClient(create_app()).get("/api/v1/admin/circuit-breaker/status").json()
    except Exception as exc:
        errors.append(f"runtime indisponível: {exc}")
        overview = expenses = status = {}

    if not overview.get("success"):
        errors.append("overview não retorna success=true com circuit OPEN")
    if overview.get("resilience", {}).get("source") not in {"live", "snapshot", "degraded"}:
        errors.append("overview sem resilience.source válido")

    if not expenses.get("success"):
        errors.append("expenses não retorna success=true com circuit OPEN")
    if expenses.get("resilience", {}).get("source") not in {"live", "snapshot", "degraded"}:
        errors.append("expenses sem resilience.source válido")

    banner = overview.get("resilience", {}).get("banner") or ""
    if overview.get("resilience", {}).get("source") == "snapshot" and "snapshot homologado" not in banner.lower():
        errors.append("banner snapshot ausente no overview")

    if not status.get("success"):
        errors.append("circuit status endpoint falhou")

    fin_dir = ROOT / "snapshots" / "financial"
    if not fin_dir.is_dir():
        errors.append("snapshots/financial/ ausente")

    print("F08.0 QA")
    print(f"  overview source: {overview.get('resilience', {}).get('source')}")
    print(f"  expenses source: {expenses.get('resilience', {}).get('source')}")
    print(f"  erros: {len(errors)}")
    for err in errors:
        print(f"  - {err}")

    if errors:
        raise SystemExit(1)

    print("[PARECER FINAL: F08.0 FINANCIAL RESILIENCE APROVADA]")


if __name__ == "__main__":
    main()
