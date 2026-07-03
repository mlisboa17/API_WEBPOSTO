# BUILD-03B — Multi-Tenant Discovery Trace

Data: 2026-07-03  
Modo: auditoria com runtime real (sem mocks)

## FASE 1 — Credenciais no ambiente

| environment_variable_name | credential_present | masked_token | credential_source | consumer |
|---|---|---|---|---|
| WEBPOSTO_API_KEY | true | ****8fd7 | `.env` | `load_core_config()` fallback legacy |
| WEBPOSTO_API_KEY_POSTO_VIP_RIO_DOCE | true | ****8fd7 | `.env` | `OFFICIAL_WEBPOSTO_TOKEN_ENV_KEYS[0]` |
| WEBPOSTO_API_KEY_POSTO_CASA_CAIADA | true | ****53a8 | `.env` | `OFFICIAL_WEBPOSTO_TOKEN_ENV_KEYS[1]` |
| WEBPOSTO_API_KEY_POSTO_DOZE_FILIAL_II | true | ****43c1 | `.env` | `OFFICIAL_WEBPOSTO_TOKEN_ENV_KEYS[2]` |
| WEBPOSTO_API_KEY_POSTO_VIP | true | ****8fd7 | `.env` | duplicata do VIP (deduplicada) |
| WEBPOSTO_API_KEY_CASA_CAIADA | true | ****53a8 | `.env` | alias legado (não entra em OFFICIAL keys) |
| WEBPOSTO_TENANT_PRIMARY | true | POSTO_VIP | `.env` | documentação/legado — **não usado pelo Discovery** |
| WEBPOSTO_TENANT_SECONDARY | true | CASA_CAIADA | `.env` | documentação/legado — **não usado pelo Discovery** |

Respostas objetivas:

1. **Quantas credenciais WebPosto existem?** 3 valores únicos carregados (`webposto_api_keys.count = 3`).
2. **Quais classes carregam?** `src/core/config.py`, `src/core/webposto_credentials.py`, `src/infrastructure/config/settings.py`, `WebPostoClient`.
3. **Todas são carregadas?** Sim, as 3 oficiais deduplicadas por valor.
4. **Existe credencial default?** `primary_key = official_keys[0]` (VIP Rio Doce) — usada só como fallback legacy.
5. **Fallback silencioso para POSTO VIP?** **Sim (antes da correção):** `owner_action_center.py` fazia `empresaCodigo or "vip"` e frontend enviava `DEFAULT_TENANT=11495`.
6. **Variável que sobrescreve?** Frontend `empresaCodigo=11495` limitava análise a 1 tenant mesmo com 3 tokens.
7. **Settings modela múltiplas credenciais?** Sim (`webposto_api_key_posto_*`).
8. **Runtime recebia 3 configurações?** Tokens sim; pipeline de análise **não** — executava 1 tenant.

## FASE 2 — Trace do pipeline (causa raiz)

```
.env (3 tokens)
  ↓ INPUT: 3 api_keys | OUTPUT: CoreConfig.webposto_api_keys=(3,)
Settings / Config
  ↓ INPUT: OFFICIAL_WEBPOSTO_TOKEN_ENV_KEYS | OUTPUT: 3 credenciais deduplicadas
Frontend useHomeData
  ↓ INPUT: DEFAULT_TENANT.code=11495 | OUTPUT: GET /top5?empresaCodigo=11495
Owner Action Center (ANTES)
  ↓ INPUT: empresaCodigo=11495 | OUTPUT: tenant_code="11495", tenant_count=1
DecisionDiscoveryEngine.discover(tenant_code)  ← single-tenant
  ↓ INPUT: 1 tenant | OUTPUT: 1 execução FuelRevenueDetector
FuelRevenueDetector
  ↓ INPUT: tenant_code=11495 | OUTPUT: fuel-summary filtrado por empresaCodigo=11495
analysis_proof
  ↓ OUTPUT: tenant_count=1, tenant_ids=["11495"]
Home NORMAL
  ↓ "1 posto analisado"
```

**Ponto exato onde 3 viravam 1:**

| Camada | Arquivo | Linha/comportamento |
|---|---|---|
| Frontend | `NewWebLogos/.../useHomeData.ts` | Enviava `empresaCodigo=11495` |
| Owner Action Center | `owner_action_center.py` | `tenant_code = empresaCodigo or "vip"` + `engine.discover()` único |
| Discovery Engine | `discovery_engine.py` | `discover(tenant_code: str)` — sem loop multi-tenant |
| analysis_proof | `owner_action_center.py` | `tenant_count: 1` hardcoded |

## FASE 3 — FuelRevenueDetector

