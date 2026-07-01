# RT-07 — IA-4: Products Consolidation

**Problema:** Mix · Resultados · Oportunidades geram confusão como 3 telas separadas.

---

## 1. Situação atual

```
Produtos Vendidos (nav)
├── Vendas & Mix      → nonFuelProducts.js     ✓ forte
├── Oportunidades     → commercialCopilot.js   ⚠ overlap com Mix
├── Resultados        → commercialLearning.js  ⚠ overlap com Indicadores
└── Avançado
    └── Plano de ações → commercialExecution.js
```

**Confusão identificada:**
| Tela | O que o usuário espera | O que encontra |
|------|------------------------|----------------|
| Vendas & Mix | Pareto, mix, filiais | ✓ Claro |
| Oportunidades | Ações comerciais | Copilot + recomendações genéricas |
| Resultados | ROI campanhas | Calibração + learning engine |

---

## 2. Proposta — 1 entrada, 3 sub-abas

### Menu: **Produtos Vendidos** (1 aba nav)

| Sub-aba | Origem | Conteúdo |
|---------|--------|----------|
| **Mix & Vendas** | `nonFuelProducts.js` | Pareto, KPIs, alertas comerciais — **default** |
| **Oportunidades** | `commercialCopilot.js` | Top oportunidades + ações (sem label “copilot”) |
| **Performance** | `commercialLearning.js` | Resultados campanhas (sem “calibração engine”) |

### Widgets (não telas)

| Conteúdo atual | Destino |
|----------------|---------|
| `commercialExecution` — Plano de ações | Card no detalhe de Oportunidades |
| Alertas cross-area no Resumo | Link deep-link → sub-aba Oportunidades |

---

## 3. Renomeações (linguagem executiva)

| De | Para |
|----|------|
| Oportunidades (aba nav) | *(absorvida)* |
| Resultados (aba nav) | **Performance** (sub-aba) |
| Commercial Copilot | **Oportunidades de venda** |
| Closed loop / calibração | **Resultado de ações** |
| Plano de ações (motor) | **Próximos passos** (widget) |

---

## 4. Wireframe

```
Produtos Vendidos
─────────────────
[Mix & Vendas] [Oportunidades] [Performance]

4 KPIs | Gráfico Pareto | 3 alertas   ← só na sub-aba Mix (1ª dobra)

<details> Detalhamento …
```

Sub-abas Oportunidades e Performance: mesma 1ª dobra RT-06, conteúdo atual reciclado.

---

## 5. O que permanece / vira aba / vira widget

| Item | Decisão |
|------|---------|
| `nonFuelProducts` | **Tela principal** (sub-aba default) |
| `commercialCopilot` | **Sub-aba** |
| `commercialLearning` | **Sub-aba** Performance |
| `commercialExecution` | **Widget** no detalhe |
| Nav: 3 abas → 1 aba | **−2 entradas menu** |

---

## 6. Sem alteração de backend

- Mesmas APIs: `/commercial-copilot`, `/commercial-learning`, `/non-fuel-products`
- Mesmos motores no payload — só não expostos na UI executiva

---

## 7. Classificação

| Critério | Status |
|----------|--------|
| Remove confusão Mix/Resultados/Oportunidades | **APROVADO** |
| Mantém funcionalidade | **APROVADO** |
| Reduz entradas nav 4→1 | **APROVADO** |
| Remove complexidade? | **SIM** |

---

**IA-4 — Conclusão:** Produtos = **1 tela · 3 sub-abas · 1 widget**. Eliminar 3 entradas de menu sem perda funcional.
