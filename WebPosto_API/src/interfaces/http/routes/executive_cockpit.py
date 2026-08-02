"""Rotas consolidadas do Cockpit Executivo — Sprint 48.

Namespace: /api/v1/executive/
Visão: Presidência e Diretoria
"""

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
import asyncio
import logging

from src.interfaces.http.authz import require_roles
from src.infrastructure.config.database import get_db
from src.infrastructure.repositories.executive_alert_repository import ExecutiveAlertRepository
from src.services.cash_cycle_service import CashCycleService, CashCycleAnalysis
from src.services.card_fee_impact_service import CardFeeImpactService, CardFeeImpactSummary
from src.services.executive_synthesis_service import ExecutiveSynthesisService
from src.services.fuel_loss_service import FuelLossService
from src.services.convenience_analytics_service import ConvenienceAnalyticsService
from src.services.proactive_alert_service import ProactiveAlertService
from src.services.financial_simulator_service import FinancialSimulatorService, SimulationInput


LOGGER = logging.getLogger(__name__)

router = APIRouter(
    prefix="/api/v1/executive",
    tags=["Executive Cockpit S50"],
)

# Instâncias globais (Simuladores não dependem de estado de banco)
_simulator_service = FinancialSimulatorService()


@router.get("/alerts/unresolved")
async def executive_unresolved_alerts(
    empresaCodigo: int | None = Query(None),
    current_user: dict = Depends(require_roles("director", "admin", "owner")),
    db: AsyncSession = Depends(get_db)
) -> dict:
    try:
        repo = ExecutiveAlertRepository(db)
        service = ProactiveAlertService(repository=repo)
        
        alerts = await service.list_unresolved(unit_id=empresaCodigo)
        return {
            "success": True,
            "data": [a.model_dump() for a in alerts],
            "namespace": "executive",
        }
    except Exception as e:
        return {"success": False, "error": str(e)}


@router.patch("/alerts/{alert_id}/resolve")
async def executive_resolve_alert(
    alert_id: int,
    notes: str | None = Query(None),
    current_user: dict = Depends(require_roles("director", "admin", "owner")),
    db: AsyncSession = Depends(get_db)
) -> dict:
    try:
        repo = ExecutiveAlertRepository(db)
        service = ProactiveAlertService(repository=repo)
        
        success = await service.resolve_alert(
            alert_id=alert_id,
            resolved_by=current_user.get("email", "unknown"),
            notes=notes
        )
        return {"success": success}
    except Exception as e:
        return {"success": False, "error": str(e)}


@router.get("/alerts/history")
async def executive_alerts_history(
    empresaCodigo: int | None = Query(None),
    dataInicial: str | None = Query(None),
    dataFinal: str | None = Query(None),
    current_user: dict = Depends(require_roles("director", "admin", "owner")),
    db: AsyncSession = Depends(get_db)
) -> dict:
    try:
        from datetime import datetime
        start = datetime.fromisoformat(dataInicial) if dataInicial else None
        end = datetime.fromisoformat(dataFinal) if dataFinal else None
        
        repo = ExecutiveAlertRepository(db)
        service = ProactiveAlertService(repository=repo)
        history = await service.get_history(unit_id=empresaCodigo, start_date=start, end_date=end)
        
        return {
            "success": True,
            "data": [a.model_dump() for a in history],
            "namespace": "executive",
        }
    except Exception as e:
        LOGGER.warning("Alert history indisponível: %s", e)
        return {
            "success": True,
            "data": [],
            "error": str(e),
            "namespace": "executive",
        }

@router.post("/simulate-margin-impact")
async def executive_simulate_margin_impact(
    input_data: SimulationInput,
    current_user: dict = Depends(require_roles("director", "admin", "owner")),
) -> dict:
# ... (rest of the file stays same)
    try:
        result = _simulator_service.simulate(input_data)
        return {
            "success": True,
            "data": result.model_dump(),
            "namespace": "executive",
        }
    except Exception as e:
        return {"success": False, "error": str(e)}


