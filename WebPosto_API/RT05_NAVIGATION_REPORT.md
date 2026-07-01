# RT05 — Navigation Report

**Data:** 2026-06-09 | **Base:** `frontend/config/navigation.js`, RT-03B, RT-04 jornadas  
**Objetivo:** jornada executiva enterprise — **sem novas rotas/APIs**

---

## 1. Diagnóstico — navegação hoje

| Camada | Elementos | Problema RT-04 |
|---|---:|---|
| Sidebar macroáreas | 6 | OK pós RT-03B |
| Abas por área | 3 | OK |
| Strip "Avançado" | 0–6 motores | **72% não encontram Contas/Fluxo/LMC** |
| Filtros globais | 8 | Competem com conteúdo |
| Deep links `?view=` | 40 mapeados | Funcionam; descoberta ruim |

**Taxa localização espontânea (RT-04):** 72% sem ajuda · **Financeiro Contas:** 17% (1/6).

---

## 2. Jornadas validadas RT-04

| Perfil | Fluxo principal | Cliques | Conclusão |
|---|---|---:|---|
| Diretoria | Resumo → Alertas → Receitas | 0–2 | 90% |
| Financeiro | Receitas → Despesas → Conciliação | 2–3 | 85% |
| Operação | Vendas → Estoque | 1–2 | 90% |
| Comercial | Mix → Oportunidades → ~~Resultados~~ | 2+ | 60% |
| Fiscal | NFCE → Conciliação | 1–2 | 95% |

**Fluxo mais usado:** Executivo Resumo → Alertas → Financeiro Receitas  
**Fluxo menos usado:** Produtos Oportunidades → Resultados → motor Plano

---

## 3. Navegação alvo — perfil Diretoria

### Sidebar reduzida (4 entradas)

| # | Label | Destino | Views |
|---|---|---|---|
| 1 | **Visão Geral** | Overview executiva | `executive-workspace` (reorganizado) |
| 2 | **Financeiro** | Receitas · Despesas · Inteligência | 3 abas existentes |
| 3 | **Operação** | Combustíveis + Fiscal unificados | sub-nav interno |
| 4 | *(oculto)* Administração | Somente TI | `administration`, F08.3 |

**Motores removidos da jornada diretoria:**

```text
goalsCampaign · benchmark · corporateHub
accounts · cashFlow · cashOperations · financeCenter
lmcIntelligence · fuels · fuelExecutive · commercialExecution
operatorPerformance · peopleIntelligence
```

Acesso: **Administração → Diagnóstico** ou deep link bookmark — não sidebar/strip.

### Operação — sub-nav compacto

```text
Operação
├── Combustíveis (Vendas · Estoque · Governança)
└── Fiscal (NFCE · Conciliação · Tributação)
```

Reduz 6→4 entradas sidebar sem perder telas RT-01.

---

## 4. Navegação alvo — perfil Financeiro / Operação

| Elemento | Diretoria | Financeiro | Operação |
|---|---|---|---|
| Filtros visíveis | Período + Empresa | + link Avançado | Período + Empresa |
| Strip Avançado | **Oculto** | **Visível** | Visível |
| F08.3 Diagnóstico | Oculto | Oculto | Oculto (Admin) |
| Produtos 3 abas | 1 entrada "Comercial" | Igual | Igual |

---

## 5. Unificações recomendadas (UX only)

| Duplicidade RT-03A | Decisão RT-05 |
|---|---|
| Resumo + Indicadores | **Unificar** — Indicadores vira 2ª dobra do Resumo |
| Produtos 4 telas | **1 tela** 4 abas internas (Mix · Oportunidades · Ações · Resultados) |
| NFCE + Tributação | Abas mesma área Fiscal (já OK) |
| Alertas + Management Action | **Unificar** — action-center único |
| Fluxo + Extratos + Conciliação financeira | **1 experiência** "Caixa" em Avançado |

---

## 6. Mapa de deep links executivos (homologado)

| Destino | URL |
|---|---|
| Visão Geral | `/app/financial?view=executive-workspace&dataInicial=2026-06-01&dataFinal=2026-06-07` |
| Receitas | `?view=dashboard&...` |
| Despesas | `?view=expenses&...` |
| Alertas | `?view=action-center&...` |
| Vendas | `?view=sales&...` |
| NFCE | `?view=nfce-intelligence&...` |

Período sempre nos query params — **único filtro obrigatório além de empresa**.

---

## 7. Critérios de corte navegação

| Ocultar da diretoria | Motivo |
|---|---|
| Strip Avançado | Motores ignorados RT-04 |
| Indicadores (top-level) | Redundante Resumo |
| Oportunidades default | Baixo valor RT-04 |
| Diagnóstico Técnico | TI only |
| 15 motores deep link | Nunca abertos espontaneamente |

---

## 8. Métricas alvo pós-rebuild

| Métrica | Hoje | Alvo RT-06+ |
|---|---:|---:|
| Cliques até Receitas | 1–2 | **1** |
| Localização sem ajuda | 72% | **≥90%** |
| Motores descobertos espontaneamente | ~0 | N/A (proposital) |
| Entradas sidebar diretoria | 6 | **4** |
| Elementos nav antes do conteúdo | 10–16 | **≤7** |

---

## 9. Veredicto

| Pergunta | Resposta |
|---|---|
| Menu atual adequado? | **Parcial** — macroáreas OK; strip + filtros reprovam |
| Diretoria se perde? | **Sim** — motores Avançado e Produtos |
| Rebuild necessário? | **Sim** — reorganizar, não expandir |

---

**[RT05 NAVIGATION — PLANO APROVADO]**
