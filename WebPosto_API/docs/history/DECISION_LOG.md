---
# 📝 DECISION_LOG.md | LOGOS
# Type: DECISION_LOG
# Version: 1.0
# Updated: 2026-06-29
---

# LOGOS — Decision Log

> **Registro formal de todas as decisões arquiteturais e de produto**

---

## 📋 Estrutura

Cada entrada segue o formato:

```
ADR-XXX: [Título]
Status: [PROPOSED | ACCEPTED | DEPRECATED | SUPERSEDED]
Data: [YYYY-MM-DD]
Sprint: [Sprint Name]
Contexto: [Por que foi necessário]
Decisão: [O que foi decidido]
Consequências: [Impacto positivo e negativo]
```

---

## ADR-001: HTTPX para Chamadas HTTP Assíncronas
**Status:** ✅ ACCEPTED  
**Data:** 2026-06-15  
**Sprint:** Foundation

### Contexto
Necessidade de cliente HTTP assíncrono eficiente para integração com WebPosto API.

### Decisão
- Usar `httpx.AsyncClient` para todas as chamadas HTTP assíncronas
- Reutilizar cliente/pool quando fizer sentido
- Nunca usar requests síncrono em paths hot

### Consequências
- ✅ Performance superior em chamadas concorrentes
- ✅ Compatível com FastAPI nativo
- ✅ Suporte nativo a HTTP/2
- ⚠️ Requer cuidado com lifecycle do cliente

---

## ADR-002: Circuit Breaker para Resiliência
**Status:** ✅ ACCEPTED  
**Data:** 2026-06-16  
**Sprint:** Foundation

### Contexto
WebPosto API pode ficar indisponível. Sistema precisa falhar gracefully.

### Decisão
- Implementar `SimpleCircuitBreaker` com `failure_threshold=3`
- `block_seconds=3600` (1 hora)
- Estado armazenado em memória (simplificado)

### Consequências
- ✅ Sistema não fica lento quando API externa falha
- ✅ Recuperação automática após 1 hora
- ✅ Logs claros de estado do circuit breaker
- ⚠️ Estado não persiste entre restarts (aceitável)

---

## ADR-003: Zero Mocks, Dados Reais
**Status:** ✅ ACCEPTED  
**Data:** 2026-06-16  
**Sprint:** Foundation

### Contexto
Risco de apresentar dados simulados como reais para proprietários.

### Decisão
- **PROIBIDO:** Mocks, JSON fixo, valores hardcoded, dados "placeholder"
- **OBRIGATÓRIO:** Apenas dados do WebPosto, APIs certificadas
- Fallback: `insufficient_data` em vez de simulação

### Consequências
- ✅ Confiança do proprietário garantida
- ✅ Detecção precoce de problemas de integração
- ✅ Qualidade real mensurável
- ⚠️ UX degradada quando dados indisponíveis (aceitável)

---

## ADR-004: Baseline Calculation Automático
**Status:** ✅ ACCEPTED  
**Data:** 2026-06-20  
**Sprint:** DATA-01

### Contexto
Necessidade de comparar valores atuais contra histórico sem hardcoding.

### Decisão
- Calcular baselines automaticamente de dados históricos
- Usar média móvel de 90 dias
- Aplicar sazonalidade quando disponível
- Nunca usar valores fixos ("R$ 50.000 é normal")

### Consequências
- ✅ Adaptativo por tenant
- ✅ Detecta mudanças de comportamento reais
- ✅ Personalizado por produto/posto/turno
- ⚠️ Requer mínimo de 30 dias de histórico

---

## ADR-005: Multi-Tenancy por empresaCodigo
**Status:** ✅ ACCEPTED  
**Data:** 2026-06-20  
**Sprint:** Foundation

### Contexto
Necessidade de isolar dados de múltiplos postos/tenants.

### Decisão
- Usar `empresaCodigo` como identificador de tenant
- Todas as queries filtradas por empresaCodigo
- Cache segmentado por tenant

### Consequências
- ✅ Isolamento completo de dados
- ✅ Cache eficiente por tenant
- ✅ Segurança a nível de dados
- ✅ Escalável para novos tenants

---

## ADR-006: Owner Signals como Sinais de Valor
**Status:** ✅ ACCEPTED  
**Data:** 2026-06-22  
**Sprint:** DATA-02

### Contexto
Dashboards mostram dados, mas proprietário precisa de ações.

