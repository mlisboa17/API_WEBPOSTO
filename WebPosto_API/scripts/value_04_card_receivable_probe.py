#!/usr/bin/env python3
"""VALUE-04 — prova runtime de cartão e recebíveis nos 3 postos."""

from __future__ import annotations

import asyncio
import json
import re
import sys
import time
from datetime import date, timedelta
from decimal import Decimal
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
OUT = ROOT / "docs" / "validation" / "VALUE_04_CARD_RECEIVABLE_RAW.json"

PAN_RE = re.compile(r"\b\d{13,19}\b")


def _mask_secrets(obj):
    if isinstance(obj, dict):
        out = {}
        for k, v in obj.items():
            kl = str(k).lower()
            if any(x in kl for x in ("token", "key", "senha", "password", "authorization")):
                out[k] = "***"
            elif "cartao" in kl or "card" in kl:
                out[k] = "***" if v else v
            else:
                out[k] = _mask_secrets(v)
        return out
    if isinstance(obj, list):
        return [_mask_secrets(x) for x in obj[:5]]
    if isinstance(obj, str) and PAN_RE.search(obj):
        return PAN_RE.sub("****", obj)
    return obj


def _sample_keys(rows: list[dict], n: int = 3) -> list[str]:
    keys: set[str] = set()
    for row in rows[:n]:
        keys.update(row.keys())
    return sorted(keys)


def _sum_val(rows: list[dict], key: str = "valor") -> float:
    total = Decimal("0")
    for r in rows:
        for k in (key, "valorTotal", "valorReceber", "valorPago", "totalVenda"):
            if r.get(k) is not None:
                try:
                    total += Decimal(str(r[k]))
                    break
                except Exception:
                    pass
    return float(total)


async def probe_tenant(tenant_id: str, api_key: str, start: str, end: str, ref_date: str) -> dict:
    from src.domain.value_objects.payment_method import PaymentMethod
    from src.gateway.webposto_client import WebPostoClient
    from src.services.analytics_multiselect import build_overview_filters
    from src.services.corporate_finance_center_service import CorporateFinanceCenterService
    from src.services.network_financial_overview_service import NetworkFinancialOverviewService

    t0 = time.perf_counter()
    client = WebPostoClient.for_api_key(api_key)
    overview = NetworkFinancialOverviewService(client)
    finance = CorporateFinanceCenterService(overview)
    filters = build_overview_filters(start, end, tenant_id)

    vendas_resp = await overview._fetch_vendas_produtos(filters, int(tenant_id))
    fp_rows: list[dict] = []
    if vendas_resp.success:
        fp_rows = overview._rows((vendas_resp.data or {}).get("venda_forma_pagamento"))
        fp_rows = [r for r in fp_rows if str(r.get("empresaCodigo") or "") == tenant_id or finance._matches_empresa(r, filters)]

    card_rows = []
    formas: set[str] = set()
    for row in fp_rows:
        forma = str(row.get("formaPagamento") or row.get("descricaoFormaPagamento") or row.get("descricao") or "")
        formas.add(forma)
        pm = PaymentMethod.from_raw(forma)
        if pm in {PaymentMethod.CARTAO_CREDITO, PaymentMethod.CARTAO_DEBITO}:
            card_rows.append(row)

    rec_rows, _ = await finance._fetch_titulo_receber_all(filters)
    rec_rows = [r for r in rec_rows if str(r.get("empresaCodigo")) == tenant_id or finance._matches_empresa(r, filters)]
    buckets = finance._classify_receivables(rec_rows, ref_date)

    bank_rows, _ = await finance._fetch_movimento_conta_all(filters)
    bank_rows = [r for r in bank_rows if str(r.get("empresaCodigo")) == tenant_id or finance._matches_empresa(r, filters)]
    bank = finance._classify_bank_movements(bank_rows)

    statuses = sorted({str(r.get("situacao") or "") for r in rec_rows if r.get("situacao")})
    venc_dates = [str(r.get("dataVencimento") or r.get("vencimento") or "")[:10] for r in rec_rows if r.get("dataVencimento") or r.get("vencimento")]
    venc_dates = [d for d in venc_dates if d]

    return {
        "tenant_id": tenant_id,
        "empresa_codigo": tenant_id,
        "periodo": {"start": start, "end": end},
        "vendas_cartao_count": len(card_rows),
        "valor_bruto_cartao": round(_sum_val(card_rows, "valor"), 2),
        "formas_pagamento_amostra": sorted(formas)[:25],
        "formas_pagamento_count": len(formas),
        "recebiveis_total_count": len(rec_rows),
        "recebiveis_valor_total": round(_sum_val(rec_rows), 2),
        "recebidos_count": len(buckets["recebido"]),
        "recebidos_valor": round(_sum_val(buckets["recebido"]), 2),
        "pendentes_count": len(buckets["pendente"]),
        "pendentes_valor": round(_sum_val(buckets["pendente"]), 2),
        "vencidos_count": len(buckets["vencido"]),
        "vencidos_valor": round(_sum_val(buckets["vencido"]), 2),
        "a_vencer_count": len(buckets["aVencer"]),
        "a_vencer_valor": round(_sum_val(buckets["aVencer"]), 2),
        "status_encontrados": statuses,
        "datas_vencimento_min": min(venc_dates) if venc_dates else None,
        "datas_vencimento_max": max(venc_dates) if venc_dates else None,
        "movimento_bancario_creditos_count": bank["creditos"]["count"],
        "movimento_bancario_creditos_valor": float(bank["creditos"]["valor"]),
        "field_keys": {
            "venda_forma_pagamento": _sample_keys(fp_rows),
            "titulo_receber": _sample_keys(rec_rows),
            "movimento_conta": _sample_keys(bank_rows),
        },
        "amostra_sanitizada": {
            "venda_forma_pagamento": [_mask_secrets(dict(r)) for r in card_rows[:2]],
            "titulo_receber_vencido": [_mask_secrets(dict(r)) for r in buckets["vencido"][:2]],
        },
        "registros_sem_vinculo_venda_recebivel": len(card_rows),
        "query_ms": round((time.perf_counter() - t0) * 1000, 1),
    }


async def main() -> None:
    from src.core.webposto_credentials import list_webposto_credentials
    from src.services.tenant_discovery_service import TenantDiscoveryService

    end = date.today()
    start = (end - timedelta(days=29)).isoformat()
    end_s = end.isoformat()
    ref_date = end_s

    discovery = await TenantDiscoveryService().discover_tenants()
    cred_by_alias = {c.env_key: c.api_key for c in list_webposto_credentials()}

    tenants_out = []
    for t in discovery.tenants_discovered:
        key = cred_by_alias.get(t.credential_alias)
        if not key:
            continue
        row = await probe_tenant(t.tenant_id, key, start, end_s, ref_date)
        row["tenant_name"] = t.tenant_name
        tenants_out.append(row)

    report = {
        "executed_at": end_s,
        "periodo": {"start": start, "end": end_s, "days": 30},
        "tenants_discovered": len(discovery.tenants_discovered),
        "tenants": tenants_out,
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({"tenants": len(tenants_out), "out": str(OUT)}, indent=2))


if __name__ == "__main__":
    asyncio.run(main())
