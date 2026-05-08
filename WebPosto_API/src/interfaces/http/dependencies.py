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


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """Dependency: Sessão do banco de dados."""
    async with AsyncSessionLocal() as session:
        try:
            yield session
        finally:
            await session.close()


async def get_cliente_repository(
    db: AsyncSession,
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
    repository: SQLAlchemyClienteRepository,
    event_bus: RedisEventBus,
) -> ClienteService:
    """Dependency: Serviço de Clientes."""
    return ClienteService(repository, event_bus)


async def get_sync_service(
    webposto_client: WebPostoClient,
    cliente_service: ClienteService,
    event_bus: RedisEventBus,
) -> SyncService:
    """Dependency: Serviço de Sincronização."""
    return SyncService(webposto_client, cliente_service, event_bus)