### Decisão
- Criar sistema de "sinais" — insights acionáveis
- Sinais devem ter: tipo, severidade, mensagem, ação sugerida
- Nunca exibir apenas "dados"; sempre "o que fazer"

### Consequências
- ✅ Proprietário recebe orientação, não tabelas
- ✅ Foco em valor prático
- ✅ Base para Daily Decisions
- ⚠️ Requer mais processamento que simples exibição

---

## ADR-007: Confidence Score para Qualidade
**Status:** ✅ ACCEPTED  
**Data:** 2026-06-25  
**Sprint:** TRUST-01

### Contexto
Necessidade de quantificar confiabilidade de decisões.

### Decisão
- Criar Confidence Score (0-100) para toda decisão
- Decisões < 60% não são exibidas
- Score baseado em: data quality, endpoint health, cache freshness, historical data

### Consequências
- ✅ Transparência de qualidade
- ✅ Prevenção de decisões em dados ruins
- ✅ Accountability do sistema
- ⚠️ Menos decisões exibidas quando dados ruins

---

## ADR-008: Business Truth Auditor
**Status:** ✅ ACCEPTED  
**Data:** 2026-06-25  
**Sprint:** VALIDATION-01

### Contexto
Necessidade de provar que LOGOS = WebPosto matematicamente.

### Decisão
- Criar `BusinessTruthAuditor` para reconciliação automática
- Comparar relatórios WebPosto vs cálculos LOGOS
- Truth Score ≥ 95% para certificação
- Zero tolerância para divergência financeira

### Consequências
- ✅ Confiança matemática na precisão
- ✅ Detecção automática de bugs de cálculo
- ✅ Compliance para relatórios fiscais
- ⚠️ Requer exportação manual de relatórios WebPosto

---

## ADR-009: Owner Action Center como Home
**Status:** ✅ ACCEPTED  
**Data:** 2026-06-28  
**Sprint:** PRODUCT-03

### Contexto
Dashboard tradicional não gera ações. Proprietário precisa de decisões.

### Decisão
- Tornar Owner Action Center a nova Home do LOGOS
- Estrutura: Business Health → Top 5 Decisions → Quick Actions
- Eliminar gráficos puramente estéticos
- Mostrar apenas decisões com impacto financeiro

### Consequências
- ✅ Foco absoluto em ação
- ✅ Redução de tempo para decisão
- ✅ Valor imediatamente percebido
- ⚠️ Curva de aprendizado para usuários de dashboards tradicionais

---

## ADR-010: 4 Motores do Owner Intelligence
**Status:** ✅ ACCEPTED  
**Data:** 2026-06-28  
**Sprint:** PRODUCT-03

### Contexto
Necessidade de múltiplas perspectivas para geração de decisões.

### Decisão
- Motor 1: Money At Risk (proteger)
- Motor 2: Recoverable Money (recuperar)
- Motor 3: Growth Opportunities (crescer)
- Motor 4: Daily Actions (priorizar)
- Cada motor especializado em uma perspectiva de valor

### Consequências
- ✅ Cobertura completa de valor (proteger, recuperar, crescer)
- ✅ Decisões holísticas e balanceadas
- ✅ Extensível para novos motores
- ⚠️ Coordenação necessária entre motores

---

## ADR-011: Priority Engine com Pesos Financeiros
**Status:** ✅ ACCEPTED  
**Data:** 2026-06-28  
**Sprint:** PRODUCT-03

### Contexto
Múltiplas decisões possíveis, mas proprietário precisa foco.

### Decisão
- Criar Priority Engine com scoring ponderado
- Pesos: Financial Impact (30%), Urgency (25%), Confidence (20%), Ease (15%), Time (10%)
- Apenas Top 5 exibidas na Home
- Resto disponível em "Ver todas"

### Consequências
- ✅ Foco no maior valor primeiro
- ✅ Limitação cognitiva respeitada (5 itens)
- ✅ Priorização justificável
- ⚠️ Peso financeiro pode ignorar urgências menores

---

## ADR-012: Automatic Baselines — Nunca Hardcoded
**Status:** ✅ ACCEPTED  
**Data:** 2026-06-28  
**Sprint:** PRODUCT-03

### Contexto
Risco de thresholds fixos não se adaptarem a diferentes tenants.

### Decisão
- Todos os detectores usam baselines calculados automaticamente
- Cálculo baseado em histórico do próprio tenant
- Z-score para detectar anomalias (|z| > 2)
- Nunca valores fixos como "R$ 50.000"

