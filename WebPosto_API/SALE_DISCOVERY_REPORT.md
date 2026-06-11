# SALE DISCOVERY — D01 · Agente 2

Registros: **200**

## Campos

caixaCodigo, cancelada, centroCustoCodigo, centroCustoVeiculo, clienteCodigo, clienteCodigoExterno, clienteCpfCnpj, codigo, dataHora, destacaAcrescimoDesconto, empresaCodigo, formaPagamento, funcionarioCodigo, identificacaoFidelidade, itens, modeloDocumento, motoristaCodigo, notaChave, notaCodigo, notaNumero, notaSerie, placaVeiculo, totalVenda, troco, vendaCodigo, vendaUuid

## Respostas

| # | Pergunta | Resposta | Cobertura |
|---|---|---|---|
| 1 | Ligação com caixa? | **Sim** | 100.0% |
| 2 | Ligação com operador? | **Sim** | 100.0% |
| 3 | Venda cancelada? | **Sim** | 100.0% |
| 4 | Troco? | **Sim** | 100.0% |
| 5 | PDV direto? | **Não** | 0.0% |

**Nota:** `pdvCodigo` normalmente via **CAIXA** (join `caixaCodigo`), não em VENDA.
