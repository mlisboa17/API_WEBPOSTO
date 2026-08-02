"""Testes de quebra de caixa — Sprint 48."""

from src.services.cash_break_service import (
    CashBreakService,
    CashBreakSummary,
    CashBreakItem,
    CashBreakSeverity,
)


def test_classify_break_normal():
    service = CashBreakService(tolerance_normal=20.0, tolerance_warning=100.0)

    assert service.classify_break(10.0) == CashBreakSeverity.NORMAL
    assert service.classify_break(20.0) == CashBreakSeverity.NORMAL


def test_classify_break_warning():
    service = CashBreakService(tolerance_normal=20.0, tolerance_warning=100.0)

    assert service.classify_break(21.0) == CashBreakSeverity.WARNING
    assert service.classify_break(50.0) == CashBreakSeverity.WARNING
    assert service.classify_break(100.0) == CashBreakSeverity.WARNING


def test_classify_break_critico():
    service = CashBreakService(tolerance_normal=20.0, tolerance_warning=100.0)

    assert service.classify_break(101.0) == CashBreakSeverity.CRITICO
    assert service.classify_break(500.0) == CashBreakSeverity.CRITICO


def test_analyze_closure_positive_break():
    service = CashBreakService()

    item = service.analyze_closure(
        caixa_codigo=101,
        empresa_codigo=11495,
        data_fechamento="2026-07-25",
        valor_esperado=5000.0,
        valor_informado=5050.0,
        operador_nome="João",
    )

    assert item.diferenca == 50.0
    assert item.diferenca_absoluta == 50.0
    assert item.severity == CashBreakSeverity.WARNING


def test_analyze_closure_negative_break():
    service = CashBreakService()

    item = service.analyze_closure(
        caixa_codigo=102,
        empresa_codigo=11495,
        data_fechamento="2026-07-25",
        valor_esperado=5000.0,
        valor_informado=4900.0,
        operador_nome="Maria",
    )

    assert item.diferenca == -100.0
    assert item.diferenca_absoluta == 100.0
    assert item.severity == CashBreakSeverity.WARNING


def test_analyze_closure_critical():
    service = CashBreakService()

    item = service.analyze_closure(
        caixa_codigo=103,
        empresa_codigo=11495,
        data_fechamento="2026-07-25",
        valor_esperado=5000.0,
        valor_informado=4800.0,
    )

    assert item.diferenca == -200.0
    assert item.severity == CashBreakSeverity.CRITICO
    assert item.requires_justification is True


def test_analyze_batch_summary():
    service = CashBreakService()

    closures = [
        {"caixaCodigo": 1, "empresaCodigo": 11495, "dataFechamento": "2026-07-25",
         "valorEsperado": 5000, "valorInformado": 5000},
        {"caixaCodigo": 2, "empresaCodigo": 11495, "dataFechamento": "2026-07-25",
         "valorEsperado": 6000, "valorInformado": 5950},
        {"caixaCodigo": 3, "empresaCodigo": 11495, "dataFechamento": "2026-07-25",
         "valorEsperado": 7000, "valorInformado": 6800},
    ]

    summary = service.analyze_batch(closures, "2026-07-25", "2026-07-25", 11495)

    assert summary.total_fechamentos == 3
    assert summary.fechamentos_normais == 1
    assert summary.fechamentos_warning == 1
    assert summary.fechamentos_criticos == 1
    assert summary.fechamentos_com_quebra == 2


def test_analyze_batch_somas():
    service = CashBreakService()

    closures = [
        {"caixaCodigo": 1, "empresaCodigo": 11495, "dataFechamento": "2026-07-25",
         "valorEsperado": 5000, "valorInformado": 5050},
        {"caixaCodigo": 2, "empresaCodigo": 11495, "dataFechamento": "2026-07-25",
         "valorEsperado": 6000, "valorInformado": 5900},
    ]

    summary = service.analyze_batch(closures, "2026-07-25", "2026-07-25")

    assert summary.soma_quebras_positivas == 50.0
    assert summary.soma_quebras_negativas == -100.0
    assert summary.maior_quebra_positiva == 50.0
    assert summary.maior_quebra_negativa == -100.0


def test_analyze_batch_operadores_criticos():
    service = CashBreakService()

    closures = [
        {"caixaCodigo": 1, "empresaCodigo": 11495, "dataFechamento": "2026-07-25",
         "valorEsperado": 5000, "valorInformado": 4800, "operadorCodigo": 501, "operadorNome": "João"},
        {"caixaCodigo": 2, "empresaCodigo": 11495, "dataFechamento": "2026-07-25",
         "valorEsperado": 6000, "valorInformado": 6000, "operadorCodigo": 502, "operadorNome": "Maria"},
    ]

    summary = service.analyze_batch(closures, "2026-07-25", "2026-07-25")

    assert "João" in summary.operadores_com_quebra_critica
    assert "Maria" not in summary.operadores_com_quebra_critica


def test_overall_status_critico():
    service = CashBreakService()

    closures = [
        {"caixaCodigo": 1, "empresaCodigo": 11495, "dataFechamento": "2026-07-25",
         "valorEsperado": 5000, "valorInformado": 4700},
    ]

    summary = service.analyze_batch(closures, "2026-07-25", "2026-07-25")

    assert summary.overall_status == CashBreakSeverity.CRITICO


def test_overall_status_warning():
    service = CashBreakService()

    closures = [
        {"caixaCodigo": 1, "empresaCodigo": 11495, "dataFechamento": "2026-07-25",
         "valorEsperado": 5000, "valorInformado": 4950},
    ]

    summary = service.analyze_batch(closures, "2026-07-25", "2026-07-25")

    assert summary.overall_status == CashBreakSeverity.WARNING


def test_requires_investigation():
    service = CashBreakService()

    closures_critico = [
        {"caixaCodigo": 1, "empresaCodigo": 11495, "dataFechamento": "2026-07-25",
         "valorEsperado": 5000, "valorInformado": 4700},
    ]
    summary_critico = service.analyze_batch(closures_critico, "2026-07-25", "2026-07-25")

    closures_ok = [
        {"caixaCodigo": 1, "empresaCodigo": 11495, "dataFechamento": "2026-07-25",
         "valorEsperado": 5000, "valorInformado": 5000},
    ]
    summary_ok = service.analyze_batch(closures_ok, "2026-07-25", "2026-07-25")

    assert service.requires_investigation(summary_critico) is True
    assert service.requires_investigation(summary_ok) is False


def test_calculate_risk_score():
    service = CashBreakService()

    closures_high_risk = [
        {"caixaCodigo": 1, "empresaCodigo": 11495, "dataFechamento": "2026-07-25",
         "valorEsperado": 5000, "valorInformado": 4700},
        {"caixaCodigo": 2, "empresaCodigo": 11495, "dataFechamento": "2026-07-25",
         "valorEsperado": 6000, "valorInformado": 5700},
    ]
    summary_high = service.analyze_batch(closures_high_risk, "2026-07-25", "2026-07-25")

    closures_low_risk = [
        {"caixaCodigo": 1, "empresaCodigo": 11495, "dataFechamento": "2026-07-25",
         "valorEsperado": 5000, "valorInformado": 5000},
        {"caixaCodigo": 2, "empresaCodigo": 11495, "dataFechamento": "2026-07-25",
         "valorEsperado": 6000, "valorInformado": 6000},
    ]
    summary_low = service.analyze_batch(closures_low_risk, "2026-07-25", "2026-07-25")

    assert service.calculate_risk_score(summary_high) > service.calculate_risk_score(summary_low)
    assert service.calculate_risk_score(summary_low) == 0
