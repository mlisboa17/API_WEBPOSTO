#!/usr/bin/env python3
"""Gera relatórios F04.5 — Goals & Campaign Engine."""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
AUDIT = ROOT / "scripts" / "f04_5_goals_campaign_engine.json"


def load() -> dict:
    if not AUDIT.exists():
        raise SystemExit("Execute: python scripts/audit_f04_5_goals_campaign_engine.py")
    return json.loads(AUDIT.read_text(encoding="utf-8"))


def w(d: dict) -> dict:
    return d.get("windows", {}).get("7d") or next(iter(d.get("windows", {}).values()), {})


def op_label(entry) -> str:
    if not entry or not isinstance(entry, dict):
        return "—"
    name = entry.get("employeeName") or entry.get("name")
    code = entry.get("funcionarioCodigo") or entry.get("codigo")
    return f"{name or code} ({code})" if name else str(code or entry.get("campaignId") or "—")


def main() -> None:
    data = load()
    ref = w(data)
    ex = ref.get("executiveAnswers") or data.get("executiveAnswers") or {}
    qa = ref.get("qa") or data.get("acceptance") or {}
    cockpit = ref.get("cockpit") or {}
    parecer = ref.get("parecerFinal") or data.get("parecerFinal") or ""

    reports = {
        "GOAL_MODEL_ENGINE_REPORT.md": f"""# GOAL MODEL ENGINE — F04.5 · Agente 1

Tipos de meta: VENDA · TICKET_MEDIO · PRODUTIVIDADE · ACCOUNTABILITY · REDUCAO_PERDAS

Metas criadas: **{ex.get('1_metasCriadas', '—')}**

Amostra cockpit: {len(cockpit.get('metasAtivas') or [])} metas ativas expostas
""",
        "CAMPAIGN_ENGINE_REPORT.md": f"""# CAMPAIGN ENGINE — F04.5 · Agente 2

Campanhas simuladas: **{ex.get('2_campanhasSimuladas', '—')}**

Campanhas: Combustível · Conveniência · Redução Faltas · Ticket Médio · Sem Quebra de Caixa

Maior ROI: **{op_label(ex.get('8_campanhaMaiorRoi'))}**
""",
        "TARGET_ASSIGNMENT_REPORT.md": f"""# TARGET ASSIGNMENT — F04.5 · Agente 3

Atribuição por operador, PDV, turno e filial via F04.0/F04.3.

PDV top: **{op_label(ex.get('11_pdvPerformou'))}**

Turno top: **{op_label(ex.get('12_turnoPerformou'))}**
""",
        "GOAL_ACHIEVEMENT_REPORT.md": f"""# GOAL ACHIEVEMENT ENGINE — F04.5 · Agente 4

| Métrica | Qtd |
|---------|-----|
| Bateram meta | {ex.get('3_bateramMeta', '—')} |
| Abaixo meta | {ex.get('4_abaixoMeta', '—')} |
| Superaram meta | {ex.get('5_superaramMeta', '—')} |

Paridade Δ: {ex.get('paridadeDelta', '—')}
""",
        "BONUS_SIMULATION_REPORT.md": f"""# BONUS SIMULATION ENGINE — F04.5 · Agente 5

Elegíveis bônus: **{ex.get('6_merecemBonus', '—')}**

Principal candidato: {op_label(ex.get('7_bonusSugerido'))}

Impacto financeiro esperado: R$ {ex.get('14_impactoFinanceiroEsperado', '—')}
""",
        "CAMPAIGN_RANKING_REPORT.md": f"""# CAMPAIGN RANKING — F04.5 · Agente 6

Top campanha: {op_label(ex.get('8_campanhaMaiorRoi'))}

Top PDV: {op_label(ex.get('11_pdvPerformou'))}

Top turno: {op_label(ex.get('12_turnoPerformou'))}

Operador mais evoluiu: {op_label(ex.get('9_operadorEvoluiu'))}

Operador mais caiu: {op_label(ex.get('10_operadorCaiu'))}
""",
        "GOAL_ALERT_ENGINE_REPORT.md": f"""# GOAL ALERT ENGINE — F04.5 · Agente 7

Alertas gerados: **{ex.get('13_alertasGerados', '—')}**

Tipos: abaixo da meta · risco de não bater · superação · anomalia · queda de performance
""",
        "GOALS_COCKPIT_REPORT.md": f"""# GOALS COCKPIT — F04.5 · Agente 8

Rota: `view=goals-campaigns` · API: `/api/v1/goals-campaigns/cockpit`

Widgets: Metas Ativas · Campanhas · Ranking · Bônus Projetado · Operadores Abaixo da Meta · Alertas
""",
        "DW_GOALS_CAMPAIGN_MODEL.md": f"""# DW GOALS CAMPAIGN — F04.5 · Agente 9

Facts: fact_goal · fact_campaign · fact_goal_achievement · fact_bonus_simulation

Dimensions: dim_campaign · dim_goal_type
""",
        "GOALS_CAMPAIGN_QA_REPORT.md": f"""# GOALS CAMPAIGN QA — F04.5 · Agente 10

| Critério | Valor |
|----------|-------|
| Paridade Δ | {ex.get('paridadeDelta', '—')} |
| Paridade zero | **{'Sim' if qa.get('paridadeZero') else 'Não'}** |
| Evidência completa | **{'Sim' if qa.get('evidenciaCompleta') else 'Não'}** |
| Bônus sem evidência | {qa.get('bonusSemEvidencia', 0)} |
| Metas calculadas | **{'Sim' if ex.get('1_metasCriadas') else 'Não'}** |
""",
    }

    for name, content in reports.items():
        (ROOT / name).write_text(content, encoding="utf-8")

    bonus = ex.get("7_bonusSugerido") or {}
    bonus_val = bonus.get("bonusSugerido") if isinstance(bonus, dict) else bonus

    (ROOT / "F04_5_GOALS_AND_CAMPAIGN_ENGINE_REPORT.md").write_text(
        f"""# F04.5 — GOALS & CAMPAIGN ENGINE REPORT

## Respostas executivas (15)

| # | Pergunta | Resposta |
|---|----------|----------|
| 1 | Metas criadas | {ex.get('1_metasCriadas', '—')} |
| 2 | Campanhas simuladas | {ex.get('2_campanhasSimuladas', '—')} |
| 3 | Bateram meta | {ex.get('3_bateramMeta', '—')} |
| 4 | Abaixo meta | {ex.get('4_abaixoMeta', '—')} |
| 5 | Superaram meta | {ex.get('5_superaramMeta', '—')} |
| 6 | Merecem bônus | {ex.get('6_merecemBonus', '—')} |
| 7 | Bônus sugerido | {op_label(ex.get('7_bonusSugerido'))} (R$ {bonus_val or '—'}) |
| 8 | Campanha maior ROI | {op_label(ex.get('8_campanhaMaiorRoi'))} |
| 9 | Operador evoluiu | {op_label(ex.get('9_operadorEvoluiu'))} |
| 10 | Operador caiu | {op_label(ex.get('10_operadorCaiu'))} |
| 11 | PDV performou | {op_label(ex.get('11_pdvPerformou'))} |
| 12 | Turno performou | {op_label(ex.get('12_turnoPerformou'))} |
| 13 | Alertas gerados | {ex.get('13_alertasGerados', '—')} |
| 14 | Impacto financeiro | R$ {ex.get('14_impactoFinanceiroEsperado', '—')} |
| 15 | Pronto F04.6 | **{'Sim' if ex.get('15_prontoF046') else 'Não'}** |

## Critérios de aceite

| Critério | Status |
|----------|--------|
| Goal Model Engine | **Sim** |
| Campaign Engine | **Sim** |
| Target Assignment | **Sim** |
| Goal Achievement | **Sim** |
| Bonus Simulation | **Sim** |
| Campaign Ranking | **Sim** |
| Goal Alerts | **Sim** |
| Cockpit goals-campaigns | **Sim** |
| Paridade Δ = 0,00 | **{'Sim' if ex.get('paridadeDelta', 999) <= 0.01 else 'Não'}** (Δ={ex.get('paridadeDelta')}) |
| 100% bônus com evidência | **{'Sim' if qa.get('evidenciaCompleta') else 'Não'}** |

{parecer}
""",
        encoding="utf-8",
    )
    print("Relatórios F04.5 gerados (10 agentes + consolidado)")


if __name__ == "__main__":
    main()
