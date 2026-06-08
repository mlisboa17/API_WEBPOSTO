#!/usr/bin/env python3
"""Gera account_category_mapping.json a partir de catálogo + evidência de uso."""
from __future__ import annotations

import asyncio
import json
import sys
from collections import Counter, defaultdict
from decimal import Decimal
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src.core.config import load_core_config
from src.services.logos_expense_classifier_v2 import classify_logos_expense_v2, map_v2_to_legacy

PERIOD = {"dataInicial": "2026-06-01", "dataFinal": "2026-06-07"}
OUT = ROOT / "config" / "account_category_mapping.json"

PLANO_OVERRIDES: dict[int, dict[str, str]] = {
    47952: {"categoriaLogosV3": "OPERACIONAL", "evidence": "DESPESA LOJA — uso 29 regs"},
    29072: {"categoriaLogosV3": "PESSOAL", "evidence": "B01 - SALARIOS"},
    48547: {"categoriaLogosV3": "OPERACIONAL", "evidence": "DESPESA POSTO"},
    39370: {"categoriaLogosV3": "PESSOAL", "evidence": "SR. MOISES plano"},
    61815: {"categoriaLogosV3": "PESSOAL", "evidence": "FOLGUISTA"},
    167278: {"categoriaLogosV3": "ENERGIA", "evidence": "conta energia rede"},
    29084: {"categoriaLogosV3": "PESSOAL", "evidence": "SINDICATO"},
}


async def main() -> int:
    import httpx

    cfg = load_core_config()
    async with httpx.AsyncClient() as client:
        pr = await client.get(
            f"{cfg.webposto_base_url}/INTEGRACAO/PLANO_CONTA_GERENCIAL",
            params={**PERIOD, "CHAVE": cfg.webposto_api_key},
            timeout=60,
        )
        planos = pr.json() if pr.status_code == 200 else []
        if isinstance(planos, dict):
            planos = planos.get("resultados") or planos.get("data") or []

        er = await client.get(
            f"{cfg.webposto_base_url}/INTEGRACAO/CONSULTAR_DESPESAS_FINANCEIRO_REDE",
            params={**PERIOD, "CHAVE": cfg.webposto_api_key},
            timeout=120,
        )
        expenses = er.json() if er.status_code == 200 else []
        if isinstance(expenses, dict):
            expenses = expenses.get("resultados") or expenses.get("data") or []

    usage: Counter[int] = Counter()
    usage_val: dict[int, Decimal] = defaultdict(Decimal)
    for row in expenses:
        pc = row.get("planoContaGerencialCodigo")
        if pc:
            usage[int(pc)] += 1
            usage_val[int(pc)] += Decimal(str(row.get("valor") or 0))

    mappings: list[dict] = []
    for p in planos:
        if not isinstance(p, dict) or p.get("codigo") is None:
            continue
        code = int(p["codigo"])
        desc = str(p.get("descricao") or "")
        override = PLANO_OVERRIDES.get(code)
        if override:
            cat_v3 = override["categoriaLogosV3"]
            source = "MANUAL"
            conf = 0.95
            evidence = override["evidence"]
        else:
            v2 = classify_logos_expense_v2(desc)
            cat_v3 = v2.categoria_v2
            source = "PLANO_CONTA"
            conf = min(1.0, v2.confidence_score / 100 * 0.6 + 0.35) if cat_v3 != "OUTROS" else 0.0
            evidence = f"catalogo:{desc[:60]}"

        mappings.append(
            {
                "planoContaId": code,
                "codigoGerencial": code,
                "descricaoGerencial": desc,
                "codigoContabil": p.get("planoContaCodigo"),
                "descricaoContabil": None,
                "natureza": p.get("natureza"),
                "tipo": p.get("tipo"),
                "apuraDre": p.get("apuraDre"),
                "categoriaLogosV3": cat_v3,
                "categoriaLogosV2": cat_v3,
                "categoriaLogos": map_v2_to_legacy(cat_v3),
                "classificationSource": source,
                "confidenceScore": round(conf, 3),
                "usageCount": usage.get(code, 0),
                "usageValor": str(usage_val.get(code, Decimal("0")).quantize(Decimal("0.01"))),
                "evidence": evidence,
                "ativo": True,
            }
        )

    payload = {
        "version": "1.0.0",
        "generatedFrom": f"PLANO_CONTA_GERENCIAL + DESPESAS_REDE {PERIOD['dataInicial']}..{PERIOD['dataFinal']}",
        "totalPlanos": len(mappings),
        "mappedNonOutros": sum(1 for m in mappings if m["categoriaLogosV3"] != "OUTROS"),
        "mappings": mappings,
        "byDescricaoPattern": {
            "Energia Elétrica": "ENERGIA",
            "Taxa Bancária": "FINANCEIRO",
            "Internet": "TECNOLOGIA",
            "Folha de Pagamento": "PESSOAL",
            "Combustível Consumo": "VEÍCULOS",
            "Despesa Posto": "OPERACIONAL",
        },
    }
    OUT.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"Mapped {payload['mappedNonOutros']}/{payload['totalPlanos']} planos non-OUTROS → {OUT}")
    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
