# A04_READINESS_REPORT — A03.7

## O DW deve começar agora?

**Não imediatamente.** Consolidar F01 (Centro Financeiro) antes do DW físico.

## O modelo financeiro já está maduro?

**Sim conceitualmente** (LOGOS_FINANCIAL_MODEL_1.0 + esta sprint). **Parcial operacionalmente** (recebíveis stub, tesouraria/caixa não integrados).

## O que falta?

1. Integrar TITULO_RECEBER no LOGOS
2. Módulo Tesouraria (MOVIMENTO_CONTA)
3. Token NOTA_ENTRADA / COMPRA_REDE
4. Snapshot/cache financeiro corporativo
5. Classificador despesa em produção (rules engine)

## Qual o risco?

**Médio-baixo (30/100)** — risco principal: somar despesas + títulos por engano.

## Prioridade

**F01 Centro Financeiro** → depois DW com facts já validados.
