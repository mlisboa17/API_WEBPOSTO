import json
from typing import Any, Callable, Dict, List

import redis.asyncio as redis

from src.infrastructure.config.settings import settings
from src.shared.domain_event import DomainEvent
from src.shared.logger import get_logger

logger = get_logger(__name__)


class RedisEventBus:
    """Event Bus usando Redis Pub/Sub. Implementação do padrão Adapter."""

    def __init__(self, redis_url: str = settings.redis_url):
        self.redis_url = redis_url
        self.redis: redis.Redis = None
        self.pubsub = None
        self.handlers: Dict[str, List[Callable]] = {}

    async def connect(self):
        """Conecta ao Redis."""
        try:
            self.redis = await redis.from_url(self.redis_url, decode_responses=True)
            self.pubsub = self.redis.pubsub()
            logger.info("Conectado ao Redis")
        except Exception as e:
            logger.error(f"Erro ao conectar Redis: {str(e)}")
            raise

    async def disconnect(self):
        """Desconecta do Redis."""
        if self.pubsub:
            await self.pubsub.close()
        if self.redis:
            await self.redis.close()
        logger.info("Desconectado do Redis")

    async def publish(self, event: DomainEvent):
        """Publica um evento no Redis."""
        channel = f"events:{event.event_name}"
        payload = self._serialize_event(event)

        try:
            await self.redis.publish(channel, payload)
            logger.info(f"Evento publicado: {event.event_name}", channel=channel)
        except Exception as e:
            logger.error(
                f"Erro ao publicar evento: {str(e)}",
                event_name=event.event_name,
            )
            raise

    async def subscribe(
        self, event_name: str, handler: Callable[[Dict[str, Any]], None]
    ):
        """Se inscreve a um tipo de evento."""
        if event_name not in self.handlers:
            self.handlers[event_name] = []
        self.handlers[event_name].append(handler)
        logger.info(f"Handler registrado para: {event_name}")

    async def listen(self):
        """Listener long-running que processa eventos."""
        logger.info("Iniciando listener de eventos")
        try:
            # Se inscreve em todos os eventos
            await self.pubsub.psubscribe("events:*")

            async for message in self.pubsub.listen():
                if message["type"] == "pmessage":
                    channel = message["channel"]
                    event_name = channel.replace("events:", "")
                    payload = message["data"]

                    # Desserializa e processa
                    await self._process_event(event_name, payload)
        except Exception as e:
            logger.error(f"Erro no listener: {str(e)}")
            raise

    async def _process_event(self, event_name: str, payload: str):
        """Processa um evento e chama handlers."""
        try:
            data = json.loads(payload)
            handlers = self.handlers.get(event_name, [])

            for handler in handlers:
                try:
                    if hasattr(handler, "__await__"):
                        await handler(data)
                    else:
                        handler(data)
                except Exception as e:
                    logger.error(
                        f"Erro ao executar handler: {str(e)}", event=event_name
                    )
        except json.JSONDecodeError as e:
            logger.error(f"Erro ao desserializar evento: {str(e)}")

    @staticmethod
    def _serialize_event(event: DomainEvent) -> str:
        """Serializa evento para JSON."""
        return json.dumps(
            {
                "event_id": event.event_id,
                "event_name": event.event_name,
                "timestamp": event.timestamp.isoformat(),
                "aggregate_id": event.aggregate_id,
                **event.__dict__,
            },
            default=str,
        )

    @staticmethod
    def _deserialize_event(payload: str) -> Dict[str, Any]:
        """Desserializa JSON para dicionário."""
        return json.loads(payload)
