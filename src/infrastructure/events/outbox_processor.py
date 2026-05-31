"""
Outbox Processor: Background worker para publicar eventos.

Lê eventos da tabela Outbox e os publica em fila de mensagens.
"""

import asyncio
import logging
from typing import Optional, Callable
from datetime import datetime, timedelta

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from src.infrastructure.persistence.postgresql.repositories import (
    PostgresOutboxRepository
)

logger = logging.getLogger(__name__)


class OutboxProcessor:
    """
    Processador Outbox: Lê eventos não processados e publica.
    
    Features:
    - Polling configurável
    - Retry automático com backoff
    - Batch processing
    - Limpeza de eventos antigos
    """
    
    def __init__(
        self,
        session_factory: async_sessionmaker,
        poll_interval_seconds: int = 5,
        batch_size: int = 100,
        max_retries: int = 3,
        cleanup_days: int = 7
    ):
        """
        Inicializar processador.
        
        Args:
            session_factory: AsyncSession factory
            poll_interval_seconds: Intervalo de polling
            batch_size: Tamanho do batch
            max_retries: Tentativas máximas por evento
            cleanup_days: Remover eventos processados após X dias
        """
        self.session_factory = session_factory
        self.poll_interval = poll_interval_seconds
        self.batch_size = batch_size
        self.max_retries = max_retries
        self.cleanup_days = cleanup_days
        
        self.running = False
        self.event_handler: Optional[Callable] = None
        self.error_handler: Optional[Callable] = None
    
    def registrar_handler(self, handler: Callable) -> None:
        """
        Registrar handler para eventos publicados.
        
        Args:
            handler: Função async(event_type, event_data) -> None
        """
        self.event_handler = handler
        logger.info(f"Handler registrado: {handler.__name__}")
    
    def registrar_error_handler(self, handler: Callable) -> None:
        """
        Registrar handler para erros.
        
        Args:
            handler: Função async(outbox_id, error) -> None
        """
        self.error_handler = handler
        logger.info(f"Error handler registrado: {handler.__name__}")
    
    async def iniciar(self) -> None:
        """Iniciar processador."""
        self.running = True
        logger.info("Outbox Processor iniciado")
        
        try:
            await self._loop_processamento()
        
        except asyncio.CancelledError:
            logger.info("Outbox Processor cancelado")
            self.running = False
        
        except Exception as e:
            logger.error(f"Erro no Outbox Processor: {e}", exc_info=True)
            self.running = False
    
    async def parar(self) -> None:
        """Parar processador."""
        self.running = False
        logger.info("Outbox Processor parado")
    
    async def _loop_processamento(self) -> None:
        """Loop principal de processamento."""
        while self.running:
            try:
                # 1. Processar eventos não processados
                await self._processar_eventos()
                
                # 2. Limpar eventos antigos (a cada 10 iterações)
                if int(datetime.utcnow().timestamp()) % 50 == 0:
                    await self._limpar_eventos_processados()
                
                # 3. Aguardar próximo ciclo
                await asyncio.sleep(self.poll_interval)
            
            except Exception as e:
                logger.error(f"Erro no loop de processamento: {e}", exc_info=True)
                await asyncio.sleep(self.poll_interval)
    
    async def _processar_eventos(self) -> None:
        """Processar batch de eventos."""
        async with self.session_factory() as session:
            outbox_repo = PostgresOutboxRepository(session)
            
            # Recuperar eventos não processados
            eventos = await outbox_repo.obter_nao_processados()
            
            if not eventos:
                return
            
            logger.info(f"Processando {len(eventos)} eventos do Outbox")
            
            # Processar em batch
            for evento in eventos[:self.batch_size]:
                await self._processar_evento(evento, outbox_repo, session)
    
    async def _processar_evento(self, evento, outbox_repo, session) -> None:
        """Processar um evento individual."""
        try:
            logger.debug(f"Publicando evento: {evento.outbox_id} ({evento.event_type})")
            
            # Chamar handler registrado
            if self.event_handler:
                await self.event_handler(evento.event_type, evento.event_data)
            
            # Marcar como processado
            await outbox_repo.marcar_processado(evento.outbox_id)
            await session.commit()
            
            logger.info(f"Evento publicado: {evento.outbox_id}")
        
        except Exception as e:
            logger.error(f"Erro ao processar evento {evento.outbox_id}: {e}")
            
            # Incrementar tentativas
            tentativas = await outbox_repo.incrementar_tentativas(evento.outbox_id)
            
            # Chamar error handler se configurado
            if self.error_handler:
                await self.error_handler(evento.outbox_id, str(e))
            
            # Se excedeu máx tentativas, logar
            if tentativas >= self.max_retries:
                logger.error(f"Evento {evento.outbox_id} falhou após {tentativas} tentativas")
            
            await session.commit()
    
    async def _limpar_eventos_processados(self) -> None:
        """Limpar eventos processados antigos."""
        try:
            async with self.session_factory() as session:
                outbox_repo = PostgresOutboxRepository(session)
                
                count = await outbox_repo.limpar_processados(self.cleanup_days)
                
                if count > 0:
                    await session.commit()
                    logger.info(f"Limpeza Outbox: {count} eventos removidos")
        
        except Exception as e:
            logger.error(f"Erro ao limpar Outbox: {e}")


class OutboxProcessorFactory:
    """Factory para criar instâncias do processador."""
    
    @staticmethod
    def criar_processador(
        session_factory: async_sessionmaker,
        **kwargs
    ) -> OutboxProcessor:
        """
        Criar novo processador Outbox.
        
        Args:
            session_factory: AsyncSession factory
            **kwargs: Argumentos adicionais
        
        Returns:
            Instância do processador
        """
        return OutboxProcessor(session_factory=session_factory, **kwargs)
