# VENDA FORMA PAGAMENTO — CATALOG — Sprint D00

## Endpoints

| Endpoint | HTTP | Registros probe | Uso Logos |
|----------|------|-----------------|-----------|
| `/INTEGRACAO/VENDA_FORMA_PAGAMENTO` | 200 | 200 | `network_financial_overview` — **agregado, não operacional** |
| `/INTEGRACAO/CONSULTAR_VENDA_FORMA_PAGAMENTO_REDE` | 200 | 0 | Fallback rede — **0 reg no período** |

## Campos API (13 campos)

`empresaCodigo, vendaCodigo, vendaPrazoCodigo, dataMovimento, vencimento, valorPagamento, taxaPercentual, formaPagamentoCodigo, administradoraCodigo, turnoCodigo, tipoFormaPagamento, nomeFormaPagamento, codigo`

## Mapeamento formas de pagamento

| Forma | Fonte primária | Campos chave |
|---|---|---|
| DINHEIRO | CAIXA_APRESENTADO.dinheiro* | VENDA_FORMA_PAGAMENTO (nomeFormaPagamento) |
| PIX | VENDA_FORMA_PAGAMENTO | tipoFormaPagamento / nomeFormaPagamento |
| DEBITO | VENDA_FORMA_PAGAMENTO + cartao* | administradoraCodigo |
| CREDITO | VENDA_FORMA_PAGAMENTO + cartao* | administradoraCodigo |
| CONVENIO | VENDA_FORMA_PAGAMENTO | nomeFormaPagamento |
| VALE | CAIXA_APRESENTADO.valeCliente* + DESPESAS | valeFun* parcial |
| PRAZO | CAIXA_APRESENTADO.notaPrazo* + TITULO_RECEBER | vendaPrazoCodigo |

## Dimensões disponíveis vs exploradas

| Dimensão | Campo API | Explorado no Logos |
|----------|-----------|-------------------|
| PDV | via join `VENDA.caixaCodigo` → `CAIXA.pdvCodigo` | **Não** |
| Operador | via join `VENDA.funcionarioCodigo` | **Não** |
| Turno | `turnoCodigo` | **Não** |
| Empresa | `empresaCodigo` | Sim (filtro) |
| Bandeira cartão | `administradoraCodigo` | **Não** |

## Oportunidade F04

`CONSULTAR_VENDA_FORMA_PAGAMENTO_REDE = 200` nos logs, mas **subexplorado**. Cruzamento com CAIXA + Prestação habilita mix Dinheiro/PIX/Cartão **por operador/turno/PDV**.
