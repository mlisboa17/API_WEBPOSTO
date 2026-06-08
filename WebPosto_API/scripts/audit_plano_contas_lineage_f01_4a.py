#!/usr/bin/env python3
"""Auditoria linhagem Plano de Contas — Sprint F01.4-A (Agente 1)."""
from __future__ import annotations

import asyncio
import json
import sys
from collections import defaultdict
from decimal import Decimal
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src.core.config import load_core_config
from src.services.logos_expense_classifier import classify_logos_expense_v1_baseline
from src.services.logos_expense_classifier_v2 import classify_logos_expense_v2, map_v2_to_legacy

PERIOD = {"dataInicial": "2026-06-01", "dataFinal": "2026-06-07"}
OUT_JSON = ROOT / "scripts" / "plano_contas_lineage_audit.json"
OUT_MD = ROOT / "PLANO_CONTAS_INTELLIGENCE_REPORT.md"

FIELD_SPECS = {
    "planoContaGerencialCodigo": "planoContaGerencialCodigo",
    "planoContaGerencialDescricao": ("planoContaGerencialDescricao", "descricaoPlanoContaGerencial"),
    "planoContaContabilCodigo": ("planoContaContabilCodigo", "planoContaCodigo"),
    "planoContaContabilDescricao": ("planoContaContabilDescricao", "descricaoPlanoContaContabil"),
    "centroCustoCodigo": "centroCustoCodigo",
    "centroCustoDescricao": ("centroCustoDescricao", "descricaoCentroCusto"),
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


def _has_field(row: dict[str, Any], spec: str | tuple[str, ...]) -> bool:
    keys = (spec,) if isinstance(spec, str) else spec
    for k in keys:
        v = row.get(k)
        if v is not None and str(v).strip() not in ("", "0", "None"):
            return True
    return False


def _coverage(rows: list[dict[str, Any]], spec: str | tuple[str, ...]) -> dict[str, Any]:
    if not rows:
        return {"count": 0, "pct": 0.0, "byEmpresa": {}}
    by_emp: dict[str, int] = defaultdict(int)
    hit = 0
    for row in rows:
        if _has_field(row, spec):
            hit += 1
            emp = str(row.get("empresaCodigo") or "null")
            by_emp[emp] += 1
    total = len(rows)
    by_emp_pct = {k: round(v / total * 100, 2) for k, v in sorted(by_emp.items())}
    return {"count": hit, "pct": round(hit / total * 100, 2), "byEmpresa": by_emp_pct}


async def _fetch(client, base: str, key: str, path: str, params: dict) -> tuple[str, list[dict], int]:
    try:
        r = await client.get(f"{base}{path}", params={**params, "CHAVE": key}, timeout=120)
        return path, _rows(r.json() if r.status_code == 200 else []), r.status_code
    except Exception:
        return path, [], 0


async def main() -> int:
    import httpx

    cfg = load_core_config()
    params = dict(PERIOD)

    endpoints = {
        "DESPESAS_REDE": "/INTEGRACAO/CONSULTAR_DESPESAS_FINANCEIRO_REDE",
        "TITULO_PAGAR": "/INTEGRACAO/TITULO_PAGAR",
        "MOVIMENTO_CONTA": "/INTEGRACAO/MOVIMENTO_CONTA",
        "LANCAMENTO_CONTABIL": "/INTEGRACAO/LANCAMENTO_CONTABIL",
    }

    async with httpx.AsyncClient() as client:
        facts: dict[str, Any] = {}
        for name, path in endpoints.items():
            _, rows, status = await _fetch(client, cfg.webposto_base_url, cfg.webposto_api_key, path, params)
            field_cov = {fname: _coverage(rows, spec) for fname, spec in FIELD_SPECS.items()}
            facts[name] = {
                "httpStatus": status,
                "registros": len(rows),
                "campos": field_cov,
                "sampleKeys": sorted(rows[0].keys()) if rows else [],
            }

        _, planos, ps = await _fetch(
            client, cfg.webposto_base_url, cfg.webposto_api_key,
            "/INTEGRACAO/PLANO_CONTA_GERENCIAL", params,
        )
        _, centros, cs = await _fetch(
            client, cfg.webposto_base_url, cfg.webposto_api_key,
            "/INTEGRACAO/CENTRO_CUSTO_REDE", params,
        )

        plano_map = {
            int(p["codigo"]): p
            for p in planos
            if isinstance(p, dict) and p.get("codigo") is not None
        }

        exp_rows = facts["DESPESAS_REDE"]
        exp_data = _rows(
            (await client.get(
                f"{cfg.webposto_base_url}/INTEGRACAO/CONSULTAR_DESPESAS_FINANCEIRO_REDE",
                params={**params, "CHAVE": cfg.webposto_api_key},
                timeout=120,
            )).json()
        )

        outros_val = Decimal("0")
        outros_with_plano = 0
        outros_with_centro = 0
        outros_total = 0
        total_val = Decimal("0")

        for row in exp_data:
            val = Decimal(str(row.get("valor") or 0))
            total_val += val
            desc = str(row.get("descricaoDocumento") or "")
            v2 = classify_logos_expense_v2(desc)
            if map_v2_to_legacy(v2.categoria_v2) != "OUTROS":
                continue
            outros_total += 1
            outros_val += val
            if row.get("planoContaGerencialCodigo"):
                outros_with_plano += 1
            pc = row.get("planoContaGerencialCodigo")
            if pc and int(pc) in plano_map:
                pd = str(plano_map[int(pc)].get("descricao") or "")
                if classify_logos_expense_v2(pd).categoria_v2 != "OUTROS":
                    pass  # reclassifiable via plano

        reclass_via_plano = 0
        reclass_val = Decimal("0")
        for row in exp_data:
            desc = str(row.get("descricaoDocumento") or "")
            if map_v2_to_legacy(classify_logos_expense_v2(desc).categoria_v2) != "OUTROS":
                continue
            pc = row.get("planoContaGerencialCodigo")
            if not pc or int(pc) not in plano_map:
                continue
            pd = str(plano_map[int(pc)].get("descricao") or "")
            if classify_logos_expense_v2(pd).categoria_v2 != "OUTROS":
                reclass_via_plano += 1
                reclass_val += Decimal(str(row.get("valor") or 0))

        reduction_pct = float(reclass_val / outros_val * 100) if outros_val else 0.0

    result = {
        "period": PERIOD,
        "facts": facts,
        "catalogs": {
            "PLANO_CONTA_GERENCIAL": {"httpStatus": ps, "registros": len(planos), "sampleKeys": sorted(planos[0].keys()) if planos else []},
            "CENTRO_CUSTO_REDE": {"httpStatus": cs, "registros": len(centros)},
        },
        "outrosAnalysis": {
            "outrosRegistros": outros_total,
            "outrosValor": str(outros_val.quantize(Decimal("0.01"))),
            "comPlanoContaGerencialCodigo": outros_with_plano,
            "comPlanoContaGerencialPct": round(outros_with_plano / max(outros_total, 1) * 100, 2),
            "reclassificavelViaPlanoDescricao": reclass_via_plano,
            "valorReclassificavelViaPlano": str(reclass_val.quantize(Decimal("0.01"))),
            "reducaoOutrosPotencialPct": round(reduction_pct, 2),
        },
        "planoCatalogSize": len(plano_map),
    }
    OUT_JSON.write_text(json.dumps(result, indent=2, ensure_ascii=False), encoding="utf-8")

    despesas = facts["DESPESAS_REDE"]["campos"]
    md = f"""# PLANO CONTAS INTELLIGENCE REPORT — F01.4-A

**Período:** {PERIOD["dataInicial"]} → {PERIOD["dataFinal"]}

## Cobertura por fato financeiro

| Fato | Registros | planoGerencialCodigo | planoContabilCodigo | centroCustoCodigo | centroCustoDescricao |
|------|----------:|---------------------:|--------------------:|------------------:|---------------------:|
| DESPESAS_REDE | {facts["DESPESAS_REDE"]["registros"]} | {despesas["planoContaGerencialCodigo"]["pct"]}% | {despesas["planoContaContabilCodigo"]["pct"]}% | {despesas["centroCustoCodigo"]["pct"]}% | {despesas["centroCustoDescricao"]["pct"]}% |
| TITULO_PAGAR | {facts["TITULO_PAGAR"]["registros"]} | {facts["TITULO_PAGAR"]["campos"]["planoContaGerencialCodigo"]["pct"]}% | {facts["TITULO_PAGAR"]["campos"]["planoContaContabilCodigo"]["pct"]}% | {facts["TITULO_PAGAR"]["campos"]["centroCustoCodigo"]["pct"]}% | {facts["TITULO_PAGAR"]["campos"]["centroCustoDescricao"]["pct"]}% |
| MOVIMENTO_CONTA | {facts["MOVIMENTO_CONTA"]["registros"]} | {facts["MOVIMENTO_CONTA"]["campos"]["planoContaGerencialCodigo"]["pct"]}% | {facts["MOVIMENTO_CONTA"]["campos"]["planoContaContabilCodigo"]["pct"]}% | {facts["MOVIMENTO_CONTA"]["campos"]["centroCustoCodigo"]["pct"]}% | {facts["MOVIMENTO_CONTA"]["campos"]["centroCustoDescricao"]["pct"]}% |
| LANCAMENTO_CONTABIL | {facts["LANCAMENTO_CONTABIL"]["registros"]} | — | — | — | — |

## Catálogos

| Catálogo | HTTP | Registros |
|----------|-----:|----------:|
| PLANO_CONTA_GERENCIAL | {ps} | {len(planos)} |
| CENTRO_CUSTO_REDE | {cs} | {len(centros)} |

## OUTROS × Plano de Contas

| Métrica | Valor |
|---------|------:|
| Registros OUTROS (V2 legacy) | {outros_total} |
| Com planoContaGerencialCodigo | **{result["outrosAnalysis"]["comPlanoContaGerencialPct"]}%** |
| Reclassificável via descrição do plano | {reclass_via_plano} registros |
| Redução potencial OUTROS | **{reduction_pct:.1f}%** do valor OUTROS |

Evidência: `scripts/plano_contas_lineage_audit.json`
"""
    OUT_MD.write_text(md, encoding="utf-8")
    print(json.dumps(result["outrosAnalysis"], indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
