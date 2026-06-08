# ENTRYPOINT MIGRATION — LOGOS SPACE
## Sprint A02.5 | Agente 1 — Arquitetura Backend

| Campo | Valor |
|---|---|
| **Total entrypoints** | 8 |
| **Oficial** | `src/main.py` (porta 8040) |
| **Data** | 2026-06-08 |

---

## Tabela de EntryPoints

| Arquivo | Responsabilidade | Dependências | Status Atual | Status Futuro |
|---|---|---|---|---|
| `src/main.py` | Launcher produção API Financeira LOGOS SPACE | `src.interfaces.http.app:create_app` | Ativo — porta 8040 | **OFICIAL** |
| `src/interfaces/http/app.py` | Factory `create_app()` — routers, CORS, DB startup | `routes/*`, `settings`, `init_db` | Ativo | **OFICIAL** (factory) |
| `main.py` (raiz) | Wrapper Docker/CLI → `src.main:app` | `uvicorn`, env `API_PORT` | Ativo | **OFICIAL** (launcher) |
| `src/presentation/app.py` | Gateway Adelaide — proxy, UI estática, CRUD legado | `build_adelaide_metrics`, Valkey, httpx | Ativo — porta 8050 | **DEPRECATED** |
| `logos-webposto-gateway/src/main.py` | Subprojeto gateway duplicado | bootstrap, presentation routes | Paralelo — 8050 | **REMOVER FUTURAMENTE** |
| `explorador_standalone.py` | Explorador técnico WebPosto (sem DB) | `explorador_catalog`, FastAPI inline | Experimental | **REMOVER FUTURAMENTE** |
| `src/main_minimal.py` | Sync + CRUD + enterprise minimal | `routes_crud`, `fechamento_enterprise` | Inativo prod | **REMOVER FUTURAMENTE** |
| `src/main-mlisboa17.py` | Variante pessoal desenvolvedor | Similar `src/main.py` | Inativo | **REMOVER FUTURAMENTE** |

---

## Routers Montados por Entrypoint

### OFICIAL — `create_app()` (8040)

| Prefixo | Router | Arquivo |
|---|---|---|
| `/health`, `/ready` | health | `routes/health.py` |
| `/v1` | fechamento_enterprise | `routes/fechamento_enterprise.py` |
| `/api/v1` | analytics | `routes/analytics.py` |
| `/v1/expenses` | gateway_expenses | `routes/gateway_expenses.py` |
| `/expenses` | expenses | `routes/expenses.py` |
| `/clientes` | clientes | `routes/clientes.py` |
| `/sync` | sync | `routes/sync.py` |
| `/auth` | auth | `routes/auth.py` |
| `/metrics` | metrics | `routes/metrics.py` |
| `/app/financial` | frontend SPA | `app.py` (FileResponse) |
| `/frontend/*` | StaticFiles | `frontend/` |

### DEPRECATED — `presentation/app.py` (8050)

| Grupo | Rotas |
|---|---|
| Routers dinâmicos | auth, metrics, clientes, sync, expenses |
| CRUD legado | `routes_crud.py` |
| Auditoria | `audit_routes.py`, `auditoria.py` |
| Adelaide | `/api/v1/adelaide/*` |
| Proxy | `/api/v1/proxy/*`, `/api/webposto/proxy` |
| KPIs legado | `/api/executive/kpis` |
| UI | `/dashboard`, `/produtos`, `/app/vendas`, `/` |

### NÃO MONTADOS no 8040 (órfãos)

| Arquivo | Status Futuro |
|---|---|
| `routes/auditoria.py` | DEPRECATED → analytics |
| `src/routes_crud.py` | REMOVER FUTURAMENTE |

---

## Ações de Migração

| Fase | Ação | Tipo |
|---|---|---|
| A02.5 | Documentar oficial = 8040 em README/runbooks | Doc |
| A03 | Banner DEPRECATED no startup 8050 | Doc |
| A03 | CI valida testes contra `create_app()` | CI |
| A04 | Redirect 8050 → 8040 para rotas equivalentes | Config |
| A04 | Arquivar `main_minimal`, `main-mlisboa17` | Cleanup |
| A05 | Remover subprojeto `logos-webposto-gateway/` | Cleanup |

---

*Agente 1 — sem alteração de código nesta sprint.*
