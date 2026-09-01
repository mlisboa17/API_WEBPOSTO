"""Serviço de conciliação de perdas volumétricas de combustíveis — Sprint 46."""

from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal, ROUND_HALF_UP
from enum import Enum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator


class LossClassification(str, Enum):
    """Classificação da variação volumétrica."""

    NORMAL = "NORMAL"
    PERDA_TERMICA = "PERDA_TERMICA"
    ATENCAO = "ATENCAO"
    CRITICO = "CRITICO"
    SOBRA_SUSPEITA = "SOBRA_SUSPEITA"
    DESVIO_SUSPEITO = "DESVIO_SUSPEITO"
    VAZAMENTO = "VAZAMENTO"


FUEL_EXPANSION_COEFFICIENTS: dict[str, float] = {
    "GASOLINA": 0.00120,
    "GASOLINA COMUM": 0.00120,
    "GASOLINA ADITIVADA": 0.00120,
    "ETANOL": 0.00110,
    "ALCOOL": 0.00110,
    "DIESEL": 0.00095,
    "DIESEL S10": 0.00095,
    "DIESEL S500": 0.00095,
    "GNV": 0.00000,
    "DEFAULT": 0.00095,
}


class ThermalAnalysis(BaseModel):
    """Análise de variação térmica de um tanque."""

    model_config = ConfigDict(frozen=True)

    temp_inicial: float | None = None
    temp_final: float | None = None
    delta_temp: float | None = None
    coef_expansao: float = 0.00095
    variacao_termica_esperada: float = 0.0
    variacao_termica_pct: float = 0.0
    has_thermal_data: bool = False


class TankReconciliation(BaseModel):
    """Conciliação volumétrica de um tanque individual."""

    model_config = ConfigDict(frozen=True)

    tanque_codigo: int
    empresa_codigo: int
    empresa_nome: str | None = None
    combustivel_tipo: str | None = None
    estoque_inicial: float
    entradas_nf: float
    saidas_vendas: float
    estoque_esperado: float
    estoque_medido: float
    variacao_litros: float
    variacao_percentual: float
    variacao_reais: float | None = None
    preco_medio_litro: float | None = None
    classificacao: LossClassification
    tolerancia_pct: float = 0.6
    within_tolerance: bool
    alert_level: str = "OK"
    thermal_analysis: ThermalAnalysis | None = None
    variacao_real_litros: float | None = None
    variacao_real_pct: float | None = None
    dias_periodo: int = 1
    venda_media_diaria: float | None = None
    dias_para_ruptura: float | None = None

    @property
    def is_loss(self) -> bool:
        return self.variacao_litros < 0

    @property
    def is_surplus(self) -> bool:
        return self.variacao_litros > 0

    @property
    def is_thermal_explained(self) -> bool:
        if not self.thermal_analysis or not self.thermal_analysis.has_thermal_data:
            return False
        if self.variacao_real_litros is None:
            return False
        return abs(self.variacao_real_litros) <= abs(self.variacao_litros) * 0.3

    @property
    def ruptura_iminente(self) -> bool:
        if self.dias_para_ruptura is None:
            return False
        return self.dias_para_ruptura <= 3


class FuelLossSummary(BaseModel):
    """Resumo consolidado de perdas e sobras de combustíveis."""

    model_config = ConfigDict(frozen=True)

    period_start: str
    period_end: str
    empresa_codigo: int | None = None
    total_tanques_analisados: int = 0
    tanques_com_perda: int = 0
    tanques_com_sobra: int = 0
    tanques_criticos: int = 0
    perda_total_litros: float = 0.0
    sobra_total_litros: float = 0.0
    perda_total_reais: float = 0.0
    sobra_total_reais: float = 0.0
    variacao_liquida_litros: float = 0.0
    variacao_liquida_reais: float = 0.0
    reconciliations: list[TankReconciliation] = Field(default_factory=list)
    critical_alerts: list[dict[str, Any]] = Field(default_factory=list)
    overall_status: str = "OK"
    generated_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


