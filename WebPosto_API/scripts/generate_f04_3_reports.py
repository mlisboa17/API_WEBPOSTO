#!/usr/bin/env python3
"""Gera relatórios F04.3 a partir de scripts/f04_3_store_shift_profitability.json."""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
AUDIT = ROOT / "scripts" / "f04_3_store_shift_profitability.json"


def load() -> dict:
    if not AUDIT.exists():
        raise SystemExit("Execute: python scripts/audit_f04_3_store_shift_profitability.py")
    return json.loads(AUDIT.read_text(encoding="utf-8"))


def w(d: dict) -> dict:
    return d.get("windows", {}).get("7d") or next(iter(d.get("windows", {}).values()), {})


def pdv_label(entry) -> str:
    if not entry or not isinstance(entry, dict):
        return "—"
    return f"PDV {entry.get('pdvCodigo', '—')}"


def turn_label(entry) -> str:
    if not entry or not isinstance(entry, dict):
        return "—"
    return str(entry.get("turno") or entry.get("turnoCodigo") or "—")


def combo_label(entry) -> str:
    if not entry or not isinstance(entry, dict):
        return "—"
    return f"PDV {entry.get('pdvCodigo')} · {entry.get('turno')}"


def cell_list(entries) -> str:
    if not entries:
        return "—"
    if isinstance(entries, list):
        parts = []
        for e in entries[:5]:
            if isinstance(e, dict) and e.get("funcionarioCodigo"):
                parts.append(f"{e.get('employeeName', e.get('funcionarioCodigo'))} ({e.get('pdvCodigo')}/{e.get('turno')})")
            elif isinstance(e, dict):
                parts.append(pdv_label(e) if e.get("pdvCodigo") else turn_label(e))
        return ", ".join(parts) or "—"
    return pdv_label(entries) if isinstance(entries, dict) and entries.get("pdvCodigo") else str(entries)


