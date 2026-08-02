# Sprint 49 — Inteligência Proativa e Simulação Estratégica

## Objetivo

Implementar a camada de inteligência proativa que monitora exceções críticas automaticamente e fornecer ferramentas de simulação financeira para tomada de decisão da Diretoria. Além disso, garantir 100% de sanidade e execução da suíte de testes unitários.

## Entregas

### 1. Sanidade da Suíte de Testes (100% Active)

- Substituição de `pytest.skip` por **fixtures sintéticas** nos testes de `Decision Discovery`.
- Mocking dinâmico de `DecisionEvidenceService` para validar cenários de `explain` e `scope` sem dependência de snapshots locais.
- Total de **103 testes unitários** passando na suíte completa.

### 2. ProactiveAlertService — Motor de Exceções

- Monitoramento automático de 4 gatilhos críticos (Production Ready):
  - **Quebra de Caixa Crítica:** Alerta imediato para divergências > R$ 100,00.
  - **Desvio de Tanque:** Identificação de variações volumétricas não explicadas pela física térmica (ANP 20ºC).
  - **Ruptura Iminente Curva A:** Alerta para produtos de alta margem/giro com cobertura ≤ 2 dias.
  - **Estouro de Vácuo Financeiro:** Alerta quando o ciclo de caixa (Recebimento - Pagamento) ultrapassa 15 dias.
- Gerenciamento de estado de alertas (pendentes vs resolvidos).
- Endpoint: `GET /api/v1/executive/alerts/unresolved`.

### 3. FinancialSimulatorService — Simulador Estratégico

- Ferramenta para projeção de cenários estratégicos para a Diretoria:
  - **Input Mandatário:** Alteração de preço (R$/L ou por combustível), variação de volume (%) e taxa de antecipação (%).
  - **Output Mandatário:** Impacto projetado em EBITDA mensal, Margem Líquida Pós-Cartões e Necessidade de Capital de Giro / Vácuo de Caixa (R$).
- Permite avaliar elasticidade de preço vs volume com precisão decimal.
- Endpoint: `POST /api/v1/executive/simulate-margin-impact`.

## Arquivos Criados

| Arquivo | Descrição |
|---------|-----------|
| `src/services/proactive_alert_service.py` | Motor de alertas de exceção |
| `src/services/financial_simulator_service.py` | Simulador estratégico de margem |
| `tests/unit/test_proactive_alerts.py` | Testes do motor de alertas |
| `tests/unit/test_financial_simulator.py` | Testes do simulador |

## Arquivos Modificados

| Arquivo | Modificação |
|---------|-------------|
| `src/interfaces/http/routes/executive_cockpit.py` | Novos endpoints de alertas e simulação |
| `tests/unit/test_discovery_explain_endpoint.py` | Ativação dos testes via fixtures sintéticas |
| `tests/unit/test_discovery_scope.py` | Ativação dos testes via fixtures sintéticas |

## Testes Unitários

**103 testes passando** (Sprint 47 + 48 + 49 + Legado Corrigido):
- 8 testes de ProactiveAlertService
- 4 testes de FinancialSimulatorService
- 9 testes de Discovery (re-ativados)
- Demais testes financeiros e operacionais (zero failures, zero skips)

## Próximos Passos (Sprint 50)

- Dashboard visual de perdas volumétricas com gráficos Highcharts/Recharts.
- Integração de webhooks para disparo de alertas críticos em tempo real (Slack/WhatsApp).
- Refatoração de `ProactiveAlertService` para persistência em banco de dados (SQLModel).
- Consolidação do "Cockpit do Presidente" com visão multi-unidade em tempo real.
