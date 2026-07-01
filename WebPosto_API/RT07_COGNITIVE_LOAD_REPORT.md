# RT-07 — IA-7: Cognitive Load Audit

**Pergunta:** O diretor entende a tela em menos de 5 segundos?

---

## 1. Fatores de carga cognitiva (peso)

| Fator | Peso | Estado LOGOS |
|-------|------|--------------|
| Filtros antes do conteúdo | Alto | Presente em todas |
| Banner técnico | Alto | Receitas/Despesas |
| Múltiplos refresh | Médio | 3 botões |
| Títulos engine | Alto | 9 views órfãs |
| KPIs semânticos errados | Alto | Combustível, NFCE |
| Sub-nav clara (≤3) | Baixo | OK por área |
| 1ª dobra padronizada | Positivo | RT-06 ✓ |

---

## 2. Telas principais — regra 5 segundos

| Tela | Receita/Despesa/Margem/Alertas visíveis? | Entendimento <5s? | Classificação |
|------|------------------------------------------|-------------------|---------------|
| Resumo Executivo | Sim | Sim | **SIM** |
| Alertas | Parcial | Parcial | **PARCIAL** |
| Indicadores | Parcial | Parcial | **PARCIAL** |
| Receitas | Sim (pós-banner) | Não — banner primeiro | **NÃO** |
| Despesas | Sim (pós-banner) | Não | **NÃO** |
| Intel. Financeira | Parcial (score) | Parcial | **PARCIAL** |
| Contas / Fluxo / Extratos / Conciliação | Variável | Não — muitas entradas | **NÃO** |
| Vendas Combustível | Não | Não | **NÃO** |
| Estoque | Parcial | Parcial | **PARCIAL** |
| Governança | Parcial | Parcial | **PARCIAL** |
| Produtos Vendidos | Sim | Sim | **SIM** |
| Oportunidades (separada) | Confuso | Não | **NÃO** |
| Resultados (separada) | Confuso | Não | **NÃO** |
| NFCE | Parcial | Parcial | **PARCIAL** |
| Conciliação Fiscal | Sim | Sim | **SIM** |
| Tributação | Parcial | Parcial | **PARCIAL** |
| Sistema / Diagnóstico | N/A (admin) | N/A | — |

**Score:** 3 **SIM** · 7 **PARCIAL** · 6 **NÃO**

---

## 3. Carga por jornada

### Jornada: “Como está meu resultado?”
| Passo | Cliques hoje | Cliques RT-07 |
|-------|--------------|---------------|
| Abrir LOGOS | 0 | 0 |
| Achar receita/despesa/margem | 2–3 (nav + scroll) | **1** (Resumo ou Visão Financeira) |
| **Total** | **~8s** | **~3s** ✓ |

### Jornada: “O que preciso fazer?”
| Passo | Hoje | RT-07 |
|-------|------|-------|
| Alertas | 2 cliques | 1 clique |
| **Total** | **~4s** ✓ | **~3s** ✓ |

### Jornada: “Como estão produtos?”
| Passo | Hoje | RT-07 |
|-------|------|-------|
| Mix vs Oportunidades vs Resultados | 3 telas confusas | 1 hub, sub-abas |
| **Total** | **>10s** | **~4s** ✓ |

---

## 4. Redução de carga — ações RT-07

| Ação | Impacto cognitivo |
|------|-------------------|
| Hub Financeiro | −40% cliques domínio financeiro |
| Hub Produtos | −66% entradas produtos |
| Remover banner | −2s Receitas/Despesas |
| Chip filtros | −1 bloco visual fixo |
| Eliminar views engine | −9 conceitos fantasma |

---

## 5. Meta final RT-07

> Receita · Despesa · Margem · Alertas · Ações em **<5 segundos**

| Entry point | Atende meta? | Pós RT-07? |
|-------------|--------------|------------|
| Resumo Executivo | **SIM** | SIM |
| Visão Financeira (hub) | NÃO hoje | **SIM** |
| Demais telas | PARCIAL | PARCIAL+ |

**Target pós RT-07:** 8/14 entradas principais = **SIM** (≥57%)

---

**IA-7 — Conclusão:** Carga cognitiva **alta** hoje (6 telas NÃO). RT-07 hubs + banner + menu = caminho para meta 5s.
