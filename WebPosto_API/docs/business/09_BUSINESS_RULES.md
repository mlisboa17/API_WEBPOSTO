# Business Rules
## Regras de Negócio - LOGOS SPACE

**Versão:** 1.0
**Data:** 2026-06-28
**Status:** Ativo
**Sprint:** DOCS-02

---

## 🎯 Princípios Fundamentais

> **Toda regra de negócio deve estar documentada aqui, não apenas no código.**

---

## 💰 Receita (Revenue)

### Definição

```
Receita = Total de vendas - Cancelamentos - Devoluções
```

### Componentes

| Componente | Fórmula | Fonte |
|------------|---------|-------|
| **Vendas Brutas** | `SUM(valor_total)` | `fact_venda` |
| **Cancelamentos** | `SUM(valor_total WHERE status='CANCELADO')` | `fact_venda` |
| **Devoluções** | `SUM(valor_devolucao)` | `fact_venda` |

### Regras

1. **Vendas incluem:** Combustíveis, produtos, serviços
2. **Vendas excluem:** ICMS, PIS/COFINS, outros impostos (quando destacados)
3. **Período:** Data de emissão da nota/venda
4. **Consolidação:** Por `empresaCodigo` (filial)

### Cálculo do Backend

```python
receita_liquida = (
    sum(v.valor_total for v in vendas if v.status != 'CANCELADO')
    - sum(v.valor_devolucao for v in vendas)
)
```

---

## 💸 Fluxo de Caixa (Cash Flow)

### Definição

```
Fluxo de Caixa = Receitas - Despesas
Saldo = Saldo Anterior + Fluxo de Caixa
```

### Componentes

| Componente | Descrição | Fonte |
|------------|-----------|-------|
| **Entradas** | Recebimentos de vendas, outros recebimentos | `fact_receber` |
| **Saídas** | Pagamentos a fornecedores, despesas operacionais | `fact_pagar` |
| **Transferências** | Movimentação entre contas | Interno |

### Regras

1. **Entradas realizadas:** Data de recebimento efetivo
2. **Saídas realizadas:** Data de pagamento efetivo
3. **Previsões:** Entradas/saídas esperadas (não realizadas)
4. **Período:** Analisado diariamente, consolidado mensalmente

### Alertas

| Condição | Severidade | Ação |
|----------|------------|------|
| Saldo < 10% da média histórica | 🔴 Crítico | Alerta imediato |
| Fluxo negativo por 3+ dias | 🟠 Alto | Notificação |
| Projeção de déficit em 7 dias | 🟡 Médio | Relatório |

---

## ⛽ Litros (Fuel Volume)

### Definição

```
Volume Total = SUM(litros) por tipo de combustível
```

### Tipos de Combustível

| Código | Nome | Categoria |
|--------|------|-----------|
| GASOLINA | Gasolina Comum | Derivados |
| ETANOL | Etanol Hidratado | Bio |
| DIESEL | Diesel S500 | Derivados |
| DIESELS10 | Diesel S10 | Derivados |
| GNV | Gás Natural | Gás |

### Regras

1. **Litros medidos:** Pela bomba (Bico)
2. **Temperatura:** Litros a 20°C (correção opcional)
3. **Período:** Data/hora do abastecimento
4. **Consolidação:** Por bico, bomba, ilha, filial

### KPIs

| KPI | Fórmula | Meta |
|-----|---------|------|
| **Ticket Médio** | `Receita / Nº de abastecimentos` | > R$ 100 |
| **Litros por Bico** | `Volume / Nº de bicos` | > 10.000 L/dia |
| **Margem por Litro** | `(Preço - Custo) / Litros` | > R$ 0.20/L |

---

## 📊 Benchmark

### Definição

Comparação de performance entre filiais ou contra mercado.

### Tipos

1. **Intra-rede:** Filial A vs Filial B
2. **Histórico:** Mês atual vs mês anterior
3. **Meta:** Realizado vs orçado
4. **Mercado:** Vs concorrência (quando disponível)

### Regras

1. **Normalização:** Usar mesma base (dia útil, volume similar)
2. **Período:** Comparar períodos iguais
3. **Moeda:** Valores em Reais (R$)
4. **Ajustes:** Considerar sazonalidade quando relevante

### Cálculo de Score

```python
score = (
    receita_score * 0.30 +
    lucro_score * 0.25 +
    eficiencia_score * 0.20 +
    satisfacao_score * 0.15 +
    crescimento_score * 0.10
)
```

---

## 🔮 Forecast

### Definição

Projeção de indicadores futuros baseada em dados históricos.

### Métodos

1. **Média Móvel:** Média dos últimos N períodos
2. **Tendência:** Regressão linear
3. **Sazonalidade:** Ajuste por padrões históricos
4. **Combinação:** Média ponderada dos métodos

### Regras

1. **Confiança:** Indicar nível de confiança (ex: 80%)
2. **Período base:** Mínimo 3 meses de histórico
3. **Atualização:** Recalcular semanalmente
4. **Variáveis:** Considerar feriados, eventos locais

### Exemplo: Previsão de Vendas

```python
forecast_semana = (
    media_4_semanas_anteriores * 0.4 +
    tendencia_linear * 0.3 +
    ajuste_sazonal * 0.3
)
```

---

## 🚨 Revenue Leakage (Vazão de Receita)

### Definição

```
Leakage = Receita Esperada - Receita Realizada
```

### Fontes de Leakage

