# F02.1-B CASH ROOT CAUSE REPORT

**Sprint:** F02.1-B · Cash Root Cause Investigation & Cash Control Intelligence  
**Branch:** `feature/f02-1b-cash-root-cause`  
**Evidência:** `scripts/f02_1b_root_cause.json`  
**Gerado:** 2026-06-09T17:35:12

---

## Relatórios agentes

| Agente | Documento |
|--------|-----------|
| 1 Timeline | [CASH_TIMELINE_REPORT.md](./CASH_TIMELINE_REPORT.md) |
| 2 Forensics | [CASH_FORENSICS_ADVANCED_REPORT.md](./CASH_FORENSICS_ADVANCED_REPORT.md) |
| 3 Operador | [OPERATOR_ROOT_CAUSE_REPORT.md](./OPERATOR_ROOT_CAUSE_REPORT.md) |
| 4 PDV | [PDV_ROOT_CAUSE_REPORT.md](./PDV_ROOT_CAUSE_REPORT.md) |
| 5 Componentes | [CASH_COMPONENT_ANALYTICS_V2.md](./CASH_COMPONENT_ANALYTICS_V2.md) |
| 6 Turno | [SHIFT_RISK_REPORT.md](./SHIFT_RISK_REPORT.md) |
| 7 Heatmap | [CASH_HEATMAP_REPORT.md](./CASH_HEATMAP_REPORT.md) |
| 8 Recuperação | [FINANCIAL_RECOVERY_REPORT.md](./FINANCIAL_RECOVERY_REPORT.md) |
| 9 DW | [DW_CASH_OPERATIONS_V2.md](./DW_CASH_OPERATIONS_V2.md) |
| 10 QA | [CASH_ROOT_CAUSE_QA.md](./CASH_ROOT_CAUSE_QA.md) |

---

## Respostas obrigatórias (14)

| # | Pergunta | Resposta | Fórmula / Evidência | Período |
|---|----------|----------|---------------------|---------|
| 1 | Fluxo completo reconstruído? | **Sim** | Timeline por caixaCodigo | 7d |
| 2 | Existe sangria? | **Não detectada** | sangriaExplicita = 0 | 7d |
| 3 | Existe suprimento? | **Campos sim; 7d zerado; 30d/90d: 24/15 reg. (sem impacto diff)** | ap_suprimentoCaixa | 7d–90d |
| 4 | Existe fundo caixa? | **Campos sim; movimento 7d = 0** | fundoCaixaCredito | 7d |
| 5 | Operadores críticos? | **294273** (diff), **276288** (recorrência) | stats P95/P99 | 7d/90d |
| 6 | PDVs críticos? | **54193**, **15880** | |sum diff| ranking | 7d |
| 7 | Turnos críticos? | **1º turno** (1º TURNO) | ~95% impacto | 7d |
| 8 | Concentrado ou distribuído? | **CONCENTRADO** | dinheiro 100% | 7d |
| 9 | Padrão recorrente? | **Sim** | 276288 48×90d; 3 PDVs fixos | 90d |
| 10 | Risco operacional? | **Sim** | 21/21 turnos c/ diff | 7d |
| 11 | Causa raiz provável? | **Erro contagem dinheiro físico no fechamento — 1º turno — PDV 54193/15880** | diferenca_total ≈ dinheiroDiferenca (corr=1.0 no período 7d) | 7d |
| 12 | Potencial financeiro anual? | **R$ 844.327,73** obs · **R$ 62.457,12** rec 30% | perdaDiaria×365 | 90d |
| 13 | Fatos DW prontos? | **5 facts + 5 dims especificados** | ver DW_CASH_OPERATIONS_V2 | — |
| 14 | Pronto para F03? | **Sim** — causa raiz quantificada | QA + heatmap | — |

---

## Hipótese principal

Erro de contagem de dinheiro físico no fechamento — 1º turno — PDV 54193/15880

**Evidência:** dinheiro participação 100.0% do impacto absoluto; cartão diff=0  
**Amostra:** caixa top diff em CASH_TIMELINE_REPORT.md  
**Período:** ['2026-06-01', '2026-06-07']

---

## PARECER FINAL

```text
[PARECER FINAL: APROVADO PARA F03]
```

**Justificativa:** investigação read-only concluída; diferença 100% dinheiro; concentração operacional mapeada; projeção financeira calculada (base 90d); modelo DW v2 especificado. Janela 365d omitida por degradação. Próximo: F03 alertas + DDL.
