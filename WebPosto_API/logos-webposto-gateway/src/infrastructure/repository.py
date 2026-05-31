from typing import Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.domain.entities import (
    PostoCredentials,
    PostoCredentialsRecord,
    TenantPosto,
    TenantPostoRecord,
)


class PostoCredentialsRepository:
    """Repository to access posto credentials in local SQLite."""

    def __init__(self, db_session: AsyncSession):
        self.db = db_session

    async def get_by_posto_id(self, posto_id: str) -> Optional[PostoCredentials]:
        stmt = select(PostoCredentialsRecord).where(PostoCredentialsRecord.posto_id == posto_id)
        result = await self.db.execute(stmt)
        row = result.scalar_one_or_none()
        if row is None:
            return None
        return PostoCredentials(
            id=row.id,
            posto_id=row.posto_id,
            api_key=row.api_key,
            api_secret=row.api_secret,
            status=row.status,
            created_at=row.created_at,
        )

    async def get_all_active(self) -> list[PostoCredentials]:
        stmt = select(PostoCredentialsRecord).where(PostoCredentialsRecord.status == "ativa")
        result = await self.db.execute(stmt)
        rows = result.scalars().all()
        return [
            PostoCredentials(
                id=row.id,
                posto_id=row.posto_id,
                api_key=row.api_key,
                api_secret=row.api_secret,
                status=row.status,
                created_at=row.created_at,
            )
            for row in rows
        ]

    async def get_tenant_by_posto_id(self, posto_id: str) -> Optional[TenantPosto]:
        stmt = select(TenantPostoRecord).where(TenantPostoRecord.id == posto_id)
        result = await self.db.execute(stmt)
        row = result.scalar_one_or_none()
        if row is None:
            return None
        return TenantPosto(
            id=row.id,
            nome_posto=row.nome_posto,
            webposto_base_url=row.webposto_base_url,
            api_key=row.api_key,
            ativo=row.ativo,
        )
