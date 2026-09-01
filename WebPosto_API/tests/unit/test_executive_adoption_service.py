from src.services.executive_adoption_service import ExecutiveAdoptionService


def test_adoption_metrics_measure_time_clicks_usage_and_ignored_features(tmp_path):
    service = ExecutiveAdoptionService(tmp_path / "adoption.json")
    service.record({"eventType": "PAGE_OPEN", "feature": "ATTENTION", "sessionId": "s1"})
    service.record({"eventType": "FEATURE_USED", "feature": "AI_VALUE", "sessionId": "s1"})
    service.record({"eventType": "INFORMATION_FOUND", "feature": "AI_VALUE", "sessionId": "s1", "elapsedMs": 4200, "clicks": 1})
    summary = service.summary()
    assert summary["sessions"] == 1
    assert summary["averageTimeToInformationMs"] == 4200
    assert summary["averageClicksToInformation"] == 1
    assert summary["featureUsage"]["AI_VALUE"] == 1
    assert "DETAILS" in summary["ignoredFeatures"]
    assert summary["containsBusinessData"] is False


def test_block_review_flags_ignored_and_slow_presidency_blocks(tmp_path):
    service = ExecutiveAdoptionService(tmp_path / "adoption.json")
    service.record({"eventType": "PAGE_OPEN", "feature": "ATTENTION", "sessionId": "s1"})
    service.record({"eventType": "FEATURE_USED", "feature": "ATTENTION", "sessionId": "s1"})
    service.record({"eventType": "INFORMATION_FOUND", "feature": "ATTENTION", "sessionId": "s1", "elapsedMs": 28000, "clicks": 1})
    service.record({"eventType": "FEATURE_USED", "feature": "AI_VALUE", "sessionId": "s1"})
    service.record({"eventType": "INFORMATION_FOUND", "feature": "AI_VALUE", "sessionId": "s1", "elapsedMs": 45000, "clicks": 2})
    review = service.block_review()
    attention = next(item for item in review["blocks"] if item["feature"] == "ATTENTION")
    value = next(item for item in review["blocks"] if item["feature"] == "VALUE")
    ai_value = next(item for item in review["blocks"] if item["feature"] == "AI_VALUE")

    assert attention["engagement"] == "ENGAGED"
    assert attention["withinThirtySecondTarget"] is True
    assert value["engagement"] == "IGNORED"
    assert "VALUE" in review["ignoredPresidencyBlocks"]
    assert ai_value["withinThirtySecondTarget"] is False
    assert any("AI_VALUE" in item or "Valor gerado" in item for item in review["recommendations"])