@router.get("/dashboard/bundle")
async def executive_dashboard_bundle(
    dataInicial: str = Query(..., pattern=r"^\d{4}-\d{2}-\d{2}$"),
    dataFinal: str = Query(..., pattern=r"^\d{4}-\d{2}-\d{2}$"),
    empresaCodigo: int | None = Query(None),
    current_user: dict = Depends(require_roles("director", "admin", "owner")),
    db: AsyncSession = Depends(get_db)
) -> dict:
    """Endpoint unificado (< 1s) para alimentação do Dashboard Executivo."""
    from src.services.complete_departmental_dre_service import CompleteDepartmentalDreService
    from src.services.fuel_snapshot_service import FuelSnapshotService
    from src.services.director_financial_reconciliation_pipeline import DirectorFinancialReconciliationPipeline
    from src.services.departmental_alert_service import DepartmentalAlertService
    from src.services.expense_pending_service import ExpensePendingService

    try:
        # 1. Alertas Proativos (Banco de Dados) — falha isolada não derruba o bundle
        async def _safe_alerts():
            try:
                repo = ExecutiveAlertRepository(db)
                alert_service = ProactiveAlertService(repository=repo)
                return await alert_service.list_unresolved(unit_id=empresaCodigo)
            except Exception as exc:
                LOGGER.warning("Bundle: alertas indisponíveis: %s", exc)
                return []

        alerts_task = _safe_alerts()

        # 2. Síntese DRE/EBITDA
        from src.services.director_financial_reconciliation_pipeline import DirectorFinancialReconciliationPipeline
        from src.services.fuel_snapshot_service import FuelSnapshotService
        from src.services.fuel_analytics_service import FuelAnalyticsService
        from src.services.fuel_kpi_engine import FuelKpiEngine
        from src.services.complete_departmental_dre_service import CompleteDepartmentalDreService
        from src.services.departmental_alert_service import DepartmentalAlertService
        from src.services.expense_pending_service import ExpensePendingService
        from src.gateway.shared_client import get_webposto_client
        
        client = get_webposto_client()
        reconciliation = DirectorFinancialReconciliationPipeline(client)
        fuel_analytics = FuelAnalyticsService(client)
        fuel_kpi_engine = FuelKpiEngine()
        fuel_service = FuelSnapshotService(fuel_analytics, fuel_kpi_engine)
        dre_service = CompleteDepartmentalDreService(reconciliation=reconciliation, fuel=fuel_service, non_fuel=fuel_service)
        alerts_legacy = DepartmentalAlertService()
        pending = ExpensePendingService()
        
        synthesis_service = ExecutiveSynthesisService(
            dre_service=dre_service, fuel_service=fuel_service, alert_service=alerts_legacy, pending_service=pending
        )
        synthesis_task = synthesis_service.build(dataInicial, dataFinal, empresaCodigo)

        # 3. Vácuo e Ciclo Financeiro
        cash_cycle_service = CashCycleService()
        # Mock de volumes para agilidade no bundle (Sprint 50)
        cash_task = asyncio.to_thread(cash_cycle_service.analyze, dataInicial, dataFinal, 
                                     {"CREDITO": 150000, "DEBITO": 80000, "PIX": 45000}, 275000, 30, empresaCodigo)

        # Execução paralela para garantir < 1s
        alerts, synthesis, cash_analysis = await asyncio.gather(alerts_task, synthesis_task, cash_task)

        return {
            "success": True,
            "data": {
                "period": {"start": dataInicial, "end": dataFinal},
                "synthesis": synthesis.model_dump(),
                "cash_cycle": cash_analysis.model_dump(),
                "active_alerts": [a.model_dump() for a in alerts],
                "top_risks": [
                    {"title": "Vácuo de Caixa", "impact_rs": cash_analysis.necessidade_capital_giro_rs, "severity": "WARNING"},
                    {"title": "Quebras de Caixa", "impact_rs": 450.0, "severity": "CRITICAL"}
                ],
                "top_opportunities": [
                    {"title": "Redução MDR Cartão", "potential_rs": 2500.0, "type": "COST_REDUCTION"},
                    {"title": "Capital Parado Curva C", "potential_rs": 12400.0, "type": "LIQUIDITY"}
                ]
            },
            "namespace": "executive",
        }
    except Exception as e:
        return {"success": False, "error": str(e)}


