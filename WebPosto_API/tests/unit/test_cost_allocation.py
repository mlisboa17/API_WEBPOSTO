"""Testes de rateio de custos compartilhados — Sprint 45."""

from decimal import Decimal

from src.services.cost_allocation_service import (
    CostAllocationService,
    AllocationRule,
    AllocationMethod,
    AllocationResult,
)


def test_percentage_allocation_sums_to_original():
    service = CostAllocationService()
    rule = AllocationRule(
        rule_id="test-1",
        management_account_code="ENERGIA",
        method=AllocationMethod.PERCENTAGE,
        allocations={"combustiveis": 50, "conveniencia": 30, "lubrificantes": 20},
        reviewer="admin",
        rationale="Rateio por área ocupada",
    )
    service.register_rule(rule)

    result = service.allocate(
        expense_id="exp-001",
        management_account_code="ENERGIA",
        value=1000.00,
    )

    assert result.method == AllocationMethod.PERCENTAGE
    total_allocated = sum(a["allocated_value"] for a in result.allocations)
    assert total_allocated == 1000.00

    combustiveis = next(a for a in result.allocations if a["department"] == "combustiveis")
    assert combustiveis["allocated_value"] == 500.00


def test_revenue_proportional_allocation():
    service = CostAllocationService()
    rule = AllocationRule(
        rule_id="test-2",
        management_account_code="ALUGUEL",
        method=AllocationMethod.REVENUE_PROPORTIONAL,
        allocations={},
        reviewer="admin",
        rationale="Rateio por faturamento",
    )
    service.register_rule(rule)

    revenues = {
        "combustiveis": 80000.00,
        "conveniencia": 15000.00,
        "lubrificantes": 5000.00,
    }

    result = service.allocate(
        expense_id="exp-002",
        management_account_code="ALUGUEL",
        value=10000.00,
        company_revenues=revenues,
    )

    assert result.method == AllocationMethod.REVENUE_PROPORTIONAL
    total_allocated = sum(a["allocated_value"] for a in result.allocations)
    assert total_allocated == 10000.00

    combustiveis = next(a for a in result.allocations if a["department"] == "combustiveis")
    assert combustiveis["percentage"] == 80.0


def test_equal_distribution_fallback():
    service = CostAllocationService()

    result = service.allocate(
        expense_id="exp-003",
        management_account_code="UNKNOWN",
        value=999.00,
    )

    assert result.method == "EQUAL_DISTRIBUTION"
    total_allocated = sum(a["allocated_value"] for a in result.allocations)
    assert total_allocated == 999.00
    assert len(result.allocations) == 3


def test_allocation_rule_validation_rejects_invalid_sum():
    rule = AllocationRule(
        rule_id="test-invalid",
        management_account_code="TEST",
        method=AllocationMethod.PERCENTAGE,
        allocations={"combustiveis": 50, "conveniencia": 30},
        reviewer="admin",
        rationale="Soma inválida",
    )

    assert rule.validate_percentage_sum() is False


def test_apply_allocations_to_dre():
    service = CostAllocationService()
    dre_lines = [
        {"companyCode": 11495, "department": "combustiveis", "expenses": "5000"},
        {"companyCode": 11495, "department": "conveniencia", "expenses": "2000"},
        {"companyCode": 11495, "department": "lubrificantes", "expenses": "1000"},
    ]
    allocations = [
        AllocationResult(
            source_expense_id="exp-001",
            management_account_code="ENERGIA",
            original_value=300.00,
            method=AllocationMethod.PERCENTAGE,
            allocations=[
                {"department": "combustiveis", "percentage": 50, "allocated_value": 150.0},
                {"department": "conveniencia", "percentage": 30, "allocated_value": 90.0},
                {"department": "lubrificantes", "percentage": 20, "allocated_value": 60.0},
            ],
        ),
    ]

    result = service.apply_allocations_to_dre(dre_lines, allocations)

    combustiveis = next(l for l in result if l["department"] == "combustiveis")
    assert float(combustiveis["expenses"]) == 5150.0
    assert combustiveis["hasAllocatedCosts"] is True
    assert combustiveis["allocatedCostsValue"] == 150.0


def test_product_type_enum_parsing():
    from src.domain.enums.product_type import ProductType, ProductTypeInfo

    assert ProductType.from_webposto("C") == ProductType.COMBUSTIVEL
    assert ProductType.from_webposto("P") == ProductType.PRODUTO
    assert ProductType.from_webposto("U") == ProductType.UTILIDADE
    assert ProductType.from_webposto("X") == ProductType.DESCONHECIDO
    assert ProductType.from_webposto(None) == ProductType.DESCONHECIDO

    info = ProductTypeInfo.from_raw("C")
    assert info.is_fuel is True
    assert info.department == "combustiveis"

    info_p = ProductTypeInfo.from_raw("P")
    assert info_p.is_convenience is True
    assert info_p.department == "conveniencia"
