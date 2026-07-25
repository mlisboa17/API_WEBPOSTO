from src.services.proactive_value_service import ProactiveValueService


def radar():
    return {
        "day": "2026-07-24",
        "generatedAt": "2026-07-24T09:00:00+00:00",
        "priorities": [{
            "id": "risk-1",
            "type": "RISK",
            "title": "Margem negativa",
            "estimatedImpactBRL": 4000,
            "confidence": "HIGH",
            "lineage": {"alertId": "risk-1"},
        }],
    }


def briefing():
    return {
        "presidencyAgent": {
            "coordinatedPriorities": [{
                "id": "risk-1",
                "contributingAgents": ["FINANCIAL", "OPERATIONAL"],
            }]
        }
    }


def validated_service(tmp_path):
    service = ProactiveValueService(tmp_path / "value.json")
    service.register_radar(radar(), briefing())
    service.mark_delivered(radar())
    recommendation_id = "2026-07-24:risk-1"
    service.transition(recommendation_id, "VIEWED", "director", "Visualizada no painel")
    service.transition(recommendation_id, "ACCEPTED", "director", "Ação aprovada")
    service.transition(recommendation_id, "IMPLEMENTED", "manager", "Preço corrigido")
    service.transition(
        recommendation_id,
        "VALIDATED",
        "audit",
        "Conferência financeira anexada",
        {"costAvoidedBRL": 1500, "riskMitigatedBRL": 2000, "executiveHoursSaved": 3},
    )
    return service


def test_value_lifecycle_separates_estimated_from_validated(tmp_path):
    service = validated_service(tmp_path)
    summary = service.summary("2026-07")

    assert summary["estimatedValue"]["potentialValueBRL"] == 4000
    assert summary["businessValueGeneratedByAI"]["costAvoidedBRL"] == 1500
    assert summary["businessValueGeneratedByAI"]["label"] == "VALIDATED_VALUE_ONLY"
    assert summary["recommendations"] == {
        "generated": 1,
        "delivered": 1,
        "viewed": 1,
        "accepted": 1,
        "rejected": 0,
        "implemented": 1,
        "validated": 1,
    }


def test_agent_reliability_uses_only_observed_results_and_splits_value(tmp_path):
    service = validated_service(tmp_path)
    summary = service.summary("2026-07")
    financial = next(item for item in summary["agentMetrics"] if item["agent"] == "FINANCIAL")
    commercial = next(item for item in summary["agentMetrics"] if item["agent"] == "COMMERCIAL")

    assert financial["reliability"]["score"] == 100
    assert financial["attributedValidatedValueBRL"] == 1750
    assert commercial["reliability"]["score"] is None
    assert commercial["reliability"]["status"] == "INSUFFICIENT_VALIDATED_OUTCOMES"
    assert summary["topContributingAgent"]["agent"] in {"FINANCIAL", "OPERATIONAL"}


def test_rejection_can_record_false_positive_without_inventing_value(tmp_path):
    service = ProactiveValueService(tmp_path / "value.json")
    service.register_radar(radar(), briefing())
    service.mark_delivered(radar())
    recommendation_id = "2026-07-24:risk-1"
    service.transition(recommendation_id, "VIEWED", "director", "Análise realizada")
    service.transition(
        recommendation_id, "REJECTED", "director",
        "Evidência operacional demonstrou alarme indevido", false_positive=True,
    )
    summary = service.summary()
    financial = next(item for item in summary["agentMetrics"] if item["agent"] == "FINANCIAL")

    assert financial["falsePositives"] == 1
    assert financial["reliability"]["components"]["historicalPrecision"] == 0
    assert summary["businessValueGeneratedByAI"]["totalFinancialValueBRL"] == 0


def test_validation_requires_measurable_value(tmp_path):
    service = ProactiveValueService(tmp_path / "value.json")
    service.register_radar(radar(), briefing())
    service.mark_delivered(radar())
    recommendation_id = "2026-07-24:risk-1"
    service.transition(recommendation_id, "VIEWED", "director", "Visualizada")
    service.transition(recommendation_id, "ACCEPTED", "director", "Aprovada")
    service.transition(recommendation_id, "IMPLEMENTED", "manager", "Implementada")
    try:
        service.transition(recommendation_id, "VALIDATED", "audit", "Validada", {})
    except ValueError as exc:
        assert str(exc) == "VALIDATED_VALUE_REQUIRED"
    else:
        raise AssertionError("resultado sem valor observado não pode ser validado")


def test_monthly_report_separates_validated_from_estimated(tmp_path):
    service = validated_service(tmp_path)
    report = service.monthly_report("2026-07")

    assert report["reportType"] == "MONTHLY_BUSINESS_VALUE_GENERATED_BY_AI"
    assert report["period"] == "2026-07"
    assert report["businessValueGeneratedByAI"]["label"] == "VALIDATED_VALUE_ONLY"
    assert report["estimatedValue"]["label"] == "ESTIMATED_NOT_REALIZED"
    assert report["governance"]["validatedOnlyInTotals"] is True
    assert len(report["items"]) == 1
    assert report["items"][0]["status"] == "VALIDATED"
