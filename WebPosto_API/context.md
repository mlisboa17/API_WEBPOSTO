# Contexto do Projeto: Logos Postos (BI Executivo)

**Versão:** 3.6  
**Atualizado:** 2026-07-14  
**Repositório:** `WebPosto_API`  
**Fase:** FASE 1 / FASE 2 — Transição de Análise para Diagnóstico  
**Runtime:** `http://127.0.0.1:8046` · SPA `/app/financial`

> Documento oficial de governança, arquitetura C-Level e roadmap.  
> Base de leitura obrigatória para todas as sessões do Cursor Agent.

---

## 1. Visão do Produto & Referências de Mercado

- **Conceito:** BI Ativo C-Level e Gestão Estratégica alimentado pelo ERP WebPosto.
- **Benchmarks:** Inspirado nas visões consolidadas do Linx/WebPosto Gerencial e ClubPetro BI.
- **Premissa de Design:** Menos telas, mais inteligência. O presidente não caça o dado; o sistema aponta o desvio de margem ou gargalo de caixa e sugere a ação.
- **Escopo Proibido (Operacional):** Telas de bicos de bomba, turnos nominais, escalas de frentistas e paridade de PIX/dinheiro unitária.
- **Escopo Aprovado (Estratégico):** Visões consolidadas da rede, rankings de postos, evolução de margem e DRE gerencial.

### Regras de agregação (obrigatórias)

| Regra | Definição |
|-------|-----------|
| Visão rede | Faturamento e margem devem suportar agregação **multi-empresas** (rede consolidada) |
| Drill-down | Todo KPI deve permitir filtro por **filial** (`empresaCodigo`) |
| Granularidade mínima | Filial · combustível · natureza gerencial — nunca bico, turno ou operador |
| Filtros padrão | `dataInicial`, `dataFinal`, `empresaCodigo` |
| Dados | Runtime real — sem mock, sem seed |
| Arquitetura | Snapshot First (TTL ~300s) · FastAPI + SPA · `httpx` assíncrono |

---

## 2. Arquitetura de Navegação — As 3 Telas do Presidente

O produto se resume a **3 telas executivas**. Módulos auxiliares (evidência, conferência, acompanhamento) são suporte — não novas superfícies C-Level.

### Tela 1: Owner Action Center (Top 5 Decisions)

- **Rota UI:** `/app/financial?view=owner-diretoria`
- **Origem:** `/api/v1/owner-action-center/top5`, `/api/v1/discovery/top-5`
- **Finalidade:** Apresentar as 5 principais anomalias ou vazamentos de margem do dia que demandam intervenção direta da diretoria.

| Suporte | Rota | Papel |
|---------|------|-------|
| Evidência | `GET /api/v1/decisions/{id}/evidence` | Lançamentos, root cause, pergunta executiva |
| Conferência | `POST /api/v1/decisions/{id}/review-requests` | Encaminha validação ao Financeiro |
| Acompanhamento | `GET /api/v1/executive/follow-ups` | Progresso de decisões anteriores |
| Inbox Financeiro | `GET /api/v1/financial/review-inbox` | Caixa de trabalho da conferência |

**Hierarquia visual:** Prioridade da Rede → Próximas Decisões → Sinais em Observação → Em Acompanhamento.

---

### Tela 2: Cockpit Comercial & Precificação

- **Rota UI:** `/app/financial?view=fuelExecutive`
- **Origem:** `/api/v1/fuel/executive`, `/api/v1/sales/fuel-summary`
- **Finalidade:** Volume de litros, participação de mercado interna, margem média realizada, e comparação de Preço Médio de Compra (Distribuidora) vs Preço Médio de Venda na bomba por combustível.

| KPI | Origem complementar |
|-----|---------------------|
| Litros vendidos | `/v1/vendas-combustivel` |
| Preço médio compra | `/v1/abastecimento` |
| Margem / KPIs rede | `/api/v1/kpis` |
| Participação interna | `fuel/executive` → `participacao` |

Agregação obrigatória: **rede → filial → combustível**.

---

### Tela 3: DRE Executivo & Fluxo de Caixa

- **Rota UI:** `/app/financial?view=financialHub`
- **Origem:** `/api/v1/dre`, `/api/v1/finance/cash-flow`
- **Finalidade:** Demonstrativo de Resultado Gerencial estruturado da rede/posto, controle de evolução de despesas gerais e projeção de liquidez de curto prazo.

