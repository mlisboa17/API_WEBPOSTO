from typing import List, Optional
from uuid import uuid4

from src.application.dto.cliente_dto import (
    ClienteCreateDTO,
    ClienteResponseDTO,
    ClienteUpdateDTO,
)
from src.domain.entities.cliente import Cliente
from src.domain.events.cliente_events import ClienteAdicionado, ClienteAtualizado
from src.domain.repositories.cliente_repository import ClienteRepository
from src.infrastructure.event_bus.redis_event_bus import RedisEventBus
from src.shared.logger import get_logger

logger = get_logger(__name__)


class ClienteService:
    """Serviço de Clientes - Orquestra domain e event bus."""

    def __init__(self, repository: ClienteRepository, event_bus: RedisEventBus):
        self.repository = repository
        self.event_bus = event_bus

    async def criar_cliente(self, dto: ClienteCreateDTO) -> ClienteResponseDTO:
        """Cria um novo cliente."""
        cliente_id = str(uuid4())

        cliente = Cliente(
            id=cliente_id,
            nome=dto.nome,
            cnpj=dto.cnpj,
            webposto_id=dto.webposto_id,
        )

        # Salva no repositório
        await self.repository.save(cliente)

        # Publica evento de domínio
        evento = ClienteAdicionado(
            aggregate_id=cliente_id,
            nome=cliente.nome,
            cnpj=cliente.cnpj,
        )
        await self.event_bus.publish(evento)

        logger.info(f"Cliente criado: {cliente_id}")
        return ClienteResponseDTO.model_validate(cliente)

    async def obter_cliente(self, cliente_id: str) -> Optional[ClienteResponseDTO]:
        """Obtém um cliente por ID."""
        cliente = await self.repository.find_by_id(cliente_id)
        if not cliente:
            logger.warning(f"Cliente não encontrado: {cliente_id}")
            return None
        return ClienteResponseDTO.model_validate(cliente)

    async def obter_por_cnpj(self, cnpj: str) -> Optional[ClienteResponseDTO]:
        """Obtém um cliente por CNPJ."""
        cliente = await self.repository.find_by_cnpj(cnpj)
        if not cliente:
            return None
        return ClienteResponseDTO.model_validate(cliente)

    async def listar_clientes(
        self, skip: int = 0, limit: int = 100
    ) -> List[ClienteResponseDTO]:
        """Lista todos os clientes."""
        clientes = await self.repository.find_all(skip, limit)
        return [ClienteResponseDTO.model_validate(c) for c in clientes]

    async def listar_ativos(
        self, skip: int = 0, limit: int = 100
    ) -> List[ClienteResponseDTO]:
        """Lista apenas clientes ativos."""
        clientes = await self.repository.find_all_ativos(skip, limit)
        return [ClienteResponseDTO.model_validate(c) for c in clientes]

    async def atualizar_cliente(
        self, cliente_id: str, dto: ClienteUpdateDTO
    ) -> Optional[ClienteResponseDTO]:
        """Atualiza um cliente existente."""
        cliente = await self.repository.find_by_id(cliente_id)
        if not cliente:
            logger.warning(f"Cliente não encontrado para atualizar: {cliente_id}")
            return None

        # Atualiza dados
        if dto.nome:
            cliente.nome = dto.nome
        if dto.cnpj:
            cliente.cnpj = dto.cnpj
        if dto.ativo is not None:
            cliente.ativo = dto.ativo

        # Salva atualização
        await self.repository.update(cliente_id, cliente)

        # Publica evento
        evento = ClienteAtualizado(
            aggregate_id=cliente_id,
            nome=cliente.nome,
            cnpj=cliente.cnpj,
        )
        await self.event_bus.publish(evento)

        logger.info(f"Cliente atualizado: {cliente_id}")
        return ClienteResponseDTO.model_validate(cliente)

    async def deletar_cliente(self, cliente_id: str) -> bool:
        """Deleta um cliente."""
        success = await self.repository.delete(cliente_id)
        if success:
            logger.info(f"Cliente deletado: {cliente_id}")
        else:
            logger.warning(f"Cliente não encontrado para deletar: {cliente_id}")
        return success
