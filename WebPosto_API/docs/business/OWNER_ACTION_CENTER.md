---
# 🎯 OWNER ACTION CENTER | LOGOS
# Type: PRODUCT_VISION
# Version: 1.0
# Sprint: PRODUCT-03 — Owner Action Center
# Status: IMPLEMENTED
---

# Owner Action Center — Product Vision

> **O LOGOS deixa oficialmente de ser um Dashboard Financeiro.**
>
> **O LOGOS passa a ser um Gerente Digital para Proprietários de Postos.**

---

## 🎯 Missão

Mostrar, em **menos de 15 segundos**, quais decisões o proprietário deve tomar hoje para:

1. **Proteger caixa**
2. **Recuperar dinheiro**
3. **Aumentar lucro**

---

## 🔄 Mudança de Posicionamento

| Antes | Depois |
|-------|--------|
| Dashboard Financeiro | Gerente Digital |
| "Quanto vendi?" | "O que devo fazer agora?" |
| Gráficos e KPIs | Decisões e Ações |
| Informação passiva | Ação orientada |
| 50+ métricas | Top 5 decisões |

---

## 📋 Nova Home: Owner Action Center

### Estrutura

```
┌─────────────────────────────────────────────────────────┐
│  Bom dia. [Saudação personalizada]                        │
├─────────────────────────────────────────────────────────┤
│  📊 BUSINESS HEALTH [Score 0-100]                       │
├─────────────────────────────────────────────────────────┤
│  💰 DINHEIRO EM RISCO                                    │
│  Total: R$ XX,XXX | [Ver detalhes]                      │
├─────────────────────────────────────────────────────────┤
│  💵 DINHEIRO RECUPERÁVEL                                 │
│  Total: R$ XX,XXX | [Ver detalhes]                      │
├─────────────────────────────────────────────────────────┤
│  📈 OPORTUNIDADES                                        │
│  Total: R$ XX,XXX | [Ver detalhes]                      │
├─────────────────────────────────────────────────────────┤
│  ⭐ TOP 5 DECISÕES DO DIA                                │
│                                                           │
│  1. [Título] [R$ X,XXX] [Executar Agora →]              │
│  2. [Título] [R$ X,XXX] [Executar Agora →]              │
│  3. [Título] [R$ X,XXX] [Executar Agora →]              │
│  4. [Título] [R$ X,XXX] [Executar Agora →]              │
│  5. [Título] [R$ X,XXX] [Executar Agora →]              │
└─────────────────────────────────────────────────────────┘
```

---

## 💰 Dinheiro em Risco

O que detecta automaticamente:

| Risco | Descrição | Quanto Dinheiro |
|-------|-----------|-----------------|
| **Revenue Decline** | Receita caindo vs baseline | Até 30% do faturamento mensal |
| **Expense Anomaly** | Despesas acima do normal | Valor do excesso × 30 dias |
| **Cash Shortage** | Caixa negativo | Valor do déficit × 2 |
| **Margin Compression** | Margem caindo | Impacto no lucro mensal |
| **Voucher Anomaly** | Vales acima do padrão | Valor em risco × 30 dias |
| **Overdue Receivables** | Clientes inadimplentes | Total vencido |
| **Card Reconciliation** | Diferenças em cartões | Valor da divergência |

### Detecção Inteligente

- ✅ **Nunca usa limites fixos**
- ✅ Calcula baseline automaticamente
- ✅ Detecta anomalias estatísticas
- ✅ Considera sazonalidade (dia da semana)
- ✅ Confiança mínima: 60%

---

## 💵 Dinheiro Recuperável

O que descobre automaticamente:

| Tipo | Descrição | Probabilidade de Recuperação |
|------|-----------|------------------------------|
| **Overdue Receivables** | Contas vencidas | 80% (< 30 dias) / 60% (> 30 dias) |
| **Unbilled Sales** | Vendas não faturadas | 95% |
| **Card Reconciliation Gaps** | Pendências em cartões | 90% |
| **Duplicate Payments** | Pagamentos duplicados | 70% |
| **Billing Errors** | Erros de faturamento | 85% |
| **Unclaimed Credits** | Créditos não resgatados | 90% |
| **Negotiable Expenses** | Despesas negociáveis | 50% |

---

## 📈 Oportunidades

O que descobre automaticamente:

| Oportunidade | Descrição | Valor Potencial |
|--------------|-----------|-----------------|
| **Product Growth** | Produtos em crescimento | 20% mais volume |
| **Declining Products** | Produtos perdendo share | Recuperação do declínio |
| **Mix Optimization** | Upsell para premium | R$ 0,30/L adicional |
| **Digital Payments** | Tendência Pix | Redução de taxas |
| **Premium Opportunities** | Produtos premium | Margem maior |
| **Day Patterns** | Dias fortes/fracos | 20% em dias fracos |
| **Margin Improvement** | Revisão de preços | 1-2% no mix |

---

## ⭐ Top 5 Decisões do Dia

### Cada decisão responde obrigatoriamente:

1. **Por que apareceu?**
   - Explicação da detecção
   - Dados que triggeram
   - Deviations identificados

