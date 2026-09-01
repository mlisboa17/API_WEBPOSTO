"""Testes de recomendação de compras — Sprint 47."""

from src.services.purchase_recommendation_service import (
    PurchaseRecommendationService,
    PurchaseRecommendation,
    PurchaseRecommendationSummary,
    UrgencyLevel,
)
from src.services.convenience_analytics_service import ABCClassification


def test_calculate_reorder_point():
    service = PurchaseRecommendationService(default_lead_time=3, safety_stock_days=7)

    reorder_point = service.calculate_reorder_point(venda_media_diaria=10.0)

    assert reorder_point == 100.0


def test_calculate_order_quantity():
    service = PurchaseRecommendationService()

    quantity = service.calculate_order_quantity(
        venda_media_diaria=10.0,
        estoque_atual=50.0,
        target_days=30,
    )

    assert quantity == 250.0


def test_recommend_immediate_rupture():
    service = PurchaseRecommendationService()

    rec = service.recommend(
        produto_codigo=1001,
        produto_nome="Energético Red Bull",
        estoque_atual=0,
        venda_media_diaria=5.0,
        classificacao_abc=ABCClassification.A,
        custo_unitario=8.50,
    )

    assert rec is not None
    assert rec.urgencia == UrgencyLevel.IMEDIATO
    assert "ruptura" in rec.justificativa.lower()
    assert rec.quantidade_sugerida > 0


def test_recommend_urgent_low_coverage():
    service = PurchaseRecommendationService(default_lead_time=5)

    rec = service.recommend(
        produto_codigo=1002,
        produto_nome="Água Mineral 500ml",
        estoque_atual=5.0,
        venda_media_diaria=5.0,
        classificacao_abc=ABCClassification.A,
        custo_unitario=2.50,
    )

    assert rec is not None
    assert rec.dias_cobertura_atual == 1.0
    assert rec.urgencia == UrgencyLevel.IMEDIATO


def test_recommend_normal_reorder():
    service = PurchaseRecommendationService(default_lead_time=3, safety_stock_days=7)

    rec = service.recommend(
        produto_codigo=1003,
        produto_nome="Chocolate Snickers",
        estoque_atual=30.0,
        venda_media_diaria=5.0,
        classificacao_abc=ABCClassification.B,
        custo_unitario=4.00,
    )

    assert rec is not None
    assert rec.dias_cobertura_atual == 6.0
    assert rec.urgencia == UrgencyLevel.NORMAL


def test_recommend_no_recommendation_for_c_with_stock():
    service = PurchaseRecommendationService()

    rec = service.recommend(
        produto_codigo=1004,
        produto_nome="Revista Velha",
        estoque_atual=500.0,
        venda_media_diaria=0.5,
        classificacao_abc=ABCClassification.C,
        custo_unitario=10.00,
    )

    assert rec is None


def test_recommend_no_recommendation_without_sales():
    service = PurchaseRecommendationService()

    rec = service.recommend(
        produto_codigo=1005,
        produto_nome="Produto Sem Venda",
        estoque_atual=100.0,
        venda_media_diaria=0,
        classificacao_abc=ABCClassification.C,
    )

    assert rec is None


def test_recommend_batch():
    service = PurchaseRecommendationService()

    products = [
        {
            "produtoCodigo": 1001,
            "produtoNome": "Energético",
            "estoqueAtual": 0,
            "vendaMediaDiaria": 10,
            "classificacaoAbc": "A",
            "precoCusto": 8.50,
        },
        {
            "produtoCodigo": 1002,
            "produtoNome": "Água",
            "estoqueAtual": 50,
            "vendaMediaDiaria": 20,
            "classificacaoAbc": "A",
            "precoCusto": 2.00,
        },
        {
            "produtoCodigo": 1003,
            "produtoNome": "Chiclete",
            "estoqueAtual": 100,
            "vendaMediaDiaria": 5,
            "classificacaoAbc": "C",
        },
    ]

    summary = service.recommend_batch(products)

    assert isinstance(summary, PurchaseRecommendationSummary)
    assert summary.total_recomendacoes >= 2
    assert summary.recomendacoes_urgentes >= 1
    assert summary.valor_total_estimado > 0


def test_priority_score_curva_a_higher():
    service = PurchaseRecommendationService()

    rec_a = service.recommend(
        produto_codigo=1,
        produto_nome="Curva A",
        estoque_atual=5,
        venda_media_diaria=10,
        classificacao_abc=ABCClassification.A,
    )

    rec_c = service.recommend(
        produto_codigo=2,
        produto_nome="Curva C",
        estoque_atual=5,
        venda_media_diaria=10,
        classificacao_abc=ABCClassification.C,
    )

    assert rec_a is not None
    assert rec_c is not None
    assert rec_a.prioridade_score > rec_c.prioridade_score


def test_order_quantity_respects_minimum():
    service = PurchaseRecommendationService()

    rec = service.recommend(
        produto_codigo=1006,
        produto_nome="Produto com Mínimo",
        estoque_atual=295,
        venda_media_diaria=1,
        classificacao_abc=ABCClassification.B,
        quantidade_minima=12.0,
    )

    assert rec is not None
    assert rec.quantidade_sugerida >= 12.0


def test_valor_pedido_calculado_corretamente():
    service = PurchaseRecommendationService()

    rec = service.recommend(
        produto_codigo=1007,
        produto_nome="Produto com Custo",
        estoque_atual=0,
        venda_media_diaria=10,
        classificacao_abc=ABCClassification.A,
        custo_unitario=5.00,
    )

    assert rec is not None
    assert rec.valor_pedido_estimado is not None
    assert rec.valor_pedido_estimado == rec.quantidade_sugerida * 5.00
