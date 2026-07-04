#!/usr/bin/env python3
"""VALUE-03 — prova de dados reais de despesas nos 3 postos."""

from __future__ import annotations

import asyncio
import json
import time
from datetime import date, timedelta
from decimal import Decimal
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
import sys
sys.path.insert(0, str(ROOT))
OUT = ROOT / "docs" / "validation" / "VALUE_03_EXPENSE_DATA_RAW.json"


async def probe_tenant(tenant_id: str, credential_key: str, api_key: str, cur_start: str, cur_end: str, base_start: str, base_end: str) -> dict:
    from src.gateway.webposto_client import WebPostoClient
    from src.services.analytics_multiselect import build_overview_filters
    from src.services.network_financial_overview_service import NetworkFinancialOverviewService
    from src.services.tenant_discovery_service import TenantDiscoveryService

    t0 = time.perf_counter()
    client = WebPostoClient.for_api_key(api_key)
    overview = NetworkFinancialOverviewService(client)

    cur_f = build_overview_filters(cur_start, cur_end, tenant_id)
    base_f = build_overview_filters(base_start, base_end, tenant_id)

    cur_rows, cur_err = await overview._load_filtered_expenses(cur_f)
    base_rows, base_err = await overview._load_filtered_expenses(base_f)

    titulo_cur = await overview._fetch_titulo_pagar(cur_f, int(tenant_id))
    titulo_base = await overview._fetch_titulo_pagar(base_f, int(tenant_id))

    def sum_val(rows: list) -> float:
        t = Decimal("0")
        for r in rows:
            try:
                t += Decimal(str(r.get("valor") or 0))
            except Exception:
                pass
        return float(t)

    cats = sorted({str(r.get("planoConta") or "SEM_CATEGORIA") for r in cur_rows})
    suppliers = sorted(
        {
            str((overview._normalize_titulo_pagar(r) or {}).get("fornecedor") or "")
            for r in overview._rows(titulo_cur.data if titulo_cur.success else [])
            if overview._normalize_titulo_pagar(r)
        }
    )

    return {
        "tenant_id": tenant_id,
        "empresa_codigo": tenant_id,
        "fonte": "CONSULTAR_DESPESAS_FINANCEIRO_REDE + TITULO_PAGAR",
        "periodo_atual": {"start": cur_start, "end": cur_end},
        "baseline": {"start": base_start, "end": base_end},
        "registros_atual": len(cur_rows),
        "registros_baseline": len(base_rows),
        "valor_total_atual": round(sum_val(cur_rows), 2),
        "valor_total_baseline": round(sum_val(base_rows), 2),
        "categorias_atual": cats[:40],
        "categorias_count": len(cats),
        "fornecedores_titulo_count": len([s for s in suppliers if s]),
        "fornecedores_amostra": [s for s in suppliers if s][:15],
        "errors": {
            "despesas_atual": None if not cur_err else str(getattr(cur_err.error, "message", cur_err)),
            "despesas_baseline": None if not base_err else str(getattr(base_err.error, "message", base_err)),
            "titulo_atual": None if titulo_cur.success else str(getattr(titulo_cur.error, "message", titulo_cur)),
            "titulo_baseline": None if titulo_base.success else str(getattr(titulo_base.error, "message", titulo_base)),
        },
        "query_ms": round((time.perf_counter() - t0) * 1000, 1),
    }


async def main() -> None:
    from src.core.webposto_credentials import list_webposto_credentials
    from src.services.tenant_discovery_service import TenantDiscoveryService

    end = date.today()
    cur_start = (end - timedelta(days=29)).isoformat()
    cur_end = end.isoformat()
    base_end = (end - timedelta(days=30)).isoformat()
    base_start = (end - timedelta(days=59)).isoformat()

    discovery = await TenantDiscoveryService().discover_tenants()
    cred_by_alias = {c.env_key: c.api_key for c in list_webposto_credentials()}

    tenants_out = []
    for t in discovery.tenants_discovered:
        key = cred_by_alias.get(t.credential_alias)
        if not key:
            continue
        tenants_out.append(await probe_tenant(t.tenant_id, t.credential_alias, key, cur_start, cur_end, base_start, base_end))

    report = {
        "executed_at": cur_end,
        "periodo_atual": {"start": cur_start, "end": cur_end},
        "baseline": {"start": base_start, "end": base_end},
        "tenants_discovered": len(discovery.tenants_discovered),
        "tenants": tenants_out,
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({"tenants": len(tenants_out), "out": str(OUT)}, indent=2))


if __name__ == "__main__":
    asyncio.run(main())
