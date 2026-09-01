import asyncio
from contextlib import asynccontextmanager, suppress
from typing import AsyncIterator

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse, RedirectResponse
from starlette.requests import Request
from fastapi.staticfiles import StaticFiles
from pathlib import Path

from src.infrastructure.config.database import close_db, init_db
from src.infrastructure.config.gateway_database import init_gateway_db
from src.infrastructure.config.settings import settings
from src.interfaces.http.routes import clientes, expenses, gateway_expenses, health, sync
from src.interfaces.http.routes import fechamento_enterprise
from src.interfaces.http.routes import auth
from src.interfaces.http.routes import metrics
from src.interfaces.http.routes import analytics
from src.interfaces.http.routes import finance_center
from src.interfaces.http.routes import cash_flow
from src.interfaces.http.routes import cash_operations
from src.interfaces.http.routes import operator_performance
from src.interfaces.http.routes import operator_sales_intelligence
from src.interfaces.http.routes import operator_accountability_incentive
from src.interfaces.http.routes import operator_profitability
from src.interfaces.http.routes import store_shift_profitability
from src.interfaces.http.routes import management_action_center
from src.interfaces.http.routes import goals_campaign_engine
from src.interfaces.http.routes import benchmark_intelligence
from src.interfaces.http.routes import executive_scorecard
from src.interfaces.http.routes import corporate_intelligence_hub
from src.interfaces.http.routes import executive_decision_engine
from src.interfaces.http.routes import action_center
from src.interfaces.http.routes import owner_action_center  # BUILD-01D
from src.interfaces.http.routes import decision_discovery  # VALUE-01
from src.interfaces.http.routes import executive_ai_copilot
from src.interfaces.http.routes import executive_copilot_ask
from src.interfaces.http.routes import autonomous_recommendation_engine
from src.interfaces.http.routes import closed_loop_learning_engine
from src.interfaces.http.routes import nfce_intelligence
from src.interfaces.http.routes import lmc_intelligence
from src.interfaces.http.routes import tax_product_fiscal_intelligence
from src.interfaces.http.routes import fiscal_reconciliation_hub
from src.interfaces.http.routes import fuel_governance
from src.interfaces.http.routes import non_fuel_product_sales
from src.interfaces.http.routes import commercial_execution
from src.interfaces.http.routes import commercial_copilot
from src.interfaces.http.routes import commercial_learning
from src.interfaces.http.routes import statements
from src.interfaces.http.routes import data_trust_baseline
from src.interfaces.http.routes import prestacao_contas
from src.interfaces.http.routes import periodic_audits
from src.interfaces.http.routes import cash_reconciliation
from src.interfaces.http.routes import decisions
from src.interfaces.http.routes import executive_follow_up
from src.interfaces.http.routes import financial_review_inbox
from src.interfaces.http.routes import financial_intelligence
from src.interfaces.http.routes import admin_circuit_breaker
from src.interfaces.http.routes import financial_snapshot_health
from src.interfaces.http.routes import financial_operations
from src.interfaces.http.routes import financial_operations_center
from src.interfaces.http.routes import business_analyst
from src.interfaces.http.routes import governance
from src.interfaces.http.routes import financial_intelligence_center
from src.interfaces.http.routes import director_financial_reconciliation
from src.interfaces.http.routes import departmental_facts
from src.interfaces.http.routes import departmental_kpis
from src.interfaces.http.routes import departmental_governance
from src.interfaces.http.routes import executive_synthesis
from src.interfaces.http.routes import operational_advanced
from src.interfaces.http.routes import expense_mappings
from src.interfaces.http.routes import executive_cockpit
from src.interfaces.http.routes import operational_cockpit
from src.interfaces.http.routes import executive_analytics
from src.interfaces.http.routes import executive_employees
from src.interfaces.http.routes import executive_market
from src.interfaces.http.routes import executive_consolidated_report
from src.interfaces.http.routes import fuel_volumetry
from src.interfaces.http.routes import fuel_demand_intelligence
from src.interfaces.http.routes import expenses_dre
from src.interfaces.http.routes import cockpit_live
from src.interfaces.http.routes import pista_live_feed
from src.interfaces.http.routes import pista_intelligence
from src.interfaces.http.routes import abastecimentos_rest
from src.interfaces.http.routes import product_inspection
from src.interfaces.http.routes import operational_fuel_loss
from src.interfaces.http.routes import debug_fuel_volume
from src.interfaces.http.routes import inventory_prediction
from src.interfaces.http.routes import alert_engine
from src.interfaces.http.routes import data_audit
from src.interfaces.http.routes import branch_benchmark
from src.interfaces.http.routes import financial_intelligence_dre
from src.interfaces.http.routes import dre_multidimensional
from src.interfaces.http.routes import executive_health_synthesis
from src.interfaces.http.routes import financial_conciliation
from src.interfaces.http.routes import expense_reclassify
from src.interfaces.http.routes import units_performance
from src.interfaces.http.routes import pista_rush_heatmap
from src.interfaces.http.routes import forecourt_layout
from src.interfaces.http.routes import card_fraud_audit
from src.interfaces.http.routes import cashier_audit
from src.interfaces.http.routes import cashier_audit_finance
from src.interfaces.http.routes import president_dashboard
from src.api.v1.endpoints import audit_settings as audit_settings_ep
from src.api.v1.endpoints import fiscal_audit as fiscal_audit_ep
from src.api.v1.endpoints import ai_chat as ai_chat_ep
from src.api.v1.endpoints import ai_health as ai_health_ep
from src.api.v1.endpoints import conveniencia as conveniencia_ep
from src.api.v1.endpoints import webhooks_audit as webhooks_audit_ep
from src.api.v1.endpoints import webhooks_receiver as webhooks_receiver_ep
from src.api.v1.endpoints import cost_proposals as cost_proposals_ep
from src.api.v1.endpoints import conveniencia_sales as conveniencia_sales_ep
from src.api.v1.endpoints import proposals as proposals_ep
from src.api.v1.endpoints import logistica as logistica_ep
from src.api.v1.endpoints import conveniencia_sync as conveniencia_sync_ep
from src.api.v1.endpoints import conveniencia_receiving as conveniencia_receiving_ep
from src.api.v1.endpoints import conveniencia_visual_audit as conveniencia_visual_audit_ep
from src.api.v1.endpoints import conveniencia_analytics as conveniencia_analytics_ep
from src.api.v1.endpoints import conveniencia_onboarding as conveniencia_onboarding_ep
from src.api.v1.endpoints import conveniencia_quality as conveniencia_quality_ep
from src.api.v1.endpoints import conveniencia_executive as conveniencia_executive_ep
from src.api.v1.endpoints import conveniencia_ia_ops as conveniencia_ia_ops_ep
from src.api.v1.endpoints import financial as financial_ep
from src.api.v1.endpoints import premmia as premmia_ep
from src.api.v1.endpoints import cash_deposit as cash_deposit_ep
from src.api.v1.endpoints import expense_review as expense_review_ep
from src.interfaces.http.routes import data_sync
from src.interfaces.http.routes import price_update_operational
from src.interfaces.http.routes import product_registration_operational
from src.interfaces.http.routes import fiscal_models_operational
from src.interfaces.http.routes import dfe_operational
from src.services.financial_snapshot_scheduler import get_financial_scheduler
from src.services.departmental_automation_service import get_departmental_automation
from src.services.data_sync_scheduler import get_data_sync_scheduler
from src.interfaces.http.read_mode_guard import (
    enforce_read_mode,
    should_mount_public_snapshots,
)
from src.services.webposto.offline_mode import (
    WebPostoOfflineBlocked,
    install_webposto_offline_network_guard,
    offline_unavailable_payload,
    webposto_background_jobs_allowed,
    webposto_offline_mode,
)
from src.shared.logger import setup_logging


