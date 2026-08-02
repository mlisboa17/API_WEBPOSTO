"""Serviço de Ciclo de Caixa e Vácuo Financeiro — Sprint 48."""

from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal, ROUND_HALF_UP
from enum import Enum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class CashCycleStatus(str, Enum):
    """Status do ciclo de caixa."""

    SAUDAVEL = "SAUDAVEL"
    ATENCAO = "ATENCAO"
    CRITICO = "CRITICO"


class PaymentMethodTiming(BaseModel):
    """Prazo de recebimento por método de pagamento."""

    model_config = ConfigDict(frozen=True)

    method: str
    days_to_receive: int
    volume_pct: float = 0.0
    weighted_days: float = 0.0


class SupplierPaymentTiming(BaseModel):
    """Prazo de pagamento a fornecedores."""

    model_config = ConfigDict(frozen=True)

    supplier_type: str
    average_payment_days: int
    volume_pct: float = 0.0
    weighted_days: float = 0.0


class CashCycleAnalysis(BaseModel):
    """Análise completa do ciclo de caixa."""

    model_config = ConfigDict(frozen=True)

    period_start: str
    period_end: str
    empresa_codigo: int | None = None

    prazo_medio_recebimento_dias: float
    prazo_medio_pagamento_dias: float
    vacuo_financeiro_dias: float
    faturamento_diario_medio: float
    necessidade_capital_giro_rs: float

    receivables_breakdown: list[PaymentMethodTiming] = Field(default_factory=list)
    payables_breakdown: list[SupplierPaymentTiming] = Field(default_factory=list)

    status: CashCycleStatus = CashCycleStatus.SAUDAVEL
    alert_message: str | None = None

    custo_oportunidade_mensal_pct: float = 1.5
    custo_oportunidade_rs: float = 0.0

    generated_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


DEFAULT_RECEIVABLE_DAYS = {
    "CREDITO": 30,
    "CREDIT": 30,
    "CARTAO_CREDITO": 30,
    "DEBITO": 1,
    "DEBIT": 1,
    "CARTAO_DEBITO": 1,
    "PIX": 0,
    "DINHEIRO": 0,
    "CASH": 0,
    "TRANSFERENCIA": 0,
    "FROTISTA": 15,
    "PRAZO": 30,
}

DEFAULT_SUPPLIER_DAYS = {
    "COMBUSTIVEL": 3,
    "DISTRIBUIDORA": 3,
    "CONVENIENCIA": 14,
    "LUBRIFICANTES": 21,
    "SERVICOS": 30,
    "DEFAULT": 7,
}


