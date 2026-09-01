"""Repositório para preços de concorrentes."""
from __future__ import annotations
from typing import Optional, List
from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select

from src.models.competitor_price_model import CompetitorPriceModel


class CompetitorPriceRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create(self, data: dict) -> CompetitorPriceModel:
        obj = CompetitorPriceModel(**data)
        self._session.add(obj)
        await self._session.commit()
        await self._session.refresh(obj)
        return obj

    async def list(
        self,
        produto_codigo: Optional[str] = None,
        limit: int = 100,
    ) -> List[CompetitorPriceModel]:
        query = select(CompetitorPriceModel).order_by(CompetitorPriceModel.created_at.desc()).limit(limit)
        if produto_codigo:
            query = query.where(CompetitorPriceModel.produto_codigo == produto_codigo)
        result = await self._session.execute(query)
        return list(result.scalars().all())
