#!/usr/bin/env python3
"""Gera relatórios F06.4 Fiscal Reconciliation Hub."""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
AUDIT = ROOT / "scripts" / "f06_4_fiscal_reconciliation_hub.json"


def _load() -> dict:
    return json.loads(AUDIT.read_text(encoding="utf-8"))


def _w(name: str, body: str) -> None:
    p = ROOT / name
    p.write_text(body, encoding="utf-8")
    print(f"Wrote {p}")


def main() -> None:
    data = _load()
    w = data.get("windows", {}).get("7d") or {}
    ex = w.get("executiveAnswers") or data.get("executiveAnswers") or {}
    qa = w.get("qa") or {}
    lineage = w.get("fiscalLineageEngine") or {}
    nfce = w.get("nfceVendaReconciliation") or {}
    prod = w.get("productSalesReconciliation") or {}
    lmc = w.get("lmcSalesReconciliation") or {}
    bridge = w.get("fiscalFinancialBridge") or {}
    risks = w.get("fiscalRiskConsolidation") or {}
    cockpit = w.get("cockpit") or {}
    parecer = w.get("parecerFinal") or data.get("parecerFinal") or ""

    _w(
        "FISCAL_LINEAGE_ENGINE_REPORT.md",
        f"# Fiscal Lineage Engine (F06.4)\n\n"
        f"- Itens mapeados: **{lineage.get('total')}**\n"
        f"- Cobertura: **{lineage.get('coverage')}**\n"
        f"- Campos: empresa, venda, item, produto, NFCE, LMC, conta, plano gerencial\n\n"
        f"## Amostra\n\n"
        + "\n".join(
            f"- Venda **{i.get('vendaCodigo')}** → NFCE **{i.get('nfceCodigo')}** → Produto **{i.get('produtoCodigo')}**"
            for i in (lineage.get("items") or [])[:5]
        )
        + "\n",
    )
    _w(
        "NFCE_VENDA_RECONCILIATION_REPORT.md",
        f"# NFCE × Venda Reconciliation\n\n"
        f"- Vendas total: **{nfce.get('vendasTotal')}**\n"
        f"- Conciliadas: **{nfce.get('nfceMatched')}**\n"
        f"- Cobertura: **{nfce.get('coveragePct')}%**\n"
        f"- Venda sem NFCE: **{nfce.get('vendaSemNfce')}**\n"
        f"- NFCE divergente: **{nfce.get('nfceDivergente')}**\n"
        f"- Cancelamentos: **{nfce.get('cancelamentos')}**\n",
    )
    _w(
        "PRODUCT_SALES_RECONCILIATION_REPORT.md",
        f"# Produto × Venda Item Reconciliation\n\n"
        f"- Itens conciliados: **{prod.get('itensConciliados')}** / **{prod.get('itensTotal')}**\n"
        f"- Cobertura: **{prod.get('coveragePct')}%**\n"
        f"- Produtos com NCM: **{prod.get('produtosComNcm')}**\n"
        f"- Produto sem NCM: **{prod.get('produtoSemNcm')}**\n"
        f"- Item sem produto: **{prod.get('itemSemProduto')}**\n"
        f"- NCM ausente: **{prod.get('ncmAusente')}**\n",
    )
    _w(
        "LMC_SALES_RECONCILIATION_REPORT.md",
        f"# LMC × Venda Reconciliation\n\n"
        f"- Litros vendidos: **{lmc.get('litrosVendidos')}**\n"
        f"- Litros LMC: **{lmc.get('litrosLmc')}**\n"
        f"- Litros conciliados: **{lmc.get('litrosConciliados')}**\n"
        f"- Litros sem LMC: **{lmc.get('litrosSemLmc')}**\n"
        f"- LMC sem venda: **{lmc.get('lmcSemVenda')}**\n"
        f"- Perda não conciliada: **{lmc.get('perdaNaoConciliada')}**\n"
        f"- Sobra não conciliada: **{lmc.get('sobraNaoConciliada')}**\n",
    )
    _w(
        "FISCAL_FINANCIAL_CLASSIFICATION_REPORT.md",
        f"# Fiscal × Financial Classification\n\n"
        f"- DRE fiscal viável: **{bridge.get('dreFiscalViavel')}**\n"
        f"- Classificação gerencial viável: **{bridge.get('classificacaoGerencialViavel')}**\n"
        f"- Centro de custo disponível: **{bridge.get('centroCustoDisponivel')}**\n"
        f"- Centro custo 401 bloqueado: **{bridge.get('centroCustoBlocked401')}**\n"
        f"- CONTA registros: **{bridge.get('contaRegistros')}**\n"
        f"- PLANO_CONTA registros: **{bridge.get('planoContaRegistros')}**\n",
    )
    _w(
        "FISCAL_RISK_CONSOLIDATION_REPORT.md",
        f"# Fiscal Risk Consolidation\n\n"
        f"- Total riscos: **{risks.get('total')}**\n"
        f"- Maior risco: **{ex.get('9_maiorRiscoConsolidado')}**\n"
        f"- Filial mais crítica: **{ex.get('10_filialMaisCritica')}**\n"
        f"- Produto mais crítico: **{ex.get('11_produtoMaisCritico')}**\n\n"
        + "\n".join(
            f"- **{r.get('dominio')}**: {r.get('risco')} (filial {r.get('empresaCodigo') or '—'})"
            for r in (risks.get("risks") or [])[:8]
        )
        + "\n",
    )
    _w(
        "FISCAL_RECONCILIATION_COCKPIT_REPORT.md",
        f"# Fiscal Reconciliation Cockpit\n\n"
        f"- View: **`fiscal-reconciliation`**\n"
        f"- API: `/api/v1/fiscal-reconciliation/cockpit`\n"
        f"- Widgets: Lineage, Divergências NFCE, Divergências LMC, Produtos críticos, Risco consolidado\n"
        f"- Trust: **{cockpit.get('trustExecutivo')}**\n",
    )
    _w(
        "DW_FISCAL_RECONCILIATION_MODEL.md",
        f"# DW Fiscal Reconciliation Model\n\n"
        f"- `fact_fiscal_reconciliation`\n"
        f"- `fact_fiscal_lineage`\n"
        f"- `fact_fiscal_risk_consolidated`\n"
        f"- `fact_fiscal_financial_bridge`\n"
        f"- DDL: `dw/ddl/fact_fiscal_reconciliation_hub.sql`\n",
    )
    _w(
        "FISCAL_RECONCILIATION_QA_REPORT.md",
        f"# Fiscal Reconciliation QA Gate\n\n"
        f"| Critério | OK |\n|---|---|\n"
        f"| Sem lineage sem origem | {qa.get('semLineageSemOrigem')} |\n"
        f"| Sem conciliação sem evidência | {qa.get('semConciliacaoSemEvidencia')} |\n"
        f"| Sem produto/NCM inventado | {qa.get('semProdutoNcmInventado')} |\n"
        f"| Sem LMC sem fonte | {qa.get('semLmcSemFonte')} |\n"
        f"| Sem NFCE sem fonte | {qa.get('semNfceSemFonte')} |\n"
        f"| Sem cross-tenant | {qa.get('semCrossTenant')} |\n"
        f"| Motor auditável | {qa.get('motorAuditavel')} |\n"
        f"| Lineage completo | {qa.get('lineageCompleto')} |\n\n"
        f"{parecer}\n",
    )
    _w(
        "F06_4_FISCAL_RECONCILIATION_HUB_REPORT.md",
        f"# F06.4 — Fiscal Reconciliation Hub\n\n"
        f"## Respostas executivas 1–20\n\n"
        + "\n".join(f"{k}: {v}" for k, v in sorted(ex.items()))
        + f"\n\n## Critérios de aceite\n\n"
        f"- WebPosto live: **False**\n"
        f"- SPED: **False**\n"
        f"- Snapshots homologados: **True**\n"
        f"- Trust executivo: **{ex.get('trustExecutivo')}**\n\n"
        f"{parecer}\n",
    )


if __name__ == "__main__":
    main()