class CashCycleService:
    """Calcula ciclo de caixa, vácuo financeiro e necessidade de capital de giro."""

    DEFAULT_FUEL_PAYMENT_DAYS = 3
    TAXA_ANTECIPACAO_MENSAL_PCT = 1.5

    def __init__(
        self,
        fuel_payment_days: int = DEFAULT_FUEL_PAYMENT_DAYS,
        taxa_antecipacao_pct: float = TAXA_ANTECIPACAO_MENSAL_PCT,
    ) -> None:
        self._fuel_days = fuel_payment_days
        self._taxa_antecipacao = taxa_antecipacao_pct

    def _get_receivable_days(self, method: str) -> int:
        normalized = method.upper().strip().replace(" ", "_")
        return DEFAULT_RECEIVABLE_DAYS.get(normalized, 15)

    def _get_supplier_days(self, supplier_type: str) -> int:
        normalized = supplier_type.upper().strip()
        return DEFAULT_SUPPLIER_DAYS.get(normalized, DEFAULT_SUPPLIER_DAYS["DEFAULT"])

    def calculate_receivable_timing(
        self,
        sales_by_method: dict[str, float],
    ) -> tuple[float, list[PaymentMethodTiming]]:
        total_sales = sum(sales_by_method.values())
        if total_sales <= 0:
            return 0.0, []

        breakdown: list[PaymentMethodTiming] = []
        weighted_sum = 0.0

        for method, value in sales_by_method.items():
            days = self._get_receivable_days(method)
            pct = value / total_sales * 100
            weighted = days * (value / total_sales)
            weighted_sum += weighted

            breakdown.append(PaymentMethodTiming(
                method=method,
                days_to_receive=days,
                volume_pct=round(pct, 2),
                weighted_days=round(weighted, 2),
            ))

        return round(weighted_sum, 2), sorted(breakdown, key=lambda x: -x.volume_pct)

    def calculate_payable_timing(
        self,
        purchases_by_type: dict[str, float] | None = None,
        fuel_payment_days: int | None = None,
    ) -> tuple[float, list[SupplierPaymentTiming]]:
        if not purchases_by_type:
            days = fuel_payment_days or self._fuel_days
            return float(days), [
                SupplierPaymentTiming(
                    supplier_type="COMBUSTIVEL",
                    average_payment_days=days,
                    volume_pct=100.0,
                    weighted_days=float(days),
                )
            ]

        total_purchases = sum(purchases_by_type.values())
        if total_purchases <= 0:
            return float(self._fuel_days), []

        breakdown: list[SupplierPaymentTiming] = []
        weighted_sum = 0.0

        for supplier_type, value in purchases_by_type.items():
            days = self._get_supplier_days(supplier_type)
            pct = value / total_purchases * 100
            weighted = days * (value / total_purchases)
            weighted_sum += weighted

            breakdown.append(SupplierPaymentTiming(
                supplier_type=supplier_type,
                average_payment_days=days,
                volume_pct=round(pct, 2),
                weighted_days=round(weighted, 2),
            ))

        return round(weighted_sum, 2), sorted(breakdown, key=lambda x: -x.volume_pct)

    def analyze(
        self,
        period_start: str,
        period_end: str,
        sales_by_method: dict[str, float],
        total_revenue: float,
        days_in_period: int,
        purchases_by_type: dict[str, float] | None = None,
        empresa_codigo: int | None = None,
    ) -> CashCycleAnalysis:
        prazo_recebimento, recv_breakdown = self.calculate_receivable_timing(sales_by_method)
        prazo_pagamento, pay_breakdown = self.calculate_payable_timing(purchases_by_type)

        vacuo = prazo_recebimento - prazo_pagamento
        faturamento_diario = total_revenue / max(days_in_period, 1)
        necessidade_capital = max(0, vacuo * faturamento_diario)

        custo_oportunidade = (necessidade_capital * self._taxa_antecipacao / 100) if vacuo > 0 else 0

        if vacuo <= 0:
            status = CashCycleStatus.SAUDAVEL
            alert = None
        elif vacuo <= 15:
            status = CashCycleStatus.ATENCAO
            alert = f"Vácuo de {vacuo:.0f} dias requer R$ {necessidade_capital:,.2f} de capital de giro"
        else:
            status = CashCycleStatus.CRITICO
            alert = f"Vácuo crítico de {vacuo:.0f} dias. Necessidade: R$ {necessidade_capital:,.2f}"

        return CashCycleAnalysis(
            period_start=period_start,
            period_end=period_end,
            empresa_codigo=empresa_codigo,
            prazo_medio_recebimento_dias=prazo_recebimento,
            prazo_medio_pagamento_dias=prazo_pagamento,
            vacuo_financeiro_dias=round(vacuo, 2),
            faturamento_diario_medio=round(faturamento_diario, 2),
            necessidade_capital_giro_rs=round(necessidade_capital, 2),
            receivables_breakdown=recv_breakdown,
            payables_breakdown=pay_breakdown,
            status=status,
            alert_message=alert,
            custo_oportunidade_mensal_pct=self._taxa_antecipacao,
            custo_oportunidade_rs=round(custo_oportunidade, 2),
        )

    def simulate_antecipation(
        self,
        valor_recebivel: float,
        dias_antecipacao: int,
        taxa_mensal_pct: float | None = None,
    ) -> dict[str, float]:
        taxa = taxa_mensal_pct or self._taxa_antecipacao
        taxa_diaria = taxa / 30
        custo = valor_recebivel * (taxa_diaria / 100) * dias_antecipacao
        valor_liquido = valor_recebivel - custo

        return {
            "valor_bruto": round(valor_recebivel, 2),
            "dias_antecipacao": dias_antecipacao,
            "taxa_mensal_pct": taxa,
            "taxa_diaria_pct": round(taxa_diaria, 4),
            "custo_antecipacao": round(custo, 2),
            "valor_liquido": round(valor_liquido, 2),
            "taxa_efetiva_pct": round((custo / valor_recebivel) * 100, 4) if valor_recebivel > 0 else 0,
        }
