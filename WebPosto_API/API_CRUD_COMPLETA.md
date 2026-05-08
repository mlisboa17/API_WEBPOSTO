# 📚 API REST Completa — webPosto CRUD

**Versão:** 0.2.0  
**Status:** Production Ready ✅  
**Base URL:** `http://localhost:5000/api/v1`

---

## 🎯 Visão Geral

API REST completa para gerenciar dados reais do webPosto com:
- ✅ **CRUD completo** (Create, Read, Update, Delete)
- ✅ **Auditoria completa** de todas as operações
- ✅ **Validação rigorosa** com Pydantic v2
- ✅ **Paginação e filtros**
- ✅ **Rastreamento de usuário** (IP, usuário, motivo da operação)

---

## 🔐 Autenticação

Não requer token JWT. Usa headers opcionais para rastreamento:

```bash
# Headers opcionais (recomendados)
-H "X-Usuario: seu-usuario"         # Quem está fazendo a operação
-H "X-Motivo: Atualizar status"     # Razão da operação
```

**Nota:** O IP origem é capturado automaticamente. Todas as operações são registradas em auditoria.

---

## 📊 1. FINANCEIRO (Títulos a Receber/Pagar)

### 1.1 Listar Títulos

**Endpoint:** `GET /financeiro`

**Query Parameters:**
```
pagina=1                    # Número da página (padrão: 1)
limite=50                   # Registros por página (padrão: 50, máx: 500)
tipo=RECEBER               # Filtro: RECEBER ou PAGAR
status=pendente            # Filtro: pendente, pago, vencido, cancelado
ordenar_por=data_vencimento # Campo para ordenação
```

**Exemplo — cURL:**
```bash
curl -X GET "http://localhost:5000/api/v1/financeiro?pagina=1&limite=50&tipo=RECEBER&status=pendente" \
  -H "Content-Type: application/json"
```

**Exemplo — Postman:**
```
GET http://localhost:5000/api/v1/financeiro
Params:
  pagina: 1
  limite: 50
  tipo: RECEBER
  status: pendente
```

**Resposta (200 OK):**
```json
{
  "status": "success",
  "total": 10,
  "pagina": 1,
  "limite": 50,
  "total_paginas": 1,
  "dados": [
    {
      "id": "TIT001",
      "tipo": "RECEBER",
      "valor": 1500.00,
      "data_vencimento": "2026-05-14T00:00:00",
      "descricao": "Venda de produtos",
      "cliente_fornecedor": "Cliente ABC",
      "categoria": "Vendas",
      "pago": false,
      "dias_vencido": -29,
      "status": "pendente",
      "webposto_id": "WP000001",
      "data_criacao": "2026-04-14T10:30:00",
      "data_pagamento": null,
      "data_atualizacao": "2026-04-14T10:30:00",
      "modificado_por": "gerente"
    }
  ],
  "timestamp": "2026-04-14T18:30:45Z"
}
```

---

### 1.2 Obter Título Específico

**Endpoint:** `GET /financeiro/{titulo_id}`

**Exemplo — cURL:**
```bash
curl -X GET "http://localhost:5000/api/v1/financeiro/TIT001"
```

**Resposta (200 OK):**
```json
{
  "status": "success",
  "mensagem": "Título obtido com sucesso",
  "dados": {
    "id": "TIT001",
    "tipo": "RECEBER",
    "valor": 1500.00,
    ...
  }
}
```

---

### 1.3 Criar Novo Título

**Endpoint:** `POST /financeiro`

**Headers:**
```
Content-Type: application/json
X-Usuario: seu-usuario         # RECOMENDADO
X-Motivo: Criar título de venda # RECOMENDADO
```

**Body (JSON):**
```json
{
  "tipo": "RECEBER",
  "valor": 2500.50,
  "data_vencimento": "2026-05-15T00:00:00Z",
  "descricao": "Venda de material de construção",
  "cliente_fornecedor": "Construtora ABC Ltda",
  "categoria": "Vendas"
}
```

**Exemplo — cURL:**
```bash
curl -X POST "http://localhost:5000/api/v1/financeiro" \
  -H "Content-Type: application/json" \
  -H "X-Usuario: gerente" \
  -H "X-Motivo: Venda realizada hoje" \
  -d '{
    "tipo": "RECEBER",
    "valor": 2500.50,
    "data_vencimento": "2026-05-15T00:00:00Z",
    "descricao": "Venda de material",
    "cliente_fornecedor": "Construtora ABC",
    "categoria": "Vendas"
  }'
```

**Exemplo — Postman:**
```
POST http://localhost:5000/api/v1/financeiro
Headers:
  Content-Type: application/json
  X-Usuario: gerente
  X-Motivo: Venda realizada

Body (raw JSON):
{
  "tipo": "RECEBER",
  "valor": 2500.50,
  "data_vencimento": "2026-05-15T00:00:00Z",
  "descricao": "Venda de material",
  "cliente_fornecedor": "Construtora ABC",
  "categoria": "Vendas"
}
```

