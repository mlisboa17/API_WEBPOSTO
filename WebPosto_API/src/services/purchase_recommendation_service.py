"""Serviço de recomendação de compras para conveniência — Sprint 47."""

from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal, ROUND_HALF_UP
from enum import Enum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from src.services.convenience_analytics_service import ABCClassification, StockStatus


class UrgencyLevel(str, Enum):
    """Nível de urgência do pedido."""

    IMEDIATO = "IMEDIATO"
    URGENTE = "URGENTE"
    NORMAL = "NORMAL"
    PREVENTIVO = "PREVENTIVO"


class PurchaseRecommendation(BaseModel):
    """Recomendação de compra para um produto."""

    model_config = ConfigDict(frozen=True)

    produto_codigo: int
    produto_nome: str
    empresa_codigo: int | None = None
    classificacao_abc: ABCClassification
    estoque_atual: float
    venda_media_diaria: float
    dias_cobertura_atual: float | None
    lead_time_dias: int
    estoque_seguranca_dias: int = 7
    quantidade_sugerida: float
    quantidade_minima_pedido: float = 1.0
    custo_unitario: float | None = None
    valor_pedido_estimado: float | None = None
    margem_unitaria: float | None = None
    urgencia: UrgencyLevel
    justificativa: str
    prioridade_score: float


class PurchaseRecommendationSummary(BaseModel):
    """Resumo de recomendações de compra."""

    model_config = ConfigDict(frozen=True)

    data_analise: str
    empresa_codigo: int | None = None
    total_recomendacoes: int = 0
    recomendacoes_urgentes: int = 0
    valor_total_estimado: float = 0.0
    valor_curva_a: float = 0.0
    recommendations: list[PurchaseRecommendation] = Field(default_factory=list)
    generated_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


