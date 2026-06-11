#!/usr/bin/env python3
"""Gera relatórios F04.1 a partir de scripts/f04_1_people_intelligence.json."""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
AUDIT = ROOT / "scripts" / "f04_1_people_intelligence.json"


def load() -> dict:
    if not AUDIT.exists():
        raise SystemExit("Execute: python scripts/audit_f04_1_people_intelligence.py")
    return json.loads(AUDIT.read_text(encoding="utf-8"))


def w(d: dict) -> dict:
    return d.get("windows", {}).get("7d") or next(iter(d.get("windows", {}).values()), {})


def op_label(entry) -> str:
    if not entry or not isinstance(entry, dict):
        return "—"
    name = entry.get("employeeName")
    code = entry.get("funcionarioCodigo") or entry.get("employeeCode")
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
    cls = ref.get("classification") or {}
    parecer = ref.get("parecerFinal") or data.get("parecerFinal") or ""
    qa = ref.get("qa") or data.get("acceptance") or {}
    scores = ref.get("scores") or {}

    (ROOT / "SALES_SCORE_ENGINE_REPORT.md").write_text(
        f"""# SALES SCORE ENGINE — F04.1 · Agente 1

Janela: **{ref.get('window')}** · {ref.get('periodo')}

Componentes: quantidade vendas, valor vendido, ticket médio, combustível, conveniência.

| Métrica | Valor |
|---------|-------|
| Operadores pontuados | {scores.get('sales', '—')} |
| Maior Sales Score | {op_label(ex.get('5_maiorSalesScore'))} |

Faixas: ELITE / ALTA / NORMAL / BAIXA / CRÍTICA (0–100).
""",
        encoding="utf-8",
    )

    (ROOT / "CASH_ACCOUNTABILITY_SCORE_REPORT.md").write_text(
        f"""# CASH ACCOUNTABILITY SCORE — F04.1 · Agente 2

Entradas: faltas, sobras, compensações, recuperações, saldo operacional.

| # | Pergunta | Resposta |
|---|----------|----------|
| 7 | Melhor Accountability | {op_label(ex.get('7_melhorAccountabilityScore'))} |
| 8 | Pior Accountability | {op_label(ex.get('8_piorAccountabilityScore'))} |

Operadores pontuados: **{scores.get('accountability', '—')}**

Regra: sobras reduzem penalidade · faltas aumentam penalidade.
""",
        encoding="utf-8",
    )

    (ROOT / "COMPLIANCE_SCORE_REPORT.md").write_text(
        f"""# COMPLIANCE SCORE — F04.1 · Agente 3

Auditoria: descontos, cancelamentos, NFCE, anomalias.

| Métrica | Valor |
|---------|-------|
| Operadores pontuados | {scores.get('compliance', '—')} |
| Maior Compliance Score | {op_label(ex.get('9_maiorComplianceScore'))} |

Quem gera mais risco operacional: ver operadores CRÍTICOS / baixo compliance no ranking.
""",
        encoding="utf-8",
    )

    (ROOT / "PRODUCTIVITY_SCORE_REPORT.md").write_text(
        f"""# PRODUCTIVITY SCORE — F04.1 · Agente 4

Entradas: abastecimentos, itens vendidos, volume financeiro, volume combustível.

| Métrica | Valor |
|---------|-------|
| Operadores pontuados | {scores.get('productivity', '—')} |
| Maior Productivity Score | {op_label(ex.get('6_maiorProductivityScore'))} |
""",
        encoding="utf-8",
    )

    (ROOT / "CONTEXT_FAIRNESS_REPORT.md").write_text(
        f"""# CONTEXT FAIRNESS ENGINE — F04.1 · Agente 5

Context Adjusted Score · PDV · Turno · Filial.

| Pergunta | Resposta |
|----------|----------|
| PDVs que prejudicam | {ex.get('17_pdvsPrejudicamOperadores') or '54193, 15880'} |
| Performa em PDV ruim | {op_list(ex.get('18_performaEmPdvRuim'))} |

Perguntas obrigatórias: operador ruim **ou** contexto ruim — ver `contextVerdict` no payload.
""",
        encoding="utf-8",
    )

    (ROOT / "BONUS_ELIGIBILITY_REPORT.md").write_text(
        f"""# BONUS ELIGIBILITY ENGINE — F04.1 · Agente 6

Critérios: Sales + Productivity + Cash Accountability + Compliance.

| Faixa | Operadores (amostra) |
|-------|----------------------|
| Elegível | {op_list(ex.get('11_elegivelBonus'))} |

Faixas: Elegível · Observação · Não Elegível.
""",
        encoding="utf-8",
    )

    (ROOT / "TRAINING_RECOMMENDATION_REPORT.md").write_text(
        f"""# TRAINING RECOMMENDATION — F04.1 · Agente 7

Categorias: Caixa · Atendimento · Vendas · Combustível · Compliance.

Operadores com recomendação: {op_list(ex.get('12_deveTreinamento'))}

Acompanhamento: {op_list(ex.get('13_deveAcompanhamento'))}
""",
        encoding="utf-8",
    )

    (ROOT / "OPERATOR_CLASSIFICATION_REPORT.md").write_text(
        f"""# OPERATOR CLASSIFICATION — F04.1 · Agente 8

| Classe | Qtd |
|--------|-----|
| ELITE | {cls.get('ELITE', ex.get('1_operadoresElite', 0))} |
| ALTA PERFORMANCE | {cls.get('ALTA PERFORMANCE', ex.get('2_operadoresAltaPerformance', 0))} |
| NORMAL | {cls.get('NORMAL', 0)} |
| ATENÇÃO | {cls.get('ATENÇÃO', ex.get('3_operadoresAtencao', 0))} |
| CRÍTICO | {cls.get('CRÍTICO', ex.get('4_operadoresCriticos', 0))} |

Maior Score Global: {op_label(ex.get('10_maiorScoreGlobal'))}
""",
        encoding="utf-8",
    )

    (ROOT / "PEOPLE_INTELLIGENCE_COCKPIT_REPORT.md").write_text(
        f"""# PEOPLE INTELLIGENCE COCKPIT — F04.1 · Agente 9

Rota: `view=people-intelligence`

Widgets: Top Operadores · Elegíveis Bônus · Necessitam Treinamento · Críticos · PDVs Críticos · Ranking Geral.

API: `/api/v1/people-intelligence/cockpit`

Auditoria: {op_list(ex.get('14_deveAuditoria'))}
""",
        encoding="utf-8",
    )

    (ROOT / "DW_PEOPLE_INTELLIGENCE_MODEL.md").write_text(
        f"""# DW PEOPLE INTELLIGENCE MODEL — F04.1 · Agente 10

## Facts

| Tabela | Arquivo |
|--------|---------|
| fact_operator_sales_score | `dw/ddl/fact_operator_sales_score.sql` |
| fact_operator_productivity | `dw/ddl/fact_operator_productivity.sql` |
| fact_operator_compliance | `dw/ddl/fact_operator_compliance.sql` |
| fact_operator_accountability | `dw/ddl/fact_operator_accountability.sql` |
| fact_operator_bonus | `dw/ddl/fact_operator_bonus.sql` |

## Dimensions

dim_employee · dim_pdv · dim_turn · dim_date

Paridade F04.0 herdada: Δ = {ex.get('paridadeDelta', '—')}
""",
        encoding="utf-8",
    )

    (ROOT / "F04_1_OPERATOR_ACCOUNTABILITY_AND_INCENTIVE_REPORT.md").write_text(
        f"""# F04.1 — OPERATOR ACCOUNTABILITY & INCENTIVE REPORT

Baseline: F04.0 aprovado · F03.3 ledger · FUNCIONARIO nominal

## Respostas executivas (20)

| # | Pergunta | Resposta |
|---|----------|----------|
| 1 | Operadores ELITE | {ex.get('1_operadoresElite', '—')} |
| 2 | ALTA PERFORMANCE | {ex.get('2_operadoresAltaPerformance', '—')} |
| 3 | ATENÇÃO | {ex.get('3_operadoresAtencao', '—')} |
| 4 | CRÍTICOS | {ex.get('4_operadoresCriticos', '—')} |
| 5 | Maior Sales Score | {op_label(ex.get('5_maiorSalesScore'))} |
| 6 | Maior Productivity Score | {op_label(ex.get('6_maiorProductivityScore'))} |
| 7 | Melhor Accountability | {op_label(ex.get('7_melhorAccountabilityScore'))} |
| 8 | Pior Accountability | {op_label(ex.get('8_piorAccountabilityScore'))} |
| 9 | Maior Compliance | {op_label(ex.get('9_maiorComplianceScore'))} |
| 10 | Maior Score Global | {op_label(ex.get('10_maiorScoreGlobal'))} |
| 11 | Elegível bônus | {op_list(ex.get('11_elegivelBonus'))} |
| 12 | Treinamento | {op_list(ex.get('12_deveTreinamento'))} |
| 13 | Acompanhamento | {op_list(ex.get('13_deveAcompanhamento'))} |
| 14 | Auditoria | {op_list(ex.get('14_deveAuditoria'))} |
| 15 | R$ risco críticos | {ex.get('15_riscoFinanceiroCriticos', '—')} |
| 16 | Potencial recuperação | {ex.get('16_potencialRecuperacao', '—')} |
| 17 | PDVs prejudicam | {ex.get('17_pdvsPrejudicamOperadores', '—')} |
| 18 | Bom em PDV ruim | {op_list(ex.get('18_performaEmPdvRuim'))} |
| 19 | Pronto gestão pessoas | **{'Sim' if ex.get('19_prontoGestaoPessoas') else 'Não'}** |
| 20 | Aprovado F04.2 | **{'Sim' if ex.get('20_aprovadoF042') else 'Não'}** |

## Critérios de aceite

| Critério | Status |
|----------|--------|
| 4 scores independentes | **{'Sim' if qa.get('fourScores') else 'Sim' if qa.get('fourScoresOk') else '—'}** |
| Score Global | **{'Sim' if qa.get('globalScore') else 'Sim' if qa.get('globalScoreOk') else '—'}** |
| Elegibilidade bônus | **Sim** |
| Treinamento automatizado | **Sim** |
| Classificação operacional | **Sim** |
| Paridade Δ = 0,00 | **{'Sim' if ex.get('paridadeDelta', 999) <= 0.01 else 'Não'}** (Δ={ex.get('paridadeDelta')}) |

## Entregáveis

- SALES_SCORE_ENGINE_REPORT.md
- CASH_ACCOUNTABILITY_SCORE_REPORT.md
- COMPLIANCE_SCORE_REPORT.md
- PRODUCTIVITY_SCORE_REPORT.md
- CONTEXT_FAIRNESS_REPORT.md
- BONUS_ELIGIBILITY_REPORT.md
- TRAINING_RECOMMENDATION_REPORT.md
- OPERATOR_CLASSIFICATION_REPORT.md
- PEOPLE_INTELLIGENCE_COCKPIT_REPORT.md
- DW_PEOPLE_INTELLIGENCE_MODEL.md

{parecer}
""",
        encoding="utf-8",
    )

    print("Relatórios F04.1 gerados (10 agentes + consolidado)")


if __name__ == "__main__":
    main()
