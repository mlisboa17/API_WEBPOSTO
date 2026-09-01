# D02 — Other Payment Natures (Agente 5)

> Pré-conferência interna por natureza — evidência externa obrigatória para fechamento. [D02_CONCEPTUAL_CORRECTION.md](./D02_CONCEPTUAL_CORRECTION.md)

| Natureza | Validação | Evidência primária | Gap |
|---|---|---|---|
| NOTAS | apresentado vs apurado | notaPrazo* | sparse |
| CHEQUE À VISTA | dif turno | cheque* | campos vazios |
| CHEQUE PRÉ | dif + vencimento | chequePre* | baixa cobertura |
| CARTA FRETE | dif turno | cartaFrete* | raro |
| VALE CLIENTE | dif + saldo cliente | valeCliente* + TITULO | parcial |
| DESPESA | dif + plano conta | despesa* + DESPESAS | OK |
| EMPRÉSTIMO | dif + ledger func. | emprestimo* | médio |
| PRÉ-PAGO | dif agregado | prePag* | parcial |
| VALE FUNCIONÁRIO | dif + ledger | valeFun* + DESPESAS | OK |
| TRANSF. CRÉDITO | dif + MOVIMENTO | transfBanc* | vínculo banco |
| TRANSF. DÉBITO | dif | transfDeb* | idem |
| CHEQUE PAGAR | dif | chequePagar* | baixo volume |
| FUNDO CAIXA DÉBITO | dif + abertura | fundoCxDeb* | parcial |

Cada natureza usa estratégia em `nature_strategies.py` — tolerância R$ 0,01; divergência ≥ R$ 10,00 → DIVERGENT.
