# OPERATIONAL JOIN KEY MATRIX — D01 · Agente 6

Janela: **7d**

| Fonte A | Fonte B | Chave | Cobertura % | Confiança |
|---|---|---|---|---|
| VENDA_FORMA_PAGAMENTO | VENDA | empresaCodigo, vendaCodigo | 100.0% | HIGH |
| VENDA | CAIXA | empresaCodigo, caixaCodigo | 100.0% | HIGH |
| VENDA_ITEM | VENDA | empresaCodigo, vendaCodigo | 100.0% | HIGH |
| ABASTECIMENTO | VENDA_ITEM | empresaCodigo, vendaItemCodigo | 42.0% | LOW |
| NFCE | VENDA | empresaCodigo, vendaCodigo | 100.0% | HIGH |
| VFP | CAIXA | via VENDA.caixaCodigo | 100.0% | MEDIUM |
