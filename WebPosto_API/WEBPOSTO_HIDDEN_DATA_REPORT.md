# WEBPOSTO HIDDEN DATA REPORT — Sprint D00

## Perguntas obrigatórias (1–20)


| # | Pergunta | Resposta |
|---|----------|----------|
| 1 | Relatórios com mais campos que APIs? | **Prestação de Contas**, **Operações PDV (UI)**, **Movimento no Caixa (UI)** |
| 2 | Campos UI sem API? | **funcionarioNome, participacaoIndividual, produtividadeFuncionario, fundoCaixa, metaFuncionario, autorizacaoPDV** |
| 3 | APIs 200 nunca usadas? | **NFCE**, **PRODUTO_META**, **FINANCEIRO_EXCLUSAO** (prod), **CONSULTAR_LMC_REDE_BICO/TANQUE** (401) |
| 4 | APIs com dados de operador? | CAIXA, VENDA, VENDA_ITEM, ABASTECIMENTO.codigoFrentista |
| 5 | APIs com dados de PDV? | CAIXA.pdvCodigo (+ join VENDA→caixa) |
| 6 | APIs com produtividade? | **Nenhuma dedicada** — proxy ABASTECIMENTO + VENDA_ITEM |
| 7 | APIs com sangria? | **Nenhuma tipada** — DESPESAS_REDE semântico |
| 8 | APIs com suprimento? | **Nenhuma tipada** — MOVIMENTO_CONTA inferido |
| 9 | APIs com vale? | CAIXA_APRESENTADO.valeFun*/valeCliente* + DESPESAS |
| 10 | APIs com desconto funcionário? | VENDA_ITEM.totalDesconto (sem consolidação operador) |
| 11 | APIs com troco? | **VENDA.troco** |
| 12 | APIs com nota a prazo? | CAIXA_APRESENTADO.notaPrazo* + TITULO_RECEBER |
| 13 | APIs com empréstimo? | CAIXA_APRESENTADO.emprestimo* |
| 14 | APIs com carta frete? | CAIXA_APRESENTADO.cartaFrete* |
| 15 | APIs auditoria operacional? | NFCE, FINANCEIRO_EXCLUSAO, VENDA.cancelada |
| 16 | Prestação não usada? | Nome, participação %, produtividade, fundo caixa, layout nominal turno |
| 17 | Operações PDV não usadas? | Cancelamentos, autorizações, estornos PDV, abastecimento→performance |
| 18 | LMC não usado? | lmcBico, lmcTanque, perdaSobra vs caixa, encerrante |
| 19 | Top 20 campos ocultos? | Ver tabela abaixo |
| 20 | Módulo Logos mais valor? | **Operator Performance + Cash Accountability (F04)** consumindo Prestação + VENDA_FP + VENDA |


## Top 20 campos ocultos mais valiosos

| # | Campo/Conceito | Fonte | Valor F04 | Prioridade |
|---|---|---|---|---|
| 1 | funcionarioNome | Prestação de Contas | Accountability nominal | P0 |
| 2 | participacaoIndividual | Prestação de Contas | Performance justa por turno | P0 |
| 3 | produtividadeFuncionario | Prestação de Contas | Score operacional F04 | P0 |
| 4 | VENDA.funcionarioCodigo + cancelada | Operações PDV (proxy VENDA) | Auditoria cancelamentos por operador | P0 |
| 5 | VENDA_FORMA_PAGAMENTO por turno/PDV | Venda Forma Pagamento | Mix pagamento operacional | P0 |
| 6 | ABASTECIMENTO.codigoFrentista | Operações PDV (proxy) | Produtividade bomba | P1 |
| 7 | CAIXA_APRESENTADO.cartaFrete* | Movimento Caixa / Nota | Recebíveis carta frete | P1 |
| 8 | CAIXA_APRESENTADO.notaPrazo* | Nota no Caixa | Crédito cliente / prazo | P1 |
| 9 | LMC.perdaSobra + lmcBico | LMC | Quebra física vs caixa | P1 |
| 10 | VENDA_ITEM.funcionarioCodigo | Operações PDV | Vendas por operador (item) | P1 |
| 11 | NFCE.situacao + vendaCodigo | Operações PDV | Rastreio fiscal cancelamento | P2 |
| 12 | fundoCaixa | Prestação de Contas | Abertura turno / accountability | P2 |
| 13 | metaFuncionario | Prestação / GRUPO_META | Meta vs realizado | P2 |
| 14 | MOVIMENTO_CONTA suprimento | Movimento Caixa | Fluxo físico caixa | P2 |
| 15 | TITULO_RECEBER + vendaCodigo | Nota no Caixa | Conta cliente / recebimento | P2 |
| 16 | VENDA.troco | Operações PDV | Perdas operacionais troco | P2 |
| 17 | FINANCEIRO_EXCLUSAO | Auditoria | Estornos / exclusões | P3 |
| 18 | CONSULTAR_LMC_REDE_BICO (401) | LMC granular | Encerrante por bico | P3 — pedir token |
| 19 | VALE_FUNCIONARIO_REDE (401) | Vale | Vale nominal direto | P3 — pedir token |
| 20 | FUNCIONARIO_REDE (401) | Cadastro | Nome operador em API | P3 — pedir token |

## APIs por dimensão operacional

### Operador
| Endpoint | Campos |
|---|---|
| CAIXA / CAIXA_REDE | funcionarioCodigo, pdvCodigo, turno, diferenca |
| VENDA | funcionarioCodigo, cancelada, troco, caixaCodigo |
| VENDA_ITEM | funcionarioCodigo, totalDesconto |
| ABASTECIMENTO | codigoFrentista, encerrante, codigoBico |
| VENDA_FORMA_PAGAMENTO | turnoCodigo, formaPagamentoCodigo, nomeFormaPagamento |

### PDV
| Endpoint | Campos |
|---|---|
| CAIXA | pdvCodigo, turnoCodigo |
| VENDA | caixaCodigo → join PDV |
| ABASTECIMENTO | empresaCodigo (sem pdv direto) |

## Conclusão executiva

1. **Não existe API de Prestação** — o documento é a fonte nominal; a API decompõe em CAIXA/DESPESAS/VENDA.
2. **Movimento no Caixa e Operações PDV são módulos UI** — dados existem, mas **fragmentados** em 6+ endpoints.
3. **VENDA_FORMA_PAGAMENTO** responde 200 com `turnoCodigo` — **nunca cruzado** com operador/PDV no Logos.
4. **LMC** abre quebra física (`perdaSobra`, `lmcBico`) — **desconectado** de accountability caixa.
5. **Módulo F04 com maior ROI:** Performance + Accountability alimentados por **Prestação (nominal) + VENDA/VENDA_FP (transacional) + CAIXA (turno)**.

## Próximo passo recomendado (D01 — fora deste escopo)

- Solicitar à Quality: `FUNCIONARIO_REDE`, `VALE_FUNCIONARIO_REDE`, `CONSULTAR_VENDA_ITEM_REDE`, `CONSULTAR_LMC_REDE_BICO` no token.
- Probe live `VENDA_FORMA_PAGAMENTO` × `CAIXA` × `funcionarioCodigo` janela 90d.
- OCR/parser Prestação PDF se API nominal continuar bloqueada.