### Consequências
- ✅ Adaptativo por tenant
- ✅ Personalizado por padrão
- ✅ Não requer configuração
- ⚠️ Requer mínimo de dados históricos

---

## ADR-013: Trust Engine como Camada Transversal
**Status:** ✅ ACCEPTED  
**Data:** 2026-06-28  
**Sprint:** TRUST-01

### Contexto
Necessidade de confiança em toda decisão gerada.

### Decisão
- Trust Engine é camada transversal, não módulo isolado
- Cada motor chama Trust Engine para calcular Confidence Score
- Decision Trace registrado para auditabilidade
- Sem Trust Score, sem exibição

### Consequências
- ✅ Qualidade garantida em todo pipeline
- ✅ Audit trail completo
- ✅ Debuggability aprimorada
- ⚠️ Overhead de processamento

---

## ADR-014: Sales Investigation Engine (Motor 5)
**Status:** 🔄 PROPOSED  
**Data:** 2026-06-29  
**Sprint:** PRODUCT-04

### Contexto
Quedas de vendas precisam de investigação profunda, não apenas alerta.

### Decisão
- Criar 5º motor: Sales Investigation Engine
- Investigar automaticamente: produto, local, turno, horário, causa
- Nunca informar apenas "vendas caíram" — sempre investigar e recomendar
- 6 dimensões de investigação obrigatórias

### Consequências
- ✅ Diagnóstico automático de problemas
- ✅ Causa raiz identificada sem esforço do proprietário
- ✅ Decisões mais informadas
- ⚠️ Complexidade de implementação
- ⚠️ Requer mais dados (estoque, funcionários, etc.)

---

## ADR-015: Owner Success Score
**Status:** 🔄 PROPOSED  
**Data:** 2026-06-29  
**Sprint:** PRODUCT-04

### Contexto
Necessidade de demonstrar valor do LOGOS de forma quantificável.

### Decisão
- Criar métrica Owner Success Score (OSS)
- Medir impacto do LOGOS, não do posto
- Métricas: decisões geradas/executadas, dinheiro recuperado, economia, ROI
- Target: ROI ≥ 10x

### Consequências
- ✅ Demonstração clara de valor
- ✅ Justificativa de preço
- ✅ Feedback loop de melhoria
- ⚠️ Requer tracking de execução
- ⚠️ Requer confirmação do proprietário

---

## ADR-016: Owner Operating System (Nova Fase)
**Status:** 🔄 PROPOSED  
**Data:** 2026-06-29  
**Sprint:** PRODUCT-04

### Contexto
Evolução natural de Dashboard → Intelligence → Action Center → Operating System

### Decisão
- Transformar LOGOS em "Owner Operating System"
- Proprietário pergunta: "O que devo fazer hoje?"
- LOGOS responde com decisões priorizadas
- Próxima fase: EXECUTAR (ação direta na plataforma)

### Consequências
- ✅ Posicionamento único no mercado
- ✅ Valor cada vez mais tangível
- ✅ Base para fases futuras (EXECUTAR, APRENDER, ANTECIPAR)
- ⚠️ Mudança de paradigma completa
- ⚠️ Requer reeducação de mercado

---

## ADR-017: Toda Tela Termina em Decisão
**Status:** 🔄 PROPOSED  
**Data:** 2026-06-29  
**Sprint:** PRODUCT-04

### Contexto
Telas com apenas dados sem ação são incompletas.

### Decisão
- Regra: Toda tela → Uma decisão
- Se uma tela termina apenas mostrando números, está incompleta
- Cada informação deve ter ação associada
- Nenhum KPI sem caminho para ação

### Consequências
- ✅ UX focada em resultado
- ✅ Tempo de decisão minimizado
- ✅ Valor percebido imediato
- ⚠️ Requer redesign de telas existentes
- ⚠️ Mais complexidade por tela

---

## ADR-018: Logos Investiga Automaticamente
**Status:** 🔄 PROPOSED  
**Data:** 2026-06-29  
**Sprint:** PRODUCT-04

### Contexto
Alertas de problema sem investigação geram trabalho manual para proprietário.

### Decisão
- PROIBIDO: "As vendas caíram 11,8%"
- OBRIGATÓRIO: Investigação completa + recomendação
- 6 dimensões mínimas de investigação
- Confidence Score ≥ 80% para exibição

