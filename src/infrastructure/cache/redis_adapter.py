"""
Redis Cache Adapter: Cache distribuído para sincronização.

Armazena estado de sincronização em cache para recuperação rápida.
"""

import json
import logging
from typing import Optional, Dict, Any
from datetime import timedelta

import redis.asyncio as redis

logger = logging.getLogger(__name__)


class RedisCacheException(Exception):
    """Exceção de cache Redis."""
    pass


class RedisCacheAdapter:
    async def warmup(self) -> bool:
        """Executa um PING para garantir que o Redis está pronto."""
        try:
            if not self.redis:
                await self.connect()
            await self.redis.ping()
            logger.info("Redis warmup PING OK")
            return True
        except Exception as e:
            logger.error(f"Redis warmup falhou: {e}")
            return False

    async def __aenter__(self):
        await self.connect()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.disconnect()
    """
    Adaptador Redis para cache distribuído.
    
    Features:
    - Connection pooling
    - Serialização JSON
    - TTL configurável
    - Invalidação automática
    """
    
    def __init__(
        self,
        host: str = "localhost",
        port: int = 6379,
        db: int = 0,
        password: Optional[str] = None,
        default_ttl_seconds: int = 3600
    ):
        """
        Inicializar adaptador.
        
        Args:
            host: Host Redis
            port: Porta Redis
            db: Database number
            password: Senha (opcional)
            default_ttl_seconds: TTL padrão em segundos
        """
        self.host = host
        self.port = port
        self.db = db
        self.password = password
        self.default_ttl = timedelta(seconds=default_ttl_seconds)
        self.redis: Optional[redis.Redis] = None
    
    async def connect(self) -> None:
        """Conectar ao Redis usando redis.asyncio."""
        try:
            self.redis = redis.Redis(
                host=self.host,
                port=self.port,
                db=self.db,
                password=self.password,
                encoding="utf-8",
                decode_responses=True,
            )
            # Testar conexão
            await self.redis.ping()
            logger.info(f"Redis conectado: {self.host}:{self.port}")
        except Exception as e:
            logger.error(f"Erro ao conectar em Redis: {e}")
            raise RedisCacheException(f"Redis connection failed: {e}")
    
    async def disconnect(self) -> None:
        """Desconectar do Redis e fechar pool."""
        if self.redis:
            await self.redis.connection_pool.disconnect()
            logger.info("Redis desconectado")
    
    async def get(self, key: str) -> Optional[Dict[str, Any]]:
        """
        Recuperar valor do cache.
        
        Args:
            key: Chave
        
        Returns:
            Valor (dict) ou None
        """
        if not self.redis:
            raise RedisCacheException("Not connected to Redis")
        
        try:
            value = await self.redis.get(key)
            
            if value is None:
                logger.debug(f"Cache miss: {key}")
                return None
            
            logger.debug(f"Cache hit: {key}")
            return json.loads(value)
        
        except Exception as e:
            logger.error(f"Erro ao recuperar do cache: {e}")
            return None
    
    async def set(
        self,
        key: str,
        value: Dict[str, Any],
        ttl: Optional[int|timedelta] = None
    ) -> bool:
        """
        Armazenar valor no cache.
        
        Args:
            key: Chave
            value: Valor (dict)
            ttl: TTL (usa padrão se não especificado)
        
        Returns:
            True se sucesso
        """
        if not self.redis:
            raise RedisCacheException("Not connected to Redis")
        
        try:
            json_value = json.dumps(value)
            # Accept either int seconds or timedelta
            if ttl is None:
                ttl_seconds = int(self.default_ttl.total_seconds())
            elif isinstance(ttl, int):
                ttl_seconds = int(ttl)
            else:
                ttl_seconds = int(ttl.total_seconds())

            await self.redis.setex(key, ttl_seconds, json_value)
            logger.debug(f"Cache set: {key} (TTL: {ttl_seconds}s)")
            
            return True
        
        except Exception as e:
            logger.error(f"Erro ao armazenar no cache: {e}")
            return False
    
    async def delete(self, key: str) -> bool:
        """
        Deletar chave do cache.
        
        Args:
            key: Chave
        
        Returns:
            True se deletado
        """
        if not self.redis:
            raise RedisCacheException("Not connected to Redis")
        
        try:
            result = await self.redis.delete(key)
            logger.debug(f"Cache delete: {key} (result: {result})")
            return result > 0
        
        except Exception as e:
            logger.error(f"Erro ao deletar do cache: {e}")
            return False
    
    async def invalidar_empresa(self, empresa_id: str) -> int:
        """
        Invalidar todos os caches de uma empresa.
        
        Args:
            empresa_id: ID da empresa
        
        Returns:
            Número de chaves deletadas
        """
        if not self.redis:
            raise RedisCacheException("Not connected to Redis")
        
        try:
            pattern = f"empresa:{empresa_id}:*"
            cursor = 0
            count = 0
            
            while True:
                cursor, keys = await self.redis.scan(cursor, match=pattern)
                if keys:
                    count += await self.redis.delete(*keys)
                
                if cursor == 0:
                    break
            
            logger.info(f"Cache invalidado para empresa {empresa_id}: {count} chaves")
            return count
        
        except Exception as e:
            logger.error(f"Erro ao invalidar cache: {e}")
            return 0
    
    async def obter_sync_status(self, sync_id: str) -> Optional[Dict[str, Any]]:
        """
        Recuperar status de sincronização do cache.
        
        Args:
            sync_id: ID de sincronização
        
        Returns:
            Dados de status ou None
        """
        key = f"sync:{sync_id}:status"
        return await self.get(key)
    
    async def armazenar_sync_status(
        self,
        sync_id: str,
        status: Dict[str, Any],
        ttl_minutes: int = 60
    ) -> bool:
        """
        Armazenar status de sincronização em cache.
        
        Args:
            sync_id: ID de sincronização
            status: Dados de status
            ttl_minutes: TTL em minutos
        
        Returns:
            True se sucesso
        """
        key = f"sync:{sync_id}:status"
        ttl = timedelta(minutes=ttl_minutes)
        return await self.set(key, status, ttl)
    
    async def health_check(self) -> bool:
        """
        Verificar saúde do Redis.
        
        Returns:
            True se conectado e respondendo
        """
        if not self.redis:
            return False
        
        try:
            await self.redis.ping()
            return True
        
        except Exception as e:
            logger.error(f"Redis health check failed: {e}")
            return False


class RedisCacheFactory:
    """Factory para criar instâncias do cache Redis."""
    
    @staticmethod
    async def criar_cache(
        host: str = "localhost",
        port: int = 6379,
        **kwargs
    ) -> RedisCacheAdapter:
        """
        Criar novo adaptador Redis.
        
        Args:
            host: Host Redis
            port: Porta Redis
            **kwargs: Argumentos adicionais
        
        Returns:
            Instância do adaptador
        """
        cache = RedisCacheAdapter(host=host, port=port, **kwargs)
        await cache.connect()
        return cache