def _operational_routes_enabled() -> bool:
    """Sprint 01 — default True; override via ENABLE_OPERATIONAL_ROUTES no .env."""
    return bool(getattr(settings, "enable_operational_routes", True))


def _mount_core(app: FastAPI) -> None:
    """Saúde, auth, gateway legado e frontend."""
    app.include_router(health.router)
    app.include_router(auth.router)
    app.include_router(gateway_expenses.router)
    app.include_router(expenses.router)
    app.include_router(clientes.router)
    app.include_router(sync.router)
    app.include_router(metrics.router)


def _mount_executive_barramento(app: FastAPI) -> None:
    """
    Barramento das 3 Telas do Presidente (context.md).

    Tela 1 — Top 5:     owner-action-center, discovery, decisions, follow-ups, review-inbox
    Tela 2 — Comercial: analytics (fuel/executive, fuel-summary, kpis), fechamento_enterprise
    Tela 3 — Financeiro: analytics (dre), cash-flow, finance_center, fechamento_enterprise (/v1/financial/*)

    Agregação obrigatória: empresaCodigo (filial) ou rede consolidada.
    """
    # Tela 1 — Owner Action Center
    app.include_router(owner_action_center.router)
    app.include_router(decision_discovery.router)
    app.include_router(decisions.router)
    app.include_router(decisions.review_lookup_router)
    app.include_router(executive_follow_up.router)
    app.include_router(financial_review_inbox.router)

    # Tela 2 & 3 — Comercial + Financeiro (contratos analíticos)
    app.include_router(analytics.router)  # /api/v1/dre, /fuel/executive, /sales/fuel-summary, /kpis
    app.include_router(
        fechamento_enterprise.router
    )  # /v1/financial/overview, /v1/vendas-combustivel, ...
    app.include_router(finance_center.router)
    app.include_router(cash_flow.router)  # /api/v1/finance/cash-flow
    app.include_router(financial_intelligence.router)
    app.include_router(financial_intelligence_center.router)
    app.include_router(prestacao_contas.router)
    app.include_router(periodic_audits.router)
    app.include_router(cash_reconciliation.router)
    app.include_router(director_financial_reconciliation.router)


