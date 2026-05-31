import os

from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker
from sqlmodel import SQLModel

# Import models so metadata is registered before create_all.
from src.domain import entities as _entities  # noqa: F401
from src.domain import crud_entities as _crud_entities  # noqa: F401

# URL assíncrona leve para SQLite (aiosqlite)
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite+aiosqlite:///./logos_gateway.db")

# Engine assíncrono com configurações compatíveis com SQLite.
engine = create_async_engine(
    DATABASE_URL,
    echo=False,
    future=True,
    pool_pre_ping=True,
)

async_session = sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False
)


async def init_db():
    """Inicializa o banco de dados e garante criação de tabelas."""
    async with engine.begin() as conn:
        await conn.run_sync(SQLModel.metadata.create_all)


async def get_db():
    """Dependency para obter sessão do banco de dados"""
    async with async_session() as session:
        try:
            yield session
        finally:
            await session.close()
