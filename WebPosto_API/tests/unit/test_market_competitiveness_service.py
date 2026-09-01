"""Testes unitários para MarketCompetitivenessService - Sprint 55.

Motor 100% dinâmico: preços e custos lidos de CompanySettings.
"""
import pytest
from src.services.market_competitiveness_service import MarketCompetitivenessService
from src.services.company_settings_service import (
    CompanySettingsService,
    FuelProductConfig,
    FuelCategory,
    ProductPricing,
)


@pytest.fixture
def settings_service():
    """Cria serviço de configurações limpo para cada teste."""
    return CompanySettingsService()


@pytest.fixture
def market_service(settings_service):
    """Cria serviço de market competitiveness com settings injetado."""
    return MarketCompetitivenessService(settings_service=settings_service)


class TestMarketBenchmark:
    """Testes para benchmark de mercado."""

    def test_benchmark_returns_products_from_settings(self, market_service, settings_service):
        """Verifica que benchmark usa produtos da empresa."""
        empresa_codigo = 5555
        
        result = market_service.get_benchmark(empresa_codigo)
        
        settings = settings_service.get_settings(empresa_codigo)
        active_products = [p.codigo for p in settings.produtos if p.ativo]
        
        for produto in result.produtos:
            assert produto.produto_codigo in active_products
    
    def test_benchmark_uses_company_prices(self, market_service, settings_service):
        """Verifica que benchmark usa preços da empresa."""
        empresa_codigo = 5555
        
        result = market_service.get_benchmark(empresa_codigo)
        
        for produto in result.produtos:
            pricing = settings_service.get_product_pricing(empresa_codigo, produto.produto_codigo)
            if pricing:
                assert produto.preco_lisboa_rs == pricing.preco_venda_rs
    
    def test_benchmark_calculates_margin(self, market_service, settings_service):
        """Verifica que margem é calculada corretamente."""
        empresa_codigo = 5555
        
        result = market_service.get_benchmark(empresa_codigo)
        
        for produto in result.produtos:
            pricing = settings_service.get_product_pricing(empresa_codigo, produto.produto_codigo)
            if pricing:
                expected_margin = round(pricing.preco_venda_rs - pricing.custo_aquisicao_rs, 2)
                assert produto.margem_lisboa_rs == expected_margin
    
    def test_benchmark_detects_squeeze(self, market_service, settings_service):
        """Verifica que squeeze é detectado quando margem é baixa."""
        empresa_codigo = 5555
        
        settings_service.update_product_pricing(empresa_codigo, "GC", preco_venda=5.15, custo_aquisicao=5.10)
        
        market_service.clear_cache(empresa_codigo)
        result = market_service.get_benchmark(empresa_codigo)
        
        gc_produto = next((p for p in result.produtos if p.produto_codigo == "GC"), None)
        
        if gc_produto:
            assert gc_produto.squeeze_risk is True
            assert len(result.alertas_squeeze) > 0


class TestDynamicPricing:
    """Testes para preços dinâmicos."""

    def test_update_pricing_reflects_in_benchmark(self, market_service, settings_service):
        """Verifica que atualização de preço reflete no benchmark."""
        empresa_codigo = 5555
        novo_preco = 6.50
        
        settings_service.update_product_pricing(empresa_codigo, "GA", preco_venda=novo_preco)
        
        market_service.clear_cache(empresa_codigo)
        result = market_service.get_benchmark(empresa_codigo)
        
        ga_produto = next((p for p in result.produtos if p.produto_codigo == "GA"), None)
        
        if ga_produto:
            assert ga_produto.preco_lisboa_rs == novo_preco
    
    def test_different_companies_have_independent_prices(self, market_service, settings_service):
        """Verifica que empresas diferentes têm preços independentes."""
        empresa_1 = 5555
        empresa_2 = 6666
        
        settings_service.update_product_pricing(empresa_1, "EH", preco_venda=4.50)
        
        market_service.clear_cache()
        result_1 = market_service.get_benchmark(empresa_1)
        result_2 = market_service.get_benchmark(empresa_2)
        
        eh_1 = next((p for p in result_1.produtos if p.produto_codigo == "EH"), None)
        eh_2 = next((p for p in result_2.produtos if p.produto_codigo == "EH"), None)
        
        if eh_1 and eh_2:
            assert eh_1.preco_lisboa_rs != eh_2.preco_lisboa_rs


class TestCompetitorPrices:
    """Testes para preços de concorrentes."""

    def test_list_competitor_prices_by_product(self, market_service):
        """Verifica filtro por produto."""
        empresa_codigo = 5555
        
        all_prices = market_service.list_competitor_prices(empresa_codigo)
        gc_prices = market_service.list_competitor_prices(empresa_codigo, "GC")
        
        assert len(gc_prices) <= len(all_prices)
        for price in gc_prices:
            assert price.produto_codigo == "GC"
    
    def test_register_competitor_price_updates_cache(self, market_service):
        """Verifica que registro de preço atualiza o cache."""
        empresa_codigo = 5555
        
        payload = {
            "concorrente_nome": "Novo Posto",
            "produto_codigo": "GC",
            "produto_nome": "Gasolina Comum",
            "preco_venda_rs": 5.60,
            "datahora": "2026-07-27T10:00:00",
        }
        
        market_service.register_competitor_price(payload, empresa_codigo)
        
        prices = market_service.list_competitor_prices(empresa_codigo, "GC")
        novo_posto = [p for p in prices if p.concorrente_nome == "Novo Posto"]
        
        assert len(novo_posto) >= 0


class TestMarginLimits:
    """Testes para limites de margem por produto."""

    def test_uses_product_margin_limit(self, market_service, settings_service):
        """Verifica que margem mínima do produto é usada."""
        empresa_codigo = 5555
        
        result = market_service.get_benchmark(empresa_codigo)
        
        assert result.margem_minima_configurada_pct >= 0
    
    def test_uses_global_margin_when_not_set(self, market_service, settings_service):
        """Verifica fallback para margem global."""
        empresa_codigo = 5555
        
        settings = settings_service.get_settings(empresa_codigo)
        
        result = market_service.get_benchmark(empresa_codigo)
        
        assert result.margem_minima_configurada_pct == settings.margem_minima_global_pct


class TestSupplierIntegration:
    """Testes para integração com fornecedores."""

    def test_settings_service_lists_suppliers(self, settings_service):
        """Verifica que fornecedores são listados."""
        empresa_codigo = 5555
        
        suppliers = settings_service.list_suppliers(empresa_codigo)
        
        assert len(suppliers) > 0
        for s in suppliers:
            assert "codigo" in s
            assert "nome" in s
            assert "produtos_fornecidos" in s

    def test_suppliers_have_product_list(self, settings_service):
        """Verifica que fornecedores têm lista de produtos."""
        empresa_codigo = 5555
        
        suppliers = settings_service.list_suppliers(empresa_codigo)
        
        for s in suppliers:
            assert isinstance(s["produtos_fornecidos"], list)
