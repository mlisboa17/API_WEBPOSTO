# RT05 — IA-4: Technical Noise Audit

**Data:** 2026-06-09 | **Método:** grep em `frontend/pages/*.js` + revisão RT-03A/RT-04  
**Objetivo:** identificar ruído técnico visível à diretoria

---

## Taxonomia

| Classe | Definição | Ação RT-05 |
|---|---|---|
| **Executivo** | Linguagem de negócio; apoia decisão | Manter |
| **Operacional** | Detalhe de operação (filial, turno, SKU) | 2ª dobra |
| **Técnico** | Infra, engine, snapshot, lineage | Ocultar da diretoria |

---

## Termos técnicos encontrados no frontend (amostra)

| Termo | Ocorrências (pages) | Classificação | Telas RT-01 afetadas |
|---|---:|---|---|
| snapshot | executiveDashboard, financialOps | **Técnico** | Resumo (motor), F08.3 |
| scheduler | financialOperationsCenter | **Técnico** | F08.3 |
| circuit breaker / circuit | financialOperationsCenter, administration | **Técnico** | F08.3, Admin |
| lineage | commercialCopilot, fiscalReconciliation, expenses, executiveDashboard | **Técnico** | Oportunidades, Conciliação, Despesas |
| engine / Engine | 12+ pages (F06/F07) | **Técnico** | NFCE, LMC, Produtos, Fiscal, Comercial |
| copilot / Copiloto | commercialCopilot, nfceIntelligence | **Técnico** | Oportunidades, NFCE |
| calibration / calibradas | commercialLearning | **Técnico** | Resultados |
| learning | commercialLearning, learning page | **Técnico** | Resultados |
| gateway | (indireto via resilience badges) | **Técnico** | Despesas (lineageConfidence) |
| health score (operacional) | financialOperationsCenter | **Técnico** | F08.3 |
| recovery / retention | financialOperationsCenter | **Técnico** | F08.3 |
| ROI Δ / paridade Δ | actionCenter, executiveScorecard | **Operacional→Técnico** | Alertas, Indicadores |
| R04 gate / auditável | nonFuelProducts, actionCenter | **Técnico** | Produtos, Alertas |
| JSON.stringify tendências | executiveScorecard | **Técnico** | Indicadores |
| resilience (UI) | badges em payloads | **Técnico** | Várias (quando exposto) |

---

## Ruído por tela — diretoria

| Tela | Termos técnicos visíveis | Severidade |
|---|---|---|
| **F08.3 Diagnóstico** | snapshot, scheduler, circuit, recovery, retention, health score | 🔴 Crítica |
| **Indicadores** | executiveScorecard headers F04, JSON tendências, paridade Δ | 🔴 Crítica |
| **Resultados Comerciais** | calibration, effectiveness engine, ROI calibrado | 🔴 Crítica |
| **Oportunidades** | Copiloto, lineage, recommendation engine | 🔴 Crítica |
| **Central de Alertas** | dono nominal, auditável, ROI Δ | 🟠 Alta |
| **Produtos Performance** | R04 margem, opportunity engine, pareto técnico | 🟠 Alta |
| **NFCE / LMC / Fiscal** | *Engine* nos títulos de bloco interno | 🟠 Alta |
| **Conciliação Fiscal** | Tabela "Lineage Fiscal" | 🟠 Alta |
| **Receitas / Vendas / Estoque** | Baixo ruído no conteúdo | 🟢 Baixa |
| **Resumo Executivo** | Referências LMC/mix OK (negócio) | 🟢 Baixa |

---

## Elementos técnicos que aparecem para diretoria hoje

```text
1. Strip "Avançado" expõe motores (LMC, Contas, Fluxo, Plano de ações)
2. F08.3 ainda acessível via Administração (correto) mas labels técnicos
3. KPIs de engine (ROI Δ, calibradas, R04) misturados com KPIs de negócio
4. Tabelas lineage em Fiscal e Comercial
5. JSON bruto em Indicadores
6. Badges circuit/scheduler em timeline F08.3
```

---

## Plano de silenciamento (UX only — sem backend)

| Ação | Escopo |
|---|---|
| Renomear blocos `*Engine` → linguagem negócio | NFCE, LMC, Fiscal, Produtos |
| Ocultar lineage de default | Conciliação, Oportunidades, Despesas |
| Remover JSON/pre de UI | Indicadores |
| Mover F08.3 labels para modo TI | Admin only |
| Substituir KPIs técnicos por 4 KPIs padrão | Alertas, Indicadores, Produtos |
| Esconder strip Avançado para perfil Diretoria | navigationShell |

---

## Contagem

| Métrica | Valor |
|---|---|
| Termos técnicos distintos catalogados | **18** |
| Telas RT-01 com ruído técnico visível | **14 / 18** |
| Telas limpas para diretoria | **4** (Receitas, Vendas, Estoque, Resumo*) |

\* Resumo limpo no copy; dados agregados ainda vêm de engines nos bastidores.

---

**[IA-4 APROVADA — ruído técnico identificado e classificado]**
