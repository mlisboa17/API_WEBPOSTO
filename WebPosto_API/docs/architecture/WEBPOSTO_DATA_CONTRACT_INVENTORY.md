# Inventário de dados WebPosto — Sprint 1

## Escopo da coleta

Este inventário cobre exclusivamente as licenças 11495, 5555 e 74014. Toda coleta deve preservar `empresaCodigo`, período e departamento. Tokens são identificadores de acesso e nunca podem aparecer em relatórios, logs ou snapshots.

## Estado atual

| Domínio | Endpoint WebPosto | Chave de segregação | Paginação | Contrato | Estado |
|---|---|---|---|---|---|
| Empresas | `/INTEGRACAO/EMPRESAS` | `empresaCodigo` | A confirmar | `LicensedCompany` | Limitado às 3 licenças |
| Grupos | `/INTEGRACAO/GRUPO` | `grupoCodigo` | A confirmar | `ProdutoGrupoItem` | 23 grupos confirmados nas 3 licenças |
| Metas de grupo | `/INTEGRACAO/GRUPO_META` | código da meta | A confirmar | Pendente | Não representa departamento |
| Produtos | `/INTEGRACAO/PRODUTO` | `produtoCodigo`, `grupoCodigo` | Obrigatória | `NormalizedProductCatalogEntry` | 419 produtos observados |
| Produto por empresa | `/INTEGRACAO/PRODUTO_EMPRESA` | `empresaCodigo`, `produtoCodigo` | Obrigatória | `NormalizedProductCatalogEntry` | Junção implementada |
| Vendas | `/INTEGRACAO/VENDA` | `empresaCodigo`, `vendaCodigo` | Obrigatória | Pendente | Inventariar campos reais |
| Itens vendidos | `/INTEGRACAO/VENDA_ITEM` | `empresaCodigo`, `vendaCodigo`, `vendaItemCodigo` | Obrigatória | Pendente | Fonte de receita departamental |
| Formas de pagamento | `/INTEGRACAO/VENDA_FORMA_PAGAMENTO` | `empresaCodigo`, `vendaCodigo` | Obrigatória | Pendente | Não atribuir departamento sem join |
| Despesas | `/INTEGRACAO/CONSULTAR_DESPESAS_FINANCEIRO_REDE` | `empresaCodigo` + vínculo gerencial | Obrigatória | Pendente | Departamento precisa ser comprovado |
| Caixa | `/INTEGRACAO/CAIXA` | `empresaCodigo`, caixa/turno | A confirmar | Pendente | Base para quebra e fechamento |
| Estoque | `/INTEGRACAO/PRODUTO_ESTOQUE` | `empresaCodigo`, `produtoCodigo` | Obrigatória | Pendente | Departamento deriva do produto |
| Combustíveis | `/INTEGRACAO/PRODUTO_COMBUSTIVEL` | `empresaCodigo`, produto/LMC | A confirmar | Pendente | Operação exclusiva de Combustíveis |

## Campos confirmados do catálogo

| Campo normalizado | Possíveis campos de origem | Regra |
|---|---|---|
| `produtoCodigo` | `produtoCodigo`, `codigo` | Obrigatório e positivo |
| `nomeProduto` | `nomeProduto`, `nome`, `descricao`, `descricaoProduto` | Fallback sinalizado quando ausente |
| `grupoCodigo` | `grupoCodigo`, `codigoGrupo`, `grupoProdutoCodigo` | Principal chave departamental |
| `grupoProduto` | `nomeGrupo`, `grupoProduto`, `descricaoGrupo` | Informativo; código prevalece |
| `tipoProduto` | `tipoProduto`, `produtoTipo` | Significado de C/P/U ainda pendente |
| `combustivel` | `combustivel`, `tipoCombustivel`, `tipoProduto=C` | Evidência auxiliar |
| `produtoLmcCodigo` | `produtoLmcCodigo` | Evidência de combustível |
| `empresaCodigo` | contexto de `/PRODUTO_EMPRESA` | Nunca inferir outra empresa |

## Regras de departamentalização

1. `grupoCodigo` confirmado é a regra prioritária.
2. Nome do grupo é auxiliar e não substitui código conhecido.
3. Tipo do produto só será usado após confirmação formal de C/P/U.
4. Produto sem grupo conhecido permanece `NAO_CLASSIFICADA`.
5. COMODATO, DIVERSOS e USO E CONSUMO não entram em KPIs.
6. Forma de pagamento e caixa não recebem departamento sem ligação rastreável com a venda.
7. Despesas compartilhadas não são rateadas sem regra aprovada.

## Grupos reais confirmados

### Combustíveis

- 24554 — COMBUSTIVEIS

### Lubrificantes

- 24555 — LUBRIFICANTES
- 24556 — ADITIVOS
- 24557 — FLUIDOS
- 28811 — FILTROS
- 62009 — PALHETAS

### Conveniência

- 162956 — TABACO
- 162989 — BAZAR
- 51350 — ANTIGO GRUPO CIGARRO
- 55443 — DIVERSOS LOJA
- 55444 — FAST FOOD
- 55445 — MERCEARIA
- 55446 — SALGADINHOS-BISCOITOS
- 55447 — SORVETES-GELO
- 55449 — BOMBONIERI
- 55450 — BEBIDAS ALCOOLICAS
- 55451 — BEBIDAS ENERGETICAS
- 55452 — BEBIDAS GASEIFICADAS
- 55453 — BEBIDAS NATURAIS
- 56795 — AGUA RETORNALVEL

### Quarentena gerencial

- 25016 — COMODATO
- 26039 — DIVERSOS
- 29273 — USO E CONSUMO

## Pendências para concluir a Sprint 1

- Confirmar C/P/U com documentação ou amostra inequívoca.
- Capturar esquema real de vendas, itens, despesas, caixa e estoque nas três licenças.
- Medir paginação, duplicidade e cobertura por endpoint/licença.
- Criar contratos Pydantic para venda, item, despesa, caixa e estoque.
- Aprovar a quarentena gerencial com a Diretoria.
