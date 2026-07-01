"""
FastAPI Application Setup: Main application entry point.

Configuração de rotas, middlewares, health check e inicialização.
"""

import logging
import asyncio
import uuid
from contextlib import asynccontextmanager
from typing import Optional

from fastapi import FastAPI, Depends, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker

from src.application.usecases.tax_recovery import run_adelaide_recovery
from src.domain.adelaide_engine import AdelaideEngine, ProductAuditInput, TaxContext
from src.infrastructure.persistence.postgresql.models import Base
from src.infrastructure.cache.redis_adapter import RedisCacheAdapter, RedisCacheException
from src.infrastructure.tax_api.repository import SqlAlchemyTaxMatrixRepository
from src.infrastructure.webposto.client import WebPostoClient
from src.infrastructure.events.outbox_processor import OutboxProcessor
from src.infrastructure.sse import router as sse_router, publish_job_event
from src.api.tms_routes import router as tms_router

logger = logging.getLogger(__name__)


# ===== DATABASE SETUP =====

class DatabaseManager:
    """Gerencia conexão com banco de dados PostgreSQL."""
    
    def __init__(self, database_url: str):
        self.database_url = database_url
        self.engine = None
        self.session_factory = None
    
    async def initialize(self) -> None:
        """Inicializar engine e criar tabelas."""
        self.engine = create_async_engine(
            self.database_url,
            echo=False,
            pool_size=20,
            max_overflow=40,
            pool_pre_ping=True
        )
        
        self.session_factory = async_sessionmaker(
            self.engine,
            class_=AsyncSession,
            expire_on_commit=False
        )
        
        # Criar tabelas
        async with self.engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        
        logger.info("Database initialized")
    
    async def shutdown(self) -> None:
        """Fechar conexão."""
        if self.engine:
            await self.engine.dispose()
            logger.info("Database connection closed")
    
    def get_session(self) -> AsyncSession:
        """Obter nova sessão."""
        if not self.session_factory:
            raise RuntimeError("Database not initialized")
        return self.session_factory()


# ===== HEALTH CHECK =====

class HealthStatus:
    """Status de saúde da aplicação."""
    
    def __init__(
        self,
        db_manager: DatabaseManager,
        cache: Optional[RedisCacheAdapter],
        webposto_client: Optional[WebPostoClient]
    ):
        self.db_manager = db_manager
        self.cache = cache
        self.webposto_client = webposto_client
    
    async def check(self) -> dict:
        """
        Verificar saúde de todos os componentes.
        
        Returns:
            Dict com status de cada componente
        """
        status = {
            "status": "ok",
            "timestamp": __import__('datetime').datetime.utcnow().isoformat(),
            "components": {}
        }
        
        # Check Database
        try:
            async with self.db_manager.session_factory() as session:
                await session.execute(__import__('sqlalchemy').text("SELECT 1"))
            status["components"]["database"] = "ok"
        except Exception as e:
            status["components"]["database"] = f"error: {str(e)}"
            status["status"] = "degraded"
        
        # Check Redis Cache
        if self.cache:
            try:
                health = await self.cache.health_check()
                status["components"]["cache"] = "ok" if health else "error"
                if not health:
                    status["status"] = "degraded"
            except RedisCacheException as e:
                status["components"]["cache"] = f"error: {str(e)}"
                status["status"] = "degraded"
        
        # Check WebPosto API
        if self.webposto_client:
            try:
                is_available = await self.webposto_client.validar_conexao()
                status["components"]["webposto_api"] = "ok" if is_available else "unavailable"
                if not is_available:
                    status["status"] = "degraded"
            except Exception as e:
                status["components"]["webposto_api"] = f"error: {str(e)}"
                status["status"] = "degraded"
        
        return status


class AdelaideRunRequest(BaseModel):
    context: dict
    products: list[dict] = []


