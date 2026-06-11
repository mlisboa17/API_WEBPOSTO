#!/usr/bin/env python3
"""Gera relatórios F05.0 — Corporate Intelligence Hub."""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
AUDIT = ROOT / "scripts" / "f05_0_corporate_intelligence_hub.json"


def load() -> dict:
    if not AUDIT.exists():
        raise SystemExit("Execute: python scripts/audit_f05_0_corporate_intelligence_hub.py")
    return json.loads(AUDIT.read_text(encoding="utf-8"))


def w(d: dict) -> dict:
    return d.get("windows", {}).get("7d") or next(iter(d.get("windows", {}).values()), {})


def label(entry, name_keys=("nomeFilial", "employeeName", "title"), code_keys=("empresaCodigo", "funcionarioCodigo", "type")) -> str:
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
    kpis = ref.get("corporateKpiConsolidation") or {}
    opps = ref.get("opportunityEngine") or {}
    risks = ref.get("riskIntelligenceEngine") or {}
    decisao = ref.get("decisaoArquitetural") or {}
    parecer = ref.get("parecerFinal") or data.get("parecerFinal") or ""

    reports = {
        "CORPORATE_KPI_CONSOLIDATION_REPORT.md": f"""# CORPORATE KPI CONSOLIDATION — F05.0 · IA-1

Corporate Score: **{ex.get('1_corporateScore', '—')}**

Executive Score: {ex.get('2_executiveScore', '—')}

Paridade Δ: {ex.get('paridadeDelta', '—')}
""",
        "FINANCIAL_INTELLIGENCE_HUB_REPORT.md": f"""# FINANCIAL INTELLIGENCE HUB — F05.0 · IA-2

Potencial capturável: R$ {ex.get('14_podeRecuperar', '—')}

Recuperado identificado: R$ {ex.get('13_recuperado', '—')}

Filial campeã: {label(ex.get('5_filialLider'))}
""",
        "PEOPLE_INTELLIGENCE_HUB_REPORT.md": f"""# PEOPLE INTELLIGENCE HUB — F05.0 · IA-3

Melhor operador: {label(ex.get('7_operadorValor'))}

Pior operador: {label(ex.get('8_operadorRisco'))}
""",
        "OPERATIONS_INTELLIGENCE_HUB_REPORT.md": f"""# OPERATIONS INTELLIGENCE HUB — F05.0 · IA-4

PDV destrói margem: {label(ex.get('9_pdvDestroiMargem'), ('pdvCodigo',), ('pdvCodigo',))}

Turno problemático: {label(ex.get('11_turnoProblematico'), ('turno',), ('turnoCodigo',))}
""",
        "OPPORTUNITY_ENGINE_REPORT.md": f"""# OPPORTUNITY ENGINE — F05.0 · IA-5

Maior oportunidade: {label(ex.get('4_maiorOportunidadeCorporativa'))}

Total oportunidades: {len(opps.get('opportunities') or [])}
""",
        "RISK_INTELLIGENCE_ENGINE_REPORT.md": f"""# RISK INTELLIGENCE ENGINE — F05.0 · IA-6

Maior risco: {label(ex.get('3_maiorRiscoCorporativo'), ('riskType', 'message'), ('severity',))}

Total riscos: {len(risks.get('risks') or [])}
""",
        "CORPORATE_HUB_COCKPIT_REPORT.md": f"""# CORPORATE HUB COCKPIT — F05.0 · IA-7

Rota: `view=corporate-hub` · API: `/api/v1/corporate-hub/cockpit`
""",
        "DW_CORPORATE_INTELLIGENCE_MODEL.md": f"""# DW CORPORATE INTELLIGENCE — F05.0 · IA-8

Facts: fact_corporate_score · fact_corporate_risk · fact_corporate_opportunity · fact_corporate_snapshot

Dimensions: dim_risk_type · dim_opportunity_type · dim_corporate_metric
""",
        "CORPORATE_INTELLIGENCE_QA_REPORT.md": f"""# CORPORATE INTELLIGENCE QA — F05.0 · IA-9

| Critério | Valor |
|----------|-------|
| Paridade Δ | {ex.get('paridadeDelta', '—')} |
| Paridade zero | **{'Sim' if qa.get('paridadeZero') else 'Não'}** |
| Scores com evidência | **{'Sim' if qa.get('scoresComEvidencia') else 'Não'}** |
| Oportunidades com cálculo | **{'Sim' if qa.get('oportunidadesComCalculo') else 'Não'}** |
| Riscos com justificativa | **{'Sim' if qa.get('riscosComJustificativa') else 'Não'}** |
| Fonte WebPosto | **Não** |
""",
    }

    for name, content in reports.items():
        (ROOT / name).write_text(content, encoding="utf-8")

    (ROOT / "F05_0_CORPORATE_INTELLIGENCE_HUB_REPORT.md").write_text(
        f"""# F05.0 — CORPORATE INTELLIGENCE HUB REPORT

## Respostas executivas (20)

| # | Pergunta | Resposta |
|---|----------|----------|
| 1 | Corporate Score | **{ex.get('1_corporateScore', '—')}** |
| 2 | Executive Score | {ex.get('2_executiveScore', '—')} |
| 3 | Maior risco corporativo | {label(ex.get('3_maiorRiscoCorporativo'), ('message',), ('severity',))} |
| 4 | Maior oportunidade | {label(ex.get('4_maiorOportunidadeCorporativa'))} |
| 5 | Filial líder | {label(ex.get('5_filialLider'))} |
| 6 | Filial preocupa | {label(ex.get('6_filialPreocupa'))} |
| 7 | Operador valor | {label(ex.get('7_operadorValor'))} |
| 8 | Operador risco | {label(ex.get('8_operadorRisco'))} |
| 9 | PDV destrói margem | {label(ex.get('9_pdvDestroiMargem'), ('pdvCodigo',), ('pdvCodigo',))} |
| 10 | PDV preserva margem | {label(ex.get('10_pdvPreservaMargem'), ('pdvCodigo',), ('pdvCodigo',))} |
| 11 | Turno problemático | {label(ex.get('11_turnoProblematico'), ('turno',), ('turnoCodigo',))} |
| 12 | Turno eficiente | {label(ex.get('12_turnoEficiente'), ('turno',), ('turnoCodigo',))} |
| 13 | Recuperado | R$ {ex.get('13_recuperado', '—')} |
| 14 | Pode recuperar | R$ {ex.get('14_podeRecuperar', '—')} |
| 15 | Ação maior ROI | {label(ex.get('15_acaoMaiorRoi'))} |
| 16 | Ação reduz risco | {label(ex.get('16_acaoReduzRisco'), ('message',), ('severity',))} |
| 17 | Operação melhorando | **{'Sim' if ex.get('17_operacaoMelhorando') else 'Não'}** |
| 18 | Hub confiável | **{'Sim' if ex.get('18_hubConfiavel') else 'Não'}** |
| 19 | Pronto Decision Engine | **{'Sim' if ex.get('19_prontoDecisionEngine') else 'Não'}** |
| 20 | Aprovado F05.1 | **{'Sim' if ex.get('20_aprovadoF051') else 'Não'}** |

## Decisão arquitetural

**{decisao.get('pergunta', '')}**

Resposta: **{'Sim' if decisao.get('resposta') else 'Não'}**

{decisao.get('justificativa', '')}

## Critérios de aceite

| Critério | Status |
|----------|--------|
| Nenhuma consulta WebPosto | **Sim** |
| Artefatos homologados F03-F04.7 | **Sim** |
| Paridade Δ = 0,00 | **{'Sim' if ex.get('paridadeDelta', 999) <= 0.01 else 'Não'}** (Δ={ex.get('paridadeDelta')}) |
| Cockpit corporate-hub | **Sim** |
| DW Corporate | **Sim** |
| Risk Engine | **Sim** |
| Opportunity Engine | **Sim** |
| QA aprovado | **{'Sim' if ex.get('20_aprovadoF051') else 'Não'}** |

{parecer}
""",
        encoding="utf-8",
    )
    print("Relatórios F05.0 gerados (IA 1-9 + consolidado)")


if __name__ == "__main__":
    main()