**Resposta (200 OK):**
```json
{
  "status": "success",
  "mensagem": "Título criado com sucesso",
  "dados": {
    "id": "TIT9A8B7C6D",
    "tipo": "RECEBER",
    "valor": 2500.50,
    "data_vencimento": "2026-05-15T00:00:00",
    "descricao": "Venda de material",
    "cliente_fornecedor": "Construtora ABC",
    "categoria": "Vendas",
    "pago": false,
    "dias_vencido": -30,
    "status": "pendente",
    "webposto_id": null,
    "data_criacao": "2026-04-14T18:30:45Z",
    "data_pagamento": null,
    "data_atualizacao": "2026-04-14T18:30:45Z",
    "modificado_por": "gerente"
  },
  "timestamp": "2026-04-14T18:30:45Z"
}
```

**Validações:**
- ❌ `valor` deve ser > 0
- ❌ `descricao` deve ter 3-255 caracteres
- ❌ `cliente_fornecedor` deve ter 3-255 caracteres
- ❌ `tipo` deve ser RECEBER ou PAGAR

**Erros:**
```json
{
  "status": "error",
  "detail": "Validação falhou: valor deve ser positivo"
}
```

---

### 1.4 Atualizar Título

**Endpoint:** `PUT /financeiro/{titulo_id}`

**Headers:**
```
Content-Type: application/json
X-Usuario: seu-usuario
X-Motivo: Razão da atualização  # RECOMENDADO
```

**Body (parcial — envie apenas campos a atualizar):**
```json
{
  "valor": 3000.00,
  "pago": true,
  "data_pagamento": "2026-04-14T15:30:00Z"
}
```

**Exemplo — cURL:**
```bash
curl -X PUT "http://localhost:5000/api/v1/financeiro/TIT001" \
  -H "Content-Type: application/json" \
  -H "X-Usuario: gerente" \
  -H "X-Motivo: Recebimento confirmado" \
  -d '{
    "valor": 3000.00,
    "pago": true,
    "data_pagamento": "2026-04-14T15:30:00Z"
  }'
```

**Resposta (200 OK):**
```json
{
  "status": "success",
  "mensagem": "Título atualizado com sucesso",
  "dados": {
    "id": "TIT001",
    "tipo": "RECEBER",
    "valor": 3000.00,
    "pago": true,
    "status": "pago",
    "data_pagamento": "2026-04-14T15:30:00Z",
    "data_atualizacao": "2026-04-14T18:35:20Z",
    "modificado_por": "gerente",
    ...
  }
}
```

---

### 1.5 Deletar Título

**Endpoint:** `DELETE /financeiro/{titulo_id}`

**Headers:**
```
X-Usuario: seu-usuario
X-Motivo: Razão da deleção (opcional)
```

**Exemplo — cURL:**
```bash
curl -X DELETE "http://localhost:5000/api/v1/financeiro/TIT001" \
  -H "X-Usuario: gerente" \
  -H "X-Motivo: Deleção acidental"
```

**Resposta (200 OK):**
```json
{
  "status": "success",
  "mensagem": "Título deletado com sucesso",
  "dados": {
    "id": "TIT001",
    "status": "cancelado",
    "mensagem": "Título cancelado com sucesso"
  }
}
```

**Nota:** Soft delete — o título é marcado como "cancelado", não é removido do banco.

---

## 📦 2. CAIXA (Movimentos de Caixa)

### 2.1 Listar Movimentos

**Endpoint:** `GET /caixa`

**Query Parameters:**
```
pagina=1              # Padrão: 1
limite=50             # Padrão: 50, máx: 500
numero_caixa=1        # Filtro: 1, 2, 3, etc.
tipo_movimento=VENDA  # Filtro: ABERTURA, VENDA, SAQUE, FECHAMENTO, TRANSFERENCIA, DEVOLUCAO, AJUSTE
data=2026-04-14       # Filtro por data (YYYY-MM-DD)
```

**Exemplo — cURL:**
```bash
curl -X GET "http://localhost:5000/api/v1/caixa?numero_caixa=1&tipo_movimento=VENDA"
```

**Resposta (200 OK):**
```json
{
  "status": "success",
  "total": 15,
  "pagina": 1,
  "limite": 50,
  "total_paginas": 1,
  "dados": [
    {
      "id": "CAIXA001",
      "numero_caixa": 1,
      "descricao": "Venda Pista",
      "tipo_movimento": "VENDA",
      "valor": 250.50,
      "saldo": 5250.50,
      "data_movimento": "2026-04-14T10:30:00",
      "referencia": "VND-001",
      "operador": "João Silva",
      "webposto_id": "WPC000001",
      "data_criacao": "2026-04-14T10:30:00",
      "data_atualizacao": "2026-04-14T10:30:00",
      "modificado_por": null
    }
  ]
}
```

