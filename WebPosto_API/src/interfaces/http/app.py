from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
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
from src.interfaces.http.routes import data_trust_baseline
from src.interfaces.http.routes import prestacao_contas
from src.interfaces.http.routes import financial_intelligence
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
    app.include_router(data_trust_baseline.router)
    app.include_router(prestacao_contas.router)
    app.include_router(financial_intelligence.router)

    root = Path(__file__).resolve().parents[3]
    frontend_dir = root / "frontend"
    if frontend_dir.is_dir():
        app.mount("/frontend", StaticFiles(directory=str(frontend_dir)), name="frontend")

        @app.get("/app/financial")
        async def financial_frontend() -> FileResponse:
            return FileResponse(frontend_dir / "index.html", media_type="text/html; charset=utf-8")

    # Startup event
    @app.on_event("startup")
    async def on_startup():
        """Executado ao iniciar a aplicação."""
        await init_db()
        await init_gateway_db()

    # Shutdown event
    @app.on_event("shutdown")
    async def on_shutdown():
        """Executado ao desligar a aplicação."""
        await close_db()

    return app


app = create_app()