| Bloco | Origem complementar |
|-------|---------------------|
| Overview por posto | `/v1/financial/overview` |
| Despesas por natureza | `/v1/financial/expenses` |
| Contas a pagar | `/v1/financial/accounts-payable` |
| Fluxo diário/semanal/mensal | `/api/v1/finance/cash-flow/daily`, `/weekly`, `/monthly` |

**Regra de ouro:** nunca somar `totalFinanceiro` agregando DESPESA + CP + BANCO + CAIXA + CR.

---

## 3. Roadmap de Sprints & Governança do Git

### Sprint 1: Consolidação da Camada de Dados (FASE 1 / 2 Atual)

- **Escopo:** Limpeza de rotas operacionais do gateway, mapeamento fino dos payloads de vendas/financeiro do WebPosto e auditoria de cache.
- **Entregas:** Inventário de endpoints · filtro C-Level · contrato unificado de filtros · degradação elegante em `/v1/financial/*`.
- **Valor Presidência:** Base confiável — dados certos, rápidos, sem ruído de pista.
- **Commit Padrão:** `feat(sprint-1/infra): encerramento da sprint 1 com higienizacao do front e blindagem de cache`
- **Status:** ✅ **Concluída**

#### Ações realizadas (2026-07-12)

| Ação | Detalhe |
|------|---------|
| Reorganização `app.py` | Barramento dividido em `_mount_core`, `_mount_executive_barramento`, `_mount_executive_support`, `_mount_operational_deprecated` |
| Barramento C-Level ativo | Tela 1: `owner-action-center`, `discovery`, `decisions`, `follow-ups`, `review-inbox` |
| Barramento C-Level ativo | Tela 2: `analytics` (`/fuel/executive`, `/sales/fuel-summary`, `/kpis`), `fechamento_enterprise` |
| Barramento C-Level ativo | Tela 3: `analytics` (`/dre`), `cash-flow`, `finance_center`, `/v1/financial/*` |
| Rotas operacionais isoladas | `cash/operations`, `performance`, `operator-intelligence`, `people-intelligence`, `people-roi`, `operation-roi` — **desmontadas** (`ENABLE_OPERATIONAL_ROUTES=false`) |
| Código preservado | Módulos operacionais intactos; apenas exposição HTTP desligada na camada de roteamento |
| Multitenancy | Contratos executivos mantêm `empresaCodigo` + visão rede via `analytics` e `fechamento_enterprise` |
| Higienização frontend | `frontend/services/api.js` — funções operacionais retornam payloads vazios seguros (`DEPRECATED - OPERATIONAL`) |
| Cache snapshots | TTL unificado 300s em `snapshot_ttl.py`; metadados `cacheHit`/`stale`/`ttlSeconds` em `/executive/snapshot` e `/fuel/snapshot` |
| Degradação financeira | `FinancialResilienceService` cobre `overview`, `expenses`, `accounts-payable`, `accounts-receivable`, `companies` |

#### Pendente (fora do escopo Sprint 1)

- Documentar contrato fino de payloads WebPosto em `docs/validation/` (Sprint 2+)

---

### Sprint 2: Motor de Descoberta Executive (Top 5)

- **Escopo:** Engenharia do algoritmo de priorização de anomalias com base em perdas financeiras e impacto em margem.
- **Entregas:** Detectores · `priority_score` · hierarquia UI · evidência + conferência · teste 15s + Playwright.
- **Valor Presidência:** Responde em 15s: o que está errado, onde, quanto e o que fazer primeiro.
- **Commit Padrão:** `feat(sprint-2/intelligence): algoritmo de priorizacao do top 5 de decisoes`
- **Status:** ✅ **Concluída**

#### Ações realizadas (2026-07-12 — 2026-07-14)

| Ação | Detalhe |
|------|---------|
| `/discovery/explain/{id}` | Mock removido — resolve candidato real via `DecisionEvidenceService` + `RootCauseEngine` |
| Contratos WebPosto | `docs/validation/DISCOVERY_WEBPOSTO_PAYLOAD_CONTRACTS.md` — mapeamento por detector |
| Testes explain | `tests/unit/test_discovery_explain_endpoint.py` — snapshot real + 404 |
| **Multi-tenant Discovery** | `DiscoveryScopeService` — portfólio via `TenantDiscoveryService`; sem default `vip` |
| Escopo snapshot | Busca indexada por `empresaCodigo` / rede (`all`); cross-tenant → `403`/`404` |
| Rotas `/discovery/*` | `discover_all_tenants` filtrado pelo portfólio autorizado |
| **`business-health` real** | `OwnerBusinessHealthService` — score 100 − deduções ponderadas por anomalias ativas |
| **`MarginDetector`** | Compara preço compra (abastecimento) vs venda vs meta do scorecard |
| Testes score/margem | `test_business_health_score.py`, `test_margin_detector.py` — 16 passed |

