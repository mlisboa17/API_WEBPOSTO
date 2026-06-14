# IA-5 — Pagination & Retry

## Retry

- `max_retries` configurável (default 3)
- Backoff exponencial: `2^(attempt-1)` capped em 8s
- Retry em: 429, 500, 502, 503, 504, timeouts e erros HTTP

## Timeout

- `default_timeout_s=30.0` configurável por request
- Connect timeout: `min(5s, timeout_s)`

## Erros (sem mascaramento)

| HTTP | Exceção |
|------|---------|
| 401/403 | `WebPostoAuthError` |
| 429 | `WebPostoRateLimitError` |
| 5xx | `WebPostoServerError` |
| 4xx outros | `WebPostoDataError` |
| timeout | `WebPostoServerError` (408) |

## Paginação

- `paginate()` — cursor `ultimoCodigo` para ABASTECIMENTO
- Paginação numérica (`pagina` + `tamanhoPagina`) para demais endpoints
- `PaginationState` configurável
