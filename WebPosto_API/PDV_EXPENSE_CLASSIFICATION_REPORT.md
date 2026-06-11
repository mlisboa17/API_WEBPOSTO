# PDV EXPENSE CLASSIFICATION REPORT — F03.1

**Total classificados (7d):** 21

---

## Distribuição por categoria

| categoriaPdvDespesa | Fechamentos |
|---------------------|-------------|
| DESPESA_CAIXA | 19 |
| OUTROS | 1 |
| VALE_FUNCIONARIO | 1 |

## Schema de saída

```json
{
  "categoriaPdvDespesa": "DESPESA_CAIXA|VALE_FUNCIONARIO|...",
  "confidenceScore": 0.70-0.95,
  "classificationSource": "campo_despesaApurado|..."
}
```

## Regras

| Campo origem | Categoria | Confidence |
|--------------|-----------|------------|
| despesaApurado | DESPESA_CAIXA | 0.95 |
| valeFunApurado | VALE_FUNCIONARIO | 0.92 |
| emprestimoApurado | EMPRESTIMO | 0.90 |
| suprimentoCaixa | SUPRIMENTO | 0.88 |
| fundoCaixa* | FUNDO_CAIXA | 0.85 |
| transfBancApurado | OUTROS | 0.70 |

**Nota:** `despesaDiferenca` permanece componente de fechamento — **não** confundir com despesa financeira de rede.
