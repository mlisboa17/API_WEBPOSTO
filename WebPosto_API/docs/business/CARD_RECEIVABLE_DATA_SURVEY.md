# Card & Receivable Data Survey — VALUE-04

**Data:** 2026-07-04 | **Escopo:** WebPosto_API real

## Endpoints mapeados

| Endpoint | Key | Service | Arquivo |
|---|---|---|---|
| `/INTEGRACAO/VENDA_FORMA_PAGAMENTO` | `venda_forma_pagamento` | `NetworkFinancialOverviewService._fetch_vendas_produtos` | `network_financial_overview_service.py` |
| `/INTEGRACAO/CONSULTAR_VENDA_FORMA_PAGAMENTO_REDE` | `venda_forma_pagamento_rede` | idem (fallback paginado) | idem |
| `/INTEGRACAO/TITULO_RECEBER` | `titulo_receber` | `CorporateFinanceCenterService._fetch_titulo_receber_all` | `corporate_finance_center_service.py` |
| `/INTEGRACAO/MOVIMENTO_CONTA` | `movimento_conta` | `_fetch_movimento_conta_all` | idem |
| `/INTEGRACAO/VENDA` | `venda` | vendas (contexto) | idem |

## Campos observados (runtime 30d)

**VENDA_FORMA_PAGAMENTO:** vazio nos 3 postos no período (filtro vendaCodigo/rede).

**TITULO_RECEBER:** `empresaCodigo`, `tituloCodigo`, `vendaCodigo`, `nomeCliente`, `valor`, `dataVencimento`, `dataPagamento`, `pendente`, `documento`, `tipo` — **sem** NSU, bandeira, adquirente, taxa.

**MOVIMENTO_CONTA:** `valor`, `dataMovimento`, `tipo`, `descricao`, `lote`, `conciliado`, `tipoDocumentoOrigem` — movimento bancário, não vínculo TEF.

## Respostas (1–25)

| # | Pergunta | Resposta |
|---|---|---|
| 1 | Venda por forma pagamento? | SIM (endpoint) / **vazio runtime 30d** nos 3 postos |
| 2 | Identificação cartão? | PARCIAL (`PaymentMethod.from_raw` em `formaPagamento`) |
| 3 | Bandeira? | **NÃO** |
| 4 | Adquirente? | **NÃO** |
| 5 | NSU? | **NÃO** |
| 6 | Autorização? | **NÃO** |
| 7 | Valor bruto? | SIM (`valor` forma pagamento / titulo) |
| 8 | Valor líquido? | **NÃO** direto |
| 9 | Taxa? | **NÃO** |
| 10 | Data prevista recebimento? | SIM (`dataVencimento`) |
| 11 | Data efetiva? | PARCIAL (`dataPagamento` quando preenchido) |
| 12 | Título a receber? | SIM |
| 13 | Baixa do título? | PARCIAL (`pendente=false` ou `dataPagamento`) |
| 14 | Status liquidação? | PARCIAL (`pendente`, sem enum padronizado) |
| 15 | Vínculo venda→recebível? | PARCIAL (`vendaCodigo` no titulo, não validado 1:1) |
| 16 | Vínculo recebível→baixa? | SIM via `pendente`/`dataPagamento` |
| 17 | Reconciliar 1:1? | **NÃO** (sem NSU/TEF) |
| 18 | Reconciliar agregado? | **SIM** (totais por status/vencimento) |
| 19 | Valor esperado? | PARCIAL (titulo pendente; cartão indisponível no período) |
| 20 | Provar valor recebido? | PARCIAL (baixa contábil, não movimento bancário confirmado) |
| 21 | Detectar atraso? | **SIM** (vencimento < ref) |
| 22 | Detectar diferença valor? | PARCIAL agregado |
| 23 | Detectar ausência baixa? | **SIM** (`pendente=true` + vencido) |
| 24 | Detectar duplicidade? | SINAL (`cliente+valor+vencimento`) |
| 25 | **Maior limitação** | Sem NSU/bandeira/adquirente; `VENDA_FORMA_PAGAMENTO` vazio; titulo ≠ liquidação cartão TEF |
