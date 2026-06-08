# Inventario de Endpoints (OpenAPI)

## GET /health
- **Tags:** Health
- **Summary:** Health Check
- **Request:** None
- **Responses:**
  - `200`: Successful Response

## GET /ready
- **Tags:** Health
- **Summary:** Readiness Check
- **Request:** None
- **Responses:**
  - `200`: Successful Response

## GET /v1/expenses
- **Tags:** WebPosto Enterprise
- **Summary:** Expenses
- **Request:**
  - `dataInicial` (query, required: True)
  - `dataFinal` (query, required: True)
- **Responses:**
  - `200`: Successful Response
  - `422`: Validation Error

## GET /v1/permissions
- **Tags:** WebPosto Enterprise
- **Summary:** Permissions
- **Request:** None
- **Responses:**
  - `200`: Successful Response

## GET /v1/abastecimento
- **Tags:** WebPosto Enterprise
- **Summary:** Abastecimento
- **Request:**
  - `dataInicial` (query, required: True)
  - `dataFinal` (query, required: True)
- **Responses:**
  - `200`: Successful Response
  - `422`: Validation Error

## GET /v1/financeiro
- **Tags:** WebPosto Enterprise
- **Summary:** Financeiro
- **Request:**
  - `dataInicial` (query, required: True)
  - `dataFinal` (query, required: True)
- **Responses:**
  - `200`: Successful Response
  - `422`: Validation Error

## GET /v1/caixa
- **Tags:** WebPosto Enterprise
- **Summary:** Caixa
- **Request:**
  - `dataInicial` (query, required: True)
  - `dataFinal` (query, required: True)
- **Responses:**
  - `200`: Successful Response
  - `422`: Validation Error

## GET /v1/caixa-apresentado
- **Tags:** WebPosto Enterprise
- **Summary:** Caixa Apresentado
- **Request:**
  - `dataInicial` (query, required: True)
  - `dataFinal` (query, required: True)
- **Responses:**
  - `200`: Successful Response
  - `422`: Validation Error

## GET /v1/vendas-combustivel
- **Tags:** WebPosto Enterprise
- **Summary:** Vendas Combustivel
- **Request:**
  - `dataInicial` (query, required: True)
  - `dataFinal` (query, required: True)
- **Responses:**
  - `200`: Successful Response
  - `422`: Validation Error

## GET /v1/box-closure
- **Tags:** WebPosto Enterprise
- **Summary:** Box Closure
- **Request:**
  - `dataInicial` (query, required: True)
  - `dataFinal` (query, required: True)
  - `X-Posto-ID` (header, required: True)
- **Responses:**
  - `200`: Successful Response
  - `422`: Validation Error

## GET /v1/operacao-inteligente
- **Tags:** WebPosto Enterprise
- **Summary:** Operacao Inteligente
- **Request:**
  - `dataInicial` (query, required: True)
  - `dataFinal` (query, required: True)
  - `X-Posto-ID` (header, required: True)
- **Responses:**
  - `200`: Successful Response
  - `422`: Validation Error

## GET /v1/observability
- **Tags:** WebPosto Enterprise
- **Summary:** Observability
- **Request:** None
- **Responses:**
  - `200`: Successful Response

## GET /v1/network/financial-overview
- **Tags:** WebPosto Enterprise
- **Summary:** Network Financial Overview
- **Request:**
  - `dataInicial` (query, required: True)
  - `dataFinal` (query, required: True)
  - `empresa` (query, required: False)
  - `tipoDespesa` (query, required: False)
  - `planoContaCodigo` (query, required: False)
  - `planoConta` (query, required: False)
  - `centroCusto` (query, required: False)
  - `valorMin` (query, required: False)
  - `valorMax` (query, required: False)
  - `status` (query, required: False)
  - `origem` (query, required: False)
  - `fornecedor` (query, required: False)
  - `vencimentoInicial` (query, required: False)
  - `vencimentoFinal` (query, required: False)
- **Responses:**
  - `200`: Successful Response
  - `422`: Validation Error

## GET /v1/financial/overview
- **Tags:** WebPosto Enterprise
- **Summary:** Financial Overview
- **Request:**
  - `dataInicial` (query, required: True)
  - `dataFinal` (query, required: True)
  - `empresaCodigo` (query, required: False)
  - `tipoDespesa` (query, required: False)
  - `planoConta` (query, required: False)
  - `centroCusto` (query, required: False)
  - `valorMin` (query, required: False)
  - `valorMax` (query, required: False)
  - `origem` (query, required: False)
- **Responses:**
  - `200`: Successful Response
  - `422`: Validation Error

## GET /v1/financial/companies
- **Tags:** WebPosto Enterprise
- **Summary:** Financial Companies
- **Request:** None
- **Responses:**
  - `200`: Successful Response

## GET /v1/financial/expenses
- **Tags:** WebPosto Enterprise
- **Summary:** Financial Expenses
- **Request:**
  - `dataInicial` (query, required: True)
  - `dataFinal` (query, required: True)
  - `empresaCodigo` (query, required: False)
  - `tipoDespesa` (query, required: False)
  - `planoConta` (query, required: False)
  - `centroCusto` (query, required: False)
  - `valorMin` (query, required: False)
  - `valorMax` (query, required: False)
  - `origem` (query, required: False)
  - `page` (query, required: False)
  - `limit` (query, required: False)
