# WEBPOSTO CONSOLIDATION PLAN — LOGOS SPACE
## Sprint A02.5 | Agente 2 — Integração

| Campo | Valor |
|---|---|
| **Cliente oficial** | `src/gateway/webposto_client.py` → `WebPostoClient` |
| **Alvo físico** | `src/integrations/webposto/client.py` |
| **Total clientes** | 7 (+ SDK legado) |
| **Data** | 2026-06-08 |

---

## Inventário de Clientes

| Classe | Localização | Consumidores | Status |
|---|---|---|---|
| `WebPostoClient` | `src/gateway/webposto_client.py` | analytics, fuel, network, produto, scripts auditoria | **OFICIAL** |
| `GatewayWebPostoClient` | `src/infrastructure/clients/gateway_webposto_client.py` | `gateway_expenses.py`, `fetch_expenses.py` | **DUPLICADO** |
| `WebPostoClient` | `src/webposto/client.py` | scripts legados, testes | **OBSOLETO** |
| `WebPostoClient` | `src/infrastructure/webposto/client.py` | `main_minimal.py`, `crud.py`, `sync_service.py` | **OBSOLETO** |
| `WebPostoAuditClient` | `src/infrastructure/clients/webposto_client.py` | `audit_tasks.py` | **OBSOLETO** |
| `WebPostoClient` | `logos-webposto-gateway/.../webposto_client.py` | subprojeto gateway | **DUPLICADO** |
| `httpx` inline | `src/presentation/app.py` | proxy Adelaide `/api/v1/proxy/*` | **OBSOLETO** |

### SDK legado (não HTTP, duplica integração)

| Diretório | Status |
|---|---|
| `src/webposto/endpoints/combustivel.py` | OBSOLETO |
| `src/webposto/endpoints/abastecimento.py` | OBSOLETO |
| `src/webposto/endpoints/produtos.py` | OBSOLETO |
| `src/webposto/endpoints/integracoes.py` | OBSOLETO |

---

## Capacidades do Cliente Oficial

- 26 endpoints em `ENDPOINTS` dict
- Circuit breaker (`SimpleCircuitBreaker`)
- Retry (`retry_async`)
- Permission discovery + cache
- Timeouts estendidos (≥20s) para rotas pesadas
- Métricas (`metrics_collector`)
- Contrato `WebPostoResponse`

---

## Plano de Consolidação

| Fase | Sprint | Ação | Esforço |
|---|---|---|---|
| 1 | A03 | Criar `src/integrations/webposto/client.py` (move oficial) | M |
| 2 | A03 | Absorver `GatewayWebPostoClient` (multi-posto + fallback despesas) | M |
| 3 | A03 | Atualizar imports em todos services 8040 | M |
| 4 | A04 | Substituir httpx inline em `presentation/app.py` | M |
| 5 | A04 | Remover clientes obsoletos + SDK `src/webposto/` | L |
| 6 | A05 | Arquivar `logos-webposto-gateway/` | M |

---

## Regras Oficiais

```python
# ÚNICO import permitido (após Fase 1)
from src.integrations.webposto.client import WebPostoClient
```

1. Proibido criar novo client HTTP fora de `integrations/webposto/`
2. Proibido httpx direto em routes (exceto gateway congelado até A04)
3. Novos endpoints WebPosto → registrar em `ENDPOINTS` dict
4. Retorno obrigatório: `WebPostoResponse`

---

*Agente 2 — sem alteração de código nesta sprint.*
