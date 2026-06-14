# IA-8 — Gateway Tests

**Arquivo:** `tests/unit/test_webposto_gateway.py`

## Cobertura

| Caso | Status |
|------|--------|
| Montagem params + empresaCodigo | PASS |
| Token fingerprint | PASS |
| Snapshot guard (default) | PASS |
| Shape WebPostoResponse | PASS |
| Erro 401 → WebPostoAuthError | PASS |
| Erro 500 → WebPostoServerError | PASS |
| Timeout | PASS |
| Sem token em log | PASS |
| Mapa ENDPOINTS | PASS |

## Execução

```bash
python -m pytest tests/unit/test_webposto_gateway.py -q --no-cov
```

**Resultado:** 10/10 PASS (sem WebPosto live)