def _default_products() -> list[dict]:
    return [
        {
            "sku": f"SKU-{index:05d}",
            "descricao": "CERV SKOL LATA 350ML" if index % 3 == 0 else "REFRIGERANTE ZERO 2L",
            "ncm": "22030000" if index % 4 else "00000000",
            "cst": "060" if index % 4 else "010",
            "regime": "LUCRO_REAL",
            "preco_venda": "12.50",
            "custo": "8.10",
            "taxa_cartao": "0.34",
            "centro_custo": "0.22",
            "quantidade": "2",
            "pis_pago": "0.44",
            "cofins_pago": "2.02",
            "grupo_produto": "Bebidas",
        }
        for index in range(1, 26)
    ]


# ===== FASTAPI APP =====

def criar_app(
    database_url: str,
    redis_host: str = "localhost",
    redis_port: int = 6379,
    webposto_url: Optional[str] = None,
    webposto_api_key: Optional[str] = None
) -> FastAPI:
    """
    Criar aplicação FastAPI.
    
    Args:
        database_url: URL de conexão PostgreSQL
        redis_host: Host Redis
        redis_port: Porta Redis
        webposto_url: URL base WebPosto (opcional)
        webposto_api_key: Chave API WebPosto (opcional)
    
    Returns:
        Instância de FastAPI
    """
    
    # Gerenciadores de infraestrutura
    db_manager = DatabaseManager(database_url)
    cache: Optional[RedisCacheAdapter] = None
    webposto_client: Optional[WebPostoClient] = None
    outbox_processor: Optional[OutboxProcessor] = None
    health_status: Optional[HealthStatus] = None
    
    @asynccontextmanager
    async def lifespan(app: FastAPI):
        """Gerenciar ciclo de vida da aplicação."""
        # Startup
        try:
            logger.info("Iniciando aplicação...")
            
            # Inicializar banco de dados
            await db_manager.initialize()
            
            # Inicializar cache Redis
            nonlocal cache
            try:
                cache = RedisCacheAdapter(host=redis_host, port=redis_port)
                await cache.connect()
            except Exception as e:
                logger.warning(f"Redis não disponível: {e}")
                cache = None
            
            # Inicializar cliente WebPosto
            nonlocal webposto_client
            if webposto_url and webposto_api_key:
                webposto_client = WebPostoClient(
                    base_url=webposto_url,
                    api_key=webposto_api_key
                )
                await webposto_client.connect()
            
            # Inicializar Outbox Processor
            nonlocal outbox_processor
            outbox_processor = OutboxProcessor(
                session_factory=db_manager.session_factory
            )
            
            # Inicializar health check
            nonlocal health_status
            health_status = HealthStatus(db_manager, cache, webposto_client)
            
            logger.info("Aplicação iniciada com sucesso")
        
        except Exception as e:
            logger.error(f"Erro ao iniciar aplicação: {e}", exc_info=True)
            raise
        
        yield
        
        # Shutdown
        logger.info("Encerrando aplicação...")
        
        if webposto_client:
            await webposto_client.disconnect()
        
        if cache:
            await cache.disconnect()
        
        if outbox_processor:
            await outbox_processor.parar()
        
        await db_manager.shutdown()
        
        logger.info("Aplicação encerrada")
    
    # Criar aplicação
    app = FastAPI(
        title="WebPosto API",
        description="API para sincronização de rateios",
        version="1.0.0",
        lifespan=lifespan
    )
    
    # ===== ROTAS =====
    
    @app.get("/health")
    async def health() -> dict:
        """Verificar saúde da aplicação."""
        if not health_status:
            raise HTTPException(status_code=503, detail="App not ready")
        
        status = await health_status.check()
        
        if status["status"] == "ok":
            return status
        elif status["status"] == "degraded":
            return JSONResponse(status_code=200, content=status)
        else:
            raise HTTPException(status_code=503, detail="Service unavailable")
    
    @app.get("/ready")
    async def readiness() -> dict:
        """Verificar se aplicação está pronta para receber requisições."""
        if not health_status:
            raise HTTPException(status_code=503, detail="App not ready")
        
        status = await health_status.check()
        
        required_components = ["database"]
        
        for component in required_components:
            if component not in status["components"]:
                raise HTTPException(status_code=503, detail=f"{component} not available")
            
            if status["components"][component] != "ok":
                raise HTTPException(status_code=503, detail=f"{component} not ready")
        
        return {"status": "ready"}
    
    @app.get("/version")
    async def version() -> dict:
        """Obter versão da API."""
        return {
            "version": "1.0.0",
            "name": "WebPosto API",
            "environment": __import__('os').getenv("ENVIRONMENT", "development")
        }
    
    # Dependency para obter sessão do BD
    async def get_db_session() -> AsyncSession:
        async with db_manager.session_factory() as session:
            yield session

    async def get_tax_matrix_repository(
        session: AsyncSession = Depends(get_db_session),
    ) -> SqlAlchemyTaxMatrixRepository:
        return SqlAlchemyTaxMatrixRepository(session)

    @app.post("/api/adelaide/run")
    async def run_adelaide(
        payload: AdelaideRunRequest,
        repository: SqlAlchemyTaxMatrixRepository = Depends(get_tax_matrix_repository),
    ) -> dict:
        context = payload.context or {
            "cnpj": "12.345.678/0001-99",
            "regime": "LUCRO_REAL",
            "cnae": "4731800",
            "uf": "PE",
        }
        products = payload.products or _default_products()
        job_id = str(uuid.uuid4())

        if products:
            # Touch the injected repository so the route remains wired via Depends.
            await repository.get_matrix(context["uf"], context["cnae"], products[0].get("ncm"))

        async def _runner() -> None:
            total_credit = 0.0
            total = max(len(products), 1)
            engine = AdelaideEngine()
            tax_context = TaxContext(**context)
            findings = []
            async with db_manager.session_factory() as session:
                job_repository = SqlAlchemyTaxMatrixRepository(session)
                for index, product_row in enumerate(products, start=1):
                    product = ProductAuditInput(**product_row)
                    matrix = await job_repository.get_matrix(tax_context.uf, tax_context.cnae, product.ncm)
                    if matrix is None:
                        matrix = await job_repository.upsert_matrix(
                            uf=tax_context.uf,
                            cnae=tax_context.cnae,
                            ncm=product.ncm or "00000000",
                            cst=product.cst or "060",
                            monofasico=(product.ncm or "").startswith("22"),
                            aliquota_pis=product.pis_pago,
                            aliquota_cofins=product.cofins_pago,
                            descricao_referencia=product.descricao,
                        )
                    finding = engine.audit_product(tax_context, product, matrix)
                    findings.append(finding.model_dump())
                    total_credit += float(finding.recoverable_credit)
                    await publish_job_event(
                        job_id,
                        {
                            "event": "progress",
                            "processed": index,
                            "total": total,
                            "recovery_estimated": round(total_credit, 2),
                            "risk_score": finding.risk_score,
                            "latest_sku": finding.sku,
                        },
                    )
                report = await run_adelaide_recovery(context, products, job_repository, engine)
            await publish_job_event(
                job_id,
                {
                    "event": "done",
                    "processed": total,
                    "total": total,
                    "recovery_estimated": round(total_credit, 2),
                    "risk_score": max((item.get("risk_score", 0) for item in findings), default=0),
                    "report": report,
                },
            )

        asyncio.create_task(_runner())
        return {"job_id": job_id, "total": len(products)}
    
    # Armazenar managers no app para uso em rotas
    app.state.db_manager = db_manager
    app.state.cache = cache
    app.state.webposto_client = webposto_client
    app.state.outbox_processor = outbox_processor
    app.state.get_db_session = get_db_session

    # SSE endpoint for real-time dashboard updates.
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    app.include_router(sse_router)
    app.include_router(tms_router)
    
    return app