2. **Por que está nesta posição?**
   - Score de prioridade
   - Componentes do score
   - Urgência vs Impacto

3. **Quanto dinheiro envolve?**
   - Valor esperado
   - Probabilidade
   - Timeframe

4. **O que devo fazer?**
   - Ação específica
   - Passos recomendados
   - Tempo estimado

5. **Qual a confiança?**
   - Confidence Score
   - Origem dos dados
   - Endpoint consumido

### Priorização

**Algoritmo de Prioridade:**

| Fator | Peso | Descrição |
|-------|------|-----------|
| **Impacto Financeiro** | 30% | Valor monetário esperado |
| **Urgência** | 25% | Tempo para materializar |
| **Confiança** | 20% | Qualidade dos dados |
| **Facilidade** | 15% | Tempo para executar |
| **Tempo** | 10% | Quick wins privilegiados |

**Fórmula:**
```
Total Score = (Financial × 0.30) + 
              (Urgency × 0.25) + 
              (Confidence × 0.20) + 
              (Ease × 0.15) + 
              (Time × 0.10)
```

---

## 🎨 UX Premium

### Princípios de Design

Seguindo referências:
- Apple (simplicidade)
- Stripe (confiança)
- Linear (performance)
- Raycast (foco)
- Arc Browser (organização)

### Diretrizes

| Princípio | Aplicação |
|-----------|-----------|
| **Muito espaço em branco** | Cards com padding generoso |
| **Tipografia forte** | Títulos grandes, dados em destaque |
| **Poucos elementos** | Máximo 7 elementos na tela |
| **Poucas cores** | Palette minimalista |
| **Poucos gráficos** | Apenas quando agregam decisão |
| **Poucos cards** | 3-4 seções principais |

### Regra de Ouro

> **Se um componente não ajuda o proprietário a decidir alguma coisa, ele não deve existir.**

---

## 🔒 Regras de Confiança

### Confidence Score

| Score | Ação |
|-------|------|
| **≥ 90%** | Exibir com destaque máximo |
| **80-89%** | Exibir normalmente |
| **70-79%** | Exibir com ressalva |
| **60-69%** | Exibir com alerta |
| **< 60%** | **NÃO EXIBIR** |

### Requisitos Obrigatórios

Toda decisão DEVE ter:
- ✅ Origem conhecida (endpoint)
- ✅ Fórmula documentada
- ✅ Dados certificados
- ✅ Confidence Score ≥ 80%
- ✅ Rastreabilidade completa

---

## 🏪 Multi-Tenant

### Isolamento Total

- Cada posto comparado apenas consigo mesmo
- Nunca comparar empresas diferentes
- Baselines específicos por tenant

### Identificação

```python
{
    "tenant_id": "tenant_001",
    "empresa_codigo": "11495",
    "company_name": "POSTO VIP"
}
```

---

## 📊 API Endpoints

### Core Endpoints

| Endpoint | Método | Descrição |
|----------|--------|-----------|
| `/api/v1/owner-action-center/summary` | GET | Sumário completo |
| `/api/v1/owner-action-center/money-at-risk` | GET | Dinheiro em risco |
| `/api/v1/owner-action-center/recoverable` | GET | Dinheiro recuperável |
| `/api/v1/owner-action-center/opportunities` | GET | Oportunidades |
| `/api/v1/owner-action-center/top5` | GET | Top 5 decisões |
| `/api/v1/owner-action-center/actions` | GET | Todas as ações |
| `/api/v1/owner-action-center/business-health` | GET | Saúde do negócio |
| `/api/v1/owner-action-center/today` | GET | Hoje (conveniência) |
| `/api/v1/owner-action-center/execute` | POST | Executar ação |

### Parâmetros

- `dataInicial`: Data início (YYYY-MM-DD)
- `dataFinal`: Data fim (YYYY-MM-DD)
- `empresaCodigo`: Código WebPosto (obrigatório)
- `tenantId`: Tenant ID (opcional, default = empresaCodigo)
- `status`: Filtro por status (pending, in_progress, completed)
- `priority`: Filtro por prioridade (critical, high, medium, low)

---

## 🚀 Próximos Passos

### Implementação Frontend

1. Criar nova Home — Owner Action Center
2. Componentizar: BusinessHealth, MoneyAtRisk, RecoverableMoney, Opportunities, Top5Decisions
3. Implementar botão "Executar Agora"
4. Adicionar filtros e busca
5. Implementar notificações

### Melhorias Backend

1. Integrar com serviços reais de dados
2. Implementar cache TTL
3. Adicionar mais detectores de risco
4. Expandir oportunidades
5. Machine learning para baselines

---

## ✅ Critérios de Sucesso

| Métrica | Target |
|---------|--------|
| Tempo para entender | < 15 segundos |
| Decisões relevantes | ≥ 80% aprovadas pelo owner |
| Confiança média | ≥ 85% |
| Ações executadas | ≥ 60% das sugeridas |
| Valor recuperado/prevenido | > R$ 10.000/mês |
| NPS do owner | > 50 |

---

**[OWNER ACTION CENTER — PRODUCT-03]**

*Status: IMPLEMENTED | Core Engine: COMPLETE | API: COMPLETE | Frontend: PENDING*
