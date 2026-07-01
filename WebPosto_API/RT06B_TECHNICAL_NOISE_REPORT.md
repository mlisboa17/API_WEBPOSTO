# RT-06B — Agente 6: Technical Noise Removal

**Objetivo:** Ocultar ruído técnico das telas de negócio.  
**Destino permitido:** Administração · Diagnóstico Técnico

---

## Inventário de ruído

| Elemento | Onde aparece | 1ª dobra? | Ação |
|----------|--------------|-----------|------|
| Snapshot / idade / origem | `financialResilienceBanner` | **SIM** — Receitas, Despesas | **MOVER** |
| Saúde / confiança / circuit | Idem | **SIM** | **MOVER** |
| Lineage fiscal | `fiscalReconciliation.js` | Não — `<details>` | OK |
| Scheduler / recovery | `financialOperations.js` | Admin | OK |
| Circuit breaker UI | `administration.js` | Admin | OK |
| Health score cards | `financialOperationsCenter.js` | Admin/Diagnóstico | OK |
| Snapshot status bar | `executiveDashboard.js` (legado) | Sim se acessado | **REMOVER view** |
| ParecerFinal / QA | Cockpits adapter | Detalhe recolhido | OK |
| Copilot / calibration | `commercialLearning.js`, etc. | Detalhe | OK |
| Motor strip “Avançado” | `navigationShell.js` | Aba secundária | OK (rotulado) |
| `data-area` admin gate | RT-06A parcial | — | Verificar cobertura |

---

## Telas de negócio — ruído na 1ª dobra

| Tela | Ruído visível | Classificação |
|------|---------------|---------------|
| Receitas | Banner resiliência completo | **REPROVADA** |
| Despesas | Banner resiliência completo | **REPROVADA** |
| Resumo Executivo | Mínimo | **APROVADA** |
| Demais prioritárias | Sem ruído técnico explícito | **APROVADA** |

---

## RT-06A — banner técnico

`app.js` / RT-06A: banner oculto fora de `body[data-area="administracao"]` — **parcialmente implementado** para banner global, mas `financialResilienceBanner` é **por página** e ignora essa regra.

---

## Plano de remoção (UX only)

### P0
1. Não renderizar `renderFinancialResilienceBanner` em Receitas/Despesas na 1ª dobra
2. Mover indicador de origem para Administração → Sistema (link discreto “Origem dos dados”)

### P1
3. Remover `#executiveView` / `executiveDashboard.js` do roteamento
4. Garantir `motor-strip--technical` oculto ou estilizado como secundário em telas executivas

### P2
5. Renomear labels expostos: “Copilot” → “Oportunidades”; “Engine” → nunca na UI executiva

---

## Classificação global

| Critério | Status |
|----------|--------|
| Ruído fora de Admin | **PARCIAL** — 2 telas financeiras violam |
| Lineage/scheduler ocultos | **APROVADO** |
| Motores em faixa Avançado | **APROVADO** |

---

**Agente 6 — Conclusão:** Ruído técnico **majoritariamente controlado**, exceto **banner resiliência** = bloqueador P0.
