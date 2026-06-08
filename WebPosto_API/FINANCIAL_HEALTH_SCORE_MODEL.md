# FINANCIAL HEALTH SCORE MODEL — Proposta F01.2+

**Escala:** 0–100 por filial | **Regra:** scores independentes — **nunca somar** DESPESA+CP+BANCO+CAIXA em um total financeiro.

## Componentes sugeridos

| Indicador | Peso | Cálculo (0–100) |
|---|---:|---|
| Despesas vs média rede | 15% | Inverso do desvio % vs média filial |
| CP vencido / CP aberto | 20% | 100 − (vencido÷aberto×100) |
| CR vencido / CR pendente | 15% | 100 − (vencido÷pendente×100) |
| Diferença caixa / turnos | 20% | 100 − min(100, Σ|dif|÷turnos normalizado) |
| Tarifas bancárias / créditos | 10% | 100 − min(100, tarifas÷créditos×1000) |
| Vale funcionário / despesa caixa | 10% | Penalidade se ratio > limiar |
| Classificação LOGOS OUTROS % | 10% | 100 − pct_OUTROS |

## Fórmula

```text
score = Σ (peso_i × subscore_i)
```

Subscores normalizados por filial, período rolling 30d.

## Indicadores que **não** entram

- Total financeiro único
- Soma CP + CR + Banco + Caixa
- DRE consolidada automática

## Próximo passo

Implementar em **F01.3 BI Financeiro** após F01.2 Fluxo de Caixa (somente leitura, sem produção nesta sprint).
