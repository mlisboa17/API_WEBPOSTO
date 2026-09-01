"""Testes de validação de integridade de paginação — Sprint 44."""

from src.services.pagination_integrity_service import (
    PaginationIntegrityService,
    PaginationIntegrityResult,
)


def test_complete_pagination_with_matching_count():
    service = PaginationIntegrityService()
    metadata = {
        "resultados": [{"id": i} for i in range(100)],
        "pagination": {
            "complete": True,
            "termination": "EMPTY_BATCH",
            "pages": 2,
            "duplicatesRemoved": 0,
        },
    }

    result = service.validate(
        endpoint="VENDA",
        empresa_codigo=11495,
        period_start="2026-07-01",
        period_end="2026-07-25",
        pagination_metadata=metadata,
        expected_total=100,
    )

    assert result.is_complete is True
    assert result.integrity_status == "VERIFIED"
    assert result.alert_level == "OK"
    assert result.variance_pct == 0.0
    assert result.has_data_loss_risk is False


def test_incomplete_pagination_triggers_critical_alert():
    service = PaginationIntegrityService()
    metadata = {
        "resultados": [{"id": i} for i in range(50)],
        "pagination": {
            "complete": False,
            "termination": "CURSOR_STALLED",
            "pages": 1,
            "duplicatesRemoved": 0,
        },
    }

    result = service.validate(
        endpoint="DESPESAS",
        empresa_codigo=5555,
        period_start="2026-07-01",
        period_end="2026-07-25",
        pagination_metadata=metadata,
        expected_total=100,
    )

    assert result.is_complete is False
    assert result.integrity_status == "INCOMPLETE"
    assert result.alert_level == "CRITICAL"
    assert result.has_data_loss_risk is True


def test_variance_detected_when_count_differs():
    service = PaginationIntegrityService()
    metadata = {
        "resultados": [{"id": i} for i in range(95)],
        "pagination": {
            "complete": True,
            "termination": "SHORT_BATCH",
            "pages": 2,
            "duplicatesRemoved": 0,
        },
    }

    result = service.validate(
        endpoint="VENDA",
        empresa_codigo=74014,
        period_start="2026-07-01",
        period_end="2026-07-25",
        pagination_metadata=metadata,
        expected_total=100,
    )

    assert result.is_complete is True
    assert result.integrity_status == "VARIANCE_DETECTED"
    assert result.alert_level == "WARNING"
    assert result.variance_pct == 5.0


def test_summarize_multiple_results():
    service = PaginationIntegrityService()

    results = [
        PaginationIntegrityResult(
            endpoint="VENDA",
            empresa_codigo=11495,
            period_start="2026-07-01",
            period_end="2026-07-25",
            collected_total=100,
            pages_fetched=2,
            termination_reason="EMPTY_BATCH",
            is_complete=True,
            integrity_status="VERIFIED",
            alert_level="OK",
        ),
        PaginationIntegrityResult(
            endpoint="DESPESAS",
            empresa_codigo=5555,
            period_start="2026-07-01",
            period_end="2026-07-25",
            collected_total=50,
            pages_fetched=1,
            termination_reason="CURSOR_STALLED",
            is_complete=False,
            integrity_status="INCOMPLETE",
            alert_level="CRITICAL",
        ),
    ]

    summary = service.summarize(results)

    assert summary["total_validations"] == 2
    assert summary["complete"] == 1
    assert summary["incomplete"] == 1
    assert summary["overall_status"] == "CRITICAL"
    assert summary["data_loss_risk"] is True
    assert len(summary["critical_endpoints"]) == 1
