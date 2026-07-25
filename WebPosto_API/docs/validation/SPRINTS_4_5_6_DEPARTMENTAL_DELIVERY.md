# Sprints 4, 5 e 6 — entrega departamental

Data: 2026-07-24

## Entregue

- histórico diário e comparação com período anterior de mesma duração;
- ausência de dia explícita, sem preenchimento por zero;
- cockpit da Presidência com três departamentos independentes;
- painéis Financeiro, Comercial e Operacional sobre a mesma DRE;
- filtros de empresa e período, evidência e linhas exportáveis com escopo;
- tela em `/app/departmental`;
- APIs:
  - `/api/v1/departmental-kpis/trends`;
  - `/api/v1/departmental-kpis/presidency-cockpit`;
  - `/api/v1/departmental-kpis/director-panels`.

## Estado real em 24/07/2026

Há materialização real somente para 23/07/2026. O cockpit publica receita, CMV e
margem bruta desse dia. Tendência e variação continuam nulas até existir o período
anterior completo.

Despesas permanecem sem cobertura departamental completa. Por isso, resultado
operacional, lucro e rentabilidade não são publicados.

Metas, oportunidades financeiras, perdas, rupturas, LMC e produtividade não foram
simulados. Seus espaços permanecem bloqueados ou marcados como indisponíveis até
haver fonte e regra aprovadas.

## Validação

- períodos incompletos não geram variação;
- Presidência e Diretoria consomem o mesmo serviço de DRE;
- nenhuma linha exportável perde empresa ou departamento;
- revisão de profissional financeiro continua obrigatória.
