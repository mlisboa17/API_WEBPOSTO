# UX BACKLOG A04 — Top 20 Melhorias
## Sprint A03.6 | LOGOS SPACE Combustíveis

| Campo | Valor |
|---|---|
| **Data** | 2026-06-08 |
| **Escopo** | Backlog UX — sem implementação nesta sprint |

---

## Top 20 Melhorias UX

| # | Melhoria | Área | Prioridade |
|---|---|---|---|
| 1 | Integrar financial snapshot na UI expenses/accounts | Performance | P0 |
| 2 | Polling fuels pós-refresh (como executive) | Combustíveis | P0 |
| 3 | Indicador progresso carga sales (>10s) | Feedback | P0 |
| 4 | Badge "carregando snapshot" em fuels | Feedback | P1 |
| 5 | Exibir `indiceCoberturaRede` no card Coverage | Governança | P1 |
| 6 | Tooltip explicando LMC vs Litros Vendidos | Combustíveis | P1 |
| 7 | Desabilitar export até carga completa | Tabelas | P1 |
| 8 | Contador "X de Y filiais com dados" no filtro empresa | Filtros | P1 |
| 9 | Feedback visual multiselect (chips em vez de select nativo) | Filtros | P2 |
| 10 | Unificar botão Refresh por view (padrão executive) | Ações | P2 |
| 11 | Mensagem clara token insuficiente por filial | Erros | P2 |
| 12 | Reduzir campos redundantes centroCusto em views sem uso | Filtros | P2 |
| 13 | Stale banner executivo menos intrusivo | Executive | P2 |
| 14 | Skeleton loading em KPIs (não texto "Carregando…") | Loading | P2 |
| 15 | Gráficos fuel com CSS classes (não inline) | Manutenção | P3 |
| 16 | `pageFuels` na URL não usado — remover ou implementar | URL | P3 |
| 17 | Sales subview fuels fora da URL — perde estado F5 | Navegação | P3 |
| 18 | Header filters: opção Todos por coluna mais visível | Tabelas | P3 |
| 19 | PDF preview: incluir linha de totais (autosoma) | Export | P3 |
| 20 | Modo compacto mobile para tabelas financeiras | Responsivo | P3 |

---

## Auditoria Rápida

| Pergunta | Resposta |
|---|---|
| Existe opção Todos? | **Sim** — `__ALL__` no select empresa |
| Multiselect intuitivo? | **Parcial** — select nativo, hint Ctrl+click |
| Campos redundantes? | **Sim** — centroCusto/tipoDespesa em views que não filtram backend |
| Elementos duplicados? | **Sim** — refresh por view + refresh global cache |

---

*Backlog para priorização na Sprint A04.*
