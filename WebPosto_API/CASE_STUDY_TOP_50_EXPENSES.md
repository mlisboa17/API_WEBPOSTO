# CASE STUDY TOP 50 EXPENSES — F03.1-A

## Caso obrigatório: BOBINA TERMICA

| Pergunta | Resposta |
|----------|----------|
| Existe no caixa (7d)? | **Não** |
| Existe DESPESAS_REDE (7d)? | **Não** |
| Existe DESPESAS_REDE (30d)? | **Sim** |
| Existe Título Pagar? | **Não** |
| Linhagem caixa→financeiro? | **Não** — despesa financeira sem espelho caixa |

### Amostras BOBINA (30d · DESPESAS_REDE)

- 2026-05-12 · emp 5556 · R$ 16,60 · bobina termica
- 2026-05-13 · emp 5555 · R$ 135,00 · ref uma caixa de bobina termica
- 2026-05-12 · emp 5556 · R$ 16,60 · bobina termica
- 2026-05-13 · emp 5555 · R$ 135,00 · ref uma caixa de bobina termica
- 2026-05-12 · emp 5556 · R$ 16,60 · bobina termica
- 2026-05-13 · emp 5555 · R$ 135,00 · ref uma caixa de bobina termica

## Top 5 maiores lançamentos DESPESAS_REDE (7d)

| # | Valor | Descrição | Caixa? | Título? | Plano |
|---|-------|-----------|--------|---------|-------|
| 1 | R$ 5.008,48 | REF NF:000064790 - SOLAR INOVE - PE | Não | Não | — |
| 2 | R$ 5.008,48 | REF NF:000064790 - SOLAR INOVE - PE | Não | Não | — |
| 3 | R$ 5.008,48 | REF NF:000064790 - SOLAR INOVE - PE | Não | Não | — |
| 4 | R$ 3.926,00 | FARDAMNETOS | Não | Não | — |
| 5 | R$ 3.926,00 | FARDAMNETOS | Não | Não | — |

**Total auditado:** 50 maiores lançamentos financeiros (ver JSON `top50`).
