# Sprint 1 — Combustíveis

## Objetivo

Construir a primeira trilha departamental confiável do webposto CODEX, restrita a Combustíveis e às três empresas licenciadas.

## Cobertura observada

Período consultado: 01/07/2026 a 17/07/2026.

| Empresa | Código | Combustíveis retornados | Litros observados | Endpoint validado |
|---|---:|---:|---:|---|
| Posto VIP | 11495 | 8 | 156.738,88 | `/api/v1/fuel/executive` |
| AP Casa Caiada | 5555 | 4 | 12.649,78 | `/api/v1/fuel/executive` |
| Posto Doze Filial II | 74014 | 7 | 183.603,04 | `/api/v1/fuel/executive` |

Os volumes acima comprovam disponibilidade operacional, mas ainda não constituem DRE. Receita, custo e margem somente serão publicados após reconciliação por produto e empresa.

## Contrato entregue

`FuelVolumeFact` garante:

- `empresa_codigo` limitado às três licenças;
- `produto_codigo` positivo;
- volume maior que zero e normalizado em três casas;
- departamento fixo `combustiveis`;
- origem explícita `CONSULTAR_LMC_REDE`;
- produto LMC e data de referência preservados quando disponíveis.

`FuelSaleItemFact` garante:

- chave única `empresaCodigo + vendaCodigo + vendaItemCodigo`;
- classificação somente por grupo 24554 ou evidência de LMC/bico/tanque;
- litros, preço de venda, preço de custo, faturamento e custo total normalizados;
- itens sem evidência colocados em quarentena;
- duplicidades removidas antes da agregação.

## Amostra controlada de VENDA_ITEM

Consulta de 01/07/2026. O parâmetro `tamanhoPagina=10` foi enviado, mas a API retornou 200 registros para cada licença e não apresentou metadados claros de total ou última página.

| Empresa | Itens retornados | Com evidência operacional de combustível | Duplicados na amostra |
|---|---:|---:|---:|
| Posto VIP | 200 | 120 | 0 |
| AP Casa Caiada | 200 | 198 | 0 |
| Posto Doze Filial II | 200 | 200 | 0 |

Os itens restantes não são considerados loja automaticamente: eles permanecem em quarentena até o cruzamento com `PRODUTO.grupoCodigo`.

### Campos financeiros confirmados

- `quantidade`, `precoVenda`, `precoCusto`;
- `totalVenda`, `totalCusto`;
- `totalDesconto`, `totalAcrescimo`;
- `produtoCodigo`, `produtoLmcCodigo`;
- `bicoCodigo`, `tanqueCodigo`;
- `empresaCodigo`, `vendaCodigo`, `vendaItemCodigo`, `dataMovimento`.

### Risco de paginação

A paginação foi comprovada em 01/07/2026. `/VENDA_ITEM` usa `ultimoCodigo`, cujo valor é o campo `codigo` do último item retornado. O endpoint `/CONSULTAR_VENDA_ITEM_REDE` respondeu 401 e o fallback unitário é o contrato operacional válido.

| Empresa | Lotes | Itens únicos | Duplicidades | Término | Cursor crescente |
|---|---:|---:|---:|---|---|
| Posto VIP | 6 | 1.197 | 0 | lote menor que 200 | Sim |
| AP Casa Caiada | 2 | 278 | 0 | lote menor que 200 | Sim |
| Posto Doze Filial II | 5 | 999 | 0 | lote menor que 200 | Sim |

O coletor foi corrigido para derivar o cursor também quando a resposta é uma lista simples. Cursor parado, limite de segurança ou falha HTTP interrompem o cálculo com erro explícito; resultados parciais não são publicados como totais.

## Fontes do departamento

| Finalidade | Fonte | Situação |
|---|---|---|
| Volume vendido | `CONSULTAR_LMC_REDE` | Disponível |
| Produto e vínculo LMC | `PRODUTO`, `PRODUTO_COMBUSTIVEL` | Parcialmente contratado |
| Receita de venda | `VENDA_ITEM` / resumo executivo | Requer reconciliação |
| Custo de aquisição | `ABASTECIMENTO` | Motor existente, requer validação por empresa/produto |
| Margem por litro | venda menos aquisição | Não publicar antes da reconciliação |
| Estoque físico | `TANQUE`, `ESTOQUE_PERIODO`, LMC | Próximo incremento |
| Perdas e diferenças | vendas × LMC × estoque | Próximo incremento |

## Próximas entregas

1. Reconciliar produto normal com `produtoLmcCodigo`.
2. Validar litros e faturamento por empresa e produto.
3. Validar custo médio de aquisição por empresa e produto.
4. Calcular preço médio de venda, custo/litro e margem/litro.
5. Conciliar venda, LMC e estoque físico.
6. Expor KPIs de Combustíveis na tela presidencial sem qualquer valor de loja.

## Incremento de reconciliação entregue

O endpoint `GET /api/v1/fuel/sales-reconciliation` entrega, separadamente para cada empresa:

- produtos de combustível classificados;
- litros vendidos;
- faturamento registrado;
- custo registrado no item;
- margem registrada;
- preço médio de venda por litro;
- custo médio registrado por litro;
- cobertura, quarentena, duplicidades e prova de paginação.

Não existe total genérico da rede no contrato (`consolidacaoGenerica=false`). Uma empresa não licenciada recebe HTTP lógico 403 no envelope de erro.

### Observação sobre margem

`margemRegistrada` usa o `totalCusto` informado no item vendido. Ela ainda não é a margem gerencial definitiva. O próximo passo é confrontá-la com o custo médio de aquisição vindo de `ABASTECIMENTO`, por empresa e produto, antes de publicar o indicador para a Presidência.

## Critério para publicar na Presidência

Um KPI financeiro de Combustíveis só pode ser exibido quando possuir empresa, produto, período, volume, valor, fonte e reconciliação. Cobertura parcial deve aparecer como parcial; ausência nunca será transformada em zero.