---

### 2.2 Obter Movimento Específico

**Endpoint:** `GET /caixa/{movimento_id}`

**Exemplo — cURL:**
```bash
curl -X GET "http://localhost:5000/api/v1/caixa/CAIXA001"
```

---

### 2.3 Criar Movimento de Caixa

**Endpoint:** `POST /caixa`

**Body (JSON):**
```json
{
  "numero_caixa": 1,
  "descricao": "Venda Pista — combustível",
  "tipo_movimento": "VENDA",
  "valor": 150.75,
  "referencia": "VND-001",
  "operador": "João Silva"
}
```

**Exemplo — cURL:**
```bash
curl -X POST "http://localhost:5000/api/v1/caixa" \
  -H "Content-Type: application/json" \
  -H "X-Usuario: operador" \
  -d '{
    "numero_caixa": 1,
    "descricao": "Venda combustível",
    "tipo_movimento": "VENDA",
    "valor": 150.75,
    "referencia": "VND-001",
    "operador": "João"
  }'
```

**Validações:**
- ❌ `numero_caixa` deve estar entre 1-999
- ❌ `valor` deve ser > 0
- ❌ `descricao` deve ter 3-255 caracteres
- ❌ `tipo_movimento` deve ser válido

---

### 2.4 Atualizar Movimento

**Endpoint:** `PUT /caixa/{movimento_id}`

**Body (parcial):**
```json
{
  "valor": 200.00,
  "operador": "Maria Santos"
}
```

**Exemplo — cURL:**
```bash
curl -X PUT "http://localhost:5000/api/v1/caixa/CAIXA001" \
  -H "Content-Type: application/json" \
  -H "X-Usuario: supervisor" \
  -H "X-Motivo: Ajuste de valor" \
  -d '{
    "valor": 200.00
  }'
```

---

### 2.5 Deletar Movimento

**Endpoint:** `DELETE /caixa/{movimento_id}`

**Exemplo — cURL:**
```bash
curl -X DELETE "http://localhost:5000/api/v1/caixa/CAIXA001" \
  -H "X-Usuario: gerente" \
  -H "X-Motivo: Cancelamento de entrada duplicada"
```

---

## 📋 3. AUDITORIA (Log de Operações)

### 3.1 Listar Log Completo

**Endpoint:** `GET /auditoria`

**Query Parameters:**
```
pagina=1              # Padrão: 1
limite=50             # Padrão: 50
tabela=financeiro     # Filtro: financeiro ou caixa
usuario=gerente       # Filtro por usuário
operacao=UPDATE       # Filtro: CREATE, UPDATE, DELETE
```

**Exemplo — cURL:**
```bash
curl -X GET "http://localhost:5000/api/v1/auditoria?tabela=financeiro&operacao=CREATE"
```

**Resposta (200 OK):**
```json
{
  "status": "success",
  "total": 156,
  "pagina": 1,
  "limite": 50,
  "total_paginas": 4,
  "dados": [
    {
      "id": "AUD12345678",
      "tabela": "financeiro",
      "record_id": "TIT001",
      "operacao": "UPDATE",
      "usuario": "gerente",
      "valores_antes": {
        "valor": 1500.00,
        "pago": false
      },
      "valores_depois": {
        "valor": 3000.00,
        "pago": true
      },
      "data_operacao": "2026-04-14T15:30:20Z",
      "ip_origem": "192.168.1.100",
      "motivo": "Recebimento confirmado"
    }
  ]
}
```

**Filtros Úteis:**

Listar apenas criações:
```bash
GET /auditoria?operacao=CREATE
```

Listar operações de um usuário:
```bash
GET /auditoria?usuario=gerente
```

Listar deletions em caixa:
```bash
GET /auditoria?tabela=caixa&operacao=DELETE
```

---

## 🧪 Exemplos Completos — Workflows Reais

### Workflow 1: Registrar Venda Completa

