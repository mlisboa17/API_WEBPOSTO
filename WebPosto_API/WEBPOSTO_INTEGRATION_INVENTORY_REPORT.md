# IA-1 — WebPosto Integration Inventory

**Data:** 2026-06-13 · Branch `feature/webposto-unified-gateway`

## Clientes/wrappers existentes

| # | Arquivo | Papel |
|---|---------|-------|
| 1 | `src/gateway/webposto_client.py` | Cliente async principal (ENDPOINTS dict) |
| 2 | `src/infrastructure/clients/webposto_client.py` | Cliente infra legado |
| 3 | `src/infrastructure/clients/gateway_webposto_client.py` | Adapter gateway |
| 4 | `src/webposto/client.py` + `http.py` | SDK requests-based |
| 5 | `src/infrastructure/webposto/client.py` | Cliente infra alternativo |
| 6 | `logos-webposto-gateway/...` | Subprojeto paralelo |

**Total wrappers/clients:** **6 implementações** (+ **4 classes** WebPostoClient/HTTPClient)

## Endpoints alvo — ocorrências no código Python

| Endpoint | Referências |
|----------|-------------|
| `/INTEGRACAO/PRODUTO` | 120 |
| `/INTEGRACAO/VENDA` | 61 |
| `/INTEGRACAO/CONSULTAR_LMC_REDE` | 37 |
| `/INTEGRACAO/ABASTECIMENTO` | 34 |
| `/INTEGRACAO/VENDA_ITEM` | 27 |
| `/INTEGRACAO/PRODUTO_EMPRESA` | 20 |
| `/INTEGRACAO/PLANO_CONTA_GERENCIAL` | 13 |
| `/INTEGRACAO/NFCE` | 12 |
| `/INTEGRACAO/CONTA` | 12 |

## Duplicação

- Chamadas `/INTEGRACAO/*` espalhadas em **scripts/** (auditorias) e **src/services/** (motores)
- **3+ clientes** com lógica paralela de CHAVE, timeout e retry
- Paginação duplicada: `webposto_pagination.py` vs lógica inline em serviços

## Endpoints sem padrão unificado

- Tokens por filial no `.env` sem policy central
- `empresaCodigo` injetado de formas distintas por serviço
- Logs heterogêneos (alguns structured, outros print)

## Resposta IA-1

| Pergunta | Resposta |
|----------|----------|
| Wrappers existentes | **6 clientes / 4 classes** |
| Chamadas duplicadas | **Sim** — múltiplos clientes + scripts |
| Mais usados | **PRODUTO, VENDA, LMC_REDE** |
| Sem padrão | **Auth, empresaCodigo, logs, paginação** |
