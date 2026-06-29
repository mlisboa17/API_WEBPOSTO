---
# 📋 OWNER DECISIONS | LOGOS
# Type: BUSINESS_RULES
# Version: 1.0
# Sprint: PRODUCT-03 — Owner Action Center
# Status: IMPLEMENTED
---

# Owner Decisions — Business Rules

> Regras de negócio para geração e priorização de decisões.

---

## 🎯 Princípio Central

**O LOGOS não mostra dados. O LOGOS entrega decisões.**

Cada decisão deve responder:

> *"Isso ajuda o proprietário a ganhar dinheiro, evitar perdas ou economizar tempo?"*

Se a resposta for **NÃO**, a decisão não deve ser gerada.

---

## 📋 Estrutura de uma Decisão

### Campos Obrigatórios

| Campo | Descrição | Formato |
|-------|-----------|---------|
| `id` | Identificador único | `dec_[tenant]_[rank]_[data]` |
| `rank` | Posição (1-5) | Número 1-5 |
| `title` | Título da decisão | Máx 100 caracteres |
| `description` | Descrição completa | Máx 500 caracteres |
| `decision_question` | Pergunta para o owner | Frase direta |
| `why_appeared` | Por que apareceu? | Explicação de trigger |
| `why_ranked` | Por que nesta posição? | Justificativa do score |
| `money_involved` | Quanto dinheiro? | Valor e contexto |
| `what_rule_triggered` | Qual regra? | Endpoint e método |
| `action` | Ação sugerida | DecisionAction completo |

### Campos de Scoring

| Campo | Descrição | Escala |
|-------|-----------|--------|
| `total_score` | Score final | 0-100 |
| `financial_impact_score` | Impacto financeiro | 0-100 |
| `urgency_score` | Urgência | 0-100 |
| `confidence_score` | Confiança | 0-100 |
| `ease_score` | Facilidade | 0-100 |
| `time_score` | Tempo | 0-100 |

---

## 💰 Decisões de Dinheiro em Risco

### Regra R001 — Revenue Decline

**Condição:** Receita atual < 80% da baseline

**Score de Urgência:**
- > 30% abaixo: 1.0 (CRITICAL)
- 20-30% abaixo: 0.9 (HIGH)

**Valor em Risco:**
```
Valor = (Baseline Diário × 7 dias) × (Declínio %)
```

**Exemplo:**
```
Baseline: R$ 50.000/dia
Atual: R$ 35.000/dia (-30%)
Valor em Risco: R$ 50.000 × 7 × 0.30 = R$ 105.000
```

**Ação Sugerida:**
"Revisar performance de vendas imediatamente. Verificar: preços vs concorrência, nível de estoque, presença de funcionários, problemas operacionais."

### Regra R002 — Expense Anomaly

**Condição:** Despesa atual > 130% da baseline

**Score de Urgência:**
- > 50% acima: 0.8 (HIGH)
- 30-50% acima: 0.6 (MEDIUM)

**Valor em Risco:**
```
Valor = (Despesa Atual - Baseline) × 30 dias
```

**Ação Sugerida:**
"Revisar despesas anormais. Verificar: vales de funcionários, pagamentos a fornecedores, compras atípicas, pagamentos duplicados."

### Regra R003 — Cash Shortage

**Condição:** Posição de caixa < -R$ 1.000

**Score de Urgência:** 1.0 (CRITICAL)

**Valor em Risco:**
```
Valor = |Posição Caixa| × 2
```

**Ação Sugerida:**
"Resolver déficit de caixa imediatamente. Ações: cobrar clientes inadimplentes, negociar prazos com fornecedores, verificar depósitos pendentes."

### Regra R004 — Margin Compression

**Condição:** Margem atual < Margem baseline - 5%

**Score de Urgência:**
- > 10% abaixo: 0.9 (HIGH)
- 5-10% abaixo: 0.7 (MEDIUM)

