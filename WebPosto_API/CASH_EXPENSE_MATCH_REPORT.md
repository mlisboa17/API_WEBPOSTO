# CASH EXPENSE MATCH REPORT — F03.1-A

## Motor de reconciliação

Chaves: `(empresaCodigo, data, valor)` · parcial: `(empresa, valor)` + data ±2d

| Classificação | Qtd 7d | % 7d | Qtd 30d | Qtd 90d |
|---------------|--------|------|---------|---------|
| MATCH_EXATO | 3 | 15.8% | 54 | 129 |
| MATCH_PARCIAL | 1 | 5.3% | 34 | 79 |
| SEM_MATCH | 15 | 78.9% | 762 | 1952 |

## SEM_MATCH — explicação

Despesas agregadas no fechamento (`despesaApurado` = soma de múltiplas saídas PDV) **sem** espelho 1:1 por valor+data em DESPESAS_REDE. Não indicam quebra de caixa (F03.1: r=-0,0409).
