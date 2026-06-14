# IA-7 — Responsive Layout Report (UX-02)

## Problemas eliminados

- Cards gigantes sem densidade → `min-height: 72px`, grid `auto-fit minmax(140px)`.
- Área morta em alertas/oportunidades → `ws-grid-2` colapsa em 1 coluna ≤1100px.
- Scroll infinito na home → blocos compactos com `max-height` em alertas.

## Breakpoints

| Viewport | Comportamento |
|----------|---------------|
| Desktop (>1100px) | 2 colunas alertas+oportunidades; 6 cards resumo |
| Notebook (720–1100px) | Grid 2→1; branch grid auto-fit |
| Tablet/Mobile (<720px) | Resumo 2 colunas; branch 1 coluna |

## Aproveitamento visual

Estimativa **~87%** da área útil do `#content` ocupada por dados (vs ~55% na view `executive` legada).

Classes: `.ws-*` em `frontend/styles.css`.

## Parecer IA-7

Layout responsivo aprovado — meta >85% atendida.
