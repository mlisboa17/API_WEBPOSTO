"""Servico de Previsao de Estoque e Sugestao de Compras (Run-Out Prediction).

Sprint 58/59-B: Calculo preditivo dinamico por empresa/fornecedor.
"""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass, field
from datetime import date, timedelta
from typing import Any

from src.gateway.shared_client import get_webposto_client
from src.services.company_settings_service import (
    CompanySettingsService,
    get_company_settings_service,
)


@dataclass
class TankPrediction:
    """Predicao de run-out para um tanque/produto."""
    
    produto_codigo: int = 0
    produto_nome: str = ""
    tipo_combustivel: str = ""
    
    estoque_atual_litros: float = 0.0
    capacidade_tanque: float = 0.0
    ocupacao_percentual: float = 0.0
    
    consumo_medio_diario: float = 0.0
    dias_cobertura_desejado: int = 3
    lead_time_horas: int = 24
    
    autonomia_horas_restantes: float = 0.0
    autonomia_dias_restantes: float = 0.0
    
    status_alerta: str = "OK"  # OK | ATENCAO | COMPRA_URGENTE
    sugestao_compra_litros: float = 0.0
    alerta_label: str = "Saudável"
    
    dias_historico_usado: int = 7
    fonte_consumo: str = ""
    observacoes: list[str] = field(default_factory=list)

    # Sprint 60 — CPM / margem / estoque imobilizado
    cpm_rs_litro: float = 0.0
    preco_venda_rs_litro: float = 0.0
    margem_bruta_rs_litro: float = 0.0
    valor_estoque_imobilizado_rs: float = 0.0
    cpm_origem: str = ""


@dataclass
class InventoryPredictionResult:
    """Resultado consolidado da previsao de estoque."""
    
    success: bool = True
    empresa_codigo: int = 0
    empresa_nome: str = ""
    data_calculo: str = ""
    
    dias_cobertura: int = 3
    lead_time_horas: int = 24
    
    predicoes: list[TankPrediction] = field(default_factory=list)
    
    total_sugestao_compra_litros: float = 0.0
    tanques_com_alerta: int = 0
    tanques_urgentes: int = 0
    
    observacoes: list[str] = field(default_factory=list)


FUEL_KEYWORDS = {
    "GASOLINA_COMUM": ["GASOLINA COMUM", "GAS COMUM", "GASOLINA C"],
    "GASOLINA_ADITIVADA": ["ADITIVADA", "PREMIUM", "PODIUM", "GRID"],
    "ETANOL": ["ETANOL", "ALCOOL", "EAC", "EHC", "HIDRATADO"],
    "DIESEL_S10": ["DIESEL S10", "S10", "S-10"],
    "DIESEL_S500": ["DIESEL S500", "S500", "S-500", "DIESEL COMUM"],
    "GNV": ["GNV", "GAS NATURAL"],
}


def classify_fuel_type(product_name: str) -> str:
    """Classifica o tipo de combustivel baseado no nome."""
    name_upper = (product_name or "").upper()
    
    for fuel_type, keywords in FUEL_KEYWORDS.items():
        if any(kw in name_upper for kw in keywords):
            return fuel_type
    
    if "GASOLINA" in name_upper:
        return "GASOLINA_COMUM"
    if "DIESEL" in name_upper:
        return "DIESEL_S500"
    
    return "OUTROS"


