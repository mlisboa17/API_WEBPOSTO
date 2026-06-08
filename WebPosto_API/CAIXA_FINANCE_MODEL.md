# CAIXA_FINANCE_MODEL — A03.6

**Período:** 2026-06-01 .. 2026-06-07

## O WebPosto considera despesa de caixa?

**Sim, agregada** em `CAIXA_APRESENTADO`: campos `valeClienteApresentado, valeClienteApurado, valeClienteDiferenca, emprestimoApresentado, emprestimoApurado, emprestimoDiferenca...`

## Respostas

| Conceito | Existe no token? | Campo |
|---|---|---|
| Despesa caixa agregada | **Sim** | despesaApresentado/Apurado/Diferenca |
| Vale funcionário | **Sim** | valeFunApresentado/Apurado/Diferenca |
| Empréstimo | **Sim** | emprestimoApresentado/Apurado/Diferenca |
| Quebra/diferença | **Sim** | diferenca (CAIXA), *Diferenca por forma |
| Sangria explícita | **Não** | — |
| Suprimento | **Não** | — |
| Fundo de caixa | **Não** | — |
| Retirada | Parcial | via DESPESAS_REDE (plano gerencial) |

**Conclusão:** Despesa de caixa = agregados despesaApresentado/Apurado/Diferenca em CAIXA_APRESENTADO; sangria/suprimento não expostos como campos dedicados no token

**Registros:** CAIXA=21, APRESENTADO=21
