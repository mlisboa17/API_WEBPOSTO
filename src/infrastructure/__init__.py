"""Infrastructure module exports."""

from .webposto.client import WebPostoClient, WebPostoClientFactory, WebPostoClientException
from .cache.redis_adapter import RedisCacheAdapter, RedisCacheFactory, RedisCacheException
from .persistence.postgresql.repositories import (
    PostgresEmpresaRepository,
    PostgresRateioRepository,
    PostgresSyncHistoryRepository,
    PostgresOutboxRepository,
    PostgresEventRepository,
    PostgresUnitOfWork
)
from .events.outbox_processor import OutboxProcessor, OutboxProcessorFactory

__all__ = [
    # WebPosto Client
    "WebPostoClient",
    "WebPostoClientFactory",
    "WebPostoClientException",
    # Redis Cache
    "RedisCacheAdapter",
    "RedisCacheFactory",
    "RedisCacheException",
    # Repositories
    "PostgresEmpresaRepository",
    "PostgresRateioRepository",
    "PostgresSyncHistoryRepository",
    "PostgresOutboxRepository",
    "PostgresEventRepository",
    "PostgresUnitOfWork",
    # Event Processor
    "OutboxProcessor",
    "OutboxProcessorFactory"
]
