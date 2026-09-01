from src.services.financial_expense_taxonomy_service import FinancialExpenseTaxonomyService


def test_fuel_freight_is_fuel_cmv() -> None:
    result = FinancialExpenseTaxonomyService().suggest({"planoConta": "Frete combustível julho"})
    assert result.accounting_nature == "CMV"
    assert result.suggested_department == "combustiveis"


def test_lubricants_remain_an_independent_department() -> None:
    result = FinancialExpenseTaxonomyService().suggest({"descricao": "Compra óleo motor para revenda"})
    assert result.category == "LUBRIFICANTES - CMV"
    assert result.suggested_department == "lubrificantes"


def test_unknown_expense_stays_out_of_dre_until_review() -> None:
    result = FinancialExpenseTaxonomyService().suggest({"planoConta": "pagamento sem detalhe"})
    assert result.category == "AGUARDANDO CLASSIFICACAO"
    assert result.accounting_nature == "NAO_DEFINIDA"
    assert result.requires_review is True
