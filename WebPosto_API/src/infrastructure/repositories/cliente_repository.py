from typing import List, Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.domain.entities.cliente import Cliente
from src.domain.repositories.cliente_repository import (
    ClienteRepository as ClienteRepositoryInterface,
)
from src.infrastructure.repositories.models import ClienteModel
from src.shared.logger import get_logger

logger = get_logger(__name__)


class SQLAlchemyClienteRepository(ClienteRepositoryInterface):
    """Implementação de ClienteRepository com SQLAlchemy (Adapter)."""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def save(self, entity: Cliente) -> Cliente:
        """Salva (create ou update) um cliente."""
        model = ClienteModel(
            id=entity.id,
            nome=entity.nome,
            cnpj=entity.cnpj,
            ativo=entity.ativo,
            webposto_id=entity.webposto_id,
            created_at=entity.created_at,
            updated_at=entity.updated_at,
        )
        self.session.add(model)
        await self.session.flush()
        logger.info(f"Cliente salvo: {entity.id}")
        return entity

    async def find_by_id(self, entity_id: str) -> Optional[Cliente]:
        """Encontra cliente por ID."""
        stmt = select(ClienteModel).where(ClienteModel.id == entity_id)
        result = await self.session.execute(stmt)
        model = result.scalar_one_or_none()
        if not model:
            return None
        return self._model_to_entity(model)

    async def find_all(self, skip: int = 0, limit: int = 100) -> List[Cliente]:
        """Lista clientes com paginação."""
        stmt = select(ClienteModel).offset(skip).limit(limit)
        result = await self.session.execute(stmt)
        models = result.scalars().all()
        return [self._model_to_entity(m) for m in models]

    async def find_by_cnpj(self, cnpj: str) -> Optional[Cliente]:
        """Encontra cliente por CNPJ."""
        stmt = select(ClienteModel).where(ClienteModel.cnpj == cnpj)
        result = await self.session.execute(stmt)
        model = result.scalar_one_or_none()
        if not model:
            return None
        return self._model_to_entity(model)

    async def find_by_webposto_id(self, webposto_id: str) -> Optional[Cliente]:
        """Encontra cliente por ID do webPosto."""
        stmt = select(ClienteModel).where(ClienteModel.webposto_id == webposto_id)
        result = await self.session.execute(stmt)
        model = result.scalar_one_or_none()
        if not model:
            return None
        return self._model_to_entity(model)

    async def find_all_ativos(self, skip: int = 0, limit: int = 100) -> List[Cliente]:
        """Lista apenas clientes ativos."""
        stmt = (
            select(ClienteModel)
            .where(ClienteModel.ativo == True)
            .offset(skip)
            .limit(limit)
        )
        result = await self.session.execute(stmt)
        models = result.scalars().all()
        return [self._model_to_entity(m) for m in models]

    async def update(self, entity_id: str, entity: Cliente) -> Optional[Cliente]:
        """Atualiza um cliente."""
        stmt = select(ClienteModel).where(ClienteModel.id == entity_id)
        result = await self.session.execute(stmt)
        model = result.scalar_one_or_none()

        if not model:
            return None

        model.nome = entity.nome
        model.cnpj = entity.cnpj
        model.ativo = entity.ativo
        model.updated_at = entity.updated_at

        await self.session.flush()
        logger.info(f"Cliente atualizado: {entity_id}")
        return entity

    async def delete(self, entity_id: str) -> bool:
        """Deleta um cliente."""
        stmt = select(ClienteModel).where(ClienteModel.id == entity_id)
        result = await self.session.execute(stmt)
        model = result.scalar_one_or_none()

        if not model:
            return False

        await self.session.delete(model)
        await self.session.flush()
        logger.info(f"Cliente deletado: {entity_id}")
        return True

    @staticmethod
    def _model_to_entity(model: ClienteModel) -> Cliente:
        """Converte ORM model para domain entity."""
        return Cliente(
            id=model.id,
            nome=model.nome,
            cnpj=model.cnpj,
            ativo=model.ativo,
            webposto_id=model.webposto_id,
            created_at=model.created_at,
            updated_at=model.updated_at,
        )
