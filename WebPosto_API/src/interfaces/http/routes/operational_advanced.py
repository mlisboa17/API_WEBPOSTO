"""Rotas operacionais avançadas — Sprint 46: Perdas, Curva ABC, Ruptura."""

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel, ConfigDict, Field

from src.interfaces.http.authz import require_roles
from src.services.fuel_loss_service import FuelLossService, FuelLossSummary
from src.services.convenience_analytics_service import (
    ConvenienceAnalyticsService,
    ABCCurveSummary,
    StockBreakSummary,
    IdleStockSummary,
)

router = APIRouter(
    prefix="/api/v1/operational",
    tags=["Operational Advanced S46"],
)


class FuelLossResponse(BaseModel):
    model_config = ConfigDict(frozen=True)

    success: bool = True
    data: FuelLossSummary | None = None
    error: str | None = None


class ABCCurveResponse(BaseModel):
    model_config = ConfigDict(frozen=True)

    success: bool = True
    data: ABCCurveSummary | None = None
    error: str | None = None


class StockBreakResponse(BaseModel):
    model_config = ConfigDict(frozen=True)

    success: bool = True
    data: StockBreakSummary | None = None
    error: str | None = None


class IdleStockResponse(BaseModel):
    model_config = ConfigDict(frozen=True)

    success: bool = True
    data: IdleStockSummary | None = None
    error: str | None = None


def _get_fuel_loss_service() -> FuelLossService:
    return FuelLossService()


def _get_convenience_service() -> ConvenienceAnalyticsService:
    return ConvenienceAnalyticsService()


@router.get("/fuel-losses", response_model=FuelLossResponse)
async def fuel_losses_report(
    dataInicial: str = Query(..., pattern=r"^\d{4}-\d{2}-\d{2}$"),
    dataFinal: str = Query(..., pattern=r"^\d{4}-\d{2}-\d{2}$"),
    empresaCodigo: int | None = Query(None),
    toleranciaPct: float = Query(0.6, ge=0.1, le=5.0),
    current_user: dict = Depends(require_roles("director", "admin", "owner", "manager")),
) -> FuelLossResponse:
    from src.services.lmc_intelligence_service import LmcIntelligenceService

    try:
        lmc_service = LmcIntelligenceService()
        lmc_response = await lmc_service.build(dataInicial, dataFinal, empresaCodigo)

        if not lmc_response.success:
            return FuelLossResponse(
                success=False,
                data=None,
                error="Dados LMC indisponíveis para o período",
            )

        lmc_records = lmc_response.data.get("factLmc") or []
        loss_service = FuelLossService(tolerance_pct=toleranciaPct)
        summary = loss_service.extract_from_lmc_data(lmc_records, dataInicial, dataFinal)

        return FuelLossResponse(success=True, data=summary)

    except Exception as e:
        return FuelLossResponse(success=False, error=str(e))


@router.get("/fuel-losses/tank/{tanqueCodigo}")
async def fuel_loss_by_tank(
    tanqueCodigo: int,
    dataInicial: str = Query(..., pattern=r"^\d{4}-\d{2}-\d{2}$"),
    dataFinal: str = Query(..., pattern=r"^\d{4}-\d{2}-\d{2}$"),
    empresaCodigo: int = Query(...),
    current_user: dict = Depends(require_roles("director", "admin", "owner", "manager")),
) -> dict:
    from src.services.lmc_intelligence_service import LmcIntelligenceService

    try:
        lmc_service = LmcIntelligenceService()
        lmc_response = await lmc_service.build(dataInicial, dataFinal, empresaCodigo)

        if not lmc_response.success:
            return {"success": False, "error": "Dados LMC indisponíveis"}

        lmc_records = lmc_response.data.get("factLmc") or []
        loss_service = FuelLossService()
        summary = loss_service.extract_from_lmc_data(lmc_records, dataInicial, dataFinal)

        tank_recon = next(
            (r for r in summary.reconciliations if r.tanque_codigo == tanqueCodigo),
            None
        )

        if not tank_recon:
            return {"success": False, "error": f"Tanque {tanqueCodigo} não encontrado"}

        return {"success": True, "data": tank_recon.model_dump()}

    except Exception as e:
        return {"success": False, "error": str(e)}


