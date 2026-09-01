from src.services.proactive_executive_radar_service import ProactiveExecutiveRadarService


class FakeOperations:
    def health(self, day):
        return {
            "status": "DEGRADED",
            "companies": [{
                "companyCode": 11495,
                "referenceDayAvailable": day.endswith("24"),
                "publishable": False,
                "blockingReasons": ["EXPENSES_INCOMPLETE"],
            }],
        }

    def daily_report(self, day):
        return {
            "health": self.health(day),
            "alerts": [{
                "id": "alert-1",
                "companyCode": 11495,
                "department": "combustiveis",
                "severity": "CRITICAL",
                "rule": "NEGATIVE_GROSS_MARGIN",
                "message": "Margem bruta negativa.",
                "estimatedImpactBRL": 2500.0,
                "suggestedOwner": "Diretoria Operacional",
                "dueInDays": 1,
                "evidence": {"grossMarginValue": -2500.0},
                "period": {"start": day, "end": day},
            }],
        }


def test_daily_radar_prioritizes_evidenced_risk_and_answers_presidency(tmp_path):
    service = ProactiveExecutiveRadarService(FakeOperations(), tmp_path)
    radar = service.generate("2026-07-24")

    assert radar["status"] == "ACTION_REQUIRED"
    assert radar["priorities"][0]["estimatedImpactBRL"] == 2500.0
    assert radar["priorities"][0]["priorityScore"] > 60
    assert radar["executiveAnswers"]["whereLosingMoney"]["id"] == "alert-1"
    assert radar["governance"]["automaticExecution"] is False
    assert service.latest()["day"] == "2026-07-24"


def test_radar_does_not_invent_unsupported_growth_opportunity(tmp_path):
    radar = ProactiveExecutiveRadarService(FakeOperations(), tmp_path).generate("2026-07-24")
    assert radar["executiveAnswers"]["fastestGrowthOpportunity"] == {
        "status": "INSUFFICIENT_EQUIVALENT_DATA"
    }
    assert "customers" in radar["governance"]["unsupportedDomains"]
