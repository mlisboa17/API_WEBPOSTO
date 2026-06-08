# RECEIVABLES EXPANSION REPORT — F01.1.1

## Fontes auditadas

| Endpoint | HTTP | Registros | Usado no FC? |
|---|---|---:|---|
| TITULO_RECEBER | 200 | 11 | ✅ Sim |
| TITULO_RECEBER_REDE | 401 | 0 | ❌ 401 |
| CLIENTE | 200 | 200 | ❌ Cadastro only |
| CLIENTE_EMPRESA | 200 | 132 | ❌ Não integrado |
| CONSUMO_CLIENTE | 400 | 0 | ❌ 400 (params) |
| INTEGRACAO_LISTA_CLIENTE_PRAZO | 401 | 0 | ❌ 401 |
| CLIENTE_UNIDADE_NEGOCIO | 401 | 0 | ❌ 401 |

## Respostas

| Pergunta | Resposta |
|---|---|
| **Existe recebível oculto?** | Potencial em **CLIENTE_EMPRESA** (132 registros) e **CONSUMO_CLIENTE** (requer params de período/cliente). |
| **Fontes não utilizadas?** | TITULO_RECEBER_REDE, CLIENTE_PRAZO, UNIDADE_NEGOCIO — auth ou contrato pendente. |
| **Potencial de expansão?** | **Alto** em F05 Recebíveis: enriquecer CR com limite/prazo de CLIENTE + consumo faturado. |

## Situação atual FC (rede)

- CR vencido: **6** títulos — R$ **92,58**
- CR pendente: ver buckets API
