"""Testes unitários para EmployeePerformanceService (Sprint 55 / 02)."""

from src.services.employee_performance_service import EmployeePerformanceService


def test_analyze_empty_cache_returns_empty_ranking():
    svc = EmployeePerformanceService()
    # Sem PistaSync / cashier na suite unitária → coleções vazias (sem mock fictício)
    result = svc.analyze("2026-07-01", "2026-07-31", empresa_codigo=5555)
    assert result.ranking == []
    assert result.auditoria_caixa == []
    assert result.melhor_frentista is None
    assert result.pior_frentista is None


def test_build_summary_from_real_shaped_rows():
    svc = EmployeePerformanceService()
    sales = [
        {
            "funcionarioCodigo": 101,
            "tipo": "ABASTECIMENTO",
            "litros": 1000,
            "valor": 6000,
            "upsell": 100,
        },
        {
            "funcionarioCodigo": 102,
            "tipo": "ABASTECIMENTO",
            "litros": 500,
            "valor": 3000,
            "upsell": 50,
        },
    ]
    cash = [
        {
            "funcionarioCodigo": 103,
            "turno": "Manhã",
            "pdvCodigo": 1,
            "caixaCodigo": 10,
            "datahora": "2026-07-26",
            "diferenca": -20.0,
            "status": "ATENCAO",
        }
    ]
    employees = [
        {
            "funcionarioCodigo": 101,
            "nome": "João",
            "funcao": "Frentista",
            "horas_trabalhadas": 8,
        },
        {
            "funcionarioCodigo": 102,
            "nome": "Maria",
            "funcao": "Frentista",
            "horas_trabalhadas": 8,
        },
        {
            "funcionarioCodigo": 103,
            "nome": "Pedro",
            "funcao": "Operador Caixa",
            "horas_trabalhadas": 8,
        },
    ]
    result = svc._build_summary(sales, cash, employees)
    assert len(result.ranking) == 2
    assert result.melhor_frentista is not None
    assert result.melhor_frentista.score >= result.pior_frentista.score
    assert len(result.auditoria_caixa) == 1
    for r in result.ranking:
        assert 0 <= r.score <= 100