**Valor em Risco:**
```
Valor = Faturamento Mensal × (Declínio Margem %)
```

**Ação Sugerida:**
"Analisar compressão de margem. Verificar: preços de compra de combustível, mix de produtos, descontos concedidos, alterações de preços de fornecedores."

### Regra R005 — Overdue Receivables

**Condição:** Existem contas vencidas

**Score de Urgência:**
- > 60 dias: 0.95 (CRITICAL)
- 30-60 dias: 0.8 (HIGH)
- < 30 dias: 0.6 (MEDIUM)

**Valor em Risco:**
```
Valor = Total Vencido × 0.30 (30% perda esperada)
```

**Ação Sugerida:**
"Contatar clientes inadimplentes. Priorizar: contas mais antigas, maiores valores, clientes históricos. Oferecer planos de pagamento se necessário."

---

## 💵 Decisões de Dinheiro Recuperável

### Regra REC001 — Overdue Receivables Recovery

**Condição:** Total vencido > R$ 1.000

**Probabilidade de Recuperação:**
- < 30 dias: 80%
- 30-60 dias: 60%
- > 60 dias: 40%

**Valor Recuperável:**
```
Valor = Total Vencido × Probabilidade
```

**Ação Sugerida:**
"Cobrar R$ [valor] de [count] clientes inadimplentes. Começar pelas contas mais antigas. Documentar compromissos de pagamento."

### Regra REC002 — Unbilled Sales

**Condição:** Existem vendas não faturadas

**Probabilidade de Recuperação:** 95%

**Ação Sugerida:**
"Faturar [count] transações não faturadas imediatamente. Gerar notas fiscais e enviar aos clientes."

### Regra REC003 — Card Reconciliation

**Condição:** Diferença em conciliação > R$ 500

**Probabilidade de Recuperação:** 90%

**Ação Sugerida:**
"Reconciliar diferença de R$ [valor] em transações de cartão. Verificar: liquidações pendentes, chargebacks, erros de processamento."

---

## 📈 Decisões de Oportunidades

### Regra OPP001 — Product Growth Trend

**Condição:** Crescimento de produto > 40% vs baseline

**Trend Strength:**
```
Força = min(Crescimento % / 100, 1.0)
```

**Valor da Oportunidade:**
```
Valor = Receita Atual × 0.20 (20% mais volume)
```

**Ação Sugerida:**
"Capitalizar crescimento de [produto]. Ações: garantir estoque adequado, considerar variantes premium, promover aos clientes."

### Regra OPP002 — Mix Optimization

**Condição:** % Premium < 15% do mix

**Gap:**
```
Gap = 15% - % Premium Atual
```

**Valor da Oportunidade:**
```
Valor = Faturamento Total × Gap × R$ 0.30/L (diferença premium)
```

**Ação Sugerida:**
"Aumentar foco em produtos premium. Treinar atendentes para fazer upsell. Instalar sinalização adequada."

---

## ⚖️ Algoritmo de Priorização

### Componentes do Score

| Componente | Peso | Cálculo |
|------------|------|---------|
| **Impacto Financeiro** | 30% | Valor esperado em tiers |
| **Urgência** | 25% | Tempo até materializar |
| **Confiança** | 20% | Qualidade dos dados |
| **Facilidade** | 15% | Tempo para executar |
| **Tempo** | 10% | Quick wins = bonus |

### Fórmula

```python
Total Score = (
    FinancialScore × 0.30 +
    UrgencyScore × 0.25 +
    ConfidenceScore × 0.20 +
    EaseScore × 0.15 +
    TimeScore × 0.10
) × PriorityMultiplier
```

### Multiplicadores

| Prioridade | Multiplicador |
|------------|---------------|
| CRITICAL | 1.15 |
| HIGH | 1.05 |
| MEDIUM | 1.00 |
| LOW | 0.95 |

### Ajustes Adicionais

