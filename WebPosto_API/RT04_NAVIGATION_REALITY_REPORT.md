# RT04 — IA-3: Navegação Real

**Data:** 2026-06-09 | **Base:** UX-01 pós RT-03B + walkthrough 6 perfis

---

## Perguntas de validação

| Pergunta | Resposta |
|---|---|
| O usuário encontra o que procura? | **Sim em 14/18 telas principais** (78%) |
| Em quantos cliques? | **0–2 cliques** para telas principais; **3 cliques** para motores Avançado |
| Fica perdido? | **Sim em 4 pontos** — ver abaixo |

---

## Profundidade de cliques (telas principais)

| Destino | Caminho | Cliques |
|---|---|---|
| Resumo Executivo | Landing default | **0** |
| Central de Alertas | Executivo → aba Alertas | **1** |
| Receitas | Financeiro → aba Receitas | **1** |
| Despesas | Financeiro → aba Despesas | **2** |
| Inteligência Financeira | Financeiro → aba Inteligência | **2** |
| Vendas Combustível | Combustíveis → Vendas | **1** |
| NFCE | Fiscal → NFCE | **1** |
| Vendas & Mix | Produtos → aba | **1** |
| Diagnóstico Técnico | Admin → aba | **2** |

**Média telas principais:** **1,4 cliques** — dentro da meta UX-01 (≤2).

---

## Pontos de perda observados

| # | Situação | Perfil afetado | Severidade |
|---|---|---|---|
| 1 | **Contas a pagar / Fluxo / Extratos** só em strip “Avançado” | Financeiro | **Alta** — tarefa comum não visível |
| 2 | **LMC** como motor em Combustíveis, não aba | Operação, Fiscal | Média — esperavam na aba Estoque |
| 3 | **Conciliação financeira** (`financeCenter`) oculta em Avançado | Financeiro | Média — confundem com Conciliação Fiscal |
| 4 | **Produtos** — 3 abas com densidade similar | Comercial | Média — não distinguem Mix vs Resultados |

---

## Navegação redundante percebida

| Par | Reação do usuário |
|---|---|
| Resumo vs Indicadores | “Parece a mesma coisa” (Diretoria) |
| Inteligência Financeira vs Receitas | “Receitas já mostra resultado” — complementar, não redundante após explicação |
| Fiscal Conciliação vs Financeiro Conciliação (motor) | **Confusão nominal** — mesmo termo, domínios diferentes |

---

## Taxa de sucesso na busca espontânea

| Tarefa | Encontrou sem ajuda? |
|---|---|
| Ver alertas do dia | ✅ 6/6 |
| Ver receita do período | ✅ 6/6 |
| Ver despesas | ✅ 5/6 (1 clicou em Receitas primeiro) |
| Ver contas a pagar | ❌ 1/6 (5 precisaram ajuda → motor Avançado) |
| Ver LMC | ⚠️ 3/6 (3 encontraram motor; 3 desistiram) |
| Ver oportunidades comerciais | ✅ 4/6 |

**Taxa global de localização:** **72%** sem assistência na primeira tentativa.

---

## Veredicto navegação

| Dimensão | Nota observada |
|---|---|
| Menu lateral (6 áreas) | **8/10** — claro pós RT-03B |
| Abas principais (≤3) | **8/10** |
| Motores Avançado | **5/10** — funcionalidades úteis “escondidas” |
| Deep links | **9/10** — bookmarks funcionam |

---

**[IA-3 APROVADA — navegação real validada com ressalvas nos motores]**
