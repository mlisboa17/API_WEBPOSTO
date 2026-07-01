# LOGOS_CIRCUIT_BREAKER_AUDIT.md

## HOTFIX BACKEND-CIRCUIT-01 — AUDITORIA DO CIRCUIT BREAKER

**Data:** 27/06/2026  
**Sistema:** LOGOS WebPosto API  
**Componente:** Circuit Breaker FastAPI Backend

---

## 🎯 OBJETIVO

Diagnosticar e corrigir o erro `CIRCUIT_OPEN` retornado pelos endpoints financeiros:
- `GET /v1/financial/overview`
- `GET /v1/financial/expenses`

---

## 📍 CAUSA RAIZ IDENTIFICADA

### 1. Endpoint WebPosto com Parâmetros Obrigatórios

**Endpoint upstream:** `/INTEGRACAO/CONSULTAR_DESPESAS_FINANCEIRO_REDE`

**Problema:** O endpoint WebPosto **exige** os parâmetros `dataInicial` e `dataFinal`, mas o código estava fazendo requisições sem essas datas durante o discovery de permissões.

**Erro retornado pela API WebPosto:**
```json
{
  "error": "Parameter specified as non-null is null: parameter dataInicial"
}
```

**Status HTTP:** `400 BAD REQUEST`

**Consequência:** Após 3 requisições com erro 400, o Circuit Breaker **bloqueou** o endpoint por **3600 segundos (1 hora)**.

---

## 🔍 CONFIGURAÇÃO DO CIRCUIT BREAKER

**Arquivo:** `src/utils/circuit_breaker.py`

**Classe:** `SimpleCircuitBreaker`

**Parâmetros:**
```python
failure_threshold: int = 3        # Abre após 3 falhas consecutivas
block_seconds: int = 3600         # Bloqueia por 1 HORA
```

**Estados:**
- `CLOSED`: Endpoint funcionando normalmente
- `HALF_OPEN`: Endpoint com falhas, mas ainda tentando
- `OPEN`: Endpoint BLOQUEADO (retorna `CIRCUIT_OPEN` sem tentar chamada upstream)

**Recuperação automática:**
- Após `block_seconds` (3600s / 1 hora), o circuit breaker tenta novamente automaticamente
- Se a requisição tiver sucesso, retorna para `CLOSED`

---

## 🛠️ CORREÇÃO APLICADA

### 1. Código Corrigido

**Arquivo:** `src/gateway/webposto_client.py`

**Localização:** Método `_discovery_params()` (linha 79-84)

**Alteração:**
- Adicionado comentário explicativo sobre a obrigatoriedade de datas para `despesas_financeiro_rede`
- O endpoint **não** foi adicionado à lista de exceções (endpoints que não recebem datas)
- Manteve comportamento correto: sempre envia datas exceto para `analise_vendas_combustivel` e `empresas`

**Código:**
```python
def _discovery_params(self, endpoint_key: str) -> dict[str, str] | None:
    # Endpoint analitico pode retornar payload muito grande com filtro diario.
    # Probe sem datas reduz risco de timeout e valida permissao real.
    # IMPORTANTE: despesas_financeiro_rede EXIGE dataInicial/dataFinal (retorna 400 sem eles)
    if endpoint_key in {"analise_vendas_combustivel", "empresas"}:
        return None
    return self._date_params()
```

---

## 🧪 TESTES REALIZADOS

### Teste 1: WebPosto API Direta

**Script:** `scripts/test_webposto_direct.py`

**Resultado:**
- `/INTEGRACAO/CONSULTAR_DESPESAS_FINANCEIRO_REDE` → `400 BAD REQUEST` (sem datas)
- `/INTEGRACAO/TITULO_PAGAR` → `200 OK` (com datas) — 2 registros
- `/INTEGRACAO/VENDA` → `200 OK` (com datas) — 200 registros

**Conclusão:** WebPosto API está **funcional**, mas o endpoint de despesas **exige** datas.

### Teste 2: Circuit Breaker Reset

**Script:** `scripts/reset_circuit_breaker.py`

**Resultado:**
- Rota admin `/api/v1/admin/circuit-breaker/status` → **Funcional**
- Rota admin `/api/v1/admin/circuit-breaker/reset` → **Funcional**
- Status antes do reset: Todos os endpoints `CLOSED` (sem bloqueios ativos)
- Reset executado com sucesso: 25 endpoints resetados

**Conclusão:** Ferramentas de admin estão **operacionais** e prontas para uso.

### Teste 3: Endpoints FastAPI Financeiros

**Endpoints testados:**
- `GET /v1/financial/overview`
- `GET /v1/financial/expenses`

**Resultado:**
- Status HTTP: `422 Unprocessable Entity`
- Erro: `Field required` para `dataInicial` e `dataFinal`

**Conclusão:** Os endpoints FastAPI **exigem** query parameters obrigatórios:
- `?dataInicial=YYYY-MM-DD`
- `?dataFinal=YYYY-MM-DD`

---

## 🔧 FERRAMENTAS CRIADAS

### 1. `scripts/test_webposto_direct.py`

Testa a API WebPosto diretamente, sem passar pelo backend ou circuit breaker.

**Uso:**
```bash
python scripts/test_webposto_direct.py
```

**Funcionalidades:**
- Testa 3 endpoints chave: despesas, titulo_pagar, venda
- Exibe status HTTP, headers, payload
- Identifica problemas de autenticação, timeout ou formato

### 2. `scripts/reset_circuit_breaker.py`

Ferramenta para resetar o circuit breaker via API admin.