#### Pendente Sprint 2

- _(nenhum — sprint encerrada)_

---

### Sprint 3: Cockpit Financeiro & DRE Estratégico

- **Escopo:** Interface e consolidação das visões de fluxo de caixa gerencial, despesas e faturamento macro.
- **Entregas:** DRE por rede/posto · cash-flow integrado · resiliência UI (skeleton/retry) · inbox de conferências.
- **Valor Presidência:** Visão única da saúde financeira — margem, despesas e liquidez sem planilhas.
- **Commit Padrão:** `feat(sprint-3/financeiro): unificacao de endpoints de despesas e visualizacao de dre`
- **Status:** ✅ **Concluída**

#### Ações realizadas (2026-07-14)

| Ação | Detalhe |
|------|---------|
| **`/api/v1/dre`** | Estrutura gerencial: faturamentoBruto, deduções, margemContribuicao, despesasOperacionais, porFilial |
| **`/api/v1/finance/cash-flow`** | `semanticBreakdown` com despesas/receitas semânticas + séries daily/weekly/monthly consolidadas |
| Agregação multiselect | `_aggregate_dre` preserva campos gerenciais na visão rede |

---

### Sprint 4: Painel Comercial Dinâmico & Margens

- **Escopo:** Interface executiva de litragem, precificação e elasticidade de margem de combustíveis.
- **Entregas:** Cockpit combustível · benchmark entre filiais · paridade compra/venda · alertas de outlier.
- **Valor Presidência:** Identifica perda de margem antes do fechamento do mês.
- **Commit Padrão:** `feat(sprint-4/comercial): visualizacao executiva de combustiveis e precificacao`
- **Status:** ✅ **Concluída**

#### Ações realizadas (2026-07-14)

| Ação | Detalhe |
|------|---------|
| **`/api/v1/fuel/executive`** | `FuelPricingService` — litros × preço médio compra (abastecimento) vs venda por combustível |
| **`paridadePrecos`** | Bloco `paridadePrecos` + KPIs `precificacao` sem alterar contrato existente do cockpit |
| Enriquecimento combustíveis | `precoMedioCompra`, `precoMedioVenda`, `margemRealizadaPct` por item em `combustiveis` |

---

## 4. Protocolo de Engenharia

- Commits obrigatoriamente atômicos e isolados por entrega de Sprint seguindo o padrão definido.
- Ao término de cada Sprint, este arquivo deve ser atualizado com o status de progresso das tarefas.

### Padrão de commit

```
<tipo>(sprint-X/<modulo>): <mensagem curta no imperativo>
```

| Tipo | Uso |
|------|-----|
| `feat` | Entrega funcional da sprint |
| `fix` | Correção |
| `docs` | Atualização de `context.md` |
| `test` | Evidências runtime |
| `refactor` | Refatoração sem mudança de comportamento |

### Regras adicionais

- Não versionar `.env`, segredos, `__pycache__`, snapshots locais
- Registrar evidências em `docs/validation/` ao fechar sprint
- Débito técnico: `docs/follow-up/TECH_DEBT_POST_FIN02.md`
- Preferir `httpx` assíncrono · logs detalhados em falhas WebPosto · reutilizar snapshots existentes

---

## Changelog

| Data | Versão | Alteração |
|------|--------|-----------|
| 2026-07-14 | 3.6 | Sprints 2–4 concluídas — business-health, MarginDetector, DRE gerencial, cash-flow semântico, paridade preços |
| 2026-07-13 | 3.5 | Sprint 2 — isolamento multi-tenant rigoroso em `/discovery/*` |
| 2026-07-12 | 3.4 | Sprint 2 em progresso — `/discovery/explain` com snapshot real + contratos payload |
| 2026-07-12 | 3.3 | Sprint 1 concluída — front higienizado, cache TTL 300s, degradação `/v1/financial/*` |
| 2026-07-12 | 3.2 | Sprint 1 em progresso — barramento C-Level em `app.py`, rotas operacionais isoladas |
