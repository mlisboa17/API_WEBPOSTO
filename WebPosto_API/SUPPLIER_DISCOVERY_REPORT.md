# SUPPLIER DISCOVERY REPORT — F01.4-C

**Período:** 2026-06-01 → 2026-06-07
**Evidência:** `scripts/supplier_discovery_audit.json`

| Endpoint | HTTP | Registros | Classificação | Campos fornecedor |
|----------|------|-----------|---------------|-------------------|
| FORNECEDOR_REDE | 401 | 0 | **401** | — |
| CONTA_FORNECEDOR | 401 | 0 | **401** | — |
| FORNECEDOR | 200 | 200 | **USAR_AGORA** | fornecedorCodigo, tipoPessoa |
| DESPESAS_REDE | 200 | 436 | **SEM_COBERTURA** | — |
| TITULO_PAGAR | 200 | 70 | **USAR_AGORA** | fornecedorCodigo, nomeFornecedor, cpfCnpjFornecedor, contaFornecedor |
| MOVIMENTO_CONTA | 200 | 200 | **USAR_COM_CUIDADO** | codigoPessoa, tipoPessoa |
| COMPRA_REDE | 401 | 0 | **401** | — |
| PEDIDO_COMPRAS | 401 | 0 | **401** | — |
| NOTA_ENTRADA | 401 | 0 | **401** | — |
| CLIENTE_EMPRESA_REDE | 401 | 0 | **401** | — |

## Fonte primária recomendada

**TITULO_PAGAR** — `nomeFornecedor`, `fornecedorCodigo`, `cpfCnpjFornecedor`, `contaFornecedor`

## Bloqueados (401)

FORNECEDOR_REDE, COMPRA_REDE, PEDIDO_COMPRAS, NOTA_ENTRADA