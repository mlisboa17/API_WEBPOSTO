"""Testes de analytics de conveniência — Curva ABC, ruptura, capital parado — Sprint 46."""

from src.services.convenience_analytics_service import (
    ConvenienceAnalyticsService,
    ABCClassification,
    StockStatus,
    ProductABC,
    ABCCurveSummary,
    StockBreakSummary,
    IdleStockSummary,
)


def test_calculate_abc_curve_classifies_correctly():
    service = ConvenienceAnalyticsService()

    products = [
        {"produtoCodigo": 1, "produtoNome": "Produto A1", "faturamento": 50000, "custo": 30000, "quantidade": 1000, "estoqueAtual": 100},
        {"produtoCodigo": 2, "produtoNome": "Produto A2", "faturamento": 30000, "custo": 18000, "quantidade": 600, "estoqueAtual": 80},
        {"produtoCodigo": 3, "produtoNome": "Produto B1", "faturamento": 10000, "custo": 6000, "quantidade": 200, "estoqueAtual": 50},
        {"produtoCodigo": 4, "produtoNome": "Produto B2", "faturamento": 5000, "custo": 3000, "quantidade": 100, "estoqueAtual": 40},
        {"produtoCodigo": 5, "produtoNome": "Produto C1", "faturamento": 3000, "custo": 1800, "quantidade": 60, "estoqueAtual": 30},
        {"produtoCodigo": 6, "produtoNome": "Produto C2", "faturamento": 2000, "custo": 1200, "quantidade": 40, "estoqueAtual": 20},
    ]

    summary = service.calculate_abc_curve(products, "2026-07-01", "2026-07-25")

    assert isinstance(summary, ABCCurveSummary)
    assert summary.total_produtos == 6
    assert summary.total_faturamento == 100000.0

    a_products = [p for p in summary.produtos if p.classificacao == ABCClassification.A]
    b_products = [p for p in summary.produtos if p.classificacao == ABCClassification.B]
    c_products = [p for p in summary.produtos if p.classificacao == ABCClassification.C]

    assert len(a_products) == 2
    assert len(b_products) == 2
    assert len(c_products) == 2

    assert summary.faturamento_a_pct == 80.0


def test_abc_curve_calculates_margin():
    service = ConvenienceAnalyticsService()

    products = [
        {"produtoCodigo": 1, "produtoNome": "Produto 1", "faturamento": 10000, "custo": 6000, "quantidade": 100},
    ]

    summary = service.calculate_abc_curve(products, "2026-07-01", "2026-07-25")

    assert summary.total_margem == 4000.0
    assert summary.produtos[0].margem_contribuicao == 4000.0
    assert summary.produtos[0].margem_pct == 40.0


def test_abc_curve_calculates_days_coverage():
    service = ConvenienceAnalyticsService()

    products = [
        {
            "produtoCodigo": 1,
            "produtoNome": "Produto 1",
            "faturamento": 10000,
            "custo": 6000,
            "quantidade": 100,
            "estoqueAtual": 20,
            "vendaMediaDiaria": 5.0,
        },
    ]

    summary = service.calculate_abc_curve(products, "2026-07-01", "2026-07-25")

    assert summary.produtos[0].dias_cobertura == 4.0
    assert summary.produtos[0].status_estoque == StockStatus.NORMAL


def test_abc_curve_detects_rupture():
    service = ConvenienceAnalyticsService()

    products = [
        {
            "produtoCodigo": 1,
            "produtoNome": "Produto em Ruptura",
            "faturamento": 50000,
            "custo": 30000,
            "quantidade": 1000,
            "estoqueAtual": 0,
        },
    ]

    summary = service.calculate_abc_curve(products, "2026-07-01", "2026-07-25")

    assert summary.produtos[0].status_estoque == StockStatus.RUPTURA


def test_abc_curve_detects_critical_stock():
    service = ConvenienceAnalyticsService(default_lead_time=5)

    products = [
        {
            "produtoCodigo": 1,
            "produtoNome": "Produto Crítico",
            "faturamento": 50000,
            "custo": 30000,
            "quantidade": 1000,
            "estoqueAtual": 10,
            "vendaMediaDiaria": 10.0,
        },
    ]

    summary = service.calculate_abc_curve(products, "2026-07-01", "2026-07-25")

    assert summary.produtos[0].dias_cobertura == 1.0
    assert summary.produtos[0].status_estoque == StockStatus.CRITICO


def test_detect_stock_breaks():
    service = ConvenienceAnalyticsService()

    products = [
        {"produtoCodigo": 1, "produtoNome": "Produto A em Ruptura", "faturamento": 50000, "custo": 30000, "quantidade": 1000, "estoqueAtual": 0, "vendaMediaDiaria": 50},
        {"produtoCodigo": 2, "produtoNome": "Produto A Crítico", "faturamento": 30000, "custo": 18000, "quantidade": 600, "estoqueAtual": 5, "vendaMediaDiaria": 10},
        {"produtoCodigo": 3, "produtoNome": "Produto B Normal", "faturamento": 10000, "custo": 6000, "quantidade": 200, "estoqueAtual": 100, "vendaMediaDiaria": 5},
    ]

    abc_curve = service.calculate_abc_curve(products, "2026-07-01", "2026-07-25")
    breaks = service.detect_stock_breaks(abc_curve, "2026-07-25")

    assert isinstance(breaks, StockBreakSummary)
    assert breaks.total_rupturas >= 1
    assert breaks.rupturas_curva_a >= 1
    assert breaks.alert_level == "CRITICAL"
    assert len(breaks.items) >= 2


