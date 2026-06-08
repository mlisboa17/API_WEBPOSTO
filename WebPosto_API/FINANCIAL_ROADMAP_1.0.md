# FINANCIAL_ROADMAP_1.0

| Fase | Módulo | Fonte | Status | Sprint |
|---|---|---|---|---|
| F01 | Centro Financeiro | DESPESAS+TITULO_PAGAR+RECEBER+MOV | Especificado | A03.7 → A04 prep |
| F02 | Tesouraria | MOVIMENTO_CONTA | Blueprint | Pós F01 |
| F03 | Operação Caixa | CAIXA+APRESENTADO | Modelo | Pós F01 |
| F04 | Compras | NOTA_ENTRADA | Aguarda token | Quality |
| F05 | Recebíveis | TITULO_RECEBER | 11 reg API | Pós F01 |
| F06 | Fluxo Caixa | TITULO_* + MOVIMENTO | Projetado | F01+F02 |
| F07 | Conciliação Bancária | MOVIMENTO_CONTA | Projetado | F02 |
| F08 | DRE Gerencial | facts separados | Projetado | F01 consolidado |

**Sequência recomendada:** F01 → F05 → F02 → F03 → F06 → F07 → F08 → F04
