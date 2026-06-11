# CASH FORENSICS ADVANCED REPORT — F02.1-B

**Período:** 7d · **Evidência:** `scripts/f02_1b_root_cause.json`

## Detecção forense

| Indicador | Valor | Evidência |
|-----------|-------|-----------|
| Sangria explícita | **0** | regex sangria em MOVIMENTO/TRANSF |
| Suprimento ≠ 0 | **0** | `suprimentoCaixa` / `ap_suprimentoCaixa` |
| Fundo caixa ≠ 0 | **0** | `fundoCaixaCredito`, `fundoCxDebApurado` |

## Campos forenses mapeados

| Campo | Frequência |
|-------|------------|
| `ap_valeClienteApresentado` | 21 ocorrências |
| `ap_valeClienteApurado` | 21 ocorrências |
| `ap_valeClienteDiferenca` | 21 ocorrências |
| `ap_emprestimoApresentado` | 21 ocorrências |
| `ap_emprestimoApurado` | 21 ocorrências |
| `ap_emprestimoDiferenca` | 21 ocorrências |
| `ap_valeFunApresentado` | 21 ocorrências |
| `ap_valeFunApurado` | 21 ocorrências |
| `ap_valeFunDiferenca` | 21 ocorrências |
| `ap_fundoCxDebApresentado` | 21 ocorrências |
| `ap_fundoCxDebApurado` | 21 ocorrências |
| `ap_fundoCxDebDiferenca` | 21 ocorrências |
| `ap_valeCliente` | 21 ocorrências |
| `ap_suprimentoCaixa` | 21 ocorrências |
| `ap_chequeTroco` | 21 ocorrências |

## Evidências não-zero (amostra)

| Fonte | Campo/Texto | Valor | Caixa |
|-------|-------------|-------|-------|
| CAIXA_APRESENTADO | ap_valeFunApresentado | 1045.09 | 4335818 |
| CAIXA_APRESENTADO | ap_valeFunApurado | 1045.09 | 4335818 |
| CAIXA_APRESENTADO | ap_suprimentoCaixa | 0 | 4335818 |
| CAIXA_APRESENTADO | ap_suprimentoCaixa | 0 | 4335835 |
| CAIXA_APRESENTADO | ap_valeFunApresentado | 3476.0 | 4335874 |
| CAIXA_APRESENTADO | ap_valeFunApurado | 3476.0 | 4335874 |
| CAIXA_APRESENTADO | ap_suprimentoCaixa | 0 | 4335874 |
| CAIXA_APRESENTADO | ap_suprimentoCaixa | 0 | 4336075 |
| CAIXA_APRESENTADO | ap_suprimentoCaixa | 0 | 4336768 |
| CAIXA_APRESENTADO | ap_suprimentoCaixa | 0 | 4336785 |

## Respostas

| Pergunta | Resposta |
|----------|----------|
| Existe sangria? | **Não detectada** (7d) |
| Existe suprimento? | **Campos existem; zerados no período** |
| Existe fundo caixa? | **Campos existem; sem movimento 7d** |
| Troco inicial / fundo troco | Campos presentes em schema; **sem impacto na diferença 7d** |
