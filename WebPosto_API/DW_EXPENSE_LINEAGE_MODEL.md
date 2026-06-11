# DW EXPENSE LINEAGE MODEL — F03.1-B · Agente 8

## Fact: fact_expense_lineage

Grain: 1 linha tela pós-dedup P0.1-B.

Campos-chave: valor, operational_financial_match, lineage_confidence, lineage_path_json, rastreabilidade_ok.

## Dimensions

- dim_expense_source (origem_tecnica, origem_negocio)
- dim_expense_category (classificacao_lineage, evento_operacional)
- dim_supplier
- dim_account (plano_conta)
- dim_cost_center
- dim_operator
- dim_pdv

## ETL

Fonte: snapshot `expense:lineage:*` + JSON audit. Status: **documentado — implementação F03.2**.
