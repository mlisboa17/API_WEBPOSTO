from __future__ import annotations

from decimal import Decimal

from fastapi import APIRouter, Header, Query

from src.gateway.webposto_client import WebPostoClient
from src.metrics.collector import get_metrics_snapshot
from src.services.abastecimento_service import AbastecimentoService
from src.services.caixa_service import CaixaService
from src.services.expenses_service import ExpensesService
from src.services.fechamento_service import FechamentoService
from src.services.financeiro_service import FinanceiroService
from src.services.analytics_multiselect import build_overview_filters
from src.services.network_financial_overview_service import FinancialOverviewFilters, NetworkFinancialOverviewService
from src.services.operacao_inteligente_service import OperacaoInteligenteService
from src.services.vendas_combustivel_service import VendasCombustivelService

router = APIRouter(prefix="/v1", tags=["WebPosto Enterprise"])

_client = WebPostoClient()
_abastecimento = AbastecimentoService(_client)
_financeiro = FinanceiroService(_client)
_caixa = CaixaService(_client)
_expenses = ExpensesService(_client)
_fechamento = FechamentoService(_caixa)
_vendas_combustivel = VendasCombustivelService(_client)
_operacao_inteligente = OperacaoInteligenteService(
    abastecimento_service=_abastecimento,
    caixa_service=_caixa,
    financeiro_service=_financeiro,
    vendas_combustivel_service=_vendas_combustivel,
)
_network_financial_overview = NetworkFinancialOverviewService(_client)


@router.get("/permissions")
async def permissions() -> dict:
    perms = await _client.discover_permissions(force=False)
    return {"success": True, "data": perms, "error": None}


@router.get("/abastecimento")
async def abastecimento(dataInicial: str = Query(...), dataFinal: str = Query(...)) -> dict:
    resp = await _abastecimento.get_periodo(dataInicial, dataFinal)
    return resp.to_dict()


@router.get("/expenses")
async def expenses(dataInicial: str = Query(...), dataFinal: str = Query(...)) -> dict:
    resp = await _expenses.get_periodo(dataInicial, dataFinal)
    return resp.to_dict()


@router.get("/financeiro")
async def financeiro(dataInicial: str = Query(...), dataFinal: str = Query(...)) -> dict:
    resp = await _financeiro.get_periodo(dataInicial, dataFinal)
    return resp.to_dict()


@router.get("/caixa")
async def caixa(dataInicial: str = Query(...), dataFinal: str = Query(...)) -> dict:
    resp = await _caixa.get_caixa(dataInicial, dataFinal)
    return resp.to_dict()


@router.get("/caixa-apresentado")
async def caixa_apresentado(dataInicial: str = Query(...), dataFinal: str = Query(...)) -> dict:
    resp = await _caixa.get_caixa_apresentado(dataInicial, dataFinal)
    return resp.to_dict()


@router.get("/vendas-combustivel")
async def vendas_combustivel(dataInicial: str = Query(...), dataFinal: str = Query(...)) -> dict:
    resp = await _vendas_combustivel.get_periodo(dataInicial, dataFinal)
    return resp.to_dict()


@router.get("/box-closure")
async def box_closure(
    dataInicial: str = Query(...),
    dataFinal: str = Query(...),
    x_posto_id: str = Header(..., alias="X-Posto-ID"),
) -> dict:
    resp = await _fechamento.get_fechamento(x_posto_id, dataInicial, dataFinal)
    return resp.to_dict()


@router.get("/operacao-inteligente")
async def operacao_inteligente(
    dataInicial: str = Query(...),
    dataFinal: str = Query(...),
    x_posto_id: str = Header(..., alias="X-Posto-ID"),
) -> dict:
    resp = await _operacao_inteligente.get_visao_unificada(x_posto_id, dataInicial, dataFinal)
    return resp.to_dict()


@router.get("/observability")
async def observability() -> dict:
    return {
        "success": True,
        "data": {
            "system": "webposto",
            "metrics": get_metrics_snapshot(),
        },
        "error": None,
    }


@router.get("/network/financial-overview")
async def network_financial_overview(
    dataInicial: str = Query(...),
    dataFinal: str = Query(...),
    empresa: int | None = Query(None),
    tipoDespesa: str | None = Query(None),
    planoContaCodigo: int | None = Query(None),
    planoConta: str | None = Query(None),
    centroCusto: str | None = Query(None),
    valorMin: Decimal | None = Query(None),
    valorMax: Decimal | None = Query(None),
    status: str | None = Query(None),
    origem: str | None = Query(None),
    fornecedor: str | None = Query(None),
    vencimentoInicial: str | None = Query(None),
    vencimentoFinal: str | None = Query(None),
) -> dict:
    filters = FinancialOverviewFilters(
        data_inicial=dataInicial,
        data_final=dataFinal,
        empresa_codigo=empresa,
        tipo_despesa=tipoDespesa,
        plano_conta_codigo=planoContaCodigo,
        plano_conta=planoConta,
        centro_custo=centroCusto,
        valor_min=valorMin,
        valor_max=valorMax,
        status=status,
        origem=origem,
        fornecedor=fornecedor,
        vencimento_inicial=vencimentoInicial,
        vencimento_final=vencimentoFinal,
    )
    resp = await _network_financial_overview.get_financial_overview(filters)
    return resp.to_dict()


