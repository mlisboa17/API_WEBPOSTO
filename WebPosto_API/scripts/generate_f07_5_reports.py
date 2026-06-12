#!/usr/bin/env python3
"""Gera relatórios F07.5 Product Opportunity & Assortment Intelligence."""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
AUDIT = ROOT / "scripts" / "f07_5_product_opportunity_assortment.json"


def _load() -> dict:
    return json.loads(AUDIT.read_text(encoding="utf-8"))


def _w(name: str, body: str) -> None:
    p = ROOT / name
    p.write_text(body, encoding="utf-8")
    print(f"Wrote {p}")


def main() -> None:
    data = _load()
    w = data.get("windows", {}).get("7d") or {}
    ex = w.get("executiveAnswers") or {}
    ass = w.get("productOpportunityAssortment") or {}
    leaders = ass.get("marginLeaders") or {}
    low = ass.get("highVolumeLowMargin") or {}
    exp = ass.get("expansionPotential") or {}
    gap = ass.get("branchBenchmarkGap") or {}
    focus = ass.get("commercialFocus") or {}
    fuel = ass.get("fuelDependencyRisk") or {}
    qa = w.get("qa") or {}
    parecer = w.get("parecerFinal") or ""

    _w(
        "MARGIN_LEADERS_REPORT.md",
        f"# IA-1 — Margin Leaders\n\n"
        f"- Top margem: **{leaders.get('topProdutoMargemPct', {}).get('produtoCodigo')}**\n"
        f"- Margem %: **{leaders.get('topProdutoMargemPct', {}).get('margemPct')}**\n"
        f"- Ranking: **{len(leaders.get('rankingMargemPct') or [])}** produtos\n",
    )
    _w(
        "HIGH_VOLUME_LOW_MARGIN_REPORT.md",
        f"# IA-2 — High Volume Low Margin\n\n"
        f"- Benchmark margem: **{low.get('benchmarkMargemPct')}%**\n"
        f"- Alertas: **{low.get('totalAlertas')}**\n",
    )
    _w(
        "EXPANSION_POTENTIAL_REPORT.md",
        f"# IA-3 — Expansion Potential\n\n"
        f"- Produtos com potencial: **{exp.get('totalPotencial')}**\n",
    )
    _w(
        "BRANCH_BENCHMARK_GAP_REPORT.md",
        f"# IA-4 — Branch Benchmark Gap\n\n"
        f"- Benchmark mix PV: **{gap.get('benchmarkMixProdutosVendidosPct')}%**\n"
        f"- Filiais abaixo: **{gap.get('totalAbaixoBenchmark')}**\n",
    )
    _w(
        "COMMERCIAL_FOCUS_REPORT.md",
        f"# IA-5 — Commercial Focus\n\n"
        f"- Produtos foco: **{focus.get('totalFoco')}**\n",
    )
    _w(
        "FUEL_DEPENDENCY_RISK_REPORT.md",
        f"# IA-6 — Fuel Dependency Risk\n\n"
        f"- Threshold: **{fuel.get('thresholdDependenciaPct')}%**\n"
        f"- Filiais risco: **{fuel.get('totalFiliaisRisco')}**\n"
        f"- Rede excessiva: **{fuel.get('dependenciaRedeExcessiva')}**\n",
    )
    _w(
        "DW_ASSORTMENT_INTELLIGENCE_REPORT.md",
        f"# IA-7 — DW Assortment\n\nVer `dw/ddl/fact_product_assortment_f075.sql`\n",
    )
    _w(
        "ASSORTMENT_QA_REPORT.md",
        f"# IA-8 — Assortment QA\n\n"
        f"- Lineage: **{qa.get('assortmentComLineage')}**\n"
        f"- Motor decisão: **{qa.get('motorDecisaoComercial')}**\n"
        f"- Sem conveniência: **{qa.get('semTermoConveniencia')}**\n",
    )
    ex_lines = "\n".join(f"{k}: {v}" for k, v in sorted(ex.items()))
    _w(
        "F07_5_PRODUCT_OPPORTUNITY_ASSORTMENT_REPORT.md",
        f"# F07.5 — Product Opportunity & Assortment Intelligence\n\n"
        f"Fonte: **{w.get('fonte', {}).get('modo')}**\n\n"
        f"## Respostas executivas 1–20\n\n{ex_lines}\n\n{parecer}\n",
    )


if __name__ == "__main__":
    main()
