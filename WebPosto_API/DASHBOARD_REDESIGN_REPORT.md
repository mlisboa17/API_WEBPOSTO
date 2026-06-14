# IA-2 — Dashboard Redesign Report (UX-02)

## Filosofia

**Antes:** usuário escolhe módulo.  
**Depois:** usuário recebe prioridades.

## Nova estrutura (5 blocos)

| # | Bloco | Componente | Decisão suportada |
|---|-------|------------|-------------------|
| 1 | Resumo da Rede | 6 executive cards | Saúde consolidada da rede |
| 2 | Alert Center | Lista priorizada (até 8) | O que exige ação imediata |
| 3 | Opportunity Center | Tabela (até 8) | Onde investir esforço comercial |
| 4 | Execução | 5 KPIs de ações | Progresso operacional |
| 5 | Branch Intelligence | 5 rankings | Qual filial merece foco |

## Navegação

- Sidebar: 6 áreas (UX-01) — **sem dezenas de botões**.
- Home: um scroll vertical denso, grids responsivos.
- Clique em alerta/oportunidade → deep link para view de origem (motor oculto na home).

## Arquivos

- `frontend/pages/executiveWorkspace.js` — render
- `frontend/services/workspaceEngine.js` — agregação
- `frontend/config/navigation.js` — Resumo → `executiveWorkspace`

## Parecer IA-2

Redesign aprovado: máximo 5 blocos principais, zero botões de motor na home.
