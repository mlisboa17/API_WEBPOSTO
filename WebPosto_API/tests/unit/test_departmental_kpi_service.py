from src.services.departmental_fact_store import DepartmentalFactStore
from src.services.departmental_kpi_service import DepartmentalKpiService


def fact(kind, department, value, quantity="0", endpoint="/INTEGRACAO/VENDA_ITEM"):
    return {
        "fact_id": f"{kind}:{department}:{value}",
        "kind": kind,
        "empresa_codigo": 11495,
        "departamento": department,
        "status": "CLASSIFIED",
        "source_record_id": "1:1",
        "quantidade": quantity,
        "valor": value,
        "lineage": {
            "logical_token": "POSTO VIP",
            "endpoint": endpoint,
            "collected_at": "2026-07-24T00:00:00+00:00",
        },
    }


def save_batches(store, *, expense_quarantine=True):
    expenses = {
        "facts": [] if expense_quarantine else [
            fact("EXPENSE", "combustiveis", "10", endpoint="/INTEGRACAO/DESPESAS")
        ],
        "quarantine": [fact("EXPENSE", None, "10")] if expense_quarantine else [],
        "identity_conflicts": 0,
        "reconciliation_difference": "0",
    }
    store.save(
        {
            "materialized": True,
            "publishable": not expense_quarantine,
            "companyCode": 11495,
            "day": "2026-07-23",
            "blockingReasons": [],
            "batches": {
                "sales": {
                    "facts": [
                        fact("SALE", "combustiveis", "100", "10"),
                        fact("SALE", "conveniencia", "50", "5"),
                    ],
                    "quarantine": [],
                    "identity_conflicts": 0,
                    "reconciliation_difference": "0",
                },
                "costs": {
                    "facts": [
                        fact("COST", "combustiveis", "70"),
                        fact("COST", "conveniencia", "30"),
                    ],
                    "quarantine": [],
                    "identity_conflicts": 0,
                    "reconciliation_difference": "0",
                },
                "expenses": expenses,
            },
        }
    )


def test_dre_publishes_gross_margin_but_not_operating_profit_without_expense_coverage(tmp_path):
    store = DepartmentalFactStore(tmp_path)
    save_batches(store, expense_quarantine=True)

    result = DepartmentalKpiService(store).build_dre(11495, "2026-07-23")
    fuel = next(line for line in result["lines"] if line["department"] == "combustiveis")

    assert fuel["revenue"] == "100.00"
    assert fuel["costOfRevenue"] == "70.00"
    assert fuel["grossMarginValue"] == "30.00"
    assert fuel["grossMarginPercent"] == "30.00"
    assert fuel["marginPerUnit"] == "3.00"
    assert fuel["quantityUnit"] == "L"
    assert fuel["specificMetrics"] == {
        "liters": "10",
        "averageSalePricePerLiter": "10.00",
        "costPerLiter": "7.00",
        "grossMarginPerLiter": "3.00",
    }
    assert fuel["operatingExpenses"] is None
    assert fuel["operatingResult"] is None
    assert fuel["status"] == "PARTIAL_GROSS_MARGIN_ONLY"
    assert result["publishable"] is False
    assert result["reviewRequired"] is True

    convenience = next(
        line for line in result["lines"] if line["department"] == "conveniencia"
    )
    assert convenience["specificMetrics"]["transactionCount"] == 1
    assert convenience["specificMetrics"]["averageTicket"] == "50.00"
    assert convenience["specificMetrics"]["itemsPerTransaction"] == "1.00"


def test_complete_expense_coverage_releases_operating_result(tmp_path):
    store = DepartmentalFactStore(tmp_path)
    save_batches(store, expense_quarantine=False)

    result = DepartmentalKpiService(store).build_dre(11495, "2026-07-23")
    fuel = next(line for line in result["lines"] if line["department"] == "combustiveis")

    assert fuel["operatingExpenses"] == "10.00"
    assert fuel["operatingResult"] == "20.00"
    assert fuel["operatingMarginPercent"] == "20.00"
    assert fuel["status"] == "COMPLETE"
    assert result["publishable"] is True


def test_dre_has_all_three_departments_even_when_one_has_no_movement(tmp_path):
    store = DepartmentalFactStore(tmp_path)
    save_batches(store)

    result = DepartmentalKpiService(store).build_dre(11495, "2026-07-23")

    assert [line["department"] for line in result["lines"]] == [
        "combustiveis",
        "conveniencia",
        "lubrificantes",
    ]
    lubricants = result["lines"][2]
    assert lubricants["revenue"] == "0.00"
    assert lubricants["grossMarginPercent"] is None


def test_unlicensed_company_is_rejected_before_store_access(tmp_path):
    service = DepartmentalKpiService(DepartmentalFactStore(tmp_path))

    try:
        service.build_dre(5256, "2026-07-23")
    except ValueError as exc:
        assert str(exc) == "UNLICENSED_COMPANY"
    else:
        raise AssertionError("Empresa não licenciada deveria ser rejeitada")


def test_batch_coverage_accepts_quarantine_only_below_count_and_value_tolerance():
    service = DepartmentalKpiService()
    facts = [{"valor": "1"}] * 99

    assert service._batch_complete(
        {
            "facts": facts,
            "quarantine": [{"valor": "1"}],
            "source_total": "100",
            "identity_conflicts": 0,
            "reconciliation_difference": "0",
        }
    )
    assert not service._batch_complete(
        {
            "facts": facts,
            "quarantine": [{"valor": "50"}],
            "source_total": "149",
            "identity_conflicts": 0,
            "reconciliation_difference": "0",
        }
    )
