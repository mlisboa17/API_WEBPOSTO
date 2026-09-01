import logging

from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

from src.infrastructure.config.settings import settings

LOGGER = logging.getLogger(__name__)

# Criar engine async
engine = create_async_engine(
    settings.database_url,
    echo=settings.database_echo,
    pool_size=settings.database_pool_size,
    max_overflow=settings.database_max_overflow,
    pool_pre_ping=True,
    future=True,
)

# Factory para criar sessions
AsyncSessionLocal = sessionmaker(
    engine, class_=AsyncSession, expire_on_commit=False, future=True
)


async def get_db() -> AsyncSession:
    """Dependency para injeção de sessão do banco no FastAPI."""
    async with AsyncSessionLocal() as session:
        try:
            yield session
        finally:
            await session.close()


async def init_db():
    """Sincroniza tabelas SQLModel/Adapter (create_all idempotente)."""
    async with engine.begin() as conn:
        try:
            from src.infrastructure.adapter.database import Base as AdapterBase

            await conn.run_sync(AdapterBase.metadata.create_all)
        except Exception as exc:
            LOGGER.warning("init_db adapter metadata: %s", exc)

        try:
            from sqlmodel import SQLModel
            import src.models.alert_model  # noqa: F401
            import src.models.company_product_model  # noqa: F401
            import src.models.sales_daily_summary_model  # noqa: F401
            import src.models.sds_day_status_model  # noqa: F401
            import src.models.audit_fraud_settings_model  # noqa: F401
            import src.models.forecourt_layout_model  # noqa: F401
            import src.models.notification_profile_model  # noqa: F401

            await conn.run_sync(SQLModel.metadata.create_all)
            LOGGER.info(
                "init_db SQLModel OK — tabelas: executive_alerts, "
                "configuracao_auditoria_fraude, notification_profiles, …"
            )
        except Exception as exc:
            # Não aborta o boot: settings/alerts têm fallback JSON local.
            LOGGER.error("init_db SQLModel falhou: %s", exc, exc_info=True)


async def close_db():
    """Fecha conexão com o banco."""
    await engine.dispose()
