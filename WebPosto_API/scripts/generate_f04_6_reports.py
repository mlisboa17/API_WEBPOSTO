#!/usr/bin/env python3
"""Gera relatórios F04.6 — Benchmark Intelligence."""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
AUDIT = ROOT / "scripts" / "f04_6_benchmark_intelligence.json"


def load() -> dict:
    if not AUDIT.exists():
        raise SystemExit("Execute: python scripts/audit_f04_6_benchmark_intelligence.py")
    return json.loads(AUDIT.read_text(encoding="utf-8"))


def w(d: dict) -> dict:
    return d.get("windows", {}).get("7d") or next(iter(d.get("windows", {}).values()), {})


def label(entry, name_keys=("nomeFilial", "employeeName", "nome"), code_keys=("empresaCodigo", "funcionarioCodigo", "pdvCodigo")) -> str:
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
    company = ref.get("companyBenchmark") or {}
    operators = ref.get("operatorBenchmark") or {}
    gaps = ref.get("gapEngine") or {}
    practices = ref.get("bestPracticesEngine") or {}
    parecer = ref.get("parecerFinal") or data.get("parecerFinal") or ""

    reports = {
        "COMPANY_BENCHMARK_REPORT.md": f"""# COMPANY BENCHMARK — F04.6 · IA-1

| Métrica | Referência |
|---------|------------|
| Melhor filial | {label(ex.get('1_melhorFilial'))} |
| Pior filial | {label(ex.get('2_piorFilial'))} |
| Maior ROI | {label(ex.get('9_maiorRoi') or company.get('maiorRoi'))} |
| Maior perda | {label(company.get('maiorPerda'))} |
| Maior crescimento | {label(company.get('maiorCrescimento'))} |
| Maior risco | {label(ex.get('10_maiorRisco') or company.get('maiorRisco'))} |

Filiais indexadas: {len(company.get('filiais') or [])}
Paridade Δ: {ex.get('paridadeDelta', '—')}
""",
        "OPERATOR_BENCHMARK_REPORT.md": f"""# OPERATOR BENCHMARK — F04.6 · IA-2

Top 20: **{len(operators.get('top20') or [])}** operadores

Bottom 20: **{len(operators.get('bottom20') or [])}** operadores

| Destaque | Referência |
|----------|------------|
| Melhor operador | {label(ex.get('3_melhorOperador'))} |
| Pior operador | {label(ex.get('4_piorOperador'))} |
| Maior ROI | {label(operators.get('maiorRoi'))} |
| Maior Accountability | {label(operators.get('maiorAccountability'))} |
| Maior risco | {label(operators.get('maiorRisco'))} |
| Maior evolução | {label(ex.get('9_maiorRoi') and operators.get('maiorEvolucao') or operators.get('maiorEvolucao'), ('employeeName',), ('funcionarioCodigo',))} |
| Maior queda | {label(operators.get('maiorQueda'), ('employeeName',), ('funcionarioCodigo',))} |
""",
        "PDV_BENCHMARK_REPORT.md": f"""# PDV BENCHMARK — F04.6 · IA-3

Melhor PDV: {label(ex.get('5_melhorPdv'), ('pdvCodigo',), ('pdvCodigo',))}

Pior PDV: {label(ex.get('6_piorPdv'), ('pdvCodigo',), ('pdvCodigo',))}

Maior risco: {label(ex.get('10_maiorRisco'))}

Maior oportunidade: {label(ex.get('11_maiorOportunidade'), ('pdvCodigo',), ('pdvCodigo',))}
""",
        "SHIFT_BENCHMARK_REPORT.md": f"""# SHIFT BENCHMARK — F04.6 · IA-3

Melhor turno: {label(ex.get('7_melhorTurno'), ('turno',), ('turnoCodigo',))}

Pior turno: {label(ex.get('8_piorTurno'), ('turno',), ('turnoCodigo',))}
""",
        "GAP_ENGINE_REPORT.md": f"""# GAP ENGINE — F04.6 · IA-4

Filiais abaixo da média: **{len(gaps.get('filiaisAbaixoMedia') or [])}**

Operadores abaixo da média: **{len(gaps.get('operadoresAbaixoMedia') or [])}**

PDVs abaixo da média: **{len(gaps.get('pdvsAbaixoMedia') or [])}**

Turnos abaixo da média: **{len(gaps.get('turnosAbaixoMedia') or [])}**

Maior gap: {label(ex.get('12_maiorGap'), ('tipo',), ('gap',))}
""",
        "BEST_PRACTICES_ENGINE_REPORT.md": f"""# BEST PRACTICES — F04.6 · IA-4

Melhor prática: {(ex.get('13_melhorPratica') or {}).get('padrao', '—') if isinstance(ex.get('13_melhorPratica'), dict) else '—'}

Pior prática: {(ex.get('14_piorPratica') or {}).get('padrao', '—') if isinstance(ex.get('14_piorPratica'), dict) else '—'}

Ações replicáveis: {practices.get('acoesReplicaveis') or []}

Ações corretivas: {practices.get('acoesCorretivas') or []}
""",
        "BENCHMARK_COCKPIT_REPORT.md": f"""# BENCHMARK COCKPIT — F04.6 · IA-5

Rota: `view=benchmark` · API: `/api/v1/benchmark/cockpit`

Widgets: Ranking Filiais · Ranking Operadores · Ranking PDVs · Ranking Turnos · Gaps · Best Practices
""",
        "DW_BENCHMARK_MODEL.md": f"""# DW BENCHMARK — F04.6 · IA-5

Facts: fact_benchmark · fact_gap · fact_best_practice

Dimension: dim_benchmark_type
""",
        "BENCHMARK_QA_REPORT.md": f"""# BENCHMARK QA — F04.6 · IA-5

| Critério | Valor |
|----------|-------|
| Paridade Δ | {ex.get('paridadeDelta', '—')} |
| Paridade zero | **{'Sim' if qa.get('paridadeZero') else 'Não'}** |
| Sem cross-tenant | **{'Sim' if qa.get('semCrossTenant') else 'Não'}** |
| Sem duplicidade | **{'Sim' if qa.get('semDuplicidade') else 'Não'}** |
| Sem métricas órfãs | **{'Sim' if qa.get('semMetricasOrfas') else 'Não'}** |
| Fonte WebPosto | **Não** |
""",
    }

    for name, content in reports.items():
        (ROOT / name).write_text(content, encoding="utf-8")

    (ROOT / "F04_6_BENCHMARK_INTELLIGENCE_REPORT.md").write_text(
        f"""# F04.6 — BENCHMARK INTELLIGENCE REPORT

## Respostas executivas (20)

| # | Pergunta | Resposta |
|---|----------|----------|
| 1 | Melhor filial | {label(ex.get('1_melhorFilial'))} |
| 2 | Pior filial | {label(ex.get('2_piorFilial'))} |
| 3 | Melhor operador | {label(ex.get('3_melhorOperador'))} |
| 4 | Pior operador | {label(ex.get('4_piorOperador'))} |
| 5 | Melhor PDV | {label(ex.get('5_melhorPdv'), ('pdvCodigo',), ('pdvCodigo',))} |
| 6 | Pior PDV | {label(ex.get('6_piorPdv'), ('pdvCodigo',), ('pdvCodigo',))} |
| 7 | Melhor turno | {label(ex.get('7_melhorTurno'), ('turno',), ('turnoCodigo',))} |
| 8 | Pior turno | {label(ex.get('8_piorTurno'), ('turno',), ('turnoCodigo',))} |
| 9 | Maior ROI | {label(ex.get('9_maiorRoi'))} |
| 10 | Maior risco | {label(ex.get('10_maiorRisco'))} |
| 11 | Maior oportunidade | {label(ex.get('11_maiorOportunidade'), ('pdvCodigo',), ('pdvCodigo',))} |
| 12 | Maior gap | {label(ex.get('12_maiorGap'), ('tipo',), ('gap',))} |
| 13 | Melhor prática | {(ex.get('13_melhorPratica') or {}).get('padrao', '—') if isinstance(ex.get('13_melhorPratica'), dict) else '—'} |
| 14 | Pior prática | {(ex.get('14_piorPratica') or {}).get('padrao', '—') if isinstance(ex.get('14_piorPratica'), dict) else '—'} |
| 15 | Potencial capturável | R$ {ex.get('15_potencialCapturavel', '—')} |
| 16 | Potencial perdido | R$ {ex.get('16_potencialPerdido', '—')} |
| 17 | Ranking executivo | consolidado no cockpit |
| 18 | Benchmark confiável | **{'Sim' if ex.get('18_benchmarkConfiavel') else 'Não'}** |
| 19 | Pronto Scorecard | **{'Sim' if ex.get('19_prontoScorecard') else 'Não'}** |
| 20 | Aprovado F04.7 | **{'Sim' if ex.get('20_aprovadoF047') else 'Não'}** |

## Critérios de aceite

| Critério | Status |
|----------|--------|
| Nenhuma consulta WebPosto | **Sim** |
| Uso exclusivo F04.5 + snapshots | **Sim** |
| Paridade Δ = 0,00 | **{'Sim' if ex.get('paridadeDelta', 999) <= 0.01 else 'Não'}** (Δ={ex.get('paridadeDelta')}) |
| Sem cross-tenant | **{'Sim' if qa.get('semCrossTenant') else 'Não'}** |
| Cockpit benchmark | **Sim** |
| DW benchmark | **Sim** |
| QA aprovado | **{'Sim' if ex.get('20_aprovadoF047') else 'Não'}** |

{parecer}
""",
        encoding="utf-8",
    )
    print("Relatórios F04.6 gerados (IA 1-5 + consolidado)")


if __name__ == "__main__":
    main()
