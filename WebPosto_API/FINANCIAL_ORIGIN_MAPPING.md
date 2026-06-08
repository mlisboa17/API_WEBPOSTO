# FINANCIAL_ORIGIN_MAPPING — Sprint P0.1

**Gerado:** 2026-06-08T13:13:31
**Período:** 2026-06-01 .. 2026-06-07

## Resumo executivo

O WebPosto expõe **múltiplas entidades financeiras** em endpoints distintos.
A **visão consolidada de despesas** (tela financeiro) vem principalmente de `CONSULTAR_DESPESAS_FINANCEIRO_REDE`,
que agrega lançamentos de plano gerencial — **incluindo compras, salários e despesas operacionais** na mesma tabela.

## Matriz origem (formato solicitado)

| Tipo Financeiro | Endpoint Origem | Valor (período) | Empresa | Aparece no WebPosto? |
|---|---|---:|---|---|
| Energia / água | DESPESAS_FINANCEIRO_REDE | R$ 186,00 (19 reg) | Rede 10 filiais | Sim — tela despesas |
| Salário / folha | DESPESAS_FINANCEIRO_REDE | R$ 13.711,00 (27 reg) | Rede | Sim |
| Compra mercadoria | DESPESAS_FINANCEIRO_REDE | R$ 2.116,75 (15 reg) | Rede | Sim (descrição "REF COMPRA...") |
| Compra combustível | DESPESAS_FINANCEIRO_REDE | R$ 399,00 (1 reg) | Rede | Sim |
| Sangria / retirada | DESPESAS_FINANCEIRO_REDE | R$ 200,00 (1 reg) | Rede | Sim |
| Despesa operacional | DESPESAS_FINANCEIRO_REDE | R$ 119.117,95 (363 reg) | Rede | Sim |
| Tarifa bancária | MOVIMENTO_CONTA | R$ 10.450,52 (400 reg) | 8 filiais alvo | Parcial — extrato banco |
| Título a pagar | TITULO_PAGAR | R$ 363.452,16 (66 reg) | 5555, 11495 | Sim — contas a pagar |
| Quebra caixa | CAIXA | `diferenca` por turno | 5555, 11495 | Sim — fechamento turno |
| Despesa caixa agregada | CAIXA_APRESENTADO | `despesaApurado` | 5555, 11495 | Sim — conciliação |
| Compra NF detalhada | NOTA_ENTRADA / COMPRA_REDE | — | — | **Não** (401 token) |
| Vale funcionário | VALE_FUNCIONARIO_REDE | — | — | **Não** (401 token) |
| Log exclusões | FINANCEIRO_EXCLUSAO | R$ 40M+ (histórico*) | 5555, 11495 | Diagnóstico apenas |

## Matriz origem (detalhada)

