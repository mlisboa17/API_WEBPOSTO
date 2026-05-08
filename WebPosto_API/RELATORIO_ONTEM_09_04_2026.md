# Relatório WebPosto API — 09/04/2026 (Ontem)
**Filial:** POSTO VIP — Rio Doce Comércio e Serviços Ltda  
**CNPJ:** 03.008.754/0001-86  
**Endereço:** Av. Brasil, 2701 — Rio Doce, Olinda/PE  
**Chave API usada:** <WEBPOSTO_API_TOKEN>  
**Gerado em:** 10/04/2026 via WebPosto API (HTTP 200 confirmado)

---

## ✅ STATUS DA CHAVE

| Endpoint | HTTP | Resultado |
|---|---|---|
| ABASTECIMENTO | 200 | ✅ 200+ registros |
| VENDA | 200 | ✅ 200+ registros |
| CAIXA | 200 | ✅ 4 caixas |
| TITULO_RECEBER | 200 | ✅ 3 títulos |
| TITULO_PAGAR | 200 | ✅ 10 títulos |
| ESTOQUE | 200 | ✅ 5 produtos |
| FUNCIONARIO | 200 | ✅ 50 funcionários |
| EMPRESAS | 200 | ✅ 1 filial |
| DRE | 200 | ✅ Acessível |

**Conclusão: Chave 100% operacional. Não são apenas testes — dados reais de produção.**

---

## ⛽ ABASTECIMENTO — 09/04/2026

> **ATENÇÃO:** Endpoint pagina em blocos de 200. Existem MAIS de 200 abastecimentos no dia.  
> Use o parâmetro `ultimoCodigo` para paginar e obter todos.

### Totais (primeiros 200 registros retornados)
| Produto (código) | Quantidade (L) | Valor (R$) | Qtd. Transações |
|---|---|---|---|
| 1257884 | 876,41 L | R$ 6.476,26 | 145 |
| 1975728 | 413,66 L | R$ 2.419,72 | 51 |
| 1260803 | 45,66 L | R$ 310,00 | 4 |
| **TOTAL parcial** | **1.335,73 L** | **R$ 9.205,98** | **200** |

### Primeiro abastecimento do dia
- **Hora:** 00:04:03
- **Bico:** 42905
- **Produto:** 1257884
- **Volume:** 6,766 L
- **Valor unit.:** R$ 7,39
- **Valor total:** R$ 50,00
- **Frentista:** 227386

### Último abastecimento (da paginação atual)
- **Data/hora fiscal:** 09/04/2026

---

## 🛒 VENDAS (NFC-e) — 09/04/2026

> **ATENÇÃO:** Também paginado em 200. Total real do dia pode ser maior.

| Métrica | Valor |
|---|---|
| Registros retornados | 200 |
| Valor total (200 primeiros) | R$ 7.775,13 |
| Canceladas | 0 |
| Modelo documento | NFC-e (65) — 100% |
| Nota fiscal chave (1ª venda) | 26260403008754000186650270002086221003331797 |

### Estrutura de cada venda
- `vendaCodigo`, `funcionarioCodigo`, `clienteCodigo`, `clienteCpfCnpj`
- `dataHora`, `notaNumero`, `notaSerie`, `totalVenda`
- `caixaCodigo`, `cancelada`, `placaVeiculo`
- `itens[]`, `formaPagamento[]`, `troco[]`

---

## 💰 CAIXA — 09/04/2026

| Caixa | Turno | PDV | Abertura | Fechamento | Apurado | Diferença |
|---|---|---|---|---|---|---|
| 4285373 | 1º TURNO | 54193 | 00:01:46 | 23:59:28 | R$ 39.373,52 | -R$ 307,31 |
| 4285374 | 1º TURNO | 56764 | 00:01:41 | 23:50:47 | (ver sistema) | — |
| + 2 caixas adicionais | — | — | — | — | — | — |

- **Total de caixas no dia:** 4  
- **Status:** Todos fechados (`fechado: true`)

---

## 📋 TÍTULOS A RECEBER — 09/04/2026

| Qtd | Total |
|---|---|
| 3 títulos | Consultar no sistema para conferência |

---