| # | Pergunta | Resposta |
|---|---|---|
| 1 | Recebe tenant_id? | Sim, via `tenant_code` |
| 2 | Recebe lista de tenants? | Não (antes); loop feito pelo engine (depois) |
| 3 | Descobre tenants? | Não |
| 4 | Default tenant? | Herdava `"vip"` do router |
| 5 | empresaCodigo hardcoded? | Não no detector; vem do parâmetro |
| 6 | "vip" hardcoded? | No router, não no detector |
| 7 | 11495 hardcoded? | Não no detector; vinha do frontend |
| 8 | Fallback primeiro tenant? | Fallback `"vip"` no router |
| 9 | Executa 1x ou Nx? | 1x por chamada `discover()` |
| 10 | Mesmo client para todos? | Sim — `WebPostoClient()` merge de todas as keys |
| 11 | fuel-summary exige empresaCodigo? | Sim, via `FinancialOverviewFilters.empresa_codigo` |
| 12 | empresaCodigo enviado | O `tenant_code` recebido (11495 no runtime antigo) |
| 13 | Chamadas /fuel-summary | 2 por tenant (período atual + anterior) |

**Correção BUILD-03B:** client isolado por credencial (`WebPostoClient.for_api_key`) + log `DISCOVERY_TENANT_TRACE`.

## FASE 4 — DecisionDiscoveryEngine

| Pergunta | Resposta |
|---|---|
| Quem descobre tenants? | **Antes:** ninguém. **Depois:** `TenantDiscoveryService` |
| Quem itera tenants? | **Antes:** ninguém. **Depois:** `discover_all_tenants()` |
| Engine tenant-aware? | **Antes:** não. **Depois:** sim |
| BaseDetector TenantContext? | Não existe classe; contexto via kwargs |
| DecisionCandidate tenant_id? | Campo `tenant` + `tenant_name` |
| Priority Score global? | Sim — candidatos de todos os tenants competem |
| analysis_proof agrega tenants? | **Depois:** sim, campo `tenants[]` |

## FASE 5 — Descoberta automática

**Existia:** `fetch_unidade_webposto.py` (1 empresa por chave), `PostoAPIClient.listar_filiais()`, `GatewayCredentialsRepository` (DB).

**Não existia:** `TenantRegistry`, `TenantDiscoveryService`, loop no Discovery Engine.

**Implementado (mínimo):** `TenantDiscoveryService` + `list_webposto_credentials()` — descobre via `/INTEGRACAO/EMPRESAS` por credencial, sem lista fixa de códigos.

## FASE 6 — Correção arquitetural

1. `TenantDiscoveryService.discover_tenants()` — EMPRESAS por credencial
2. `DecisionDiscoveryEngine.discover_all_tenants()` — loop sequencial por tenant
3. `owner_action_center.py` — omitir `empresaCodigo` = todos os postos
4. `WebPostoClient.for_api_key()` — isolamento por credencial
5. Frontend — Home sem `empresaCodigo` fixo

## FASE 7 — Isolamento

- Cliente WebPosto isolado por tenant via credencial mapeada
- `FinancialOverviewFilters.empresa_codigo` segrega dados por filial
- Cache React Query: `queryKey: ['home', 'all-tenants']`

## FASE 10 — BUILD-03 vs BUILD-03A (candidatos R$ 4.200 / 72%)

Comparação objetiva:

| Fator | BUILD-03 | BUILD-03A (pré-03B) |
|---|---|---|
| Tenant | Provavelmente 11495 only | 11495 only (confirmado) |
| Período | Pode diferir | 2026-06-26 a 2026-07-03 |
| Threshold decisão | 80% / R$ 5.000 | 80% / R$ 5.000 |
| Candidatos abaixo threshold | Exibidos como decisão? | Rejeitados → observations |

**Causa mais provável (evidência):** **C)** tenant limitado a VIP + **B)** período/dataset real sem queda ≥ R$ 5.000 no período atual. Os valores R$ 4.200 e 72% seriam **observations**, não decisions — e só aparecem se houver queda detectável no ERP.

## FASE 11 — Performance

- Execução **sequencial** por tenant (integridade > paralelismo cego)
- Estimativa: ~60–120s × N tenants
- Paralelização não habilitada — rate limits e isolamento de client não auditados para concorrência

## Correção aplicada — resumo

**Causa raiz:** pipeline single-tenant iniciado no frontend (`empresaCodigo=11495`) e no router (`discover()` único), sem descoberta automática de tenants.

**Pergunta final:** Após BUILD-03B, o Discovery Engine investiga todos os postos descobertos via EMPRESAS antes de escolher a decisão global — ver runtime em `BUILD_03B_RUNTIME_REPORT.md` (gerado após teste real).
