# Continuidade do WebPosto no Cursor

## Abra esta pasta

`C:\Users\mlisb\OneDrive\ProjetosAntigravy\LOGOS SPACE\Api_WebPosto\WebPosto_API`

Não abra apenas `executive-web`: o backend FastAPI, o frontend executivo e os testes
fazem parte do mesmo produto.

## Leia primeiro

1. `CURSOR_HANDOFF.md`
2. `docs/business/ROADMAP_WEBPOSTO_CODEX.md`
3. `docs/business/PROACTIVE_EXECUTIVE_INTELLIGENCE.md`
4. `docs/business/SPRINT_42_EXECUTIVE_EXPERIENCE.md`
5. `AGENTS.md`, se estiver disponível na raiz/contexto do workspace.

## Estado atual

As Sprints 28–50 entregaram o ecossistema completo de inteligência para o Grupo Lisboa. **O BACKEND ESTÁ CONCLUÍDO E PRONTO PARA PRODUÇÃO.**

- rotinas diária e semanal configuráveis;
- execução diária padrão às 06:00 sobre o dia anterior;
- auditoria periódica com PDF, conciliação, revisão, dossiê e integridade;
- backup e restauração dos dossiês;
- radar executivo proativo;
- notificações, valor comprovado, EVS e confiabilidade por agente;
- agentes Financeiro, Operacional, Comercial, Governança e Presidência;
- Dashboard Presidência 2.0 em quatro blocos;
- telemetria anônima de adoção executiva;
- validação de integridade de paginação;
- tratativa de despesas pendentes (PENDENTE_CLASSIFICACAO);
- síntese executiva < 1s com cache;
- rateio de custos compartilhados (%, faturamento ou fixo);
- enums ProductType C/P/U e ExpenseClassification;
- conciliação de perdas volumétricas de combustíveis com correção térmica;
- Curva ABC, ruptura de estoque e capital parado de conveniência;
- engine de mapeamento de despesas (De-Para WebPosto → DRE);
- recomendações de compra baseadas em Curva ABC e dias de cobertura;
- ciclo de caixa e vácuo financeiro (necessidade de capital de giro);
- impacto de taxas de cartão na margem líquida;
- quebra de caixa com régua de tolerância (Normal/Warning/Crítico);
- motor de alertas proativos de exceção (Quebras, Desvios, Vácuo, Ruptura Curva A);
- simulador estratégico de impacto em EBITDA e Capital de Giro;
- persistência de alertas (PostgreSQL), webhooks e dashboard bundle;
- namespaces separados /executive/ e /operational/ (Cockpits).

## Arquivos centrais

Backend:

- `src/services/departmental_automation_service.py`
- `src/services/proactive_executive_radar_service.py`
- `src/services/proactive_agent_orchestrator_service.py`
- `src/services/proactive_notification_service.py`
- `src/services/proactive_value_service.py`
- `src/services/executive_adoption_service.py`
- `src/interfaces/http/routes/departmental_governance.py`
- `src/interfaces/http/routes/periodic_audits.py`

Frontend executivo:

- `executive-web/src/components/executive/presidency-dashboard-v2.tsx`
- `executive-web/src/app/page.tsx`
- `executive-web/src/app/api/executive-intelligence/route.ts`
- `executive-web/src/app/api/executive-adoption/route.ts`

## Regras que não podem ser quebradas

- Não produzir insight sem fonte homologada, evidência, linhagem e confiança.
- Não transformar ausência de dados em zero.
- Não elevar confiança automaticamente.
- Não executar recomendações sem decisão humana.
- Manter valor estimado separado de valor validado.
- Somente resultado validado alimenta EVS, confiabilidade e aprendizado.
- Não misturar empresas ou departamentos.
- Não versionar `.env`, credenciais, logs, `tmp/` ou snapshots sensíveis.

## Próxima sprint sugerida

Sprint 57 — Visualização Avançada e Integrações:

- gráficos interativos Recharts para Perdas Volumétricas e Evolução de Margens;
- integração de webhooks para alertas críticos em tempo real (Slack/WhatsApp);
- telemetria de tanque com leitura automática de nível e temperatura;
- exportação de relatórios completos em Excel (.xlsx) com formatação;
- comparativo histórico mês-a-mês para métricas executivas;
- drill-down interativo nas tabelas de relatórios.

