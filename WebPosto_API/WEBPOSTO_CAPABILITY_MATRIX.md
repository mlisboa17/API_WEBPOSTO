# WEBPOSTO CAPABILITY MATRIX — Sprint D00

**Data:** 2026-06-09 · **Fonte:** `webposto_network_probe_result.json` + gateway oficial · **Período probe:** 2026-06-01 → 2026-06-07

## Resumo

| Camada | Endpoints gateway | Probe adicional | HTTP 200 c/ dados | HTTP 401 |
|--------|-------------------|-----------------|-------------------|----------|
| Oficial LOGOS | 28 | +35 scripts | ~18 | ~12 |
| Módulos UI sem API | Prestação, Movimento Caixa, Operações PDV | — | 0 endpoint dedicado | — |

## Matriz gateway + probe

| Path | Chave LOGOS | HTTP | Registros | Classificação | Uso produtivo |
|---|---|---|---|---|---|
| /INTEGRACAO/ABASTECIMENTO | abastecimento | 200 | 200 | USAR_AGORA | Sim |
| /INTEGRACAO/CAIXA | caixa | 200 | 21 | USAR_AGORA | Sim |
| /INTEGRACAO/CAIXA_APRESENTADO | caixa_apresentado | 200 | 21 | USAR_AGORA | Sim |
| /INTEGRACAO/CONSULTAR_ANALISE_VENDAS_COMBUSTIVEL | analise_vendas_combustivel | 200 | 0 | APENAS_DIAGNOSTICO | Parcial/Não |
| /INTEGRACAO/CONSULTAR_CAIXA_APRESENTADO_REDE | caixa_apresentado_rede | — | — | — | Parcial/Não |
| /INTEGRACAO/CONSULTAR_CAIXA_REDE | caixa_rede | — | — | — | Sim |
| /INTEGRACAO/CONSULTAR_DESPESAS_FINANCEIRO_REDE | despesas_financeiro_rede | 200 | 427 | USAR_AGORA | Sim |
| /INTEGRACAO/CONSULTAR_LMC_REDE | lmc_rede | 200 | 28 | USAR_AGORA | Sim |
| /INTEGRACAO/CONSULTAR_VENDA_FORMA_PAGAMENTO_REDE | venda_forma_pagamento_rede | 200 | 0 | APENAS_DIAGNOSTICO | Parcial/Não |
| /INTEGRACAO/CONSULTAR_VENDA_ITEM_REDE | venda_item_rede | 401 | 0 | NAO_USAR | Parcial/Não |
| /INTEGRACAO/CONTA | conta | 200 | 17 | USAR_AGORA | Parcial/Não |
| /INTEGRACAO/EMPRESAS | empresas | 200 | 2 | USAR_AGORA | Parcial/Não |
| /INTEGRACAO/ESTOQUE_PERIODO | estoque_periodo | 200 | 200 | USAR_COM_CUIDADO | Parcial/Não |
| /INTEGRACAO/MOVIMENTO_CONTA | movimento_conta | 200 | 200 | USAR_AGORA | Sim |
| /INTEGRACAO/NFCE | nfce | 200 | 200 | USAR_AGORA | Parcial/Não |
| /INTEGRACAO/PRODUTO | produto | 200 | 200 | USAR_COM_CUIDADO | Parcial/Não |
| /INTEGRACAO/PRODUTO_COMBUSTIVEL | produto_combustivel | 401 | 0 | NAO_USAR | Parcial/Não |
| /INTEGRACAO/PRODUTO_EMPRESA | produto_empresa | 200 | 200 | USAR_AGORA | Parcial/Não |
| /INTEGRACAO/PRODUTO_EMPRESA_REDE | produto_empresa_rede | 401 | 0 | NAO_USAR | Parcial/Não |
| /INTEGRACAO/PRODUTO_ESTOQUE | produto_estoque | 400 | 0 | APENAS_DIAGNOSTICO | Parcial/Não |
| /INTEGRACAO/PRODUTO_REDE | produto_rede | 401 | 0 | NAO_USAR | Parcial/Não |
| /INTEGRACAO/TANQUE | tanque | 200 | 6 | USAR_AGORA | Parcial/Não |
| /INTEGRACAO/TITULO_PAGAR | financeiro | 200 | 66 | USAR_AGORA | Sim |
| /INTEGRACAO/TITULO_RECEBER | titulo_receber | 200 | 11 | USAR_COM_CUIDADO | Sim |
| /INTEGRACAO/TRANSFERENCIA_BANCARIA | transferencia_bancaria | 200 | 200 | USAR_COM_CUIDADO | Parcial/Não |
| /INTEGRACAO/VENDA | venda | 200 | 200 | USAR_AGORA | Sim |
| /INTEGRACAO/VENDA_FORMA_PAGAMENTO | venda_forma_pagamento | 200 | 200 | USAR_AGORA | Sim |
| /INTEGRACAO/VENDA_ITEM | venda_item | 200 | 200 | USAR_AGORA | Sim |
| /INTEGRACAO/FUNCIONARIO_REDE | — | 401 | 0 | NAO_USAR | Probe only |
| /INTEGRACAO/CONSULTAR_VENDA_ITEM_REDE | — | 401 | 0 | NAO_USAR | Probe only |
| /INTEGRACAO/CONSULTAR_LMC_REDE_BICO | — | 401 | 0 | NAO_USAR | Probe only |
| /INTEGRACAO/DRE | — | 200 | 0 | APENAS_DIAGNOSTICO | Probe only |

## Módulos WebPosto UI vs endpoint

| Módulo UI (documentação WebPosto) | Endpoint `/INTEGRACAO/*` | Status |
|-----------------------------------|--------------------------|--------|
| Prestação de Contas | **Inexistente** | Camada documento/PDF — inferência via CAIXA+DESPESAS |
| Movimento no Caixa | **Inexistente** | Decomposto em CAIXA_APRESENTADO + MOVIMENTO_CONTA |
| Nota no Caixa | **Inexistente** | Parcial: `notaPrazo*` em CAIXA_APRESENTADO |
| Operações PDV | **Inexistente** | Proxy: VENDA, VENDA_ITEM, ABASTECIMENTO, CAIXA, NFCE |
| Venda Forma Pagamento | `VENDA_FORMA_PAGAMENTO` | **200** — subexplorado no Logos |
| LMC | `CONSULTAR_LMC_REDE` | **200** — 2 filiais; extensões 401 |
