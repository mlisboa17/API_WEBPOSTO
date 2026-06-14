# IA-6 — Logging & Observability

## Formato padronizado

```json
{
  "system": "webposto",
  "endpoint": "/INTEGRACAO/PRODUTO",
  "status": 200,
  "latency_ms": 432.44,
  "has_data": true,
  "synthetic": false,
  "empresaCodigo": "11495",
  "tokenFingerprint": "abc123def456"
}
```

## Implementação

- `WebPostoLogEvent.to_dict()` → `logger.info(json.dumps(...))`
- Emitted em sucesso e falha HTTP
- **Proibido:** token completo, CHAVE raw em logs

## Teste

`test_logs_never_include_full_token` valida ausência do api_key nos logs.
