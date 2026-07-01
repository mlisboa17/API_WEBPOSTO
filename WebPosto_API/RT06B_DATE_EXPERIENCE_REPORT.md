# RT-06B — Agente 4: Date Experience

**Obrigatório:** Date Range Picker · calendário visual · clique · sem digitação  
**Proibido:** usuário digitar data manualmente

---

## Implementação atual

| Item | Status | Arquivo |
|------|--------|---------|
| Date Range Picker (DRP) | ✓ | `DateRangePicker.js` |
| Presets (Hoje, 7d, 30d, mês…) | ✓ | `DateRangePicker.js` |
| Seleção início → fim (2 cliques) | ✓ | Corrigido RT-06A |
| Aplicar dispara refresh | ✓ | `filters.js` → `emitChange` → `refreshAll` |
| Inputs dd/mm/aaaa | ✗ Removidos da UI | — |
| Código legado `bindBrDateInput` | ⚠ Ainda presente | `filters.js` (não usado) |

**Date picker obrigatório:** **APROVADO**

---

## Botões redundantes

| Botão | Local | Comportamento |
|-------|-------|---------------|
| **Aplicar** | Popover DRP | Aplica período + `refreshAll(false)` |
| **Atualizar dados** | Barra filtros | Limpa cache + `refreshAll(true)` |
| **Atualizar** | Topbar | Limpa cache + `refreshAll(true)` |

### Análise
- **Aplicar** = fluxo correto para mudança de período
- **Atualizar** / **Atualizar dados** = duplicados entre si
- Usuário não sabe qual clicar após mudar data

---

## Fluxo único proposto

```
Período → selecionar início → selecionar fim → Aplicar → refresh automático
```

| Ação | Botão |
|------|-------|
| Mudar período | **Aplicar** (DRP) |
| Forçar reload (cache) | **Atualizar** (topbar) — único, com tooltip “Recarregar dados” |
| Remover | **Atualizar dados** (filtros) |

---

## Classificação

| Critério | Status |
|----------|--------|
| Sem digitação manual | **APROVADO** |
| Calendário visual | **APROVADO** |
| Refresh automático pós-Aplicar | **APROVADO** |
| Fluxo único de refresh | **REPROVADO** — 3 botões |

---

**Agente 4 — Conclusão:** Experiência de data = **APROVADA**. Governança de botões = **REPROVADA**.