| Condição | Ajuste |
|----------|--------|
| URGENT + CRITICAL | +10% |
| Confidence < 60% | -20% |
| Time < 15 min | +5% |

---

## 📊 Tiers de Impacto Financeiro

| Valor (R$) | Score | Classificação |
|------------|-------|---------------|
| > 100.000 | 100 | Excepcional |
| 50.000 - 100.000 | 90 | Muito Alto |
| 20.000 - 50.000 | 80 | Alto |
| 10.000 - 20.000 | 70 | Significativo |
| 5.000 - 10.000 | 60 | Moderado |
| 2.000 - 5.000 | 50 | Pequeno |
| 1.000 - 2.000 | 40 | Mínimo |
| 500 - 1.000 | 30 | Marginal |
| 100 - 500 | 20 | Baixo |
| < 100 | 10 | Muito Baixo |

---

## 🎨 Linguagem das Decisões

### Principios

1. **Simples:** Nenhum termo técnico
2. **Direto:** Ir direto ao ponto
3. **Actionable:** Começar com verbo
4. **Quantificado:** Sempre incluir valor
5. **Personalizado:** Usar dados do posto

### Templates

#### Título
```
[Verbo] [Objeto] [Valor]

Exemplos:
- "Review overdue accounts: R$ 12,450"
- "Collect from 3 customers: R$ 8,200"
- "Train staff on premium upselling"
```

#### Descrição
```
Contexto + Impacto + Ações

Exemplo:
"3 customer accounts are overdue totaling R$ 12,450. 
Oldest is 45 days overdue. Call each customer to 
arrange payment. Offer 10% discount for immediate 
payment if needed."
```

#### Pergunta de Decisão
```
"Will you [ação] to [resultado]?"

Exemplo:
"Will you contact 3 overdue customers to recover 
R$ 12,450?"
```

---

## ✅ Critérios de Geração

### Uma decisão SÓ é gerada se:

1. ✅ **Impacto financeiro > R$ 100**
2. ✅ **Confidence score ≥ 60%**
3. ✅ **Urgência justificável**
4. ✅ **Ação executável**
5. ✅ **Dados reais disponíveis**
6. ✅ **Origem rastreável**

### Uma decisão NUNCA é gerada se:

1. ❌ Sem dados reais
2. ❌ Baseada em mock/simulação
3. ❌ Confidence < 60%
4. ❌ Ação não definida
5. ❌ Sem valor financeiro
6. ❌ Origem desconhecida

---

## 🔄 Ciclo de Vida de uma Decisão

```
┌─────────────────────────────────────────────────────────┐
│  1. DETECÇÃO                                            │
│     Motor identifica anomalia/oportunidade              │
└────────────────┬────────────────────────────────────────┘
                 │
                 ▼
┌─────────────────────────────────────────────────────────┐
│  2. AVALIAÇÃO                                           │
│     Calcular scores e prioridade                          │
└────────────────┬────────────────────────────────────────┘
                 │
                 ▼
┌─────────────────────────────────────────────────────────┐
│  3. CERTIFICAÇÃO                                        │
│     Verificar confidence ≥ 80%                            │
└────────────────┬────────────────────────────────────────┘
                 │
                 ▼
┌─────────────────────────────────────────────────────────┐
│  4. EXIBIÇÃO                                            │
│     Mostrar ao proprietário                               │
└────────────────┬────────────────────────────────────────┘
                 │
                 ▼
┌─────────────────────────────────────────────────────────┐
│  5. EXECUÇÃO                                            │
│     Proprietário executa ação                             │
└────────────────┬────────────────────────────────────────┘
                 │
                 ▼
┌─────────────────────────────────────────────────────────┐
│  6. FECHAMENTO                                          │
│     Marcar como concluída                                 │
└─────────────────────────────────────────────────────────┘
```

---

**[OWNER DECISIONS — PRODUCT-03]**

*Status: IMPLEMENTED | Rules: ACTIVE | Algorithm: VALIDATED*
