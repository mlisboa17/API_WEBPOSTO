from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, RedirectResponse
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
from src.interfaces.http.routes import cash_reconciliation
from src.interfaces.http.routes import decisions
from src.interfaces.http.routes import executive_follow_up
from src.interfaces.http.routes import financial_intelligence
from src.interfaces.http.routes import admin_circuit_breaker
from src.interfaces.http.routes import financial_snapshot_health
from src.interfaces.http.routes import financial_operations
from src.interfaces.http.routes import financial_operations_center
from src.interfaces.http.routes import business_analyst
from src.interfaces.http.routes import governance
from src.interfaces.http.routes import financial_intelligence_center
from src.services.financial_snapshot_scheduler import get_financial_scheduler
from src.shared.logger import setup_logging


def create_app() -> FastAPI:
    """Factory para criar instância da aplicação FastAPI."""

    # Setup logging
    setup_logging(settings.log_level, settings.log_format)

    # Criar app
    app = FastAPI(
        title=settings.api_title,
        version=settings.api_version,
        debug=settings.debug,
    )

    # CORS middleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @app.middleware("http")
    async def disable_frontend_cache(request: Request, call_next):
        response = await call_next(request)
        path = request.url.path
        if path.startswith("/frontend/") and path.endswith((".js", ".css")):
            response.headers["Cache-Control"] = "no-cache, must-revalidate"
        elif path == "/app/financial":
            response.headers["Cache-Control"] = "no-cache, must-revalidate"
        return response

    # Incluir rotas
    app.include_router(health.router)
    app.include_router(gateway_expenses.router)
    app.include_router(fechamento_enterprise.router)
    app.include_router(expenses.router)
    app.include_router(clientes.router)
    app.include_router(sync.router)
    app.include_router(auth.router)
    app.include_router(metrics.router)
    app.include_router(analytics.router)
    app.include_router(finance_center.router)
    app.include_router(cash_flow.router)
    app.include_router(cash_operations.router)
    app.include_router(operator_performance.router)
    app.include_router(operator_sales_intelligence.router)
    app.include_router(operator_accountability_incentive.router)
    app.include_router(operator_profitability.router)
    app.include_router(store_shift_profitability.router)
    app.include_router(management_action_center.router)
    app.include_router(goals_campaign_engine.router)
    app.include_router(benchmark_intelligence.router)
    app.include_router(executive_scorecard.router)
    app.include_router(corporate_intelligence_hub.router)
    app.include_router(executive_decision_engine.router)
    app.include_router(action_center.router)
    app.include_router(owner_action_center.router)  # BUILD-01D
    app.include_router(decision_discovery.router)  # VALUE-01
    app.include_router(executive_ai_copilot.router)
    app.include_router(autonomous_recommendation_engine.router)
    app.include_router(closed_loop_learning_engine.router)
    app.include_router(nfce_intelligence.router)
    app.include_router(lmc_intelligence.router)
    app.include_router(tax_product_fiscal_intelligence.router)
    app.include_router(fiscal_reconciliation_hub.router)
    app.include_router(fuel_governance.router)
    app.include_router(non_fuel_product_sales.router)
    app.include_router(commercial_execution.router)
    app.include_router(commercial_learning.router)
    app.include_router(commercial_copilot.router)
    app.include_router(statements.router)
    app.include_router(data_trust_baseline.router)
    app.include_router(prestacao_contas.router)
    app.include_router(cash_reconciliation.router)
    app.include_router(decisions.router)
    app.include_router(decisions.review_lookup_router)
    app.include_router(executive_follow_up.router)
    app.include_router(financial_intelligence.router)
    app.include_router(admin_circuit_breaker.router)
    app.include_router(financial_snapshot_health.router)
    app.include_router(financial_operations.router)
    app.include_router(financial_operations_center.router)
    app.include_router(financial_intelligence_center.router)
    app.include_router(business_analyst.router)
    app.include_router(governance.router)

    root = Path(__file__).resolve().parents[3]
    frontend_dir = root / "frontend"
    snapshots_dir = root / "snapshots"
    if snapshots_dir.is_dir():
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

    # Startup event
    @app.on_event("startup")
    async def on_startup():
        """Executado ao iniciar a aplicação."""
        await init_db()
        await init_gateway_db()
        get_financial_scheduler().schedule_next_run()

    # Shutdown event
    @app.on_event("shutdown")
    async def on_shutdown():
        """Executado ao desligar a aplicação."""
        await close_db()

    return app


app = create_app()
