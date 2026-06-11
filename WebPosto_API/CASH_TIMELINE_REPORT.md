# CASH TIMELINE REPORT — F02.1-B

**Sprint:** F02.1-B · Cash Root Cause Investigation  
**Período primário:** 2026-06-01 → 2026-06-07  
**Evidência:** `scripts/f02_1b_root_cause.json`

## Fluxo reconstruído

Abertura → Suprimento → Movimentação → Despesas → Vale → Empréstimo → Transferências → Fechamento → Diferença

**Fórmula:** `diferenca_total = Σ componentesDiferenca` (validado QA: dinheiro ≈ total 7d)

## Amostras top |diferença| (7d)

### Caixa `4336819` · PDV 15880 · Op 158924

| Etapa | Valor / Info |
|-------|--------------|
| Abertura | 2026-06-02T00:01:33.000-03:00 |
| Suprimento | R$ 0,00 |
| Movimentação apurado | R$ 19.157,73 |
| Despesas apurado | R$ 359,57 |
| Vale apurado | R$ 1.863,00 |
| Empréstimo apurado | R$ 0,00 |
| Transferência apurado | R$ 0,00 |
| Fechamento | 2026-06-03T00:00:49.000-03:00 |
| Diferença total | R$ -272,07 |
| Diferença dinheiro | R$ -272,07 |
| Transferências vinculadas | 0 reg · soma R$ 0,00 |

### Caixa `4340665` · PDV 15880 · Op 299151

| Etapa | Valor / Info |
|-------|--------------|
| Abertura | 2026-06-06T00:00:03.000-03:00 |
| Suprimento | R$ 0,00 |
| Movimentação apurado | R$ 30.631,61 |
| Despesas apurado | R$ 190,00 |
| Vale apurado | R$ 289,00 |
| Empréstimo apurado | R$ 0,00 |
| Transferência apurado | R$ 0,00 |
| Fechamento | 2026-06-08T07:26:53.000-03:00 |
| Diferença total | R$ -215,77 |
| Diferença dinheiro | R$ -215,77 |
| Transferências vinculadas | 0 reg · soma R$ 0,00 |

### Caixa `4337788` · PDV 15880 · Op 158924

| Etapa | Valor / Info |
|-------|--------------|
| Abertura | 2026-06-03T00:01:02.000-03:00 |
| Suprimento | R$ 0,00 |
| Movimentação apurado | R$ 20.946,95 |
| Despesas apurado | R$ 482,38 |
| Vale apurado | R$ 1.367,00 |
| Empréstimo apurado | R$ 0,00 |
| Transferência apurado | R$ 0,00 |
| Fechamento | 2026-06-04T00:13:11.000-03:00 |
| Diferença total | R$ 208,96 |
| Diferença dinheiro | R$ 208,96 |
| Transferências vinculadas | 0 reg · soma R$ 0,00 |

### Caixa `4338777` · PDV 54193 · Op 294273

| Etapa | Valor / Info |
|-------|--------------|
| Abertura | 2026-06-04T00:04:10.000-03:00 |
| Suprimento | R$ 0,00 |
| Movimentação apurado | R$ 37.313,15 |
| Despesas apurado | R$ 548,65 |
| Vale apurado | R$ 5.607,16 |
| Empréstimo apurado | R$ 0,00 |
| Transferência apurado | R$ 6.601,42 |
| Fechamento | 2026-06-05T00:00:20.000-03:00 |
| Diferença total | R$ -194,36 |
| Diferença dinheiro | R$ -194,36 |
| Transferências vinculadas | 0 reg · soma R$ 0,00 |

### Caixa `4339655` · PDV 54193 · Op 299371

| Etapa | Valor / Info |
|-------|--------------|
| Abertura | 2026-06-05T00:00:29.000-03:00 |
| Suprimento | R$ 0,00 |
| Movimentação apurado | R$ 34.167,70 |
| Despesas apurado | R$ 486,00 |
| Vale apurado | R$ 260,00 |
| Empréstimo apurado | R$ 0,00 |
| Transferência apurado | R$ 9.239,14 |
| Fechamento | 2026-06-06T00:02:27.000-03:00 |
| Diferença total | R$ -116,80 |
| Diferença dinheiro | R$ -116,80 |
| Transferências vinculadas | 0 reg · soma R$ 0,00 |


## Janelas analisadas

| Janela | Fechamentos merge |
|--------|-------------------|
| 7d | 21 |
| 30d | 1116 |
| 90d | 3000 |
| 365d | omitida — Omitida via --skip-365 |

**Conclusão:** fluxo operacional **reconstruído** por `caixaCodigo` via CAIXA + CAIXA_APRESENTADO + TRANSFERENCIA_BANCARIA.
