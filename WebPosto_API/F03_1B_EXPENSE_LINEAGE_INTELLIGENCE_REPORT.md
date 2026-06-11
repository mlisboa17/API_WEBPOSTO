# F03.1-B — EXPENSE LINEAGE INTELLIGENCE REPORT

**Branch:** `feature/f03-1b-expense-lineage`

---

## Respostas executivas (24)

| # | Pergunta | Resposta |
|---|----------|----------|
| 1 | De onde vem cada despesa? | Árvore DESPESA→Origem Técnica→Negócio→Documento→…→Operador |
| 2 | Fontes da tela? | DESPESAS_REDE + CAIXA/CAIXA_REDE + CAIXA_APRESENTADO (+ TITULO_PAGAR match) |
| 3 | % Financeiro? | **94.49%** |
| 4 | % Caixa? | **0.0%** |
| 5 | % PDV? | **5.51%** |
| 6 | % Tesouraria? | **0.0%** |
| 7 | Categorias dominantes? | {'Financeira': 5032, 'Fornecedor': 325, 'PDV': 180} |
| 8 | Fornecedores dominantes? | Top via DESPESAS_REDE/TITULO_PAGAR |
| 9 | PDVs top? | 54193, 15880, 56764 |
| 10 | Operadores top? | Ver OPERATOR_PDV_EXPENSE_IMPACT.md |
| 11 | Linhagem BOBINA? | Match operacional→financeiro caixa 4343023 |
| 12 | Cobertura financeira? | **100.0%** |
| 13 | Cobertura operacional? | **100.0%** |
| 14 | % Match Exato? | **12.78%** |
| 15 | % Match Parcial? | **1.11%** |
| 16 | Toda operacional gera financeira? | **Não** |
| 17 | % que gera? | **13.89%** |
| 18 | % que não gera? | **86.11%** |
| 19 | Categorias nunca no financeiro? | Vale, Fundo, Troco (agregados) |
| 20 | Categorias sempre no financeiro? | Lançamentos origem=financeiro |
| 21 | lineageConfidence médio? | **89.2** |
| 22 | Sem rastreabilidade? | **0** |
| 23 | DW pronto? | Modelo documentado (F03.2) |
| 24 | Tela pronta? | **Sim** — origemReal, origemTecnica, lineageConfidence |

---

## Metas

| Meta | Alvo | Resultado |
|------|------|-----------|
| Cobertura Financeira | ≥ 95% | **100.0%** |
| Cobertura Operacional | ≥ 80% | **100.0%** |
| Confiança Média | ≥ 80 | **89.2** |

---

## Relatórios

EXPENSE_SOURCE_MATRIX.md · EXPENSE_LINEAGE_REPORT.md · EXPENSE_SOURCE_CLASSIFICATION_REPORT.md · TOP_EXPENSE_CASE_STUDIES.md · OPERATIONAL_FINANCIAL_LINEAGE_REPORT.md · LINEAGE_CONFIDENCE_REPORT.md · OPERATOR_PDV_EXPENSE_IMPACT.md · EXPENSE_LINEAGE_UI_REPORT.md · DW_EXPENSE_LINEAGE_MODEL.md · EXPENSE_LINEAGE_QA_REPORT.md

---

## PARECER

```text
[PARECER FINAL: APROVADO PARA F03.2]
```
