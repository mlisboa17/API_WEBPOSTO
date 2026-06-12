#!/usr/bin/env python3
"""Gera relatórios F07.2 Product Master Enrichment."""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
AUDIT = ROOT / "scripts" / "f07_2_product_master_enrichment.json"


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
    cov = w.get("productMasterCoverage") or {}
    rec = w.get("productMatchRecovery") or {}
    hier = w.get("productHierarchyDiscovery") or {}
    dept = w.get("departmentIntelligence") or {}
    rev = w.get("productRevenueIntelligence") or {}
    mix = w.get("branchProductMix") or {}
    cockpit = w.get("cockpit") or {}
    qa = w.get("qa") or {}
    kpi = w.get("produtosVendidosKpiEngine") or {}
    parecer = w.get("parecerFinal") or ""

    _w(
        "PRODUCT_MASTER_COVERAGE_REPORT.md",
        f"# IA-1 — Product Master Coverage\n\n"
        f"- Produtos existem (master): **{cov.get('produtosExistem')}**\n"
        f"- PRODUTO base: **{cov.get('produtosNoProdutoBase')}**\n"
        f"- Vendidos NF: **{cov.get('produtosVendidosNaoCombustivel')}**\n"
        f"- Sem cadastro (final): **{cov.get('produtosVendidosSemCadastro')}**\n"
        f"- Sem descrição: **{cov.get('produtosSemDescricao')}**\n"
        f"- Sem departamento: **{cov.get('produtosSemDepartamento')}**\n"
        f"- Cobertura F07.1: **{cov.get('coberturaCatalogoAtualPct')}%**\n"
        f"- Cobertura final: **{cov.get('coberturaCatalogoFinalPct')}%**\n",
    )
    _w(
        "PRODUCT_MATCH_RECOVERY_REPORT.md",
        f"# IA-2 — Product Match Recovery\n\n"
        f"- Antes sem match: **{rec.get('antesSemMatch')}**\n"
        f"- Depois sem match: **{rec.get('depoisSemMatch')}**\n"
        f"- Recuperados: **{rec.get('produtosRecuperados')}**\n"
        f"- Taxa recuperação: **{rec.get('taxaRecuperacaoPct')}%**\n"
        f"- Fontes: **{rec.get('fontesRecuperacao')}**\n",
    )
    _w(
        "PRODUCT_HIERARCHY_DISCOVERY_REPORT.md",
        f"# IA-3 — Product Hierarchy Discovery\n\n"
        f"- Grupos distintos: **{hier.get('gruposDistintos')}**\n"
        f"- Subgrupos distintos: **{hier.get('subgruposDistintos')}**\n"
        f"- NCMs distintos: **{hier.get('ncmsDistintos')}**\n",
    )
    dept_rows = "\n".join(
        f"- **{r.get('departamento')}**: R$ {r.get('receita')} · {r.get('itens')} itens"
        for r in (dept.get("receitaPorDepartamento") or [])
    )
    _w(
        "DEPARTMENT_INTELLIGENCE_REPORT.md",
        f"# IA-4 — Department Intelligence\n\n{dept_rows}\n\n"
        f"Top: **{(dept.get('topDepartamento') or {}).get('departamento')}**\n"
        f"Sem venda: **{dept.get('departamentosSemVenda')}**\n",
    )
    _w(
        "PRODUCT_REVENUE_INTELLIGENCE_REPORT.md",
        f"# IA-5 — Product Revenue Intelligence\n\n"
        f"- Top receita: **{(rev.get('topReceita') or [{}])[0]}**\n"
        f"- Pareto 80/20 produtos: **{rev.get('produtosPareto80')}**\n"
        f"- Concentração top 5: **{rev.get('concentracaoTop5Pct')}%**\n",
    )
    _w(
        "BRANCH_PRODUCT_MIX_REPORT.md",
        f"# IA-6 — Branch Product Mix\n\n"
        f"- Melhor mix: **{(mix.get('filialMelhorMix') or {}).get('empresaCodigo')}**\n"
        f"- Mais dependente combustível: **{(mix.get('filialMaisDependenteCombustivel') or {}).get('empresaCodigo')}**\n",
    )
    _w(
        "PRODUCT_COCKPIT_EXPANSION_REPORT.md",
        f"# IA-7 — Product Cockpit Expansion\n\n"
        f"- Título: **{cockpit.get('tituloVisual')}**\n"
        f"- Sem cadastro: **{cockpit.get('produtosSemCadastro')}**\n"
        f"- Pareto 80: **{cockpit.get('produtosPareto80')}** produtos\n"
        f"- Cobertura final: **{cockpit.get('coberturaCatalogoFinalPct')}%**\n",
    )
    _w(
        "DW_PRODUCT_MASTER_REPORT.md",
        f"# IA-8 — DW Product Master\n\n"
        f"Ver `dw/ddl/dim_product_master_f072.sql`\n\n"
        f"- dim_product_master\n- dim_product_department\n- fact_product_sales\n- fact_product_mix\n- fact_product_revenue\n",
    )
    _w(
        "PRODUCT_MASTER_QA_REPORT.md",
        f"# IA-9 — Product Master QA\n\n"
        f"- Recuperados: **{qa.get('produtosRecuperados')}**\n"
        f"- Ainda sem match: **{qa.get('produtosAindaSemMatch')}**\n"
        f"- Cobertura final: **{qa.get('coberturaFinalPct')}%**\n"
        f"- Superior F07.1: **{qa.get('coberturaSuperiorF071')}**\n"
        f"- Redução sem match: **{qa.get('reducaoSemMatch')}**\n",
    )
    ex_lines = "\n".join(f"{k}: {v}" for k, v in sorted(ex.items()))
    _w(
        "F07_2_PRODUCT_MASTER_ENRICHMENT_REPORT.md",
        f"# F07.2 — Product Master Enrichment\n\n"
        f"Fonte: **{w.get('fonte', {}).get('modo')}**\n\n"
        f"## Respostas executivas 1–20\n\n{ex_lines}\n\n{parecer}\n",
    )


if __name__ == "__main__":
    main()
