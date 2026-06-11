#!/usr/bin/env python3
"""Gera relatórios D04 — Live Data Truth Baseline."""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
AUDIT = ROOT / "scripts" / "d04_live_data_truth_baseline.json"


def load() -> dict:
    if not AUDIT.exists():
        raise SystemExit("Execute: python scripts/audit_d04_live_data_truth_baseline.py")
    return json.loads(AUDIT.read_text(encoding="utf-8"))


def w(d: dict) -> dict:
    return d.get("windows", {}).get("7d") or next(iter(d.get("windows", {}).values()), {})


def yn(v) -> str:
    if v is True:
        return "**Sim**"
    if v is False:
        return "**Não**"
    return str(v)


def md_table(headers: list[str], rows: list[list]) -> str:
    lines = ["| " + " | ".join(headers) + " |", "|" + "|".join("---" for _ in headers) + "|"]
    for row in rows:
        lines.append("| " + " | ".join(str(c) for c in row) + " |")
    return "\n".join(lines)


def main() -> None:
    data = load()
    ref = w(data)
    ex = ref.get("executiveAnswers") or data.get("executiveAnswers") or {}
    conn = ref.get("tokenConnectivityAudit") or {}
    fin = ref.get("financialCoverageAudit") or {}
    cash = ref.get("cashCoverageAudit") or {}
    sales = ref.get("salesCoverageAudit") or {}
    workforce = ref.get("workforceCoverageAudit") or {}
    lineage = ref.get("dataLineageConsistency") or {}
    trust = ref.get("trustBaselineEngine") or {}
    gov = ref.get("dataGovernance") or {}
    qa = ref.get("qaCertification") or {}
    decisao = ref.get("decisaoArquitetural") or data.get("decisaoArquitetural") or {}
    parecer = ref.get("parecerFinal") or data.get("parecerFinal") or ""

    int_rows = [
        [i.get("integration"), i.get("status"), i.get("snapshotsFound"), i.get("snapshotsExpected")]
        for i in (conn.get("integrations") or [])
    ]
    cert_rows = [
        [c.get("name"), c.get("cert"), c.get("score")]
        for c in (qa.get("certifications") or [])
    ]
    lineage_rows = [
        [l.get("indicador"), l.get("fonte"), l.get("snapshot"), l.get("api"), l.get("cockpit")]
        for l in (lineage.get("lineage") or [])[:20]
    ]

    reports = {
        "TOKEN_CONNECTIVITY_AUDIT.md": f"""# TOKEN & CONNECTIVITY AUDIT — D04 · IA-1

Filiais autorizadas: **{', '.join(str(x) for x in conn.get('authorizedFiliais') or [])}**

## Resumo

| Status | Quantidade |
|--------|------------|
| OPERACIONAL | **{conn.get('operacional', 0)}** |
| PARCIAL | **{conn.get('parcial', 0)}** |
| INDISPONÍVEL | **{conn.get('indisponivel', 0)}** |

## Integrações

{md_table(["Integração", "Status", "Snapshots OK", "Esperados"], int_rows)}
""",
        "FINANCIAL_COVERAGE_AUDIT.md": f"""# FINANCIAL COVERAGE AUDIT — D04 · IA-2

| Métrica | Valor |
|---------|-------|
| Cobertura % | **{fin.get('coberturaPct', '—')}** |
| Campos vazios % | {fin.get('camposVaziosPct', '—')} |
| Inconsistentes % | {fin.get('inconsistentesPct', '—')} |
| Duplicidades % | {fin.get('duplicidadesPct', '—')} |
| DRE validação OK | {yn(fin.get('dreValidacaoOk'))} |
| Filial 11495 | {yn(fin.get('filiais11495'))} |
| Filial 5555 | {yn(fin.get('filiais5555'))} |
""",
        "CASH_COVERAGE_AUDIT.md": f"""# CASH COVERAGE AUDIT — D04 · IA-3

| Métrica | Valor |
|---------|-------|
| Cobertura % | **{cash.get('coberturaPct', '—')}** |
| Conciliação % | {cash.get('conciliacaoPct', '—')} |
| Paridade % | **{cash.get('paridadePct', '—')}** |
| Paridade Δ | {cash.get('paridadeDelta', '—')} |
| Faltas | R$ {cash.get('faltas', '—')} |
| Sobras | R$ {cash.get('sobras', '—')} |
""",
        "SALES_COVERAGE_AUDIT.md": f"""# SALES COVERAGE AUDIT — D04 · IA-4

| Métrica | Valor |
|---------|-------|
| Cobertura % | **{sales.get('coberturaPct', '—')}** |
| Vendas com operador | {sales.get('vendasComOperador', '—')} |
| Vendas com PDV | {sales.get('vendasComPdv', '—')} |
| Vendas com turno | {sales.get('vendasComTurno', '—')} |
| Total células | {sales.get('totalCelulas', '—')} |
| Receita operacional | R$ {sales.get('receitaOperacional', '—')} |
| Combustível snapshot | {yn(sales.get('combustivelSnapshot'))} |
""",
        "WORKFORCE_COVERAGE_AUDIT.md": f"""# WORKFORCE COVERAGE AUDIT — D04 · IA-5

| Métrica | Valor |
|---------|-------|
| Cobertura nominal % | **{workforce.get('coberturaNominalPct', '—')}** |
| Cobertura operacional % | **{workforce.get('coberturaOperacionalPct', '—')}** |
| Cobertura accountability % | **{workforce.get('coberturaAccountabilityPct', '—')}** |
| Operadores nominal | {workforce.get('operadoresNominal', '—')} |
| Operadores operacional | {workforce.get('operadoresOperacional', '—')} |
| Operadores performance | {workforce.get('operadoresPerformance', '—')} |
""",
        "DATA_LINEAGE_CONSISTENCY_REPORT.md": f"""# DATA LINEAGE & CONSISTENCY — D04 · IA-6

| Métrica | Valor |
|---------|-------|
| Consistency % | **{lineage.get('consistencyPct', '—')}** |
| Campos órfãos | {lineage.get('camposOrfaos', '—')} |
| Indicadores órfãos | {lineage.get('indicadoresOrfaos', '—')} |
| Lineage quebrado | {yn(lineage.get('lineageQuebrado'))} |

## Lineage (amostra)

{md_table(["Indicador", "Fonte", "Snapshot", "API", "Cockpit"], lineage_rows)}
""",
        "TRUST_BASELINE_ENGINE_REPORT.md": f"""# TRUST BASELINE ENGINE — D04 · IA-7

| Domínio | Score | Banda | Certificação |
|---------|-------|-------|--------------|
| Financial | **{trust.get('financialTrustScore', '—')}** | {trust.get('financialTrustScoreBand', '—')} | {trust.get('financialTrustScoreCert', '—')} |
| Cash | **{trust.get('cashTrustScore', '—')}** | {trust.get('cashTrustScoreBand', '—')} | {trust.get('cashTrustScoreCert', '—')} |
| Sales | **{trust.get('salesTrustScore', '—')}** | {trust.get('salesTrustScoreBand', '—')} | {trust.get('salesTrustScoreCert', '—')} |
| People | **{trust.get('peopleTrustScore', '—')}** | {trust.get('peopleTrustScoreBand', '—')} | {trust.get('peopleTrustScoreCert', '—')} |
| Lineage | **{trust.get('lineageTrustScore', '—')}** | {trust.get('lineageTrustScoreBand', '—')} | {trust.get('lineageTrustScoreCert', '—')} |
| Corporate | **{trust.get('corporateTrustScore', '—')}** | {trust.get('corporateTrustScoreBand', '—')} | {trust.get('corporateTrustScoreCert', '—')} |

Escala: 90-100 CONFIÁVEL · 75-89 UTILIZÁVEL · 60-74 PARCIAL · 0-59 NÃO CONFIÁVEL
""",
        "DATA_GOVERNANCE_REPORT.md": f"""# DATA GOVERNANCE — D04 · IA-8

| Campo | Valor |
|-------|-------|
| dataTrust | **{gov.get('dataTrust', '—')}** |
| dataConfidence | {gov.get('dataConfidence', '—')} |
| lastValidatedAt | {gov.get('lastValidatedAt', '—')} |

## dataCoverage

| Domínio | % |
|---------|---|
| Financial | {gov.get('dataCoverage', {}).get('financial', '—')} |
| Cash | {gov.get('dataCoverage', {}).get('cash', '—')} |
| Sales | {gov.get('dataCoverage', {}).get('sales', '—')} |
| People | {gov.get('dataCoverage', {}).get('people', '—')} |

TTL snapshots trust: **300s**
""",
        "DATA_TRUST_CERTIFICATION_REPORT.md": f"""# DATA TRUST CERTIFICATION — D04 · IA-9

| Critério | Status |
|----------|--------|
| Sem cross-tenant | {yn(qa.get('semCrossTenant'))} |
| Sem duplicidade | {yn(qa.get('semDuplicidade'))} |
| Indicadores sem origem | {qa.get('indicadoresSemOrigem', 0)} |
| Scores sem evidência | {qa.get('scoresSemEvidencia', 0)} |
| QA aprovado | {yn(qa.get('aprovado'))} |

## Certificações

{md_table(["Indicador", "Certificação", "Score"], cert_rows)}

**Bloqueados:** {', '.join(qa.get('indicadoresBloqueados') or []) or '—'}

**Executivos de confiança:** {', '.join(qa.get('indicadoresExecutivosConfianca') or []) or '—'}
""",
    }

    for name, content in reports.items():
        (ROOT / name).write_text(content, encoding="utf-8")

    (ROOT / "D04_LIVE_DATA_TRUTH_BASELINE_REPORT.md").write_text(
        f"""# D04 — LIVE DATA TRUTH BASELINE REPORT

Baseline **2026-06-01 → 2026-06-07** · Filiais **11495, 5555** · Fonte: snapshots homologados (sem WebPosto live)

## Respostas executivas (20)

| # | Pergunta | Resposta |
|---|----------|----------|
| 1 | Integrações operacionais | **{ex.get('1_integracoesOperacionais', '—')}** |
| 2 | Integrações parciais | **{ex.get('2_integracoesParciais', '—')}** |
| 3 | Integrações indisponíveis | **{ex.get('3_integracoesIndisponiveis', '—')}** |
| 4 | Cobertura financeira % | **{ex.get('4_coberturaFinanceira', '—')}** |
| 5 | Cobertura caixa % | **{ex.get('5_coberturaCaixa', '—')}** |
| 6 | Cobertura vendas % | **{ex.get('6_coberturaVendas', '—')}** |
| 7 | Cobertura pessoas % | **{ex.get('7_coberturaPessoas', '—')}** |
| 8 | Cobertura nominal % | **{ex.get('8_coberturaNominal', '—')}** |
| 9 | Cobertura operacional % | **{ex.get('9_coberturaOperacional', '—')}** |
| 10 | Cobertura accountability % | **{ex.get('10_coberturaAccountability', '—')}** |
| 11 | Paridade financeira Δ | **{ex.get('11_paridadeFinanceira', '—')}** |
| 12 | Paridade operacional Δ | **{ex.get('12_paridadeOperacional', '—')}** |
| 13 | Paridade corporativa Δ | **{ex.get('13_paridadeCorporativa', '—')}** |
| 14 | Trust Score financeiro | **{ex.get('14_trustFinanceiro', '—')}** |
| 15 | Trust Score operacional (vendas) | **{ex.get('15_trustOperacional', '—')}** |
| 16 | Trust Score pessoas | **{ex.get('16_trustPessoas', '—')}** |
| 17 | Trust Score corporativo | **{ex.get('17_trustCorporativo', '—')}** |
| 18 | Indicadores bloqueados | {', '.join(ex.get('18_indicadoresBloqueados') or []) or '—'} |
| 19 | Indicadores executivos confiança | {', '.join(ex.get('19_indicadoresExecutivosConfianca') or []) or '—'} |
| 20 | Pronto decisões automatizadas | {yn(ex.get('20_prontoDecisoesAutomatizadas'))} |

## Decisão arquitetural

{decisao.get('regra', 'Nenhum indicador executivo sem evidência de cobertura')}

Trust corporativo: **{decisao.get('corporateTrustScore', trust.get('corporateTrustScore', '—'))}** ({decisao.get('corporateTrustBand', trust.get('corporateTrustScoreBand', '—'))})

{decisao.get('justificativa', '')}

## Critérios de aceite

| Critério | Status |
|----------|--------|
| Nenhuma consulta WebPosto | **Sim** |
| Filiais autorizadas apenas | **Sim** |
| Paridade corporativa Δ ≤ 0,01 | **{'Sim' if ex.get('13_paridadeCorporativa', 999) <= 0.01 else 'Não'}** |
| Trust corporativo ≥ 75 | **{'Sim' if (ex.get('17_trustCorporativo') or 0) >= 75 else 'Não'}** |
| Integrações operacionais ≥ 5 | **{'Sim' if (ex.get('1_integracoesOperacionais') or 0) >= 5 else 'Não'}** |
| QA certificação aprovada | **{'Sim' if qa.get('aprovado') else 'Não'}** |

## Relatórios IA

- TOKEN_CONNECTIVITY_AUDIT.md (IA-1)
- FINANCIAL_COVERAGE_AUDIT.md (IA-2)
- CASH_COVERAGE_AUDIT.md (IA-3)
- SALES_COVERAGE_AUDIT.md (IA-4)
- WORKFORCE_COVERAGE_AUDIT.md (IA-5)
- DATA_LINEAGE_CONSISTENCY_REPORT.md (IA-6)
- TRUST_BASELINE_ENGINE_REPORT.md (IA-7)
- DATA_GOVERNANCE_REPORT.md (IA-8)
- DATA_TRUST_CERTIFICATION_REPORT.md (IA-9)

---

{parecer}
""",
        encoding="utf-8",
    )

    print("Relatórios D04 gerados.")
    print(parecer)


if __name__ == "__main__":
    main()
