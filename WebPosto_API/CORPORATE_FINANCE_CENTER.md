# CORPORATE FINANCE CENTER — Especificação A03.7

**Gerado:** 2026-06-08T15:00:25

## Visão

Módulo **Centro Financeiro** = camada de leitura unificada da holding, **sem somar fatos distintos**.

## Fontes (módulos independentes)

| Módulo LOGOS | Fonte WebPosto | Endpoint LOGOS | Grain |
|---|---|---|---|
| Despesa Gerencial | DESPESAS_FINANCEIRO_REDE | /v1/financial/expenses | plano+data+valor |
| Contas a Pagar | TITULO_PAGAR | /v1/financial/accounts-payable | tituloPagarCodigo |
| Contas a Receber | TITULO_RECEBER | (futuro) | tituloReceberCodigo |
| Tesouraria | MOVIMENTO_CONTA | (futuro F02) | movimentoContaCodigo |

## Painéis previstos

### Resultado Financeiro
- **Receitas:** TITULO_RECEBER + vendas (módulo comercial — fora do escopo caixa)
- **Despesas:** fact_despesa_gerencial ONLY
- **Resultado:** receitas − despesas gerenciais (NÃO incluir títulos em aberto)

### Fluxo de Caixa
- **Previsto:** TITULO_PAGAR (vencimentos) + TITULO_RECEBER (recebíveis)
- **Realizado:** MOVIMENTO_CONTA (crédito/débito)

### Contas a Pagar
- Aberto: 63 | Pago: 7 | Valor aberto est.: R$ 311176.28

### Contas a Receber
- Registros API: 11 | Valor: R$ 176.31 | Vencidos est.: 11

## Regra crítica

```
DESPESA GERENCIAL ≠ TÍTULO A PAGAR ≠ MOVIMENTO BANCÁRIO ≠ CAIXA ≠ TÍTULO RECEBER
```

Correlacionar no futuro via chaves — nunca somar automaticamente.

## Evidência API (01–07/06/2026)

| Fonte | Registros | Latência |
|---|---:|---:|
| DESPESAS_REDE | 432 | 2016ms |
| TITULO_PAGAR | 70 | 170ms |
| TITULO_RECEBER | 11 | 152ms |
| MOVIMENTO_CONTA | 200* | 486ms |

\* limite de página — paginar `ultimoCodigo`
