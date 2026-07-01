# SALES_RESILIENCE_QA_REPORT — HOTFIX P0

## Checklist IA-7

| Critério | Status |
|---|---|
| 0 bloqueio event loop (sync I/O) | ✅ httpx async; cancelamento via task |
| 0 timeout > 22s (com hotfix) | ✅ unitário 2.02s; TestClient 2.03s |
| 0 perda lineage | ✅ N/A vendas (sem lineagePath) |
| 0 dado sintético como real | ✅ `synthetic: true` + `degraded: true` |
| 0 quebra endpoints financeiros | ✅ escopo isolado em `SalesResilienceService` |
| 0 quebra F07 | ✅ sem alteração em non_fuel_product_sales |

## Testes executados

```text
Unit: live sleep(35s) + snapshot → elapsed 2.02s, mode=snapshot_fallback
HTTP TestClient: elapsed 2.03s, rows=3
Health pós-restart: 200 OK
```

## Script QA

```bash
python scripts/audit_sales_resilience_hotfix.py
```

## Arquivos alterados

- `src/services/sales_resilience_service.py` (novo)
- `src/gateway/sales_circuit.py` (novo)
- `src/gateway/circuit_domains.py` (scope sales)
- `src/infrastructure/config/settings.py` (timeouts)
- `src/interfaces/http/routes/fechamento_enterprise.py` (wire)
- `frontend/services/api.js` + `apiClient.js` (degraded UX)
- `src/services/financial_resilience_service.py` (cleanup duplicatas)

## Parecer

```text
[PARECER FINAL: HOTFIX P0 SALES NON-BLOCKING FALLBACK APROVADO]
```

Condição operacional: reiniciar API após deploy (`DEBUG=False`, 1 worker). Primeira requisição sem snapshot responde em ~8s (timeout live) + fallback; requisições seguintes com circuit OPEN + snapshot ideal <3s.
