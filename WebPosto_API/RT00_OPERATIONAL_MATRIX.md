# RT00_OPERATIONAL_MATRIX — IA-8

**Data:** 2026-06-14 | **Ambiente:** API 8050, período homologado 2026-06-01→2026-06-07

## Matriz por domínio

| Domínio | Telas | APIs core | Snapshots | Fluxo | **Status final** |
|---|---|---|---|---|---|
| **Financeiro F08** | 14 | `/v1/financial/*` + F08 centers | 18 arq. financial | 2 completos, resto parcial | **PARCIAL** |
| **Combustíveis** | 6 | `/v1/sales`, `/v1/stock`, fuel API | fuel_governance | Live lento, P0 sales | **PARCIAL** |
| **Produtos Vendidos F07** | 4 | non-fuel + commercial-* | 20 arq. | Cockpit OK | **PARCIAL** |
| **Fiscal F06** | 3 | nfce + fiscal-* | 7 arq. | Snapshot read OK | **PARCIAL** |
| **Executivo F04–F05** | 12+ | 15 routers | 19+ arq. executive | Snapshot read | **PARCIAL** |
| **People/Ops F04** | 5 motors | performance, people-* | operator_* | Motor strip | **PARCIAL** |
| **Administração** | 1 | circuit-breaker admin | — | Placeholder UI | **PARCIAL** |
| **Gateway legado** | 0 | presentation/app | — | Duplicata 8050 | **OBSOLETO** |
| **Auth/Sync/Clientes** | 0 | `/auth`, `/sync` | — | Sem UI | **OBSOLETO** |

## Matriz por camada

| Camada | OPERACIONAL | PARCIAL | QUEBRADO | OBSOLETO |
|---|---|---|---|---|
| UI shell | 1 entry | 40 views | 0 | — |
| API snapshot cockpits | 13 | 2 | 0 | — |
| API live `/v1` | 0 | 5 | 0 | — |
| Snapshots disco | 18 kinds | 14 kinds | 0 | 10 kinds |
| Serviços F03–F08 | 2 centros | 30+ engines | 0 | 5+ legado |

## Sub-sistemas OPERACIONAIS (elegíveis RT-01)

1. Financial Operations Center (F08.3)
2. Financial Intelligence Center (F08.4)
3. Snapshot health + circuit admin (F08.1/F08.0)

## Sub-sistemas PARCIAL (RT-01 com ressalva)

- Despesas/vendas com hotfix resilience
- Produtos vendidos cockpits F07
- Fiscal snapshot cockpits F06
- Executivo scorecard/workspace

## Sub-sistemas OBSOLETO (ignorar RT-01)

- `src/presentation/app.py`
- `logos-webposto-gateway/`
- Views financialMonitoring / financialOperations (legado)
- F05 IA generativa (copilot, recommendations, learning)
- Rotas auth/sync/clientes sem UI

---

## Respostas executivas (20 perguntas)

| # | Pergunta | Resposta |
|---|---|---|
| 1 | Quantas telas existem? | **40 views** + 41 módulos page JS, 1 URL base |
| 2 | Quantas carregam sem erro? | **40/40 shell** OK; dados: 2 OPERACIONAL, 38 PARCIAL |
| 3 | Quantas APIs funcionam? | **~13/18 probe OK**; ~220 endpoints código; cockpits snapshot dominam |
| 4 | Módulos operacionais? | **0 pleno OPERACIONAL**; **6 domínios PARCIAL** |
| 5 | Dashboards acessíveis? | **42** (todas as views); **2** com dados confiáveis <3s |
| 6 | Snapshots ativos? | **18 kinds ATIVO**, 167 arquivos total |
| 7 | Fluxos quebrados? | **0 shell**; live `/v1` e fuel-summary **PARCIAL** |
| 8 | Telas fantasma? | **Sim** — monitoring/operations legado, motors ocultos |
| 9 | APIs órfãs? | **Sim** — auth, sync, clientes, data-trust, statements, metrics |
| 10 | Dashboards abandonados? | **Sim** — F05 IA (copilot, recommendations, learning) |
| 11 | Funcionalidade sem uso? | **Sim** — closed-loop, autonomous rec, gateway legado |
| 12 | Código morto? | **Sim** — presentation/app, gateway subprojeto, /expenses legado |
| 13 | Financeiro operacional? | **PARCIAL** — F08 centers OK; live `/v1` com fallback |
| 14 | Produtos Vendidos operacional? | **PARCIAL** — cockpits snapshot OK |
| 15 | Combustíveis operacional? | **PARCIAL** — sales P0 OK; fuels/stock live lento |
| 16 | Fiscal operacional? | **PARCIAL** — snapshot cockpits OK |
| 17 | Administração operacional? | **PARCIAL** — placeholder, só circuit admin API |
| 18 | Sistema utilizável hoje? | **PARCIAL** — homologado 2026-06-01→07 com snapshots |
| 19 | Entra na RT-01? | F08 centers, F07/F06 cockpits, despesas/vendas c/ hotfix |
| 20 | Ignorar nos testes? | Gateway legado, F05 IA, auth/sync, monitoring/operations UI legado |

---

## Parecer

```text
[PARECER FINAL: RT-00 INVENTÁRIO OPERACIONAL CONCLUÍDO]
```

**Síntese:** O LOGOS SPACE tem **amplo código** (~44 routers, 167 snapshots, 40 views) mas **uso operacional concentrado** em cockpits snapshot read-only (F08.3/F08.4) e engines F06/F07. Live WebPosto via `/v1` permanece **PARCIAL** mesmo com hotfixes P0. Desenvolvimento pausado corretamente — RT-01 deve focar apenas itens **OPERACIONAL/PARCIAL homologados**.

**Script de revalidação:** `python scripts/audit_rt00_operational_inventory.py`