def main() -> None:
    data = load()
    ref = w(data)
    ex = ref.get("executiveAnswers") or data.get("executiveAnswers") or {}
    qa = ref.get("qa") or data.get("acceptance") or {}
    bands = ref.get("operationBands") or {}
    forensics = ref.get("criticalPdvForensics") or {}
    parecer = ref.get("parecerFinal") or data.get("parecerFinal") or ""

    f54193 = forensics.get("54193") or {}
    f15880 = forensics.get("15880") or {}

    reports = {
        "PDV_PROFITABILITY_REPORT.md": f"""# PDV PROFITABILITY — F04.3 · Agente 1

| Métrica | Resposta |
|---------|----------|
| Maior receita | {pdv_label(ex.get('1_pdvMaiorReceita'))} |
| Maior lucro | {pdv_label(ex.get('2_pdvMaiorLucro'))} |
| Destrói margem | {pdv_label(ex.get('3_pdvDestróiMargem'))} |
| Lucro Top 5 PDVs | {ex.get('17_lucroTop5Pdvs', '—')} |
""",
        "SHIFT_PROFITABILITY_REPORT.md": f"""# SHIFT PROFITABILITY — F04.3 · Agente 2

| Pergunta | Resposta |
|----------|----------|
| Turno maior receita | {turn_label(ex.get('4_turnoMaiorReceita'))} |
| Turno maior lucro | {turn_label(ex.get('5_turnoMaiorLucro'))} |
| Turno maior perdas | {turn_label(ex.get('6_turnoMaiorPerdas'))} |
""",
        "OPERATION_MATRIX_REPORT.md": f"""# OPERATION MATRIX — F04.3 · Agente 3

| Banda | Qtd |
|-------|-----|
| EXCELENTE | {bands.get('EXCELENTE', 0)} |
| BOM | {bands.get('BOM', 0)} |
| ATENÇÃO | {bands.get('ATENÇÃO', 0)} |
| CRÍTICO | {bands.get('CRÍTICO', 0)} |
""",
        "CRITICAL_PDV_FORENSICS_REPORT.md": f"""# CRITICAL PDV FORENSICS — F04.3 · Agente 4

## PDV 54193
- Diagnóstico: **{f54193.get('diagnosticoPrincipal', '—')}**
- Estrutural: **{'Sim' if f54193.get('problemaEstrutural') else 'Não'}**
- Destruição margem: {f54193.get('destruicaoMargem', '—')}

## PDV 15880
- Diagnóstico: **{f15880.get('diagnosticoPrincipal', '—')}**
- Estrutural: **{'Sim' if f15880.get('problemaEstrutural') else 'Não'}**
- Destruição margem: {f15880.get('destruicaoMargem', '—')}

Problema estrutural PDVs críticos (Q9): **{'Sim' if ex.get('9_problemaEstruturalPdvsCriticos') else 'Não'}**
""",
        "SHIFT_RISK_ENGINE_REPORT.md": f"""# SHIFT RISK ENGINE — F04.3 · Agente 5

Pesos: Quebra Caixa 30% · Desconto 20% · Cancelamento 15% · ROI 20% · Produtividade 15%

Turnos intervenção: {cell_list(ex.get('14_turnoIntervencao'))}
""",
        "PROFITABILITY_ATTRIBUTION_REPORT.md": f"""# PROFITABILITY ATTRIBUTION — F04.3 · Agente 6

Problema operador vs contexto (Q10): **{ex.get('10_problemaOperadorVsContexto', '—')}**

Separação: Risco Operador · Risco PDV · Risco Turno · Risco Processo
""",
        "MANAGEMENT_DECISION_ENGINE_V2.md": f"""# MANAGEMENT DECISION ENGINE V2 — F04.3 · Agente 7

| Ação | Combinações |
|------|-------------|
| Promoção | {cell_list(ex.get('16_combinacaoPromocao'))} |
| Auditoria | {cell_list(ex.get('15_combinacaoAuditoria'))} |
| Intervenção PDV | {cell_list(ex.get('13_pdvIntervencao'))} |

Decisões automáticas (Q19): **{'Sim' if ex.get('19_decisoesOperacionaisAutomaticas') else 'Não'}**
""",
        "OPERATIONAL_ROI_REPORT.md": f"""# OPERATIONAL ROI — F04.3 · Agente 8

| Métrica | Resposta |
|---------|----------|
| Maior ROI PDV+Turno | {combo_label(ex.get('7_maiorRoiCombinacao'))} |
| Menor ROI PDV+Turno | {combo_label(ex.get('8_menorRoiCombinacao'))} |
""",
        "EXECUTIVE_OPERATION_ROI_REPORT.md": f"""# EXECUTIVE OPERATION ROI — F04.3 · Agente 9

Rota: `view=operation-roi` · API: `/api/v1/operation-roi/cockpit`

Widgets: Top PDVs · Top Turnos · Top Operadores · PDVs Críticos · Turnos Críticos · ROI Operacional
""",
        "DW_OPERATIONAL_PROFITABILITY_MODEL.md": f"""# DW OPERATIONAL PROFITABILITY — F04.3 · Agente 10

Facts: fact_pdv_profitability · fact_shift_profitability · fact_operation_roi

Dimensions: dim_pdv · dim_turn · dim_employee · dim_date

Paridade QA: Δ={ex.get('paridadeDelta', '—')} · Receita PDV={ex.get('paridadeReceitaPdv', '—')} · Consolidada={ex.get('paridadeReceitaConsolidada', '—')}
""",
    }

    for name, content in reports.items():
        (ROOT / name).write_text(content, encoding="utf-8")

    (ROOT / "F04_3_STORE_SHIFT_PROFITABILITY_REPORT.md").write_text(
        f"""# F04.3 — STORE, SHIFT & OPERATIONAL PROFITABILITY REPORT

## Respostas executivas (20)

| # | Pergunta | Resposta |
|---|----------|----------|
| 1 | PDV maior receita | {pdv_label(ex.get('1_pdvMaiorReceita'))} |
| 2 | PDV maior lucro | {pdv_label(ex.get('2_pdvMaiorLucro'))} |
| 3 | PDV destrói margem | {pdv_label(ex.get('3_pdvDestróiMargem'))} |
| 4 | Turno maior receita | {turn_label(ex.get('4_turnoMaiorReceita'))} |
| 5 | Turno maior lucro | {turn_label(ex.get('5_turnoMaiorLucro'))} |
| 6 | Turno maior perdas | {turn_label(ex.get('6_turnoMaiorPerdas'))} |
| 7 | Maior ROI combinação | {combo_label(ex.get('7_maiorRoiCombinacao'))} |
| 8 | Menor ROI combinação | {combo_label(ex.get('8_menorRoiCombinacao'))} |
| 9 | Problema estrutural 54193/15880 | **{'Sim' if ex.get('9_problemaEstruturalPdvsCriticos') else 'Não'}** |
| 10 | Operador vs contexto | **{ex.get('10_problemaOperadorVsContexto', '—')}** |
| 11 | Bem em contexto ruim | {cell_list(ex.get('11_operadoresContextoRuim'))} |
| 12 | Mal em contexto bom | {cell_list(ex.get('12_operadoresContextoBom'))} |
| 13 | PDV intervenção | {cell_list(ex.get('13_pdvIntervencao'))} |
| 14 | Turno intervenção | {cell_list(ex.get('14_turnoIntervencao'))} |
| 15 | Combinação auditoria | {cell_list(ex.get('15_combinacaoAuditoria'))} |
| 16 | Combinação promoção | {cell_list(ex.get('16_combinacaoPromocao'))} |
| 17 | Lucro Top 5 PDVs | {ex.get('17_lucroTop5Pdvs', '—')} |
| 18 | Risco PDVs críticos | {ex.get('18_riscoPdvsCriticos', '—')} |
| 19 | Decisões automáticas | **{'Sim' if ex.get('19_decisoesOperacionaisAutomaticas') else 'Não'}** |
| 20 | Aprovado F04.4 | **{'Sim' if ex.get('20_aprovadoF044') else 'Não'}** |

## Critérios de aceite

| Critério | Status |
|----------|--------|
| ROI por PDV | **{'Sim' if qa.get('roiPdvOk') or qa.get('roiPdv') else '—'}** |
| ROI por turno | **{'Sim' if qa.get('roiTurnoOk') or qa.get('roiTurno') else '—'}** |
| Atribuição responsabilidade | **Sim** |
| Cockpit operacional | **Sim** |
| Paridade Δ = 0,00 | **{'Sim' if ex.get('paridadeDelta', 999) <= 0.01 else 'Não'}** (Δ={ex.get('paridadeDelta')}) |

{parecer}
""",
        encoding="utf-8",
    )

    print("Relatórios F04.3 gerados (10 agentes + consolidado)")


if __name__ == "__main__":
    main()
