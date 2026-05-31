"""
Contratos Adelaide para o cockpit Lionda — Pydantic v2 + Decimal(12,4).
"""

from __future__ import annotations

from decimal import Decimal, ROUND_HALF_UP
from enum import Enum
from typing import Any, List, Optional

from pydantic import BaseModel, ConfigDict, Field, field_serializer, field_validator

from src.domain.catalog.grupo_schema import UnidadeWebPosto

DECIMAL_Q = Decimal("0.0001")
ROLES_FULL_ACCESS = frozenset(
    {
        "director",
        "diretor",
        "diretoria",
        "president",
        "presidente",
        "admin",
        "administrator",
    }
)


def quantize_money(value: Decimal) -> Decimal:
    return value.quantize(DECIMAL_Q, rounding=ROUND_HALF_UP)


class PeriodoMetricas(str, Enum):
    hoje = "hoje"
    sete_dias = "7d"
    mensal = "mensal"


class AdelaideDashboardMetrics(BaseModel):
    """Payload estrito do endpoint /api/v1/adelaide/metrics."""

    model_config = ConfigDict(frozen=True, str_strip_whitespace=True)

    faturamento_bruto: Decimal = Field(default=Decimal("0"), ge=0)
    faturamento_nao_combustivel: Decimal = Field(default=Decimal("0"), ge=0)
    galonagem_total: Decimal = Field(default=Decimal("0"), ge=0)
    credito_recuperavel: Decimal = Field(default=Decimal("0"), ge=0)
    despesas_caixa: Decimal = Field(default=Decimal("0"), ge=0)
    margem_liquida_real: Decimal = Field(default=Decimal("0"))
    periodo: str = "30D"
    status_api: str = "demonstracao_offline"
    fallback: bool = True
    dados_reais: bool = False
    mensagem: Optional[str] = None
    unidade: Optional[UnidadeWebPosto] = None
    combustiveis: List[dict[str, Any]] = Field(default_factory=list)
    por_produto: List[dict[str, Any]] = Field(default_factory=list)
    qtd_abastecimentos: int = 0
    qtd_itens_venda: int = 0
    data_inicial: Optional[str] = None
    data_final: Optional[str] = None
    filtros_aplicados: dict[str, Any] = Field(default_factory=dict)
    masked: bool = False

    @field_validator(
        "faturamento_bruto",
        "faturamento_nao_combustivel",
        "galonagem_total",
        "credito_recuperavel",
        "despesas_caixa",
        "margem_liquida_real",
        mode="before",
    )
    @classmethod
    def coerce_decimal(cls, v: Any) -> Decimal:
        if v is None:
            return Decimal("0")
        if isinstance(v, Decimal):
            return quantize_money(v)
        return quantize_money(Decimal(str(v)))

    @field_serializer(
        "faturamento_bruto",
        "faturamento_nao_combustivel",
        "galonagem_total",
        "credito_recuperavel",
        "despesas_caixa",
        "margem_liquida_real",
    )
    def serialize_decimal(self, v: Decimal) -> str:
        return format(quantize_money(v), "f")


def mask_metrics_for_role(metrics: AdelaideDashboardMetrics, role: str) -> AdelaideDashboardMetrics:
    """Oculta valores financeiros para perfis sem privilégio de diretoria."""
    role_l = (role or "").lower().strip()
    if role_l in ROLES_FULL_ACCESS:
        return metrics.model_copy(update={"masked": False})
    return metrics.model_copy(
        update={
            "masked": True,
            "faturamento_bruto": Decimal("0"),
            "faturamento_nao_combustivel": Decimal("0"),
            "credito_recuperavel": Decimal("0"),
            "despesas_caixa": Decimal("0"),
            "margem_liquida_real": Decimal("0"),
            "mensagem": "Dados restritos — perfil sem acesso Diretoria/Presidente.",
        }
    )
