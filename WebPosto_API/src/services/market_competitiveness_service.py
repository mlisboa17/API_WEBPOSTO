"""Sprint 55 — Market Competitiveness Service: precificação regional, spread e alerta de squeeze.

Motor 100% dinâmico - preços e custos lidos de CompanySettings.
"""
from __future__ import annotations
import logging
from typing import Any, List, Dict, Optional
from statistics import mean
from datetime import datetime, timedelta, timezone

from src.interfaces.http.schemas.executive_market_schema import (
    MarketBenchmarkSummary,
    ProductBenchmark,
    CompetitorPrice,
)
from src.services.company_settings_service import (
    CompanySettingsService,
    get_company_settings_service,
)

logger = logging.getLogger(__name__)


class MarketCompetitivenessService:
    """
    Consolida preços de concorrentes e calcula spread competitivo para cada produto.
    Alerta squeeze quando margem do posto cai abaixo do limite configurado.
    
    100% dinâmico - lê preços e custos das configurações da empresa.
    """

    def __init__(
        self,
        repository: Any | None = None,
        settings_service: CompanySettingsService | None = None,
    ) -> None:
        self._repo = repository
        self._settings = settings_service or get_company_settings_service()
        self._competitor_cache: Dict[int, List[Dict[str, Any]]] = {}

    def _get_sample_competitors(self, empresa_codigo: int) -> List[Dict[str, Any]]:
        """
        Retorna preços de concorrentes (mock ou do repositório quando integrado).
        Usa os produtos configurados para a empresa.
        """
        if empresa_codigo in self._competitor_cache:
            return self._competitor_cache[empresa_codigo]
        
        settings = self._settings.get_settings(empresa_codigo)
        pricing = self._settings.get_all_products_pricing(empresa_codigo)
        
        competitors = []
        competitor_names = ["Posto Sol", "Posto Norte", "Posto Sul", "Posto Leste"]
        
        for produto in settings.produtos:
            if not produto.ativo:
                continue
            
            produto_pricing = pricing.get(produto.codigo)
            if not produto_pricing:
                continue
            
            base_price = produto_pricing.preco_venda_rs
            
            for name in competitor_names:
                variation = (hash(f"{name}{produto.codigo}") % 20 - 10) / 100
                competitor_price = round(base_price * (1 + variation), 2)
                
                competitors.append({
                    "concorrente": name,
                    "produto": produto.codigo,
                    "preco": competitor_price,
                    "produto_nome": produto.nome,
                    "empresa_codigo": empresa_codigo,
                })
        
        self._competitor_cache[empresa_codigo] = competitors
        return competitors

    def _get_company_prices(self, empresa_codigo: int) -> Dict[str, float]:
        """Retorna preços de venda da empresa (dinâmico)."""
        pricing = self._settings.get_all_products_pricing(empresa_codigo)
        return {code: p.preco_venda_rs for code, p in pricing.items()}

    def _get_company_costs(self, empresa_codigo: int) -> Dict[str, float]:
        """Retorna custos de aquisição da empresa (dinâmico)."""
        pricing = self._settings.get_all_products_pricing(empresa_codigo)
        return {code: p.custo_aquisicao_rs for code, p in pricing.items()}

    def _get_margin_limits(self, empresa_codigo: int) -> Dict[str, float]:
        """Retorna limites de margem por produto (dinâmico)."""
        settings = self._settings.get_settings(empresa_codigo)
        return {p.codigo: p.margem_minima_pct for p in settings.produtos if p.ativo}

    def get_benchmark(
        self,
        unidade_codigo: Optional[int] = None,
        margem_minima_pct: float | None = None,
    ) -> MarketBenchmarkSummary:
        """
        Calcula benchmark de mercado para a empresa.
        
        Args:
            unidade_codigo: Código da empresa/filial (default: primeira cadastrada)
            margem_minima_pct: Margem mínima para squeeze (usa config da empresa se None)
        """
        empresa_codigo = unidade_codigo or 5555
        settings = self._settings.get_settings(empresa_codigo)
        
        if margem_minima_pct is None:
            margem_minima_pct = settings.margem_minima_global_pct
        
        competitors = self._get_sample_competitors(empresa_codigo)
        company_prices = self._get_company_prices(empresa_codigo)
        company_costs = self._get_company_costs(empresa_codigo)
        margin_limits = self._get_margin_limits(empresa_codigo)

        grouped: Dict[str, List[Dict[str, Any]]] = {}
        for c in competitors:
            grouped.setdefault(c["produto"], []).append(c)

        produtos: List[ProductBenchmark] = []
        alertas: List[str] = []
        
        for code, data in grouped.items():
            prices = [d["preco"] for d in data]
            avg_price = round(mean(prices), 2)
            company_price = company_prices.get(code, 0.0)
            cost = company_costs.get(code, 0.0)
            product_margin_limit = margin_limits.get(code, margem_minima_pct)
            
            spread = round(company_price - avg_price, 2)
            margin = round(company_price - cost, 2)
            margin_pct = round((margin / company_price) * 100, 2) if company_price else 0.0
            squeeze = margin_pct < product_margin_limit

            if squeeze:
                alertas.append(
                    f"Squeeze de margem em {data[0]['produto_nome']}: "
                    f"margem {margin_pct:.1f}% abaixo do limite {product_margin_limit:.1f}%"
                )

            produtos.append(ProductBenchmark(
                produto_codigo=code,
                produto_nome=data[0]["produto_nome"],
                preco_lisboa_rs=company_price,
                preco_medio_concorrentes_rs=avg_price,
                preco_minimo_concorrentes_rs=round(min(prices), 2),
                preco_maximo_concorrentes_rs=round(max(prices), 2),
                spread_rs=spread,
                margem_lisboa_rs=margin,
                squeeze_risk=squeeze,
            ))

        return MarketBenchmarkSummary(
            produtos=produtos,
            margem_minima_configurada_pct=margem_minima_pct,
            alertas_squeeze=alertas,
        )

    def list_competitor_prices(
        self,
        empresa_codigo: int | None = None,
        produto_codigo: Optional[str] = None,
        limit: int = 100,
    ) -> List[CompetitorPrice]:
        """Lista preços de concorrentes (mock ou do repositório)."""
        empresa_codigo = empresa_codigo or 5555
        competitors = self._get_sample_competitors(empresa_codigo)
        
        prices: List[CompetitorPrice] = []
        for i, c in enumerate(competitors[:limit]):
            if produto_codigo and c["produto"] != produto_codigo:
                continue
            prices.append(CompetitorPrice(
                id=i + 1,
                concorrente_nome=c["concorrente"],
                produto_codigo=c["produto"],
                produto_nome=c["produto_nome"],
                preco_venda_rs=c["preco"],
                datahora=(datetime.now(timezone.utc) - timedelta(days=1)).isoformat(),
            ))
        return prices

    def register_competitor_price(
        self,
        payload: Dict[str, Any],
        empresa_codigo: int | None = None,
    ) -> CompetitorPrice:
        """Registra preço de concorrente (mock - persistir via repository)."""
        empresa_codigo = empresa_codigo or 5555
        
        if empresa_codigo in self._competitor_cache:
            self._competitor_cache[empresa_codigo].append({
                "concorrente": payload.get("concorrente_nome", ""),
                "produto": payload.get("produto_codigo", ""),
                "preco": payload.get("preco_venda_rs", 0.0),
                "produto_nome": payload.get("produto_nome", ""),
                "empresa_codigo": empresa_codigo,
            })
        
        return CompetitorPrice(id=999, **payload)
    
    def clear_cache(self, empresa_codigo: int | None = None) -> None:
        """Limpa cache de concorrentes."""
        if empresa_codigo:
            self._competitor_cache.pop(empresa_codigo, None)
        else:
            self._competitor_cache.clear()
