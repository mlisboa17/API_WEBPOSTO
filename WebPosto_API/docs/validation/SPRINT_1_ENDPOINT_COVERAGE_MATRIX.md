# Sprint 1 — Matriz de cobertura dos endpoints WebPosto

**Atualização:** 2026-07-24  
**Fonte:** capturas mascaradas em `etl/evidence/sprint_21a_r2_hotfix`  
**Escopo autorizado:** Posto VIP (11495), AP Casa Caiada (5555) e Posto Doze Filial II (74014)

## Cobertura observada

| Endpoint | Posto VIP | Casa Caiada | Posto Doze | Diagnóstico |
|---|---:|---:|---:|---|
| EMPRESAS | HTTP 200 · 2 | HTTP 200 · 2 | sem evidência | Parcial |
| GRUPO | HTTP 200 · 24 | HTTP 200 · 24 | HTTP 200 · 24 | Validado ao vivo |
| PRODUTO | HTTP 200 · 200 | HTTP 200 · 200 | HTTP 200 · 1.871 | Paginação integral comprovada no Posto Doze |
| PRODUTO_EMPRESA | HTTP 200 · 200 | HTTP 200 · 200 | sem evidência | Possível limite de página |
| VENDA | HTTP 200 · 200 | HTTP 200 · 200 | HTTP 200 · 638 | Paginação integral comprovada no Posto Doze |
| VENDA_ITEM | HTTP 200 · 200 | HTTP 200 · 200 | HTTP 200 · 924 | Paginação integral comprovada no Posto Doze |
| PRODUTO_ESTOQUE | HTTP 200 · 200 | HTTP 200 · 200 | HTTP 200 · 1.871 | Datas obrigatórias; paginação integral no Posto Doze |
| CONSULTAR_DESPESAS_FINANCEIRO_REDE | HTTP 200 · 11 | HTTP 200 · 3 | HTTP 200 · 9 | Escopo isolado ao vivo em 2026-07-23 |
| CAIXA | HTTP 200 · 2 | HTTP 200 · 1 | HTTP 200 · 1 | Validado ao vivo em 2026-07-23 |

Os números representam `HTTP status · records_count`. Uma resposta com exatamente
200 registros não prova completude. PRODUTO, PRODUTO_EMPRESA, VENDA e VENDA_ITEM
devem usar paginação por cursor até página curta ou vazia.

## Validação dos contratos

- VENDA, VENDA_ITEM, CONSULTAR_DESPESAS_FINANCEIRO_REDE e CAIXA foram validados
  contra amostras reais de Posto VIP e Casa Caiada e contra 20 registros ao vivo
  do Posto Doze (ou todos, quando a resposta possuía menos de 20).
- Os contratos preservam campos adicionais e não fabricam departamento,
  centro de custo ou identificador de despesa.
- O paginador remove duplicatas exatas, detecta cursor travado, limite de segurança
  e formato de payload incompatível.
- No Posto Doze, a paginação por `ultimoCodigo` terminou por página curta, sem
  duplicatas: PRODUTO 1.871/10 páginas, VENDA 638/4, VENDA_ITEM 924/5 e
  PRODUTO_ESTOQUE 1.871/10.
- O endpoint de despesas de rede retornava empresas fora do escopo. O gateway agora
  restringe a resposta às três licenças e, quando solicitado, à empresa escolhida.

## Bloqueios para fechar a Sprint 1

1. Persistir capturas mascaradas do Posto Doze no próximo ciclo de evidências.
2. Executar e registrar a paginação completa de Posto VIP e Casa Caiada em tarefas
   particionadas; a execução conjunta excedeu 60 segundos.
3. Confirmar gerencialmente os significados de `tipoProduto` C, P e U.
4. Aprovar o tratamento de COMODATO, DIVERSOS e USO E CONSUMO.

## Tipos de produto observados

Na primeira página de 200 produtos: Posto VIP apresentou C=9, P=136, U=55;
Casa Caiada C=3, P=45, U=152; Posto Doze C=4, P=111, U=85. Esses dados provam uso,
mas não o significado de negócio. A classificação permanece bloqueada até confirmação
do WebPosto ou aprovação gerencial.

## Regra de confiança

Nenhum endpoint desta matriz é considerado completo apenas porque retornou HTTP 200.
Completude exige término comprovado da paginação, ausência de cursor travado e
validação da empresa de cada registro.