def _mount_executive_support(app: FastAPI) -> None:
    """Módulos de suporte C-Level (rede/posto) — não são superfícies operacionais de pista."""
    app.include_router(corporate_intelligence_hub.router)
    app.include_router(executive_scorecard.router)
    app.include_router(benchmark_intelligence.router)
    app.include_router(executive_decision_engine.router)
    app.include_router(action_center.router)
    app.include_router(fuel_governance.router)
    app.include_router(non_fuel_product_sales.router)
    app.include_router(commercial_execution.router)
    app.include_router(commercial_learning.router)
    app.include_router(commercial_copilot.router)
    app.include_router(data_trust_baseline.router)
    app.include_router(executive_copilot_ask.router)
    app.include_router(executive_ai_copilot.router)
    app.include_router(autonomous_recommendation_engine.router)
    app.include_router(closed_loop_learning_engine.router)
    app.include_router(management_action_center.router)
    app.include_router(goals_campaign_engine.router)
    app.include_router(nfce_intelligence.router)
    app.include_router(lmc_intelligence.router)
    app.include_router(tax_product_fiscal_intelligence.router)
    app.include_router(fiscal_reconciliation_hub.router)
    app.include_router(business_analyst.router)
    app.include_router(governance.router)
    app.include_router(statements.router)
    app.include_router(admin_circuit_breaker.router)
    app.include_router(financial_snapshot_health.router)
    app.include_router(financial_operations.router)
    app.include_router(financial_operations_center.router)
    app.include_router(departmental_facts.router)
    app.include_router(departmental_kpis.router)
    app.include_router(departmental_governance.router)
    app.include_router(executive_synthesis.router)
    app.include_router(operational_advanced.router)
    app.include_router(expense_mappings.router)
    app.include_router(executive_cockpit.router)
    app.include_router(operational_cockpit.router)
    app.include_router(cockpit_live.router)
    app.include_router(pista_live_feed.router)
    app.include_router(pista_intelligence.router)
    app.include_router(abastecimentos_rest.router)
    app.include_router(executive_analytics.router)
    app.include_router(executive_employees.router)
    app.include_router(executive_market.router)
    app.include_router(executive_consolidated_report.router)
    app.include_router(fuel_volumetry.router)
    app.include_router(fuel_demand_intelligence.router)
    app.include_router(expenses_dre.router)
    app.include_router(product_inspection.router)
    app.include_router(operational_fuel_loss.router)
    app.include_router(debug_fuel_volume.router)
    app.include_router(inventory_prediction.router)
    app.include_router(alert_engine.router)
    app.include_router(data_audit.router)
    app.include_router(branch_benchmark.router)
    app.include_router(financial_intelligence_dre.router)
    app.include_router(dre_multidimensional.router)
    app.include_router(executive_health_synthesis.router)
    app.include_router(financial_conciliation.router)
    app.include_router(expense_reclassify.router)
    app.include_router(units_performance.router)
    app.include_router(pista_rush_heatmap.router)
    app.include_router(forecourt_layout.router)
    app.include_router(card_fraud_audit.router)
    app.include_router(cashier_audit.router)
    app.include_router(cashier_audit_finance.router)
    app.include_router(president_dashboard.router)
    app.include_router(audit_settings_ep.router)
    app.include_router(fiscal_audit_ep.router)
    app.include_router(ai_chat_ep.router)
    app.include_router(ai_health_ep.router)
    app.include_router(conveniencia_ep.router)
    app.include_router(webhooks_audit_ep.router)
    app.include_router(webhooks_receiver_ep.router)
    app.include_router(webhooks_receiver_ep.admin_router)
    app.include_router(cost_proposals_ep.router)
    app.include_router(conveniencia_sales_ep.router)
    app.include_router(proposals_ep.router)
    app.include_router(logistica_ep.router)
    app.include_router(conveniencia_sync_ep.router)
    app.include_router(conveniencia_receiving_ep.router)
    app.include_router(conveniencia_visual_audit_ep.router)
    app.include_router(conveniencia_analytics_ep.router)
    app.include_router(conveniencia_onboarding_ep.router)
    app.include_router(conveniencia_quality_ep.router)
    app.include_router(conveniencia_executive_ep.router)
    app.include_router(conveniencia_ia_ops_ep.router)
    app.include_router(financial_ep.router)
    app.include_router(premmia_ep.router)
    app.include_router(cash_deposit_ep.router)
    app.include_router(expense_review_ep.router)
    app.include_router(data_sync.router)


