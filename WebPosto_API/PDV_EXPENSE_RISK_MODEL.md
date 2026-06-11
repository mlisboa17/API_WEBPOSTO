# PDV EXPENSE RISK MODEL — F03.1

---

## Respostas

| # | Pergunta | Resposta |
|---|----------|----------|
| 1 | Deve entrar no Cash Risk Score? | **Sim (peso baixo)** |
| 2 | Com qual peso? | **8%** (máx recomendado 10%) |
| 3 | Evitar falso positivo? | Ver regras abaixo |

---

## Proposta de integração (F03.2 — não implementada)

| Regra | Efeito no score |
|-------|-----------------|
| Despesa sem correspondência DESPESAS_REDE | +penalidade leve |
| Despesa com correspondência | neutro |
| Recorrência operador/PDV | +penalidade leve |
| Suprimento documentado | −penalidade leve |

## Anti-falso-positivo

- Exigir match DESPESAS_REDE antes de penalizar
- Separar VALE/SUPRIMENTO de DESPESA_CAIXA
- Não misturar despesaApurado (fluxo) com despesaDiferenca (componente)

## Evidência quantitativa

| Indicador | Valor |
|-----------|-------|
| Correlação despesa×diff | -0.0409 |
| Match DESPESAS_REDE | 15.8% |

**Justificativa:** baixa paridade DESPESAS_REDE → penalizar risco operacional
