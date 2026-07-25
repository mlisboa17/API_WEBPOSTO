from src.services.proactive_notification_service import ProactiveNotificationService


def radar():
    return {
        "day": "2026-07-24",
        "priorities": [{
            "id": "risk-1",
            "type": "RISK",
            "title": "Margem negativa",
            "severity": "CRITICAL",
            "evidence": {"grossMarginValue": -1000},
            "confidence": "HIGH",
            "estimatedImpactBRL": 1000,
            "impactLabel": "ESTIMATED_FROM_EVIDENCE",
            "suggestedOwner": "Diretoria Operacional",
            "recommendedAction": "Revisar causa.",
            "dueInDays": 1,
            "lineage": {"alertId": "risk-1"},
        }],
    }


def test_notifications_are_idempotent_and_contain_governance_fields(tmp_path):
    service = ProactiveNotificationService(tmp_path / "outbox.json", webhook_url="")
    first = service.dispatch(radar())
    second = service.dispatch(radar())
    records = service.list()

    assert first["created"] == 2
    assert second["created"] == 0
    assert {item["audience"] for item in records} == {"PRESIDENT", "DIRECTOR"}
    assert all(item["evidence"] and item["confidence"] and item["lineage"] for item in records)


def test_configured_webhook_is_actively_dispatched(tmp_path):
    sent = []
    service = ProactiveNotificationService(
        tmp_path / "outbox.json",
        webhook_url="https://notifications.invalid/hook",
        sender=lambda url, payload: sent.append((url, payload["id"])),
    )

    result = service.dispatch(radar())

    assert result["webhookDelivered"] == 2
    assert len(sent) == 2
    assert all(item["delivery"]["webhook"] == "DELIVERED" for item in service.list())
