#!/usr/bin/env python3
"""Gera relatórios F07.4 Produtos Vendidos Performance & Margin Intelligence."""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
AUDIT = ROOT / "scripts" / "f07_4_produtos_vendidos_performance.json"


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
    perf = w.get("productSalesPerformance") or {}
    margin = w.get("marginIntelligence") or {}
    mix = w.get("mixHealthCommercial") or {}
    opp = w.get("opportunityEngine") or {}
    cockpit = w.get("cockpit") or {}
    qa = w.get("qa") or {}
    parecer = w.get("parecerFinal") or ""

    _w(
        "PRODUCT_SALES_PERFORMANCE_REPORT.md",
        f"# IA-1 — Product Sales Performance\n\n"
        f"- Top volume: **{perf.get('topProdutoVolume', {}).get('produtoCodigo')}**\n"
        f"- Top receita: **{perf.get('topProdutoReceita', {}).get('produtoCodigo')}**\n"
        f"- Ranking volume: **{len(perf.get('rankingVolume') or [])}** produtos\n"
        f"- Ranking receita: **{len(perf.get('rankingReceita') or [])}** produtos\n",
    )
    _w(
        "MARGIN_INTELLIGENCE_REPORT.md",
        f"# IA-2 — Margin Intelligence\n\n"
        f"- Receita PV: **R$ {margin.get('receitaProdutosVendidos')}**\n"
        f"- Margem bruta: **R$ {margin.get('margemBrutaTotal')}** ({margin.get('margemBrutaPct')}%)\n"
        f"- Dept. líder: **{(margin.get('topDepartamentoMargem') or {}).get('departamento')}**\n"
        f"- Filiais analisadas: **{len(margin.get('porFilial') or [])}**\n",
    )
    _w(
        "MIX_HEALTH_COMMERCIAL_REPORT.md",
        f"# IA-3 — Mix Health Commercial\n\n"
        f"- Participação PV: **{mix.get('participacaoProdutosVendidosPct')}%**\n"
        f"- Margem média: **{mix.get('margemMediaPct')}%**\n"
        f"- Mix saudável: **{mix.get('mixSaudavel')}**\n"
        f"- Filial mix saudável: **{(mix.get('filialMixMaisSaudavel') or {}).get('empresaCodigo')}**\n",
    )
    _w(
        "COMMERCIAL_OPPORTUNITY_REPORT.md",
        f"# IA-4 — Commercial Opportunity Engine\n\n"
        f"- Oportunidades: **{opp.get('totalOportunidades')}**\n"
        f"- Crescimento possível: **{opp.get('existeOportunidadeCrescimento')}**\n\n"
        + "\n".join(f"- {o.get('tipo')}: {o.get('descricao')}" for o in opp.get("oportunidades") or []),
    )
    _w(
        "COMMERCIAL_COCKPIT_REPORT.md",
        f"# IA-5 — Commercial Cockpit\n\n"
        f"- Título: **{cockpit.get('tituloVisual')}**\n"
        f"- Margem bruta: **R$ {cockpit.get('margemBrutaTotal')}**\n"
        f"- Mix saudável: **{cockpit.get('mixSaudavel')}**\n"
        f"- Filial destaque: **{(cockpit.get('filialDestaque') or {}).get('empresaCodigo')}**\n",
    )
    _w(
        "DW_COMMERCIAL_INTELLIGENCE_REPORT.md",
        f"# IA-6 — DW Commercial Intelligence\n\nVer `dw/ddl/fact_product_margin_f074.sql`\n",
    )
    _w(
        "COMMERCIAL_QA_REPORT.md",
        f"# IA-7 — Commercial QA\n\n"
        f"- Margem com evidência: **{qa.get('margemComEvidenciaVendaItem')}**\n"
        f"- Sem conveniência: **{qa.get('semTermoConveniencia')}**\n"
        f"- Motor auditável: **{qa.get('motorAuditavel')}**\n",
    )
    ex_lines = "\n".join(f"{k}: {v}" for k, v in sorted(ex.items()))
    _w(
        "F07_4_PRODUTOS_VENDIDOS_PERFORMANCE_REPORT.md",
        f"# F07.4 — Produtos Vendidos Performance & Margin Intelligence\n\n"
        f"Fonte: **{w.get('fonte', {}).get('modo')}**\n\n"
        f"## Respostas executivas 1–20\n\n{ex_lines}\n\n{parecer}\n",
    )


if __name__ == "__main__":
    main()
