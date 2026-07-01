# RT-06B — Agente 8: First Fold Validation

**Regra:** Título · Período · 4 KPIs · 1 gráfico · 3 alertas — **nada além**

---

## Checklist por tela prioritária

| Tela | Título | Período | 4 KPIs | 1 Gráfico | 3 Alertas | Extras na 1ª dobra | Status |
|------|--------|---------|--------|-----------|-----------|-------------------|--------|
| Resumo Executivo | ✓ | ✓ subtitle | ✓ | ✓ barras | ✓ (≤3) | — | **OK** |
| Alertas | ✓ | ✓ | ✓ adapter | ✓ auto | ✓ auto | — | **OK** |
| Receitas | ✓ | ✓ | ✓ | ✓ posto | ✓ | **Banner resiliência** | **EXCESSO** |
| Despesas | ✓ | ✓ | ✓ | ✓ natureza | ✓ | **Banner resiliência** | **EXCESSO** |
| Intel. Financeira | ✓ | ✓ | ✓ | ✓ cards | ✓ riscos | — | **OK** |
| Produtos Vendidos | ✓ | ✓ | ✓ | ✓ Pareto | ✓ | — | **OK** |
| Vendas Combustível | ✓ | ✓ | ✓ (2 vazios) | ✓ filial | **~1 alerta** | KPIs “—” | **INSUFICIENTE** |
| NFCE | ✓ | ✓ | ✓ | ✓ diverg. | ✓ | Labels genéricos | **OK** |
| Conciliação Fiscal | ✓ | ✓ | ✓ | ✓ domínios | ✓ | — | **OK** |

**Resumo:** 6 OK · 2 EXCESSO · 1 INSUFICIENTE

---

## Padrões de implementação

| Padrão | Páginas | 1ª dobra compacta |
|--------|---------|-------------------|
| `buildExecutivePageHtml` | 9 prioritárias + fiscal | RT-06A ✓ |
| `renderExecutiveCockpitPage` | ~25 cockpits | Adapter ✓ |
| `renderExecutiveTablePage` | sales, stock, accounts | Parcial |
| `executiveDashboard.js` legado | `executive` | **Não conforme** |

---

## Brief / Painel de decisão

RT-06A moveu para `<details>` — **correto** ✓  
Exceção: `executiveDashboard.js` tenta passar `brief` ao first fold (ignorado).

---

## Ações

### P0
1. Remover banner da 1ª dobra (Receitas, Despesas)
2. Enriquecer alertas em `sales.js` / `renderExecutiveTablePage` (mín. 3)

### P1
3. KPIs semânticos NFCE e Combustíveis
4. Deprecar `executiveDashboard.js`

---

**Agente 8 — Conclusão:** **6/9 OK**. Bloqueadores: banner + Vendas Combustível.
