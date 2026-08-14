# Cadastro de produtos — empresa 118508

Pipeline de cadastro de produtos na API WebPosto com gates que impedem escrita sem
evidência documental. Toda operação é `POST` no endpoint legado; não há `PUT`, `PATCH`,
`DELETE` nem rollback, então um cadastro errado é permanente. Os gates existem por isso.

## Fluxo

1. `fiscal_sheet_loader` lê a planilha de produtos a cadastrar e normaliza os campos.
2. `dfe_cost_resolver` apura o custo unitário a partir da NF-e de entrada.
3. `fiscal_resolver` decide a base de ICMS a partir da tributação observada na entrada.
4. `tax_table_matcher` casa a base decidida com as tabelas locais da empresa.
5. `scripts/preflight_fiscal_sheet_118508.py` classifica o lote e seleciona o microbatch.
6. `scripts/execute_microbatch_118508.py --batch NN` executa um POST por vez.
7. `scripts/verify_microbatch_118508.py --batch NN` relê a API e confere o resultado.

## Normalização da planilha

Planilhas gravam NCM e CEST como número e perdem o zero à esquerda: `9011110` é
`09011110` e `201600` é `0201600`. O loader completa à esquerda e registra que completou.
Campo vazio permanece vazio: CEST ausente não é CEST zero.

## Política de custo

O custo vem da NF-e de entrada autorizada e não cancelada mais recente que contenha o
EAN exato. Nunca é digitado, copiado de produto semelhante nem derivado de margem.

    custo = (vProd - desconto + frete + seguro + outras + IPI não recuperável
             + ICMS-ST cobrado) / quantidade

O IPI entra quando destacado, porque a empresa é comércio e não credita IPI. O ICMS-ST
cobrado em `CST 10` e `CST 30` entra porque a saída é sem débito e o valor não é
recuperável. Em `CST 60` a ST foi retida antes na cadeia e não é cobrada de novo.

A quantidade do divisor é a de unidades de venda, não a de embalagens. Quando a unidade
comercial é caixa, fardo ou display, a nota ainda pode declarar a quantidade tributável
em unidades, e esse fator vem do próprio documento: um display com `qTrib = 30 UNI` dá
trinta unidades. Quando a unidade tributável é peso ou repete a embalagem, o número de
unidades é indeterminado e o custo é recusado — dividir pelo número de caixas produziria
custo várias vezes maior que o real.

### Custo pendente

Produto sem NF-e de entrada pode ser cadastrado com custo zero apenas quando declarado
com `cost_status = PENDING` e quando a execução recebe a autorização explícita:

    ALLOW_PENDING_DFE_COST=true

A flag vale só para o processo e não é gravada em arquivo de ambiente. Sem ela, o
executor recusa custo zero. Cada produto nessa condição é registrado em
`pending_cost_update_118508.json` para atualização quando a compra chegar.

## Política fiscal

A base de ICMS nunca é inferida a partir do NCM. `CST 00` e `CST 60` são situações
distintas: produto que entrou tributado não herda base de produto que entrou substituído,
ainda que ambos sejam alimentos do capítulo 19.

A entrada é classificada em quatro situações:

| Classificação | Origem | Base aplicada |
| --- | --- | --- |
| `ST_COMPROVADA` | NF-e com CST de substituição ou ST retida | Base de ST, se casar integralmente com a tabela local |
| `SEM_ST_COMPROVADA` | NF-e com CST tributado e sem CEST | Base pela alíquota de entrada, confiança baixa |
| `ANTECIPACAO_POSSIVEL` | NF-e com CST tributado e com CEST | Base pela alíquota de entrada, confiança baixa, revisão obrigatória |
| `SEM_EVIDENCIA_DE_ENTRADA` | Sem NF-e | Só com base única sustentada por NCM e CEST; duas hipóteses bloqueiam |

Confiança alta exige evidência de entrada. Inferência sempre grava `confidence`,
`fiscal_risk`, `requires_accountant_review` e os campos inferidos, e o produto vai para
`accountant_review_118508.json`.

Capítulos de NCM com regime próprio (bebida alcoólica, tabaco, fármaco, combustível,
pirotécnico) não entram em lote automático.

Na analogia por NCM e CEST, contar itens não basta. A evidência precisa vir de pelo
menos três notas e dois fornecedores, com CST único e a maioria dos itens na mesma
família comercial do candidato. Itens concentrados em um fornecedor podem refletir a
prática dele, e não o regime da mercadoria. Produto cuja família não é reconhecida não
recebe base por analogia, porque afirmar semelhança sem reconhecer a mercadoria seria
inventar evidência.

## Duplicidade

O EAN não basta para decidir se o produto já existe. Fabricante que troca o código de
barras faz o mesmo item parecer novo, e cadastrar de novo dividiria estoque e histórico.
Por isso a descrição também é comparada: termos de ligação, embalagem e medida são
descartados e o produto é considerado repetido quando todos os termos restantes já
aparecem em um cadastro existente. Sabor ou variante diferente sobra um termo e não
casa. Como a medida é descartada, produtos que diferem apenas no tamanho são retidos
para conferência em vez de cadastrados — a decisão é de quem opera, não do lote.

## Roteamento e credencial

A empresa 118508 usa exclusivamente `WEBPOSTO_CONVENIENCIA_24_HORAS_KEY`, sem fallback.
O roteamento é por chave apenas e `empresaCodigo` não vai no corpo nem na query. Como a
mesma chave alcança mais de uma empresa, cada POST é seguido de leitura em
`PRODUTO_EMPRESA` para confirmar o vínculo. Antes de escrever, um produto sentinela
conhecido é consultado para confirmar que a chave resolve para a empresa pretendida.

Chaves, certificados e chaves de acesso de NF-e nunca aparecem em log, relatório ou
teste: a chave de acesso é sempre mascarada.

## Execução em microbatches

No máximo cinco produtos por lote, um POST por vez, verificação individual entre eles.
Qualquer divergência interrompe o lote. Cada lote grava uma trava persistente que recusa
reexecução, e o checkpoint impede reenvio de EAN já processado.
