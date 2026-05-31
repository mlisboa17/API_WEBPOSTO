import asyncio
import os
from src.infrastructure.base import Base
# Executa o create_all automaticamente ao importar este módulo (apenas em ambiente de teste/dev)
async def _auto_schema():
    try:
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
    except Exception as e:
        print(f"[AutoSchema] Falha ao criar schema: {e}")

if __name__ != "__main__":
    try:
        asyncio.get_event_loop().run_until_complete(_auto_schema())
    except RuntimeError:
        asyncio.run(_auto_schema())
import asyncio
import logging
# Healthcheck async para o pool
async def check_readiness(engine) -> bool:
    try:
        async with engine.connect() as conn:
            from sqlalchemy import text
            result = await conn.execute(text("SELECT 1"))
            await conn.close()
        return True
    except Exception as e:
        logging.error(f"[HEALTHCHECK] DB pool não está pronto: {e}")
        # Tenta reconectar após 2s
        await asyncio.sleep(2)
        return False
"""
Async SQLAlchemy Engine and Session Factory for Postgres 17 (asyncpg)
"""
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession, AsyncEngine
from sqlalchemy.orm import DeclarativeBase
from typing import AsyncGenerator
import contextlib

DB_URL = os.environ.get("DATABASE_URL", "postgresql+asyncpg://postgres:admin@localhost:5432/logos_space")

# Declarative base for models
class Base(DeclarativeBase):
    pass

# Async engine with optimized pool
engine: AsyncEngine = create_async_engine(
    DB_URL,
    echo=False,
    pool_size=10,
    max_overflow=20,
    pool_pre_ping=True,
    future=True,
)

# Async session factory
async_session: async_sessionmaker[AsyncSession] = async_sessionmaker(
    engine, expire_on_commit=False, class_=AsyncSession
)

@contextlib.asynccontextmanager
async def get_session() -> AsyncGenerator[AsyncSession, None]:
    async with async_session() as session:
        yield session
