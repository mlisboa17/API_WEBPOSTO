#!/usr/bin/env python3
"""Gera relatórios F07.0A Product Coverage Truth Audit."""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
AUDIT = ROOT / "scripts" / "f07_0a_product_coverage_truth_audit.json"


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
    cat = w.get("productCatalogAudit") or {}
    disc = w.get("categoryDiscovery") or {}
    cov = w.get("productCoverageAudit") or {}
    miss = w.get("missingProductDetection") or {}
    rev = w.get("revenueCoverageAudit") or {}
    store = w.get("storeSalesDiscovery") or {}
    ch = w.get("executiveChallenge") or {}
    dw = w.get("dwCoverage") or {}
    qa = w.get("qa") or {}
    parecer = w.get("parecerFinal") or ""

    _w(
        "PRODUCT_CATALOG_AUDIT_REPORT.md",
        f"# IA-1 — Product Catalog Audit\n\n"
        f"- Produtos no cadastro: **{cat.get('produtosNoCadastro')}**\n"
        f"- Produtos em VENDA_ITEM: **{cat.get('produtosEmVendaItem')}**\n"
        f"- Nunca vendidos: **{cat.get('produtosNuncaVendidos')}**\n"
        f"- Vendidos sem cadastro: **{cat.get('produtosVendidosSemCadastro')}**\n"
        f"- Cobertura cadastro: **{cat.get('coberturaCadastroPct')}%**\n",
    )
    cats = disc.get("categoriasVendidas") or {}
    cat_rows = "\n".join(f"- **{k}**: {v} itens" for k, v in cats.items())
    _w(
        "PRODUCT_CATEGORY_DISCOVERY_REPORT.md",
        f"# IA-2 — Category Discovery\n\n"
        f"Classificação baseada em evidência (sem presunção).\n\n"
        f"## Categorias vendidas\n\n{cat_rows or '—'}\n\n"
        f"## Receita por categoria\n\n"
        + "\n".join(f"- **{k}**: R$ {v}" for k, v in (disc.get('receitaPorCategoria') or {}).items())
        + "\n",
    )
    _w(
        "PRODUCT_COVERAGE_AUDIT_REPORT.md",
        f"# IA-3 — Product Coverage Audit\n\n"
        f"| Domínio | Registros |\n|---|---|\n"
        f"| PRODUTO | {cov.get('registrosProduto')} |\n"
        f"| VENDA_ITEM | {cov.get('registrosVendaItem')} |\n"
        f"| NFCE | {cov.get('registrosNfce')} |\n"
        f"| Produtos distintos VENDA_ITEM | {cov.get('produtosDistintosVendaItem')} |\n"
        f"| NFCE coverage | {cov.get('nfceCoveragePct')}% |\n",
    )
    _w(
        "MISSING_PRODUCT_DETECTION_REPORT.md",
        f"# IA-4 — Missing Product Detection\n\n"
        f"- Itens sem classificação: **{miss.get('itensSemClassificacao')}**\n"
        f"- Produtos distintos sem classificação: **{miss.get('produtosDistintosSemClassificacao')}**\n"
        f"- Itens baixa confiança: **{miss.get('itensBaixaConfianca')}**\n",
    )
    _w(
        "REVENUE_COVERAGE_AUDIT_REPORT.md",
        f"# IA-5 — Revenue Coverage Audit\n\n"
        f"- Receita não combustível (live): **R$ {rev.get('receitaNaoCombustivelLive')}**\n"
        f"- Receita não combustível (F07.0): **R$ {rev.get('receitaNaoCombustivelF070')}**\n"
        f"- Gap: **R$ {rev.get('gapReceita')}** ({rev.get('gapPct')}%)\n"
        f"- Veredito: **{rev.get('veredito')}**\n\n"
        f"> {rev.get('nota')}\n",
    )
    _w(
        "STORE_SALES_DISCOVERY_REPORT.md",
        f"# IA-6 — Store Sales Discovery\n\n"
        f"| Tipo | Existe | Itens |\n|---|---|---|\n"
        f"| Loja | {store.get('existeLoja')} | {store.get('itensLoja')} |\n"
        f"| Conveniência | {store.get('existeConveniencia')} | {store.get('itensConveniencia')} |\n"
        f"| Lubrificantes | {store.get('existeLubrificante')} | {store.get('itensLubrificantes')} |\n"
        f"| Serviços | {store.get('existeServico')} | {store.get('itensServicos')} |\n"
        f"| Acessórios | {store.get('existeAcessorio')} | — |\n",
    )
    _w(
        "PRODUCT_COVERAGE_EXECUTIVE_CHALLENGE_REPORT.md",
        f"# IA-7 — Executive Challenge\n\n"
        f"**Pergunta:** {ch.get('pergunta')}\n\n"
        f"**Resposta:** {ch.get('respostaExecutiva')}\n\n"
        f"- Veredito: **{ch.get('veredito')}**\n"
        f"- F07.0 produtos NF: **{ch.get('produtosNaoCombustivelF070')}**\n"
        f"- Live produtos NF distintos: **{ch.get('produtosDistintosNaoCombustivelLive')}**\n"
        f"- Catálogo total: **{ch.get('produtosNoCadastro')}**\n",
    )
    _w(
        "DW_PRODUCT_COVERAGE_REPORT.md",
        f"# IA-8 — DW Coverage\n\n"
        f"- Cobertura cadastro: **{dw.get('coberturaCadastroPct')}%**\n"
        f"- Produtos nunca vendidos: **{dw.get('produtosNuncaVendidos')}**\n"
        f"- Lacuna: {dw.get('lacunaDw')}\n",
    )
    _w(
        "PRODUCT_COVERAGE_QA_REPORT.md",
        f"# IA-9 — QA\n\n"
        f"| Critério | OK |\n|---|---|\n"
        f"| Sem classificação inventada | {qa.get('semClassificacaoInventada')} |\n"
        f"| Sem categorias presumidas | {qa.get('semCategoriasPresumidas')} |\n"
        f"| Tudo baseado em evidência | {qa.get('tudoBaseadoEvidencia')} |\n"
        f"| Motor auditável | {qa.get('motorAuditavel')} |\n\n"
        f"{parecer}\n",
    )
    _w(
        "F07_0A_PRODUCT_COVERAGE_TRUTH_REPORT.md",
        f"# F07.0A — Product Coverage Truth Audit\n\n"
        f"Fonte: **{w.get('fonteDados')}**\n\n"
        f"## Respostas executivas\n\n"
        + "\n".join(f"{k}: {v}" for k, v in sorted(ex.items()))
        + f"\n\n{parecer}\n",
    )


if __name__ == "__main__":
    main()
