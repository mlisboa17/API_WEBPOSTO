"""Testes do motor de alertas proativos — Sprint 50 (Persistência e Notificações)."""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from src.services.proactive_alert_service import ProactiveAlertService
from src.models.alert_model import AlertCategory, AlertSeverity, ExecutiveAlertModel
from src.infrastructure.repositories.executive_alert_repository import ExecutiveAlertRepository


@pytest.mark.asyncio
async def test_evaluate_cash_break_triggers_alert():
    # Mock Repository para evitar dependência de banco real nos testes unitários
    repo = MagicMock(spec=ExecutiveAlertRepository)
    repo.get_by_external_id = AsyncMock(return_value=None)
    repo.create = AsyncMock(side_effect=lambda x: x)
    
    service = ProactiveAlertService(repository=repo)
    
    alert = await service.evaluate_cash_break(
        empresa_codigo=11495,
        data="2026-07-25",
        diferenca_absoluta=150.0,
        operador="João Silva"
    )
    
    assert alert is not None
    assert alert.category == AlertCategory.QUEBRA_CAIXA
    assert alert.severity == AlertSeverity.CRITICAL
    assert alert.impact_rs == 150.0
    assert "João Silva" in alert.description


@pytest.mark.asyncio
async def test_evaluate_cash_break_below_threshold():
    service = ProactiveAlertService() # Sem repo
    alert = await service.evaluate_cash_break(11495, "2026-07-25", 50.0, "Maria")
    assert alert is None


@pytest.mark.asyncio
async def test_evaluate_tank_deviation_triggers_alert():
    repo = MagicMock(spec=ExecutiveAlertRepository)
    repo.get_by_external_id = AsyncMock(return_value=None)
    repo.create = AsyncMock(side_effect=lambda x: x)
    
    service = ProactiveAlertService(repository=repo)
    
    alert = await service.evaluate_tank_deviation(
        empresa_codigo=11495,
        data="2026-07-25",
        tanque_id=1,
        combustivel="Gasolina Aditivada",
        variacao_real_litros=-60.0,
        is_thermal_explained=False
    )
    
    assert alert is not None
    assert alert.category == AlertCategory.DESVIO_TANQUE
    assert alert.severity == AlertSeverity.CRITICAL


@pytest.mark.asyncio
async def test_evaluate_cash_vacuum_triggers_alert():
    repo = MagicMock(spec=ExecutiveAlertRepository)
    repo.get_by_external_id = AsyncMock(return_value=None)
    repo.create = AsyncMock(side_effect=lambda x: x)
    
    service = ProactiveAlertService(repository=repo)
    
    alert = await service.evaluate_cash_vacuum(
        empresa_codigo=11495,
        data="2026-07-25",
        vacuo_dias=20.0,
        necessidade_capital=300000.0
    )
    
    assert alert is not None
    assert alert.category == AlertCategory.ESTOURO_VACUO
    assert alert.severity == AlertSeverity.WARNING


@pytest.mark.asyncio
async def test_list_unresolved_alerts():
    repo = MagicMock(spec=ExecutiveAlertRepository)
    repo.list_unresolved = AsyncMock(return_value=[MagicMock(), MagicMock()])
    
    service = ProactiveAlertService(repository=repo)
    unresolved = await service.list_unresolved()
    
    assert len(unresolved) == 2
    repo.list_unresolved.assert_called_once()