@router.get("/convenience/abc-curve", response_model=ABCCurveResponse)
async def convenience_abc_curve(
    dataInicial: str = Query(..., pattern=r"^\d{4}-\d{2}-\d{2}$"),
    dataFinal: str = Query(..., pattern=r"^\d{4}-\d{2}-\d{2}$"),
    empresaCodigo: int | None = Query(None),
    limiteA: float = Query(80.0, ge=50.0, le=90.0),
    limiteB: float = Query(95.0, ge=80.0, le=99.0),
    current_user: dict = Depends(require_roles("director", "admin", "owner", "manager")),
) -> ABCCurveResponse:
    from src.services.non_fuel_product_sales_service import NonFuelProductSalesService

    try:
        nf_service = NonFuelProductSalesService()
        nf_response = await nf_service.build(dataInicial, dataFinal, empresaCodigo)

        if not nf_response.success:
            return ABCCurveResponse(
                success=False,
                error="Dados de vendas conveniência indisponíveis",
            )

        products = nf_response.data.get("produtos") or []
        conv_service = ConvenienceAnalyticsService(a_threshold=limiteA, b_threshold=limiteB)
        summary = conv_service.calculate_abc_curve(products, dataInicial, dataFinal, empresaCodigo)

        return ABCCurveResponse(success=True, data=summary)

    except Exception as e:
        return ABCCurveResponse(success=False, error=str(e))


@router.get("/convenience/stock-break", response_model=StockBreakResponse)
async def convenience_stock_breaks(
    dataInicial: str = Query(..., pattern=r"^\d{4}-\d{2}-\d{2}$"),
    dataFinal: str = Query(..., pattern=r"^\d{4}-\d{2}-\d{2}$"),
    empresaCodigo: int | None = Query(None),
    apenasUrgentes: bool = Query(False),
    current_user: dict = Depends(require_roles("director", "admin", "owner", "manager")),
) -> StockBreakResponse:
    from src.services.non_fuel_product_sales_service import NonFuelProductSalesService

    try:
        nf_service = NonFuelProductSalesService()
        nf_response = await nf_service.build(dataInicial, dataFinal, empresaCodigo)

        if not nf_response.success:
            return StockBreakResponse(
                success=False,
                error="Dados de vendas conveniência indisponíveis",
            )

        products = nf_response.data.get("produtos") or []
        conv_service = ConvenienceAnalyticsService()
        abc_curve = conv_service.calculate_abc_curve(products, dataInicial, dataFinal, empresaCodigo)
        summary = conv_service.detect_stock_breaks(abc_curve, dataFinal)

        if apenasUrgentes:
            summary = StockBreakSummary(
                data_analise=summary.data_analise,
                empresa_codigo=summary.empresa_codigo,
                total_rupturas=summary.total_rupturas,
                total_riscos=summary.total_riscos,
                rupturas_curva_a=summary.rupturas_curva_a,
                perda_estimada_dia=summary.perda_estimada_dia,
                items=[i for i in summary.items if i.urgencia in {"IMEDIATA", "ALTA"}],
                alert_level=summary.alert_level,
            )

        return StockBreakResponse(success=True, data=summary)

    except Exception as e:
        return StockBreakResponse(success=False, error=str(e))


@router.get("/convenience/idle-stock", response_model=IdleStockResponse)
async def convenience_idle_stock(
    data: str = Query(..., pattern=r"^\d{4}-\d{2}-\d{2}$"),
    empresaCodigo: int | None = Query(None),
    diasMinimo: int = Query(30, ge=7, le=180),
    current_user: dict = Depends(require_roles("director", "admin", "owner", "manager")),
) -> IdleStockResponse:
    try:
        products_with_idle = _mock_idle_stock_data(empresaCodigo, diasMinimo)

        conv_service = ConvenienceAnalyticsService()
        conv_service.IDLE_DAYS_WARNING = diasMinimo
        summary = conv_service.detect_idle_stock(products_with_idle, data, empresaCodigo)

        return IdleStockResponse(success=True, data=summary)

    except Exception as e:
        return IdleStockResponse(success=False, error=str(e))


