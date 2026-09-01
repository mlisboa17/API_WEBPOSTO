"""Repositório de Alertas Executivos — Sprint 50."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import List, Optional

from sqlalchemy import select, and_, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from src.models.alert_model import ExecutiveAlertModel, AlertSeverity, AlertCategory


class ExecutiveAlertRepository:
    """Repositório para persistência e gestão de alertas executivos."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def get_by_external_id(self, external_id: str) -> Optional[ExecutiveAlertModel]:
        """Busca alerta pelo ID externo (idempotência)."""
        stmt = select(ExecutiveAlertModel).where(ExecutiveAlertModel.alert_external_id == external_id)
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def create(self, alert: ExecutiveAlertModel) -> ExecutiveAlertModel:
        """Persiste um novo alerta (safe sob corrida em alert_external_id)."""
        self.session.add(alert)
        try:
            await self.session.commit()
            await self.session.refresh(alert)
            return alert
        except IntegrityError:
            await self.session.rollback()
            existing = await self.get_by_external_id(alert.alert_external_id)
            if existing is not None:
                return existing
            raise

    async def list_unresolved(self, unit_id: Optional[int] = None) -> List[ExecutiveAlertModel]:
        """Lista alertas pendentes, opcionalmente filtrados por unidade."""
        stmt = select(ExecutiveAlertModel).where(ExecutiveAlertModel.is_resolved == False)
        if unit_id is not None:
            stmt = stmt.where(ExecutiveAlertModel.unit_id == unit_id)
        
        result = await self.session.execute(stmt.order_by(ExecutiveAlertModel.created_at.desc()))
        return list(result.scalars().all())

    async def get_history(
        self, 
        unit_id: Optional[int] = None, 
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None
    ) -> List[ExecutiveAlertModel]:
        """Histórico de alertas (resolvidos ou todos) por período/unidade."""
        stmt = select(ExecutiveAlertModel)
        
        filters = []
        if unit_id is not None:
            filters.append(ExecutiveAlertModel.unit_id == unit_id)
        if start_date:
            filters.append(ExecutiveAlertModel.created_at >= start_date)
        if end_date:
            filters.append(ExecutiveAlertModel.created_at <= end_date)
            
        if filters:
            stmt = stmt.where(and_(*filters))
            
        result = await self.session.execute(stmt.order_by(ExecutiveAlertModel.created_at.desc()))
        return list(result.scalars().all())

    async def resolve(
        self, 
        alert_id: int, 
        resolved_by: str, 
        notes: Optional[str] = None
    ) -> bool:
        """Marca um alerta como resolvido."""
        stmt = (
            update(ExecutiveAlertModel)
            .where(ExecutiveAlertModel.id == alert_id)
            .values(
                is_resolved=True,
                resolved_at=datetime.now(timezone.utc),
                resolved_by=resolved_by,
                resolution_notes=notes
            )
        )
        result = await self.session.execute(stmt)
        await self.session.commit()
        return result.rowcount > 0
