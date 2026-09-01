"""Testes de ciclo de caixa e vácuo financeiro — Sprint 48."""

from src.services.cash_cycle_service import (
    CashCycleService,
    CashCycleAnalysis,
    CashCycleStatus,
    PaymentMethodTiming,
    DEFAULT_RECEIVABLE_DAYS,
)


def test_calculate_receivable_timing_credito_only():
    service = CashCycleService()

    prazo, breakdown = service.calculate_receivable_timing({"CREDITO": 100000.0})

    assert prazo == 30.0
    assert len(breakdown) == 1
    assert breakdown[0].method == "CREDITO"
    assert breakdown[0].days_to_receive == 30


def test_calculate_receivable_timing_mixed():
    service = CashCycleService()

    sales = {
        "CREDITO": 50000.0,
        "DEBITO": 30000.0,
        "PIX": 20000.0,
    }
    total = sum(sales.values())

    prazo, breakdown = service.calculate_receivable_timing(sales)

    expected = (50000 * 30 + 30000 * 1 + 20000 * 0) / total
    assert abs(prazo - expected) < 0.1
    assert len(breakdown) == 3


def test_calculate_payable_timing_default():
    service = CashCycleService(fuel_payment_days=3)

    prazo, breakdown = service.calculate_payable_timing()

    assert prazo == 3.0
    assert len(breakdown) == 1
    assert breakdown[0].supplier_type == "COMBUSTIVEL"


def test_analyze_positive_vacuum():
    service = CashCycleService(fuel_payment_days=3)

    sales = {"CREDITO": 100000.0}
    total_revenue = 100000.0
    days = 10

    analysis = service.analyze(
        period_start="2026-07-01",
        period_end="2026-07-10",
        sales_by_method=sales,
        total_revenue=total_revenue,
        days_in_period=days,
    )

    assert analysis.prazo_medio_recebimento_dias == 30.0
    assert analysis.prazo_medio_pagamento_dias == 3.0
    assert analysis.vacuo_financeiro_dias == 27.0
    assert analysis.faturamento_diario_medio == 10000.0
    assert analysis.necessidade_capital_giro_rs == 270000.0


def test_analyze_negative_vacuum_healthy():
    service = CashCycleService()

    sales = {"PIX": 50000.0, "DINHEIRO": 50000.0}
    total_revenue = 100000.0
    days = 10

    analysis = service.analyze(
        period_start="2026-07-01",
        period_end="2026-07-10",
        sales_by_method=sales,
        total_revenue=total_revenue,
        days_in_period=days,
        purchases_by_type={"COMBUSTIVEL": 80000.0},
    )

    assert analysis.vacuo_financeiro_dias < 0
    assert analysis.necessidade_capital_giro_rs == 0
    assert analysis.status == CashCycleStatus.SAUDAVEL


def test_analyze_status_atencao():
    service = CashCycleService(fuel_payment_days=20)

    sales = {"CREDITO": 80000.0, "PIX": 20000.0}
    total_revenue = 100000.0
    days = 10

    analysis = service.analyze(
        period_start="2026-07-01",
        period_end="2026-07-10",
        sales_by_method=sales,
        total_revenue=total_revenue,
        days_in_period=days,
    )

    assert analysis.status == CashCycleStatus.ATENCAO
    assert analysis.alert_message is not None


def test_analyze_status_critico():
    service = CashCycleService(fuel_payment_days=1)

    sales = {"CREDITO": 100000.0}
    total_revenue = 100000.0
    days = 10

    analysis = service.analyze(
        period_start="2026-07-01",
        period_end="2026-07-10",
        sales_by_method=sales,
        total_revenue=total_revenue,
        days_in_period=days,
    )

    assert analysis.vacuo_financeiro_dias > 15
    assert analysis.status == CashCycleStatus.CRITICO


def test_simulate_antecipation():
    service = CashCycleService(taxa_antecipacao_pct=1.5)

    result = service.simulate_antecipation(
        valor_recebivel=100000.0,
        dias_antecipacao=30,
    )

    assert result["valor_bruto"] == 100000.0
    assert result["dias_antecipacao"] == 30
    assert result["custo_antecipacao"] == 1500.0
    assert result["valor_liquido"] == 98500.0


def test_simulate_antecipation_custom_rate():
    service = CashCycleService()

    result = service.simulate_antecipation(
        valor_recebivel=50000.0,
        dias_antecipacao=15,
        taxa_mensal_pct=2.0,
    )

    expected_cost = 50000 * (2.0 / 30 / 100) * 15
    assert abs(result["custo_antecipacao"] - expected_cost) < 0.01


def test_custo_oportunidade_calculated():
    service = CashCycleService(taxa_antecipacao_pct=1.5)

    analysis = service.analyze(
        period_start="2026-07-01",
        period_end="2026-07-10",
        sales_by_method={"CREDITO": 100000.0},
        total_revenue=100000.0,
        days_in_period=10,
    )

    assert analysis.custo_oportunidade_rs > 0
    assert analysis.custo_oportunidade_mensal_pct == 1.5
