# F04 SOURCE ARCHITECTURE DECISION — D01 · Agente 10

## Respostas

| # | Pergunta | Decisão |
|---|----------|---------|
| 1 | API reconstrói Prestação? | **Parcial (87.5%)** — transacional sim, nominal não |
| 2 | Campos exigem PDF/UI? | **funcionarioNome, produtividade oficial, participação UI, fundoCaixa, meta** |
| 3 | Módulos API estruturada? | Vendas, forma pagamento, abastecimento, cancelamentos, mix PDV |
| 4 | Módulos precisam Prestação? | Accountability nominal, produtividade oficial, layout turno |
| 5 | Fontes primárias F04 | **VENDA, VENDA_ITEM, VENDA_FORMA_PAGAMENTO, CAIXA, ABASTECIMENTO** |
| 6 | Fontes auxiliares F04 | NFCE, MOVIMENTO_CONTA, CAIXA_APRESENTADO, DESPESAS_REDE |

## Modelo híbrido F04

```text
TRANSACIONAL (API)     → VENDA + VFP + VENDA_ITEM + ABASTECIMENTO + CAIXA
ACCOUNTABILITY NOMINAL → Prestação PDF/UI ou parser
FINANCEIRO             → DESPESAS + TITULO (mantém)
AUDITORIA              → NFCE + FINANCEIRO_EXCLUSAO
```

Join proof: ****Sim****
