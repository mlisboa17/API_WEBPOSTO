from __future__ import annotations

from collections.abc import AsyncGenerator

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

GATEWAY_DATABASE_URL = "sqlite+aiosqlite:///./logos_gateway.db"

engine = create_async_engine(GATEWAY_DATABASE_URL, echo=False, future=True)
SessionLocal = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


async def init_gateway_db() -> None:
    async with engine.begin() as conn:
        await conn.execute(
            text(
                """
                CREATE TABLE IF NOT EXISTS posto_credentials (
                    posto_id TEXT PRIMARY KEY,
                    api_key TEXT NOT NULL,
                    base_url TEXT NOT NULL,
                    updated_at TEXT DEFAULT CURRENT_TIMESTAMP
                )
                """
            )
        )


async def get_gateway_db() -> AsyncGenerator[AsyncSession, None]:
    async with SessionLocal() as session:
        yield session
