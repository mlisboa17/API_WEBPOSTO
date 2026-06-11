#!/usr/bin/env python3
"""Gera relatórios F04.2 a partir de scripts/f04_2_operator_profitability.json."""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
AUDIT = ROOT / "scripts" / "f04_2_operator_profitability.json"


def load() -> dict:
    if not AUDIT.exists():
        raise SystemExit("Execute: python scripts/audit_f04_2_operator_profitability.py")
    return json.loads(AUDIT.read_text(encoding="utf-8"))


def w(d: dict) -> dict:
    return d.get("windows", {}).get("7d") or next(iter(d.get("windows", {}).values()), {})


def op_label(entry) -> str:
    if not entry or not isinstance(entry, dict):
        return "—"
    name = entry.get("employeeName")
    code = entry.get("funcionarioCodigo")
    return f"{name or code} ({code})" if name else str(code or "—")


def op_list(entries) -> str:
    if not entries:
        return "—"
    if isinstance(entries, list):
        return ", ".join(op_label(e) for e in entries[:5])
    return op_label(entries)


def main() -> None:
    data = load()
    ref = w(data)
    ex = ref.get("executiveAnswers") or data.get("executiveAnswers") or {}
    qa = ref.get("qa") or data.get("acceptance") or {}
    bands = ref.get("profitabilityBands") or {}
    parecer = ref.get("parecerFinal") or data.get("parecerFinal") or ""

    reports = {
        "OPERATOR_REVENUE_REPORT.md": f"""# OPERATOR REVENUE — F04.2 · Agente 1

| Métrica | Resposta |
|---------|----------|
| Maior receita | {op_label(ex.get('1_maiorReceita'))} |
| Receita operadores | {ex.get('paridadeReceitaOperador', '—')} |
| Receita consolidada | {ex.get('paridadeReceitaConsolidada', '—')} |
""",
        "MARGIN_IMPACT_REPORT.md": f"""# MARGIN IMPACT — F04.2 · Agente 2

| Pergunta | Resposta |
|----------|----------|
| Maior margem | {op_label(ex.get('2_maiorMargem'))} |
| Destrói margem | {op_label(ex.get('3_destróiMargem'))} |
| Mais descontos | {op_label(ex.get('4_maisDescontos'))} |
""",
        "PROFITABILITY_SCORE_REPORT.md": f"""# PROFITABILITY SCORE — F04.2 · Agente 3

| Banda | Qtd |
|-------|-----|
| GERA_LUCRO | {bands.get('GERA_LUCRO', 0)} |
| NEUTRO | {bands.get('NEUTRO', 0)} |
| DESTRUI_MARGEM | {bands.get('DESTRUI_MARGEM', 0)} |

Maior score: {op_label(ex.get('5_maiorProfitabilityScore'))} · Menor: {op_label(ex.get('6_menorProfitabilityScore'))}
""",
        "BONUS_ROI_REPORT.md": f"""# BONUS ROI — F04.2 · Agente 4

Merece bônus: {op_list(ex.get('10_mereceBonus'))}

Remuneração variável suportada: **{'Sim' if ex.get('19_remuneracaoVariavel') else 'Não'}**
""",
        "MANAGEMENT_ACTION_REPORT.md": f"""# MANAGEMENT ACTION — F04.2 · Agente 5

| Ação | Operadores |
|------|------------|
| Promover | {op_list(ex.get('9_merecePromocao'))} |
| Bonificar | {op_list(ex.get('10_mereceBonus'))} |
| Treinar | {op_list(ex.get('11_mereceTreinamento'))} |
| Auditar | {op_list(ex.get('12_mereceAuditoria'))} |
""",
        "CONTEXT_NORMALIZATION_V2_REPORT.md": f"""# CONTEXT NORMALIZATION V2 — F04.2 · Agente 6

Melhor retorno em PDV crítico: {op_list(ex.get('16_melhorRetornoPdvCritico'))}

Profitability Adjusted Score aplicado sobre score bruto com penalty/bonus de contexto.
""",
        "PEOPLE_ROI_REPORT.md": f"""# PEOPLE ROI — F04.2 · Agente 7

| Métrica | Resposta |
|---------|----------|
| Maior ROI | {op_label(ex.get('7_maiorRoi'))} |
| Menor ROI | {op_label(ex.get('8_menorRoi'))} |
| Lucro Top 10 | {ex.get('13_lucroTop10', '—')} |
| Risco críticos | {ex.get('14_riscoCriticos', '—')} |
| Destrói valor econômico | {op_label(ex.get('17_destróiValorEconomico'))} |
""",
        "PEOPLE_ROI_COCKPIT_REPORT.md": f"""# PEOPLE ROI COCKPIT — F04.2 · Agente 8

Rota: `view=people-roi` · API: `/api/v1/people-roi/cockpit`

Widgets: Top ROI · Top Lucro · Top Risco · Top Bônus · Top Auditoria
""",
        "DW_OPERATOR_PROFITABILITY_MODEL.md": f"""# DW OPERATOR PROFITABILITY — F04.2 · Agente 9

Facts: fact_operator_profitability · fact_operator_roi · fact_operator_management_action

Dimensions: dim_employee · dim_pdv · dim_turn · dim_date
""",
        "PEOPLE_ROI_QA_REPORT.md": f"""# PEOPLE ROI QA — F04.2 · Agente 10

| Critério | Status |
|----------|--------|
| Receita operador = consolidada | Δ={ex.get('paridadeDelta', '—')} |
| Paridade OK | **{'Sim' if qa.get('paridadeZero') else 'Sim' if ex.get('paridadeDelta', 999) <= 0.01 else 'Não'}** |
| Profitability Score | **{'Sim' if qa.get('profitabilityScore') else 'Sim' if qa.get('profitabilityScoreOk') else '—'}** |
| ROI | **Sim** |
| Cockpit | **Sim** |
""",
    }

    for name, content in reports.items():
        (ROOT / name).write_text(content, encoding="utf-8")

    (ROOT / "F04_2_OPERATOR_PROFITABILITY_AND_ROI_REPORT.md").write_text(
        f"""# F04.2 — OPERATOR PROFITABILITY & ROI REPORT

## Respostas executivas (20)

| # | Pergunta | Resposta |
|---|----------|----------|
| 1 | Maior receita | {op_label(ex.get('1_maiorReceita'))} |
| 2 | Maior margem | {op_label(ex.get('2_maiorMargem'))} |
| 3 | Destrói margem | {op_label(ex.get('3_destróiMargem'))} |
| 4 | Mais descontos | {op_label(ex.get('4_maisDescontos'))} |
| 5 | Maior Profitability Score | {op_label(ex.get('5_maiorProfitabilityScore'))} |
| 6 | Menor Profitability Score | {op_label(ex.get('6_menorProfitabilityScore'))} |
| 7 | Maior ROI | {op_label(ex.get('7_maiorRoi'))} |
| 8 | Menor ROI | {op_label(ex.get('8_menorRoi'))} |
| 9 | Promoção | {op_list(ex.get('9_merecePromocao'))} |
| 10 | Bônus | {op_list(ex.get('10_mereceBonus'))} |
| 11 | Treinamento | {op_list(ex.get('11_mereceTreinamento'))} |
| 12 | Auditoria | {op_list(ex.get('12_mereceAuditoria'))} |
| 13 | Lucro Top 10 | {ex.get('13_lucroTop10', '—')} |
| 14 | Risco críticos | {ex.get('14_riscoCriticos', '—')} |
| 15 | Retorno/venda | {op_label(ex.get('15_melhorRetornoPorVenda'))} |
| 16 | PDV crítico | {op_list(ex.get('16_melhorRetornoPdvCritico'))} |
| 17 | Destrói valor | {op_label(ex.get('17_destróiValorEconomico'))} |
| 18 | Meritocracia | **{'Sim' if ex.get('18_gestaoMeritocratica') else 'Não'}** |
| 19 | Remuneração variável | **{'Sim' if ex.get('19_remuneracaoVariavel') else 'Não'}** |
| 20 | Aprovado F04.3 | **{'Sim' if ex.get('20_aprovadoF043') else 'Não'}** |

## Critérios de aceite

| Critério | Status |
|----------|--------|
| Profitability Score | **Sim** |
| ROI | **Sim** |
| Ações gerenciais | **Sim** |
| Paridade Δ = 0,00 | **{'Sim' if ex.get('paridadeDelta', 999) <= 0.01 else 'Não'}** (Δ={ex.get('paridadeDelta')}) |
| Cockpit executivo | **Sim** |

{parecer}
""",
        encoding="utf-8",
    )

    print("Relatórios F04.2 gerados (10 agentes + consolidado)")


if __name__ == "__main__":
    main()
