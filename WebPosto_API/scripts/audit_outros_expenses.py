#!/usr/bin/env python3
"""Auditoria profunda categoria OUTROS — Sprint F01.2."""
from __future__ import annotations

import asyncio
import json
import sys
import unicodedata
from collections import Counter, defaultdict
from decimal import Decimal
from pathlib import Path

import httpx

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src.core.config import load_core_config
from src.services.logos_expense_classifier import classify_logos_expense

PERIOD = {"dataInicial": "2026-06-01", "dataFinal": "2026-06-07"}
OUT_JSON = ROOT / "scripts" / "outros_expenses_audit.json"
OUT_MD = ROOT / "OUTROS_EXPENSES_DEEP_AUDIT.md"


def _norm(text: str) -> str:
    s = str(text or "").strip().casefold()
    return "".join(c for c in unicodedata.normalize("NFD", s) if unicodedata.category(c) != "Mn")


async def main() -> int:
    config = load_core_config()
    async with httpx.AsyncClient() as client:
        r = await client.get(
            f"{config.webposto_base_url}/INTEGRACAO/CONSULTAR_DESPESAS_FINANCEIRO_REDE",
            params={**PERIOD, "CHAVE": config.webposto_api_key},
            timeout=120,
        )
        rows = r.json() if r.status_code == 200 else []
        if isinstance(rows, dict):
            rows = rows.get("resultados") or rows.get("data") or []

    outros_rows = []
    desc_counter: Counter = Counter()
    valor_outros = Decimal("0")
    valor_total = Decimal("0")
    reclass_suggestions: dict[str, Counter] = defaultdict(Counter)

    for row in rows:
        if not isinstance(row, dict):
            continue
        val = Decimal(str(row.get("valor") or 0))
        valor_total += val
        desc = str(row.get("descricaoDocumento") or row.get("planoConta") or "")
        plano = str(row.get("planoContaGerencialDescricao") or "")
        cat = classify_logos_expense(desc, plano)
        if cat != "OUTROS":
            continue
        outros_rows.append(row)
        valor_outros += val
        key = desc[:80] or "(vazio)"
        desc_counter[key] += 1
        for trial in ("OPERACIONAL", "PESSOAL", "ADMINISTRATIVA", "COMERCIAL", "COMPRAS", "FINANCEIRO"):
            if trial != "OUTROS":
                reclass_suggestions[trial][_norm(desc)] += 1

    pct = float(valor_outros / valor_total * 100) if valor_total else 0
    top_desc = desc_counter.most_common(20)

    result = {
        "period": PERIOD,
        "total_registros": len(rows),
        "outros_registros": len(outros_rows),
        "valor_total": str(valor_total.quantize(Decimal("0.01"))),
        "valor_outros": str(valor_outros.quantize(Decimal("0.01"))),
        "pct_outros": round(pct, 2),
        "top_descriptions": [{"desc": d, "count": c} for d, c in top_desc],
    }
    OUT_JSON.write_text(json.dumps(result, indent=2, ensure_ascii=False), encoding="utf-8")

    md = f"""# OUTROS EXPENSES DEEP AUDIT — F01.2

**Período:** {PERIOD["dataInicial"]} → {PERIOD["dataFinal"]}

## Respostas obrigatórias

| Pergunta | Resposta |
|---|---|
| **Quais descrições compõem OUTROS?** | Top 20 abaixo (amostra {len(outros_rows)} registros) |
| **Quanto valor em OUTROS?** | R$ {result["valor_outros"]} de R$ {result["valor_total"]} (**{pct:.1f}%**) |
| **Reclassificar automaticamente?** | **Parcial** — expandir keywords em `logos_expense_classifier.py` |
| **Novas categorias?** | Manter 7 LOGOS; mapear padrões recorrentes OUTROS → FINANCEIRO/COMPRAS |

## Top 20 descrições OUTROS

| # | Descrição | Qtd |
|---|-----------|----:|
"""
    for i, (desc, cnt) in enumerate(top_desc, 1):
        md += f"| {i} | {desc[:70]} | {cnt} |\n"

    md += f"""
## Meta redução OUTROS

| Atual | Meta F01.3 |
|------:|-----------:|
| **{pct:.1f}%** | **< 15%** |

## Ações recomendadas (sem implementar nesta sprint)

1. Adicionar keywords para top 10 descrições OUTROS
2. Revisão manual amostra 50 registros OUTROS > R$ 500
3. Validar após reclassificação em F01.3 BI

Evidência JSON: `scripts/outros_expenses_audit.json`
"""
    OUT_MD.write_text(md, encoding="utf-8")
    print(f"OUTROS: {pct:.1f}% — gravado {OUT_MD}")
    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
