# OUTROS EXPENSES DEEP AUDIT — F01.2

**Período:** 2026-06-01 → 2026-06-07

## Respostas obrigatórias

| Pergunta | Resposta |
|---|---|
| **Quais descrições compõem OUTROS?** | Top 20 abaixo (amostra 193 registros) |
| **Quanto valor em OUTROS?** | R$ 64193.26 de R$ 136784.10 (**46.9%**) |
| **Reclassificar automaticamente?** | **Parcial** — expandir keywords em `logos_expense_classifier.py` |
| **Novas categorias?** | Manter 7 LOGOS; mapear padrões recorrentes OUTROS → FINANCEIRO/COMPRAS |

## Top 20 descrições OUTROS

| # | Descrição | Qtd |
|---|-----------|----:|
| 1 | POSTO | 4 |
| 2 | passagem josiane | 3 |
| 3 | folguista joao | 3 |
| 4 | PARA SR MOISES | 2 |
| 5 | SERVIÇO POSTO | 2 |
| 6 | sr moises | 2 |
| 7 | SR. MOISES / COM PEDRO | 2 |
| 8 | FRETE TELHA | 2 |
| 9 | para sr,o moises | 2 |
| 10 | ref pag apoio loja | 2 |
| 11 | pagamento alamoa | 1 |
| 12 | para seu moises | 1 |
| 13 | abastecimento sr moises | 1 |
| 14 | REMEDIO SR MOISES | 1 |
| 15 | ABASTECIMENTO SR MOISES | 1 |
| 16 | CAFE SR MOISES | 1 |
| 17 | MOISES( CARLOS ALBERTO) | 1 |
| 18 | REF (SEU MOISES PALMEIRA) | 1 |
| 19 | para moisés | 1 |
| 20 | ref troca da mangueira | 1 |

## Meta redução OUTROS

| Atual | Meta F01.3 |
|------:|-----------:|
| **46.9%** | **< 15%** |

## Ações recomendadas (sem implementar nesta sprint)

1. Adicionar keywords para top 10 descrições OUTROS
2. Revisão manual amostra 50 registros OUTROS > R$ 500
3. Validar após reclassificação em F01.3 BI

Evidência JSON: `scripts/outros_expenses_audit.json`
