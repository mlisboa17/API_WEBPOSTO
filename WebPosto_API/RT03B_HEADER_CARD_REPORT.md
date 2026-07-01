# RT03B — IA-3: Audit Headers e Cards

**Data:** 2026-06-09 | **Pergunta central:** *O usuário entende sem treinamento?*

---

## Critérios

| Elemento | Antes RT-03B | Depois RT-03B |
|---|---|---|
| Títulos H2 | 62% em inglês ou código sprint | **100% PT executivo** nas 18 telas |
| Subtítulos | Headers F0x, snapshot-first, READ ONLY | Período + contexto de negócio |
| Cards KPI | Termos EN + Aprovado F0x | PT + métricas de negócio |
| Alertas | Alert Center, severidade EN | Alertas prioritários, categorias PT |

---

## Avaliação por macroárea

### Executivo

| Tela | Headers/Cards | Entendimento sem treinamento |
|---|---|---|
| Resumo | KPI receita/despesa/resultado; blocos Alertas e Oportunidades | ✅ **Sim** (~5s) |
| Indicadores | Score executivo + 5 dimensões PT | ✅ **Sim** (~10s) |
| Alertas | Total ações, ROI, prioridade 1 | ✅ **Sim** (~10s) |

### Financeiro

| Tela | Headers/Cards | Entendimento |
|---|---|---|
| Receitas | DRE, faturamento, margem | ✅ **Sim** (~10s) |
| Despesas | Natureza, filial, totais | ✅ **Sim** (~15s) |
| Inteligência | Score financeiro, tendências, riscos, oportunidades | ⚠️ **Parcial** (~30s — densidade alta) |
| Diagnóstico (Admin) | Saúde, agendamento, recuperação | ❌ **Não** (TI) — fora da diretoria |

### Combustíveis

| Tela | Entendimento |
|---|---|
| Vendas | ✅ Sim (~10s) |
| Estoque & Tanques | ✅ Sim (~15s) |
| Governança | ⚠️ Parcial (~20s — termos LMC ainda técnicos no conteúdo) |

### Produtos

| Tela | Entendimento |
|---|---|
| Vendas & Mix | ⚠️ Parcial (~30s — muitos KPIs) |
| Oportunidades | ⚠️ Parcial (~20s) |
| Resultados | ⚠️ Parcial (~30s) |

### Fiscal

| Tela | Entendimento |
|---|---|
| NFCE | ✅ Sim (~10s) |
| Conciliação | ✅ Sim (~15s) |
| Tributação & Riscos | ✅ Sim (~15s) |

---

## Cards problemáticos corrigidos

| Card (antes) | Card (depois) | Tela |
|---|---|---|
| Executive Score / Financial / People | Score executivo / Financeiro / Pessoas | Indicadores |
| Snapshot Coverage | Cobertura de dados | Diagnóstico |
| Circuit Status / Circuit Breaker | Proteção de integração | Diagnóstico / Admin |
| Aprovado F06.x / F07.x | *Removido* | Todas RT-01 |
| Auditável | Rastreável | Alertas |

---

## Respostas executivas (IA-3)

| # | Pergunta | Resposta |
|---|---|---|
| 5 | Quais telas confundem diretoria? | **Inteligência Financeira, Produtos (3 telas), Governança combustível** |
| 6 | Quais telas são intuitivas? | **Resumo, Alertas, Receitas, Despesas, NFCE, Conciliação, Vendas combustível** |

---

**[IA-3 APROVADA — headers e cards revisados]**