- **Responses:**
  - `200`: Successful Response
  - `422`: Validation Error

## GET /v1/financial/accounts-payable
- **Tags:** WebPosto Enterprise
- **Summary:** Financial Accounts Payable
- **Request:**
  - `dataInicial` (query, required: True)
  - `dataFinal` (query, required: True)
  - `empresaCodigo` (query, required: False)
  - `status` (query, required: False)
  - `fornecedor` (query, required: False)
  - `vencimentoInicial` (query, required: False)
  - `vencimentoFinal` (query, required: False)
  - `page` (query, required: False)
  - `limit` (query, required: False)
- **Responses:**
  - `200`: Successful Response
  - `422`: Validation Error

## GET /v1/financial/accounts-receivable
- **Tags:** WebPosto Enterprise
- **Summary:** Financial Accounts Receivable
- **Request:**
  - `dataInicial` (query, required: True)
  - `dataFinal` (query, required: True)
  - `empresaCodigo` (query, required: False)
  - `page` (query, required: False)
  - `limit` (query, required: False)
- **Responses:**
  - `200`: Successful Response
  - `422`: Validation Error

## GET /v1/sales
- **Tags:** WebPosto Enterprise
- **Summary:** Sales
- **Request:**
  - `dataInicial` (query, required: True)
  - `dataFinal` (query, required: True)
  - `empresaCodigo` (query, required: False)
  - `page` (query, required: False)
  - `limit` (query, required: False)
- **Responses:**
  - `200`: Successful Response
  - `422`: Validation Error

## GET /v1/stock
- **Tags:** WebPosto Enterprise
- **Summary:** Stock
- **Request:**
  - `dataInicial` (query, required: True)
  - `dataFinal` (query, required: True)
  - `empresaCodigo` (query, required: False)
  - `page` (query, required: False)
  - `limit` (query, required: False)
- **Responses:**
  - `200`: Successful Response
  - `422`: Validation Error

## POST /expenses/extract
- **Tags:** Expenses
- **Summary:** Extract Expenses
- **Request:**
  - Body: JSON
- **Responses:**
  - `200`: Successful Response
  - `422`: Validation Error

## POST /clientes/
- **Tags:** Clientes
- **Summary:** Criar Cliente
- **Request:**
  - Body: JSON
- **Responses:**
  - `201`: Successful Response
  - `422`: Validation Error

## GET /clientes/
- **Tags:** Clientes
- **Summary:** Listar Clientes
- **Request:**
  - `skip` (query, required: False)
  - `limit` (query, required: False)
  - `apenas_ativos` (query, required: False)
- **Responses:**
  - `200`: Successful Response
  - `422`: Validation Error

## GET /clientes/{cliente_id}
- **Tags:** Clientes
- **Summary:** Obter Cliente
- **Request:**
  - `cliente_id` (path, required: True)
- **Responses:**
  - `200`: Successful Response
  - `422`: Validation Error

## PUT /clientes/{cliente_id}
- **Tags:** Clientes
- **Summary:** Atualizar Cliente
- **Request:**
  - `cliente_id` (path, required: True)
  - Body: JSON
- **Responses:**
  - `200`: Successful Response
  - `422`: Validation Error

## DELETE /clientes/{cliente_id}
- **Tags:** Clientes
- **Summary:** Deletar Cliente
- **Request:**
  - `cliente_id` (path, required: True)
- **Responses:**
  - `204`: Successful Response
  - `422`: Validation Error

## POST /sync/clientes
- **Tags:** Sync
- **Summary:** Sync Clientes
- **Request:** None
- **Responses:**
  - `200`: Successful Response

## POST /sync/abastecimentos
- **Tags:** Sync
- **Summary:** Sync Abastecimentos
- **Request:** None
- **Responses:**
  - `200`: Successful Response

## POST /sync/financeiro
- **Tags:** Sync
- **Summary:** Sync Financeiro
- **Request:** None
- **Responses:**
  - `200`: Successful Response

## POST /sync/caixa
- **Tags:** Sync
- **Summary:** Sync Caixa
- **Request:** None
- **Responses:**
  - `200`: Successful Response

## POST /sync/full
- **Tags:** Sync
- **Summary:** Full Sync
- **Request:** None
- **Responses:**
  - `200`: Successful Response

## POST /auth/login
- **Tags:** auth
- **Summary:** Login
- **Request:**
  - Body: JSON
- **Responses:**
  - `200`: Successful Response
  - `422`: Validation Error

## POST /auth/refresh
- **Tags:** auth
- **Summary:** Refresh
- **Request:** None
- **Responses:**
  - `200`: Successful Response

## POST /auth/logout
- **Tags:** auth
- **Summary:** Logout
- **Request:** None
- **Responses:**
  - `200`: Successful Response

## GET /metrics/executive
- **Tags:** Metrics
- **Summary:** Executive Metrics
- **Request:** None
- **Responses:**
  - `200`: Successful Response

## GET /metrics/stream
- **Tags:** Metrics
- **Summary:** Stream Metrics
- **Request:** None
- **Responses:**
  - `200`: Successful Response

## GET /app/financial
- **Tags:** 
- **Summary:** Financial Frontend
- **Request:** None
- **Responses:**
  - `200`: Successful Response