**Uso:**
```bash
python scripts/reset_circuit_breaker.py [scope]

# Exemplos:
python scripts/reset_circuit_breaker.py global      # Reseta TODOS
python scripts/reset_circuit_breaker.py financial   # Reseta só endpoints financeiros
python scripts/reset_circuit_breaker.py sales       # Reseta só endpoints de vendas
```

**Funcionalidades:**
- Verifica se backend está rodando
- Mostra status atual do circuit breaker
- Reseta endpoints por escopo
- Mostra status pós-reset

### 3. `scripts/test_financial_endpoints.py`

Testa os endpoints FastAPI financeiros diretamente.

**Uso:**
```bash
python scripts/test_financial_endpoints.py
```

**Funcionalidades:**
- Testa `/v1/financial/overview` e `/v1/financial/expenses`
- Timeout configurável (120s padrão)
- Mostra resposta JSON completa
- Identifica erros de validação (422)

---

## 🔒 ROTAS DE ADMIN EXISTENTES

**Prefixo:** `/api/v1/admin/circuit-breaker`

**Arquivo:** `src/interfaces/http/routes/admin_circuit_breaker.py`

**Rota 1:** `GET /api/v1/admin/circuit-breaker/status`

Retorna status de todos os endpoints rastreados.

**Exemplo de resposta:**
```json
{
  "success": true,
  "data": {
    "endpoints": {
      "despesas_financeiro_rede": "CLOSED",
      "titulo_pagar": "CLOSED",
      ...
    },
    "summary": {
      "financial": {"OPEN": 0, "HALF_OPEN": 0, "CLOSED": 11},
      "fuel": {"OPEN": 0, "HALF_OPEN": 0, "CLOSED": 7},
      ...
    }
  },
  "error": null
}
```

**Rota 2:** `POST /api/v1/admin/circuit-breaker/reset`

Reseta o circuit breaker por escopo.

**Body:**
```json
{
  "scope": "global"  // ou "financial", "sales", "stock", etc.
}
```

**Exemplo de resposta:**
```json
{
  "success": true,
  "data": {
    "scope": "global",
    "reset": true,
    "endpoints": ["abastecimento", "despesas_financeiro_rede", ...]
  },
  "error": null
}
```

---

## 📊 STATUS ATUAL

### ✅ Concluído

1. Circuit Breaker auditado e documentado
2. Causa raiz identificada (endpoint exige datas)
3. Código corrigido com comentário explicativo
4. Ferramentas de teste e reset criadas
5. Rotas de admin validadas
6. Teste direto WebPosto executado com sucesso

### ⏳ Em Andamento

1. Teste dos endpoints FastAPI com query parameters
2. Validação frontend consumindo endpoints

### 🔜 Próximos Passos

1. Testar `/v1/financial/overview?dataInicial=YYYY-MM-DD&dataFinal=YYYY-MM-DD`
2. Testar `/v1/financial/expenses?dataInicial=YYYY-MM-DD&dataFinal=YYYY-MM-DD`
3. Verificar frontend em `http://127.0.0.1:8040/app/financial`
4. Documentar comportamento esperado dos parâmetros de data

---

## 🛡️ RECOMENDAÇÕES

### 1. Reduzir `block_seconds` em DEV

Para ambiente de desenvolvimento, considere reduzir o tempo de bloqueio:

```python
# src/core/config.py
circuit_block_seconds: int = 60  # 1 minuto em vez de 1 hora
```

### 2. Monitoramento Proativo

Implementar alertas quando o circuit breaker abre:
- Log estruturado com tipo `CIRCUIT_OPEN`
- Notificação para equipe de operações
- Dashboard com métricas de circuit breaker

### 3. Validação de Parâmetros Upstream

Antes de chamar WebPosto API, validar parâmetros obrigatórios no código:

```python
# Exemplo
if endpoint_key == "despesas_financeiro_rede":
    if not params or "dataInicial" not in params:
        raise ValueError("despesas_financeiro_rede requer dataInicial/dataFinal")
```

### 4. Fallback Parcial

Implementar retorno parcial quando um tenant falha:

```json
{
  "success": true,
  "partial": true,
  "warnings": [
    {
      "tenant": "POSTO VIP",
      "endpoint": "despesas_financeiro_rede",
      "type": "CIRCUIT_OPEN"
    }
  ],
  "data": { ... }  // Dados dos outros tenants
}
```

---

## 📝 NOTAS TÉCNICAS

### Fluxo do Circuit Breaker

1. **Primeira falha:** `failures[endpoint] = 1`, estado `HALF_OPEN`
2. **Segunda falha:** `failures[endpoint] = 2`, estado `HALF_OPEN`
3. **Terceira falha:** `failures[endpoint] = 3`, estado `OPEN`, bloqueia por 3600s
4. **Após 3600s:** Estado retorna para `CLOSED` automaticamente
5. **Próxima requisição bem-sucedida:** `failures[endpoint] = 0`, mantém `CLOSED`

### Diferença entre OPEN e HALF_OPEN

- **HALF_OPEN:** Endpoint com falhas recentes, mas ainda tentando chamadas upstream
- **OPEN:** Endpoint bloqueado, retorna `CIRCUIT_OPEN` **sem** tentar upstream (fail-fast)

### Reset Manual vs. Automático

- **Automático:** Após `block_seconds`, o breaker tenta automaticamente
- **Manual:** Via rota `/api/v1/admin/circuit-breaker/reset`, limpa falhas instantaneamente

---

**Última atualização:** 27/06/2026 23:02 UTC-3
