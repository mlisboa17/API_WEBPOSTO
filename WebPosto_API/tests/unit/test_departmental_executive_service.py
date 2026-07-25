from src.services.departmental_executive_service import DepartmentalExecutiveService


class FakeComparison:
    def build(self, day):
        return {
            "period": {"start": day, "end": day},
            "missingCompanies": [],
            "departments": [
                {
                    "department": department,
                    "period": {"start": day, "end": day},
                    "ranking": [
                        {"companyCode": 11495, "grossMarginValue": "30.00"},
                        {"companyCode": 5555, "grossMarginValue": "20.00"},
                    ],
                    "excludedCompanies": [],
                }
                for department in ("combustiveis", "conveniencia", "lubrificantes")
            ],
        }


class FakeKpis:
    def build_dre(self, company, day):
        return {
            "coverage": {"salesComplete": True, "costsComplete": True, "expensesComplete": False},
            "lines": [
                {
                    "department": department,
                    "revenue": "100.00",
                    "grossMarginValue": "30.00",
                    "grossMarginPercent": "30.00",
                    "specificMetrics": {},
                    "status": "PARTIAL_GROSS_MARGIN_ONLY",
                    "lineage": {"endpoints": ["/INTEGRACAO/VENDA_ITEM"]},
                }
                for department in ("combustiveis", "conveniencia", "lubrificantes")
            ],
        }


class FakeHistory:
    def build(self, company, start, end):
        return {"period": {"start": start, "end": end}, "departments": []}


def test_presidency_cockpit_keeps_departments_separate_and_does_not_call_margin_profit():
    result = DepartmentalExecutiveService(FakeKpis(), FakeComparison(), FakeHistory()).cockpit("2026-07-23")
    assert [item["department"] for item in result["blocks"]] == [
        "combustiveis", "conveniencia", "lubrificantes"
    ]
    assert all(item["operatingProfit"] is None for item in result["blocks"])


def test_director_panels_share_same_departmental_statement_and_export_scope():
    result = DepartmentalExecutiveService(FakeKpis(), FakeComparison(), FakeHistory()).director_panels(
        11495, "2026-07-23", "2026-07-23"
    )
    assert set(result["panels"]) == {"financial", "commercial", "operational"}
    assert all(row["companyCode"] == 11495 for row in result["exportRows"])
    assert {row["department"] for row in result["exportRows"]} == {
        "combustiveis", "conveniencia", "lubrificantes"
    }