class InventoryPredictionService:
    """Servico para calculo de run-out e sugestao de compras (dinamico)."""
    
    def __init__(self, settings_service: CompanySettingsService | None = None) -> None:
        self.client = get_webposto_client()
        self._settings = settings_service or get_company_settings_service()
    
    async def predict(
        self,
        empresa_codigo: int,
        dias_cobertura: int | None = None,
        lead_time_horas: int | None = None,
        dias_historico: int = 7,
        fornecedor_codigo: str | None = None,
    ) -> InventoryPredictionResult:
        """
        Calcula a previsao de run-out e sugestao de compras.
        
        Args:
            empresa_codigo: Codigo da filial
            dias_cobertura: Dias de estoque desejado (ou usa config da empresa)
            lead_time_horas: Tempo de entrega (ou usa config do fornecedor)
            dias_historico: Dias de historico para calcular media de consumo
            fornecedor_codigo: Codigo do fornecedor (ou usa principal da empresa)
        """
        
        settings = self._settings.get_settings(empresa_codigo)
        fornecedor = self._settings.get_supplier(empresa_codigo, fornecedor_codigo)
        
        if dias_cobertura is None:
            dias_cobertura = settings.dias_cobertura_padrao
        if lead_time_horas is None:
            lead_time_horas = fornecedor.lead_time_horas if fornecedor else settings.lead_time_padrao_horas
        
        dias_cobertura = max(1, min(15, dias_cobertura))
        lead_time_horas = max(1, min(168, lead_time_horas))
        
        result = InventoryPredictionResult(
            empresa_codigo=empresa_codigo,
            empresa_nome=settings.empresa_nome,
            data_calculo=date.today().isoformat(),
            dias_cobertura=dias_cobertura,
            lead_time_horas=lead_time_horas,
        )
        
        if fornecedor:
            result.observacoes.append(f"Fornecedor: {fornecedor.nome} | Terminal: {fornecedor.terminal}")
        
        try:
            tanks = await self._fetch_tank_levels(empresa_codigo)
            consumption = await self._fetch_consumption_history(
                empresa_codigo, dias_historico
            )
            
            if not tanks:
                result.observacoes.append("Nenhum tanque encontrado para esta filial")
                return result
            
            # CPM real (webPosto) + fallback CompanySettings
            cpm_map: dict[str, dict[str, Any]] = {}
            try:
                from src.services.webposto_integration_service import (
                    get_webposto_integration_service,
                )

                costs = await get_webposto_integration_service().get_weighted_avg_cost(
                    empresa_codigo
                )
                for item in costs.custos or []:
                    codigo = str(item.get("produto_codigo") or "")
                    if codigo:
                        cpm_map[codigo] = item
            except Exception:
                cpm_map = {}

            for tank in tanks:
                prediction = self._calculate_prediction(
                    tank=tank,
                    consumption=consumption,
                    dias_cobertura=dias_cobertura,
                    lead_time_horas=lead_time_horas,
                    dias_historico=dias_historico,
                    empresa_codigo=empresa_codigo,
                    cpm_map=cpm_map,
                )
                result.predicoes.append(prediction)
                
                if prediction.sugestao_compra_litros > 0:
                    result.total_sugestao_compra_litros += prediction.sugestao_compra_litros
                
                if prediction.status_alerta == "COMPRA_URGENTE":
                    result.tanques_urgentes += 1
                    result.tanques_com_alerta += 1
                elif prediction.status_alerta == "ATENCAO":
                    result.tanques_com_alerta += 1
            
            result.predicoes.sort(key=lambda x: x.autonomia_horas_restantes)
            
            return result
            
        except Exception as e:
            result.success = False
            result.observacoes.append(f"Erro no calculo: {str(e)}")
            return result
    
    async def _fetch_tank_levels(self, empresa_codigo: int) -> list[dict[str, Any]]:
        """Busca niveis atuais dos tanques."""
        
        try:
            resp = await self.client.call_endpoint(
                "tanque",
                params={"empresaCodigo": empresa_codigo}
            )
            
            if not resp.success:
                return []
            
            raw = resp.data
            if isinstance(raw, dict):
                return raw.get("resultados") or raw.get("dados") or raw.get("data") or []
            elif isinstance(raw, list):
                return raw
            
            return []
            
        except Exception:
            return []
    
    async def _fetch_consumption_history(
        self, empresa_codigo: int, dias: int
    ) -> dict[int, float]:
        """
        Venda média diária dos últimos N dias (L/dia).
        Prefere histórico local sales_daily_summary (até 90d); fallback ABASTECIMENTO.
        """
        local = await self._consumption_from_local_db(empresa_codigo, dias)
        if local:
            return local
        return await self._consumption_from_abastecimento(empresa_codigo, dias)

    async def _consumption_from_local_db(
        self, empresa_codigo: int, dias: int
    ) -> dict[int, float]:
        try:
            from sqlalchemy import select, func
            from src.infrastructure.config.database import AsyncSessionLocal
            from src.models.sales_daily_summary_model import SalesDailySummaryModel

            end_date = date.today() - timedelta(days=1)  # fecha em D-1
            start_date = end_date - timedelta(days=max(1, dias) - 1)
            async with AsyncSessionLocal() as session:
                stmt = (
                    select(
                        SalesDailySummaryModel.codigo_produto_webposto,
                        func.sum(SalesDailySummaryModel.litros_vendidos),
                    )
                    .where(
                        SalesDailySummaryModel.empresa_codigo == int(empresa_codigo),
                        SalesDailySummaryModel.data_referencia >= start_date,
                        SalesDailySummaryModel.data_referencia <= end_date,
                        SalesDailySummaryModel.litros_vendidos > 0,
                    )
                    .group_by(SalesDailySummaryModel.codigo_produto_webposto)
                )
                rows = (await session.execute(stmt)).all()
            if not rows:
                return {}
            out: dict[int, float] = {}
            for codigo, litros in rows:
                try:
                    code = int(str(codigo).strip())
                except (TypeError, ValueError):
                    continue
                if code and litros:
                    out[code] = float(litros) / max(1, dias)
            return out
        except Exception:
            return {}

    async def _consumption_from_abastecimento(
        self, empresa_codigo: int, dias: int
    ) -> dict[int, float]:
        consumption: dict[int, float] = defaultdict(float)
        try:
            end_date = date.today()
            start_date = end_date - timedelta(days=dias)
            params = {
                "dataInicial": start_date.isoformat(),
                "dataFinal": end_date.isoformat(),
                "empresaCodigo": empresa_codigo,
            }
            all_records: list[dict] = []
            ultimo_codigo = None
            page = 0
            while page < 20:
                page += 1
                req_params = {**params}
                if ultimo_codigo:
                    req_params["ultimoCodigo"] = ultimo_codigo
                resp = await self.client.call_endpoint("abastecimento", params=req_params)
                if not resp.success:
                    break
                raw = resp.data
                batch: list[dict] = []
                new_ultimo = None
                if isinstance(raw, dict):
                    batch = raw.get("dados") or raw.get("data") or raw.get("resultados") or []
                    new_ultimo = raw.get("ultimoCodigo")
                elif isinstance(raw, list):
                    batch = raw
                if not batch:
                    break
                all_records.extend(batch)
                if new_ultimo is None or new_ultimo == ultimo_codigo:
                    break
                ultimo_codigo = new_ultimo
                if len(batch) < 200:
                    break
            for record in all_records:
                prod_codigo = int(
                    record.get("produtoCodigo")
                    or record.get("produtoLmcCodigo")
                    or 0
                )
                litros = float(
                    record.get("quantidadeLitros")
                    or record.get("litros")
                    or record.get("quantidade")
                    or 0
                )
                if prod_codigo and litros > 0:
                    consumption[prod_codigo] += litros
            for prod_codigo in consumption:
                consumption[prod_codigo] = consumption[prod_codigo] / max(1, dias)
            return dict(consumption)
        except Exception:
            return {}
    
    def _calculate_prediction(
        self,
        tank: dict[str, Any],
        consumption: dict[int, float],
        dias_cobertura: int,
        lead_time_horas: int,
        dias_historico: int,
        empresa_codigo: int = 0,
        cpm_map: dict[str, dict[str, Any]] | None = None,
    ) -> TankPrediction:
        """Calcula a previsao para um tanque especifico."""
        
        prod_codigo = int(
            tank.get("produtoCodigo")
            or tank.get("produtoLmcCodigo")
            or tank.get("codigoProduto")
            or 0
        )
        prod_nome = str(
            tank.get("nome")
            or tank.get("produtoDescricao")
            or tank.get("nomeProduto")
            or tank.get("produto")
            or f"Produto {prod_codigo}"
        ).strip()
        
        estoque_atual = float(
            tank.get("estoqueEscritural")
            or tank.get("volumeAtual")
            or tank.get("estoque")
            or tank.get("quantidade")
            or 0
        )
        capacidade = float(
            tank.get("capacidade")
            or tank.get("capacidadeTotal")
            or tank.get("volumeMaximo")
            or 15000
        )
        
        tipo_combustivel = classify_fuel_type(prod_nome)
        
        consumo_diario = consumption.get(prod_codigo, 0.0)
        
        if consumo_diario <= 0:
            consumo_diario = self._estimate_default_consumption(tipo_combustivel)
        
        prediction = TankPrediction(
            produto_codigo=prod_codigo,
            produto_nome=prod_nome,
            tipo_combustivel=tipo_combustivel,
            estoque_atual_litros=round(estoque_atual, 2),
            capacidade_tanque=round(capacidade, 2),
            ocupacao_percentual=round((estoque_atual / capacidade * 100) if capacidade > 0 else 0, 1),
            consumo_medio_diario=round(consumo_diario, 2),
            dias_cobertura_desejado=dias_cobertura,
            lead_time_horas=lead_time_horas,
            dias_historico_usado=dias_historico,
        )

        # CPM / margem / valor imobilizado
        # webPosto usa códigos numéricos no tanque; fallback CompanySettings usa GC/EH/DS10
        codigo_str = str(prod_codigo)
        alias_by_type = {
            "GASOLINA": ("GC", "GA", "GP"),
            "GASOLINA_COMUM": ("GC",),
            "GASOLINA_ADITIVADA": ("GA", "GP"),
            "ETANOL": ("EH", "EA"),
            "DIESEL": ("DS10", "DS500", "DM"),
            "DIESEL_S10": ("DS10",),
            "DIESEL_S500": ("DS500", "DM"),
            "GNV": ("GNV",),
            "ARLA": ("ARLA",),
        }
        tipo_family = (
            "GASOLINA"
            if tipo_combustivel.startswith("GASOLINA")
            else "DIESEL"
            if tipo_combustivel.startswith("DIESEL")
            else tipo_combustivel
        )
        cpm_item = (cpm_map or {}).get(codigo_str) or {}
        if not cpm_item and cpm_map:
            for alias in alias_by_type.get(tipo_combustivel, ()):
                if alias in cpm_map:
                    cpm_item = cpm_map[alias]
                    break
        cpm = float(cpm_item.get("cpm_rs") or 0)
        origem = str(cpm_item.get("origem") or "")
        pricing = self._settings.get_product_pricing(empresa_codigo, codigo_str)
        if (not pricing or pricing.custo_aquisicao_rs <= 0) and cpm_item.get("produto_codigo"):
            pricing = self._settings.get_product_pricing(
                empresa_codigo, str(cpm_item.get("produto_codigo"))
            )
        if cpm <= 0 and pricing and pricing.custo_aquisicao_rs > 0:
            cpm = float(pricing.custo_aquisicao_rs)
            origem = "company_settings_fallback"
        if cpm <= 0:
            for alias in alias_by_type.get(tipo_combustivel, (codigo_str,)):
                prod_cfg = self._settings.get_product_config(empresa_codigo, alias)
                if prod_cfg and prod_cfg.custo_base > 0:
                    cpm = float(prod_cfg.custo_base)
                    origem = "company_settings_custo_base"
                    if not pricing or pricing.preco_venda_rs <= 0:
                        pricing = self._settings.get_product_pricing(empresa_codigo, alias)
                    break
        # metadata defaults por tipo (Sprint 60)
        if cpm <= 0:
            meta = (self._settings.get_settings(empresa_codigo).metadata or {})
            defaults = meta.get("custo_fallback_defaults") or {}
            if isinstance(defaults, dict):
                cpm = float(defaults.get(tipo_family) or defaults.get(tipo_combustivel) or 0)
                if cpm > 0:
                    origem = "company_settings_tipo_fallback"
            if cpm <= 0:
                cpm = float(meta.get("custo_fallback_global") or 0)
                if cpm > 0:
                    origem = "company_settings_global_fallback"
        preco_venda = float(pricing.preco_venda_rs) if pricing and pricing.preco_venda_rs > 0 else 0.0
        if preco_venda <= 0:
            for alias in alias_by_type.get(tipo_combustivel, (codigo_str,)):
                prod_cfg = self._settings.get_product_config(empresa_codigo, alias)
                if prod_cfg and prod_cfg.preco_base > 0:
                    preco_venda = float(prod_cfg.preco_base)
                    break
        margem = round(preco_venda - cpm, 4) if preco_venda > 0 and cpm > 0 else 0.0
        prediction.cpm_rs_litro = round(cpm, 4)
        prediction.preco_venda_rs_litro = round(preco_venda, 4)
        prediction.margem_bruta_rs_litro = margem
        prediction.valor_estoque_imobilizado_rs = round(estoque_atual * cpm, 2) if cpm > 0 else 0.0
        prediction.cpm_origem = origem
        if cpm <= 0:
            prediction.observacoes.append("CPM indisponível — configure fallback em CompanySettings")
        
        # Autonomia (Dias) = Volume Atual / Venda Média Diária (7d)
        if consumo_diario > 0:
            dias_restantes = estoque_atual / consumo_diario
            prediction.autonomia_dias_restantes = round(dias_restantes, 1)
            prediction.autonomia_horas_restantes = round(dias_restantes * 24, 1)
            prediction.fonte_consumo = "sales_daily_summary|abastecimento"
        else:
            prediction.autonomia_dias_restantes = 999
            prediction.autonomia_horas_restantes = 999 * 24
            prediction.observacoes.append("Sem historico de consumo - usando estimativa")

        # Alertas: Crítico < 1.5d | Atenção < 3d | Saudável >= 3d
        autonomia = prediction.autonomia_dias_restantes
        if autonomia < 1.5:
            prediction.status_alerta = "COMPRA_URGENTE"
            prediction.alerta_label = "Risco de Ruptura - Pedir Carreta"
        elif autonomia < 3.0:
            prediction.status_alerta = "ATENCAO"
            prediction.alerta_label = "Atenção"
        else:
            prediction.status_alerta = "OK"
            prediction.alerta_label = "Saudável"

        if prediction.status_alerta != "OK":
            estoque_desejado = consumo_diario * max(dias_cobertura, 3)
            volume_necessario = (
                estoque_desejado
                - estoque_atual
                + (consumo_diario * (lead_time_horas / 24))
            )
            espaco_disponivel = capacidade - estoque_atual
            sugestao = max(0, min(volume_necessario, espaco_disponivel))
            prediction.sugestao_compra_litros = round(sugestao / 1000) * 1000

        return prediction
    
    def _estimate_default_consumption(self, tipo_combustivel: str) -> float:
        """Estima consumo padrao quando nao ha historico."""
        
        defaults = {
            "GASOLINA_COMUM": 800.0,
            "GASOLINA_ADITIVADA": 400.0,
            "ETANOL": 600.0,
            "DIESEL_S10": 1200.0,
            "DIESEL_S500": 500.0,
            "GNV": 300.0,
            "OUTROS": 200.0,
        }
        
        return defaults.get(tipo_combustivel, 200.0)
