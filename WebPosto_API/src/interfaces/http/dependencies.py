from typing import AsyncGenerator

from sqlalchemy.ext.asyncio import AsyncSession

from src.application.services.cliente_service import ClienteService
from src.application.services.sync_service import SyncService
from src.infrastructure.config.database import AsyncSessionLocal
from src.infrastructure.event_bus.redis_event_bus import RedisEventBus
from src.infrastructure.repositories.cliente_repository import (
    SQLAlchemyClienteRepository,
)
from src.infrastructure.webposto.client import WebPostoClient
from src.application.usecases.extract_expenses import ExtractExpensesFromCashMovement
from fastapi import Depends, HTTPException, Request
from typing import Dict
from src.infrastructure.security.jwt_utils import decode_token


async def get_current_user(request: Request) -> Dict:
    """Dependency: extrai usuário do cookie de access token e valida."""
    token = request.cookies.get("access_token")
    if not token:
        raise HTTPException(status_code=401, detail="Not authenticated")
    try:
        payload = decode_token(token)
        return payload
    except Exception:
        raise HTTPException(status_code=401, detail="Invalid token")


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """Dependency: Sessão do banco de dados."""
    async with AsyncSessionLocal() as session:
        try:
            yield session
        finally:
            await session.close()


async def get_cliente_repository(
    db: AsyncSession = Depends(get_db),
) -> SQLAlchemyClienteRepository:
    """Dependency: Repositório de Clientes."""
    return SQLAlchemyClienteRepository(db)


async def get_event_bus() -> RedisEventBus:
    """Dependency: Event Bus."""
    event_bus = RedisEventBus()
    await event_bus.connect()
    return event_bus


async def get_webposto_client() -> WebPostoClient:
    """Dependency: Cliente webPosto."""
    return WebPostoClient()


async def get_cliente_service(
    repository: SQLAlchemyClienteRepository = Depends(get_cliente_repository),
    event_bus: RedisEventBus = Depends(get_event_bus),
) -> ClienteService:
    """Dependency: Serviço de Clientes."""
    return ClienteService(repository, event_bus)


async def get_sync_service(
    webposto_client: WebPostoClient = Depends(get_webposto_client),
    cliente_service: ClienteService = Depends(get_cliente_service),
    event_bus: RedisEventBus = Depends(get_event_bus),
) -> SyncService:
    """Dependency: Serviço de Sincronização."""
    return SyncService(webposto_client, cliente_service, event_bus)


async def get_extract_expenses_usecase(
    event_bus: RedisEventBus = Depends(get_event_bus),
) -> ExtractExpensesFromCashMovement:
    """Dependency: Caso de uso de extração/classificação de despesas."""
    return ExtractExpensesFromCashMovement(event_bus=event_bus)
