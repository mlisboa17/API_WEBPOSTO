# EXPENSE LINEAGE QA — F03.1-B · Agente 9

## Caso BOBINA · AP CASA CAIADA · 08/06/2026

| # | Validação | Resultado |
|---|-----------|-----------|
| 1 | Origem real | Financeiro |
| 2 | Fornecedor | — |
| 3 | Plano | BOBINA TERMICA |
| 4 | Centro custo | — |
| 5 | Documento | None |
| 6 | Categoria | Material Operacional |
| 7 | Linhagem | DESPESA → Origem Técnica:DESPESAS_REDE → Origem Negócio:Financeiro → Evento:Material Operacional → Documento:? → Fornecedor:? → Plano:BOBINA TERMICA → Centro:? → PDV:? → Turno:? → Operador:? |

## Paridade

| Camada | Δ valor |
|--------|--------:|
| Tela = API | **0.0** |

## Critérios

| Critério | Status |
|----------|--------|
| Paridade = 0,00 | OK |
| Confiança média ≥ 80 | OK (89.2) |
| Cobertura documentada | OK (100.0%) |
| Sem rastreio | 0 |