def _mount_operational_deprecated(app: FastAPI) -> None:
    """
    Operacional — turnos, operadores, PDVs, ROI de pessoas/turno.

    Sprint 01: montado por padrão (settings.enable_operational_routes=True).
    """
    if not _operational_routes_enabled():
        return

    app.include_router(cash_operations.router)  # /api/v1/cash/operations
    app.include_router(operator_performance.router)  # /api/v1/performance
    app.include_router(operator_sales_intelligence.router)  # /api/v1/operator-intelligence
    app.include_router(operator_accountability_incentive.router)  # /api/v1/people-intelligence
    app.include_router(operator_profitability.router)  # /api/v1/people-roi
    app.include_router(store_shift_profitability.router)  # /api/v1/operation-roi
    app.include_router(price_update_operational.router)  # /api/v1/operational/price-update
    app.include_router(product_registration_operational.router)  # /api/v1/operational/product-registration
    app.include_router(fiscal_models_operational.router)  # /api/v1/operational/fiscal-models
    app.include_router(dfe_operational.router)  # /api/v1/operational/dfe


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    """Lifecycle manager — substitui on_event startup/shutdown (FastAPI 0.93+)."""
    await init_db()
    await init_gateway_db()
    try:
        from src.services.proposals.db import init_local_db

        init_local_db()
    except Exception:
        pass
    jobs_ok = webposto_background_jobs_allowed()
    if jobs_ok:
        get_financial_scheduler().schedule_next_run()

    scheduler_task = None
    if jobs_ok and settings.departmental_scheduler_enabled:

        async def poll_departmental_schedule() -> None:
            while True:
                await get_departmental_automation().run_due()
                await asyncio.sleep(max(15, settings.departmental_scheduler_poll_seconds))

        scheduler_task = asyncio.create_task(
            poll_departmental_schedule(),
            name="departmental-scheduler",
        )
        app.state.departmental_scheduler_task = scheduler_task

    # Híbrido: consolidação D-1 + autodiscovery — cron 0 3 * * * (03:00 AM)
    data_sync_sched = get_data_sync_scheduler()
    if jobs_ok and settings.data_sync_scheduler_enabled:
        await data_sync_sched.start()
        app.state.data_sync_scheduler = data_sync_sched

    # Cockpit 30s — worker asyncio → cache RAM (API_WORKERS=1)
    pista_worker = None
    if jobs_ok and settings.pista_sync_worker_enabled:
        from src.workers.pista_sync_worker import get_pista_sync_worker

        pista_worker = get_pista_sync_worker()
        pista_worker.interval_seconds = max(
            10, int(settings.pista_sync_interval_seconds or 30)
        )
        await pista_worker.start()
        app.state.pista_sync_worker = pista_worker

    yield

    if pista_worker is not None:
        await pista_worker.stop()
    if jobs_ok and settings.data_sync_scheduler_enabled:
        await data_sync_sched.stop()
    if scheduler_task:
        scheduler_task.cancel()
        with suppress(asyncio.CancelledError):
            await scheduler_task
    await close_db()


