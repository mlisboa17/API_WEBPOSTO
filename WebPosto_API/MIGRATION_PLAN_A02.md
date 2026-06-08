# LOGOS SPACE — Migration Plan A02
## Sprint A02 — Plano de Migração Arquitetural

| Campo | Valor |
|---|---|
| **Horizonte** | 12 meses |
| **Pré-requisito** | A01.1 Baseline + A02 Consolidação documental |
| **Princípio** | Migrar sem quebrar produção — strangler fig pattern |
| **Data** | 2026-06-08 |

---

## Visão Geral das Fases

```
A02 (agora)     A03           A04           B01..H03
Documentar  →  Snapshot   →  Data WH    →  Módulos negócio
               First Arch     Inicial
     │
     ├── FASE 1: Entrypoints
     ├── FASE 2: WebPosto Client
     ├── FASE 3: Analytics
     ├── FASE 4: Dashboards
     └── FASE 5: Snapshot First
```

---

## FASE 1 — Consolidação de Entrypoints

**Duração estimada:** 2 semanas  
**Risco:** Baixo (documental + config)

### Objetivo

1 entrada oficial: `src/main.py` porta 8040.

### Ações

| # | Ação | Tipo | Esforço |
|---|---|---|---|
| 1.1 | Adicionar `DEPRECATED.md` nos entrypoints legados | Doc | XS |
| 1.2 | Fixar porta 8040 no README e runbooks (separar 8050 gateway) | Doc | XS |
| 1.3 | Adicionar banner no startup de `presentation/app.py`: "GATEWAY AUXILIAR" | Código | S |
| 1.4 | Remover referências a `main_minimal.py` em scripts de deploy | Config | S |
| 1.5 | CI: validar que testes usam `create_app()` do 8040 | CI | M |
| 1.6 | Arquivar `src/main-mlisboa17.py` (mover para `_archive/`) | Código | XS |

### Critério de aceite

- [ ] Documentação aponta exclusivamente para `src/main.py:8040`
- [ ] Nenhum runbook referencia `main_minimal` ou `main-mlisboa17`
- [ ] CI roda contra `create_app()`

### Rollback

Reverter documentação; entrypoints legados continuam funcionais.

---

## FASE 2 — Consolidação WebPosto Client

**Duração estimada:** 3-4 semanas  
**Risco:** Médio (refactor imports)

### Objetivo

1 cliente oficial: `src/gateway/webposto_client.py`.

### Ações

| # | Ação | Tipo | Esforço |
|---|---|---|---|
| 2.1 | Criar `src/integrations/webposto/` (symlink ou move do gateway client) | Código | M |
| 2.2 | Migrar `GatewayWebPostoClient` → método `fetch_multi_posto()` no oficial | Código | M |
| 2.3 | Substituir import em `main_minimal.py` → oficial (ou deprecar minimal) | Código | S |
| 2.4 | Lint rule: proibir `from src.webposto.client import` | CI | S |
| 2.5 | Congelar `presentation/app.py` proxy — bugfix only | Processo | — |
| 2.6 | Solicitar expansão token Quality (paralelo, externo) | Negócio | — |

### Critério de aceite

- [ ] Zero imports de `src/webposto/client.py` em código ativo 8040
- [ ] `gateway_expenses.py` usa cliente oficial
- [ ] Testes de integração passam com cliente único

### Rollback

Manter clients legados em `_archive/`; reverter imports.

---

## FASE 3 — Consolidação Analytics

**Duração estimada:** 4-6 semanas  
**Risco:** Médio-alto (métricas sensíveis)

### Objetivo

1 engine por domínio; eliminar fluxos Adelaide/metrics duplicados.

### Ações

| # | Ação | Tipo | Esforço |
|---|---|---|---|
| 3.1 | Documentar contrato "Litros LMC" vs "Litros Vendidos" na UI | Doc+UI | S |
| 3.2 | Deprecar `/api/executive/kpis` (8050) → redirect `/api/v1/kpis` | Código | M |
| 3.3 | Deprecar `/metrics/executive` → usar snapshot | Código | S |
| 3.4 | Unificar normalização monetária (analytics + network) | Código | M |
| 3.5 | Mover agregação multiselect para backend (KPIs, DRE, fuel) | Código | L |
| 3.6 | Criar `src/analytics/` e mover engines | Código | L |
| 3.7 | Alinhar timeout fuels frontend (30s → 90s) | Código | XS |

### Critério de aceite

- [ ] KPIs do executive = KPIs do `/api/v1/kpis` (mesmo número)
- [ ] Apenas 1 fluxo de KPIs executivos ativo
- [ ] UI distingue "Litros LMC" vs "Litros Vendidos"

### Rollback

Manter engines legadas como fallback; feature flag.

---

## FASE 4 — Consolidação Dashboards

