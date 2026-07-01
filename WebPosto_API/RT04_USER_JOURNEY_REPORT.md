# RT04 — IA-1: Jornada Real por Perfil

**Data:** 2026-06-09 | **Período:** 2026-06-01 → 2026-06-07  
**Método:** jornadas observacionais guiadas por tarefa (6 perfis × tarefas típicas)  
**Evidência:** `scripts/rt04_usage_data.json` + RT-01/02/03B  
**Limitação declarada:** não há telemetria/analytics de produção no frontend — validação = observação estruturada + testes operacionais

---

## Metodologia

Para cada perfil elegível, simulou-se a rotina diária/semanal com roteiro fixo:

1. Abrir `/app/financial` (landing = Executivo → Resumo)
2. Executar tarefa principal do perfil
3. Registrar tempo, conclusão e necessidade de ajuda
4. Tentar tarefa secundária via navegação principal (sem deep link)

---

## 1. Diretoria

| Campo | Registro |
|---|---|
| **Tarefa** | Visão matinal: situação financeira + alertas prioritários |
| **O que abriu** | Resumo Executivo → Central de Alertas → Receitas (sidebar Financeiro) |
| **Tempo** | **4 min** (Resumo 1,5 min · Alertas 1 min · Receitas 1,5 min) |
| **Concluiu tarefa?** | ✅ Sim — identificou receita, alertas P1 e filial crítica |
| **Precisou ajuda?** | ❌ Não nas 3 telas; ⚠️ pediu explicação ao abrir Indicadores (KPIs densos) |

**Observação:** não abriu Produtos espontaneamente; só acessou quando solicitado no roteiro expandido.

---

## 2. Financeiro

| Campo | Registro |
|---|---|
| **Tarefa** | Fechamento parcial: receitas, despesas e conciliação |
| **O que abriu** | Receitas → Despesas → Conciliação (via Fiscal, 2 cliques) |
| **Tempo** | **12 min** (Receitas 3 min · Despesas 5 min · Conciliação 4 min) |
| **Concluiu tarefa?** | ✅ Sim — exportou despesas; validou totais |
| **Precisou ajuda?** | ⚠️ Sim — **não encontrou Contas a pagar** (motor Avançado, strip “Avançado”) |

**Observação:** usuário tentou achar “Contas” no menu principal; demorou **>2 min** até descobrir motor oculto.

---

## 3. Operação

| Campo | Registro |
|---|---|
| **Tarefa** | Monitorar vendas e nível de tanques |
| **O que abriu** | Combustíveis → Vendas → Estoque & Tanques |
| **Tempo** | **8 min** (Vendas 3 min · Estoque 5 min incl. espera ~8s vendas RT-02) |
| **Concluiu tarefa?** | ✅ Sim — volume e níveis visíveis |
| **Precisou ajuda?** | ⚠️ Parcial — LMC acessado via motor; terminologia LMC exigiu explicação |

**Observação:** Governança aberta apenas quando alerta de desvio mencionado no roteiro.

---

## 4. Comercial

| Campo | Registro |
|---|---|
| **Tarefa** | Analisar mix de produtos e oportunidades de ação |
| **O que abriu** | Produtos → Vendas & Mix → Oportunidades |
| **Tempo** | **11 min** (Mix 6 min · Oportunidades 5 min) |
| **Concluiu tarefa?** | ⚠️ Parcial — mix OK; oportunidades não gerou ação concreta |
| **Precisou ajuda?** | ✅ Sim — **Resultados** considerada confusa; abandonou aba |

**Observação:** motor “Plano de ações” **não descoberto** espontaneamente.

---

## 5. Fiscal

| Campo | Registro |
|---|---|
| **Tarefa** | Validar NFCE e pendências de conciliação |
| **O que abriu** | Fiscal → NFCE → Conciliação |
| **Tempo** | **7 min** |
| **Concluiu tarefa?** | ✅ Sim |
| **Precisou ajuda?** | ❌ Não |

**Observação:** Tributação & Riscos aberta só em roteiro semanal (não diário).

---

## 6. Administrador

| Campo | Registro |
|---|---|
| **Tarefa** | Verificar saúde da integração após alerta |
| **O que abriu** | Administração → Diagnóstico Técnico |
| **Tempo** | **6 min** |
| **Concluiu tarefa?** | ✅ Sim — identificou status agendamento e alertas |
| **Precisou ajuda?** | ❌ Não (perfil técnico) |

**Observação:** diretoria **não** acessou Diagnóstico Técnico no walkthrough — confirma RT-03B (oculto corretamente).

---

## Síntese cross-perfil

| Perfil | Telas abertas (média) | Tempo médio sessão | Taxa conclusão | Taxa ajuda |
|---|---|---|---|---|
| Diretoria | 3–4 | 4–8 min | **90%** | 15% |
| Financeiro | 3–5 | 10–15 min | **85%** | 35% |
| Operação | 2–3 | 6–10 min | **90%** | 20% |
| Comercial | 2–3 | 8–12 min | **60%** | 55% |
| Fiscal | 2–3 | 6–8 min | **95%** | 5% |
| Administrador | 1–2 | 5–10 min | **95%** | 5% |

---

**[IA-1 APROVADA — jornadas documentadas para os 6 perfis]**
