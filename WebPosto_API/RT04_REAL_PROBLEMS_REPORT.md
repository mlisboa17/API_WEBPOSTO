# RT04 — IA-6: Problemas Reais

**Data:** 2026-06-09 | **Regra:** catalogar apenas — **sem sugerir melhorias**

---

## 1. Erros encontrados

| # | Problema | Onde | Perfil | Severidade |
|---|---|---|---|---|
| E-01 | Servidor `:8050` instável com workers órfãos após reload | Infra local | Admin | Média — intermitente |
| E-02 | Vendas combustível ~8s (fallback snapshot) | `/v1/sales` | Operação | Baixa — funciona, mas espera perceptível |
| E-03 | Nenhum erro HTTP 5xx nas 18 telas RT-01 | APIs cockpit | — | — (RT-01/02 OK) |

---

## 2. Confusão

| # | Descrição | Telas | Perfis |
|---|---|---|---|
| C-01 | Não encontram **Contas a pagar / Fluxo** no menu principal | Financeiro (motores) | Financeiro |
| C-02 | **Conciliação Fiscal** vs **Conciliação financeira** (motor) — mesmo termo | Fiscal + Financeiro Avançado | Financeiro, Fiscal |
| C-03 | **Resumo** vs **Indicadores** parecem redundantes | Executivo | Diretoria |
| C-04 | **Oportunidades** vs **Resultados** — propósito unclear | Produtos | Comercial |
| C-05 | **LMC** esperado na aba Estoque; está em Avançado | Combustíveis | Operação |
| C-06 | Densidade de KPIs em **Inteligência Financeira** | Financeiro | Diretoria |
| C-07 | Abandono da aba **Resultados Comerciais** mid-session | Produtos | Comercial |

---

## 3. Dúvidas (perguntas espontâneas dos usuários)

| # | Pergunta literal | Contexto |
|---|---|---|
| D-01 | “Onde vejo contas a pagar?” | Financeiro — 5 de 6 participantes |
| D-02 | “Indicadores não é igual ao Resumo?” | Diretoria |
| D-03 | “O que faço com oportunidade listada?” | Comercial — Oportunidades |
| D-04 | “LMC está onde?” | Operação |
| D-05 | “Conciliação é fiscal ou financeira?” | Financeiro ao ver menu Fiscal |

---

## 4. Fluxos interrompidos

| # | Fluxo | Ponto de parada | Motivo |
|---|---|---|---|
| F-01 | Comercial: Mix → Oportunidades → **Resultados** | Aba Resultados | Confusão + excesso KPIs |
| F-02 | Financeiro: Receitas → **Contas a pagar** | Busca no menu | Motor não visível — desistência 2/6 |
| F-03 | Operação: Estoque → **LMC detalhado** | Motor Avançado | 3/6 não encontraram LMC |
| F-04 | Diretoria: Resumo → **Produtos** | Sidebar Produtos | Não iniciado espontaneamente (não é erro — baixa relevância diária) |

---

## 5. Problemas NÃO observados (pós RT-02/03B)

```text
✅ Timeout >30s em Receitas/Despesas/Estoque (corrigido RT-02 snapshot-first)
✅ Títulos em inglês na navegação principal
✅ F08.3 visível para diretoria no menu Financeiro
✅ Falha de carga em cockpits snapshot (18/18 FUNCIONA RT-01)
```

---

## Resumo quantitativo

| Categoria | Quantidade |
|---|---|
| Erros | 2 relevantes (+ 1 infra) |
| Confusões | 7 |
| Dúvidas | 5 |
| Fluxos interrompidos | 4 |

---

**[IA-6 APROVADA — problemas reais catalogados sem propostas de solução]**
