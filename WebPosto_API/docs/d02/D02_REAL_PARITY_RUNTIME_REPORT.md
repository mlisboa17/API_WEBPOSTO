# D02 — Real Parity Runtime Report

> **Reconstrução da Prestação e Pré-Conferência Interna** — paridade expectativa WebPosto/PDF × API. Não comprova banco/adquirente/comprovantes. [D02_CONCEPTUAL_CORRECTION.md](./D02_CONCEPTUAL_CORRECTION.md)

**Gerado:** 2026-07-04T22:49:09+00:00  
**Caso:** POSTO VIP (11495) · 2026-06-29 a 2026-07-05

## Fase 1 — Totais

| Métrica | Referência (PDF) | LOGOS (API) | Delta absoluto | Status |
|---|---:|---:|---:|---|
| Apresentado | 191,420.46 | 191,420.46 | 0.00 | MATCH |
| Sangria | 41,436.00 | 0.00 | 41,436.00 | SOURCE_GAP |
| Apurado | 217,005.34 | 225,011.70 | 8,006.36 | PARTIAL_MATCH |
| Diferença (Ap−Au) | -25,584.88 | -33,591.24 | 8,006.36 | CALCULATION_ERROR |

**Turnos caixa analisados:** 12  
**Linhas VFP:** 175 · **Cartão VFP:** 62

## Fase 2 — Matriz centavo a centavo (diferença por natureza)

| NATUREZA | VALOR REFERENCIA | VALOR LOGOS | DELTA ABS | DELTA % | FONTE LOGOS | STATUS |
| --- | --- | --- | --- | --- | --- | --- |
| DINHEIRO | -9943.52 | -8556.86 | 1386.66 | 13.95% | CAIXA_APRESENTADO | CALCULATION_ERROR |
| NOTAS | -4.61 | -4.61 | 0.00 | 0.00% | CAIXA_APRESENTADO | MATCH |
| CHEQUE À VISTA | — | — | — | — | CAIXA_APRESENTADO | DATA_MISSING |
| CHEQUE PRÉ | — | — | — | — | CAIXA_APRESENTADO | DATA_MISSING |
| CARTÃO | -8235.12 | -11667.18 | 3432.06 | 41.68% | CAIXA_APRESENTADO | CALCULATION_ERROR |
| CARTA FRETE | — | — | — | — | CAIXA_APRESENTADO | DATA_MISSING |
| VALE CLIENTE | — | — | — | — | CAIXA_APRESENTADO | DATA_MISSING |
| DESPESA | -236.00 | -815.77 | 579.77 | 245.67% | CAIXA_APRESENTADO | CALCULATION_ERROR |
| EMPRÉSTIMO | — | — | — | — | CAIXA_APRESENTADO | DATA_MISSING |
| PRÉ-PAGO | — | — | — | — | CAIXA_APRESENTADO | DATA_MISSING |
| VALE FUNCIONÁRIO | -2733.41 | -5461.70 | 2728.29 | 99.81% | CAIXA_APRESENTADO | CALCULATION_ERROR |
| TRANSFERÊNCIA CRÉDITO | -4432.22 | -7085.12 | 2652.90 | 59.85% | CAIXA_APRESENTADO | CALCULATION_ERROR |
| TRANSFERÊNCIA DÉBITO | — | — | — | — | CAIXA_APRESENTADO | DATA_MISSING |
| CHEQUE PAGAR | — | — | — | — | CAIXA_APRESENTADO | DATA_MISSING |
| FUNDO DE CAIXA DÉBITO | — | — | — | — | CAIXA_APRESENTADO | DATA_MISSING |

## Fase 3 — Cartões

| Pergunta | Resposta |
|---|---|
| Valor bruto cartões (VFP) | R$ 2,582.40 |
| TEF | R$ 0.00 |
| POS_MANUAL | R$ 2,582.40 |
| Bandeiras identificadas | UNKNOWN |
| Modalidades | CARD |
| Adquirentes comprovadas | ADM_106911, ADM_106915, ADM_94760, ADM_94761, ADM_94762, ADM_94763, ADM_98784 |
| Não classificado (UNKNOWN adm) | 0 linhas |
| Dif. cartão LOGOS vs PDF | LOGOS -11667.18 · ref -8235.12 |