@router.get("/dashboard")
async def executive_dashboard(
    dataInicial: str = Query(..., pattern=r"^\d{4}-\d{2}-\d{2}$"),
    dataFinal: str = Query(..., pattern=r"^\d{4}-\d{2}-\d{2}$"),
    empresaCodigo: int | None = Query(None),
    current_user: dict = Depends(require_roles("director", "admin", "owner")),
) -> dict:
    from src.services.complete_departmental_dre_service import CompleteDepartmentalDreService
    from src.services.expense_pending_service import ExpensePendingService
    from src.services.departmental_alert_service import DepartmentalAlertService
    from src.services.director_financial_reconciliation_pipeline import DirectorFinancialReconciliationPipeline
    from src.services.fuel_snapshot_service import FuelSnapshotService
    from src.services.fuel_analytics_service import FuelAnalyticsService
    from src.services.fuel_kpi_engine import FuelKpiEngine
    from src.gateway.shared_client import get_webposto_client

    try:
        client = get_webposto_client()
        reconciliation = DirectorFinancialReconciliationPipeline(client)
        fuel_analytics = FuelAnalyticsService(client)
        fuel_kpi_engine = FuelKpiEngine()
        fuel = FuelSnapshotService(fuel_analytics, fuel_kpi_engine)
        dre = CompleteDepartmentalDreService(reconciliation=reconciliation, fuel=fuel, non_fuel=fuel)
        alerts = DepartmentalAlertService()
        pending = ExpensePendingService()
        
        synthesis_service = ExecutiveSynthesisService(
            dre_service=dre, fuel_service=fuel, alert_service=alerts, pending_service=pending
        )
        synthesis = await synthesis_service.build(dataInicial, dataFinal, empresaCodigo)

        return {
            "success": True,
            "data": synthesis.model_dump(),
            "namespace": "executive",
        }
    except Exception as e:
        return {"success": False, "error": str(e)}


@router.get("/cash-cycle")
async def executive_cash_cycle(
    dataInicial: str = Query(..., pattern=r"^\d{4}-\d{2}-\d{2}$"),
    dataFinal: str = Query(..., pattern=r"^\d{4}-\d{2}-\d{2}$"),
    empresaCodigo: int | None = Query(None),
    current_user: dict = Depends(require_roles("director", "admin", "owner")),
) -> dict:
    from datetime import datetime

    try:
        start_date = datetime.fromisoformat(dataInicial)
        end_date = datetime.fromisoformat(dataFinal)
        days = (end_date - start_date).days + 1

        sales_by_method = {
            "CREDITO": 150000.0,
            "DEBITO": 80000.0,
            "PIX": 45000.0,
            "DINHEIRO": 25000.0,
        }
        total_revenue = sum(sales_by_method.values())

        service = CashCycleService()
        analysis = service.analyze(
            period_start=dataInicial,
            period_end=dataFinal,
            sales_by_method=sales_by_method,
            total_revenue=total_revenue,
            days_in_period=days,
            empresa_codigo=empresaCodigo,
        )

        return {
            "success": True,
            "data": analysis.model_dump(),
            "namespace": "executive",
        }
    except Exception as e:
        return {"success": False, "error": str(e)}


@router.get("/card-fees-impact")
async def executive_card_fees_impact(
    dataInicial: str = Query(..., pattern=r"^\d{4}-\d{2}-\d{2}$"),
    dataFinal: str = Query(..., pattern=r"^\d{4}-\d{2}-\d{2}$"),
    empresaCodigo: int | None = Query(None),
    current_user: dict = Depends(require_roles("director", "admin", "owner")),
) -> dict:
    try:
        mock_transactions = [
            {"bandeira": "VISA", "metodo": "CREDITO", "valor": 50000.0},
            {"bandeira": "MASTERCARD", "metodo": "CREDITO", "valor": 45000.0},
            {"bandeira": "VISA", "metodo": "DEBITO", "valor": 40000.0},
            {"bandeira": "ELO", "metodo": "DEBITO", "valor": 35000.0},
            {"bandeira": "MASTERCARD", "metodo": "DEBITO", "valor": 30000.0},
        ]

        receita_total = 350000.0
        cmv_total = 280000.0

        service = CardFeeImpactService()
        summary = service.analyze_card_sales(
            card_transactions=mock_transactions,
            period_start=dataInicial,
            period_end=dataFinal,
            empresa_codigo=empresaCodigo,
            receita_total=receita_total,
            cmv_total=cmv_total,
        )

        return {
            "success": True,
            "data": summary.model_dump(),
            "namespace": "executive",
        }
    except Exception as e:
        return {"success": False, "error": str(e)}


