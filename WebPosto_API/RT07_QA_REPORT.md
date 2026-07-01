# RT-07 — IA-8: Anti-Mediocrity QA

**Validar:** SAP Fiori · SAC · Power BI Premium · vende · impressiona · **não** parece ERP comum

---

## 1. Guardrails RT-07

| Regra | Violado? |
|-------|----------|
| Nenhuma funcionalidade nova | ✓ OK — só consolidação UX |
| Nenhuma API nova | ✓ OK |
| Nenhum serviço/motor novo | ✓ OK |
| Nenhum dashboard novo | ✓ OK — hubs reutilizam renders |
| Menos telas | Plano −44% DOM |
| Menos filtros | 83% já; chip pendente |
| Menos cliques | Hubs −30–50% |
| Menos ruído | Banner + engines pendentes |
| Mais clareza | Menu 14 entradas |

---

## 2. Teste anti-mediocridade (ERP comum = REPROVAR)

| Tela / Shell | ERP comum? | SAP? | Power BI? | Vende? | Veredicto |
|--------------|------------|------|-----------|--------|-----------|
| Shell (filtros topo) | **SIM** | Não | Não | Não | **REPROVADO** |
| Resumo Executivo | Não | Parcial | Parcial | Sim | **PARCIAL** |
| Receitas + banner | **SIM** | Não | Não | Não | **REPROVADO** |
| Despesas + banner | **SIM** | Não | Não | Não | **REPROVADO** |
| Produtos Vendidos | Não | Parcial | Sim | Sim | **APROVADO** |
| Conciliação Fiscal | Não | Parcial | Parcial | Sim | **APROVADO** |
| NFCE | Parcial | Parcial | Parcial | Parcial | **PARCIAL** |
| Vendas Combustível | **SIM** (CRUD) | Não | Não | Não | **REPROVADO** |
| Views engine (learning…) | **SIM** (admin) | Não | Não | Não | **REPROVADO** |
| Admin Diagnóstico | N/A | N/A | N/A | N/A | OK (técnico) |

**ERP comum detectado:** 5 superfícies · **REPROVADAS**

---

## 3. Critérios de aceite RT-07

| # | Critério | Pré RT-07 | Pós implementação |
|---|----------|-----------|-------------------|
| 1 | Menos telas (39→~22 DOM) | ☐ | ☐ |
| 2 | Menu 12–15 entradas | ☐ (30 nav) | ☐ (14 plano) |
| 3 | Hub Financeiro | ☐ | ☐ |
| 4 | Hub Produtos | ☐ | ☐ |
| 5 | Zero engine na UI exec. | ☐ | ☐ |
| 6 | Banner fora executivo | ☐ | ☐ |
| 7 | Chip filtros | ☐ | ☐ |
| 8 | 8/14 telas <5s (SIM) | ☐ (3/14) | ☐ |
| 9 | 0 superfícies ERP REPROVADAS | ☐ (5) | ☐ |

---

## 4. Comparativo RT-06B → RT-07

| Dimensão | RT-06B (auditoria UX) | RT-07 (simplificação) |
|----------|----------------------|------------------------|
| Foco | Parecer SAP-first | **Menos telas/cliques/conceitos** |
| Filtros | Reorder shell | Chip + remover botão |
| Telas | Classificar | **Consolidar hubs** |
| Linguagem | Renomear | **Eliminar views engine** |
| Menu | ≤3/área | **14 entradas totais** |

---

## 5. Sign-off

| Fase | Resultado |
|------|-----------|
| RT-07 Planejamento | **CONCLUÍDO** |
| RT-07 Implementação | **PENDENTE** |
| Aceite final | **CONDICIONAL** |

---

## 6. Assinatura QA

```
[PARECER: RT-07 QA — PLANEJAMENTO APROVADO]

Implementação obrigatória antes de aceite final:
• P0: Eliminar 9 views órfãs + executive legado
• P0: Hub Financeiro (3 entradas)
• P0: Hub Produtos (1 entrada)
• P0: Remover banner executivo
• P1: Chip filtros + menu 14 entradas
• P1: Renomear títulos técnicos

ERP COMUM = REPROVADO (5 superfícies hoje)
PÓS RT-07 TARGET: 0 superfícies REPROVADAS na camada executiva
```

---

**IA-8 — Conclusão:** RT-07 **não adiciona nada** — **remove** até passar no anti-mediocrity.