POS **não** é natureza financeira — apenas `captureOrigin`.

## Fase 4 — Dinheiro (fórmula observada)

```
DIFERENÇA_DINHEIRO = APRESENTADO − APURADO
                   = 42,900.90 − 51,457.76
                   = -8,556.86
```

Sangria período (DESPESAS semântico): R$ 0.00  
Referência sangria PDF: R$ 41,436.00

## Fase 5 — Pré-conferência

| Métrica | Valor |
|---|---:|
| Total analisado | 62 |
| AUTO_MATCHED | 42 |
| NEEDS_REVIEW | 3 |
| DIVERGENT | 16 |
| JUSTIFIED | 1 |
| CONFIRMED | 0 |
| Valor divergente (R$) | 34,158.66 |
| % auto conferido (itens) | 67.74% |
| % financeiro pendente | 33.99% |

## Fase 6 — Audit Signals (39 sinais)

Acusação de fraude: **NÃO**

| signalType | severity | entityType | entityId | amount | occurrenceCount | explanation |
| --- | --- | --- | --- | --- | --- | --- |
| AuditSignalType.UNJUSTIFIED_DIVERGENCE | AuditSeverity.MEDIUM | RECONCILIATION_ITEM | 11495:4362627:DINHEIRO | 7.04 | 1 | DIVERGÊNCIA RECORRENTE — revisão recomendada sem justificativa registrada |
| AuditSignalType.UNJUSTIFIED_DIVERGENCE | AuditSeverity.MEDIUM | RECONCILIATION_ITEM | 11495:4362651:DINHEIRO | 1.76 | 1 | DIVERGÊNCIA RECORRENTE — revisão recomendada sem justificativa registrada |
| AuditSignalType.UNJUSTIFIED_DIVERGENCE | AuditSeverity.HIGH | RECONCILIATION_ITEM | 11495:4363575:DINHEIRO | 300.62 | 1 | DIVERGÊNCIA RECORRENTE — revisão recomendada sem justificativa registrada |
| AuditSignalType.THRESHOLD_EXCEEDED | AuditSeverity.HIGH | RECONCILIATION_ITEM | 11495:4363575:DINHEIRO | 300.62 | 1 | DIVERGÊNCIA acima do limite configurável (R$ 100.00) |
| AuditSignalType.UNJUSTIFIED_DIVERGENCE | AuditSeverity.MEDIUM | RECONCILIATION_ITEM | 11495:4364583:DINHEIRO | 82.48 | 1 | DIVERGÊNCIA RECORRENTE — revisão recomendada sem justificativa registrada |
| AuditSignalType.UNJUSTIFIED_DIVERGENCE | AuditSeverity.HIGH | RECONCILIATION_ITEM | 11495:4364591:DINHEIRO | 150.14 | 1 | DIVERGÊNCIA RECORRENTE — revisão recomendada sem justificativa registrada |
| AuditSignalType.THRESHOLD_EXCEEDED | AuditSeverity.HIGH | RECONCILIATION_ITEM | 11495:4364591:DINHEIRO | 150.14 | 1 | DIVERGÊNCIA acima do limite configurável (R$ 100.00) |
| AuditSignalType.UNJUSTIFIED_DIVERGENCE | AuditSeverity.MEDIUM | RECONCILIATION_ITEM | 11495:4365567:DINHEIRO | 56.39 | 1 | DIVERGÊNCIA RECORRENTE — revisão recomendada sem justificativa registrada |
| AuditSignalType.UNJUSTIFIED_DIVERGENCE | AuditSeverity.HIGH | RECONCILIATION_ITEM | 11495:4365607:DINHEIRO | 111.65 | 1 | DIVERGÊNCIA RECORRENTE — revisão recomendada sem justificativa registrada |
| AuditSignalType.THRESHOLD_EXCEEDED | AuditSeverity.HIGH | RECONCILIATION_ITEM | 11495:4365607:DINHEIRO | 111.65 | 1 | DIVERGÊNCIA acima do limite configurável (R$ 100.00) |
| AuditSignalType.UNJUSTIFIED_DIVERGENCE | AuditSeverity.HIGH | RECONCILIATION_ITEM | 11495:4366513:DINHEIRO | 518.29 | 1 | DIVERGÊNCIA RECORRENTE — revisão recomendada sem justificativa registrada |
| AuditSignalType.THRESHOLD_EXCEEDED | AuditSeverity.HIGH | RECONCILIATION_ITEM | 11495:4366513:DINHEIRO | 518.29 | 1 | DIVERGÊNCIA acima do limite configurável (R$ 100.00) |
| AuditSignalType.UNJUSTIFIED_DIVERGENCE | AuditSeverity.HIGH | RECONCILIATION_ITEM | 11495:4366545:DINHEIRO | 312.68 | 1 | DIVERGÊNCIA RECORRENTE — revisão recomendada sem justificativa registrada |
| AuditSignalType.THRESHOLD_EXCEEDED | AuditSeverity.HIGH | RECONCILIATION_ITEM | 11495:4366545:DINHEIRO | 312.68 | 1 | DIVERGÊNCIA acima do limite configurável (R$ 100.00) |
| AuditSignalType.UNJUSTIFIED_DIVERGENCE | AuditSeverity.HIGH | RECONCILIATION_ITEM | 11495:4367494:DINHEIRO | 934.94 | 1 | DIVERGÊNCIA RECORRENTE — revisão recomendada sem justificativa registrada |
| AuditSignalType.THRESHOLD_EXCEEDED | AuditSeverity.HIGH | RECONCILIATION_ITEM | 11495:4367494:DINHEIRO | 934.94 | 1 | DIVERGÊNCIA acima do limite configurável (R$ 100.00) |
| AuditSignalType.UNJUSTIFIED_DIVERGENCE | AuditSeverity.MEDIUM | RECONCILIATION_ITEM | 11495:4367494:NOTAS | 4.61 | 1 | DIVERGÊNCIA RECORRENTE — revisão recomendada sem justificativa registrada |
| AuditSignalType.UNJUSTIFIED_DIVERGENCE | AuditSeverity.HIGH | RECONCILIATION_ITEM | 11495:4367494:CARTAO | 975.93 | 1 | DIVERGÊNCIA RECORRENTE — revisão recomendada sem justificativa registrada |
| AuditSignalType.THRESHOLD_EXCEEDED | AuditSeverity.HIGH | RECONCILIATION_ITEM | 11495:4367494:CARTAO | 975.93 | 1 | DIVERGÊNCIA acima do limite configurável (R$ 100.00) |
| AuditSignalType.UNJUSTIFIED_DIVERGENCE | AuditSeverity.HIGH | RECONCILIATION_ITEM | 11495:4367494:DESPESA | 186.00 | 1 | DIVERGÊNCIA RECORRENTE — revisão recomendada sem justificativa registrada |
| AuditSignalType.THRESHOLD_EXCEEDED | AuditSeverity.HIGH | RECONCILIATION_ITEM | 11495:4367494:DESPESA | 186.00 | 1 | DIVERGÊNCIA acima do limite configurável (R$ 100.00) |
| AuditSignalType.UNJUSTIFIED_DIVERGENCE | AuditSeverity.HIGH | RECONCILIATION_ITEM | 11495:4367494:TRANSFERENCIA_CREDITO | 1,146.60 | 1 | DIVERGÊNCIA RECORRENTE — revisão recomendada sem justificativa registrada |
| AuditSignalType.THRESHOLD_EXCEEDED | AuditSeverity.HIGH | RECONCILIATION_ITEM | 11495:4367494:TRANSFERENCIA_CREDITO | 1,146.60 | 1 | DIVERGÊNCIA acima do limite configurável (R$ 100.00) |
| AuditSignalType.UNJUSTIFIED_DIVERGENCE | AuditSeverity.HIGH | RECONCILIATION_ITEM | 11495:4367565:DINHEIRO | 6,648.29 | 1 | DIVERGÊNCIA RECORRENTE — revisão recomendada sem justificativa registrada |
| AuditSignalType.THRESHOLD_EXCEEDED | AuditSeverity.HIGH | RECONCILIATION_ITEM | 11495:4367565:DINHEIRO | 6,648.29 | 1 | DIVERGÊNCIA acima do limite configurável (R$ 100.00) |
| AuditSignalType.UNJUSTIFIED_DIVERGENCE | AuditSeverity.HIGH | RECONCILIATION_ITEM | 11495:4367565:CARTAO | 10,691.25 | 1 | DIVERGÊNCIA RECORRENTE — revisão recomendada sem justificativa registrada |
| AuditSignalType.THRESHOLD_EXCEEDED | AuditSeverity.HIGH | RECONCILIATION_ITEM | 11495:4367565:CARTAO | 10,691.25 | 1 | DIVERGÊNCIA acima do limite configurável (R$ 100.00) |
| AuditSignalType.UNJUSTIFIED_DIVERGENCE | AuditSeverity.HIGH | RECONCILIATION_ITEM | 11495:4367565:DESPESA | 629.77 | 1 | DIVERGÊNCIA RECORRENTE — revisão recomendada sem justificativa registrada |
| AuditSignalType.THRESHOLD_EXCEEDED | AuditSeverity.HIGH | RECONCILIATION_ITEM | 11495:4367565:DESPESA | 629.77 | 1 | DIVERGÊNCIA acima do limite configurável (R$ 100.00) |
| AuditSignalType.UNJUSTIFIED_DIVERGENCE | AuditSeverity.HIGH | RECONCILIATION_ITEM | 11495:4367565:VALE_FUNCIONARIO | 5,461.70 | 1 | DIVERGÊNCIA RECORRENTE — revisão recomendada sem justificativa registrada |
## Respostas objetivas (18)

