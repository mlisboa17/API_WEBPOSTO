"""Servico de Configuracoes por Empresa/Filial.

Sprint 55/59-B: Motor 100% dinamico e configuravel por empresa/fornecedor.
Suporte multicombustivel, multi-fornecedor e parametrizacao completa.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class FuelCategory(str, Enum):
    """Categorias de combustivel suportadas dinamicamente."""
    GASOLINA = "GASOLINA"
    ETANOL = "ETANOL"
    DIESEL = "DIESEL"
    GNV = "GNV"
    ARLA = "ARLA"
    LUBRIFICANTE = "LUBRIFICANTE"
    QUEROSENE = "QUEROSENE"
    OUTROS = "OUTROS"


@dataclass
class ProductPricing:
    """Configuracao de preco e custo de um produto."""
    
    produto_codigo: str
    preco_venda_rs: float = 0.0
    custo_aquisicao_rs: float = 0.0
    margem_bruta_rs: float = 0.0
    margem_bruta_pct: float = 0.0
    
    preco_minimo_venda_rs: float = 0.0
    margem_minima_pct: float = 5.0
    
    atualizado_em: str = ""


@dataclass
class FuelProductConfig:
    """Configuracao de produto de combustivel."""
    
    codigo: str
    nome: str
    categoria: FuelCategory
    unidade: str = "L"
    
    preco_base: float = 0.0
    custo_base: float = 0.0
    margem_minima_pct: float = 5.0
    
    sazonalidade_ativa: bool = False
    safra_inicio_mes: int = 9
    safra_fim_mes: int = 3
    fator_entresafra: float = 1.08
    
    ativo: bool = True


@dataclass
class SupplierConfig:
    """Configuracao de fornecedor/distribuidora."""
    
    codigo: str
    nome: str
    terminal: str = ""
    regiao: str = ""
    
    lead_time_horas: int = 24
    pedido_minimo_litros: float = 0.0
    frequencia_entrega: str = "diaria"
    
    produtos_fornecidos: list[str] = field(default_factory=list)
    
    contato_comercial: str = ""
    contato_emergencia: str = ""
    
    ativo: bool = True


@dataclass
class CoverageTarget:
    """Meta de cobertura de estoque por produto."""
    
    produto_codigo: str
    dias_cobertura: int = 3
    estoque_minimo_litros: float = 0.0
    estoque_maximo_litros: float = 0.0


@dataclass
class CompanySettings:
    """Configuracoes completas de uma empresa/filial."""
    
    empresa_codigo: int
    empresa_nome: str
    
    fornecedores: list[SupplierConfig] = field(default_factory=list)
    fornecedor_principal_codigo: str = ""
    
    produtos: list[FuelProductConfig] = field(default_factory=list)
    precos_produtos: list[ProductPricing] = field(default_factory=list)
    metas_cobertura: list[CoverageTarget] = field(default_factory=list)
    
    regiao: str = "PE"
    terminal_padrao: str = ""
    latitude: float | None = None
    longitude: float | None = None
    
    lead_time_padrao_horas: int = 24
    dias_cobertura_padrao: int = 3
    margem_minima_global_pct: float = 5.0
    
    notificacoes_ativas: bool = True
    
    metadata: dict[str, Any] = field(default_factory=dict)
    # Sprint 60 — overrides de mercado / custo
    # metadata.keys usados:
    #   esalq_etanol_pe_override, esalq_etanol_al_override
    #   custo_fallback_por_produto: {codigo: float}
    #   custo_fallback_global: float
    #   custo_fallback_defaults: {GASOLINA|ETANOL|DIESEL: float}


DEFAULT_FUEL_PRODUCTS = [
    FuelProductConfig(codigo="GC", nome="Gasolina Comum", categoria=FuelCategory.GASOLINA, preco_base=5.89, custo_base=5.10, margem_minima_pct=5.0),
    FuelProductConfig(codigo="GA", nome="Gasolina Aditivada", categoria=FuelCategory.GASOLINA, preco_base=6.19, custo_base=5.40, margem_minima_pct=5.0),
    FuelProductConfig(codigo="GP", nome="Gasolina Premium", categoria=FuelCategory.GASOLINA, preco_base=6.49, custo_base=5.70, margem_minima_pct=5.0),
    FuelProductConfig(codigo="EH", nome="Etanol Hidratado", categoria=FuelCategory.ETANOL, preco_base=3.99, custo_base=3.50, sazonalidade_ativa=True, margem_minima_pct=5.0),
    FuelProductConfig(codigo="EA", nome="Etanol Anidro", categoria=FuelCategory.ETANOL, preco_base=4.29, custo_base=3.80, sazonalidade_ativa=True, margem_minima_pct=5.0),
    FuelProductConfig(codigo="DS10", nome="Diesel S10", categoria=FuelCategory.DIESEL, preco_base=6.29, custo_base=5.50, margem_minima_pct=4.0),
    FuelProductConfig(codigo="DS500", nome="Diesel S500", categoria=FuelCategory.DIESEL, preco_base=5.99, custo_base=5.20, margem_minima_pct=4.0),
    FuelProductConfig(codigo="DM", nome="Diesel Maritimo", categoria=FuelCategory.DIESEL, preco_base=5.79, custo_base=5.00, margem_minima_pct=4.0),
    FuelProductConfig(codigo="GNV", nome="Gas Natural Veicular", categoria=FuelCategory.GNV, preco_base=4.49, custo_base=3.80, unidade="m3", margem_minima_pct=5.0),
    FuelProductConfig(codigo="ARLA", nome="Arla 32", categoria=FuelCategory.ARLA, preco_base=6.50, custo_base=5.50, unidade="L", margem_minima_pct=10.0),
    FuelProductConfig(codigo="QAV", nome="Querosene de Aviacao", categoria=FuelCategory.QUEROSENE, preco_base=7.50, custo_base=6.80, unidade="L", margem_minima_pct=3.0),
]

ALL_FUEL_PRODUCTS = ["GC", "GA", "GP", "EH", "EA", "DS10", "DS500", "DM", "GNV", "ARLA", "QAV"]

DEFAULT_SUPPLIERS = [
    SupplierConfig(
        codigo="VIBRA", nome="Vibra Energia", terminal="Suape/PE", regiao="PE",
        lead_time_horas=24, produtos_fornecidos=["GC", "GA", "GP", "EH", "DS10", "DS500", "DM"],
    ),
    SupplierConfig(
        codigo="IPIRANGA", nome="Ipiranga", terminal="Suape/PE", regiao="PE",
        lead_time_horas=24, produtos_fornecidos=["GC", "GA", "GP", "EH", "DS10", "DS500"],
    ),
    SupplierConfig(
        codigo="RAIZEN", nome="Raizen", terminal="Suape/PE", regiao="PE",
        lead_time_horas=36, produtos_fornecidos=["GC", "GA", "GP", "EH", "EA", "DS10", "DS500"],
    ),
    SupplierConfig(
        codigo="ALESAT", nome="ALE SAT", terminal="Suape/PE", regiao="PE",
        lead_time_horas=24, produtos_fornecidos=["GC", "GA", "EH", "DS10", "DS500"],
    ),
    SupplierConfig(
        codigo="TRR", nome="TRR Regional", terminal="Local", regiao="PE",
        lead_time_horas=12, produtos_fornecidos=["GC", "EH", "DS10", "DS500"],
    ),
    SupplierConfig(
        codigo="BRANCA", nome="Bandeira Branca", terminal="Variavel", regiao="BR",
        lead_time_horas=48, produtos_fornecidos=["GC", "EH", "DS10", "DS500"],
    ),
    SupplierConfig(
        codigo="GNV_DIST", nome="Distribuidora GNV", terminal="Local", regiao="PE",
        lead_time_horas=6, produtos_fornecidos=["GNV"],
    ),
]


class CompanySettingsService:
    """Servico de gerenciamento de configuracoes por empresa - 100% dinamico."""
    
    def __init__(self) -> None:
        self._settings: dict[int, CompanySettings] = {}
        self._init_default_settings()
    
    def _init_default_settings(self) -> None:
        """Inicializa configuracoes padrao para as filiais conhecidas."""
        from src.services.external_market_service import BRANCH_GEOCOORDINATES
        
        empresas = [
            (5555, "AP Casa Caiada", "VIBRA", "Suape/PE"),
            (11495, "Posto VIP", "VIBRA", "Suape/PE"),
            (6666, "Posto VIP (alias legado)", "VIBRA", "Suape/PE"),
            (74014, "Posto Real / Doze", "VIBRA", "Suape/PE"),
        ]
        
        for codigo, nome, fornecedor, terminal in empresas:
            geo = BRANCH_GEOCOORDINATES.get(codigo, {})
            settings = CompanySettings(
                empresa_codigo=codigo,
                empresa_nome=nome,
                fornecedores=[SupplierConfig(**s.__dict__) for s in DEFAULT_SUPPLIERS],
                fornecedor_principal_codigo=fornecedor,
                produtos=[FuelProductConfig(**p.__dict__) for p in DEFAULT_FUEL_PRODUCTS],
                precos_produtos=self._generate_default_pricing(DEFAULT_FUEL_PRODUCTS),
                regiao="PE",
                terminal_padrao=terminal,
                latitude=geo.get("latitude"),
                longitude=geo.get("longitude"),
                lead_time_padrao_horas=24,
                dias_cobertura_padrao=3,
                margem_minima_global_pct=5.0,
                metadata={
                    # Override CEPEA quando scraper retorna 403
                    "esalq_etanol_pe_override": 2.80,
                    "esalq_etanol_al_override": 2.75,
                    # Fallback CPM quando NF de entrada sem custo
                    "custo_fallback_defaults": {
                        "GASOLINA": 5.10,
                        "ETANOL": 3.50,
                        "DIESEL": 5.50,
                    },
                    "custo_fallback_global": 5.00,
                },
            )
            self._settings[codigo] = settings
    
    def _generate_default_pricing(self, produtos: list[FuelProductConfig]) -> list[ProductPricing]:
        """Gera precos padrao baseado nos produtos."""
        pricing = []
        for p in produtos:
            margem_rs = round(p.preco_base - p.custo_base, 4)
            margem_pct = round((margem_rs / p.preco_base) * 100, 2) if p.preco_base > 0 else 0.0
            pricing.append(ProductPricing(
                produto_codigo=p.codigo,
                preco_venda_rs=p.preco_base,
                custo_aquisicao_rs=p.custo_base,
                margem_bruta_rs=margem_rs,
                margem_bruta_pct=margem_pct,
                margem_minima_pct=p.margem_minima_pct,
            ))
        return pricing
    
    def get_settings(self, empresa_codigo: int) -> CompanySettings:
        """Retorna configuracoes da empresa ou cria padrao."""
        
        if empresa_codigo not in self._settings:
            produtos_copy = [FuelProductConfig(**p.__dict__) for p in DEFAULT_FUEL_PRODUCTS]
            self._settings[empresa_codigo] = CompanySettings(
                empresa_codigo=empresa_codigo,
                empresa_nome=f"Empresa {empresa_codigo}",
                fornecedores=[SupplierConfig(**s.__dict__) for s in DEFAULT_SUPPLIERS],
                fornecedor_principal_codigo="TRR",
                produtos=produtos_copy,
                precos_produtos=self._generate_default_pricing(produtos_copy),
            )
        
        return self._settings[empresa_codigo]
    
    def update_settings(self, empresa_codigo: int, updates: dict[str, Any]) -> CompanySettings:
        """Atualiza configuracoes da empresa."""
        
        settings = self.get_settings(empresa_codigo)
        
        for key, value in updates.items():
            if hasattr(settings, key):
                setattr(settings, key, value)
        
        return settings
    
    def get_supplier(self, empresa_codigo: int, supplier_codigo: str | None = None) -> SupplierConfig | None:
        """Retorna fornecedor especifico ou principal da empresa."""
        
        settings = self.get_settings(empresa_codigo)
        
        target = supplier_codigo or settings.fornecedor_principal_codigo
        
        for supplier in settings.fornecedores:
            if supplier.codigo == target and supplier.ativo:
                return supplier
        
        active_suppliers = [s for s in settings.fornecedores if s.ativo]
        return active_suppliers[0] if active_suppliers else None
    
    def get_product_config(self, empresa_codigo: int, produto_codigo: str) -> FuelProductConfig | None:
        """Retorna configuracao de produto especifico."""
        
        settings = self.get_settings(empresa_codigo)
        
        for produto in settings.produtos:
            if produto.ativo and (produto.codigo == produto_codigo or produto.nome.lower() in produto_codigo.lower()):
                return produto
        
        return None
    
    def set_esalq_override(
        self,
        empresa_codigo: int,
        esalq_pe: float | None = None,
        esalq_al: float | None = None,
    ) -> CompanySettings:
        """Define cotação manual de Etanol Esalq (sobrepõe CEPEA 403)."""
        settings = self.get_settings(empresa_codigo)
        if esalq_pe is not None and esalq_pe > 0:
            settings.metadata["esalq_etanol_pe_override"] = float(esalq_pe)
        if esalq_al is not None and esalq_al > 0:
            settings.metadata["esalq_etanol_al_override"] = float(esalq_al)
        return settings

    def get_esalq_overrides(self, empresa_codigo: int | None = None) -> dict[str, float]:
        """Lê overrides Esalq (filial específica ou primeira com valor)."""
        codes = [empresa_codigo] if empresa_codigo else list(self._settings.keys())
        for codigo in codes:
            if codigo is None:
                continue
            meta = self.get_settings(int(codigo)).metadata or {}
            pe = float(meta.get("esalq_etanol_pe_override") or 0)
            al = float(meta.get("esalq_etanol_al_override") or 0)
            if pe > 0 or al > 0:
                return {"esalq_etanol_pe": pe, "esalq_etanol_al": al}
        return {"esalq_etanol_pe": 0.0, "esalq_etanol_al": 0.0}

    def set_custo_fallback(
        self,
        empresa_codigo: int,
        produto_codigo: str | None = None,
        custo: float | None = None,
        custo_global: float | None = None,
    ) -> CompanySettings:
        """Fallback de preço de custo quando NF/webPosto não traz CPM."""
        settings = self.get_settings(empresa_codigo)
        if custo_global is not None and custo_global > 0:
            settings.metadata["custo_fallback_global"] = float(custo_global)
        if produto_codigo and custo is not None and custo > 0:
            mapa = settings.metadata.setdefault("custo_fallback_por_produto", {})
            if isinstance(mapa, dict):
                mapa[str(produto_codigo)] = float(custo)
            self.update_product_pricing(empresa_codigo, str(produto_codigo), custo_aquisicao=custo)
        return settings

    def get_product_pricing(self, empresa_codigo: int, produto_codigo: str) -> ProductPricing | None:
        """Retorna preco e custo de um produto especifico."""
        
        settings = self.get_settings(empresa_codigo)
        
        for pricing in settings.precos_produtos:
            if pricing.produto_codigo == produto_codigo:
                return pricing
        
        return None
    
    def get_all_products_pricing(self, empresa_codigo: int) -> dict[str, ProductPricing]:
        """Retorna todos os precos de produtos da empresa como dict."""
        
        settings = self.get_settings(empresa_codigo)
        return {p.produto_codigo: p for p in settings.precos_produtos}
    
    def update_product_pricing(
        self,
        empresa_codigo: int,
        produto_codigo: str,
        preco_venda: float | None = None,
        custo_aquisicao: float | None = None,
    ) -> ProductPricing | None:
        """Atualiza preco/custo de um produto especifico."""
        
        settings = self.get_settings(empresa_codigo)
        
        for pricing in settings.precos_produtos:
            if pricing.produto_codigo == produto_codigo:
                if preco_venda is not None:
                    pricing.preco_venda_rs = preco_venda
                if custo_aquisicao is not None:
                    pricing.custo_aquisicao_rs = custo_aquisicao
                
                pricing.margem_bruta_rs = round(pricing.preco_venda_rs - pricing.custo_aquisicao_rs, 4)
                if pricing.preco_venda_rs > 0:
                    pricing.margem_bruta_pct = round((pricing.margem_bruta_rs / pricing.preco_venda_rs) * 100, 2)
                
                from datetime import datetime
                pricing.atualizado_em = datetime.now().isoformat()
                
                return pricing
        
        return None
    
    def get_coverage_target(self, empresa_codigo: int, produto_codigo: str) -> CoverageTarget:
        """Retorna meta de cobertura para produto."""
        
        settings = self.get_settings(empresa_codigo)
        
        for meta in settings.metas_cobertura:
            if meta.produto_codigo == produto_codigo:
                return meta
        
        return CoverageTarget(
            produto_codigo=produto_codigo,
            dias_cobertura=settings.dias_cobertura_padrao,
        )
    
    def add_supplier(self, empresa_codigo: int, supplier: SupplierConfig) -> CompanySettings:
        """Adiciona um fornecedor a empresa."""
        
        settings = self.get_settings(empresa_codigo)
        
        for existing in settings.fornecedores:
            if existing.codigo == supplier.codigo:
                for attr in ["nome", "terminal", "regiao", "lead_time_horas", "pedido_minimo_litros", "produtos_fornecidos", "ativo"]:
                    setattr(existing, attr, getattr(supplier, attr))
                return settings
        
        settings.fornecedores.append(supplier)
        return settings
    
    def remove_supplier(self, empresa_codigo: int, supplier_codigo: str) -> bool:
        """Remove (desativa) um fornecedor da empresa."""
        
        settings = self.get_settings(empresa_codigo)
        
        for supplier in settings.fornecedores:
            if supplier.codigo == supplier_codigo:
                supplier.ativo = False
                return True
        
        return False
    
    def add_product(self, empresa_codigo: int, produto: FuelProductConfig) -> CompanySettings:
        """Adiciona ou atualiza um produto na empresa."""
        
        settings = self.get_settings(empresa_codigo)
        
        for existing in settings.produtos:
            if existing.codigo == produto.codigo:
                for attr in ["nome", "categoria", "unidade", "preco_base", "custo_base", "margem_minima_pct", "sazonalidade_ativa", "ativo"]:
                    setattr(existing, attr, getattr(produto, attr))
                return settings
        
        settings.produtos.append(produto)
        
        margem_rs = round(produto.preco_base - produto.custo_base, 4)
        margem_pct = round((margem_rs / produto.preco_base) * 100, 2) if produto.preco_base > 0 else 0.0
        settings.precos_produtos.append(ProductPricing(
            produto_codigo=produto.codigo,
            preco_venda_rs=produto.preco_base,
            custo_aquisicao_rs=produto.custo_base,
            margem_bruta_rs=margem_rs,
            margem_bruta_pct=margem_pct,
            margem_minima_pct=produto.margem_minima_pct,
        ))
        
        return settings
    
    def get_suppliers_for_product(self, empresa_codigo: int, produto_codigo: str) -> list[SupplierConfig]:
        """Retorna fornecedores que fornecem um produto especifico."""
        
        settings = self.get_settings(empresa_codigo)
        
        return [
            s for s in settings.fornecedores
            if s.ativo and (not s.produtos_fornecidos or produto_codigo in s.produtos_fornecidos)
        ]
    
    def list_companies(self) -> list[dict[str, Any]]:
        """Lista todas as empresas configuradas."""
        
        return [
            {
                "empresa_codigo": s.empresa_codigo,
                "empresa_nome": s.empresa_nome,
                "fornecedor_principal": s.fornecedor_principal_codigo,
                "terminal": s.terminal_padrao,
                "regiao": s.regiao,
                "latitude": s.latitude,
                "longitude": s.longitude,
                "total_produtos": len([p for p in s.produtos if p.ativo]),
                "total_fornecedores": len([f for f in s.fornecedores if f.ativo]),
            }
            for s in self._settings.values()
        ]
    
    def list_suppliers(self, empresa_codigo: int | None = None) -> list[dict[str, Any]]:
        """Lista todos os fornecedores disponiveis (globais ou da empresa)."""
        
        if empresa_codigo:
            settings = self.get_settings(empresa_codigo)
            suppliers = settings.fornecedores
        else:
            suppliers = DEFAULT_SUPPLIERS
        
        return [
            {
                "codigo": s.codigo,
                "nome": s.nome,
                "terminal": s.terminal,
                "regiao": s.regiao,
                "lead_time_horas": s.lead_time_horas,
                "produtos_fornecidos": s.produtos_fornecidos,
                "ativo": s.ativo,
            }
            for s in suppliers
        ]
    
    def list_fuel_products(self, empresa_codigo: int | None = None) -> list[dict[str, Any]]:
        """Lista todos os produtos de combustivel disponiveis."""
        
        if empresa_codigo:
            settings = self.get_settings(empresa_codigo)
            produtos = settings.produtos
        else:
            produtos = DEFAULT_FUEL_PRODUCTS
        
        return [
            {
                "codigo": p.codigo,
                "nome": p.nome,
                "categoria": p.categoria.value,
                "unidade": p.unidade,
                "preco_base": p.preco_base,
                "custo_base": p.custo_base,
                "margem_minima_pct": p.margem_minima_pct,
                "sazonalidade_ativa": p.sazonalidade_ativa,
                "ativo": p.ativo,
            }
            for p in produtos
        ]


_settings_service: CompanySettingsService | None = None


def get_company_settings_service() -> CompanySettingsService:
    """Singleton do servico de configuracoes."""
    global _settings_service
    if _settings_service is None:
        _settings_service = CompanySettingsService()
    return _settings_service
