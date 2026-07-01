# SALES_RUNTIME_RESILIENCE_REPORT — HOTFIX P0

## Simulação unitária

Script: `scripts/audit_sales_resilience_hotfix.py`

Cenário:

```text
get_sales live simulado = sleep(35s)
snapshot financial_sales pré-carregado
sales_live_timeout_seconds = 2s (teste acelerado)
```

Resultado esperado:

```text
elapsed < 22s
resilience.mode = snapshot_fallback
resilience.reason = live_timeout
rows = 2
health continua testável em paralelo
```

## Validação manual

```bash
python -m src.main
curl http://127.0.0.1:8050/health
curl "http://127.0.0.1:8050/v1/sales?dataInicial=2026-06-01&dataFinal=2026-06-07&page=1&limit=5"
```

Resultado medido (WebPosto real + snapshot homologado):

```text
1ª requisição: 8.02s → mode=snapshot_fallback, reason=live_timeout
2ª requisição: 0.00s → mode=snapshot_fallback, reason=circuit_open
```

Correção crítica: após timeout **não** aguardar `await task` cancelada (evita bloqueio extra de 35s).
