"""
webPosto API — Completa com Sync + CRUD + Auditoria
Produção: Conecta com API webPosto real
Sandbox: Retorna dados mock para validação
"""

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
import logging
from datetime import datetime

from src.infrastructure.config.settings import settings
from src.infrastructure.webposto.client import WebPostoClient
from src.routes_crud import router as crud_router
from src.interfaces.http.routes.fechamento_enterprise import router as enterprise_router

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="webPosto Sync + CRUD Service",
    version="0.2.0",
    description="Sincroniza Financeiro e Caixa do webPosto + CRUD completo com auditoria",
    docs_url="/docs",
    redoc_url="/redoc",
)

# CORS Configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Incluir routers CRUD
app.include_router(crud_router)
app.include_router(enterprise_router)

client = WebPostoClient()


@app.get("/health")
async def health():
    """Health check"""
    return {
        "status": "healthy",
        "version": "0.2.0",
        "webposto_api": settings.webposto_base_url,
        "empresa": "POSTO VIP - Rio Doce Comércio e Serviços Ltda",
        "cors": "enabled",
        "timestamp": datetime.now().isoformat(),
    }


@app.options("/{full_path:path}")
async def options_handler(full_path: str):
    """Handle CORS preflight requests"""
    return {}


@app.post("/sync/financeiro")
@app.get("/sync/financeiro")
async def sync_financeiro():
    """Sincroniza Financeiro (Títulos a Receber/Pagar) da API webPosto"""
    try:
        logger.info("Sincronizando financeiro...")
        financeiro = await client.get_financeiro()

        return {
            "status": "success",
            "registros": len(financeiro) if financeiro else 0,
            "timestamp": __import__("datetime").datetime.now().isoformat(),
            "detalhes": financeiro,
        }
    except Exception as e:
        logger.error(f"Erro ao sincronizar financeiro: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/sync/caixa")
@app.get("/sync/caixa")
async def sync_caixa():
    """Sincroniza Movimentos de Caixa da API webPosto"""
    try:
        logger.info("Sincronizando caixa...")
        caixa = await client.get_caixa()

        return {
            "status": "success",
            "registros": len(caixa) if caixa else 0,
            "timestamp": __import__("datetime").datetime.now().isoformat(),
            "detalhes": caixa,
        }
    except Exception as e:
        logger.error(f"Erro ao sincronizar caixa: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/docs")
async def swagger():
    """Redirecionamento para Swagger UI"""
    return {
        "message": "Acesse http://localhost:8000/docs no navegador para ver a documentação interativa"
    }


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "src.main_minimal:app",
        host=settings.api_host,
        port=settings.api_port,
        reload=settings.debug,
        log_level=settings.log_level.lower(),
    )
