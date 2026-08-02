# Sprint 48 — Ciclo de Caixa, Taxas de Cartão e Visão Operacional

## Objetivo

Separar estruturalmente a **Visão Executiva (Presidência/Diretoria)** da **Visão Operacional (Gerente de Pista/Loja)**, além de implementar indicadores críticos de proteção de caixa: Vácuo Financeiro, Margem Líquida pós-Cartões e Quebra de Caixa.

## Entregas

### 1. CashCycleService — Vácuo Financeiro e Necessidade de Capital

- Cálculo do prazo médio de recebimento por método de pagamento:
  - Crédito: 30 dias
  - Débito: 1 dia
  - PIX/Dinheiro: 0 dias
  - Frotista: 15 dias
- Cálculo do prazo médio de pagamento a fornecedores (default 3 dias para combustível)
- `vacuo_financeiro_dias = prazo_recebimento - prazo_pagamento`
- `necessidade_capital_giro_rs = vacuo × faturamento_diario_medio`
- Status: `SAUDAVEL` (vácuo ≤ 0), `ATENCAO` (1-15 dias), `CRITICO` (> 15 dias)
- Simulação de custo de antecipação de recebíveis

### 2. CardFeeImpactService — Margem Líquida Pós-Cartões

- Taxas padrão por bandeira:
  - VISA/Mastercard: Crédito 2.49%, Débito 1.49%
  - ELO: Crédito 2.69%, Débito 1.59%
  - AMEX: Crédito 3.19%, Débito 2.19%
- Consumo do campo `taxaPercentual` do WebPosto quando disponível
- Cálculo da margem líquida: `Receita - CMV - Taxas_Cartão`
- Impacto das taxas na margem bruta (%)
- Agregação por bandeira e método

### 3. CashBreakService — Quebra de Caixa

- Régua de tolerância:
  - Normal: ≤ R$ 20,00
  - Warning: R$ 20,01 a R$ 100,00
  - Crítico: > R$ 100,00
- Análise por fechamento de caixa
- Agregação por operador
- Lista de operadores com quebra crítica
- Risk Score calculado

### 4. FuelLossService — Dias para Ruptura

- Nova propriedade `dias_para_ruptura = estoque_medido / venda_media_diaria`
- Flag `ruptura_iminente` (≤ 3 dias)
- Integração com endpoint de tanques em risco

### 5. ConvenienceAnalyticsService — Filtro Capital Parado

- Parâmetros `dias_minimo` e `classificacao_abc_filter` em `detect_idle_stock`
- Endpoint específico para Capital Parado Curva C > 60 dias

### 6. Namespaces de API

#### /api/v1/executive/ (Presidência/Diretoria)

| Endpoint | Descrição |
|----------|-----------|
| `/dashboard` | Síntese executiva consolidada |
| `/cash-cycle` | Vácuo financeiro e necessidade de capital |
| `/card-fees-impact` | Impacto das taxas de cartão na margem |
| `/fuel-summary` | Resumo de perdas e variação térmica |
| `/idle-capital` | Capital parado Curva C |
| `/kpi-summary` | KPIs consolidados |

#### /api/v1/operational/ (Gerência de Pista/Loja)

| Endpoint | Descrição |
|----------|-----------|
| `/cash-breaks` | Quebras de caixa por período |
| `/cash-breaks/by-operator` | Quebras por operador |
| `/tanks/{tanqueCodigo}` | Detalhe de tanque individual |
| `/tanks/rupture-risk` | Tanques em risco de ruptura |
| `/convenience/rupture` | Rupturas de conveniência |
| `/convenience/purchase-suggestions` | Sugestões de compra |
| `/summary` | Resumo operacional |

## Arquivos Criados

| Arquivo | Descrição |
|---------|-----------|
| `src/services/cash_cycle_service.py` | Ciclo de caixa e vácuo financeiro |
| `src/services/card_fee_impact_service.py` | Impacto taxas de cartão |
| `src/services/cash_break_service.py` | Quebra de caixa |
| `src/interfaces/http/routes/executive_cockpit.py` | Rotas executivas |
| `src/interfaces/http/routes/operational_cockpit.py` | Rotas operacionais |
| `tests/unit/test_cash_cycle.py` | Testes ciclo de caixa |
| `tests/unit/test_card_fee_impact.py` | Testes taxas cartão |
| `tests/unit/test_cash_break.py` | Testes quebra caixa |

## Arquivos Modificados

| Arquivo | Modificação |
|---------|-------------|
| `src/services/fuel_loss_service.py` | Adição de `dias_para_ruptura`, `venda_media_diaria`, `ruptura_iminente` |
| `src/services/convenience_analytics_service.py` | Filtros `dias_minimo` e `classificacao_abc_filter` |
| `src/interfaces/http/app.py` | Registro dos novos routers |

## Testes Unitários

33 testes passando:
- 10 testes de CashCycleService
- 10 testes de CardFeeImpactService
- 13 testes de CashBreakService

## Validação

```powershell
python -m pytest tests/unit/test_cash_cycle.py tests/unit/test_card_fee_impact.py tests/unit/test_cash_break.py -o addopts= --tb=short -v
```

## Parâmetros Configuráveis

| Parâmetro | Default | Descrição |
|-----------|---------|-----------|
| `taxa_antecipacao_mensal_pct` | 1.5% | Taxa mensal para simulação de antecipação |
| `fuel_payment_days` | 3 | Prazo padrão de pagamento de combustível |
| `tolerance_normal` | R$ 20 | Tolerância de quebra normal |
| `tolerance_warning` | R$ 100 | Tolerância de quebra warning |
| `IDLE_DAYS_WARNING` | 30 | Dias mínimos para estoque parado |

## Próximos Passos (Sprint 49)

- Dashboard visual de perdas volumétricas com gráficos
- Integração real-time de medição de tanques via telemetria WebPosto
- Alertas automatizados via webhook para quebras críticas
- Exportação de relatórios DRE em PDF/Excel
