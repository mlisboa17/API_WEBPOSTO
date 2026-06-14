# IA-1 — Endpoint Message Source Report

## Missão

Localizar a origem exata de **"Endpoint bloqueado temporariamente"**.

## Resultado

| Campo | Valor |
|-------|-------|
| **Arquivo** | `src/gateway/webposto_client.py` |
| **Linha** | **209** |
| **Função** | `WebPostoClient.call_endpoint()` |
| **Componente** | Circuit Breaker (`SimpleCircuitBreaker`) |
| **Tipo de erro** | `CIRCUIT_OPEN` |
| **HTTP lógico** | 503 (retornado dentro de `WebPostoResponse`, não como status HTTP da API FastAPI) |

## Trecho responsável

```python
if self.breaker.is_blocked(endpoint_key):
    return WebPostoResponse.fail(
        WebPostoError(
            endpoint=path,
            status=503,
            type="CIRCUIT_OPEN",
            message="Endpoint bloqueado temporariamente",
        )
    )
```

## Propagação até a UI

1. `NetworkFinancialOverviewService._fetch_despesas_rede()` → `call_endpoint("despesas_financeiro_rede")`
2. Rotas FastAPI retornam `resp.to_dict()` com `success: false` (**HTTP 200**)
3. `frontend/services/apiClient.js:75-77` lança `Error` com `data.error.message`
4. `frontend/app.js` → `setError(error.message)` exibe no `#error`

## Onde NÃO está a mensagem

| Local | Resultado |
|-------|-----------|
| `frontend/` | ❌ String ausente |
| `gateway/` (Onda 2) | ❌ Mensagem diferente (`WebPostoSnapshotGuardError`) |
| Snapshots | ❌ Não gera esta mensagem |

## Parecer IA-1

A mensagem é **100% backend**, gerada pelo **circuit breaker** do `WebPostoClient` em `src/gateway/`, não pelo frontend.
