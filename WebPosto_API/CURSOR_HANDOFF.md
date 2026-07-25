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

As Sprints 28–46 entregaram:

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
- conciliação de perdas volumétricas de combustíveis;
- Curva ABC, ruptura de estoque e capital parado de conveniência.

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

Sprint 47 — integração e automação operacional:

- integrar medição de tanque em tempo real do WebPosto;
- automatizar alertas de ruptura para produtos Curva A;
- implementar recomendações de compra por dias de cobertura;
- dashboard visual de perdas volumétricas.

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
