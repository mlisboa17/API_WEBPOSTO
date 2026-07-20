# Frontend Runtime Ownership Audit — FIN-02 gate

Data: 2026-07-07

## Perguntas respondidas

| # | Pergunta | Resposta |
|---|----------|----------|
| 1 | Por que Diretoria/FIN-01 está em `WebPosto_API/frontend`? | É o **frontend oficial** documentado no runbook; SPA Vanilla JS servida pelo FastAPI na mesma porta da API (8040). |
| 2 | Qual frontend abre para o usuário hoje? | `http://127.0.0.1:8040/app/financial` → `WebPosto_API/frontend/index.html` |
| 3 | Qual contém a jornada executiva validada? | `WebPosto_API/frontend` — `owner-diretoria`, `executive-follow-up`, `financial-review-inbox` |
| 4 | NewWebLogos está ativo/abandonado? | **Divergente + incompleto** — monorepo Next.js experimental (Home do dono, 2 rotas); **sem** fluxos FIN-01/Diretoria |
| 5 | Duas aplicações concorrentes? | **Sim** — Vanilla SPA (oficial) vs Next.js 3001 (experimental) |
| 6 | Qual é servida no runtime FIN-01? | `WebPosto_API/frontend` via FastAPI `/app/financial` |
| 7 | Duplicação de páginas/navegação? | **Parcial** — NewWebLogos não duplica FIN-01; duplica intenção de “Home do dono” de forma incompleta |
| 8 | Risco de FIN-02 em NewWebLogos? | **Alto** — jornada não existe; quebraria paridade com Diretoria/runtime validado |
| 9 | Risco de migrar agora? | **Alto** — reescreveria jornada já validada (DIR + FIN-01) sem ganho imediato |
| 10 | Consolidação segura sem reescrever? | **Sim, futura** — NewWebLogos consome API 8040; migração incremental view-a-view, não nesta sprint |

## Evidências

- Runbook: `LOGOS_RUNBOOK_OFFICIAL_APP.md` — frontend oficial = `frontend/`
- FIN-01 Playwright: `scripts/fin01_ui_validation_playwright.py` → `http://127.0.0.1:8040/app/financial?view=financial-review-inbox`
- NewWebLogos: 0 ocorrências de `financial-review-inbox`, `executive-follow-up`, `owner-diretoria`
- NewWebLogos `apps/frontend` — Next.js porta 3001; chama APIs em 8040 do WebPosto_API

## Conclusão obrigatória

```
OFFICIAL_RUNTIME_FRONTEND = WebPosto_API/frontend (Vanilla JS SPA @ /app/financial)
TARGET_FRONTEND = NewWebLogos (estratégico futuro) — NÃO runtime atual da jornada executiva/financeira
DIVERGENCE = YES
MIGRATION_REQUIRED = YES (futuro, incremental)
MIGRATION_BLOCKS_FIN_02 = NO
```

**Decisão FIN-02:** implementar UI de assignment em **`WebPosto_API/frontend`** — único local com jornada validada e servido em runtime. NewWebLogos **não recebe** FIN-02 nesta sprint.
