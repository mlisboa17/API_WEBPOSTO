"""Testes unitários para EmployeePerformanceService (Sprint 55)."""
import pytest
from src.services.employee_performance_service import EmployeePerformanceService


@pytest.fixture
def service():
    return EmployeePerformanceService()


def test_analyze_returns_ranking(service):
    result = service.analyze("2026-07-01", "2026-07-31", empresa_codigo=1)
    assert len(result.ranking) > 0
    assert result.melhor_frentista is not None
    assert result.pior_frentista is not None
    assert result.melhor_frentista.score >= result.pior_frentista.score


def test_ranking_fields(service):
    result = service.analyze("2026-07-01", "2026-07-31")
    frentista = result.ranking[0]
    assert frentista.funcionario_codigo > 0
    assert frentista.nome
    assert frentista.litros_vendidos >= 0
    assert frentista.ticket_medio >= 0
    assert frentista.galonagem_por_hora >= 0


def test_auditoria_caixa(service):
    result = service.analyze("2026-07-01", "2026-07-31")
    assert len(result.auditoria_caixa) > 0
    for item in result.auditoria_caixa:
        assert item.diferenca != 0 or item.status == "OK"
        assert item.turno


def test_score_bounds(service):
    result = service.analyze("2026-07-01", "2026-07-31")
    for r in result.ranking:
        assert 0 <= r.score <= 100
