"""
Use case: KPIs executivos com Adelaide Tax Engine e graceful fallback.
"""

from __future__ import annotations

from datetime import date, timedelta
from decimal import Decimal
from typing import Any, Optional

from pydantic import BaseModel, ConfigDict, Field

from src.domain.adelaide.tax_profile import ExecutiveKpiSummary, agregar_abastecimentos

ROLES_MASK_SENSITIVE = frozenset({"operador", "caixa", "vendedor"})


class FetchExecutiveKpisRequest(BaseModel):
    model_config = ConfigDict(frozen=True)

    data_inicial: date
    data_final: date
    periodo_label: str = "custom"
    role: str = "director"
    filial: Optional[list[int]] = None


class FetchExecutiveKpisResponse(BaseModel):
    model_config = ConfigDict(frozen=True)

    periodo: str
    kpis: ExecutiveKpiSummary
    anomalias_caixa: list[dict[str, Any]] = Field(default_factory=list)
    ok: bool = True
    fallback: bool = False
    mensagem: Optional[str] = None


def _mask_if_needed(summary: ExecutiveKpiSummary, role: str) -> ExecutiveKpiSummary:
    role_l = (role or "").lower()
    if role_l in ROLES_MASK_SENSITIVE or role_l not in (
        "admin",
        "administrator",
        "director",
        "diretor",
    ):
        return summary.model_copy(
            update={
                "masked": True,
                "faturamento_total": Decimal("0"),
                "custo_total": Decimal("0"),
                "pis_cofins_total": Decimal("0"),
                "taxas_cartao_total": Decimal("0"),
                "margem_liquida_total": Decimal("0"),
                "produtos": [],
                "mensagem": "Dados sensíveis ocultos para o seu perfil.",
            }
        )
    return summary


async def fetch_executive_kpis(
    request: FetchExecutiveKpisRequest,
    webposto_client: Any,
) -> FetchExecutiveKpisResponse:
    """
    Agrega abastecimentos + caixa; em falha 500 retorna fallback estruturado.
    """
    from src.infrastructure.anomaly.caixa_anomaly import detectar_anomalias_caixa

    registros: list[dict[str, Any]] = []
    caixa_rows: list[dict[str, Any]] = []
    fallback = False
    mensagem: Optional[str] = None

    try:
        params: dict[str, Any] = {
            "dataInicial": request.data_inicial.isoformat(),
            "dataFinal": request.data_final.isoformat(),
        }
        if request.filial:
            params["filial"] = request.filial
        registros = webposto_client.abastecimento.listar(
            request.data_inicial, request.data_final
        )
        if not isinstance(registros, list):
            registros = registros.get("resultados", []) if isinstance(registros, dict) else []
    except Exception as exc:
        fallback = True
        mensagem = f"Graceful fallback abastecimento: {exc!s}"
        registros = []

    try:
        caixa_rows = webposto_client.financeiro.listar_fechamento_caixa(
            request.data_inicial, request.data_final
        )
        if not isinstance(caixa_rows, list):
            caixa_rows = (
                caixa_rows.get("resultados", [])
                if isinstance(caixa_rows, dict)
                else []
            )
    except Exception:
        caixa_rows = []

    summary = agregar_abastecimentos(registros)
    summary = summary.model_copy(
        update={"periodo": request.periodo_label, "fallback": fallback, "mensagem": mensagem}
    )
    summary = _mask_if_needed(summary, request.role)
    anomalias = detectar_anomalias_caixa(caixa_rows)

    return FetchExecutiveKpisResponse(
        periodo=request.periodo_label,
        kpis=summary,
        anomalias_caixa=anomalias,
        ok=not fallback,
        fallback=fallback,
        mensagem=mensagem,
    )


def periodo_preset(nome: str) -> tuple[date, date, str]:
    hoje = date.today()
    nome_l = (nome or "hoje").lower()
    if nome_l in ("hoje", "today"):
        return hoje, hoje, "Hoje"
    if nome_l in ("7d", "7dias", "semana"):
        return hoje - timedelta(days=6), hoje, "7D"
    if nome_l in ("30d", "30dias", "mes"):
        return hoje - timedelta(days=29), hoje, "30D"
    return hoje, hoje, nome
