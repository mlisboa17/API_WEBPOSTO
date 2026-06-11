# PRESTAÇÃO DE CONTAS — FIELD CATALOG — Sprint D00

Documento referência: `Prestação de Contas - Não Consolida · AP CASA CAIADA · 08/06/2026 · 1º Turno`

## Catálogo base (24 campos F03.4-B)

| Campo | Descrição UI | Endpoint API | Disponível | Granularidade |
|---|---|---|---|---|
| funcionarioNome | Funcionário nominalmente identificado | — | False | — |
| funcionarioCodigo | Código do funcionário | CAIXA/CAIXA_REDE | True | turno |
| diferencaIndividual | Diferença individual por operador | CAIXA | True | turno |
| participacaoIndividual | Participação % individual no turno | — | False | — |
| produtividadeFuncionario | Produtividade por funcionário | — | False | — |
| vendasFuncionario | Vendas por funcionário | VENDA/VENDA_ITEM | partial | parcial |
| vendasProduto | Vendas por produto | VENDA_ITEM | True | item |
| cartaoDetalhado | Cartões detalhados (bandeira/operadora) | CAIXA_APRESENTADO | partial | forma agregada |
| valeFuncionario | Vale Funcionário | CAIXA_APRESENTADO + DESPESAS | True | turno agregado |
| despesaCaixa | Despesa lançada diretamente no caixa | CAIXA_APRESENTADO + DESPESAS_REDE | True | turno/plano |
| sangria | Sangria / retirada física | DESPESAS_REDE (semântico) | partial | lançamento |
| fundoCaixa | Fundo de Caixa (abertura) | — | False | — |
| prePago | Pré-pago detalhado | CAIXA_APRESENTADO | partial | forma agregada |
| emprestimo | Empréstimo funcionário | CAIXA_APRESENTADO | True | turno agregado |
| suprimento | Suprimento de caixa | MOVIMENTO_CONTA | partial | movimento |
| deposito | Depósito bancário vinculado | MOVIMENTO_CONTA | partial | movimento |
| transferencia | Transferência entre contas/caixa | TRANSFERENCIA_BANCARIA | True | movimento |
| movimentoConta | Movimentação bancária | MOVIMENTO_CONTA | True | movimento |
| formaPagamento | Formas de pagamento apresentadas | CAIXA_APRESENTADO | True | forma |
| combustivel | Combustível por produto | VENDA_ITEM/ANALISE_COMB | True | produto |
| turno | Turno operacional | CAIXA | True | turno |
| pdv | PDV / ponto de venda | CAIXA | True | turno |
| filial | Filial / empresa | CAIXA/EMPRESAS | True | empresa |

## Campos suspeitos confirmados (Bloco 1)

| Campo suspeito | Na UI/Prestação | Na API | Onde no Logos hoje |
|----------------|-----------------|--------|-------------------|
| sangria | Sim | Parcial (DESPESAS semântico) | F03.4-B sangria intelligence |
| suprimento | Sim | Parcial (MOVIMENTO_CONTA) | Não modelado |
| vale | Sim | Sim (CAIXA_APRESENTADO + DESPESAS) | F03.3 ledger |
| desconto | Sim | Parcial (VENDA_ITEM) | Sem dim operador |
| adiantamento | Sim | Parcial (DESPESAS/TITULO) | F03.2-A |
| falta / sobra | Sim | Derivado (CAIXA.diferenca) | F03.3 ledger |
| venda funcionário | Sim | Parcial (funcionarioCodigo) | Overview agregado |
| meta | Sim | **Não** (GRUPO_META isolado) | Não usado |
| produtividade | Sim | **Não** | F03.4 score parcial |

## Cobertura quantitativa

| Métrica | Valor |
|---------|-------|
| Campos catalogados UI | **31** |
| Exclusivos UI (sem API) | **5** — metaFuncionario, produtividadeFuncionario, participacaoIndividual, funcionarioNome, fundoCaixa… |
| Parciais na API | **6** |
| Endpoint dedicado prestação | **0** |

## Resposta Bloco 1

A Prestação exibe **mais campos nominais e de produtividade** do que qualquer payload consolidado. A API cobre **~70%** dos conceitos via decomposição (CAIXA + CAIXA_APRESENTADO + DESPESAS + VENDA), mas **4 campos são exclusivos da UI** e **7+ têm granularidade superior no documento**.