class FuelLossService:
    """Concilia medições de tanque e identifica perdas/sobras volumétricas com correção térmica."""

    DEFAULT_TOLERANCE_PCT = 0.6
    CRITICAL_TOLERANCE_PCT = 1.5
    VAZAMENTO_THRESHOLD_PCT = 3.0
    SURPLUS_ALERT_PCT = 0.3
    ANP_REFERENCE_TEMP = 20.0

    def __init__(self, tolerance_pct: float | None = None) -> None:
        self._tolerance = tolerance_pct or self.DEFAULT_TOLERANCE_PCT

    def _get_expansion_coefficient(self, combustivel_tipo: str | None) -> float:
        if not combustivel_tipo:
            return FUEL_EXPANSION_COEFFICIENTS["DEFAULT"]
        normalized = combustivel_tipo.upper().strip()
        for key, coef in FUEL_EXPANSION_COEFFICIENTS.items():
            if key in normalized or normalized in key:
                return coef
        return FUEL_EXPANSION_COEFFICIENTS["DEFAULT"]

    def calculate_thermal_correction(
        self,
        volume_litros: float,
        temp_inicial: float | None,
        temp_final: float | None,
        combustivel_tipo: str | None = None,
    ) -> ThermalAnalysis:
        if temp_inicial is None or temp_final is None:
            return ThermalAnalysis(has_thermal_data=False)

        coef = self._get_expansion_coefficient(combustivel_tipo)
        delta_temp = temp_final - temp_inicial
        variacao_termica = volume_litros * coef * delta_temp
        variacao_pct = abs(variacao_termica) / max(volume_litros, 1) * 100

        return ThermalAnalysis(
            temp_inicial=temp_inicial,
            temp_final=temp_final,
            delta_temp=round(delta_temp, 2),
            coef_expansao=coef,
            variacao_termica_esperada=round(variacao_termica, 2),
            variacao_termica_pct=round(variacao_pct, 4),
            has_thermal_data=True,
        )

    def reconcile_tank(
        self,
        tanque_codigo: int,
        empresa_codigo: int,
        estoque_inicial: float,
        entradas_nf: float,
        saidas_vendas: float,
        estoque_medido: float,
        combustivel_tipo: str | None = None,
        empresa_nome: str | None = None,
        preco_medio: float | None = None,
        temp_inicial: float | None = None,
        temp_final: float | None = None,
        dias_periodo: int = 1,
    ) -> TankReconciliation:
        estoque_esperado = estoque_inicial + entradas_nf - saidas_vendas
        variacao_litros = estoque_medido - estoque_esperado

        base_volume = max(abs(saidas_vendas), abs(estoque_inicial), 1)
        variacao_pct = abs(variacao_litros) / base_volume * 100

        variacao_reais = None
        if preco_medio and preco_medio > 0:
            variacao_reais = round(variacao_litros * preco_medio, 2)

        thermal = self.calculate_thermal_correction(
            estoque_inicial, temp_inicial, temp_final, combustivel_tipo
        )

        variacao_real_litros = None
        variacao_real_pct = None
        if thermal.has_thermal_data:
            variacao_real_litros = round(variacao_litros - thermal.variacao_termica_esperada, 2)
            variacao_real_pct = round(abs(variacao_real_litros) / base_volume * 100, 4)

        classificacao, alert_level = self._classify_with_thermal(
            variacao_litros, variacao_pct, variacao_real_litros, variacao_real_pct, thermal
        )

        within_tolerance = variacao_pct <= self._tolerance

        venda_media_diaria = saidas_vendas / max(dias_periodo, 1)
        dias_para_ruptura = None
        if venda_media_diaria > 0 and estoque_medido > 0:
            dias_para_ruptura = round(estoque_medido / venda_media_diaria, 1)

        return TankReconciliation(
            tanque_codigo=tanque_codigo,
            empresa_codigo=empresa_codigo,
            empresa_nome=empresa_nome,
            combustivel_tipo=combustivel_tipo,
            estoque_inicial=round(estoque_inicial, 2),
            entradas_nf=round(entradas_nf, 2),
            saidas_vendas=round(saidas_vendas, 2),
            estoque_esperado=round(estoque_esperado, 2),
            estoque_medido=round(estoque_medido, 2),
            variacao_litros=round(variacao_litros, 2),
            variacao_percentual=round(variacao_pct, 4),
            variacao_reais=variacao_reais,
            preco_medio_litro=preco_medio,
            classificacao=classificacao,
            tolerancia_pct=self._tolerance,
            within_tolerance=within_tolerance,
            alert_level=alert_level,
            thermal_analysis=thermal if thermal.has_thermal_data else None,
            variacao_real_litros=variacao_real_litros,
            variacao_real_pct=variacao_real_pct,
            dias_periodo=dias_periodo,
            venda_media_diaria=round(venda_media_diaria, 2) if venda_media_diaria else None,
            dias_para_ruptura=dias_para_ruptura,
        )

    def _classify_with_thermal(
        self,
        variacao_litros: float,
        variacao_pct: float,
        variacao_real_litros: float | None,
        variacao_real_pct: float | None,
        thermal: ThermalAnalysis,
    ) -> tuple[LossClassification, str]:
        if thermal.has_thermal_data and variacao_real_pct is not None:
            if variacao_real_pct <= self._tolerance * 0.5:
                return LossClassification.PERDA_TERMICA, "OK"
            elif variacao_real_pct > self.VAZAMENTO_THRESHOLD_PCT:
                return LossClassification.VAZAMENTO, "CRITICAL"
            elif variacao_real_pct > self.CRITICAL_TOLERANCE_PCT:
                return LossClassification.DESVIO_SUSPEITO, "CRITICAL"
            elif variacao_real_pct > self._tolerance:
                if variacao_real_litros and variacao_real_litros > 0:
                    return LossClassification.SOBRA_SUSPEITA, "WARNING"
                return LossClassification.ATENCAO, "WARNING"
            return LossClassification.NORMAL, "OK"

        if variacao_pct > self.VAZAMENTO_THRESHOLD_PCT:
            return LossClassification.VAZAMENTO, "CRITICAL"
        if variacao_pct > self.CRITICAL_TOLERANCE_PCT:
            return LossClassification.CRITICO, "CRITICAL"
        if variacao_pct > self._tolerance:
            if variacao_litros > 0:
                return LossClassification.SOBRA_SUSPEITA, "WARNING"
            return LossClassification.ATENCAO, "WARNING"
        return LossClassification.NORMAL, "OK"

    def reconcile_batch(
        self,
        tank_data: list[dict[str, Any]],
        period_start: str,
        period_end: str,
        empresa_codigo: int | None = None,
    ) -> FuelLossSummary:
        reconciliations: list[TankReconciliation] = []

        for tank in tank_data:
            recon = self.reconcile_tank(
                tanque_codigo=int(tank.get("tanqueCodigo") or tank.get("codigo") or 0),
                empresa_codigo=int(tank.get("empresaCodigo") or empresa_codigo or 0),
                estoque_inicial=float(tank.get("estoqueInicial") or 0),
                entradas_nf=float(tank.get("entradasNf") or tank.get("entradas") or 0),
                saidas_vendas=float(tank.get("saidasVendas") or tank.get("vendas") or 0),
                estoque_medido=float(tank.get("estoqueMedido") or tank.get("estoqueFinal") or 0),
                combustivel_tipo=tank.get("combustivelTipo") or tank.get("produto"),
                empresa_nome=tank.get("empresaNome"),
                preco_medio=float(tank.get("precoMedio") or 0) if tank.get("precoMedio") else None,
            )
            reconciliations.append(recon)

        com_perda = [r for r in reconciliations if r.is_loss]
        com_sobra = [r for r in reconciliations if r.is_surplus]
        criticos = [r for r in reconciliations if r.classificacao in {
            LossClassification.CRITICO,
            LossClassification.VAZAMENTO,
            LossClassification.DESVIO_SUSPEITO,
        }]

        perda_litros = sum(abs(r.variacao_litros) for r in com_perda)
        sobra_litros = sum(r.variacao_litros for r in com_sobra)
        perda_reais = sum(abs(r.variacao_reais or 0) for r in com_perda)
        sobra_reais = sum(r.variacao_reais or 0 for r in com_sobra)

        variacao_liq_litros = sobra_litros - perda_litros
        variacao_liq_reais = sobra_reais - perda_reais

        critical_alerts = [
            {
                "tanque": r.tanque_codigo,
                "empresa": r.empresa_codigo,
                "tipo": "PERDA_CRITICA" if r.is_loss else "SOBRA_SUSPEITA",
                "variacao_litros": r.variacao_litros,
                "variacao_pct": r.variacao_percentual,
                "combustivel": r.combustivel_tipo,
            }
            for r in criticos
        ]

        if criticos:
            overall = "CRITICAL"
        elif any(r.classificacao == LossClassification.ATENCAO for r in reconciliations):
            overall = "WARNING"
        elif any(r.classificacao == LossClassification.SOBRA_SUSPEITA for r in reconciliations):
            overall = "WARNING"
        else:
            overall = "OK"

        return FuelLossSummary(
            period_start=period_start,
            period_end=period_end,
            empresa_codigo=empresa_codigo,
            total_tanques_analisados=len(reconciliations),
            tanques_com_perda=len(com_perda),
            tanques_com_sobra=len(com_sobra),
            tanques_criticos=len(criticos),
            perda_total_litros=round(perda_litros, 2),
            sobra_total_litros=round(sobra_litros, 2),
            perda_total_reais=round(perda_reais, 2),
            sobra_total_reais=round(sobra_reais, 2),
            variacao_liquida_litros=round(variacao_liq_litros, 2),
            variacao_liquida_reais=round(variacao_liq_reais, 2),
            reconciliations=sorted(reconciliations, key=lambda r: abs(r.variacao_litros), reverse=True),
            critical_alerts=critical_alerts,
            overall_status=overall,
        )

    def extract_from_lmc_data(
        self,
        lmc_records: list[dict[str, Any]],
        period_start: str,
        period_end: str,
    ) -> FuelLossSummary:
        tank_aggregates: dict[tuple[int, int], dict[str, Any]] = {}

        for record in lmc_records:
            empresa = int(record.get("empresaCodigo") or 0)
            for tank in record.get("lmcTanque") or []:
                if not isinstance(tank, dict):
                    continue
                tanque_codigo = int(tank.get("tanqueCodigo") or tank.get("lmcTanqueCodigo") or 0)
                if not tanque_codigo:
                    continue

                key = (empresa, tanque_codigo)
                if key not in tank_aggregates:
                    tank_aggregates[key] = {
                        "tanqueCodigo": tanque_codigo,
                        "empresaCodigo": empresa,
                        "empresaNome": record.get("empresaNome"),
                        "combustivelTipo": tank.get("produtoDescricao") or record.get("combustivelTipo"),
                        "estoqueInicial": 0.0,
                        "entradasNf": 0.0,
                        "saidasVendas": 0.0,
                        "estoqueMedido": 0.0,
                        "precoMedio": None,
                        "count": 0,
                    }

                agg = tank_aggregates[key]
                agg["estoqueInicial"] = float(tank.get("estoqueInicial") or agg["estoqueInicial"])
                agg["entradasNf"] += float(tank.get("entradaLitros") or tank.get("entrada") or 0)
                agg["saidasVendas"] += float(tank.get("saidaLitros") or tank.get("saida") or 0)
                agg["estoqueMedido"] = float(tank.get("estoqueFinal") or tank.get("estoqueMedido") or agg["estoqueMedido"])

                preco = float(tank.get("precoCusto") or tank.get("precoMedio") or 0)
                if preco > 0:
                    agg["precoMedio"] = preco

                agg["count"] += 1

        return self.reconcile_batch(
            list(tank_aggregates.values()),
            period_start,
            period_end,
        )

    def calculate_thermal_variance(
        self,
        volume_litros: float,
        temp_inicial: float,
        temp_final: float,
        coef_expansao: float = 0.00095,
    ) -> dict[str, float]:
        delta_temp = temp_final - temp_inicial
        variacao_termica = volume_litros * coef_expansao * delta_temp
        return {
            "volume_original": round(volume_litros, 2),
            "temperatura_inicial": temp_inicial,
            "temperatura_final": temp_final,
            "delta_temperatura": round(delta_temp, 2),
            "coeficiente_expansao": coef_expansao,
            "variacao_termica_litros": round(variacao_termica, 2),
            "volume_corrigido": round(volume_litros + variacao_termica, 2),
        }

    def convert_to_anp_reference(
        self,
        volume_litros: float,
        temperatura_atual: float,
        combustivel_tipo: str | None = None,
    ) -> dict[str, float]:
        coef = self._get_expansion_coefficient(combustivel_tipo)
        delta_to_20c = self.ANP_REFERENCE_TEMP - temperatura_atual
        volume_20c = volume_litros * (1 + coef * delta_to_20c)
        return {
            "volume_ambiente": round(volume_litros, 2),
            "temperatura_ambiente": temperatura_atual,
            "volume_20c": round(volume_20c, 2),
            "fator_conversao": round(1 + coef * delta_to_20c, 6),
            "coeficiente": coef,
        }