## Sprint 44 & 45 entregues

**Sprint 44 — Sessão Executiva 30s:**
- validação de integridade de paginação com alertas;
- tratativa de despesas pendentes sem quebrar pipeline DRE;
- centro de custo PENDENTE_CLASSIFICACAO com alerta visual;
- síntese executiva consolidada com cache < 1s;
- endpoints `/api/v1/executive-synthesis/*`.

**Sprint 45 — Sanidade Financeira:**
- enum ExpenseClassification configurável;
- CostAllocationService com rateio dinâmico;
- ProductType C/P/U com fallback seguro;
- migração FastAPI `on_event` → `lifespan`;
- 15 testes unitários passando.

Detalhes: `docs/business/SPRINT_44_45_EXECUTIVE_VALIDATION.md`.

## Sprint 56 entregue — CENTRAL DE RELATÓRIOS EXECUTIVOS

**Sprint 56 — Central de Relatórios (`/executive/reports`):**

- **Página Central** (`/executive/reports`): cards de acesso rápido para Pista, Caixa e DRE; botões de exportação Markdown/PDF; KPIs consolidados.
- **Relatório de Pista & Volumetria** (`/executive/reports/fuel`):
  - cards de volume total, faturamento, ticket médio e filiais ativas;
  - tabela de volume por produto (Gasolina, Etanol, Diesel, GNV) com participação percentual;
  - ranking de filiais por litros vendidos;
  - tabela de margem por litro (R$/L) por filial.
- **Auditoria de Caixa & Anomalias** (`/executive/reports/cash-audit`):
  - cards de valor apurado, apresentado, divergente e pendente;
  - reconciliação por natureza de pagamento (dinheiro, cheque, PIX, cartão);
  - rombo detalhado por operador e turno;
  - matriz de anomalias com filiais acima da média de despesas.
- **DRE & Despesas Classificadas** (`/executive/reports/expenses`):
  - cards de total, pessoal, operacional e pendentes de classificação;
  - indicador de impacto do custo de pessoal sobre receita bruta;
  - tabela de despesas por categoria (Pessoal vs Operacional);
  - tabela DRE por filial e lista de despesas auto-classificadas.
- **Exportação**: download Markdown gerado pelo backend (`/api/v1/executive/consolidated-report/markdown`) e impressão/PDF via browser.
- **Backend**: endpoint assíncrono `/api/v1/executive/consolidated-report` consome dados reais da integração WebPosto; suporte a Markdown já integrado.
- **Navegação**: item "Central de Relatórios" adicionado à Sidebar no grupo Analytics.
- **Tipagem**: modelos TypeScript `ExecutiveReport`, `FuelProduct`, `Block1Combustiveis`, etc., em `executive-web/src/types/api.ts`.

## Sprint 55 entregue — RELATÓRIO EXECUTIVO CONSOLIDADO COM DADOS REAIS

**Sprint 55 — Integração WebPosto e Geração do Relatório Executivo:**

- `ExecutiveConsolidatedReportService` migrado para chamadas assíncronas;
- consumo das rotas `/INTEGRACAO/ABASTECIMENTO`, `/INTEGRACAO/PRODUTO`, `/INTEGRACAO/VENDA_ITEM`, `/INTEGRACAO/VENDA_FORMA_PAGAMENTO` e `/INTEGRACAO/CAIXA`;
- Blocos 1 (Combustíveis) e 3 (Margens R$/L) preenchidos com volume e faturamento reais por produto/filial;
- Bloco 4 (Conveniência) com vendas de todas as filiais ativas;
- detalhamento do rombo de caixa por operador, turno e meio de pagamento;
- auto-classificação de despesas pendentes por regras de palavras-chave;
- geração de relatório Markdown e JSON em `reports/executive_report_sprint55_YYYY-MM-DD.*`;
- testes unitários async atualizados e aprovados.

## Sprint 54 entregue — FINALIZAÇÃO DO FRONTEND EXECUTIVO

**Sprint 54 — Dashboards Especializados e Simulador:**
- **Vendas & Elasticidade** (`/dashboard/sales-analytics`):
  - Heatmap de Galonagem 7x24 (Dias x Horas) com tooltip detalhado;
  - Scatter Plot de Elasticidade: Preço x Volume x Margem Bruta;
  - Tabela de Cesta de Afinidade com Margem Total, Lift, Frequência e Ticket Médio;
  - Badge da Taxa de Conversão Pista -> Loja.
