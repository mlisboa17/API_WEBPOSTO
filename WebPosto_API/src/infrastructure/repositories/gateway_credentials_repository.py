from __future__ import annotations

from typing import Optional

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession


class GatewayCredentialsRepository:
    def __init__(self, db: AsyncSession) -> None:
        self._db = db

    async def find_by_posto_id(self, posto_id: str) -> Optional[dict[str, str]]:
        query = text(
            "SELECT posto_id, api_key, base_url FROM posto_credentials WHERE posto_id = :posto_id"
        )
        result = await self._db.execute(query, {"posto_id": posto_id})
        row = result.mappings().first()
        if not row:
            return None
        return {
            "posto_id": str(row["posto_id"]),
            "api_key": str(row["api_key"]),
            "base_url": str(row["base_url"]),
        }
