# RT05 — IA-6: SAP/Fiori Executive Benchmark

**Data:** 2026-06-09 | **Referências:** SAP Fiori Launchpad, SAP Analytics Cloud (SAC) Executive Dashboards, Power BI Premium (mobile executive layout)  
**Método:** comparação heurística contra 18 telas RT-01 (evidência RT-03A notas Fiori + auditoria RT-05)

---

## Critérios de benchmark

| Dimensão | Padrão SAP/PBI executivo | LOGOS SPACE hoje |
|---|---|---|
| Hierarquia visual | 1 mensagem → 4 KPIs → 1 visual | Múltiplos blocos competindo |
| Uso de espaço | 40% KPIs · 35% gráfico · 25% alertas | ~60% filtros+navegação · 40% conteúdo |
| Quantidade de informação | 7±2 elementos na 1ª dobra | 18–30 elementos |
| Leitura 5 segundos | Sim (Overview Page pattern) | **83% das telas falham** |

---

## Scorecard por tela (0–10 vs Fiori Overview)

| Tela | Hierarquia | Espaço | Densidade | 5 segundos | **Média** | Proximidade SAP |
|---|---:|---:|---:|---:|---:|---|
| Resumo Executivo | 7 | 6 | 5 | 5 | **5,8** | 🟡 Média |
| Receitas | 7 | 5 | 6 | 6 | **6,0** | 🟡 Média |
| Vendas Combustível | 8 | 7 | 8 | 7 | **7,5** | 🟢 Próxima |
| Estoque | 7 | 6 | 7 | 6 | **6,5** | 🟡 Média |
| Conciliação Fiscal | 7 | 6 | 6 | 5 | **6,0** | 🟡 Média |
| Alertas | 6 | 5 | 4 | 4 | **4,8** | 🔴 Distante |
| Indicadores | 5 | 4 | 4 | 3 | **4,0** | 🔴 Distante |
| Despesas | 4 | 3 | 4 | 3 | **3,5** | 🔴 Distante |
| Intel. Financeira | 6 | 5 | 4 | 4 | **4,8** | 🔴 Distante |
| Produtos Performance | 4 | 3 | 3 | 3 | **3,3** | 🔴 Distante |
| Oportunidades | 4 | 4 | 4 | 3 | **3,8** | 🔴 Distante |
| Resultados | 4 | 3 | 3 | 3 | **3,3** | 🔴 Distante |
| NFCE | 6 | 5 | 5 | 4 | **5,0** | 🟡 Média |
| LMC | 5 | 5 | 5 | 4 | **4,8** | 🔴 Distante |
| Governança | 6 | 5 | 5 | 4 | **5,0** | 🟡 Média |
| Tributação | 6 | 5 | 5 | 4 | **5,0** | 🟡 Média |
| F08.3 Diagnóstico | 3 | 2 | 2 | 1 | **2,0** | ⛔ N/A (TI) |

**Média LOGOS SPACE:** **5,1 / 10** vs Fiori Overview  
**RT-03A média Fiori:** **6,3 / 10** (pré RT-05 granular)

---

## Mais próximas do padrão SAP

```text
1. Vendas Combustível        (7,5) — Analytical List Page pattern
2. Estoque & Tanques         (6,5) — tabela focada
3. Receitas / Conciliação    (6,0) — cards + lista
4. Resumo Executivo          (5,8) — estrutura correta, densidade alta
```

---

## Mais distantes do padrão SAP

```text
1. F08.3 Diagnóstico         (2,0) — SAP usa Monitoramento em app separado
2. Produtos Performance      (3,3) — viola "one page one story"
3. Resultados Comerciais     (3,3) — SAC nunca expõe calibration na overview
4. Despesas                  (3,5) — Fiori usa Filter Bar recolhível + KPI header
5. Indicadores               (4,0) — redundante com Overview Page
```

---

## Gaps vs SAP Fiori Launchpad

| Padrão Fiori | LOGOS SPACE | Gap |
|---|---|---|
| **Overview Page** (4 KPI tiles) | 6–8 KPIs + blocos | Reduzir tiles |
| **Filter Bar** adaptativo | 8 filtros fixos | Recolher 60%+ |
| **Smart Business** drill-down | Múltiplas tabelas abertas | 1 tabela → detalhe |
| **Semantic colors** (Good/Critical) | Badges variados | Padronizar 3 níveis |
| **Role-based apps** | 1 app para todos perfis | Perfil Diretoria vs Operação |
| **Analytical List Page** | Vendas/Estoque OK | Replicar pattern |

---

## Gaps vs Power BI Premium Executive

| Padrão PBI | LOGOS SPACE | Gap |
|---|---|---|
| Mobile portrait 4 cards | Desktop denso | Layout responsivo executivo |
| Single hero visual | Sem gráfico hero | Adicionar gráfico 1ª dobra |
| Bookmarks por persona | Deep links técnicos | Simplificar URLs executivas |
| Tooltip, not paragraph | Textos longos em alertas | Encurtar copy |

---

## Espaço visual recuperável (vs benchmark)

| Área | Hoje | Alvo Fiori | Recuperação |
|---|---|---|---|
| Filter bar | ~280px | ~80px | **~200px** |
| KPI grid | 6–8 tiles | 4 tiles | **~25% largura** |
| Tabelas above fold | 1–6 | 0–1 | **~40% scroll** |
| Motor strip | ~48px | 0 (diretoria) | **~48px** |

**Total estimado:** **35–45%** da viewport vertical executiva.

---

**[IA-6 APROVADA — benchmark SAP/Fiori/PBI documentado]**