- **Eficiência Logística** (`/dashboard/logistics`):
  - Bar/Line Chart comparativo de Frete Médio e Markup por Distribuidora;
  - Card de Custo de Oportunidade (CIF > FOB histórico);
  - Tabela detalhada com Delta FOB x CIF e status de eficiência.
- **Tesouraria & Cash Pooling** (`/dashboard/treasury`):
  - Stacked Bar Chart de Saldo vs CP 48h por unidade;
  - Widget de Sugestão de Sweep intragrupo com justificativa e valor;
  - Badge de Aging de Disponibilidade de Caixa em dias;
  - Tabela de liquidez por unidade com status SUPERÁVIT/DEFICIT.
- **Simulador de Margem** (`/executive/simulator`):
  - Sliders interativos para Preço, Volume e Taxa de Antecipação;
  - Projeção em tempo real de EBITDA, Capital de Giro e Margem Líquida pós-cartões;
  - Skeleton de loading durante cálculo e design refinado no padrão LOGOS.
- **Navegação**: Sidebar reorganizada em grupos (Visão Estratégica, Analytics, Operações) com destaque visual para rota ativa.
- **Padrão Visual**: Dark Mode coeso, cards com `bg-slate-900/40`, bordas `white/5`, tooltips customizados e tipagem TypeScript estrita em todos os módulos.

## Sprint 53 entregue — UNIFICAÇÃO VISUAL E MIGRAÇÃO FINANCEIRA

**Sprint 53 — Unificação e Consolidação:**
- **Padronização Visual**: Componentes UI (`Table`, `Skeleton`) baseados no design de `localhost:3000` (Next.js 15+ / Tailwind v4);
- **Migração Financeira**: Substituição completa do `financeCenter.js` legado pela nova página `/executive/financial-center`;
- **Abas de Centro Financeiro**: Performance (DRE), Aging (Contas a Pagar/Receber) e Conciliação;
- **Painel DRE Real**: Integração do Cockpit 30s com o serviço de DRE Departamental real do backend;
- **Fila de Conciliação**: Interface modal para classificação de despesas pendentes (`ReviewableFacts`) diretamente pelo cockpit;
- **Tipagem Avançada**: Novas interfaces TypeScript para DRE, Fatos Conciliáveis e Aging Financeiro;
- **Resiliência de UI**: Implementação de Skeletons e tratamento de estados nulos/vazios com `formatBRL`.

## Sprint 52 entregue — INTELIGÊNCIA DE VENDAS E TESOURARIA

**Sprint 52 — Inteligência e Eficiência:**
- SalesAnalyticsService: Heatmap de galonagem, elasticidade preço x volume, cestas de afinidade e taxa de conversão pista->loja;
- LogisticsFreightService: Análise CIF vs FOB, custo de frete efetivo e custo de oportunidade logística;
- TreasuryConsolidationService: Consolidação de saldos da holding, aging de disponibilidade de caixa e sugestões de sweep intragrupo;
- Endpoints executivos em `/api/v1/executive/sales/*`, `/executive/logistics/*` e `/executive/treasury/*`;
- Payloads otimizados para gráficos Heatmap, Scatter e Stacked Bar;
- 6 testes unitários garantindo os cálculos matemáticos e lógicas de cross-selling.

## Sprint 51 entregue — COCKPIT DO PRESIDENTE (FRONTEND)

**Sprint 51 — Frontend Executivo:**
- Dashboard Principal `/dashboard/executive`: Visão Cockpit 30s consolidada;
- Gestão de Alertas `/executive/alerts`: Interface para auditoria e resolução de exceções;
- Simulador Financeiro `/executive/simulator`: Projeção interativa de EBITDA e Vácuo de Caixa;
- Monitoramento de Tanques `/operational/tanks`: Gráficos de variação térmica vs desvios reais;
- Tipagem rígida TypeScript espelhando DTOs do FastAPI;
- Layout moderno em Dark Mode com navegação enxuta e responsiva.

Detalhes: `executive-web/README_FRONTEND.md`.

## Sprint 50 entregue — INTEGRAÇÃO E PERSISTÊNCIA