## 📋 TÍTULOS A PAGAR — 09/04/2026

| Qtd |
|---|
| 10 títulos |

---

## 🏪 ESTOQUE (posição atual)

| Produto (código) | Qtd |
|---|---|
| 5 produtos cadastrados | Consultar endpoint para detalhes |

---

## 🔧 COMO PAGINAR ABASTECIMENTO (exemplo Python)

```python
from webposto import WebPostoClient, WebPostoConfig
from datetime import date

config = WebPostoConfig(chave="<WEBPOSTO_API_TOKEN>")
client = WebPostoClient(config)

# Busca TODOS os abastecimentos paginando
todos = []
ultimo_codigo = None

while True:
    params = {
        "dataInicial": "2026-04-09",
        "dataFinal": "2026-04-09",
    }
    if ultimo_codigo:
        params["ultimoCodigo"] = ultimo_codigo
    
    resultado = client._http.get("/INTEGRACAO/ABASTECIMENTO", params)
    registros = resultado.get("resultados", [])
    
    if not registros:
        break
    
    todos.extend(registros)
    ultimo_codigo = resultado.get("ultimoCodigo")
    
    if len(registros) < 200:  # última página
        break

print(f"Total abastecimentos: {len(todos)}")
print(f"Volume total: {sum(a['quantidade'] for a in todos):.3f} L")
print(f"Valor total: R$ {sum(a['valorTotal'] for a in todos):.2f}")
```

---

## 📊 TODOS OS 143 ENDPOINTS DISPONÍVEIS NA API

