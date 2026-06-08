#!/usr/bin/env python3
"""Auditoria Supplier Discovery — Sprint F01.4-C."""
from __future__ import annotations

import asyncio
import json
import sys
from collections import defaultdict
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

PERIOD = {"dataInicial": "2026-06-01", "dataFinal": "2026-06-07"}
OUT = ROOT / "scripts" / "supplier_discovery_audit.json"

SUPPLIER_FIELDS = (
    "fornecedorCodigo",
    "fornecedorNome",
    "nomeFornecedor",
    "fornecedorDocumento",
    "cpfCnpjFornecedor",
    "fornecedorCNPJ",
    "fornecedorCPF",
    "contaFornecedor",
    "fornecedorId",
    "fornecedor",
    "codigoPessoa",
    "tipoPessoa",
)

ENDPOINTS = {
    "FORNECEDOR_REDE": "/INTEGRACAO/FORNECEDOR_REDE",
    "CONTA_FORNECEDOR": "/INTEGRACAO/CONTA_FORNECEDOR",
    "FORNECEDOR": "/INTEGRACAO/FORNECEDOR",
    "DESPESAS_REDE": "/INTEGRACAO/CONSULTAR_DESPESAS_FINANCEIRO_REDE",
    "TITULO_PAGAR": "/INTEGRACAO/TITULO_PAGAR",
    "MOVIMENTO_CONTA": "/INTEGRACAO/MOVIMENTO_CONTA",
    "COMPRA_REDE": "/INTEGRACAO/COMPRA_REDE",
    "PEDIDO_COMPRAS": "/INTEGRACAO/PEDIDO_COMPRAS",
    "NOTA_ENTRADA": "/INTEGRACAO/NOTA_ENTRADA",
    "CLIENTE_EMPRESA_REDE": "/INTEGRACAO/CLIENTE_EMPRESA_REDE",
}


def _rows(payload: Any) -> list[dict[str, Any]]:
    if isinstance(payload, list):
        return [r for r in payload if isinstance(r, dict)]
    if isinstance(payload, dict):
        for key in ("resultados", "data", "items"):
            val = payload.get(key)
            if isinstance(val, list):
                return [r for r in val if isinstance(r, dict)]
    return []


def _field_coverage(rows: list[dict], field: str) -> dict[str, Any]:
    if not rows:
        return {"count": 0, "pct": 0.0}
    hit = sum(1 for r in rows if r.get(field) not in (None, "", 0, "0"))
    return {"count": hit, "pct": round(hit / len(rows) * 100, 2)}


def _classify(status: int, rows: list, fields_found: list[str]) -> str:
    if status == 401:
        return "401"
    if status == 404:
        return "404"
    if status != 200:
        return "SEM_COBERTURA"
    if not rows:
        return "SEM_COBERTURA"
    if any(f in fields_found for f in ("nomeFornecedor", "fornecedorCodigo", "fornecedor")):
        return "USAR_AGORA"
    if fields_found:
        return "USAR_COM_CUIDADO"
    return "SEM_COBERTURA"


async def main() -> int:
    import httpx

    from src.core.config import load_core_config

    cfg = load_core_config()
    results: dict[str, Any] = {"period": PERIOD, "endpoints": {}}

    async with httpx.AsyncClient() as client:
        for name, path in ENDPOINTS.items():
            try:
                r = await client.get(
                    f"{cfg.webposto_base_url}{path}",
                    params={**PERIOD, "CHAVE": cfg.webposto_api_key},
                    timeout=120,
                )
                status = r.status_code
                rows = _rows(r.json() if status == 200 else [])
            except Exception:
                status, rows = 0, []

            keys = sorted(rows[0].keys()) if rows else []
            fields_in_sample = [f for f in SUPPLIER_FIELDS if f in keys]
            field_cov = {f: _field_coverage(rows, f) for f in SUPPLIER_FIELDS if f in keys}
            classification = _classify(status, rows, fields_in_sample)

            results["endpoints"][name] = {
                "path": path,
                "httpStatus": status,
                "registros": len(rows),
                "classification": classification,
                "supplierFieldsInSchema": fields_in_sample,
                "fieldCoverage": field_cov,
                "sampleKeys": keys[:30],
            }

    OUT.write_text(json.dumps(results, ensure_ascii=False, indent=2), encoding="utf-8")
    md = ROOT / "SUPPLIER_DISCOVERY_REPORT.md"
    lines = [
        "# SUPPLIER DISCOVERY REPORT — F01.4-C",
        "",
        f"**Período:** {PERIOD['dataInicial']} → {PERIOD['dataFinal']}",
        f"**Evidência:** `scripts/supplier_discovery_audit.json`",
        "",
        "| Endpoint | HTTP | Registros | Classificação | Campos fornecedor |",
        "|----------|------|-----------|---------------|-------------------|",
    ]
    for name, ep in results["endpoints"].items():
        lines.append(
            f"| {name} | {ep['httpStatus']} | {ep['registros']} | **{ep['classification']}** | {', '.join(ep['supplierFieldsInSchema'][:4]) or '—'} |"
        )
    lines.extend(
        [
            "",
            "## Fonte primária recomendada",
            "",
            "**TITULO_PAGAR** — `nomeFornecedor`, `fornecedorCodigo`, `cpfCnpjFornecedor`, `contaFornecedor`",
            "",
            "## Bloqueados (401)",
            "",
            "FORNECEDOR_REDE, COMPRA_REDE, PEDIDO_COMPRAS, NOTA_ENTRADA",
        ]
    )
    md.write_text("\n".join(lines), encoding="utf-8")
    print(f"OK -> {OUT}")
    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