def test_detect_stock_breaks_calculates_loss():
    service = ConvenienceAnalyticsService()

    products = [
        {
            "produtoCodigo": 1,
            "produtoNome": "Produto A Ruptura",
            "faturamento": 10000,
            "custo": 6000,
            "quantidade": 100,
            "estoqueAtual": 0,
            "vendaMediaDiaria": 10.0,
        },
    ]

    abc_curve = service.calculate_abc_curve(products, "2026-07-01", "2026-07-25")
    breaks = service.detect_stock_breaks(abc_curve, "2026-07-25")

    assert breaks.perda_estimada_dia > 0
    assert breaks.items[0].perda_estimada_dia is not None


def test_detect_idle_stock():
    service = ConvenienceAnalyticsService()

    products = [
        {
            "produtoCodigo": 1,
            "produtoNome": "Produto Parado 45 dias",
            "estoqueAtual": 50,
            "precoCusto": 10.0,
            "diasSemVenda": 45,
            "ultimaVenda": "2026-06-10",
            "classificacaoAbc": "C",
        },
        {
            "produtoCodigo": 2,
            "produtoNome": "Produto Parado 70 dias",
            "estoqueAtual": 30,
            "precoCusto": 15.0,
            "diasSemVenda": 70,
            "ultimaVenda": "2026-05-16",
            "classificacaoAbc": "C",
        },
        {
            "produtoCodigo": 3,
            "produtoNome": "Produto Normal",
            "estoqueAtual": 100,
            "precoCusto": 5.0,
            "diasSemVenda": 10,
            "classificacaoAbc": "B",
        },
    ]

    summary = service.detect_idle_stock(products, "2026-07-25")

    assert isinstance(summary, IdleStockSummary)
    assert summary.total_itens_parados == 2
    assert summary.capital_parado_30_dias == 500.0
    assert summary.capital_parado_60_dias == 450.0
    assert summary.capital_parado_total == 950.0


def test_detect_idle_stock_suggests_actions():
    service = ConvenienceAnalyticsService()

    products = [
        {
            "produtoCodigo": 1,
            "produtoNome": "Produto Parado 90 dias",
            "estoqueAtual": 100,
            "precoCusto": 20.0,
            "diasSemVenda": 90,
            "classificacaoAbc": "C",
        },
    ]

    summary = service.detect_idle_stock(products, "2026-07-25")

    assert summary.items[0].acao_sugerida == "DEVOLUÇÃO ou QUEIMA"
    assert summary.items[0].prioridade == "ALTA"


def test_custom_abc_thresholds():
    service = ConvenienceAnalyticsService(a_threshold=70.0, b_threshold=90.0)

    products = [
        {"produtoCodigo": 1, "produtoNome": "P1", "faturamento": 70000, "custo": 42000, "quantidade": 100},
        {"produtoCodigo": 2, "produtoNome": "P2", "faturamento": 20000, "custo": 12000, "quantidade": 50},
        {"produtoCodigo": 3, "produtoNome": "P3", "faturamento": 10000, "custo": 6000, "quantidade": 25},
    ]

    summary = service.calculate_abc_curve(products, "2026-07-01", "2026-07-25")

    a_count = sum(1 for p in summary.produtos if p.classificacao == ABCClassification.A)
    assert a_count == 1
    assert summary.produtos[0].faturamento_acumulado_pct == 70.0


def test_product_requires_action_flag():
    service = ConvenienceAnalyticsService()

    products = [
        {
            "produtoCodigo": 1,
            "produtoNome": "Produto A em Ruptura",
            "faturamento": 60000,
            "custo": 36000,
            "quantidade": 1000,
            "estoqueAtual": 0,
        },
        {
            "produtoCodigo": 2,
            "produtoNome": "Produto A2",
            "faturamento": 20000,
            "custo": 12000,
            "quantidade": 400,
            "estoqueAtual": 100,
        },
        {
            "produtoCodigo": 3,
            "produtoNome": "Produto B",
            "faturamento": 12000,
            "custo": 7200,
            "quantidade": 200,
            "estoqueAtual": 50,
        },
        {
            "produtoCodigo": 4,
            "produtoNome": "Produto C",
            "faturamento": 8000,
            "custo": 4800,
            "quantidade": 100,
            "estoqueAtual": 30,
        },
    ]

    summary = service.calculate_abc_curve(products, "2026-07-01", "2026-07-25")

    produto_a = summary.produtos[0]
    assert produto_a.faturamento == 60000.0
    assert produto_a.classificacao == ABCClassification.A
    assert produto_a.is_rupture_risk is True
    assert produto_a.requires_action is True
