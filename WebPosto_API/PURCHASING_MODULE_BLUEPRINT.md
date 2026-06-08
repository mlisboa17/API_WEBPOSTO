# PURCHASING_MODULE_BLUEPRINT — A03.7

## Status token atual

| Endpoint | HTTP | Registros |
|---|---|---:|
| COMPRA_REDE | 401 | 0 |
| NOTA_ENTRADA | 401 | 0 |
| NOTA_ENTRADA_REDE | 401 | 0 |
| FORNECEDOR_REDE | 401 | 0 |

## Enquanto 401 — proxy via DESPESAS_REDE

Compras classificadas LOGOS: 39 registros / R$ 5681.12

## Schema inferido (TITULO_PAGAR link)

TITULO_PAGAR expõe `notaEntradaCodigo`, `fornecedorCodigo`, `nomeFornecedor` — base para módulo compras futuro.

## Módulo futuro F04

- fact_compra ← NOTA_ENTRADA
- dim_fornecedor ← FORNECEDOR_REDE
- Relacionamento compra → título pagar
