# FINANCIAL LINEAGE REPORT — F03.1-A

## Fluxo comprovado (matched)

```text
CAIXA_APRESENTADO.despesaApurado
    ↓ MATCH_EXATO/PARCIAL
DESPESAS_REDE (descricaoDocumento, valor, data)
    ↓
planoContaGerencialCodigo / planoContaGerencialDescricao
    ↓ (parcial)
TITULO_PAGAR (valor + fornecedor quando encontrado)
```

## Cadeias reconstruídas (7d)

| Caixa | Despesa | Descrição Rede | Plano Conta | Título |
|-------|---------|----------------|-------------|--------|
| 4335835 | R$ 130,00 | pag ref apoio loja joao vitor | — | — |
| 4335874 | R$ 59,00 | REF A COMPRA DE UM CADEADO | — | — |
| 4338701 | R$ 96,00 | ref a sanduiche natural | — | 3080060 |
| 4339720 | R$ 30,00 | REF GASOLINA MOTO HENRIQUE | — | — |

**Centro de custo:** campo frequentemente **null** em DESPESAS_REDE (CENTRO_CUSTO_REDE HTTP 401).