def _mock_idle_stock_data(empresa_codigo: int | None, dias_minimo: int) -> list[dict]:
    return [
        {
            "produtoCodigo": 1001,
            "produtoNome": "Energético XYZ 250ml",
            "empresaCodigo": empresa_codigo or 11495,
            "estoqueAtual": 48,
            "precoCusto": 8.50,
            "diasSemVenda": 45,
            "ultimaVenda": "2026-06-10",
            "classificacaoAbc": "C",
        },
        {
            "produtoCodigo": 1002,
            "produtoNome": "Chocolate Premium 100g",
            "empresaCodigo": empresa_codigo or 11495,
            "estoqueAtual": 24,
            "precoCusto": 12.00,
            "diasSemVenda": 72,
            "ultimaVenda": "2026-05-14",
            "classificacaoAbc": "C",
        },
        {
            "produtoCodigo": 1003,
            "produtoNome": "Revista Especial Ed. 45",
            "empresaCodigo": empresa_codigo or 11495,
            "estoqueAtual": 15,
            "precoCusto": 18.00,
            "diasSemVenda": 90,
            "ultimaVenda": "2026-04-26",
            "classificacaoAbc": "C",
        },
    ]


@router.get("/summary")
async def operational_summary(
    dataInicial: str = Query(..., pattern=r"^\d{4}-\d{2}-\d{2}$"),
    dataFinal: str = Query(..., pattern=r"^\d{4}-\d{2}-\d{2}$"),
    empresaCodigo: int | None = Query(None),
    current_user: dict = Depends(require_roles("director", "admin", "owner")),
) -> dict:
    from src.services.lmc_intelligence_service import LmcIntelligenceService
    from src.services.non_fuel_product_sales_service import NonFuelProductSalesService

    try:
        lmc_service = LmcIntelligenceService()
        nf_service = NonFuelProductSalesService()
        loss_service = FuelLossService()
        conv_service = ConvenienceAnalyticsService()

        lmc_response = await lmc_service.build(dataInicial, dataFinal, empresaCodigo)
        nf_response = await nf_service.build(dataInicial, dataFinal, empresaCodigo)

        fuel_summary = None
        if lmc_response.success:
            lmc_records = lmc_response.data.get("factLmc") or []
            fuel_result = loss_service.extract_from_lmc_data(lmc_records, dataInicial, dataFinal)
            fuel_summary = {
                "tanques_analisados": fuel_result.total_tanques_analisados,
                "tanques_criticos": fuel_result.tanques_criticos,
                "perda_total_litros": fuel_result.perda_total_litros,
                "perda_total_reais": fuel_result.perda_total_reais,
                "status": fuel_result.overall_status,
            }

        conv_summary = None
        if nf_response.success:
            products = nf_response.data.get("produtos") or []
            abc_curve = conv_service.calculate_abc_curve(products, dataInicial, dataFinal, empresaCodigo)
            stock_breaks = conv_service.detect_stock_breaks(abc_curve, dataFinal)
            conv_summary = {
                "produtos_curva_a": abc_curve.produtos_a,
                "total_faturamento": abc_curve.total_faturamento,
                "rupturas_ativas": stock_breaks.total_rupturas,
                "rupturas_curva_a": stock_breaks.rupturas_curva_a,
                "perda_estimada_dia": stock_breaks.perda_estimada_dia,
                "status": stock_breaks.alert_level,
            }

        return {
            "success": True,
            "data": {
                "period": {"start": dataInicial, "end": dataFinal},
                "empresa_codigo": empresaCodigo,
                "fuel_losses": fuel_summary,
                "convenience": conv_summary,
            },
        }

    except Exception as e:
        return {"success": False, "error": str(e)}
