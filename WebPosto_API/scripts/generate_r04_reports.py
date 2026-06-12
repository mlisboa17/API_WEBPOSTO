#!/usr/bin/env python3
"""Gera relatórios R04 Product Commercial Readiness."""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
AUDIT = ROOT / "scripts" / "r04_product_commercial_readiness_audit.json"


def _load() -> dict:
    return json.loads(AUDIT.read_text(encoding="utf-8"))


def _w(name: str, body: str) -> None:
    p = ROOT / name
    p.write_text(body, encoding="utf-8")
    print(f"Wrote {p}")


def main() -> None:
    data = _load()
    margin = data.get("marginReliabilityAudit") or {}
    baseline = data.get("baselineCrosscheck") or {}
    rec = data.get("executiveRecommendation") or {}
    qa = data.get("qa") or {}
    ex = data.get("executiveAnswers") or {}
    parecer = data.get("parecerFinal") or ""

    _w(
        "COST_FIELD_COVERAGE_REPORT.md",
        f"# IA-1 — Cost Field Coverage\n\n"
        f"- Cobertura `precoCusto`/`totalCusto` (VENDA_ITEM): **{margin.get('coberturaCampoCustoPct')}%**\n"
        f"- Itens PV analisados: **{margin.get('itensProdutosVendidos')}**\n"
        f"- Itens sem custo: **{margin.get('itensSemCustoVendaItem')}**\n",
    )
    _w(
        "MARGIN_RELIABILITY_REPORT.md",
        f"# IA-2 — Margin Reliability\n\n"
        f"- Confiabilidade custo/margem: **{margin.get('confiabilidadeMargemPct')}%**\n"
        f"- Receita com margem confiável: **{margin.get('receitaComMargemConfiavelPct')}%**\n"
        f"- Threshold gate R04: **{ex.get('10_thresholdGatePct')}%**\n",
    )
    _w(
        "PRODUCT_COST_COMPLETENESS_REPORT.md",
        f"# IA-3 — Product Cost Completeness\n\n"
        f"- Margem coerente: **{margin.get('margemCoerentePct')}%**\n"
        f"- Lineage margem: **{margin.get('coberturaLineageMargemPct')}%**\n"
        f"- Receita PV: **R$ {margin.get('receitaProdutosVendidos')}**\n",
    )
    _w(
        "BRANCH_MARGIN_RELIABILITY_REPORT.md",
        f"# IA-4 — Branch Margin Reliability\n\n"
        f"- Baseline F07.5 foco comercial: **{baseline.get('f075ProdutosFocoComercial')}** produtos\n"
        f"- Alertas baixa margem F07.5: **{baseline.get('f075AlertasBaixaMargem')}**\n"
        f"- Margem com evidência F07.4: **{baseline.get('f074MargemComEvidencia')}**\n",
    )
    _w(
        "COMMERCIAL_DECISION_RISK_REPORT.md",
        f"# IA-5 — Commercial Decision Risk\n\n"
        f"- Bloquear ação F07.5: **{rec.get('bloquearAcaoComercialF075')}**\n"
        f"- Track F07.6: **{rec.get('f076Track')}**\n"
        f"- Decisão: **{rec.get('decisao')}**\n"
        f"- Motivo: {rec.get('motivo')}\n",
    )
    _w(
        "HIDDEN_COST_COVERAGE_REPORT.md",
        f"# IA-6 — Hidden Cost Coverage\n\n"
        f"- Itens sem custo oculto: **{margin.get('itensSemCustoVendaItem')}**\n"
        f"- Amostra sem custo: **{len(margin.get('amostraSemCusto') or [])}** registros\n",
    )
    _w(
        "MARGIN_CHALLENGE_REPORT.md",
        f"# IA-7 — Margin Challenge\n\n"
        f"- Itens margem suspeita (≥95% sem custo): **{margin.get('itensMargemSuspeita')}**\n"
        f"- Amostra: **{len(margin.get('amostraMargemSuspeita') or [])}** registros\n",
    )
    _w(
        "COMMERCIAL_GOVERNANCE_REPORT.md",
        f"# IA-8 — Commercial Governance\n\n"
        f"- Termo conveniência: **{ex.get('17_termoConveniencia')}**\n"
        f"- empresaCodigo obrigatório: **{ex.get('18_empresaCodigoObrigatorio')}**\n"
        f"- Gate aprovado: **{ex.get('11_gateAprovado')}**\n",
    )
    _w(
        "PRODUCT_COMMERCIAL_QA_REPORT.md",
        f"# IA-9 — Product Commercial QA\n\n"
        f"- READ ONLY: **{qa.get('readOnly')}**\n"
        f"- Sem F07.6 runtime pré-gate: **{qa.get('semImplementacaoF076')}**\n"
        f"- QA aprovado: **{qa.get('aprovado')}**\n\n{parecer}\n",
    )
    ex_lines = "\n".join(f"{k}: {v}" for k, v in sorted(ex.items()))
    _w(
        "R04_PRODUCT_COMMERCIAL_READINESS_AUDIT_REPORT.md",
        f"# R04 — Product Commercial Readiness Audit\n\n"
        f"Fonte: **{data.get('fonte', {}).get('modo')}**\n\n"
        f"## Decisão gate F07.6\n\n**{rec.get('decisao')}**\n\n"
        f"## Respostas executivas 1–20\n\n{ex_lines}\n\n{parecer}\n",
    )


if __name__ == "__main__":
    main()
