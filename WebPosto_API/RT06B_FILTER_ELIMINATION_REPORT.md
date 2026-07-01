# RT-06B — Agente 3: Filter Elimination

**Meta:** 80% menos filtros visíveis  
**Visível:** Período + Empresa  
**Oculto:** demais em “Filtros Avançados”

---

## Estado atual (`filters.js`)

### Primários (sempre visíveis)
- `periodo` → Date Range Picker ✓
- `empresaCodigo` → Multiselect ✓

### Avançados ( `<details class="filters-advanced">` )
| Campo | View padrão | View Despesas |
|-------|-------------|---------------|
| Centro de custo | Oculto ✓ | Oculto ✓ |
| Tipo despesa | Oculto ✓ | Oculto ✓ |
| Texto | Oculto ✓ | Oculto ✓ |
| Valor min/max | Oculto ✓ | Oculto ✓ |
| Natureza | — | Oculto ✓ |
| Grupo gerencial | — | Oculto ✓ |
| Classe gerencial | — | Oculto ✓ |
| Impacta DRE | — | Oculto ✓ |
| Impacta Caixa | — | Oculto ✓ |
| Origem | Oculto ✓ | Oculto ✓ |

### Contagem
- **Antes RT-06:** ~12 campos visíveis na barra
- **Agora:** 2 primários + details fechado = **~83% redução visual** ✓

---

## Problemas remanescentes

| # | Problema | Severidade |
|---|----------|------------|
| 1 | Barra de filtros ocupa linha inteira **acima** do conteúdo | P0 |
| 2 | Botões “Atualizar dados” + “Limpar” sempre visíveis | P1 |
| 3 | `<details>` sem estado “fechado por padrão” explícito no HTML — ok, mas label genérico | P2 |
| 4 | Período duplicado: picker + `periodSubtitle` em cada tela | P2 |
| 5 | `bindBrDateInput` ainda no código (legado) — inputs manuais removidos da UI | P3 |

---

## Classificação

| Critério | Status |
|----------|--------|
| 80% filtros ocultos | **APROVADO** |
| Só Período + Empresa visíveis | **APROVADO** |
| Filtros avançados colapsados | **APROVADO** |
| Percepção “barra limpa” | **PARCIAL** — barra ainda domina topo |

---

## Recomendações

1. Colapsar **toda** a barra de filtros em chip “Período · Empresa ▾” (SAP Analytical List Page pattern)
2. Mover “Limpar” para dentro do popover de filtros
3. Remover código morto `bindBrDateInput` / campos `dataInicial`/`dataFinal` legados

---

**Agente 3 — Conclusão:** Eliminação de campos = **APROVADA**. Eliminação de **peso visual** = **PARCIAL**.