```bash
#!/bin/bash

API="http://localhost:5000/api/v1"
USUARIO="operador_pista"

# 1. Registrar movimento de venda em caixa
echo "1. Criando movimento de caixa..."
MOVIMENTO=$(curl -s -X POST "$API/caixa" \
  -H "Content-Type: application/json" \
  -H "X-Usuario: $USUARIO" \
  -d '{
    "numero_caixa": 1,
    "descricao": "Venda combustível gasolina",
    "tipo_movimento": "VENDA",
    "valor": 175.50,
    "referencia": "VND-2026-001",
    "operador": "João Silva"
  }')

CAIXA_ID=$(echo $MOVIMENTO | jq -r '.dados.id')
echo "✅ Movimento criado: $CAIXA_ID"

# 2. Se for venda com crédito, criar título financeiro
echo "2. Criando título a receber..."
TITULO=$(curl -s -X POST "$API/financeiro" \
  -H "Content-Type: application/json" \
  -H "X-Usuario: $USUARIO" \
  -H "X-Motivo: Venda com crédito em 30 dias" \
  -d '{
    "tipo": "RECEBER",
    "valor": 175.50,
    "data_vencimento": "2026-05-14T00:00:00Z",
    "descricao": "Combustível (venda pista)",
    "cliente_fornecedor": "Cliente Comum",
    "categoria": "Vendas Pista"
  }')

TITULO_ID=$(echo $TITULO | jq -r '.dados.id')
echo "✅ Título criado: $TITULO_ID"

# 3. Consultar auditoria da operação
echo "3. Verificando log de auditoria..."
curl -s -X GET "$API/auditoria?pagina=1&limite=2" | jq '.dados'
```

---

### Workflow 2: Receber Pagamento

```bash
#!/bin/bash

API="http://localhost:5000/api/v1"
TITULO_ID="TIT001"
USUARIO="gerente"

# 1. Marcar título como pago
echo "Registrando recebimento..."
curl -X PUT "$API/financeiro/$TITULO_ID" \
  -H "Content-Type: application/json" \
  -H "X-Usuario: $USUARIO" \
  -H "X-Motivo: Recebimento via transferência bancária" \
  -d '{
    "pago": true,
    "data_pagamento": "'$(date -u +%Y-%m-%dT%H:%M:%SZ)'"
  }'

# 2. Criar movimento de caixa (saque)
echo "Criando movimento de entrada em caixa..."
curl -X POST "$API/caixa" \
  -H "Content-Type: application/json" \
  -H "X-Usuario: $USUARIO" \
  -d '{
    "numero_caixa": 1,
    "descricao": "Recebimento — Cliente ABC",
    "tipo_movimento": "SAQUE",
    "valor": 1500.00,
    "referencia": "REC-'$(date +%Y%m%d%H%M%S)'",
    "operador": "'$USUARIO'"
  }'
```

---

## 📊 Códigos HTTP & Erros

| Código | Significado | Exemplo |
|--------|-------------|---------|
| 200 | Sucesso | Título criado/atualizado |
| 400 | Erro no request | Valor negativo, campo obrigatório faltando |
| 404 | Não encontrado | Título/movimento com ID inválido |
| 422 | Validação falhou | Formato de data inválido |
| 500 | Erro do servidor | Erro ao acessar webPosto API |

**Exemplo de Erro (422):**
```json
{
  "detail": "Validação falhou: valor deve ser positivo"
}
```

---

## 🔄 Fluxo de Auditoria Automática

Todas as operações CRUD são automaticamente registradas:

```
┌─────────────────────────────────────┐
│ Requisição HTTP (POST/PUT/DELETE)  │
│ Headers: X-Usuario, X-Motivo        │
└────────────┬────────────────────────┘
             │
             ▼
┌─────────────────────────────────────┐
│ Valida dados com Pydantic           │
│ Captura IP origem                   │
│ Extrai usuário e motivo             │
└────────────┬────────────────────────┘
             │
             ▼
┌─────────────────────────────────────┐
│ Executa CRUD (Create/Update/Delete) │
│ Gera ID único                       │
│ Calcula campos derivados (status)   │
└────────────┬────────────────────────┘
             │
             ▼
┌─────────────────────────────────────┐
│ Registra em Auditoria:              │
│ - ID operação                       │
│ - Tabela + Record ID                │
│ - Operação (CREATE/UPDATE/DELETE)   │
│ - Valores antes/depois              │
│ - Usuário + IP + Motivo             │
│ - Timestamp                         │
└────────────┬────────────────────────┘
             │
             ▼
┌─────────────────────────────────────┐
│ Retorna 200 OK                      │
│ JSON com dados operação             │
└─────────────────────────────────────┘
```

---

## 🚀 Deployment — Ativar API CRUD

**No servidor de produção:**

```bash
# 1. Atualizar código
git pull origin main

# 2. Reiniciar containers
docker-compose restart api

# 3. Verificar endpoints CRUD
curl http://localhost:5000/api/v1/financeiro
curl http://localhost:5000/api/v1/caixa
curl http://localhost:5000/api/v1/auditoria

# 4. Acessar dashboard
open http://localhost:3000
```

---

## 📞 Suporte

- 📚 **Docs Swagger:** `GET /docs`
- 📖 **Docs ReDoc:** `GET /redoc`
- 🆘 **Issues:** Raise issue no GitHub
- 💬 **Chat:** Slack @devops

---

**Status API:** ✅ Production Ready  
**Última atualização:** 2026-04-14  
**Mantido por:** Grupo Lisboa