class PurchaseRecommendationService:
    """Gera recomendações de compra baseado em Curva ABC e dias de cobertura."""

    DEFAULT_LEAD_TIME = 3
    DEFAULT_SAFETY_STOCK_DAYS = 7
    REORDER_POINT_MULTIPLIER = 1.5

    def __init__(
        self,
        default_lead_time: int = DEFAULT_LEAD_TIME,
        safety_stock_days: int = DEFAULT_SAFETY_STOCK_DAYS,
    ) -> None:
        self._lead_time = default_lead_time
        self._safety_days = safety_stock_days

    def calculate_reorder_point(
        self,
        venda_media_diaria: float,
        lead_time: int | None = None,
        safety_days: int | None = None,
    ) -> float:
        lt = lead_time or self._lead_time
        ss = safety_days or self._safety_days
        return venda_media_diaria * (lt + ss)

    def calculate_order_quantity(
        self,
        venda_media_diaria: float,
        estoque_atual: float,
        lead_time: int | None = None,
        safety_days: int | None = None,
        target_days: int = 30,
    ) -> float:
        reorder_point = self.calculate_reorder_point(venda_media_diaria, lead_time, safety_days)
        target_stock = venda_media_diaria * target_days
        quantity = max(0, target_stock - estoque_atual)
        return round(quantity, 2)

    def recommend(
        self,
        produto_codigo: int,
        produto_nome: str,
        estoque_atual: float,
        venda_media_diaria: float,
        classificacao_abc: ABCClassification,
        empresa_codigo: int | None = None,
        lead_time: int | None = None,
        custo_unitario: float | None = None,
        margem_unitaria: float | None = None,
        quantidade_minima: float = 1.0,
    ) -> PurchaseRecommendation | None:
        if venda_media_diaria <= 0:
            return None

        lt = lead_time or self._lead_time
        dias_cobertura = estoque_atual / venda_media_diaria if venda_media_diaria > 0 else None

        reorder_point = self.calculate_reorder_point(venda_media_diaria, lt)

        if estoque_atual >= reorder_point and classificacao_abc == ABCClassification.C:
            return None

        target_days = 30 if classificacao_abc == ABCClassification.A else (21 if classificacao_abc == ABCClassification.B else 14)

        quantidade = self.calculate_order_quantity(
            venda_media_diaria, estoque_atual, lt, self._safety_days, target_days
        )

        if quantidade < quantidade_minima:
            quantidade = quantidade_minima

        urgencia, justificativa = self._determine_urgency(
            estoque_atual, dias_cobertura, lt, classificacao_abc
        )

        prioridade = self._calculate_priority_score(
            classificacao_abc, urgencia, margem_unitaria, dias_cobertura
        )

        valor_pedido = None
        if custo_unitario:
            valor_pedido = round(quantidade * custo_unitario, 2)

        return PurchaseRecommendation(
            produto_codigo=produto_codigo,
            produto_nome=produto_nome,
            empresa_codigo=empresa_codigo,
            classificacao_abc=classificacao_abc,
            estoque_atual=round(estoque_atual, 2),
            venda_media_diaria=round(venda_media_diaria, 4),
            dias_cobertura_atual=round(dias_cobertura, 2) if dias_cobertura else None,
            lead_time_dias=lt,
            estoque_seguranca_dias=self._safety_days,
            quantidade_sugerida=round(quantidade, 2),
            quantidade_minima_pedido=quantidade_minima,
            custo_unitario=custo_unitario,
            valor_pedido_estimado=valor_pedido,
            margem_unitaria=margem_unitaria,
            urgencia=urgencia,
            justificativa=justificativa,
            prioridade_score=prioridade,
        )

    def _determine_urgency(
        self,
        estoque_atual: float,
        dias_cobertura: float | None,
        lead_time: int,
        classificacao_abc: ABCClassification,
    ) -> tuple[UrgencyLevel, str]:
        if estoque_atual <= 0:
            return UrgencyLevel.IMEDIATO, "Produto em ruptura de estoque"

        if dias_cobertura is None:
            return UrgencyLevel.NORMAL, "Sem dados de venda para análise"

        if dias_cobertura < lead_time * 0.5:
            if classificacao_abc == ABCClassification.A:
                return UrgencyLevel.IMEDIATO, f"Curva A com apenas {dias_cobertura:.1f} dias de cobertura"
            return UrgencyLevel.URGENTE, f"Cobertura crítica: {dias_cobertura:.1f} dias < lead time"

        if dias_cobertura < lead_time:
            return UrgencyLevel.URGENTE, f"Cobertura abaixo do lead time ({lead_time} dias)"

        if dias_cobertura < lead_time + self._safety_days:
            return UrgencyLevel.NORMAL, "Próximo do ponto de pedido"

        return UrgencyLevel.PREVENTIVO, "Reposição preventiva recomendada"

    def _calculate_priority_score(
        self,
        classificacao_abc: ABCClassification,
        urgencia: UrgencyLevel,
        margem_unitaria: float | None,
        dias_cobertura: float | None,
    ) -> float:
        abc_score = {ABCClassification.A: 100, ABCClassification.B: 60, ABCClassification.C: 30}
        urgency_score = {
            UrgencyLevel.IMEDIATO: 100,
            UrgencyLevel.URGENTE: 75,
            UrgencyLevel.NORMAL: 50,
            UrgencyLevel.PREVENTIVO: 25,
        }

        base = abc_score.get(classificacao_abc, 50)
        urg = urgency_score.get(urgencia, 50)

        margin_bonus = 0
        if margem_unitaria and margem_unitaria > 0:
            margin_bonus = min(20, margem_unitaria * 2)

        coverage_penalty = 0
        if dias_cobertura is not None and dias_cobertura < 3:
            coverage_penalty = (3 - dias_cobertura) * 10

        return round(base * 0.4 + urg * 0.4 + margin_bonus + coverage_penalty, 2)

    def recommend_batch(
        self,
        products: list[dict[str, Any]],
        empresa_codigo: int | None = None,
    ) -> PurchaseRecommendationSummary:
        recommendations: list[PurchaseRecommendation] = []

        for p in products:
            abc_raw = p.get("classificacaoAbc") or p.get("classificacao") or "C"
            try:
                classificacao = ABCClassification(abc_raw)
            except ValueError:
                classificacao = ABCClassification.C

            rec = self.recommend(
                produto_codigo=int(p.get("produtoCodigo") or p.get("codigo") or 0),
                produto_nome=str(p.get("produtoNome") or p.get("descricao") or ""),
                estoque_atual=float(p.get("estoqueAtual") or p.get("estoque") or 0),
                venda_media_diaria=float(p.get("vendaMediaDiaria") or p.get("mediaDiaria") or 0),
                classificacao_abc=classificacao,
                empresa_codigo=int(p.get("empresaCodigo") or empresa_codigo or 0),
                lead_time=int(p.get("leadTimeDias") or self._lead_time),
                custo_unitario=float(p.get("precoCusto") or 0) if p.get("precoCusto") else None,
                margem_unitaria=float(p.get("margemUnitaria") or 0) if p.get("margemUnitaria") else None,
            )

            if rec:
                recommendations.append(rec)

        recommendations.sort(key=lambda r: -r.prioridade_score)

        urgentes = sum(1 for r in recommendations if r.urgencia in {UrgencyLevel.IMEDIATO, UrgencyLevel.URGENTE})
        valor_total = sum(r.valor_pedido_estimado or 0 for r in recommendations)
        valor_a = sum(
            r.valor_pedido_estimado or 0
            for r in recommendations
            if r.classificacao_abc == ABCClassification.A
        )

        return PurchaseRecommendationSummary(
            data_analise=datetime.now(timezone.utc).strftime("%Y-%m-%d"),
            empresa_codigo=empresa_codigo,
            total_recomendacoes=len(recommendations),
            recomendacoes_urgentes=urgentes,
            valor_total_estimado=round(valor_total, 2),
            valor_curva_a=round(valor_a, 2),
            recommendations=recommendations,
        )