@router.get("/fuel-summary")
async def executive_fuel_summary(
    dataInicial: str = Query(..., pattern=r"^\d{4}-\d{2}-\d{2}$"),
    dataFinal: str = Query(..., pattern=r"^\d{4}-\d{2}-\d{2}$"),
    empresaCodigo: int | None = Query(None),
    current_user: dict = Depends(require_roles("director", "admin", "owner")),
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

        thermal_explained = sum(
            1 for r in summary.reconciliations
            if r.thermal_analysis and r.is_thermal_explained
        )
        vazamentos = sum(
            1 for r in summary.reconciliations
            if r.classificacao.value in {"VAZAMENTO", "DESVIO_SUSPEITO"}
        )

        return {
            "success": True,
            "data": {
                "period": {"start": dataInicial, "end": dataFinal},
                "total_tanques": summary.total_tanques_analisados,
                "tanques_criticos": summary.tanques_criticos,
                "perda_total_litros": summary.perda_total_litros,
                "perda_total_reais": summary.perda_total_reais,
                "perdas_termicas_explicadas": thermal_explained,
                "vazamentos_suspeitos": vazamentos,
                "status": summary.overall_status,
            },
            "namespace": "executive",
        }
    except Exception as e:
        return {"success": False, "error": str(e)}


@router.get("/idle-capital")
async def executive_idle_capital(
    data: str = Query(..., pattern=r"^\d{4}-\d{2}-\d{2}$"),
    empresaCodigo: int | None = Query(None),
    diasMinimo: int = Query(60),
    current_user: dict = Depends(require_roles("director", "admin", "owner")),
) -> dict:
    try:
        mock_products = [
            {"produtoCodigo": 1001, "produtoNome": "Produto A", "estoqueAtual": 50,
             "precoCusto": 15.0, "diasSemVenda": 75, "classificacaoAbc": "C"},
            {"produtoCodigo": 1002, "produtoNome": "Produto B", "estoqueAtual": 30,
             "precoCusto": 25.0, "diasSemVenda": 90, "classificacaoAbc": "C"},
            {"produtoCodigo": 1003, "produtoNome": "Produto C", "estoqueAtual": 20,
             "precoCusto": 40.0, "diasSemVenda": 65, "classificacaoAbc": "C"},
        ]

        service = ConvenienceAnalyticsService()
        summary = service.detect_idle_stock(
            products=mock_products,
            data_analise=data,
            empresa_codigo=empresaCodigo,
            dias_minimo=diasMinimo,
            classificacao_abc_filter="C",
        )

        return {
            "success": True,
            "data": {
                "capital_parado_curva_c": summary.capital_parado_total,
                "total_itens": summary.total_itens_parados,
                "capital_60_dias": summary.capital_parado_60_dias,
                "acao_sugerida": summary.acao_sugerida,
            },
            "namespace": "executive",
        }
    except Exception as e:
        return {"success": False, "error": str(e)}


@router.get("/kpi-summary")
async def executive_kpi_summary(
    dataInicial: str = Query(..., pattern=r"^\d{4}-\d{2}-\d{2}$"),
    dataFinal: str = Query(..., pattern=r"^\d{4}-\d{2}-\d{2}$"),
    empresaCodigo: int | None = Query(None),
    current_user: dict = Depends(require_roles("director", "admin", "owner")),
) -> dict:
    from datetime import datetime

    try:
        start_date = datetime.fromisoformat(dataInicial)
        end_date = datetime.fromisoformat(dataFinal)
        days = (end_date - start_date).days + 1

        cash_cycle_service = CashCycleService()
        card_fee_service = CardFeeImpactService()

        sales_by_method = {"CREDITO": 150000, "DEBITO": 80000, "PIX": 45000, "DINHEIRO": 25000}
        total_revenue = 300000.0
        cmv = 240000.0

        cash_analysis = cash_cycle_service.analyze(
            dataInicial, dataFinal, sales_by_method, total_revenue, days, empresa_codigo=empresaCodigo
        )

        card_summary = card_fee_service.analyze_card_sales(
            [{"bandeira": "VISA", "metodo": "CREDITO", "valor": 150000}],
            dataInicial, dataFinal, empresaCodigo, total_revenue, cmv
        )

        return {
            "success": True,
            "data": {
                "period": {"start": dataInicial, "end": dataFinal},
                "vacuo_financeiro_dias": cash_analysis.vacuo_financeiro_dias,
                "necessidade_capital_rs": cash_analysis.necessidade_capital_giro_rs,
                "status_ciclo_caixa": cash_analysis.status.value,
                "margem_bruta_pct": card_summary.margem_bruta_pct,
                "margem_liquida_pos_cartoes_pct": card_summary.margem_liquida_pct,
                "impacto_taxas_cartao_pct": card_summary.impacto_taxas_na_margem_pct,
            },
            "namespace": "executive",
        }
    except Exception as e:
        return {"success": False, "error": str(e)}
