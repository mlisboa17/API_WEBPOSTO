# IA-5 — Layout Optimization

## Mudanças

| Antes | Depois |
|-------|--------|
| Grid de 30+ botões horizontais | Sidebar 220px + abas compactas |
| Domínios Executive/Financial/Operacional empilhados | `app-shell` 2 colunas |
| Views com margin-top redundante | `content-grid` densificado |

## CSS

- `.app-shell` — grid responsivo
- `.area-tabs` — pills horizontais
- `.motor-strip` — faixa secundária (motores da área)
- Breakpoint 960px — sidebar horizontal

Objetivo: área útil de conteúdo > 80% em viewport desktop.
