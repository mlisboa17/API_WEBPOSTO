from src.services.departmental_comparison_service import DepartmentalComparisonService


class FakeKpis:
    def __init__(self, incomplete=None, missing=None):
        self.incomplete = set(incomplete or [])
        self.missing = set(missing or [])

    def build_dre(self, company, day):
        if company in self.missing:
            return None
        margin = {11495: "30.00", 5555: "20.00", 74014: "40.00"}[company]
        complete = company not in self.incomplete
        return {
            "coverage": {"salesComplete": complete, "costsComplete": complete},
            "lines": [
                {
                    "department": department,
                    "revenue": "100.00",
                    "grossMarginValue": margin,
                    "grossMarginPercent": margin,
                    "lineage": {"endpoints": ["/INTEGRACAO/VENDA_ITEM"]},
                }
                for department in ("combustiveis", "conveniencia", "lubrificantes")
            ],
        }


def test_ranks_only_same_department_and_same_period():
    result = DepartmentalComparisonService(FakeKpis()).build("2026-07-23")
    fuel = result["departments"][0]

    assert result["comparisonRule"] == "SAME_DEPARTMENT_SAME_PERIOD_ONLY"
    assert fuel["basesEquivalent"] is True
    assert [item["companyCode"] for item in fuel["ranking"]] == [74014, 11495, 5555]
    assert fuel["ranking"][0]["gapToBestGrossMargin"] == "0.00"
    assert fuel["ranking"][-1]["gapToBestGrossMargin"] == "20.00"


def test_excludes_company_with_non_equivalent_coverage():
    result = DepartmentalComparisonService(FakeKpis(incomplete={5555})).build(
        "2026-07-23"
    )
    fuel = result["departments"][0]

    assert fuel["basesEquivalent"] is False
    assert [item["companyCode"] for item in fuel["ranking"]] == [74014, 11495]
    assert fuel["excludedCompanies"] == [
        {"companyCode": 5555, "reason": "NON_EQUIVALENT_COVERAGE"}
    ]


def test_marks_missing_materialization_without_inventing_zero():
    result = DepartmentalComparisonService(FakeKpis(missing={74014})).build(
        "2026-07-23"
    )

    assert result["missingCompanies"] == [74014]
    assert all(
        department["excludedCompanies"][-1]
        == {"companyCode": 74014, "reason": "BATCH_NOT_MATERIALIZED"}
        for department in result["departments"]
    )