| Tipo Financeiro | Endpoint | Registros | Valor | WebPosto UI | LOGOS |
|---|---|---:|---:|---|---|
| Despesa operacional genérica | `DESPESAS_FINANCEIRO_REDE` | 363 | 119117.95 | Sim — tela financeiro/des | Sim — /v1/financial/ |
| Salário / folha | `DESPESAS_FINANCEIRO_REDE` | 27 | 13711.00 | Sim — tela financeiro/des | Sim — /v1/financial/ |
| Energia / utilities | `DESPESAS_FINANCEIRO_REDE` | 19 | 186.00 | Sim — tela financeiro/des | Sim — /v1/financial/ |
| Compra mercadoria / NF entrada | `DESPESAS_FINANCEIRO_REDE` | 15 | 2116.75 | Sim — tela financeiro/des | Sim — /v1/financial/ |
| Tarifa bancária | `DESPESAS_FINANCEIRO_REDE` | 2 | 87.50 | Sim — tela financeiro/des | Sim — /v1/financial/ |
| Sangria / retirada caixa | `DESPESAS_FINANCEIRO_REDE` | 1 | 200.00 | Sim — tela financeiro/des | Sim — /v1/financial/ |
| Compra combustível / TRR | `DESPESAS_FINANCEIRO_REDE` | 1 | 399.00 | Sim — tela financeiro/des | Sim — /v1/financial/ |
| Tarifa bancária | `MOVIMENTO_CONTA` | 400 | — | Sim | Não — apenas diagnós |
| Transferência bancária | `MOVIMENTO_CONTA` | 400 | — | Parcial — endpoint separa | Não — apenas diagnós |
| Despesa operacional genérica | `MOVIMENTO_CONTA` | 200 | — | Sim | Não — apenas diagnós |
| Despesa operacional genérica | `CONTA_REDE` | 17 | — | Sim | Fallback accounts-pa |
| Troco | `TITULO_PAGAR` | 66 | — | Parcial — endpoint separa | Sim — /v1/financial/ |
| Compra mercadoria / NF entrada | `TITULO_PAGAR` | 66 | — | Sim | Sim — /v1/financial/ |
| Salário / folha | `TITULO_PAGAR` | 66 | — | Sim | Sim — /v1/financial/ |
| Compra combustível / TRR | `TITULO_PAGAR` | 26 | — | Sim | Sim — /v1/financial/ |
| Energia / utilities | `TITULO_PAGAR` | 18 | — | Sim | Sim — /v1/financial/ |
| Tarifa bancária | `TITULO_PAGAR` | 11 | — | Sim | Sim — /v1/financial/ |
| Despesa operacional genérica | `TITULO_PAGAR` | 7 | — | Sim | Sim — /v1/financial/ |
| Despesa operacional genérica | `TITULO_RECEBER` | 7 | — | Sim | Não (stub accounts-r |
| Tarifa bancária | `TITULO_RECEBER` | 4 | — | Sim | Não (stub accounts-r |
| Tarifa bancária | `FINANCEIRO_EXCLUSAO` | 10203 | — | Sim | Não |
| Exclusão financeira / débito caixa | `FINANCEIRO_EXCLUSAO` | 10203 | — | Parcial — endpoint separa | Não |
| Despesa operacional genérica | `FINANCEIRO_EXCLUSAO` | 2976 | — | Sim | Não |
| Tarifa bancária | `TRANSFERENCIA_BANCARIA` | 400 | — | Sim | Não |
| Transferência bancária | `TRANSFERENCIA_BANCARIA` | 400 | — | Parcial — endpoint separa | Não |
| Despesa operacional genérica | `CAIXA` | 21 | — | Sim | Parcial — KPIs execu |
| Suprimento / fundo caixa | `CAIXA_APRESENTADO` | 21 | — | Parcial — endpoint separa | Não |
| Troco | `CAIXA_APRESENTADO` | 21 | — | Parcial — endpoint separa | Não |
| Tarifa bancária | `CAIXA_APRESENTADO` | 21 | — | Sim | Não |
| Título a receber | `CAIXA_APRESENTADO` | 21 | — | Parcial — endpoint separa | Não |
| Despesa operacional genérica | `CAIXA_APRESENTADO` | 21 | — | Sim | Não |
| (endpoint CARTAO_COMPRA) | `CARTAO_COMPRA` | 2 | 0.00 | Não comprovado | Não |

## DESPESAS_REDE — distribuição por tipo (descricaoDocumento)

- **Despesa operacional genérica**: 363 registros, R$ 119117.95
- **Salário / folha**: 27 registros, R$ 13711.00
- **Energia / utilities**: 19 registros, R$ 186.00
- **Compra mercadoria / NF entrada**: 15 registros, R$ 2116.75
- **Tarifa bancária**: 2 registros, R$ 87.50
- **Sangria / retirada caixa**: 1 registros, R$ 200.00
- **Compra combustível / TRR**: 1 registros, R$ 399.00

## Status endpoints auditados

- `CAIXA` → HTTP 200, 21 registros, campos: 18
- `CAIXA_APRESENTADO` → HTTP 200, 21 registros, campos: 40
- `CARTAO_COMPRA` → HTTP 400, 2 registros, campos: 12
- `COMPRA_ITEM_REDE` → HTTP 401, 0 registros, campos: 0
- `COMPRA_REDE` → HTTP 401, 0 registros, campos: 0
- `CONSULTAR_CAIXA_APRESENTADO_REDE` → HTTP 200, 0 registros, campos: 0
- `CONSULTAR_TITULO_PAGAR_REDE` → HTTP 200, 0 registros, campos: 0
- `CONTA_REDE` → HTTP 200, 17 registros, campos: 7
- `DESPESAS_FINANCEIRO_REDE` → HTTP 200, 427 registros, campos: 5
- `DESPESA_FUNCIONARIO` → HTTP 401, 0 registros, campos: 0
- `DUPLICATA_REDE` → HTTP 401, 0 registros, campos: 0
- `FECHAMENTO_CAIXA` → HTTP 401, 0 registros, campos: 0
- `FINANCEIRO_EXCLUSAO` → HTTP 200, 10203 registros, campos: 7
- `LANCAMENTO_CONTABIL` → HTTP 200, 0 registros, campos: 0
- `LANCAMENTO_CONTABIL_ITEM` → HTTP 401, 0 registros, campos: 0
- `MOVIMENTO_CONTA` → HTTP 200, 400 registros, campos: 22
- `NOTA_ENTRADA` → HTTP 401, 0 registros, campos: 0
- `NOTA_ENTRADA_REDE` → HTTP 401, 0 registros, campos: 0
- `PEDIDO_COMBUSTIVEL` → HTTP 500, 0 registros, campos: 0
- `PEDIDO_COMPRAS` → HTTP 401, 0 registros, campos: 0
- `PEDIDO_TRR` → HTTP 200, 0 registros, campos: 0
- `TITULO_PAGAR` → HTTP 200, 66 registros, campos: 40
- `TITULO_PAGAR_REDE` → HTTP 401, 0 registros, campos: 0
- `TITULO_RECEBER` → HTTP 200, 11 registros, campos: 18
- `TITULO_RECEBER_REDE` → HTTP 401, 0 registros, campos: 0
- `TRANSFERENCIA_BANCARIA` → HTTP 200, 400 registros, campos: 13
- `VALE_FUNCIONARIO_REDE` → HTTP 401, 0 registros, campos: 0

## O que NÃO vem de DESPESAS_REDE

- **Transferência bancária** via `MOVIMENTO_CONTA` (400 hits texto)
- **Troco** via `TITULO_PAGAR` (66 hits texto)
- **Exclusão financeira / débito caixa** via `FINANCEIRO_EXCLUSAO` (10203 hits texto)
- **Transferência bancária** via `TRANSFERENCIA_BANCARIA` (400 hits texto)
- **Suprimento / fundo caixa** via `CAIXA_APRESENTADO` (21 hits texto)
- **Troco** via `CAIXA_APRESENTADO` (21 hits texto)
- **Título a receber** via `CAIXA_APRESENTADO` (21 hits texto)
