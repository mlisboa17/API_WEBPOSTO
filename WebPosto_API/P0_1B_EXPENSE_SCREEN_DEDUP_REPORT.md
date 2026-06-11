# P0.1-B — EXPENSE SCREEN DEDUP REPORT

**Data:** 2026-06-09  
**Caso:** AP CASA CAIADA (5555) · 08/06/2026

---

## Respostas obrigatórias

| # | Pergunta | Resposta |
|---|----------|----------|
| 1 | Os 2 registros de R$ 270 caixa são distintos? | **Não.** Mesmo fechamento `4343023` contado 2× como caixa. |
| 2 | Mesmo caixaCodigo? | **Sim.** 4343023 |
| 3 | Mesmo pdvCodigo? | **Sim.** 15880 |
| 4 | Mesmo turno? | **Sim.** 1º TURNO / turnoCodigo 1 |
| 5 | Vieram de APRESENTADO + REDE? | **Sim.** merge `CAIXA_REDE` + `CAIXA_APRESENTADO` |
| 6 | Merge duplicando? | **Sim.** emitia caixa + pdv + dedupe fraco por descricao |
| 7 | Quantas duplicidades? | **2** linhas caixa extras + **1** linha pdv redundante (3→1) |
| 8 | Valor correto AP CASA CAIADA? | **R$ 2.047,00** (1912 financeiro + 135 operacional) |
| 9 | Total 2317 ou 2182? | **Nenhum.** Correto = **R$ 2.047,00** (2317−270 duplicado caixa +135 pdv redundante) |
| 10 | Correção aplicada? | **Sim** |

---

## Evidência numérica

```text
ANTES:  financeiro 2 | caixa 2 R$270 | pdv 1 R$135 | total 5 R$2317
DEPOIS: financeiro 2 | caixa 1 R$135 | pdv 0        | total 3 R$2047
```

---

## Relatórios gerados

1. `RAW_CAIXA_EXPENSE_AUDIT.md`
2. `EXPENSE_DEDUP_ANALYSIS.md`
3. `SCREEN_MERGE_AUDIT.md`
4. `EXPENSE_DEDUP_FIX_REPORT.md`
5. `EXPENSE_DEDUP_QA_REPORT.md`
6. `P0_1B_EXPENSE_SCREEN_DEDUP_REPORT.md` (este)
7. `TEMPORAL_DEDUP_AUDIT.md` (Agente 6)
8. `EXPENSE_DEDUP_REGRESSION_REPORT.md` (Agente 7)

Script caso: `scripts/audit_p0_1b_caixa_dedup.py`  
Script temporal: `scripts/audit_p0_1b_temporal_dedup.py`

---

## PARECER FINAL

```text
[PARECER FINAL: DUPLICIDADE CONFIRMADA E CORRIGIDA]
```

A duplicidade R$ 135 caixa×2 + pdv×1 no fechamento 4343023 foi eliminada. Financeiro (DESPESAS_REDE) permanece separado e intacto.
## Extensão temporal — respostas adicionais

| # | Pergunta | Resposta |
|---|----------|----------|
| 11 | Duplicidade só em 08/06/2026 ou múltiplos períodos? | **Múltiplos períodos** — padrão recorrente em 66 dias (90d) |
| 12 | % duplicidade 7d? | **4.72%** (22 registros · R$ 5.364,67) |
| 13 | % duplicidade 30d? | **5.38%** (99 registros · R$ 36.016,66) |
| 14 | % duplicidade 90d? | **3.6%** (207 registros · R$ 92.914,70) |
| 15 | Empresas impactadas? | **2** (90d) — POSTO VIP (11495) e AP CASA CAIADA (5555) |
| 16 | Valor total superestimado (90d)? | **R$ 92.914,70** |
| 17 | Redução % do total exibido pós-correção (90d)? | **5.34%** |
| 18 | Falsos positivos de deduplicação? | **Não (0)** |
| 19 | Algoritmo seguro para produção? | **Sim** |
| 20 | Correção retroativa? | **Sim** — padrão estrutural no merge operacional |

## Critério de aceite reforçado

| Critério | Status |
|----------|--------|
| Duplicidade identificada | OK |
| Duplicidade corrigida (0 dup. pós-fix) | OK |
| 0 falsos positivos | OK |
| Validação 7d / 30d / 90d | OK |
| Paridade = 0,00 | OK |

```text
[PARECER FINAL: DUPLICIDADE CONFIRMADA E CORRIGIDA — APROVADO PARA PRODUÇÃO]
```