**Duração estimada:** 3-4 semanas  
**Risco:** Baixo (remoção de legado)

### Objetivo

1 dashboard oficial: SPA `frontend/` em `/app/financial`.

### Ações

| # | Ação | Tipo | Esforço |
|---|---|---|---|
| 4.1 | Adicionar redirect `/dashboard` (8050) → `/app/financial` | Código | S |
| 4.2 | Mover dashboards legados para `_archive/dashboards/` | Código | S |
| 4.3 | Atualizar `COMO_USAR_DASHBOARDS.md` → apontar SPA oficial | Doc | XS |
| 4.4 | Remover `ABRIR_DASHBOARDS.ps1` ou redirecionar para 8040 | Config | XS |
| 4.5 | Migrar funcionalidades úteis de `vendas-dashboard.html` → `sales.js` | Código | M |
| 4.6 | Congelar gateway UI (8050) — sem novas features | Processo | — |

### Critério de aceite

- [ ] Zero dashboards HTML acessíveis em produção exceto SPA
- [ ] `DASHBOARD_CATALOG.md` atualizado com status REMOVIDO
- [ ] Equipe usa exclusivamente `/app/financial`

### Rollback

Restaurar HTML de `_archive/`.

---

## FASE 5 — Snapshot First Architecture

**Duração estimada:** 4-6 semanas  
**Risco:** Médio (muda fluxo de dados)

### Objetivo

Dashboard sempre lê snapshot/cache primeiro; API externa somente em background.

### Ações

| # | Ação | Tipo | Esforço |
|---|---|---|---|
| 5.1 | Estender snapshot para view `fuels` (não só executive) | Código | M |
| 5.2 | Criar `FuelSnapshotService` (paralelo ao executive) | Código | M |
| 5.3 | Persistir sync logs em SQLite | Código | M |
| 5.4 | Fila de refresh com lock distribuído (ou file lock) | Código | M |
| 5.5 | Prewarm snapshot no startup (período default) | Código | S |
| 5.6 | Frontend: todas views usam snapshot-first pattern | Código | L |
| 5.7 | Deprecar chamadas diretas pesadas no render inicial | Código | M |

### Critério de aceite

- [ ] Abrir qualquer view → dados em < 3s (snapshot ou cache)
- [ ] Zero timeout visível na UI
- [ ] `lastUpdated` visível em todas views analíticas
- [ ] Refresh background não bloqueia UI

### Rollback

Feature flag `USE_SNAPSHOT_FIRST=false` → volta para chamadas diretas.

---

## Cronograma Consolidado

| Fase | Sprint alvo | Duração | Dependências |
|---|---|---|---|
| FASE 1 — Entrypoints | A02 (doc) + A03 (exec) | 2 sem | A01 baseline |
| FASE 2 — WebPosto | A03 | 3-4 sem | Fase 1 |
| FASE 3 — Analytics | A03-A04 | 4-6 sem | Fase 2 |
| FASE 4 — Dashboards | A04 | 3-4 sem | Fase 1 |
| FASE 5 — Snapshot First | A03 (parcial) + A04 | 4-6 sem | Fase 3 |

```
Mês 1:  FASE 1 + início FASE 2 + FASE 5 (executive já feito)
Mês 2:  FASE 2 completa + FASE 3 início + FASE 4
Mês 3:  FASE 3 completa + FASE 5 completa
Mês 4+: B01 Governança → C01 Financeiro → E01 Combustíveis
```

---

## Próximas Sprints (pós A02)

| Sprint | Foco | Fase |
|---|---|---|
| **A03** | Snapshot Architecture (Fase 5) + Entrypoints (Fase 1 exec) | Fundação |
| **A04** | Data Warehouse Inicial + Analytics consolidation (Fase 3) | Fundação |
| **B01** | Filiais — expansão token + cobertura | Governança |
| **E01** | Combustíveis — contrato LMC vs Vendas + rede completa | Vendas |
| **G01** | Executive Dashboard — snapshot estável rede | Gestão |

---

## Riscos da Migração

| Risco | Probabilidade | Impacto | Mitigação |
|---|---|---|---|
| Token não expandido pela Quality | Alta | Crítico | Plano B: tokens por filial |
| Regressão em KPIs durante consolidação | Média | Alto | Feature flags + testes comparativos |
| Equipe continua usando 8050 | Média | Médio | Redirect + comunicação |
| Remoção prematura de legados | Baixa | Alto | `_archive/` antes de delete |

---

## Aprovação

| Papel | Decisão | Data |
|---|---|---|
| CTO LOGOS SPACE | Plano aprovado para execução | 2026-06-08 |
| Próximo gate | A03 — início Fase 1 exec + Fase 5 extensão | — |

---

*Sprint A02 — plano de migração. Sem alteração de código nesta sprint.*
