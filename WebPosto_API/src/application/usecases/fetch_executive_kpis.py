"""
Use case: KPIs executivos com Adelaide Tax Engine e graceful fallback.
"""

from __future__ import annotations

from datetime import date, timedelta
from decimal import Decimal
from typing import Any, Optional

from pydantic import BaseModel, ConfigDict, Field

from src.domain.adelaide.tax_profile import ExecutiveKpiSummary, agregar_abastecimentos
from src.shared.datetime_br import hoje_recife

ROLES_MASK_SENSITIVE = frozenset({"operador", "caixa", "vendedor", "guest", "convidado"})


class FetchExecutiveKpisRequest(BaseModel):
    model_config = ConfigDict(frozen=True)

    data_inicial: date
    data_final: date
    periodo_label: str = "custom"
    role: str = "director"
    filial: Optional[list[int]] = None
    codigos_produto: Optional[list[str]] = None
    apenas_combustivel: bool = False
    excluir_afericao: bool = True
    incluir_vendas_pdv: bool = False
    strict: bool = True


class FetchExecutiveKpisResponse(BaseModel):
    model_config = ConfigDict(frozen=True)

    periodo: str
    kpis: ExecutiveKpiSummary
    anomalias_caixa: list[dict[str, Any]] = Field(default_factory=list)
    qtd_abastecimentos: int = 0
    qtd_itens_venda: int = 0
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
        "diretoria",
        "president",
        "presidente",
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

    from src.domain.adelaide.abastecimento_filters import (
        aplicar_filtros_abastecimento,
        normalizar_registro_valor,
    )

    registros: list[dict[str, Any]] = []
    caixa_rows: list[dict[str, Any]] = []
    fallback = False
    mensagem: Optional[str] = None

    try:
        import asyncio
        from src.infrastructure.clients.webposto_pagination import fetch_all_abastecimento
        registros = await asyncio.to_thread(
            fetch_all_abastecimento,
            webposto_client.abastecimento,
            request.data_inicial,
            request.data_final,
            filial=request.filial,
        )
        registros = [
            normalizar_registro_valor(r)
            for r in aplicar_filtros_abastecimento(
                registros,
                excluir_afericao=request.excluir_afericao,
                codigos_produto=request.codigos_produto,
                apenas_combustivel=request.apenas_combustivel,
            )
        ]
    except Exception as exc:
        if request.strict:
            raise
        fallback = True
        mensagem = f"Falha abastecimento: {exc!s}"
        registros = []

    try:
        import asyncio
        caixa_rows = await asyncio.to_thread(
            webposto_client.financeiro.listar_fechamento_caixa,
            request.data_inicial,
            request.data_final
        )
        if not isinstance(caixa_rows, list):
            caixa_rows = (
                caixa_rows.get("resultados", [])
                if isinstance(caixa_rows, dict)
                else []
            )
    except Exception:
        caixa_rows = []

    despesas = _soma_despesas_caixa(caixa_rows)
    summary = agregar_abastecimentos(registros)
    qtd_venda = 0
    faturamento_nao_combustivel = Decimal("0")

    if request.incluir_vendas_pdv:
        from src.application.usecases.fetch_vendas_periodo import fetch_vendas_periodo
        from src.domain.adelaide.vendas_aggregator import (
            extrair_linhas_venda,
            mesclar_summaries_adelaide,
        )

        try:
            vendas_raw = await fetch_vendas_periodo(
                webposto_client,
                request.data_inicial,
                request.data_final,
                filial=request.filial,
            )
            faturamento_nao_combustivel = sum(
                Decimal(str(v.get("totalVenda") or 0))
                for v in vendas_raw
                if v.get("cancelada") != "S"
            )
            linhas_venda = extrair_linhas_venda(
                vendas_raw,
                codigos_produto=request.codigos_produto,
            )
            qtd_venda = len(linhas_venda)
            if linhas_venda:
                sum_venda = agregar_abastecimentos(linhas_venda)
                summary = mesclar_summaries_adelaide(summary, sum_venda)
        except Exception as exc:
            if request.strict:
                raise
            mensagem = (mensagem or "") + f" VENDA parcial: {exc!s}"

    summary = summary.model_copy(
        update={
            "periodo": request.periodo_label,
            "fallback": fallback,
            "mensagem": mensagem,
            "despesas_caixa": despesas,
            "faturamento_nao_combustivel": faturamento_nao_combustivel,
        }
    )
    summary = _mask_if_needed(summary, request.role)
    anomalias = detectar_anomalias_caixa(caixa_rows)

    return FetchExecutiveKpisResponse(
        periodo=request.periodo_label,
        kpis=summary,
        anomalias_caixa=anomalias,
        qtd_abastecimentos=len(registros),
        qtd_itens_venda=qtd_venda,
        ok=not fallback,
        fallback=fallback,
        mensagem=mensagem,
    )


def _soma_despesas_caixa(caixa_rows: list[dict[str, Any]]) -> Decimal:
    """Soma sangrias, despesas e saídas registradas nos turnos de caixa."""
    total = Decimal("0")
    for row in caixa_rows:
        for campo in (
            "valorDespesa",
            "despesa",
            "valorSangria",
            "sangria",
            "valorSaida",
            "valorRetirada",
        ):
            if row.get(campo) is not None:
                try:
                    total += Decimal(str(row[campo]))
                except Exception:
                    pass
        tipo = str(row.get("tipoMovimento") or row.get("tipo") or "").lower()
        if any(x in tipo for x in ("sangria", "despesa", "saída", "saida")):
            for campo in ("valor", "valorTotal", "valorMovimento"):
                if row.get(campo) is not None:
                    try:
                        total += Decimal(str(row[campo]))
                    except Exception:
                        pass
                    break
    return total.quantize(Decimal("0.01"))


def periodo_preset(nome: str) -> tuple[date, date, str]:
    hoje = hoje_recife()
    nome_l = (nome or "hoje").lower()
    if nome_l in ("hoje", "today"):
        return hoje, hoje, "Hoje"
    if nome_l in ("7d", "7dias", "semana"):
        return hoje - timedelta(days=6), hoje, "7D"
    if nome_l in ("30d", "30dias", "mes", "mensal"):
        return hoje - timedelta(days=29), hoje, "30D"
    return hoje, hoje, nome
