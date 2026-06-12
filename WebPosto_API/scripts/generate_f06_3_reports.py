#!/usr/bin/env python3
"""Gera relatórios F06.3 Tax & Product Fiscal Intelligence."""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
AUDIT = ROOT / "scripts" / "f06_3_tax_product_fiscal_intelligence.json"


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
    catalog = w.get("productFiscalCatalogEngine") or {}
    ncm = w.get("ncmIntelligenceEngine") or {}
    tax = w.get("taxClassificationEngine") or {}
    fin = w.get("financialClassificationEngine") or {}
    risks = w.get("fiscalRiskEngine") or {}
    exec_intel = w.get("executiveFiscalIntelligence") or {}
    cockpit = w.get("cockpit") or {}
    parecer = w.get("parecerFinal") or data.get("parecerFinal") or ""

    _w(
        "PRODUCT_FISCAL_CATALOG_REPORT.md",
        f"# Product Fiscal Catalog (F06.3)\n\n"
        f"- Total homologado: **{catalog.get('totalProdutos')}**\n"
        f"- Evidenciados: **{catalog.get('produtosEvidenciados')}**\n"
        f"- Ativos evidenciados: **{catalog.get('ativosEvidenciados')}**\n"
        f"- Sem classificação: **{catalog.get('semClassificacao')}**\n"
        f"- Combustível: **{catalog.get('combustivel')}**\n"
        f"- Loja: **{catalog.get('loja')}**\n"
        f"- Serviços: **{catalog.get('servicos')}**\n",
    )
    _w(
        "NCM_INTELLIGENCE_REPORT.md",
        f"# NCM Intelligence\n\n"
        f"- Com NCM evidenciado: **{ncm.get('comNcmEvidenciado')}**\n"
        f"- Sem NCM evidenciado: **{ncm.get('semNcmEvidenciado')}**\n"
        f"- Campo NCM no catálogo API: **{ncm.get('ncmFieldNoCatalogo')}**\n"
        f"- Duplicados: **{len(ncm.get('duplicados') or [])}**\n"
        f"- Inconsistentes: **{len(ncm.get('inconsistentes') or [])}**\n",
    )
    _w(
        "TAX_CLASSIFICATION_REPORT.md",
        f"# Tax Classification\n\n"
        f"- Cobertura tributária: **{tax.get('coberturaTributaria')}**\n"
        f"- Tributação integrada: **{tax.get('tributacaoIntegrada')}**\n"
        f"- CFOP/SPED: **{tax.get('cfopSped')}**\n\n"
        + "\n".join(
            f"- **{i.get('tributo')}**: {i.get('classificacao')} ({i.get('evidencia')})"
            for i in (tax.get("items") or [])
        )
        + "\n",
    )
    _w(
        "FINANCIAL_CLASSIFICATION_REPORT.md",
        f"# Financial Classification\n\n"
        f"- CONTA registros: **{fin.get('contaRegistros')}** ({fin.get('contaCoverage')})\n"
        f"- PLANO_CONTA registros: **{fin.get('planoContaRegistros')}** ({fin.get('planoCoverage')})\n"
        f"- Estrutura contábil: **{fin.get('estruturaContabilExiste')}**\n"
        f"- DRE possível: **{fin.get('drePossivel')}**\n"
        f"- Centro de custo possível: **{fin.get('centroCustoPossivel')}**\n"
        f"- Classificação gerencial: **{fin.get('classificacaoGerencialPossivel')}**\n",
    )
    _w(
        "FISCAL_RISK_ENGINE_REPORT.md",
        f"# Fiscal Risk Engine\n\n"
        f"- Riscos detectados: **{risks.get('total')}**\n"
        f"- Maior risco: **{ex.get('7_maiorRisco')}**\n\n"
        + "\n".join(
            f"- {r.get('produtoCodigo') or r.get('tipo')}: **{r.get('risco')}**"
            for r in (risks.get("risks") or [])[:8]
        )
        + "\n",
    )
    _w(
        "EXECUTIVE_FISCAL_INTELLIGENCE_REPORT.md",
        f"# Executive Fiscal Intelligence\n\n"
        f"- Maior risco fiscal: **{(exec_intel.get('maiorRiscoFiscal') or {}).get('produtoCodigo') or (exec_intel.get('maiorRiscoFiscal') or {}).get('tipo')}**\n"
        f"- Maior oportunidade: **{exec_intel.get('maiorOportunidadeFiscal')}**\n"
        f"- Produto mais crítico: **{(exec_intel.get('produtoMaisCritico') or {}).get('produtoCodigo')}**\n"
        f"- Categoria mais crítica: **{exec_intel.get('categoriaMaisCritica')}**\n"
        f"- Cobertura fiscal R02: **{exec_intel.get('coberturaFiscalAtual')}%**\n",
    )
    _w(
        "FISCAL_INTELLIGENCE_COCKPIT_REPORT.md",
        f"# Fiscal Intelligence Cockpit\n\n"
        f"- View: **`fiscal-intelligence`**\n"
        f"- API: `/api/v1/fiscal-intelligence/cockpit`\n"
        f"- Widgets: Produtos, NCM, Classificação, Riscos, Cobertura Fiscal\n"
        f"- Produtos: **{cockpit.get('produtos')}**\n"
        f"- NCM evidenciado: **{cockpit.get('ncmComEvidencia')}**\n"
        f"- Tributação: **{cockpit.get('classificacaoTributaria')}**\n"
        f"- Riscos: **{cockpit.get('riscosFiscais')}**\n",
    )
    _w(
        "DW_FISCAL_INTELLIGENCE_MODEL.md",
        f"# DW Fiscal Intelligence Model\n\n"
        f"- `fact_fiscal_product`\n"
        f"- `fact_fiscal_ncm`\n"
        f"- `fact_fiscal_risk`\n"
        f"- `fact_fiscal_classification`\n"
        f"- DDL: `dw/ddl/fact_fiscal_intelligence.sql`\n",
    )
    _w(
        "FISCAL_INTELLIGENCE_QA_REPORT.md",
        f"# Fiscal Intelligence QA Gate\n\n"
        f"| Critério | OK |\n|---|---|\n"
        f"| Sem produto sem origem | {qa.get('semProdutoSemOrigem')} |\n"
        f"| Sem produto sem lineage | {qa.get('semProdutoSemLineage')} |\n"
        f"| Sem cálculo fiscal sem origem | {qa.get('semCalculoFiscalSemOrigem')} |\n"
        f"| Sem NCM inventado | {qa.get('semNcmInventado')} |\n"
        f"| Sem classificação inventada | {qa.get('semClassificacaoInventada')} |\n"
        f"| Sem cross-tenant | {qa.get('semCrossTenant')} |\n"
        f"| Motor auditável | {qa.get('motorAuditavel')} |\n"
        f"| Lineage completo | {qa.get('lineageCompleto')} |\n\n"
        f"{parecer}\n",
    )
    _w(
        "F06_3_TAX_PRODUCT_FISCAL_INTELLIGENCE_REPORT.md",
        f"# F06.3 — Tax & Product Fiscal Intelligence\n\n"
        f"## Respostas executivas 1–20\n\n"
        + "\n".join(f"{k}: {v}" for k, v in sorted(ex.items()))
        + f"\n\n## Critérios de aceite\n\n"
        f"- WebPosto live: **False**\n"
        f"- SPED: **False** (sem integração)\n"
        f"- Trust executivo: **{ex.get('trustExecutivo')}**\n\n"
        f"{parecer}\n",
    )


if __name__ == "__main__":
    main()
