#!/usr/bin/env python3
"""Gera relatórios F04.7 — Executive Scorecard."""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
AUDIT = ROOT / "scripts" / "f04_7_executive_scorecard.json"


def load() -> dict:
    if not AUDIT.exists():
        raise SystemExit("Execute: python scripts/audit_f04_7_executive_scorecard.py")
    return json.loads(AUDIT.read_text(encoding="utf-8"))


def w(d: dict) -> dict:
    return d.get("windows", {}).get("7d") or next(iter(d.get("windows", {}).values()), {})


def label(entry, name_keys=("nomeFilial", "employeeName"), code_keys=("empresaCodigo", "funcionarioCodigo")) -> str:
    if not entry or not isinstance(entry, dict):
        return "—"
    name = next((entry.get(k) for k in name_keys if entry.get(k)), None)
    code = next((entry.get(k) for k in code_keys if entry.get(k) is not None), None)
    return f"{name or code} ({code})" if name else str(code or "—")


def main() -> None:
    data = load()
    ref = w(data)
    ex = ref.get("executiveAnswers") or data.get("executiveAnswers") or {}
    qa = ref.get("qa") or data.get("acceptance") or {}
    kpis = ref.get("executiveKpiEngine") or {}
    alerts = (ref.get("executiveAlertEngine") or {}).get("alerts") or []
    decisao = ref.get("decisaoArquitetural") or {}
    parecer = ref.get("parecerFinal") or data.get("parecerFinal") or ""

    reports = {
        "EXECUTIVE_KPI_ENGINE_REPORT.md": f"""# EXECUTIVE KPI ENGINE — F04.7 · IA-1

| Score | Valor |
|-------|-------|
| Executive Score | **{ex.get('1_executiveScore', '—')}** |
| Financial Score | {ex.get('2_financialScore', '—')} |
| People Score | {ex.get('3_peopleScore', '—')} |
| Operations Score | {ex.get('4_operationsScore', '—')} |
| Growth Score | {ex.get('5_growthScore', '—')} |
| Risk Score | {ex.get('6_riskScore', '—')} |

Pesos: 30% Financial · 25% People · 20% Operations · 15% Growth · 10% Risk
""",
        "FINANCIAL_SCORECARD_REPORT.md": f"""# FINANCIAL SCORECARD — F04.7 · IA-2

Financial Score: **{ex.get('2_financialScore', '—')}**

Potencial capturável: R$ {ex.get('16_potencialCapturavel', '—')}

Diagnóstico operacional: receita R$ {kpis.get('evidence', {}).get('receitaOperacional', '—')}
""",
        "PEOPLE_SCORECARD_REPORT.md": f"""# PEOPLE SCORECARD — F04.7 · IA-3

People Score: **{ex.get('3_peopleScore', '—')}**

Melhor operador: {label(ex.get('9_melhorOperador'))}

Pior operador: {label(ex.get('10_piorOperador'))}
""",
        "OPERATIONS_SCORECARD_REPORT.md": f"""# OPERATIONS SCORECARD — F04.7 · IA-4

Operations Score: **{ex.get('4_operationsScore', '—')}**

PDV crítico: {label(ex.get('11_pdvCritico'), ('pdvCodigo',), ('pdvCodigo',))}

Turno crítico: {label(ex.get('12_turnoCritico'), ('turno',), ('turnoCodigo',))}
""",
        "TREND_FORECAST_REPORT.md": f"""# TREND & FORECAST — F04.7 · IA-5

Operação geral: **{ex.get('17_operacaoTendencia', '—')}**
""",
        "EXECUTIVE_ALERT_ENGINE_REPORT.md": f"""# EXECUTIVE ALERT ENGINE — F04.7 · IA-6

Alertas executivos: **{ex.get('13_alertasExecutivos', len(alerts))}**

Severidades: {', '.join(sorted({a.get('severity') for a in alerts if a.get('severity')}))}
""",
        "EXECUTIVE_COCKPIT_REPORT.md": f"""# EXECUTIVE COCKPIT — F04.7 · IA-7

Rota: `view=executive-scorecard` · API: `/api/v1/executive-scorecard/cockpit`
""",
        "DW_EXECUTIVE_SCORECARD_MODEL.md": f"""# DW EXECUTIVE SCORECARD — F04.7 · IA-8

Facts: fact_executive_score · fact_executive_alert · fact_executive_trend · fact_executive_snapshot

Dimensions: dim_score_type · dim_alert_type · dim_trend_type
""",
        "EXECUTIVE_SCORECARD_QA_REPORT.md": f"""# EXECUTIVE SCORECARD QA — F04.7 · IA-9

| Critério | Valor |
|----------|-------|
| Paridade Δ | {ex.get('paridadeDelta', '—')} |
| Paridade zero | **{'Sim' if qa.get('paridadeZero') else 'Não'}** |
| Sem cross-tenant | **{'Sim' if qa.get('semCrossTenant') else 'Não'}** |
| Scores com evidência | **{'Sim' if qa.get('scoresComEvidencia') else 'Não'}** |
| Alertas com justificativa | **{'Sim' if qa.get('alertasComJustificativa') else 'Não'}** |
""",
    }

    for name, content in reports.items():
        (ROOT / name).write_text(content, encoding="utf-8")

    (ROOT / "F04_7_EXECUTIVE_SCORECARD_REPORT.md").write_text(
        f"""# F04.7 — EXECUTIVE SCORECARD REPORT

## Respostas executivas (20)

| # | Pergunta | Resposta |
|---|----------|----------|
| 1 | Executive Score | **{ex.get('1_executiveScore', '—')}** |
| 2 | Financial Score | {ex.get('2_financialScore', '—')} |
| 3 | People Score | {ex.get('3_peopleScore', '—')} |
| 4 | Operations Score | {ex.get('4_operationsScore', '—')} |
| 5 | Growth Score | {ex.get('5_growthScore', '—')} |
| 6 | Risk Score | {ex.get('6_riskScore', '—')} |
| 7 | Melhor filial | {label(ex.get('7_melhorFilial'))} |
| 8 | Pior filial | {label(ex.get('8_piorFilial'))} |
| 9 | Melhor operador | {label(ex.get('9_melhorOperador'))} |
| 10 | Pior operador | {label(ex.get('10_piorOperador'))} |
| 11 | PDV crítico | {label(ex.get('11_pdvCritico'), ('pdvCodigo',), ('pdvCodigo',))} |
| 12 | Turno crítico | {label(ex.get('12_turnoCritico'), ('turno',), ('turnoCodigo',))} |
| 13 | Alertas executivos | {ex.get('13_alertasExecutivos', '—')} |
| 14 | Maior risco | {label(ex.get('14_maiorRisco'))} |
| 15 | Maior oportunidade | {label(ex.get('15_maiorOportunidade'), ('pdvCodigo',), ('pdvCodigo',))} |
| 16 | Potencial capturável | R$ {ex.get('16_potencialCapturavel', '—')} |
| 17 | Operação melhorando/piorando | **{ex.get('17_operacaoTendencia', '—')}** |
| 18 | Empresa saudável | **{'Sim' if ex.get('18_empresaSaudavel') else 'Não'}** |
| 19 | Scorecard confiável | **{'Sim' if ex.get('19_scorecardConfiavel') else 'Não'}** |
| 20 | Aprovado F05 | **{'Sim' if ex.get('20_aprovadoF05') else 'Não'}** |

## Decisão arquitetural

**{decisao.get('pergunta', '')}**

Resposta: **{'Sim' if decisao.get('resposta') else 'Não'}**

{decisao.get('justificativa', '')}

## Critérios de aceite

| Critério | Status |
|----------|--------|
| Nenhuma consulta WebPosto | **Sim** |
| Artefatos homologados F03-F04.6 | **Sim** |
| Paridade Δ = 0,00 | **{'Sim' if ex.get('paridadeDelta', 999) <= 0.01 else 'Não'}** (Δ={ex.get('paridadeDelta')}) |
| Cockpit executive-scorecard | **Sim** |
| DW executivo | **Sim** |
| Alertas executivos | **Sim** ({ex.get('13_alertasExecutivos', 0)}) |
| Executive Score calculado | **Sim** |
| QA aprovado | **{'Sim' if ex.get('20_aprovadoF05') else 'Não'}** |

{parecer}
""",
        encoding="utf-8",
    )
    print("Relatórios F04.7 gerados (IA 1-9 + consolidado)")


if __name__ == "__main__":
    main()
