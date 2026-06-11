# D01 — LIVE OPERATIONAL JOIN PROBE

## Respostas executivas (1–20)

| # | Chave | Resposta |
|---|---|---|
| 1 | 1_vfp_vendaCodigo | **Sim** |
| 2 | 2_vfp_caixaCodigo | **Sim** |
| 3 | 3_vfp_turnoCodigo | **Sim** |
| 4 | 4_venda_funcionarioCodigo | **Sim** |
| 5 | 5_venda_pdvCodigo | **Sim** |
| 6 | 6_vendaItem_funcionarioCodigo | **Sim** |
| 7 | 7_abast_codigoFrentista | **Sim** |
| 8 | 8_abast_liga_venda | **Sim** |
| 9 | 9_nfce_liga_venda | **Sim** |
| 10 | 10_recon_forma_pagamento | **Sim** |
| 11 | 11_recon_venda_funcionario | **Sim** |
| 12 | 12_recon_produtividade | **Sim** |
| 13 | 13_recon_combustivel_produto | **Sim** |
| 14 | 14_recon_troco_cancel | **Sim** |
| 15 | 15_pdf_necessario | **Sim** |
| 16 | 16_campos_exclusivos_prestacao | ['funcionarioNome', 'participacaoIndividual (oficial UI)', 'produtividadeFuncionario', 'fundoCaixa', 'layout nominal turno'] |
| 17 | 17_fontes_primarias_f04 | ['VENDA', 'VENDA_ITEM', 'VENDA_FORMA_PAGAMENTO', 'CAIXA', 'ABASTECIMENTO'] |
| 18 | 18_fontes_auxiliares_f04 | ['NFCE', 'MOVIMENTO_CONTA', 'CAIXA_APRESENTADO', 'DESPESAS_REDE'] |
| 19 | 19_cobertura_reconstrucao_pct | 87.5 |
| 20 | 20_f04_api_ou_parser | API estruturada para transacional; parser/UI para nominal |

## Join matrix (resumo)

| A | B | Cobertura | Confiança |
|---|---|---|---|
| VENDA_FORMA_PAGAMENTO | VENDA | 100.0% | HIGH |
| VENDA | CAIXA | 100.0% | HIGH |
| VENDA_ITEM | VENDA | 100.0% | HIGH |
| ABASTECIMENTO | VENDA_ITEM | 42.0% | LOW |
| NFCE | VENDA | 100.0% | HIGH |

## Critérios aceite

| Critério | Status |
|----------|--------|
| Matriz de chaves | **Sim** |
| Cobertura reconstrução medida | **Sim** — **87.5%** |
| Join VENDA/CAIXA/VFP comprovado | **Sim** |
| Limitações documentadas | Sim |

## Entregáveis

- PAYMENT_FORM_DISCOVERY_REPORT.md
- SALE_DISCOVERY_REPORT.md
- SALE_ITEM_DISCOVERY_REPORT.md
- FUELING_DISCOVERY_REPORT.md
- NFCE_DISCOVERY_REPORT.md
- OPERATIONAL_JOIN_KEY_MATRIX.md
- PRESTACAO_RECONSTRUCTION_PROBE.md
- OPERATOR_PRODUCTIVITY_PROBE.md
- OPERATIONAL_PROBE_PERFORMANCE_REPORT.md
- F04_SOURCE_ARCHITECTURE_DECISION.md

[PARECER FINAL: PRESTACAO CONTAS/PARSER NECESSÁRIO PARA F04]