| Fonte | Descrição | Detecção |
|-------|-----------|----------|
| **Gap de Preço** | Venda abaixo do preço definido | `preco_venda < preco_minimo` |
| **Perda de Estoque** | Diferença física vs sistema | Inventário |
| **Descontos Excessivos** | Desconto > limite aprovado | Auditoria |
| **Fraudes** | Movimentações suspeitas | ML/Anomalias |
| **Erros Operacionais** | Lançamentos incorretos | Conciliação |

### Regras

1. **Limite de alerta:** > 0.5% da receita bruta
2. **Investigação:** > 1% da receita bruta
3. **Ação imediata:** > 2% da receita bruta
4. **Meta:** < 0.3% da receita bruta

### Detecção Automática

```python
if leakage_percent > 2.0:
    alert_level = 'CRITICAL'
    action = 'INVESTIGATE_IMMEDIATE'
elif leakage_percent > 1.0:
    alert_level = 'HIGH'
    action = 'INVESTIGATE_24H'
elif leakage_percent > 0.5:
    alert_level = 'MEDIUM'
    action = 'REVIEW_WEEKLY'
```

---

## 📋 Conciliação

### Definição

Comparação e alinhamento de dados entre sistemas.

### Pontos de Conciliação

| Sistema A | Sistema B | Frequência | Tolerância |
|-----------|-----------|------------|------------|
| WebPosto Vendas | ERP | Diária | R$ 0.01 |
| Estoque Físico | Sistema | Semanal | 0.1% |
| Caixa | Banco | Diária | R$ 0.01 |
| NFCE | Vendas | Diária | 0% |

### Regras

1. **Diferenças:** Documentar e justificar
2. **Tolerância:** Acima do limite = investigação
3. **Prazo:** Resolver em até 48h
4. **Histórico:** Manter log de ajustes

---

## 🔔 Alertas

### Hierarquia

| Nível | Cor | Condição | Resposta Esperada |
|-------|-----|----------|-------------------|
| 🔴 **CRÍTICO** | Vermelho | Perda > 5%, segurança, compliance | Imediata (< 1h) |
| 🟠 **ALTO** | Laranja | Perda 2-5%, performance ruim | 4h |
| 🟡 **MÉDIO** | Amarelo | Perda 0.5-2%, atenção | 24h |
| 🔵 **BAIXO** | Azul | Informativo, oportunidade | Semanal |

### Tipos de Alerta

#### Financeiros
- Fluxo de caixa negativo
- Inadimplência crescente
- Margem abaixo do esperado
- Receita em queda

#### Operacionais
- Estoque crítico
- Volume de vendas em queda
- Problemas de abastecimento
- Equipamento offline

#### Fiscais
- Divergência NFCE
- Prazo de obrigações
- Alíquotas incorretas
- Documentação pendente

#### IA/Anomalias
- Padrão de venda anômalo
- Comportamento suspeito
- Preço fora da curva
- Predição de problema

---

## 🏥 Business Health Score

### Definição

Score consolidado (0-100) da saúde do negócio.

### Componentes

| Componente | Peso | Descrição |
|------------|------|-----------|
| **Receita** | 25% | Performance de vendas |
| **Fluxo de Caixa** | 20% | Saúde financeira |
| **Estoque** | 10% | Giro e disponibilidade |
| **Inadimplência** | 15% | Contas a receber |
| **Crescimento** | 15% | Comparativo períodos |
| **Alertas** | 10% | Problemas ativos |
| **Divergências** | 5% | Conciliação |

### Classificação

| Score | Classificação | Cor | Ação |
|-------|---------------|-----|------|
| 95-100 | Excelente | 🟢 | Manter |
| 80-94 | Saudável | 🟢 | Otimizar |
| 60-79 | Atenção | 🟡 | Investigar |
| 40-59 | Risco | 🟠 | Ação imediata |
| 0-39 | Crítico | 🔴 | Crise |

### Cálculo

```python
health_score = (
    revenue_score * 0.25 +
    cash_flow_score * 0.20 +
    inventory_score * 0.10 +
    delinquency_score * 0.15 +
    growth_score * 0.15 +
    alerts_score * 0.10 +
    divergence_score * 0.05
)
```

---

## 📝 Documentação de Regras

### Onde Documentar

1. **Este arquivo (`09_BUSINESS_RULES.md`)** - Regras globais
2. **Código (docstrings)** - Implementação específica
3. **Tests** - Casos de teste das regras
4. **API docs** - Contratos de input/output

### Template para Nova Regra

```markdown
### [Nome da Regra]

**Definição:**
Descrição clara do que a regra calcula/define.

**Fórmula:**
```
Resultado = Componente A + Componente B - Componente C
```

**Componentes:**
| Componente | Descrição | Fonte |
|------------|-----------|-------|
| A | ... | Tabela X |
| B | ... | Tabela Y |

**Regras:**
1. [Regra específica 1]
2. [Regra específica 2]

**Implementação:**
```python
# Arquivo: src/services/xxx.py
def calcular_regra():
    ...
```
```

---

## 🔄 Manutenção

### Quando Atualizar

- Nova regra de negócio definida
- Alteração em regra existente
- Descoberta de edge case
- Auditoria de compliance

### Processo

1. Propor alteração neste documento
2. Revisar impacto nos sistemas
3. Atualizar implementação
4. Atualizar testes
5. Comunicar stakeholders

---

**[BUSINESS RULES — APROVADO]**

*Atualizar ao definir novas regras ou alterar existentes*
