# API VS UI — GAP ANALYSIS — Sprint D00

## 1. Campos na UI/Prestação sem equivalente API

- `funcionarioNome`
- `participacaoIndividual`
- `produtividadeFuncionario`
- `fundoCaixa`
- `metaFuncionario`
- `tipoMovimentoCaixa (SERVICO/TROCA)`
- `autorizacaoPDV`
- `sangriaDestino`
- `suprimentoDestino`

## 2. Campos na API sem equivalente UI/Prestação

- `classificacaoLogosV3`
- `expenseLineage`
- `snapshotTTL`
- `tituloPagarAberto detalhado`
- `FINANCEIRO_EXCLUSAO`
- `LANCAMENTO_CONTABIL`
- `planoContaGerencialNivel`

## 3. Relatórios/telas mais ricos que APIs consolidadas

| Tela/Relatório UI | API mais próxima | Gap principal |
|---|---|---|
| Prestação de Contas (PDF/UI) | CAIXA+DESPESAS API | Nome, produtividade, participação %, fundo caixa |
| Operações PDV (UI) | VENDA+ABASTECIMENTO API | Autorização, estorno nominal, log completo PDV |
| Movimento no Caixa (UI) | CAIXA_APRESENTADO API | Tipagem SERVICO/TROCA/SUPRIMENTO |
| Relatório Vendas Produto | VENDA_ITEM API | Layout gerencial vs raw API |

## 4. APIs 200 nunca usadas ou subutilizadas (probe + código)

| API | HTTP | Reg | Uso Logos |
|-----|------|-----|-----------|
| NFCE | 200 | 200 | **Nunca** em services |
| FINANCEIRO_EXCLUSAO | 200 | 10203* | Audit scripts only |
| PRODUTO_META | 200 | 22 | Probe only |
| CONSULTAR_VENDA_FORMA_PAGAMENTO_REDE | 200 | 0 | Chamado, sem dados rede |
| CONSULTAR_CAIXA_APRESENTADO_REDE | 200 | 0 | Chamado, vazio |
| ABASTECIMENTO | 200 | 200 | Fuel legado, não performance |
| TITULO_RECEBER | 200 | 11 | Overview parcial |
| ESTOQUE_PERIODO | 200 | — | Overview parcial |

*FINANCEIRO_EXCLUSAO: validar filtro data antes de BI.

## 5. Palpite confirmado

**Operações PDV (proxy) + Prestação + Venda Forma Pagamento** concentram o maior delta UI↔API. Despesas já está madura (F03.2/F03.3); o tesouro operacional está no **caixa/PDV**, não no financeiro gerencial.
