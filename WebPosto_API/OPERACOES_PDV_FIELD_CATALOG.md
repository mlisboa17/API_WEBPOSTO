# OPERAÇÕES PDV — FIELD CATALOG — Sprint D00

Módulo UI: *"Detalha todas as operações realizadas pelos funcionários no webPostoPDV"*

**Descoberta crítica:** não existe `/INTEGRACAO/OPERACOES_PDV` nem equivalente `CONSULTAR_*_PDV` no token atual.

## Operações UI vs proxies API

| Operação UI | Descrição | Proxy API | Cobertura | Gap |
|---|---|---|---|---|
| cancelamento | Cancelamento de venda | VENDA.cancelada + NFCE.situacao | partial | Sem log de autorizador |
| estorno | Estorno | FINANCEIRO_EXCLUSAO | partial | Auditoria, não operação PDV |
| aberturaCaixa | Abertura de caixa | CAIXA.abertura/fechado | yes | F03 cash ops |
| fechamentoCaixa | Fechamento | CAIXA.fechamento/consolidado | yes | F03 cash ops |
| troco | Troco | VENDA.troco | yes | Não ligado a operador no Logos |
| sangria | Sangria PDV | DESPESAS_REDE (semântico) | partial | Sem endpoint PDV |
| suprimento | Suprimento PDV | MOVIMENTO_CONTA | partial | Sem endpoint PDV |
| venda | Venda | VENDA + VENDA_ITEM + ABASTECIMENTO | yes | Overview + fuel |
| desconto | Desconto na venda | VENDA_ITEM.totalDesconto | partial | Por item, não por operador consolidado |
| autorizacao | Autorização gerencial | — | none | Não exposto na API token atual |
| abastecimento | Abastecimento bomba | ABASTECIMENTO | yes | codigoFrentista ≈ operador |

## VENDA — campos operacionais (200 reg probe)

`empresaCodigo, vendaCodigo, notaCodigo, funcionarioCodigo, clienteCodigo, destacaAcrescimoDesconto, clienteCpfCnpj, dataHora, notaNumero, notaSerie, totalVenda, caixaCodigo, notaChave, modeloDocumento, cancelada, placaVeiculo, clienteCodigoExterno, centroCustoCodigo, centroCustoVeiculo, identificacaoFidelidade, vendaUuid, motoristaCodigo, troco, itens, formaPagamento, codigo`

## ABASTECIMENTO — campos operacionais (200 reg)

`dataFiscal, horaFiscal, codigoBico, codigoProduto, quantidade, valorUnitario, valorTotal, codigoFrentista, afericao, vendaItemCodigo, precoCadastro, tabelaPrecoA, tabelaPrecoB, tabelaPrecoC, empresaCodigo, dataHoraAbastecimento, stringFull, placa, abastecimentoCodigo, encerrante, codigo`

## VENDA_ITEM — operador por item

Inclui **`funcionarioCodigo`**, **`totalDesconto`**, **`bicoCodigo`**, **`encerrante` implícito via ABASTECIMENTO**

## Risco F04 Performance

Se `VENDA` + `VENDA_ITEM` + `ABASTECIMENTO` forem consolidados por `funcionarioCodigo` + `turnoCodigo` + `pdvCodigo`, o módulo Performance pode **substituir parcialmente** Operações PDV — hoje o Logos usa apenas **CAIXA.diferenca** (F03.3/F03.4).
