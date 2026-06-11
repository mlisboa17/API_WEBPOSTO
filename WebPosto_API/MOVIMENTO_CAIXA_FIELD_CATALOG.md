# MOVIMENTO NO CAIXA — FIELD CATALOG — Sprint D00

Módulo UI WebPosto: *"Controla serviços, suprimentos, despesas e trocas movimentados no caixa"*

**Descoberta crítica:** não existe `/INTEGRACAO/MOVIMENTO_CAIXA`. O conceito está **fragmentado** em múltiplos endpoints.

## Tipos UI vs API

| Tipo UI | Descrição | Endpoint proxy | API | Observação |
|---|---|---|---|---|
| SERVICO | Serviços movimentados no caixa | — | none | Possível proxy: VENDA (não combustível) — não tipado |
| SUPRIMENTO | Reforço de caixa | MOVIMENTO_CONTA | partial | Crédito em conta caixa; sem campo tipo explícito |
| DESPESA | Despesa lançada no caixa | CAIXA_APRESENTADO + DESPESAS_REDE | yes | F03.1 mapeado |
| TROCA | Troca / devolução física | — | none | Sem endpoint; troco apenas em VENDA.troco |
| NOTA | Nota a prazo no caixa | CAIXA_APRESENTADO.notaPrazo* | yes | Bloco 3 — crédito interno |
| EMPRESTIMO | Empréstimo funcionário | CAIXA_APRESENTADO.emprestimo* | yes | F03.4-B |
| CARTA_FRETE | Carta frete | CAIXA_APRESENTADO.cartaFrete* | yes | Nunca modelado no Logos |

## Campos reais — CAIXA_APRESENTADO (probe 21 reg)

`empresaCodigo, caixaCodigo, dinheiroApresentado, dinheiroApurado, dinheiroDiferenca, notaPrazoApresentado, notaPrazoApurado, notaPrazoDiferenca, chequeApresentado, chequeApurado, chequeDiferenca, chequePreApresentado, chequePreApurado, chequePreDiferenca, cartaoApresentado…` (+ `despesaApurado`, `despesaDiferenca`, `valeFunApresentado` em produção F03.1)

## Campos reais — MOVIMENTO_CONTA (probe 200 reg)

`empresaCodigo, movimentoContaCodigo, valor, dataMovimento, descricao, tipoDocumentoOrigem, codigoTipoDocumentoOrigem, documentoOrigemCodigo, tipo, conciliado, evento, saldo, contaCodigo, planoContaGerencialCodigo, centroCustoCodigo, documento, lote, daraHoraConciliacao, usuarioConciliacao, codigoPessoa, tipoPessoa, codigo`

## Campos reais — CAIXA turno

`empresaCodigo, caixaCodigo, dataMovimento, turnoCodigo, turno, pdvCodigo, funcionarioCodigo, abertura, fechamento, apurado, diferenca, fechado, consolidado`

## Gap LOGOS

| Tipo nunca modelado | Evidência API | Impacto |
|---------------------|---------------|---------|
| CARTA_FRETE | `cartaFreteApresentado/Apurado/Diferenca` | Recebíveis operacionais ocultos |
| SERVIÇO | Sem tipo | Perda de classificação movimento |
| TROCA | Apenas `VENDA.troco` | Confunde troco com troca de turno |
| SUPRIMENTO/SANGRIA tipados | Sem campos | Inferência semântica frágil |
