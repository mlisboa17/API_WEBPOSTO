# PAYMENT FORM DISCOVERY — D01 · Agente 1

Janela ref: **7d** · {'inicio': '2026-06-02', 'fim': '2026-06-08'}

## Campos mapeados (200 registros)

administradoraCodigo, codigo, dataMovimento, empresaCodigo, formaPagamentoCodigo, nomeFormaPagamento, taxaPercentual, tipoFormaPagamento, turnoCodigo, valorPagamento, vencimento, vendaCodigo, vendaPrazoCodigo

## Respostas

| # | Pergunta | Resposta | Cobertura |
|---|---|---|---|
| 1 | Existe caixaCodigo? | **Sim** | 100.0% |
| 2 | Existe turnoCodigo? | **Sim** | 100.0% |
| 3 | Existe vendaCodigo? | **Sim** | 100.0% |
| 4 | Existe funcionarioCodigo? | **Sim** | 100.0% |
| 5 | Existe pdvCodigo? | **Sim** | 100.0% |
| 6 | Forma pagamento detalhada? | **Sim** | 100.0% |
| 7 | Existe administradora? | **Sim** | 38.0% |

**Nota:** `caixaCodigo`, `funcionarioCodigo`, `pdvCodigo` **não estão no payload VFP** — obtidos via join **VFP → VENDA → CAIXA** (cobertura bridge: **100.0%**).
