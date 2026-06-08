# CORPORATE_EXPENSE_CLASSIFICATION — A03.7

Classificador LOGOS SPACE (regras em `audit_a03_7_corporate_finance.py`).

| Categoria LOGOS | Registros | Valor | Exemplos |
|---|---:|---:|---|
| OUTROS | 193 | R$ 64091.26 | pagamento alamoa; PARA SR MOISES |
| DESPESA_PESSOAL | 118 | R$ 62045.01 | Vale de funcionário referente a consolidação de caixa; Vale  |
| DESPESA_OPERACIONAL | 79 | R$ 4420.31 | SR MOISES( CREDITO TELEFONE SR MOISES); AGUA PARA CONSUMO |
| COMPRAS | 39 | R$ 5681.12 | ref material da reforma; ref a material da reforma |
| FINANCEIRO | 2 | R$ 87.50 | REF. PAG. JULI DÔCES; REF PAGAMENTO DOCES |
| DESPESA_COMERCIAL | 1 | R$ 6.00 | 1 FLANELA BRINDE |

## Mapeamento para diretoria

- DESPESA_PESSOAL + DESPESA_OPERACIONAL → custo operacional
- COMPRAS → CMV / insumos
- FINANCEIRO → resultado financeiro
- OUTROS → revisão manual periódica
