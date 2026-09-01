from src.services.proactive_agent_orchestrator_service import (
    INSUFFICIENT_EVIDENCE,
    ProactiveAgentOrchestratorService,
)


def governed_radar():
    return {
        "day": "2026-07-24",
        "generatedAt": "2026-07-25T09:00:00+00:00",
        "priorities": [{
            "id": "risk-1",
            "type": "RISK",
            "title": "Margem negativa",
            "department": "combustiveis",
            "severity": "CRITICAL",
            "priorityScore": 85,
            "confidence": "HIGH",
            "recommendedAction": "Revisar preço e custo.",
            "evidence": {"grossMarginValue": -2000},
            "lineage": {"rule": "NEGATIVE_GROSS_MARGIN", "alertId": "risk-1"},
        }],
    }


def test_specialists_reuse_evidence_and_presidency_does_not_create_facts(tmp_path):
    service = ProactiveAgentOrchestratorService(tmp_path)
    result = service.coordinate(governed_radar())

    financial = next(item for item in result["specialistAgents"] if item["agent"] == "FINANCIAL")
    assert financial["recommendations"][0]["evidence"]["grossMarginValue"] == -2000
    assert financial["recommendations"][0]["justification"]
    assert result["presidencyAgent"]["coordinatedPriorities"][0]["id"] == "risk-1"
    assert result["presidencyAgent"]["newFactsCreated"] is False
    assert result["presidencyAgent"]["confidenceElevated"] is False
    assert service.latest()["day"] == "2026-07-24"


def test_agents_explicitly_block_when_evidence_is_absent(tmp_path):
    radar = governed_radar()
    radar["priorities"][0]["evidence"] = {}
    result = ProactiveAgentOrchestratorService(tmp_path).coordinate(radar)

    assert result["presidencyAgent"]["status"] == "INSUFFICIENT_EVIDENCE"
    assert result["presidencyAgent"]["message"] == INSUFFICIENT_EVIDENCE
    assert all(item["status"] == "INSUFFICIENT_EVIDENCE" for item in result["specialistAgents"])
