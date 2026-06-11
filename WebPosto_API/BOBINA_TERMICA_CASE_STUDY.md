# BOBINA TERMICA CASE STUDY — F03.1-B · Agente 3

## Respostas (90d rede + tela consolidada)

| # | Pergunta | Resposta |
|---|----------|----------|
| 1 | Quantas vezes aparece? | **5** na tela · **5** em DESPESAS_REDE |
| 2 | Empresas? | 5256, 5555, 5556, 5557 |
| 3 | Datas (amostra tela)? | 2026-03-21, 2026-04-17, 2026-05-12, 2026-05-13, 2026-05-15… |
| 4 | Fonte? | DESPESAS_REDE (financeiro) + espelho operacional quando match |
| 5 | Possui título? | Parcial — via TITULO_PAGAR quando valor+empresa coincidem |
| 6 | Fornecedor? | Quando presente em DESPESAS_REDE / TITULO_PAGAR |
| 7 | Plano de contas? | **Sim** — planoContaGerencialDescricao |
| 8 | Centro de custo? | Frequentemente vazio na rede |
| 9 | Operacional ou financeira? | **Ambos** — lançamento financeiro + fechamento caixa (match) |
| 10 | Duplicidade? | **Não** pós-correção P0.1-B (paridade 0) |

## Caso QA obrigatório — AP CASA CAIADA · 08/06/2026

| Campo | Valor |
|-------|-------|
| Origem real | Financeira |
| Fornecedor | — |
| Plano | BOBINA TERMICA |
| Centro custo | — |
| Documento | — |
| Linhagem | DESPESA → Financeiro → DESPESAS_REDE → Documento Financeiro → Evento:Material Operacional → Empresa:5555 → PDV:? → Turno:? → Operador:? |

Paridade valor QA: **0.0** (OK)
