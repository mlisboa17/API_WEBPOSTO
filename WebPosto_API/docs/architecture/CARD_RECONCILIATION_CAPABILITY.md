# Card Reconciliation Capability — VALUE-04

**Decisão formal:** `reconciliation_level = 1` (**LEVEL 1 — AGGREGATE SIGNAL**)

## Justificativa

| Critério | Evidência |
|---|---|
| Dados transacionais TEF | Ausentes (sem NSU, autorização, adquirente) |
| Venda forma pagamento | Endpoint existe; **0 registros** nos 3 postos (30d) |
| Titulo receber | Disponível; classificação pendente/vencido/recebido |
| Vínculo venda↔titulo | Campo `vendaCodigo` presente; **não validado** como cartão |
| Movimento bancário | Disponível; **sem match** titulo a titulo |

## O que LEVEL 1 permite afirmar

- Total de recebíveis **vencidos** sem evidência de liquidação (`pendente=true`, sem `dataPagamento`)
- Concentração por cliente / contagem de títulos
- **Não** afirmar gap cartão TEF vs adquirente
- **Não** afirmar perda confirmada — apenas ausência de evidência de baixa

## O que LEVEL 1 proíbe

- Transaction reconciliation
- "R$ X de cartão não recebido" sem fonte cartão
- CONFIRMED Money Found por ausência de baixa alone

## Fontes por papel

| Papel | Fonte |
|---|---|
| Expectativa | `TITULO_RECEBER` (pendente) |
| Liquidação contábil | `TITULO_RECEBER` (`dataPagamento`, `pendente=false`) |
| Movimento bancário | `MOVIMENTO_CONTA` (suporte apenas) |
