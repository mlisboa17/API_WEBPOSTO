# RT-07 — IA-2: Filter Reduction

**Meta:** −80% filtros visíveis · manter só **Período** + **Empresa**

---

## 1. Estado atual (`filters.js`)

### Camada primária (visível)
| Campo | Componente | Status |
|-------|------------|--------|
| `periodo` | Date Range Picker (DRP) | ✓ |
| `empresaCodigo` | Multiselect | ✓ |

### Camada avançada (`<details>`)
| Campo | Views |
|-------|-------|
| Centro de custo | Todas |
| Tipo despesa | Todas |
| Texto | Todas |
| Valor mín / máx | Todas |
| Natureza | Despesas |
| Grupo gerencial | Despesas |
| Classe gerencial | Despesas |
| Impacta DRE | Despesas |
| Impacta Caixa | Despesas |
| Origem | Despesas |

### Contagem
| Métrica | Valor |
|---------|-------|
| Campos totais (máx.) | **12** |
| Visíveis primários | **2** |
| **Redução visual** | **83%** ✓ (meta 80% atingida) |

---

## 2. Problemas remanescentes (não é quantidade — é peso)

| # | Problema | Impacto |
|---|----------|---------|
| 1 | Barra de filtros **acima** de todo conteúdo | Parece formulário ERP |
| 2 | Botões **Atualizar dados** + **Limpar** sempre visíveis | Ruído + confusão com DRP Aplicar |
| 3 | `bindBrDateInput` legado ainda no código | Código morto |
| 4 | Período duplicado: DRP + `periodSubtitle` em cada tela | Redundância |
| 5 | View Despesas: 11 campos avançados (correto ocultos, mas pesados ao expandir) | Carga ao power user |

---

## 3. RT-07 — reduções adicionais propostas

### P0 — Camada principal
- [ ] Colapsar barra inteira em chip: **`📅 Período · 🏢 Empresa ▾`**
- [ ] Remover botão **Atualizar dados** (manter só topbar **Atualizar** + DRP **Aplicar**)
- [ ] Mover **Limpar** para dentro do popover/chip de filtros

### P1 — Avançados
- [ ] Renomear summary: **“Mais filtros”** (menos técnico que “Filtros avançados”)
- [ ] Agrupar Despesas: bloco “Classificação gerencial” dentro do details
- [ ] Remover `bindBrDateInput` e campos `dataInicial`/`dataFinal` legados

### P2 — Shell
- [ ] Mover filtros **abaixo** das abas (SAP-first + menos cliques cognitivos)
- [ ] Filtros sticky só ao scrollar para baixo (opcional)

---

## 4. Métricas pós-RT-07

| Métrica | Antes RT-06 | RT-06A | RT-07 target |
|---------|-------------|--------|--------------|
| Campos visíveis | ~12 | 2 | 1 chip |
| Cliques p/ filtrar período | digitar + aplicar | 3 (abrir+2 datas+aplicar) | 3 (mantém) |
| Botões refresh visíveis | 3 | 3 | **2** |
| Altura barra filtros | ~120px | ~80px | **~44px** (chip) |

---

## 5. Classificação

| Critério | RT-07 |
|----------|-------|
| 80% redução campos | **APROVADO** (já em RT-06A) |
| Só Período + Empresa visíveis | **APROVADO** |
| Redução peso visual / cliques | **PENDENTE** (chip + reorder) |
| Remove complexidade? | **PARCIAL** — falta colapsar barra |

---

**IA-2 — Conclusão:** Meta quantitativa **atingida**. RT-07 deve focar **colapsar a barra** e **eliminar botão redundante**, não criar novos filtros.