def create_app() -> FastAPI:
    """Factory para criar instância da aplicação FastAPI."""

    settings.validate_production_security()
    install_webposto_offline_network_guard()

    # Setup logging
    setup_logging(settings.log_level, settings.log_format)

    # Criar app com lifespan manager
    app = FastAPI(
        title=settings.api_title,
        version=settings.api_version,
        debug=settings.debug,
        lifespan=lifespan,
    )

    # CORS middleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.allowed_origins(),
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @app.exception_handler(WebPostoOfflineBlocked)
    async def webposto_offline_blocked_handler(request: Request, exc: WebPostoOfflineBlocked):
        return JSONResponse(
            status_code=503,
            content=offline_unavailable_payload(route=request.url.path),
        )

    @app.middleware("http")
    async def read_mode_security(request: Request, call_next):
        blocked = enforce_read_mode(request)
        if blocked is not None:
            return blocked
        return await call_next(request)

    @app.middleware("http")
    async def offline_mode_header(request: Request, call_next):
        response = await call_next(request)
        if webposto_offline_mode():
            response.headers["X-WebPosto-Offline-Mode"] = "true"
        return response

    @app.middleware("http")
    async def disable_frontend_cache(request: Request, call_next):
        response = await call_next(request)
        path = request.url.path
        if path.startswith("/frontend/") and path.endswith((".js", ".css")):
            response.headers["Cache-Control"] = "no-cache, must-revalidate"
        elif path == "/app/financial":
            response.headers["Cache-Control"] = "no-cache, must-revalidate"
        return response

    # --- Roteamento Sprint 1: C-Level primeiro, operacional isolado ---
    _mount_core(app)
    _mount_executive_barramento(app)
    _mount_executive_support(app)
    _mount_operational_deprecated(app)

    root = Path(__file__).resolve().parents[3]
    frontend_dir = root / "frontend"
    snapshots_dir = root / "snapshots"
    if snapshots_dir.is_dir() and should_mount_public_snapshots():
        app.mount("/snapshots", StaticFiles(directory=str(snapshots_dir)), name="snapshots")

    if frontend_dir.is_dir():
        app.mount("/frontend", StaticFiles(directory=str(frontend_dir)), name="frontend")

        @app.get("/")
        async def root_redirect() -> RedirectResponse:
            return RedirectResponse(url="/app/financial")

        @app.get("/app/financial")
        async def financial_frontend() -> FileResponse:
            return FileResponse(
                frontend_dir / "index.html",
                media_type="text/html; charset=utf-8",
                headers={"Cache-Control": "no-cache, must-revalidate"},
            )

        @app.get("/app/departmental")
        async def departmental_frontend() -> FileResponse:
            return FileResponse(
                frontend_dir / "departmental.html",
                media_type="text/html; charset=utf-8",
                headers={"Cache-Control": "no-cache, must-revalidate"},
            )

    return app


app = create_app()
