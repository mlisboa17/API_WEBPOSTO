"""Testes Unitários Sprint 50 — Persistência, Notificações e Dashboard Bundle."""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime, timezone

from src.models.alert_model import ExecutiveAlertModel, AlertCategory, AlertSeverity
from src.infrastructure.repositories.executive_alert_repository import ExecutiveAlertRepository
from src.services.proactive_alert_service import ProactiveAlertService
from src.services.notification_dispatcher_service import NotificationDispatcherService


@pytest.mark.asyncio
async def test_alert_persistence_and_idempotency():
    # Mock Session and Repository
    session = AsyncMock()
    repo = ExecutiveAlertRepository(session)
    
    # 1. Test Create (New)
    alert = ExecutiveAlertModel(
        alert_external_id="test_id_123",
        category=AlertCategory.QUEBRA_CAIXA,
        severity=AlertSeverity.CRITICAL,
        title="Teste",
        description="Teste",
        data_referencia="2026-07-25"
    )
    
    # Mock repo behaviors
    with patch.object(repo, "get_by_external_id", return_value=None):
        with patch.object(repo, "create", return_value=alert) as mock_create:
            service = ProactiveAlertService(repository=repo)
            result = await service.evaluate_cash_break(11495, "2026-07-25", 150.0, "Operador X")
            
            assert result is not None
            mock_create.assert_called_once()

    # 2. Test Idempotency (Existing)
    with patch.object(repo, "get_by_external_id", return_value=alert):
        with patch.object(repo, "create") as mock_create:
            service = ProactiveAlertService(repository=repo)
            result = await service.evaluate_cash_break(11495, "2026-07-25", 150.0, "Operador X")
            
            assert result == alert
            mock_create.assert_not_called()


@pytest.mark.asyncio
async def test_notification_dispatcher_sends_critical_only():
    dispatcher = NotificationDispatcherService(webhook_url="http://fake.url")
    
    critical_alert = ExecutiveAlertModel(
        alert_external_id="crit", severity=AlertSeverity.CRITICAL, 
        category=AlertCategory.QUEBRA_CAIXA, title="Crit", description="X", data_referencia="2026"
    )
    warning_alert = ExecutiveAlertModel(
        alert_external_id="warn", severity=AlertSeverity.WARNING, 
        category=AlertCategory.ESTOURO_VACUO, title="Warn", description="Y", data_referencia="2026"
    )

    with patch("httpx.AsyncClient.post", return_value=MagicMock(status_code=200)) as mock_post:
        # Critical should send
        sent = await dispatcher.dispatch_alert(critical_alert)
        assert sent is True
        assert mock_post.called

        mock_post.reset_mock()
        
        # Warning should NOT send
        sent = await dispatcher.dispatch_alert(warning_alert)
        assert sent is False
        assert not mock_post.called


@pytest.mark.asyncio
async def test_resolve_alert_updates_db():
    session = AsyncMock()
    repo = ExecutiveAlertRepository(session)
    
    # Mock execute result for rowcount
    mock_result = MagicMock()
    mock_result.rowcount = 1
    session.execute.return_value = mock_result

    service = ProactiveAlertService(repository=repo)
    success = await service.resolve_alert(alert_id=1, resolved_by="admin@logos.com", notes="Resolvido")
    
    assert success is True
    assert session.execute.called
    assert session.commit.called


@pytest.mark.asyncio
async def test_evaluate_tank_deviation_creates_alert():
    session = AsyncMock()
    repo = ExecutiveAlertRepository(session)
    service = ProactiveAlertService(repository=repo)
    
    # Mock repo to return None (no existing alert)
    repo.get_by_external_id = AsyncMock(return_value=None)
    repo.create = AsyncMock(side_effect=lambda x: x)

    # Tank deviation > 50L and not explained
    alert = await service.evaluate_tank_deviation(11495, "2026-07-25", 1, "Gasolina", -80.0, False)
    
    assert alert is not None
    assert alert.category == AlertCategory.DESVIO_TANQUE
    assert alert.severity == AlertSeverity.CRITICAL


@pytest.mark.asyncio
async def test_evaluate_ruptura_curva_a_creates_alert():
    session = AsyncMock()
    repo = ExecutiveAlertRepository(session)
    service = ProactiveAlertService(repository=repo)
    
    repo.get_by_external_id = AsyncMock(return_value=None)
    repo.create = AsyncMock(side_effect=lambda x: x)

    # Rupture with 1.5 days coverage
    alert = await service.evaluate_ruptura_curva_a(11495, "2026-07-25", 1001, "Cerveja", 5.0, 1.5)
    
    assert alert is not None
    assert alert.category == AlertCategory.RUPTURA_CURVA_A
    assert alert.severity == AlertSeverity.CRITICAL
