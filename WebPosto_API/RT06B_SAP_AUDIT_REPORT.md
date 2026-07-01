# RT-06B — Agente 1: SAP UX Auditor

**Data:** 2026-06-09  
**Escopo:** Telas RT-01 + shell global  
**Referências:** SAP Fiori · SAP Analytics Cloud · Power BI Premium · Tableau Executive

---

## Metodologia

Comparação qualitativa contra padrões SAP-FIRST:

| Dimensão | SAP / Enterprise | LOGOS SPACE (atual) |
|----------|------------------|---------------------|
| Hierarquia | Insight → ação → detalhe | Filtros → abas → conteúdo |
| Densidade | Respirada, cards grandes | Melhorou (RT-06A), ainda densa em detalhe |
| Tipografia | Semibold títulos, KPI hero | Parcial — KPIs RT-06 ok |
| Cor | Neutros + 1 accent verde | Alinhado (`--exec-green`) |
| Filtros | Contextuais, colapsados | Período+Empresa ok; barra ainda alta |
| Ruído | Zero técnico na 1ª dobra | Banner resiliência em Receitas/Despesas |

---

## Veredicto por tela prioritária

| Tela | Parece SAP? | Motivo |
|------|-------------|--------|
| Resumo Executivo | **NÃO** | Filtros acima do negócio; boa 1ª dobra |
| Alertas | **NÃO** | Adapter genérico; falta drama executivo |
| Receitas | **NÃO** | Banner snapshot/circuit na 1ª dobra |
| Despesas | **NÃO** | Idem + muitos filtros avançados na view |
| Inteligência Financeira | **PARCIAL** | Cards ok; KPI “Margem” = score confunde |
| Produtos Vendidos | **PARCIAL** | Pareto + alertas comerciais — mais próximo |
| Vendas Combustível | **NÃO** | KPIs genéricos; alertas insuficientes |
| NFCE | **PARCIAL** | Gráfico fiscal ok; rótulos financeiros genéricos |
| Conciliação Fiscal | **PARCIAL** | Estrutura ok; lineage no detalhe (correto) |

**Resumo:** 0/9 **SIM** · 3/9 **PARCIAL** · 6/9 **NÃO**

---

## Achados críticos (SAP gap)

### P0 — Shell filters-first
`index.html`: `#filtersContainer` precede `#areaTabs` e views. SAP Fiori coloca filtros **contextuais abaixo do título** ou em barra recolhida.

### P0 — Banner técnico na 1ª dobra
`financialResilienceBanner.js` em Receitas/Despesas expõe: origem, idade snapshot, saúde, confiança, circuit.

### P1 — KPIs semânticos incorretos
NFCE e Vendas Combustível reutilizam slots Receita/Despesa/Margem para métricas não financeiras.

### P1 — Botões redundantes
Topbar **Atualizar** + filtros **Atualizar dados** + DRP **Aplicar** — três caminhos de refresh.

### P2 — View legada `executiveDashboard`
Ainda no DOM; expõe snapshot/lineage; não está na navegação RT-03B.

---

## Pontos positivos (RT-06 / RT-06A)

- `executiveFirstFold` + `executiveCockpitAdapter` — padrão unificado
- Date Range Picker corporativo (DRP) — sem digitação manual
- Brief + painel de decisão recolhidos em `<details>`
- Navegação ≤3 abas por macroárea (RT-03B)
- Motores técnicos na faixa “Avançado”

---

## Recomendações SAP-FIRST

1. Mover filtros para **abaixo das abas** ou colapsar barra por padrão
2. Relocar banner resiliência para Administração ou `<details>`
3. KPIs contextuais por domínio (fiscal, combustível, financeiro)
4. Unificar refresh: **Aplicar** no DRP = único gatilho; ocultar “Atualizar dados”
5. Remover view legada `executive`

---

**Agente 1 — Conclusão:** Plataforma **evoluiu**, mas **não passa** no teste “parece SAP” na 1ª impressão. Mediocreidade ERP = **REPROVADA** no shell; excelência parcial nas páginas de negócio.
