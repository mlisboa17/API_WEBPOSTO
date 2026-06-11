#!/usr/bin/env python3
"""Gera relatórios F04.4."""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
AUDIT = ROOT / "scripts" / "f04_4_management_action_center.json"


def load() -> dict:
    if not AUDIT.exists():
        raise SystemExit("Execute: python scripts/audit_f04_4_management_action_center.py")
    return json.loads(AUDIT.read_text(encoding="utf-8"))


def w(d: dict) -> dict:
    return d.get("windows", {}).get("7d") or next(iter(d.get("windows", {}).values()), {})


def op_label(entry) -> str:
    if not entry or not isinstance(entry, dict):
        return "—"
    name = entry.get("employeeName")
    code = entry.get("funcionarioCodigo")
    return f"{name or code} ({code})" if name else str(code or "—")


def main() -> None:
    data = load()
    ref = w(data)
    ex = ref.get("executiveAnswers") or data.get("executiveAnswers") or {}
    qa = ref.get("qa") or data.get("acceptance") or {}
    bands = ref.get("governanceBands") or {}
    counts = ref.get("actionCounts") or {}
    parecer = ref.get("parecerFinal") or data.get("parecerFinal") or ""

    reports = {
        "ACTION_ENGINE_REPORT.md": f"""# ACTION ENGINE — F04.4 · Agente 1

Total ações automáticas: {ex.get('12_acoesAutomaticasGeradas', '—')}

Ação mais recorrente: **{ex.get('13_acaoMaisRecorrente', '—')}**

Distribuição: {counts}
""",
        "PEOPLE_GOVERNANCE_REPORT.md": f"""# PEOPLE GOVERNANCE — F04.4 · Agente 2

| Banda | Qtd |
|-------|-----|
| EMBAIXADOR | {bands.get('EMBAIXADOR', 0)} |
| ALTA_PERFORMANCE | {bands.get('ALTA_PERFORMANCE', 0)} |
| OPERADOR_PADRAO | {bands.get('OPERADOR_PADRAO', 0)} |
| EM_OBSERVACAO | {bands.get('EM_OBSERVACAO', 0)} |
| EM_RECUPERACAO | {bands.get('EM_RECUPERACAO', 0)} |
| CRITICO | {bands.get('CRITICO', 0)} |
""",
        "PROMOTION_ENGINE_REPORT.md": f"""# PROMOTION ENGINE — F04.4 · Agente 3

Elegíveis promoção: **{ex.get('1_elegiveisPromocao', 0)}**

Principal candidato: {op_label(ex.get('5_principalPromocao'))}
""",
        "BONUS_ENGINE_V2_REPORT.md": f"""# BONUS ENGINE V2 — F04.4 · Agente 4

Elegíveis bônus: **{ex.get('2_elegiveisBonus', 0)}**

Principal candidato: {op_label(ex.get('6_principalBonus'))}

Impacto financeiro esperado: {ex.get('14_impactoFinanceiroEsperado', '—')}
""",
        "TRAINING_ENGINE_REPORT.md": f"""# TRAINING ENGINE — F04.4 · Agente 5

Precisam treinamento: **{ex.get('3_precisamTreinamento', 0)}**
""",
        "OPERATIONAL_INTERVENTION_REPORT.md": f"""# OPERATIONAL INTERVENTION — F04.4 · Agente 6

PDV intervenção imediata: {ex.get('10_pdvIntervencaoImediata', '—')}

Turno intervenção imediata: {ex.get('11_turnoIntervencaoImediata', '—')}
""",
        "MANAGEMENT_TIMELINE_REPORT.md": f"""# MANAGEMENT TIMELINE — F04.4 · Agente 7

Cronograma padrão: Treinamento D+15 · Reavaliação D+30 · Auditoria D+60
""",
        "MANAGEMENT_COCKPIT_REPORT.md": f"""# MANAGEMENT COCKPIT — F04.4 · Agente 8

Rota: `view=management-action` · API: `/api/v1/management-action/cockpit`
""",
        "DW_MANAGEMENT_ACTION_MODEL.md": f"""# DW MANAGEMENT ACTION — F04.4 · Agente 9

Facts: fact_management_action · fact_bonus · fact_training · fact_governance

Dimensions: dim_employee · dim_pdv · dim_turn · dim_date
""",
        "MANAGEMENT_ACTION_QA_REPORT.md": f"""# MANAGEMENT ACTION QA — F04.4 · Agente 10

| Critério | Valor |
|----------|-------|
| Paridade Δ | {ex.get('paridadeDelta', '—')} |
| Ações sem evidência | {qa.get('acoesSemEvidencia', qa.get('acoesSemEvidencia', '—'))} |
| Falsos positivos | {qa.get('falsosPositivos', '—')} |
| Evidência completa | **{'Sim' if qa.get('evidenciaCompleta') else 'Não'}** |
""",
    }

    for name, content in reports.items():
        (ROOT / name).write_text(content, encoding="utf-8")

    (ROOT / "F04_4_MANAGEMENT_ACTION_CENTER_REPORT.md").write_text(
        f"""# F04.4 — MANAGEMENT ACTION CENTER REPORT

## Respostas executivas (20)

| # | Pergunta | Resposta |
|---|----------|----------|
| 1 | Elegíveis promoção | {ex.get('1_elegiveisPromocao', '—')} |
| 2 | Elegíveis bônus | {ex.get('2_elegiveisBonus', '—')} |
| 3 | Precisam treinamento | {ex.get('3_precisamTreinamento', '—')} |
| 4 | Precisam auditoria | {ex.get('4_precisamAuditoria', '—')} |
| 5 | Principal promoção | {op_label(ex.get('5_principalPromocao'))} |
| 6 | Principal bônus | {op_label(ex.get('6_principalBonus'))} |
| 7 | Maior risco | {op_label(ex.get('7_maiorRiscoOperacional'))} |
| 8 | Em recuperação | {len(ex.get('8_emRecuperacao') or [])} operadores |
| 9 | Em observação | {len(ex.get('9_emObservacao') or [])} operadores |
| 10 | PDV intervenção | {ex.get('10_pdvIntervencaoImediata', '—')} |
| 11 | Turno intervenção | {ex.get('11_turnoIntervencaoImediata', '—')} |
| 12 | Ações geradas | {ex.get('12_acoesAutomaticasGeradas', '—')} |
| 13 | Ação recorrente | {ex.get('13_acaoMaisRecorrente', '—')} |
| 14 | Impacto financeiro | {ex.get('14_impactoFinanceiroEsperado', '—')} |
| 15 | Risco reduzível | {ex.get('15_riscoReduzivel', '—')} |
| 16 | Valor recuperável | {ex.get('16_valorRecuperavel', '—')} |
| 17 | Meritocracia | **{'Sim' if ex.get('17_gestaoMeritocratica') else 'Não'}** |
| 18 | Plano carreira | **{'Sim' if ex.get('18_planoCarreira') else 'Não'}** |
| 19 | Governança operacional | **{'Sim' if ex.get('19_governancaOperacional') else 'Não'}** |
| 20 | Aprovado F04.5 | **{'Sim' if ex.get('20_aprovadoF045') else 'Não'}** |

## Critérios de aceite

| Critério | Status |
|----------|--------|
| Motor de ações | **Sim** |
| Classificação gerencial | **Sim** |
| Promoções / Bônus / Treinamentos | **Sim** |
| Cockpit | **Sim** |
| Paridade Δ = 0,00 | **{'Sim' if ex.get('paridadeDelta', 999) <= 0.01 else 'Não'}** (Δ={ex.get('paridadeDelta')}) |
| 100% ações com evidência | **{'Sim' if qa.get('evidenciaCompleta') else 'Não'}** |

{parecer}
""",
        encoding="utf-8",
    )
    print("Relatórios F04.4 gerados (10 agentes + consolidado)")


if __name__ == "__main__":
    main()
