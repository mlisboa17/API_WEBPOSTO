# SEMANTIC CLASSIFICATION ENGINE — F03.2 · Agente 1

## Taxonomia oficial

| Natureza | Significado |
|----------|-------------|
| DESPESA_FINANCEIRA | Impacta resultado financeiro |
| DESPESA_OPERACIONAL | Gasto real da operação |
| MOVIMENTACAO_CAIXA | **Não é despesa** — movimentação operacional |
| ADIANTAMENTO | Eventos com funcionários |
| AJUSTE_OPERACIONAL | Correções de fechamento |

## Princípio de negócio

```text
DESPESA ≠ MOVIMENTAÇÃO DE CAIXA
DESPESA ≠ ADIANTAMENTO
DESPESA ≠ AJUSTE OPERACIONAL
```

## Saída por registro

```json
{
  "expenseNature": "DESPESA_FINANCEIRA",
  "expenseSubNature": "BOBINA_TERMICA",
  "semanticConfidence": 90
}
```

## Cobertura (90d)

- Registros classificados: **5537** / **5537**
- Taxa: **100.0%**
- Confiança média: **90.8**
