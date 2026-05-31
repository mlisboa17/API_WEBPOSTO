from __future__ import annotations

from datetime import date

from fastapi import APIRouter, Depends, Header, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from src.application.usecases.fetch_expenses import FetchExpensesUseCase
from src.domain.exceptions.posto_nao_configurado import PostoNaoConfiguradoException
from src.infrastructure.caching.gateway_cache import get_gateway_cache
from src.infrastructure.clients.gateway_webposto_client import GatewayWebPostoClient
from src.infrastructure.config.gateway_database import get_gateway_db, init_gateway_db
from src.infrastructure.repositories.gateway_credentials_repository import GatewayCredentialsRepository

router = APIRouter(tags=["Gateway Expenses"])


async def get_fetch_expenses_usecase(
    db: AsyncSession = Depends(get_gateway_db),
) -> FetchExpensesUseCase:
    await init_gateway_db()
    return FetchExpensesUseCase(
        credentials_repo=GatewayCredentialsRepository(db),
        webposto_client=GatewayWebPostoClient(timeout_seconds=10.0),
        cache=get_gateway_cache(),
    )


@router.get("/v1/expenses")
async def get_expenses(
    data_consulta: date = Query(..., description="Data base da consulta"),
    x_posto_id: str = Header(..., alias="X-Posto-ID"),
    usecase: FetchExpensesUseCase = Depends(get_fetch_expenses_usecase),
):
    try:
        expenses = await usecase.execute(x_posto_id, data_consulta)
    except PostoNaoConfiguradoException as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=502, detail=str(exc)[:300]) from exc

    return {
        "posto_id": x_posto_id,
        "data_consulta": data_consulta.isoformat(),
        "count": len(expenses),
        "items": [e.model_dump(mode="json") for e in expenses],
    }
