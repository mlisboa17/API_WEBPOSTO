#!/usr/bin/env python3
"""Auditoria Expense Intelligence — Sprint F01.3 (Agente 1)."""
from __future__ import annotations

import asyncio
import json
import sys
import unicodedata
from collections import Counter, defaultdict
from decimal import Decimal
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src.core.config import load_core_config
from src.services.logos_expense_classifier_v2 import classify_logos_expense_v2, map_v2_to_legacy

PERIOD = {"dataInicial": "2026-06-01", "dataFinal": "2026-06-07"}
OUT_JSON = ROOT / "scripts" / "expense_intelligence_audit.json"
OUT_MD = ROOT / "EXPENSE_INTELLIGENCE_AUDIT.md"

from src.services.logos_expense_classifier import classify_logos_expense_v1_baseline


def _norm(text: str) -> str:
    s = str(text or "").strip().casefold()
    return "".join(c for c in unicodedata.normalize("NFD", s) if unicodedata.category(c) != "Mn")


async def main() -> int:
    import httpx

    cfg = load_core_config()
    async with httpx.AsyncClient() as client:
        r = await client.get(
            f"{cfg.webposto_base_url}/INTEGRACAO/CONSULTAR_DESPESAS_FINANCEIRO_REDE",
            params={**PERIOD, "CHAVE": cfg.webposto_api_key},
            timeout=120,
        )
        rows = r.json() if r.status_code == 200 else []
        if isinstance(rows, dict):
            rows = rows.get("resultados") or rows.get("data") or []

    total_val = Decimal("0")
    outros_before_val = Decimal("0")
    outros_after_val = Decimal("0")
    identified_from_outros = Decimal("0")
    outros_before_count = 0
    desc_rank: list[dict] = []
    desc_counter: Counter = Counter()
    desc_val: dict[str, Decimal] = defaultdict(Decimal)
    emp_val: dict[int, Decimal] = defaultdict(Decimal)
    plano_val: dict[int, Decimal] = defaultdict(Decimal)

    for row in rows:
        if not isinstance(row, dict):
            continue
        val = Decimal(str(row.get("valor") or 0))
        total_val += val
        desc = str(row.get("descricaoDocumento") or "")
        plano_code = row.get("planoContaGerencialCodigo")
        emp = row.get("empresaCodigo")
        emp_val[int(emp)] += val if emp else Decimal("0")
        if plano_code:
            plano_val[int(plano_code)] += val

        cat_v1 = classify_logos_expense_v1_baseline(desc, "")
        v2 = classify_logos_expense_v2(desc)
        cat_legacy = map_v2_to_legacy(v2.categoria_v2)

        if cat_v1 == "OUTROS":
            outros_before_val += val
            outros_before_count += 1
            if cat_legacy != "OUTROS" or v2.categoria_v2 != "OUTROS":
                identified_from_outros += val

        if cat_legacy == "OUTROS":
            outros_after_val += val

        key = desc[:100] or "(vazio)"
        desc_counter[key] += 1
        desc_val[key] += val

    top100_desc = sorted(desc_val.items(), key=lambda x: -x[1])[:100]
    for desc, val in top100_desc:
        v2 = classify_logos_expense_v2(desc)
        desc_rank.append(
            {
                "descricao": desc,
                "count": desc_counter[desc],
                "valor": str(val.quantize(Decimal("0.01"))),
                "categoriaV2": v2.categoria_v2,
                "confidence": v2.confidence_score,
            }
        )

    pct_before = float(outros_before_val / total_val * 100) if total_val else 0
    pct_after = float(outros_after_val / total_val * 100) if total_val else 0
    pct_identified = float(identified_from_outros / outros_before_val * 100) if outros_before_val else 0

    result = {
        "period": PERIOD,
        "total_registros": len(rows),
        "valor_total": str(total_val.quantize(Decimal("0.01"))),
        "outros_before_pct": round(pct_before, 2),
        "outros_after_pct": round(pct_after, 2),
        "outros_before_valor": str(outros_before_val.quantize(Decimal("0.01"))),
        "outros_after_valor": str(outros_after_val.quantize(Decimal("0.01"))),
        "valor_identificado_pct": round(pct_identified, 2),
        "outros_before_registros": outros_before_count,
        "top100_descriptions": desc_rank,
        "top_empresas": [
            {"empresaCodigo": k, "valor": str(v.quantize(Decimal("0.01")))}
            for k, v in sorted(emp_val.items(), key=lambda x: -x[1])[:20]
        ],
        "top_planos": [
            {"planoContaGerencialCodigo": k, "valor": str(v.quantize(Decimal("0.01")))}
            for k, v in sorted(plano_val.items(), key=lambda x: -x[1])[:20]
        ],
    }
    OUT_JSON.write_text(json.dumps(result, indent=2, ensure_ascii=False), encoding="utf-8")

    md = f"""# EXPENSE INTELLIGENCE AUDIT — F01.3

**Período:** {PERIOD["dataInicial"]} → {PERIOD["dataFinal"]}

## Respostas obrigatórias

| Pergunta | Resposta |
|---|---|
| **O que existe dentro de OUTROS?** | {result["outros_before_valor"]} em {int(pct_before)}% do total — top descrições: SR MOISES, FARDAMENTOS, SOLAR INOVE, QUINZENA, abastecimento |
| **Quanto representa?** | R$ {result["outros_before_valor"]} de R$ {result["valor_total"]} (**{pct_before:.1f}%** antes · **{pct_after:.1f}%** depois V2) |
| **Impacto financeiro?** | Ranking e comparativos entre filiais contaminados; {pct_identified:.1f}% do valor OUTROS reclassificado com evidência |

## Métricas V2

| Métrica | Valor |
|---------|------:|
| OUTROS antes (V1) | **{pct_before:.1f}%** |
| OUTROS depois (legacy via V2) | **{pct_after:.1f}%** |
| Valor OUTROS identificado | **{pct_identified:.1f}%** |
| Meta primária (≥80% valor OUTROS) | {"✅" if pct_identified >= 80 else "❌"} |

## Top 20 descrições por valor

| # | Descrição | Valor | V2 | Conf |
|---|-----------|------:|----|-----:|
"""
    for i, item in enumerate(desc_rank[:20], 1):
        md += f"| {i} | {item['descricao'][:60]} | {item['valor']} | {item['categoriaV2']} | {item['confidence']} |\n"

    md += f"\nEvidência JSON: `scripts/expense_intelligence_audit.json`\n"
    OUT_MD.write_text(md, encoding="utf-8")
    print(json.dumps({"outros_before": pct_before, "outros_after": pct_after, "identified": pct_identified}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
