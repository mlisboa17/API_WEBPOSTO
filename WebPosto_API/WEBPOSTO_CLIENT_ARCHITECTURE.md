# LOGOS SPACE — WebPosto Client Architecture
## Sprint A02 — Padronização Oficial

| Campo | Valor |
|---|---|
| **Cliente oficial** | `src/gateway/webposto_client.py` → `WebPostoClient` |
| **Consumidores oficiais** | `analytics.py`, `fuel_analytics_service.py`, `network_financial_overview_service.py`, `produto_catalog.py` |
| **Data** | 2026-06-08 |

---

## 1. Resumo

| Pergunta | Resposta |
|---|---|
| Quantos clientes existem? | **7 implementações** (+ SDK legado `src/webposto/endpoints/`) |
| Qual é o oficial? | `src/gateway/webposto_client.py` |
| Quais estão duplicados? | 4 variantes `WebPostoClient` + 1 `GatewayWebPostoClient` + subprojeto |
| Quais estão obsoletos? | `src/webposto/client.py`, `src/infrastructure/webposto/client.py`, SDK endpoints |

---

## 2. Inventário Completo

| # | Arquivo | Classe | Usado por | Status Atual | Status Futuro |
|---|---|---|---|---|---|
| 1 | `src/gateway/webposto_client.py` | `WebPostoClient` | Analytics 8040, fuel, network, produto | **Ativo** | **OFICIAL** |
| 2 | `src/webposto/client.py` | `WebPostoClient` | SDK legado, scripts | Inativo 8040 | **DEPRECATED** |
| 3 | `src/infrastructure/webposto/client.py` | `WebPostoClient` | `main_minimal.py` | Inativo 8040 | **DEPRECATED** |
| 4 | `src/infrastructure/clients/webposto_client.py` | `WebPostoAuditClient` | Auditoria infra | Inativo 8040 | **DEPRECATED** |
| 5 | `src/infrastructure/clients/gateway_webposto_client.py` | `GatewayWebPostoClient` | `gateway_expenses.py` (multi-posto) | Ativo parcial | **DEPRECATED** → absorver no oficial |
| 6 | `logos-webposto-gateway/src/infrastructure/webposto_client.py` | `WebPostoClient` | Subprojeto gateway | Paralelo | **REMOVER FUTURAMENTE** |
| 7 | `src/presentation/app.py` (inline) | `httpx` direto + proxy | Gateway Adelaide | Ativo 8050 | **DEPRECATED** |

### SDK legado (não é client HTTP, mas duplica integração)

| Diretório | Conteúdo | Status Futuro |
|---|---|---|
| `src/webposto/endpoints/combustivel.py` | PEDIDO_COMBUSTIVEL, LMC, APRIX | **REMOVER FUTURAMENTE** |
| `src/webposto/endpoints/abastecimento.py` | ABASTECIMENTO wrapper | **REMOVER FUTURAMENTE** |
| `src/webposto/endpoints/produtos.py` | 15+ rotas CRUD | **REMOVER FUTURAMENTE** |
| `src/webposto/endpoints/integracoes.py` | VENDA, NF, etc. | **REMOVER FUTURAMENTE** |

---

## 3. Cliente Oficial — Capacidades

**Arquivo:** `src/gateway/webposto_client.py`

| Capacidade | Implementação |
|---|---|
| Endpoints mapeados | 26 chaves em `ENDPOINTS` dict |
| Circuit breaker | `SimpleCircuitBreaker` |
| Retry | `retry_async` |
| Permission discovery | `permission_cache` + `discover_permissions` |
| Timeouts estendidos | ≥20s para rotas pesadas (lmc_rede, venda*, estoque) |
| Métricas | `metrics_collector` por latência/401 |
| Logging estruturado | `log_structured` |
| Response padronizado | `WebPostoResponse` (success/data/error) |

### Endpoints mapeados (combustíveis destacados)

| Chave | Path WebPosto | Uso |
|---|---|---|
| `lmc_rede` | `/INTEGRACAO/CONSULTAR_LMC_REDE` | **Fuel executive** |
| `venda_item` | `/INTEGRACAO/VENDA_ITEM` | Fuel-summary comercial |
| `venda_item_rede` | `/INTEGRACAO/CONSULTAR_VENDA_ITEM_REDE` | KPIs (401 atual) |
| `analise_vendas_combustivel` | `/INTEGRACAO/CONSULTAR_ANALISE_VENDAS_COMBUSTIVEL` | Vendas combustível |
| `produto` | `/INTEGRACAO/PRODUTO` | Catálogo |
| `produto_combustivel` | `/INTEGRACAO/PRODUTO_COMBUSTIVEL` | 401 atual |
| `abastecimento` | `/INTEGRACAO/ABASTECIMENTO` | Operação |
| `tanque` | `/INTEGRACAO/TANQUE` | Tanques |
| `despesas_financeiro_rede` | `/INTEGRACAO/CONSULTAR_DESPESAS_FINANCEIRO_REDE` | Despesas rede |
| `empresas` | `/INTEGRACAO/EMPRESAS` | Governança filiais |

---

## 4. Diagrama Alvo

```
┌─────────────────────────────────────────────────────────┐
│                    LOGOS SPACE API 8040                  │
├─────────────────────────────────────────────────────────┤
│  analytics/          governance/         enterprise/     │
│  ├── kpi_engine      ├── filial_master   ├── expenses   │
│  ├── fuel_engine     └── produto_catalog └── sales      │
│  └── snapshot_service                                    │
├─────────────────────────────────────────────────────────┤
│           src/integrations/webposto/client.py            │
│           (único ponto de contato HTTP)                  │
├─────────────────────────────────────────────────────────┤
│           WebPosto Quality API (HTTPS)                   │
│           web.qualityautomacao.com.br                    │
└─────────────────────────────────────────────────────────┘
```

---

## 5. Plano de Consolidação

| Fase | Ação | Esforço |
|---|---|---|
| 1 | Documentar `gateway/webposto_client.py` como único import permitido | Baixo |
| 2 | Migrar `GatewayWebPostoClient` (multi-posto) para método no oficial | Médio |
| 3 | Remover imports de `src/webposto/client.py` e `infrastructure/webposto/client.py` | Médio |
| 4 | Deprecar proxy httpx inline em `presentation/app.py` | Alto |
| 5 | Arquivar subprojeto `logos-webposto-gateway/` | Alto |
| 6 | Remover SDK `src/webposto/endpoints/` após validação | Alto |

---

## 6. Regras Oficiais (a partir de A02)

1. **Proibido** criar novo client HTTP para WebPosto fora de `integrations/webposto/`
2. **Obrigatório** usar `WebPostoResponse` como contrato de retorno
3. **Obrigatório** registrar novos endpoints no dict `ENDPOINTS`
4. **Proibido** chamar httpx direto em routes (exceto gateway 8050 até deprecação)
5. Timeouts pesados: configurar em `ENDPOINTS` com override ≥20s

---

*Sprint A02 — documento de padronização. Sem alteração de código.*