**Sprint 50 — Persistência, Notificações e Bundle:**
- Persistência de alertas proativos em banco de dados (`ExecutiveAlertModel`);
- Idempotência garantida para evitar alertas duplicados;
- NotificationDispatcherService: despache de alertas CRÍTICOS via Webhook;
- Dashboard Bundle: endpoint unificado `GET /bundle` com resposta < 1s;
- 108 testes unitários passando (Sprint 47-50 + regressões).

Detalhes: `docs/business/SPRINT_50_PERSISTENCE_NOTIFICATIONS.md`.

## Sprint 49 entregue — BACKEND FINALIZADO

**Sprint 49 — Inteligência Proativa e Simulação Estratégica:**
- 100% de sanidade nos testes de Discovery (fixtures sintéticas mockadas);
- ProactiveAlertService: monitoramento de Quebras, Desvios, Vácuo e Ruptura Curva A;
- FinancialSimulatorService: projeção de EBITDA, Margem Líquida e Capital de Giro;
- Endpoints executivos de alertas e simulação em `/api/v1/executive/`;
- 103 testes unitários passando (zero skips, zero failures).

Detalhes: `docs/business/SPRINT_49_PROACTIVE_INTELLIGENCE.md`.

## Sprint 48 entregue

**Sprint 48 — Ciclo de Caixa, Taxas de Cartão e Visão Operacional:**
- CashCycleService: vácuo financeiro e necessidade de capital de giro;
- CardFeeImpactService: margem líquida pós-taxas de cartão;
- CashBreakService: quebra de caixa com régua de tolerância;
- FuelLossService: dias_para_ruptura e ruptura_iminente;
- ConvenienceAnalyticsService: filtro dias_minimo e classificacao_abc;
- Namespaces `/api/v1/executive/` e `/api/v1/operational/`;
- 33 testes unitários passando.

Detalhes: `docs/business/SPRINT_48_FINANCIAL_ADVANCED.md`.

## Sprint 47 entregue

**Sprint 47 — Motor de Mapeamento de Despesas e Automação:**
- Correção térmica no FuelLossService (coef. por combustível, ANP 20ºC);
- Classificações: PERDA_TERMICA, DESVIO_SUSPEITO, VAZAMENTO;
- ExpenseCategorizationService: engine de De-Para com regras configuráveis;
- MatchConfidence: EXACT, PATTERN, FUZZY, MANUAL;
- PurchaseRecommendationService: sugestão de compras por ABC/cobertura;
- Endpoints `/api/v1/financial/expense-mappings/*`;
- Tech Debt: cliente_dto.py migrado para Pydantic V2;
- 36 testes unitários passando.

Detalhes: `docs/business/SPRINT_47_EXPENSE_MAPPING.md`.

## Sprint 46 entregue

**Sprint 46 — Operacional Avançado:**
- FuelLossService: conciliação volumétrica com tolerância configurável;
- Classificação: NORMAL, ATENCAO, CRITICO, SOBRA_SUSPEITA;
- ConvenienceAnalyticsService: Curva ABC, ruptura, capital parado;
- Endpoints `/api/v1/operational/*`;
- 19 testes unitários passando.

Detalhes: `docs/business/SPRINT_46_OPERATIONAL_ADVANCED.md`.

## Sprint 43 entregue

- teste de 30 segundos documentado (`docs/validation/PRESIDENT_30_SECOND_TEST.md`);
- métricas de adoção com meta ≤ 30s e revisão dos 4 blocos;
- relatório mensual BVG em `GET /monthly-business-value-report`;
- homologação de webhook sem dados de negócio;
- smoke `scripts/sprint43_executive_validation.py`.

Detalhes: `docs/business/SPRINT_43_EXECUTIVE_VALIDATION.md`.

## Comandos de validação

Backend:

```powershell
python -m pytest tests/unit -o addopts= --tb=short -q
```

Frontend:

```powershell
cd executive-web
npm run lint
npm run build
```

## Configuração operacional

Consulte `.env.example`. Em produção:

- `DEPARTMENTAL_SCHEDULER_ENABLED=true`
- `DEPARTMENTAL_SCHEDULER_POLL_SECONDS=60`
- `EXECUTIVE_NOTIFICATION_WEBHOOK_URL=<canal HTTPS homologado>`

O webhook é opcional em desenvolvimento. Nunca registre tokens ou conteúdo executivo
na telemetria de adoção.