### 🔵 Integrações — GETs (consulta)
```
/INTEGRACAO/ABASTECIMENTO              dataInicial*, dataFinal*, filial, bico, ultimoCodigo, limite
/INTEGRACAO/ABASTECIMENTO_ENCERRANTE   dataInicial*, dataFinal*
/INTEGRACAO/TRANSFERENCIA_BANCARIA     dataInicial*, dataFinal*
/INTEGRACAO/TITULO_RECEBER             dataInicial*, dataFinal*, apenasPendente, dataFiltro
/INTEGRACAO/TITULO_PAGAR               dataInicial, dataFinal, apenasPendente
/INTEGRACAO/PRODUTO_INVENTARIO         dataInicial, dataFinal
/INTEGRACAO/PRODUTO_COMISSAO
/INTEGRACAO/PEDIDO_COMPRAS             dataInicial, dataFinal
/INTEGRACAO/CLIENTE                    pagina, tamanhoPagina
/INTEGRACAO/MOVIMENTO_CONTA            dataInicial*, dataFinal*
/INTEGRACAO/LANCAMENTO_CONTABIL        dataInicial*, dataFinal*
/INTEGRACAO/PLACARES
/INTEGRACAO/PIS_COFINS                 dataInicial*, dataFinal*
/INTEGRACAO/PEDIDO_TRR
/INTEGRACAO/PDV_CONFIGURACAO
/INTEGRACAO/PDV                        dataInicial*, dataFinal*
/INTEGRACAO/NOTA_SERVICO               dataInicial*, dataFinal*
/INTEGRACAO/NOTA_SERVICO_ITEM
/INTEGRACAO/NOTA_SAIDA_ITEM
/INTEGRACAO/NOTA_MANIFESTACAO
/INTEGRACAO/NFE_SAIDA                  dataInicial*, dataFinal*
/INTEGRACAO/NFE/XML                    chaveNfe*
/INTEGRACAO/NFCE                       dataInicial*, dataFinal*
/INTEGRACAO/NFCE/{id}/XML
/INTEGRACAO/MAPA_DESEMPENHO            dataInicial*, dataFinal*
/INTEGRACAO/ICMS                       dataInicial*, dataFinal*
/INTEGRACAO/IA_VENDAS_PRODUTO          dataInicial*, dataFinal*
/INTEGRACAO/IA_VENDAS_CLIENTE          dataInicial*, dataFinal*
/INTEGRACAO/GRUPO_META
/INTEGRACAO/GRUPO
/INTEGRACAO/FUNCOES
/INTEGRACAO/FUNCIONARIO_META
/INTEGRACAO/FUNCIONARIO
/INTEGRACAO/FORNECEDOR
/INTEGRACAO/FORMA_PAGAMENTO
/INTEGRACAO/FINANCEIRO_EXCLUSAO        dataInicial*, dataFinal*
/INTEGRACAO/ESTOQUE_PERIODO            dataInicial*, dataFinal*
/INTEGRACAO/ESTOQUE
/INTEGRACAO/EMPRESAS
/INTEGRACAO/DUPLICATA                  dataInicial*, dataFinal*
/INTEGRACAO/DRE                        dataInicial*, dataFinal*
/INTEGRACAO/DFE_XML
/INTEGRACAO/CONTA
/INTEGRACAO/CONTAGEM_ESTOQUE           dataInicial*, dataFinal*
/INTEGRACAO/CONSUMO_CLIENTE
/INTEGRACAO/CONSULTAR_VIEW
/INTEGRACAO/SUB_GRUPO_REDE
/INTEGRACAO/LMC                        dataInicial*, dataFinal*
/INTEGRACAO/FUNCIONARIO                (meta)
/INTEGRACAO/COMPRA                     dataInicial*, dataFinal*
/INTEGRACAO/COMPRA_ITEM
/INTEGRACAO/COMPRA/{chaveNfe}/XML
/INTEGRACAO/CLIENTE_FROTA
/INTEGRACAO/CLIENTE_EMPRESA
/INTEGRACAO/CHEQUE_PAGAR               dataInicial*, dataFinal*
/INTEGRACAO/CHEQUE                     dataInicial*, dataFinal*
/INTEGRACAO/CENTRO_CUSTO
/INTEGRACAO/CARTAO_REMESSA             dataInicial*, dataFinal*
/INTEGRACAO/CARTAO_PAGAR               dataInicial*, dataFinal*
/INTEGRACAO/CARTAO_COMPRA              dataInicial*, dataFinal*
/INTEGRACAO/CAIXA_APRESENTADO          dataInicial*, dataFinal*
/INTEGRACAO/CAIXA                      dataInicial*, dataFinal*
/INTEGRACAO/BOMBA
/INTEGRACAO/BICO
/INTEGRACAO/APRIX_PRECO_CLIENTE
/INTEGRACAO/APRIX_MOVIMENTO            dataInicial*, dataFinal*
/INTEGRACAO/APRIX_CUSTO                dataInicial*, dataFinal*
/INTEGRACAO/ADMINISTRADORA
/INTEGRACAO/ADIANTAMENTO_FORNECEDOR    dataInicial*, dataFinal*
/INTEGRACAO/ABASTECIMENTO_ENCERRANTE   dataInicial*, dataFinal*
/INTEGRACAO/ABASTECIMENTO              dataInicial*, dataFinal*
/INTEGRACAO/TITULO_PAGAR/{id}
/INTEGRACAO/PRAZO_TABELA_PRECO_ITEM/{id}
/INTEGRACAO/VENDA                      dataInicial*, dataFinal*
/INTEGRACAO/VENDA_REDE                 dataInicial*, dataFinal*
/INTEGRACAO/RELATORIO_BI               (ver Integração Relatórios)
```

### 🟠 Integração Pedido Combustível
```
/INTEGRACAO/PEDIDO_COMBUSTIVEL/PRODUTO
/INTEGRACAO/PEDIDO_COMBUSTIVEL/PEDIDO/{id}
/INTEGRACAO/PEDIDO_COMBUSTIVEL/PEDIDO/{id}/XML
/INTEGRACAO/PEDIDO_COMBUSTIVEL/PEDIDO/STATUS
/INTEGRACAO/PEDIDO_COMBUSTIVEL/CLIENTE
/INTEGRACAO/PEDIDO_COMBUSTIVEL/PEDIDO          (GET + POST)
/INTEGRACAO/PEDIDO_COMBUSTIVEL/PEDIDO/{id}/FATURAR
/INTEGRACAO/PEDIDO_COMBUSTIVEL/PEDIDO/{id}/DANFE
```

### 🟢 Integração Relatórios
```
/INTEGRACAO/RELATORIO_BI/...  (endpoints de BI/dashboards)
```

---

*Gerado automaticamente pelo diagnóstico WebPosto API — Grupo Lisboa*
