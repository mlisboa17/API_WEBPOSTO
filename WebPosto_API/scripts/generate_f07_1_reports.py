#!/usr/bin/env python3
"""Gera relatórios F07.1 Produtos Vendidos."""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
AUDIT = ROOT / "scripts" / "f07_1_produtos_vendidos_catalogo_departamentalizacao.json"


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
    pag = w.get("paginationEngine") or {}
    cat = w.get("productCatalogCompleteness") or {}
    dept = w.get("productDepartmentClassification") or {}
    rec = w.get("salesCoverageReconciliation") or {}
    kpi = w.get("produtosVendidosKpiEngine") or {}
    rank = w.get("productRankingEngine") or {}
    branch = w.get("branchProductAnalytics") or {}
    lineage = w.get("productSalesLineage") or {}
    cockpit = w.get("cockpit") or {}
    qa = w.get("qa") or {}
    parecer = w.get("parecerFinal") or ""

    _w(
        "PRODUCT_PAGINATION_ENGINE_REPORT.md",
        f"# IA-1 — Pagination Engine\n\n"
        f"### PRODUTO\n"
        f"- Páginas: **{pag.get('produto', {}).get('pages')}**\n"
        f"- Registros: **{pag.get('produto', {}).get('count')}**\n"
        f"- Truncado: **{pag.get('produto', {}).get('truncated')}**\n"
        f"- Sem duplicidade: **{pag.get('produto', {}).get('semDuplicidade')}**\n\n"
        f"### VENDA_ITEM\n"
        f"- Páginas: **{pag.get('vendaItem', {}).get('pages')}**\n"
        f"- Registros: **{pag.get('vendaItem', {}).get('count')}**\n"
        f"- Sem perda por página: **{pag.get('vendaItem', {}).get('semPerdaPorPagina')}**\n",
    )
    _w(
        "PRODUCT_CATALOG_COMPLETENESS_REPORT.md",
        f"# IA-2 — Product Catalog Completeness\n\n"
        f"- Catálogo: **{cat.get('produtosNoCatalogo')}**\n"
        f"- Vendidos: **{cat.get('produtosVendidos')}**\n"
        f"- Sem cadastro: **{cat.get('produtosVendidosSemCadastro')}**\n"
        f"- Sem descrição: **{cat.get('produtosSemDescricao')}**\n"
        f"- Cobertura: **{cat.get('coberturaCadastroPct')}%**\n",
    )
    dept_rows = "\n".join(
        f"- **{k}**: {v}" for k, v in (dept.get("porDepartamentoCatalogo") or {}).items()
    )
    _w(
        "PRODUCT_DEPARTMENT_CLASSIFICATION_REPORT.md",
        f"# IA-3 — Department Classification\n\n"
        f"Departamentos oficiais (sem Conveniência):\n\n{dept_rows}\n",
    )
    _w(
        "PRODUCT_SALES_COVERAGE_RECONCILIATION_REPORT.md",
        f"# IA-4 — Sales Coverage Reconciliation\n\n"
        f"- Receita combustível: **R$ {rec.get('receitaCombustivel')}**\n"
        f"- Receita produtos vendidos: **R$ {rec.get('receitaProdutosVendidos')}**\n"
        f"- F07.0 receita: **R$ {rec.get('f07_0_receitaProdutosVendidos')}**\n"
        f"- Gap F07.0→F07.1: **R$ {rec.get('gapReceitaF070vsF071')}**\n",
    )
    _w(
        "PRODUTOS_VENDIDOS_KPI_REPORT.md",
        f"# IA-5 — Produtos Vendidos KPI\n\n"
        f"- Valor total: **R$ {kpi.get('valorTotalProdutosVendidos')}**\n"
        f"- Itens: **{kpi.get('quantidadeItensProdutosVendidos')}**\n"
        f"- Ticket médio: **R$ {kpi.get('ticketMedioProdutosVendidos')}**\n"
        f"- Participação: **{kpi.get('participacaoNoFaturamentoPct')}%**\n"
        f"- Produtos distintos: **{kpi.get('produtosDistintosVendidos')}**\n",
    )
    br_rows = "\n".join(
        f"| {f.get('empresaCodigo')} | {f.get('nomeFilial')} | {f.get('valorProdutosVendidos')} | {f.get('departamentoDominante')} |"
        for f in (branch.get("filiais") or [])
    )
    _w(
        "BRANCH_PRODUCT_ANALYTICS_REPORT.md",
        f"# IA-6 — Branch Product Analytics\n\n"
        f"| Filial | Nome | Produtos Vendidos R$ | Dept. dominante |\n|---|---|---|---|\n{br_rows}\n",
    )
    _w(
        "PRODUTOS_VENDIDOS_COCKPIT_REPORT.md",
        f"# IA-7 — Cockpit Produtos Vendidos\n\n"
        f"- View: **`non-fuel-products`**\n"
        f"- Label: **Produtos Vendidos**\n"
        f"- Receita: **R$ {cockpit.get('receitaProdutosVendidos')}**\n"
        f"- Não classificados: **{cockpit.get('produtosNaoClassificados')}**\n",
    )
    _w(
        "DW_PRODUCT_DEPARTMENT_MODEL.md",
        f"# IA-8 — DW Product Department Layer\n\n"
        f"- `fact_product_sales`\n"
        f"- `fact_product_department_sales`\n"
        f"- `fact_product_coverage`\n"
        f"- `dim_product`\n"
        f"- `dim_product_department`\n"
        f"- DDL: `dw/ddl/fact_product_sales_f071.sql`\n",
    )
    _w(
        "PRODUTOS_VENDIDOS_QA_REPORT.md",
        f"# IA-9 — QA\n\n"
        f"| Critério | OK |\n|---|---|\n"
        f"| Paginação completa | {qa.get('paginacaoCompleta')} |\n"
        f"| Sem venda sem empresaCodigo | {qa.get('semVendaSemEmpresaCodigo')} |\n"
        f"| Sem departamento inventado | {qa.get('semDepartamentoInventado')} |\n"
        f"| Sem combustível misturado | {qa.get('semCombustivelMisturado')} |\n"
        f"| Motor auditável | {qa.get('motorAuditavel')} |\n\n"
        f"{parecer}\n",
    )
    _w(
        "F07_1_PRODUTOS_VENDIDOS_CATALOGO_DEPARTAMENTALIZACAO_REPORT.md",
        f"# F07.1 — Produtos Vendidos: Catálogo & Departamentalização\n\n"
        f"Fonte: **{w.get('fonte', {}).get('modo')}**\n\n"
        f"## Respostas executivas 1–20\n\n"
        + "\n".join(f"{k}: {v}" for k, v in sorted(ex.items()))
        + f"\n\n{parecer}\n",
    )


if __name__ == "__main__":
    main()
