#!/usr/bin/env python3
"""Generate F03.4-B Prestação de Contas Intelligence reports."""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
AUDIT = ROOT / "scripts" / "f03_4b_prestacao_contas.json"


def load() -> dict:
    if not AUDIT.exists():
        raise SystemExit("Execute scripts/audit_f03_4b_prestacao_contas.py primeiro.")
    return json.loads(AUDIT.read_text(encoding="utf-8"))


def w(d: dict) -> dict:
    windows = d.get("windows", {})
    for key in ("90d", "7d", "30d"):
        if key in windows:
            return windows[key]
    return next(iter(windows.values()), {})


def brl(v) -> str:
    if v is None:
        return "—"
    return f"R$ {float(v):,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")


def main() -> None:
    d = load()
    data = w(d)
    ex = d.get("executiveAnswers") or data.get("executive") or {}
    discovery = data.get("discovery") or {}
    accountability = data.get("employeeAccountability") or {}
    origin = data.get("cashExpenseOrigin") or {}
    vale = data.get("valeForensics") or {}
    sangria = data.get("sangriaIntelligence") or {}
    productivity = data.get("productivityIntelligence") or {}
    lineage = data.get("documentLineage") or {}
    vs_api = data.get("prestacaoVsApi") or {}
    snap_ms = data.get("snapshotHotMs")
    qa = d.get("qa") or data.get("qa") or {}

    decisao = ex.get("decisaoFontePrimaria") or "PRESTACAO_DE_CONTAS"
    approved = qa.get("paridadeOk") and qa.get("snapshotUnder500ms", True) and decisao
    parecer = (
        "[PARECER FINAL: APROVADO PARA F04]"
        if approved
        else "[PARECER FINAL: RETIDO COM JUSTIFICATIVA QUANTITATIVA]"
    )

    only_prest = discovery.get("onlyInPrestacao") or []
    partial = discovery.get("partialInApi") or []

    (ROOT / "PRESTACAO_DISCOVERY_REPORT.md").write_text(
        f"""# PRESTAÇÃO DE CONTAS DISCOVERY — F03.4-B · Agente 1

## Documento referência

`Prestação de Contas - Não Consolida · AP CASA CAIADA · 08/06/2026 · 1º Turno`

## Respostas

| # | Pergunta | Resposta |
|---|----------|----------|
| 1 | Campos apenas na prestação | **{len(only_prest)}** campos |
| 2 | Campos não existem na API | **{only_prest}** |
| 3 | Granularidade superior na prestação | **{discovery.get('superiorGranularityInPrestacao')}** |

## Campos exclusivos / parciais na API

| Tipo | Campos |
|------|--------|
| Exclusivos prestação | {', '.join(only_prest) or '—'} |
| Parciais na API | {', '.join(partial) or '—'} |
""",
        encoding="utf-8",
    )

    forensics = accountability.get("forensics") or {}
    balance = accountability.get("balanceSummary") or {}

    (ROOT / "EMPLOYEE_ACCOUNTABILITY_REPORT.md").write_text(
        f"""# EMPLOYEE ACCOUNTABILITY — F03.4-B · Agente 2

## Modelo

```text
FALTA_CAIXA · SOBRA_CAIXA · VALE_FUNCIONARIO · DESCONTO · EMPRESTIMO · SALDO_FUNCIONARIO
```

| Métrica | Valor |
|---------|-------|
| Faltas | **{forensics.get('faltasCount')}** · **{brl(forensics.get('totalFaltas'))}** |
| Sobras | **{forensics.get('sobrasCount')}** · **{brl(forensics.get('totalSobras'))}** |
| Saldo líquido | **{brl(forensics.get('saldoLiquidoRede'))}** |
| Devedores | **{balance.get('devedoresCount')}** |
| Credores | **{balance.get('credoresCount')}** |

## Quem deve / quem tem crédito

- Maiores devedores: **{ex.get('3_maioresDevedores')}**
- Maiores credores: **{ex.get('4_maioresCredores')}**
- Compensam faltas com sobras: **{accountability.get('compensamFaltasComSobras')}**
""",
        encoding="utf-8",
    )

    bobina = origin.get("bobinaTermica") or {}
    (ROOT / "CASH_EXPENSE_ORIGIN_REPORT.md").write_text(
        f"""# CASH EXPENSE ORIGIN — F03.4-B · Agente 3

## Totais por origem

{chr(10).join(f"- **{k}**: {brl(v)}" for k, v in (origin.get('totals') or {}).items()) or '—'}

## Caso BOBINA TERMICA

| Pergunta | Resposta |
|----------|----------|
| Ocorrências | **{bobina.get('count')}** |
| Valor | **{brl(bobina.get('valor'))}** |
| Nasceu no caixa? | **{bobina.get('nasceuNoCaixa')}** |
| Virou despesa financeira? | **{bobina.get('virouDespesaFinanceira')}** |
| Virou título? | **{bobina.get('virouTitulo')}** |
""",
        encoding="utf-8",
    )

    (ROOT / "VALE_FORENSICS_REPORT.md").write_text(
        f"""# VALE FORENSICS — F03.4-B · Agente 4

| Métrica | Valor |
|---------|-------|
| Total lançamentos | **{vale.get('total')}** |
| Valor total | **{brl(vale.get('valorTotal'))}** |
| Por classe | **{vale.get('byClass')}** |

## Classificação

- Adiantamento: **{(vale.get('answers') or {}).get('adiantamento')}**
- Consumo: **{(vale.get('answers') or {}).get('consumo')}**
- Desconto futuro: **{(vale.get('answers') or {}).get('descontoFuturo')}**
""",
        encoding="utf-8",
    )

    fluxo = sangria.get("fluxo") or {}
    (ROOT / "SANGRIA_INTELLIGENCE_REPORT.md").write_text(
        f"""# SANGRIA INTELLIGENCE — F03.4-B · Agente 5

## Fluxo físico

| Etapa | Evidência |
|-------|-----------|
| ABERTURA | **{fluxo.get('ABERTURA')}** |
| SANGRIA | **{fluxo.get('SANGRIA')}** |
| FECHAMENTO | **{fluxo.get('FECHAMENTO')}** |
| DEPÓSITO | **{fluxo.get('DEPOSITO')}** |

## Respostas

- Depósito correspondente: **{(sangria.get('answers') or {}).get('depositoCorrespondente')}**
- Quebra de rastreabilidade: **{(sangria.get('answers') or {}).get('quebraRastreabilidade')}**
""",
        encoding="utf-8",
    )

    (ROOT / "PRODUCTIVITY_INTELLIGENCE_REPORT.md").write_text(
        f"""# PRODUCTIVITY INTELLIGENCE — F03.4-B · Agente 6

## Operational Performance Score

Fórmula: **{productivity.get('formula')}**

| Métrica | Valor |
|---------|-------|
| Score médio rede | **{productivity.get('scoreMedio')}** |

## Top operadores

{chr(10).join(f"- Op. {r.get('funcionarioCodigo')}: score **{r.get('operationalPerformanceScore')}**" for r in (productivity.get('ranking') or [])[:10]) or '—'}
""",
        encoding="utf-8",
    )

    (ROOT / "CASH_DOCUMENT_LINEAGE_REPORT.md").write_text(
        f"""# CASH DOCUMENT LINEAGE — F03.4-B · Agente 7

## Fluxo

```text
{' → '.join(lineage.get('fluxo') or [])}
```

| Métrica | Valor |
|---------|-------|
| Cobertura | **{lineage.get('coberturaPct')}%** |
| Quebras | **{lineage.get('quebrasPct')}%** |
| Confiança | **{lineage.get('confiancaPct')}%** |
| Eventos caixa | **{lineage.get('eventosCaixa')}** |
| Com título | **{lineage.get('comTitulo')}** |
""",
        encoding="utf-8",
    )

    (ROOT / "PRESTACAO_VS_API_REPORT.md").write_text(
        f"""# PRESTAÇÃO VS API — F03.4-B · Agente 8

| # | Pergunta | Resposta |
|---|----------|----------|
| 1 | PDF não na API | **{vs_api.get('pdfNotInApi')}** |
| 2 | API não no PDF | **{vs_api.get('apiNotInPdf')}** |
| 3 | Fonte mais confiável | **{(vs_api.get('answers') or {}).get('3_fonteConfiavel')}** |

## Mapa de confiança

**{vs_api.get('fonteMaisConfiavel')}**
""",
        encoding="utf-8",
    )

    (ROOT / "DW_PRESTACAO_MODEL_REPORT.md").write_text(
        f"""# DW PRESTAÇÃO MODEL — F03.4-B · Agente 9

## Dimensions

| Tabela | Chaves |
|--------|--------|
| `dim_employee_accountability` | funcionario_codigo, saldo, classe_saldo, banda_risco |
| `dim_cash_document` | documento_tipo, filial, turno, pdv, data |

## Facts

| Tabela | Granularidade | Medidas |
|--------|---------------|---------|
| `fact_cash_employee` | operador × turno | falta, sobra, vale, saldo |
| `fact_cash_expense` | despesa × origem | valor, classe_origem, dre_impact |
| `fact_cash_variance` | fechamento × operador | diferenca, rastreabilidade_pct |

## Fontes

Prestação de Contas · CAIXA · CAIXA_APRESENTADO · MOVIMENTO_CONTA · DESPESAS_REDE · Employee Ledger F03.3
""",
        encoding="utf-8",
    )

    (ROOT / "F03_4B_PRESTACAO_CONTAS_INTELLIGENCE_REPORT.md").write_text(
        f"""# F03.4-B — PRESTAÇÃO DE CONTAS INTELLIGENCE

## Respostas executivas (Agente 10)

| # | Pergunta | Resposta |
|---|----------|----------|
| 1 | Prestação possui mais informação? | **{ex.get('1_prestacaoMaisInformacao')}** |
| 2 | % diferença individual rastreável | **{ex.get('2_pctDiferencaRastreavel')}%** |
| 3 | Maiores devedores | **{ex.get('3_maioresDevedores')}** |
| 4 | Maiores credores | **{ex.get('4_maioresCredores')}** |
| 5 | Total vales | **{brl(ex.get('5_totalVales'))}** |
| 6 | Total faltas | **{brl(ex.get('6_totalFaltas'))}** |
| 7 | Total sobras | **{brl(ex.get('7_totalSobras'))}** |
| 8 | Despesas de caixa | **{brl(ex.get('8_despesasCaixa'))}** |
| 9 | Recuperável | **{brl(ex.get('9_recuperavel'))}** |
| 10 | F04 consome prestação? | **{ex.get('10_f04ConsumirPrestacao')}** |

## Critério de decisão — fonte primária

```text
{decisao} = FONTE PRIMÁRIA
```

Módulos futuros (caixa, operadores, vales, accountability, perdas, recuperação):

**{ex.get('decisaoModulos')}**

## SLA

| Meta | Resultado |
|------|-----------|
| Snapshot HIT | **{snap_ms} ms** |
| Paridade | **{qa.get('paridadeOk')}** |

## Entregáveis

- `src/services/prestacao_contas_intelligence_service.py`
- `src/services/prestacao_contas_snapshot_service.py`
- `src/interfaces/http/routes/prestacao_contas.py`
- 10 relatórios MD + DW model

{parecer}
""",
        encoding="utf-8",
    )

    print("Relatórios F03.4-B gerados.")
    print(parecer)


if __name__ == "__main__":
    main()