@router.get("/financial/overview")
async def financial_overview(
    dataInicial: str = Query(...),
    dataFinal: str = Query(...),
    empresaCodigo: str | None = Query(None, description="Codigo ou lista separada por virgula"),
    tipoDespesa: str | None = Query(None),
    planoConta: str | None = Query(None),
    centroCusto: str | None = Query(None),
    valorMin: Decimal | None = Query(None),
    valorMax: Decimal | None = Query(None),
    origem: str | None = Query(None),
) -> dict:
    filters = build_overview_filters(dataInicial, dataFinal, empresaCodigo, centroCusto, tipoDespesa)
    filters = FinancialOverviewFilters(
        data_inicial=filters.data_inicial,
        data_final=filters.data_final,
        empresa_codigo=filters.empresa_codigo,
        empresa_codigos=filters.empresa_codigos,
        tipo_despesa=filters.tipo_despesa,
        plano_conta=planoConta,
        centro_custo=filters.centro_custo,
        valor_min=valorMin,
        valor_max=valorMax,
        origem=origem,
    )
    resp = await _network_financial_overview.get_financial_overview_only(filters)
    return resp.to_dict()



@router.get("/financial/companies")
async def financial_companies() -> dict:
    resp = await _network_financial_overview.get_companies()
    return resp.to_dict()


@router.get("/financial/expenses")
async def financial_expenses(
    dataInicial: str = Query(...),
    dataFinal: str = Query(...),
    empresaCodigo: str | None = Query(None, description="Codigo ou lista separada por virgula"),
    tipoDespesa: str | None = Query(None),
    planoConta: str | None = Query(None),
    centroCusto: str | None = Query(None),
    valorMin: Decimal | None = Query(None),
    valorMax: Decimal | None = Query(None),
    origem: str | None = Query(None),
    page: int = Query(1),
    limit: int = Query(50),
) -> dict:
    base = build_overview_filters(dataInicial, dataFinal, empresaCodigo, centroCusto, tipoDespesa)
    filters = FinancialOverviewFilters(
        data_inicial=base.data_inicial,
        data_final=base.data_final,
        empresa_codigo=base.empresa_codigo,
        empresa_codigos=base.empresa_codigos,
        tipo_despesa=base.tipo_despesa,
        plano_conta=planoConta,
        centro_custo=base.centro_custo,
        valor_min=valorMin,
        valor_max=valorMax,
        origem=origem,
    )
    resp = await _network_financial_overview.get_financial_expenses(filters, page=page, limit=limit)
    return resp.to_dict()


@router.get("/financial/accounts-payable")
async def financial_accounts_payable(
    dataInicial: str = Query(...),
    dataFinal: str = Query(...),
    empresaCodigo: str | None = Query(None, description="Codigo ou lista separada por virgula"),
    status: str | None = Query(None),
    fornecedor: str | None = Query(None),
    vencimentoInicial: str | None = Query(None),
    vencimentoFinal: str | None = Query(None),
    page: int = Query(1),
    limit: int = Query(50),
) -> dict:
    base = build_overview_filters(dataInicial, dataFinal, empresaCodigo)
    filters = FinancialOverviewFilters(
        data_inicial=base.data_inicial,
        data_final=base.data_final,
        empresa_codigo=base.empresa_codigo,
        empresa_codigos=base.empresa_codigos,
        status=status,
        fornecedor=fornecedor,
        vencimento_inicial=vencimentoInicial,
        vencimento_final=vencimentoFinal,
    )
    resp = await _network_financial_overview.get_accounts_payable(filters, page=page, limit=limit)
    return resp.to_dict()


@router.get("/financial/accounts-receivable")
async def financial_accounts_receivable(
    dataInicial: str = Query(...),
    dataFinal: str = Query(...),
    empresaCodigo: str | None = Query(None, description="Codigo ou lista separada por virgula"),
    page: int = Query(1),
    limit: int = Query(50),
) -> dict:
    base = build_overview_filters(dataInicial, dataFinal, empresaCodigo)
    filters = FinancialOverviewFilters(
        data_inicial=base.data_inicial,
        data_final=base.data_final,
        empresa_codigo=base.empresa_codigo,
        empresa_codigos=base.empresa_codigos,
    )
    resp = await _network_financial_overview.get_accounts_receivable(filters, page=page, limit=limit)
    return resp.to_dict()


@router.get("/sales")
async def sales(
    dataInicial: str = Query(...),
    dataFinal: str = Query(...),
    empresaCodigo: str | None = Query(None, description="Codigo ou lista separada por virgula"),
    page: int = Query(1),
    limit: int = Query(50),
) -> dict:
    base = build_overview_filters(dataInicial, dataFinal, empresaCodigo)
    filters = FinancialOverviewFilters(
        data_inicial=base.data_inicial,
        data_final=base.data_final,
        empresa_codigo=base.empresa_codigo,
        empresa_codigos=base.empresa_codigos,
    )
    resp = await _network_financial_overview.get_sales(filters, page=page, limit=limit)
    return resp.to_dict()


@router.get("/stock")
async def stock(
    dataInicial: str = Query(...),
    dataFinal: str = Query(...),
    empresaCodigo: str | None = Query(None, description="Codigo ou lista separada por virgula"),
    page: int = Query(1),
    limit: int = Query(50),
) -> dict:
    base = build_overview_filters(dataInicial, dataFinal, empresaCodigo)
    filters = FinancialOverviewFilters(
        data_inicial=base.data_inicial,
        data_final=base.data_final,
        empresa_codigo=base.empresa_codigo,
        empresa_codigos=base.empresa_codigos,
    )
    resp = await _network_financial_overview.get_stock(filters, page=page, limit=limit)
    return resp.to_dict()
