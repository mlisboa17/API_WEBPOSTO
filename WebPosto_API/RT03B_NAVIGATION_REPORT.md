# RT03B — IA-2: Audit Navegação

**Data:** 2026-06-09 | **Base:** UX-01 + `frontend/config/navigation.js`

---

## Perguntas de validação

| Pergunta | Resposta |
|---|---|
| A navegação é intuitiva? | **Sim, após RT-03B** — 6 macroáreas com no máximo 3 abas cada |
| Existe menu redundante? | **Sim (corrigido)** — ver tabela abaixo |
| Existe item técnico visível? | **Não na diretoria** — F08.3 movido para Administração |
| Existe item sem valor executivo? | **Motores Avançado** — acessíveis mas não no menu principal |

---

## Estrutura final (UX-01 + RT-03B)

| Macroárea | Abas principais (máx. 3) | Motores (Avançado) |
|---|---|---|
| **Executivo** | Resumo · Indicadores · Alertas | Metas · Comparativo · Visão corporativa |
| **Financeiro** | Receitas · Despesas · Inteligência Financeira | Contas · Fluxo · Extratos · Conciliação |
| **Combustíveis** | Vendas · Estoque & Tanques · Governança | Controle LMC · Bombas · Visão executiva |
| **Produtos** | Vendas & Mix · Oportunidades · Resultados | Plano de ações |
| **Fiscal** | NFCE · Conciliação · Tributação & Riscos | — |
| **Administração** | Sistema · Diagnóstico Técnico | Desempenho operadores · Gestão de pessoas |

**Total abas visíveis:** 17 (Admin com 2 + demais com 3)

---

## Classificação por item

### MANTER

| Item | Motivo |
|---|---|
| Resumo Executivo | Âncora 5s — situação da rede |
| Central de Alertas | Decisão imediata sobre riscos |
| Receitas e Resultado | DRE/KPI financeiro principal |
| Despesas | Controle de gastos |
| Inteligência Financeira | Tendências e riscos (F08.4 operacional) |
| Vendas / Estoque combustível | Operação diária |
| NFCE · Conciliação · Tributação | Compliance fiscal |
| Produtos (3 abas) | Mix comercial unificado na navegação |

### UNIFICAR

| Antes | Depois | Ação |
|---|---|---|
| Operations Center no Financeiro | Diagnóstico Técnico em Admin | **Movido** |
| Contas + Fluxo + Extratos + Conciliação (4 abas) | Strip **Avançado** no Financeiro | **Unificado** (1 entrada cognitiva) |
| Metas + Benchmark + Corporate Hub | Strip Avançado Executivo | **Unificado** |
| LMC + Bombas + Fuel Executive | Strip Avançado Combustíveis | **Unificado** |
| Aba Riscos duplicada no Fiscal | Removida — fundida em Tributação & Riscos | **Unificado** |
| 3 abas Produtos apontando mesma view (RT-01B) | 3 views distintas na navegação | **Unificado** na UX |

### OCULTAR

| Item | Destino | Motivo |
|---|---|---|
| `financialOperationsCenter` (menu Financeiro) | Admin → Diagnóstico Técnico | Infraestrutura — não decisão |
| `financialOperations` / `financialMonitoring` (legado) | Admin (deep link) | Duplicata F08.2 |
| Motores F05 (Copilot, Learning, Recommendations) | Fora do strip visível | Experimental / técnico |
| `fuel-executive` como aba | Motor Avançado | Redundante com Vendas/Governança |

---

## Menus redundantes identificados

1. **F08.3 Operations Center** vs Inteligência Financeira — ambos no Financeiro (resolvido: F08.3 → Admin)
2. **Receitas (dashboard)** vs Visão corporativa (motor) — overlap parcial (motor oculto)
3. **Conciliação fiscal** vs Tributação & Riscos — riscos duplicados (aba removida)
4. **Contas / Fluxo / Extratos / Conciliação** — 4 entradas para mesma jornada financeira (motores)

---

## Respostas executivas (IA-2)

| # | Pergunta | Resposta |
|---|---|---|
| 3 | Quais menus são redundantes? | **4 grupos** (Operations Center, financeiro avançado, fiscal riscos, produtos legado) |
| 4 | Quais menus devem ser ocultados? | **F08.3, legado F08.2, motores F05, fuel-executive como aba** |

---

**[IA-2 APROVADA — navegação executiva validada]**