1. **Apresentado:** ref 191,420.46 · LOGOS 191,420.46
2. **Sangria:** ref 41,436.00 · LOGOS 0.00
3. **Apurado:** ref 217,005.34 · LOGOS 225,011.70
4. **Diferença:** ref -25,584.88 · LOGOS -33,591.24
5. **% financeiro reconstruído:** 100.00%
6. **% centavo MATCH (naturezas ref):** 0.02%
7. **PARTIAL_MATCH:** nenhuma
8. **SOURCE_GAP / gaps:** DINHEIRO, CHEQUE À VISTA, CHEQUE PRÉ, CARTÃO, CARTA FRETE, VALE CLIENTE, DESPESA, EMPRÉSTIMO, PRÉ-PAGO, VALE FUNCIONÁRIO, TRANSFERÊNCIA CRÉDITO, TRANSFERÊNCIA DÉBITO, CHEQUE PAGAR, FUNDO DE CAIXA DÉBITO
9. **Erros classificação:** ver STATUS CLASSIFICATION_ERROR na matriz
10. **Erros cálculo:** ver STATUS CALCULATION_ERROR na matriz
11. **Valor auto conferido:** R$ 148,519.56
12. **Valor revisão humana:** R$ 76,492.14
13. **Divergências reais (itens DIVERGENT):** 16
14. **Audit signals:** 39
15. **Cartões natureza/origem separados:** SIM
16. **POS só origem:** SIM
17. **Regressão Diretoria:** não testado neste script (ver Fase 7 runtime)
18. **Tela runtime:** ver Fase 7 abaixo

## Fase 7 — Runtime UI

- [x] backend_health: 200
- [x] summary_http: 200
- [x] summary_apresentado: 191420.46
- [x] summary_nature_cards: 6
- [x] summary_items: 62
- [x] no_zero_pollution: zerados=0
- [x] divergencias_priorizadas: maior_dif=11667.18
- [x] exceptions_http: 20
- [x] audit_signals_http: 40
- [x] sem_acusacao_fraude: 
- [x] justify_http: 11495:4363558:DINHEIRO
- [x] justificativa_historico: 11495:4363558:DINHEIRO
- [x] diretoria_http: 200
- [x] frontend_shell: len=6228

**Checks OK:** 14/14 · Backend :8040 · Frontend `/app/financial`

## Veredicto

[PARECER FINAL: APROVADO COM GAPS DOCUMENTADOS] — **consistência interna / fluxo runtime**; não Conferência Financeira final.

**Pergunta financeiro:** "PARCIAL" — auto 42/62 itens; divergente R$ 34,158.66; pendente R$ 76,492.14.