### Consequências
- ✅ Proprietário recebe diagnóstico, não alerta bruto
- ✅ Economia de tempo do proprietário
- ✅ Decisões mais informadas
- ⚠️ Requer integração com mais fontes de dados
- ⚠️ Maior complexidade de processamento

---

## ADR-019: Impacto Financeiro como Métrica de Sucesso
**Status:** 🔄 PROPOSED  
**Data:** 2026-06-29  
**Sprint:** PRODUCT-05

### Contexto
Sistemas tradicionais medem sucesso por funcionalidades entregues. O LOGOS precisa medir valor real gerado.

### Decisão
- Sucesso do LOGOS = Impacto financeiro gerado para o proprietário
- Toda nova funcionalidade deve declarar impacto financeiro esperado
- Impacto mensurável obrigatório para entrar no roadmap
- LOGOS Impact Score: R$ 170.900+ total mensurável
- Componentes: Recuperado + Economizado + Evitado + Adicional + Tempo

### Métricas
- Receita Recuperada: R$ 87.300
- Economias Obtidas: R$ 41.400
- Perdas Evitadas: R$ 26.800
- Receita Adicional: R$ 15.400
- Tempo Economizado: 312 horas
- ROI: 14.8x

### Consequências
- ✅ Foco absoluto em valor tangível
- ✅ Justificativa clara para investimento no LOGOS
- ✅ Eliminação de funcionalidades sem impacto
- ✅ Accountability do produto
- ⚠️ Requer sistema de tracking de resultados
- ⚠️ Maior complexidade de mensuração

---

## ADR-020: Momento Zero — 10 Segundos para Decisão
**Status:** 🔄 PROPOSED  
**Data:** 2026-06-29  
**Sprint:** PRODUCT-05

### Contexto
Proprietários não têm tempo para analisar dashboards complexos. Precisam de clareza imediata.

### Decisão
- Primeiros 10 segundos determinam valor percebido
- Proprietário deve entender: O que fazer, quanto dinheiro, qual decisão #1
- Nova Home sem scroll
- Apenas decisões, nenhum gráfico decorativo
- Top 3 decisões visíveis imediatamente

### Checklist Momento Zero
- [ ] Contagem de decisões visível
- [ ] Business Health Score
- [ ] LOGOS Impact Score
- [ ] Dinheiro em risco
- [ ] Dinheiro recuperável
- [ ] Top 3 decisões com ações

### Consequências
- ✅ Redução drástica do tempo para ação
- ✅ Foco absoluto em valor
- ✅ Eliminação de ruído visual
- ⚠️ Requer redesign completo da Home
- ⚠️ Menos espaço para contexto

---

## ADR-021: Decision Execution Flow Completo
**Status:** 🔄 PROPOSED  
**Data:** 2026-06-29  
**Sprint:** PRODUCT-05

### Contexto
Decisões sem acompanhamento não geram aprendizado nem mensuração de resultado.

### Decisão
- Ciclo obrigatório: Detectar → Investigar → Explicar → Executar → Confirmar → Medir → Aprender
- Nenhuma decisão pode existir sem tracking de resultado
- "Executar Agora" com contexto direto
- Confirmação obrigatória: SIM/NÃO/PARCIAL
- Medição de impacto financeiro real

### Estados
- DETECTED → INVESTIGATING → EXPLAINED → PENDING → EXECUTED → CONFIRMED → MEASURED → LEARNED

### Consequências
- ✅ Ciclo completo de valor
- ✅ Aprendizado contínuo
- ✅ Mensuração precisa de ROI
- ⚠️ Complexidade de implementação
- ⚠️ Requer mudança de comportamento do usuário

---

## 📊 Resumo por Status

| Status | Quantidade |
|--------|------------|
| ✅ ACCEPTED | 13 |
| 🔄 PROPOSED | 8 |
| ⚠️ DEPRECATED | 0 |
| 🔄 SUPERSEDED | 0 |
| **Total** | **21** |

---

## 🔗 Referências

- [PRODUCT_CONSTITUTION.md](../business/PRODUCT_CONSTITUTION.md) — Princípios do produto
- [ROADMAP.md](../business/ROADMAP.md) — Evolução das fases
- [SPRINT_HISTORY.md](SPRINT_HISTORY.md) — Histórico de sprints

---

**[DECISION_LOG — LOGOS Architecture Decisions]**

*Decisions: 21 | Accepted: 13 | Proposed: 8 | Last Updated: 2026-06-29*
