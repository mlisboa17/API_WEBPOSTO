#!/usr/bin/env python3
"""HOTFIX P0 — QA gate sales non-blocking snapshot fallback."""
from __future__ import annotations

import asyncio
import sys
import time
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

QUERY = "dataInicial=2026-06-01&dataFinal=2026-06-07&page=1&limit=5"


def run_unit_tests() -> list[str]:
    errors: list[str] = []
    from src.infrastructure.config.settings import settings
    from src.services.network_financial_overview_service import FinancialOverviewFilters
    from src.services.sales_resilience_service import SalesResilienceService

    async def slow_live(*_a, **_k):
        await asyncio.sleep(35)
        from src.models.response_model import WebPostoResponse

        return WebPostoResponse.ok({"page": 1, "limit": 5, "total": 0, "data": []})

    async def _run() -> tuple[float, dict]:
        svc = SalesResilienceService()
        filters = FinancialOverviewFilters(data_inicial="2026-06-01", data_final="2026-06-07")
        key = svc._snapshots.build_key("2026-06-01", "2026-06-07", None)
        svc._snapshots.save_kind(
            "financial_sales",
            key,
            {
                "page": 1,
                "limit": 500,
                "total": 2,
                "data": [{"vendaCodigo": 1}, {"vendaCodigo": 2}],
                "consolidado": {"total_vendas": "100", "qtd_vendas": 2},
            },
            source="qa",
        )
        svc._overview.get_sales = slow_live
        with patch.object(settings, "sales_live_timeout_seconds", 2), patch.object(settings, "sales_total_budget_seconds", 22):
            t0 = time.perf_counter()
            resp = await svc.get_sales(filters, page=1, limit=5)
            return time.perf_counter() - t0, resp

    elapsed, resp = asyncio.run(_run())
    if elapsed > 22:
        errors.append(f"timeout budget violado: {elapsed:.2f}s > 22s")
    if resp.get("resilience", {}).get("mode") != "snapshot_fallback":
        errors.append(f"modo esperado snapshot_fallback, got {resp.get('resilience', {}).get('mode')}")
    if resp.get("resilience", {}).get("reason") != "live_timeout":
        errors.append(f"reason esperado live_timeout, got {resp.get('resilience', {}).get('reason')}")
    if not resp.get("success"):
        errors.append("snapshot fallback deveria retornar success=true")
    if len(resp.get("data", {}).get("data", [])) != 2:
        errors.append("snapshot paginado incompleto")

    from src.gateway.sales_circuit import sales_circuit_open

    svc2 = SalesResilienceService()
    svc2._client.breaker.block_endpoint("venda", duration_seconds=120)
    if not sales_circuit_open(svc2._client):
        errors.append("circuito sales deveria estar OPEN após block_endpoint venda")

    return errors


def run_http_tests() -> list[str]:
    errors: list[str] = []
    import urllib.error
    import urllib.request

    base = "http://127.0.0.1:8050"
    try:
        with urllib.request.urlopen(f"{base}/health", timeout=5) as resp:
            if resp.status != 200:
                errors.append(f"health status {resp.status}")
    except Exception as exc:
        errors.append(f"health indisponível: {exc}")
        return errors

    t0 = time.perf_counter()
    try:
        with urllib.request.urlopen(f"{base}/v1/sales?{QUERY}", timeout=25) as resp:
            body = resp.read()
            elapsed = time.perf_counter() - t0
            if resp.status != 200:
                errors.append(f"sales HTTP {resp.status}")
            if elapsed > 22:
                errors.append(f"sales runtime {elapsed:.2f}s > 22s")
            if not body:
                errors.append("sales body vazio")
    except urllib.error.URLError as exc:
        elapsed = time.perf_counter() - t0
        errors.append(f"sales falhou em {elapsed:.2f}s: {exc}")
    except TimeoutError as exc:
        elapsed = time.perf_counter() - t0
        errors.append(f"sales timeout em {elapsed:.2f}s (>22s budget): {exc}")

    return errors


def main() -> None:
    errors = run_unit_tests()
    errors.extend(run_http_tests())

    required = [
        "src/services/sales_resilience_service.py",
        "src/gateway/sales_circuit.py",
        "SALES_ROUTE_TRACE_REPORT.md",
        "SALES_RESILIENCE_QA_REPORT.md",
    ]
    for rel in required:
        if not (ROOT / rel).exists():
            errors.append(f"arquivo ausente: {rel}")

    print("HOTFIX P0 — Sales Resilience QA")
    print(f"  erros: {len(errors)}")
    for err in errors:
        print(f"  - {err}")

    if not errors:
        print("[PARECER FINAL: HOTFIX P0 SALES NON-BLOCKING FALLBACK APROVADO]")
        raise SystemExit(0)
    raise SystemExit(1)


if __name__ == "__main__":
    main()
