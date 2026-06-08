from src.services.data_quality_service import DataQualityService


def _evaluate(expenses=None, sales=None, items=None, accounts=None, mapped_codes=None):
    return DataQualityService.evaluate_records(
        expenses_rows=expenses or [],
        sales_rows=sales or [],
        sale_item_rows=items or [],
        accounts_rows=accounts or [],
        mapped_company_codes=mapped_codes or {5256},
        mapped_filiais_by_company={5256: "POSTO BR SHOPPING"},
        mapped_product_codes={1001},
        data_inicial="2026-06-01",
        data_final="2026-06-30",
    )


def test_score_100_when_no_records():
    result = _evaluate()
    assert result["score"] == 100.0
    assert result["status"] == "ok"
    assert result["summary"]["totalRegistros"] == 0


def test_score_with_valid_and_invalid_records():
    expenses = [
        {
            "empresaCodigo": 5256,
            "filial": "POSTO BR SHOPPING",
            "data": "2026-06-05",
            "valor": "100.00",
            "planoConta": "ENERGIA",
            "planoContaCodigo": 10,
        },
        {
            "empresaCodigo": 5256,
            "filial": "POSTO BR SHOPPING",
            "data": "2026-06-05",
            "valor": "-10.00",
            "planoConta": "ENERGIA",
            "planoContaCodigo": 10,
        },
    ]
    result = _evaluate(expenses=expenses)
    assert result["summary"]["totalRegistros"] == 2
    assert result["summary"]["invalidos"] == 1
    assert result["summary"]["validos"] == 1
    assert result["score"] == 50.0


def test_status_thresholds_ok_warning_danger():
    assert DataQualityService._status_from_score(96) == "ok"
    assert DataQualityService._status_from_score(90) == "warning"
    assert DataQualityService._status_from_score(89.99) == "danger"


def test_detect_duplicate_records():
    sales = [
        {
            "empresaCodigo": 5256,
            "filial": "POSTO BR SHOPPING",
            "vendaCodigo": 1,
            "data": "2026-06-05",
            "totalVenda": "300.00",
            "formaPagamento": "PIX",
        },
        {
            "empresaCodigo": 5256,
            "filial": "POSTO BR SHOPPING",
            "vendaCodigo": 1,
            "data": "2026-06-05",
            "totalVenda": "300.00",
            "formaPagamento": "PIX",
        },
    ]
    result = _evaluate(sales=sales)
    assert result["issues"]["duplicados"] == 1


def test_detect_unmapped_company_code():
    accounts = [
        {
            "empresaCodigo": 999999,
            "filial": "",
            "fornecedor": "Fornecedor X",
            "vencimento": "2026-06-20",
            "valor": "200.00",
        }
    ]
    result = _evaluate(accounts=accounts)
    assert result["issues"]["empresasNaoMapeadas"] == 1


def test_detect_invalid_monetary_value():
    expenses = [
        {
            "empresaCodigo": 5256,
            "filial": "POSTO BR SHOPPING",
            "data": "2026-06-05",
            "valor": None,
            "planoConta": "ENERGIA",
            "planoContaCodigo": 10,
        }
    ]
    result = _evaluate(expenses=expenses)
    assert result["issues"]["valoresInvalidos"] == 1


def test_is_active_fuel_product_various_cases():
    from src.services.network_financial_overview_service import is_active_fuel_product

    # Case 1: Active fuel product
    assert is_active_fuel_product({
        "nome": "GASOLINA COMUM.",
        "combustivel": True,
        "ativo": True
    }) is True

    # Case 2: Inactive fuel product (should be False)
    assert is_active_fuel_product({
        "nome": "GASOLINA COMUM.",
        "combustivel": True,
        "ativo": False
    }) is False

    # Case 3: Other status representing inactive (status / situacao / situação)
    assert is_active_fuel_product({
        "nome": "ETANOL COMUM",
        "combustivel": True,
        "situacao": "inativo"
    }) is False

    # Case 4: Non-fuel product (conveniência, active)
    assert is_active_fuel_product({
        "nome": "COCA COLA 350ML",
        "combustivel": False,
        "tipoProduto": "P",
        "ativo": True
    }) is False

    # Case 5: Fuel based on tipoProduto: C
    assert is_active_fuel_product({
        "nome": "DIESEL S10 COMUM",
        "tipoProduto": "C",
        "ativo": "SIM"
    }) is True
