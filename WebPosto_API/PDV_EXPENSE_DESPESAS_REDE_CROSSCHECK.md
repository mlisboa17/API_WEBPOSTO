# PDV EXPENSE DESPESAS_REDE CROSSCHECK — F03.1

---

## Respostas

| # | Pergunta | Resposta |
|---|----------|----------|
| 1 | Despesa caixa aparece em DESPESAS_REDE? | **Sim** (15.8% match) |
| 2 | Duplicidade? | **Sim** (393 chaves duplicadas) |
| 3 | Lançamento financeiro correspondente? | **Sim** |
| 4 | Valor bate? | **Sim** (100.0% paridade exata) |
| 5 | Centro/plano rastreável? | **Não** |

---

## Métricas (7d)

| Métrica | Valor |
|---------|-------|
| Despesas caixa (apurado ≠ 0) | 19 |
| Registros DESPESAS_REDE | 1317 |
| Matched | 3 |
| Unmatched | 16 |
| Taxa match | 15.8% |

## Chaves de cruce utilizadas

```text
(empresaCodigo, data[:10], round(valor, 2))
+ planoConta / centroCusto / descricaoDocumento quando matched
```

## Campos amostra DESPESAS_REDE

`empresaCodigo, planoContaGerencialCodigo, descricaoDocumento, data, valor`

**Conclusão:** parte das despesas de caixa **reflete** lançamentos financeiros consolidados; unmatched indica despesas operacionais de fechamento **sem espelho 1:1** na rede.
