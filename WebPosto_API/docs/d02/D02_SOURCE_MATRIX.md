# D02 — Source Matrix (Agente 1)

> Expectativa = WebPosto/Prestação · Evidência externa = ver [D02_CONCEPTUAL_CORRECTION.md](./D02_CONCEPTUAL_CORRECTION.md)

| natureza | campo necessário | fonte atual | endpoint/tabela | cobertura | gap | estratégia |
|---|---|---|---|---|---|---|
| DINHEIRO | apresentado/apurado/diferença | CAIXA_APRESENTADO | `/INTEGRACAO/CAIXA_APRESENTADO` | alta | sangria nominal | cruzar DESPESAS semântico + MOVIMENTO_CONTA |
| NOTAS | notaPrazo* | CAIXA_APRESENTADO | idem | média | sparse em alguns turnos | agregar por turno; tolerância centavo |
| CHEQUE À VISTA | cheque* | CAIXA_APRESENTADO | idem | baixa | campos vazios em amostras | NEEDS_REVIEW quando movimento=0 |
| CHEQUE PRÉ | chequePre* | CAIXA_APRESENTADO | idem | parcial | 16,7% cobertura amostra D02 | validar por turno com evidência |
| CARTÃO | cartao* + decomposição | CAIXA_APRESENTADO + VFP | CAIXA_APRESENTADO + `/INTEGRACAO/VENDA_FORMA_PAGAMENTO` | parcial | NSU/TEF ausente em VIP 30d | normalização bandeira/adquirente; UNKNOWN se sem adm |
| CARTA FRETE | cartaFrete* | CAIXA_APRESENTADO | idem | baixa | zero em janelas curtas | exibir somente com movimento |
| VALE CLIENTE | valeCliente* | CAIXA_APRESENTADO | idem | média | — | cruzar TITULO/ledger quando disponível |
| DESPESA | despesa* + plano | CAIXA_APRESENTADO + DESPESAS | DESPESAS_REDE + CAIXA_APRESENTADO | alta | classificação nominal | ExpenseLineage + F03.3 |
| EMPRÉSTIMO | emprestimo* | CAIXA_APRESENTADO | idem | média | — | cruzar employee ledger |
| PRÉ-PAGO | prePag* | CAIXA_APRESENTADO | idem | parcial | 50% amostra | agregado turno |
| VALE FUNCIONÁRIO | valeFun* | CAIXA_APRESENTADO + DESPESAS | idem | alta | — | cruzar VALE ledger |
| TRANSF. CRÉDITO | transfBanc* | CAIXA_APRESENTADO + MOVIMENTO | TRANSFERENCIA_BANCARIA | média | vínculo bancário parcial | evidência MOVIMENTO_CONTA |
| TRANSF. DÉBITO | transfDeb* | CAIXA_APRESENTADO | idem | média | — | idem |
| CHEQUE PAGAR | chequePagar* | CAIXA_APRESENTADO | idem | baixa | — | NEEDS_REVIEW |
| FUNDO CAIXA DÉBITO | fundoCxDeb* | CAIXA_APRESENTADO + CAIXA.abertura | CAIXA + CAIXA_APRESENTADO | parcial | rótulo Prestação | fundo via abertura (D02 nominal) |

**Premissa:** API transacional cobre ~87,5–97,5% da reconstrução (D01/D02 nominal). Gaps residuais: meta/layout Prestação (~2,5%).

**Evidência:** `scripts/d02_hidden_nominal_layer.json`, `PRESTACAO_FIELD_CATALOG.md`, runtime VALUE-03/04.
