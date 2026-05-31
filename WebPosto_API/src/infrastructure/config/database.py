from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

from src.infrastructure.config.settings import settings


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
    """Inicializa o banco de dados."""
    async with engine.begin() as conn:
        # Import models' Base metadata and create tables if missing
        try:
            from src.infrastructure.adapter.database import Base as AdapterBase

            await conn.run_sync(AdapterBase.metadata.create_all)
        except Exception:
            # If adapter isn't present or models are not yet defined, skip gracefully
            pass


async def close_db():
    """Fecha conexão com o banco."""
    await engine.dispose()
