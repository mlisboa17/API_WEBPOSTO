#!/usr/bin/env python3
"""Gera relatórios F07.0 Non-Fuel Product Sales."""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
AUDIT = ROOT / "scripts" / "f07_0_non_fuel_product_sales.json"


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
    qa = w.get("qa") or {}
    multi = w.get("multiTenantScalabilityEngine") or {}
    disc = w.get("productDepartmentDiscovery") or {}
    sales = w.get("nonFuelSalesEngine") or {}
    rank = w.get("productRankingEngine") or {}
    branch = w.get("branchDepartmentAnalytics") or {}
    lineage = w.get("productSalesLineage") or {}
    cockpit = w.get("cockpit") or {}
    parecer = w.get("parecerFinal") or ""

    _w(
        "MULTI_TENANT_SCALABILITY_REPORT.md",
        f"# Multi-Tenant Scalability (F07.0)\n\n"
        f"- Premissa: **{multi.get('premissaOficial')}**\n"
        f"- empresaCodigo obrigatório: **{multi.get('empresaCodigoObrigatorio')}**\n"
        f"- Pronto para N filiais: **{multi.get('prontoParaNFiliais')}**\n"
        f"- Tokens isolados necessários: **{multi.get('tokensIsoladosNecessarios')}**\n"
        f"- Segregação lógica confiável: **{multi.get('segregacaoLogicaConfiavel')}**\n"
        f"- Filiais: `{multi.get('filiaisHomologadas')}`\n",
    )
    dept_rows = "\n".join(f"- **{k}**: {v}" for k, v in (disc.get("porDepartamento") or {}).items())
    _w(
        "PRODUCT_DEPARTMENT_DISCOVERY_REPORT.md",
        f"# Product Department Discovery\n\n"
        f"- Total produtos catalogados: **{disc.get('totalProdutos')}**\n"
        f"- Combustível: **{disc.get('combustivel')}**\n"
        f"- Não combustível: **{disc.get('naoCombustivel')}**\n\n"
        f"## Por departamento\n\n{dept_rows}\n",
    )
    _w(
        "NON_FUEL_SALES_ENGINE_REPORT.md",
        f"# Non-Fuel Sales Engine\n\n"
        f"- Valor total não combustível: **R$ {sales.get('valorTotalNaoCombustivel')}**\n"
        f"- Itens não combustível: **{sales.get('itensNaoCombustivel')}**\n"
        f"- Ticket médio: **R$ {sales.get('ticketMedioNaoCombustivel')}**\n"
        f"- Participação no faturamento: **{sales.get('participacaoNaoCombustivelPct')}%**\n",
    )
    rank_rows = "\n".join(
        f"| {r.get('produtoCodigo')} | {r.get('nome')} | {r.get('qtd')} | {r.get('valor')} |"
        for r in (rank.get("rankingProdutos") or [])[:8]
    )
    _w(
        "PRODUCT_RANKING_REPORT.md",
        f"# Product Ranking\n\n| Produto | Nome | Qtd | Valor |\n|---|---|---|---|\n{rank_rows}\n",
    )
    br_rows = "\n".join(
        f"| {f.get('empresaCodigo')} | {f.get('nomeFilial')} | {f.get('valorNaoCombustivel')} | {f.get('participacaoNaoCombustivelPct')}% |"
        for f in (branch.get("filiais") or [])
    )
    _w(
        "BRANCH_DEPARTMENT_ANALYTICS_REPORT.md",
        f"# Branch Department Analytics\n\n| Filial | Nome | Valor NF | Part. NF |\n|---|---|---|---|\n{br_rows}\n",
    )
    _w(
        "PRODUCT_SALES_LINEAGE_REPORT.md",
        f"# Product Sales Lineage\n\n"
        f"- Itens com lineage: **{lineage.get('total')}**\n"
        f"- Sem empresaCodigo: **{lineage.get('semEmpresa')}**\n"
        f"- Sem lineage: **{lineage.get('semLineage')}**\n",
    )
    _w(
        "NON_FUEL_PRODUCTS_COCKPIT_REPORT.md",
        f"# Non-Fuel Products Cockpit\n\n"
        f"- View: **`non-fuel-products`**\n"
        f"- Label: **Produtos Vendidos**\n"
        f"- API: `/api/v1/non-fuel-products/cockpit`\n"
        f"- Faturamento NF: **R$ {cockpit.get('faturamentoNaoCombustivel')}**\n",
    )
    _w(
        "DW_NON_FUEL_PRODUCT_SALES_MODEL.md",
        f"# DW Non-Fuel Product Sales\n\n"
        f"- `fact_non_fuel_sales`\n"
        f"- `fact_product_department_sales`\n"
        f"- `fact_product_ranking`\n"
        f"- `dim_product_department`\n"
        f"- `dim_product_category`\n"
        f"- DDL: `dw/ddl/fact_non_fuel_product_sales.sql`\n",
    )
    _w(
        "NON_FUEL_PRODUCT_SALES_QA_REPORT.md",
        f"# Non-Fuel Product Sales QA\n\n"
        f"| Critério | OK |\n|---|---|\n"
        f"| Sem produto sem origem | {qa.get('semProdutoSemOrigem')} |\n"
        f"| Sem venda sem empresaCodigo | {qa.get('semVendaSemEmpresaCodigo')} |\n"
        f"| Sem cross-tenant lógico | {qa.get('semCrossTenantLogico')} |\n"
        f"| Sem combustível misturado | {qa.get('semCombustivelMisturado')} |\n"
        f"| Motor auditável | {qa.get('motorAuditavel')} |\n\n"
        f"{parecer}\n",
    )
    _w(
        "F07_0_NON_FUEL_PRODUCT_SALES_REPORT.md",
        f"# F07.0 — Non-Fuel Product Sales\n\n"
        f"## Respostas executivas 1–20\n\n"
        + "\n".join(f"{k}: {v}" for k, v in sorted(ex.items()))
        + f"\n\n{parecer}\n",
    )


if __name__ == "__main__":
    main()
