import os
from datetime import datetime
from time import perf_counter
from typing import Annotated, Optional

from fastapi import APIRouter, Depends, Header, HTTPException, Query
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from src.application.fetch_expenses import FetchExpensesUseCase
from src.application.fetch_products import FetchProductsUseCase
from src.domain.exceptions import (
    PostoInativoException,
    PostoNaoConfiguradoException,
    WebPostoIntegracaoException,
)
from src.infrastructure.cache import cache_manager
from src.infrastructure.database import get_db
from src.infrastructure.repository import PostoCredentialsRepository
from src.infrastructure.webposto_client import WebPostoClient
from src.presentation.security import require_consumer_token

router = APIRouter(tags=["gateway"])
API_PORT = int(os.getenv("API_PORT", "8050"))


def get_fetch_expenses_use_case(db: AsyncSession = Depends(get_db)) -> FetchExpensesUseCase:
    repository = PostoCredentialsRepository(db_session=db)
    webposto_client = WebPostoClient(
        timeout=min(int(os.getenv("WEBPOSTO_API_TIMEOUT", "10")), 10),
    )
    return FetchExpensesUseCase(
        repository=repository,
        webposto_client=webposto_client,
        cache=cache_manager,
    )


def get_fetch_products_use_case(db: AsyncSession = Depends(get_db)) -> FetchProductsUseCase:
    repository = PostoCredentialsRepository(db_session=db)
    webposto_client = WebPostoClient(
        timeout=min(int(os.getenv("WEBPOSTO_API_TIMEOUT", "10")), 10),
    )
    return FetchProductsUseCase(
        repository=repository,
        webposto_client=webposto_client,
        cache=cache_manager,
    )


@router.get("/ready", status_code=200, summary="Readiness probe")
async def ready():
    return {"status": "ready", "service": "logos-gateway", "port": API_PORT}


@router.get("/health", status_code=200, summary="Liveness probe")
async def health(db: AsyncSession = Depends(get_db)):
    start = perf_counter()
    try:
        await db.execute(text("SELECT 1"))
        query_ms = round((perf_counter() - start) * 1000, 3)
        return {
            "status": "healthy",
            "database": "up",
            "port": API_PORT,
            "service": "logos-gateway",
            "db_query_ms": query_ms,
            "external_dependencies": "ignored",
            "powershell_check": f"Invoke-RestMethod -Uri http://localhost:{API_PORT}/health",
        }
    except Exception as e:
        return {
            "status": "degraded",
            "database": "down",
            "port": API_PORT,
            "service": "logos-gateway",
            "error": str(e),
            "external_dependencies": "ignored",
            "powershell_check": f"Invoke-RestMethod -Uri http://localhost:{API_PORT}/health",
        }


@router.get("/v1/expenses", status_code=200, summary="Fetch posto expenses")
async def get_expenses(
    use_case: Annotated[FetchExpensesUseCase, Depends(get_fetch_expenses_use_case)],
    _: Annotated[None, Depends(require_consumer_token)],
    x_posto_id: Annotated[str, Header(alias="X-Posto-ID")],
    data_consulta: Annotated[Optional[datetime], Query()] = None,
):
    consulta = data_consulta or datetime.utcnow()
    try:
        expenses = await use_case.execute(posto_id=x_posto_id, data_consulta=consulta)
        return {
            "posto_id": x_posto_id,
            "data_consulta": consulta.isoformat(),
            "total": len(expenses),
            "items": [expense.model_dump(mode="json") for expense in expenses],
        }
    except PostoNaoConfiguradoException as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    except PostoInativoException as exc:
        raise HTTPException(status_code=403, detail=str(exc))
    except WebPostoIntegracaoException as exc:
        raise HTTPException(status_code=exc.status_code or 502, detail=str(exc))


@router.get("/v1/", status_code=200, summary="Gateway info")
async def v1_root():
    return {
        "service": "Logos WebPosto Gateway",
        "version": "1.0.0",
        "security": {
            "consumer_header": "X-Consumer-Token",
            "posto_header": "X-Posto-ID",
        },
        "endpoints": {
            "/ready": "Readiness probe",
            "/health": "Liveness probe",
            "/v1/expenses": "Fetch despesas de um Posto",
            "/v1/products": "Fetch cadastro completo de produtos de um Posto",
        },
        "port": API_PORT,
    }


@router.get("/v1/products", status_code=200, summary="Fetch posto product catalog")
async def get_products(
    use_case: Annotated[FetchProductsUseCase, Depends(get_fetch_products_use_case)],
    _: Annotated[None, Depends(require_consumer_token)],
    x_posto_id: Annotated[str, Header(alias="X-Posto-ID")],
    include_inactive: Annotated[bool, Query()] = False,
    force_refresh: Annotated[bool, Query()] = False,
):
    try:
        result = await use_case.execute(
            posto_id=x_posto_id,
            include_inactive=include_inactive,
            force_refresh=force_refresh,
        )
        return result
    except PostoNaoConfiguradoException as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    except PostoInativoException as exc:
        raise HTTPException(status_code=403, detail=str(exc))
    except WebPostoIntegracaoException as exc:
        raise HTTPException(status_code=exc.status_code or 502, detail=str(exc))
