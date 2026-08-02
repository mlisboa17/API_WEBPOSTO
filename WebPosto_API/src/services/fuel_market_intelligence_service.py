"""Servico de Inteligencia de Mercado para Combustiveis.

Sprint 59-B: Motor 100% dinamico e configuravel por empresa/fornecedor.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime
from typing import Any

from src.services.company_settings_service import (
    CompanySettingsService,
    FuelCategory,
    FuelProductConfig,
    SupplierConfig,
    get_company_settings_service,
)


@dataclass
class FuelPriceAnalysis:
    """Analise de preco de combustivel."""
    
    produto_codigo: str
    produto_nome: str
    categoria: str
    
    preco_base: float = 0.0
    preco_ajustado: float = 0.0
    
    fator_sazonalidade: float = 1.0
    fator_mercado: float = 1.0
    fator_total: float = 1.0
    
    fornecedor_nome: str = ""
    terminal: str = ""
    regiao: str = ""
    
    periodo_safra: bool = False
    descricao_periodo: str = ""
    
    justificativa: str = ""
    recomendacao: str = ""
    
    data_analise: date = field(default_factory=date.today)


@dataclass
class MarketIndicators:
    """Indicadores de mercado globais."""
    
    brent_usd: float = 80.0
    usd_brl: float = 5.50
    
    esalq_etanol_pe: float = 2.80
    esalq_etanol_al: float = 2.75
    
    data_atualizacao: datetime = field(default_factory=datetime.now)


class FuelMarketIntelligenceService:
    """Motor de inteligencia de mercado 100% dinamico."""
    
    def __init__(self, settings_service: CompanySettingsService | None = None) -> None:
        self._settings = settings_service or get_company_settings_service()
        self._indicators = MarketIndicators()
    
    def update_market_indicators(
        self,
        brent_usd: float | None = None,
        usd_brl: float | None = None,
        esalq_pe: float | None = None,
        esalq_al: float | None = None,
    ) -> MarketIndicators:
        """Atualiza indicadores de mercado."""
        
        if brent_usd is not None:
            self._indicators.brent_usd = brent_usd
        if usd_brl is not None:
            self._indicators.usd_brl = usd_brl
        if esalq_pe is not None:
            self._indicators.esalq_etanol_pe = esalq_pe
        if esalq_al is not None:
            self._indicators.esalq_etanol_al = esalq_al
        
        self._indicators.data_atualizacao = datetime.now()
        return self._indicators
    
    def _is_safra_period(self, produto: FuelProductConfig, regiao: str) -> tuple[bool, str]:
        """Verifica se esta no periodo de safra para o produto/regiao."""
        
        if not produto.sazonalidade_ativa:
            return True, "Produto sem sazonalidade"
        
        today = date.today()
        mes = today.month
        
        safra_inicio = produto.safra_inicio_mes
        safra_fim = produto.safra_fim_mes
        
        if safra_inicio > safra_fim:
            is_safra = mes >= safra_inicio or mes <= safra_fim
        else:
            is_safra = safra_inicio <= mes <= safra_fim
        
        if is_safra:
            return True, f"Periodo de Safra {regiao} (set-mar) - Oferta abundante"
        else:
            return False, f"Periodo de Entresafra {regiao} (abr-ago) - Precos em alta"
    
    def _calculate_market_factor(self, categoria: FuelCategory) -> tuple[float, str]:
        """Calcula fator de mercado baseado em indicadores globais."""
        
        if categoria in [FuelCategory.GASOLINA, FuelCategory.DIESEL]:
            brent_factor = 1.0
            if self._indicators.brent_usd > 85:
                brent_factor = 1.03
            elif self._indicators.brent_usd < 70:
                brent_factor = 0.97
            
            fx_factor = 1.0
            if self._indicators.usd_brl > 5.80:
                fx_factor = 1.02
            elif self._indicators.usd_brl < 5.20:
                fx_factor = 0.98
            
            total = brent_factor * fx_factor
            justificativa = f"Brent: USD {self._indicators.brent_usd:.2f}/bbl | Cambio: R$ {self._indicators.usd_brl:.2f}"
            
            return total, justificativa
        
        return 1.0, "Sem fator de mercado aplicavel"
    
    def analyze_price(
        self,
        empresa_codigo: int,
        produto_codigo: str,
        fornecedor_codigo: str | None = None,
    ) -> FuelPriceAnalysis:
        """Analisa preco de combustivel para empresa/produto/fornecedor."""
        
        settings = self._settings.get_settings(empresa_codigo)
        produto = self._settings.get_product_config(empresa_codigo, produto_codigo)
        fornecedor = self._settings.get_supplier(empresa_codigo, fornecedor_codigo)
        
        if not produto:
            return FuelPriceAnalysis(
                produto_codigo=produto_codigo,
                produto_nome="Produto nao encontrado",
                categoria="DESCONHECIDO",
                justificativa="Produto nao cadastrado nas configuracoes da empresa",
            )
        
        is_safra, periodo_desc = self._is_safra_period(produto, settings.regiao)
        
        fator_sazonalidade = 1.0
        if not is_safra and produto.sazonalidade_ativa:
            fator_sazonalidade = produto.fator_entresafra
        
        fator_mercado, mercado_desc = self._calculate_market_factor(produto.categoria)
        
        fator_total = fator_sazonalidade * fator_mercado
        preco_ajustado = produto.preco_base * fator_total
        
        justificativas = []
        recomendacoes = []
        
        if fornecedor:
            justificativas.append(f"Fornecedor: {fornecedor.nome} | Terminal: {fornecedor.terminal}")
        
        justificativas.append(f"Periodo: {periodo_desc}")
        
        if fator_sazonalidade > 1:
            justificativas.append(f"Fator sazonalidade: +{(fator_sazonalidade - 1) * 100:.1f}%")
            recomendacoes.append("Antecipar compras ou negociar contratos de fornecimento")
        
        if fator_mercado != 1.0:
            justificativas.append(mercado_desc)
            if fator_mercado > 1:
                recomendacoes.append("Monitorar repasse de custos")
            else:
                recomendacoes.append("Cenario favoravel para margens")
        
        if is_safra and produto.sazonalidade_ativa:
            recomendacoes.append("Negociar volumes maiores com desconto")
        
        return FuelPriceAnalysis(
            produto_codigo=produto.codigo,
            produto_nome=produto.nome,
            categoria=produto.categoria.value,
            preco_base=produto.preco_base,
            preco_ajustado=round(preco_ajustado, 4),
            fator_sazonalidade=fator_sazonalidade,
            fator_mercado=fator_mercado,
            fator_total=fator_total,
            fornecedor_nome=fornecedor.nome if fornecedor else "",
            terminal=fornecedor.terminal if fornecedor else settings.terminal_padrao,
            regiao=settings.regiao,
            periodo_safra=is_safra,
            descricao_periodo=periodo_desc,
            justificativa=" | ".join(justificativas),
            recomendacao=" | ".join(recomendacoes) if recomendacoes else "Sem recomendacoes especificas",
        )
    
    def analyze_all_products(
        self,
        empresa_codigo: int,
        fornecedor_codigo: str | None = None,
    ) -> list[FuelPriceAnalysis]:
        """Analisa todos os produtos cadastrados para a empresa."""
        
        settings = self._settings.get_settings(empresa_codigo)
        
        analyses = []
        for produto in settings.produtos:
            analysis = self.analyze_price(
                empresa_codigo=empresa_codigo,
                produto_codigo=produto.codigo,
                fornecedor_codigo=fornecedor_codigo,
            )
            analyses.append(analysis)
        
        return analyses
    
    def generate_market_alerts(
        self,
        empresa_codigo: int,
    ) -> list[dict[str, Any]]:
        """Gera alertas de mercado para a empresa."""
        
        settings = self._settings.get_settings(empresa_codigo)
        alerts = []
        
        for produto in settings.produtos:
            if not produto.sazonalidade_ativa:
                continue
            
            is_safra, periodo_desc = self._is_safra_period(produto, settings.regiao)
            
            if not is_safra:
                fator = produto.fator_entresafra
                alerts.append({
                    "empresa_codigo": empresa_codigo,
                    "empresa_nome": settings.empresa_nome,
                    "produto_codigo": produto.codigo,
                    "produto_nome": produto.nome,
                    "categoria": produto.categoria.value,
                    "alert_type": "SAZONALIDADE",
                    "severity": "MEDIO",
                    "title": f"Entresafra - {produto.nome}",
                    "description": f"Periodo de entresafra em {settings.regiao}. Precos tendem a subir {(fator - 1) * 100:.0f}% ate setembro.",
                    "justificativa": periodo_desc,
                    "recommended_action": "Antecipar compras ou negociar contratos",
                    "valid_until": date(date.today().year, 9, 1).isoformat(),
                })
        
        analyses = self.analyze_all_products(empresa_codigo)
        
        gasolina_price = None
        etanol_price = None
        
        for a in analyses:
            if a.categoria == "GASOLINA" and "Comum" in a.produto_nome:
                gasolina_price = a.preco_ajustado
            elif a.categoria == "ETANOL" and "Hidratado" in a.produto_nome:
                etanol_price = a.preco_ajustado
        
        if gasolina_price and etanol_price and gasolina_price > 0:
            ratio = etanol_price / gasolina_price
            
            if ratio > 0.70:
                alerts.append({
                    "empresa_codigo": empresa_codigo,
                    "empresa_nome": settings.empresa_nome,
                    "produto_codigo": "EH",
                    "produto_nome": "Etanol Hidratado",
                    "categoria": "ETANOL",
                    "alert_type": "PARIDADE",
                    "severity": "BAIXO",
                    "title": "Paridade Etanol/Gasolina Desfavoravel",
                    "description": f"Ratio atual: {ratio:.1%}. Etanol menos competitivo.",
                    "justificativa": f"Acima do ponto de virada de 70%",
                    "recommended_action": "Revisar margem do etanol e promocoes",
                })
        
        return alerts
    
    def get_supplier_info(
        self,
        empresa_codigo: int,
        fornecedor_codigo: str | None = None,
    ) -> dict[str, Any]:
        """Retorna informacoes do fornecedor da empresa."""
        
        settings = self._settings.get_settings(empresa_codigo)
        fornecedor = self._settings.get_supplier(empresa_codigo, fornecedor_codigo)
        
        if not fornecedor:
            return {
                "empresa_codigo": empresa_codigo,
                "empresa_nome": settings.empresa_nome,
                "fornecedor": None,
                "message": "Nenhum fornecedor cadastrado",
            }
        
        return {
            "empresa_codigo": empresa_codigo,
            "empresa_nome": settings.empresa_nome,
            "fornecedor": {
                "codigo": fornecedor.codigo,
                "nome": fornecedor.nome,
                "terminal": fornecedor.terminal,
                "regiao": fornecedor.regiao,
                "lead_time_horas": fornecedor.lead_time_horas,
                "pedido_minimo_litros": fornecedor.pedido_minimo_litros,
            },
        }
    
    def get_market_indicators(self) -> dict[str, Any]:
        """Retorna indicadores em cache (pode ser stale). Prefira refresh_market_indicators()."""
        
        return {
            "brent_usd": self._indicators.brent_usd,
            "usd_brl": self._indicators.usd_brl,
            "esalq_etanol_pe": self._indicators.esalq_etanol_pe,
            "esalq_etanol_al": self._indicators.esalq_etanol_al,
            "data_atualizacao": self._indicators.data_atualizacao.isoformat(),
            "fonte": "cache_local",
        }

    async def refresh_market_indicators(self, force: bool = False) -> dict[str, Any]:
        """Atualiza indicadores a partir de fontes externas reais."""
        from src.services.external_market_service import get_external_market_service

        external = get_external_market_service()
        live = await external.get_live_indicators(force_refresh=force)

        esalq_pe = live.esalq_etanol_pe.value
        esalq_al = live.esalq_etanol_al.value
        override_source = None

        # Sprint 60: override CompanySettings sobrepõe CEPEA/fallback (ex.: HTTP 403)
        overrides = self._settings.get_esalq_overrides()
        pe_ov = float(overrides.get("esalq_etanol_pe") or 0)
        al_ov = float(overrides.get("esalq_etanol_al") or 0)
        if pe_ov > 0:
            esalq_pe = pe_ov
            override_source = "company_settings_override"
        if al_ov > 0:
            esalq_al = al_ov
            override_source = "company_settings_override"

        self.update_market_indicators(
            brent_usd=live.brent_usd.value,
            usd_brl=live.usd_brl.value,
            esalq_pe=esalq_pe,
            esalq_al=esalq_al,
        )
        payload = live.to_dict()
        payload["esalq_etanol_pe"] = esalq_pe
        payload["esalq_etanol_al"] = esalq_al
        payload["fonte"] = override_source or "external_market_service"
        if override_source:
            warnings = list(payload.get("warnings") or [])
            warnings.append("Esalq etanol sobrescrito por CompanySettings (override)")
            payload["warnings"] = warnings
            payload["esalq_override"] = True
        return payload


_market_service: FuelMarketIntelligenceService | None = None


def get_market_intelligence() -> FuelMarketIntelligenceService:
    """Singleton do servico de inteligencia de mercado."""
    global _market_service
    if _market_service is None:
        _market_service = FuelMarketIntelligenceService()
    return _market_service
