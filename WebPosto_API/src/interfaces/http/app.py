from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from src.infrastructure.config.database import close_db, init_db
from src.infrastructure.config.settings import settings
from src.interfaces.http.routes import clientes, health, sync
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
    app.include_router(clientes.router)
    app.include_router(sync.router)

    # Startup event
    @app.on_event("startup")
    async def on_startup():
        """Executado ao iniciar a aplicação."""
        await init_db()

    # Shutdown event
    @app.on_event("shutdown")
    async def on_shutdown():
        """Executado ao desligar a aplicação."""
        await close_db()

    return app
