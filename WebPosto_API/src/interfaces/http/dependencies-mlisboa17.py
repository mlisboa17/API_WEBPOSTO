"""
FastAPI Dependencies - Injeção de Dependências
Configuração de injeção para serviços e repositórios
"""

from typing import AsyncGenerator

from src.application.services.auditoria_service import AuditoriaService
from src.application.services.cliente_service import ClienteService
from src.infrastructure.repositories.auditoria_repository import AuditoriaRepository
from src.infrastructure.repositories.cliente_repository import ClienteRepository
from src.infrastructure.webposto.client import WebPostoClient
from src.infrastructure.config.database import get_session
from src.shared.logger import logger

__all__ = [
    "get_auditoria_service",
    "get_cliente_service",
    "get_auditoria_repository",
    "get_cliente_repository",
    "get_webposto_client",
]

log = logger.getChild(__name__)


async def get_webposto_client() -> AsyncGenerator[WebPostoClient, None]:
    """
    Fornece instância do cliente webPosto

    Yields:
        WebPostoClient configurado e inicializado
    """
    client = WebPostoClient()
    try:
        yield client
    finally:
        pass  # Cleanup se necessário


async def get_auditoria_repository() -> AsyncGenerator[AuditoriaRepository, None]:
    """
    Fornece instância do repositório de auditoria

    Yields:
        AuditoriaRepository configurado
    """
    session = await get_session()
    repository = AuditoriaRepository(session=session)
    try:
        yield repository
    finally:
        pass  # Cleanup se necessário


async def get_auditoria_service() -> AuditoriaService:
    """
    Fornece instância do serviço de auditoria com injeção de dependências

    Returns:
        AuditoriaService totalmente configurado
    """
    session = await get_session()
    repository = AuditoriaRepository(session=session)
    return AuditoriaService(repository=repository)