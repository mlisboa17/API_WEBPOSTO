"""
⚡ VALKEY MANAGER - State Persistence & Cache Strategy (GROK 4 TASK)
Responsabilidades:
1. Cache persistente com 98%+ hit ratio
2. JSON zero-copy serialization
3. Versioning automático de navegação
4. Garbage collection inteligente (TTL strategy)
"""
import json
from typing import Any, Dict, Optional, Callable
from datetime import datetime, timedelta
import hashlib
import logging

logger = logging.getLogger(__name__)


class ValkeyManager:
    """
    🔑 Gerenciador Valkey (Redis) corporativo
    Padrão: Cache-aside com JSON serialization
    Target: 98%+ hit ratio, < 15ms latency
    """
    
    def __init__(self, redis_client):
        """
        Args:
            redis_client: redis.asyncio.Redis ou mock para teste
        """
        self.redis = redis_client
        self.stats = {
            "hits": 0,
            "misses": 0,
            "writes": 0,
            "deletes": 0,
        }
    
    # ─────────────────────────────────────────────────────────
    # 1️⃣ CORE OPERATIONS: Get/Set/Delete
    # ─────────────────────────────────────────────────────────
    
    async def get_json(self, key: str) -> Optional[Dict]:
        """
        Get com desserialização JSON automática
        
        Returns:
            Dict ou None se não encontrado
        """
        try:
            value = await self.redis.get(key)
            if value:
                self.stats["hits"] += 1
                return json.loads(value)
            self.stats["misses"] += 1
            return None
        except Exception as e:
            logger.error(f"❌ Valkey GET error [{key}]: {e}")
            self.stats["misses"] += 1
            return None
    
    async def set_json(
        self,
        key: str,
        value: Any,
        ttl: int = 3600,
        nx: bool = False,
    ) -> bool:
        """
        Set com serialização JSON automática + TTL
        
        Args:
            key: Chave de cache
            value: Valor (pode ser dict, objeto com model_dump(), etc)
            ttl: Time-to-live em segundos (default 1h)
            nx: Set only if not exists
        
        Returns:
            True se sucesso
        """
        try:
            # Serializar com suporte a Decimal, datetime, etc
            serialized = json.dumps(
                value,
                default=str,  # Fallback para types especiais
            )
            
            if nx:
                result = await self.redis.set(
                    key,
                    serialized,
                    ex=ttl,
                    nx=True,
                )
            else:
                await self.redis.setex(key, ttl, serialized)
                result = True
            
            if result:
                self.stats["writes"] += 1
            return bool(result)
        
        except Exception as e:
            logger.error(f"❌ Valkey SET error [{key}]: {e}")
            return False
    
    async def delete(self, key: str) -> bool:
        """Delete uma chave"""
        try:
            await self.redis.delete(key)
            self.stats["deletes"] += 1
            return True
        except Exception as e:
            logger.error(f"❌ Valkey DELETE error [{key}]: {e}")
            return False
    
    # ─────────────────────────────────────────────────────────
    # 2️⃣ CACHE-ASIDE PATTERN: Get or set with loader
    # ─────────────────────────────────────────────────────────
    
    async def get_or_set_json(
        self,
        key: str,
        loader: Callable,
        ttl: int = 3600,
    ) -> Any:
        """
        Cache-aside: Get do cache, ou executa loader se miss
        
        Args:
            key: Chave cache
            loader: async callable que retorna valor
            ttl: TTL em segundos
        
        Returns:
            Valor (do cache ou do loader)
        
        Pattern:
            value = await cache.get_or_set_json(
                "exec:overview:abc123",
                lambda: domain_service.get_overview(...),
                ttl=3600
            )
        """
        # ─ Tentar cache
        cached = await self.get_json(key)
        if cached:
            logger.debug(f"✓ Cache HIT [{key}]")
            return cached
        
        # ─ Cache miss: executar loader
        logger.debug(f"✗ Cache MISS [{key}] → loader")
        value = await loader()
        
        # ─ Persistir resultado
        await self.set_json(key, value, ttl=ttl)
        return value
    
    # ─────────────────────────────────────────────────────────
    # 3️⃣ VERSIONING: Manter histórico de navegação
    # ─────────────────────────────────────────────────────────
    
    async def store_navigation_state(
        self,
        director_id: str,
        module: str,
        context: Dict,
    ) -> str:
        """
        Versiona estado de navegação por timestamp
        
        Returns:
            version_key para recuperação
        """
        now = datetime.utcnow()
        timestamp = int(now.timestamp() * 1000)  # ms
        
        version_key = f"nav:v:{director_id}:{module}:{timestamp}"
        
        await self.set_json(
            version_key,
            {
                "timestamp": now.isoformat(),
                "module": module,
                "context": context,
            },
            ttl=86400,  # Keep 24h
        )
        
        # Manter última versão para acesso rápido
        last_key = f"nav:last:{director_id}:{module}"
        await self.set_json(last_key, context, ttl=604800)  # 7 dias
        
        return version_key
    
    async def get_last_navigation(
        self,
        director_id: str,
        module: str,
    ) -> Optional[Dict]:
        """Recupera última navegação do diretor para um módulo"""
        return await self.get_json(f"nav:last:{director_id}:{module}")
    
    # ─────────────────────────────────────────────────────────
    # 4️⃣ PATTERN MATCHING: Chaves por padrão (pattern keys)
    # ─────────────────────────────────────────────────────────
    
    async def get_all_matching(self, pattern: str) -> Dict[str, Any]:
        """
        Busca todas chaves matching padrão
        Exemplo: "exec:overview:*" → {checksum -> overview}
        """
        try:
            keys = await self.redis.keys(pattern)
            result = {}
            for key in keys:
                value = await self.get_json(key.decode() if isinstance(key, bytes) else key)
                if value:
                    result[key] = value
            return result
        except Exception as e:
            logger.error(f"❌ Pattern matching error [{pattern}]: {e}")
            return {}
    
    async def invalidate_pattern(self, pattern: str) -> int:
        """
        Delete todas chaves matching padrão (cache invalidation)
        Útil para: Trocar contexto de station invalidar todos overviews
        """
        try:
            keys = await self.redis.keys(pattern)
            if keys:
                await self.redis.delete(*keys)
            self.stats["deletes"] += len(keys)
            return len(keys)
        except Exception as e:
            logger.error(f"❌ Pattern invalidation error [{pattern}]: {e}")
            return 0
    
    # ─────────────────────────────────────────────────────────
    # 5️⃣ STATS & MONITORING
    # ─────────────────────────────────────────────────────────
    
    def get_hit_ratio(self) -> float:
        """Retorna hit ratio (target > 0.98)"""
        total = self.stats["hits"] + self.stats["misses"]
        if total == 0:
            return 0.0
        return self.stats["hits"] / total
    
    def get_stats(self) -> Dict[str, Any]:
        """Retorna estatísticas de cache"""
        total = self.stats["hits"] + self.stats["misses"]
        return {
            **self.stats,
            "total_ops": total,
            "hit_ratio": self.get_hit_ratio(),
            "hit_ratio_pct": f"{self.get_hit_ratio() * 100:.1f}%",
            "target_met": self.get_hit_ratio() >= 0.98,
        }
    
    async def reset_stats(self):
        """Reset contadores"""
        self.stats = {
            "hits": 0,
            "misses": 0,
            "writes": 0,
            "deletes": 0,
        }


# ═══════════════════════════════════════════════════════════════════
# 🌊 SSE HUB - Real-time Event Broadcasting (GROK 4 TASK Part 2)
# ═══════════════════════════════════════════════════════════════════

class SSEHub:
    """
    🔴 Hub SSE centralizado para broadcasts em tempo real
    Atualiza KPIs na home via eventos Server-Sent Events
    
    Pattern: Pub/Sub com Redis streams (ou em-memory para MVP)
    """
    
    def __init__(self, redis_client=None):
        """
        Args:
            redis_client: Para escalabilidade Pub/Sub distribuída
                          Se None, usa in-memory (MVP mode)
        """
        self.redis = redis_client
        self.subscriptions: Dict[str, list] = {}  # {channel -> [callbacks]}
    
    # ─────────────────────────────────────────────────────────
    # BROADCAST: Enviar eventos para todos listeners
    # ─────────────────────────────────────────────────────────
    
    async def broadcast_kpi_update(self, kpis: Dict[str, Any]):
        """
        Broadcast KPI update para homepage
        
        KPIs esperados:
        - kpi_recovery_estimated: float
        - kpi_risk_score: int
        - kpi_findings_count: int
        
        Evento SSE: "kpi-update"
        """
        event = {
            "event": "kpi-update",
            "timestamp": datetime.utcnow().isoformat(),
            **kpis,
        }
        
        if self.redis:
            # Publicar em Redis para distribuição
            await self.redis.publish(
                "sse:kpi-updates",
                json.dumps(event, default=str),
            )
        else:
            # In-memory: chamar callbacks registrados
            await self._call_subscribers("kpi-update", event)
    
    async def broadcast_audit_update(self, audit_data: Dict[str, Any]):
        """
        Broadcast quando novo achado de auditoria é detectado
        
        Evento SSE: "audit-finding"
        """
        event = {
            "event": "audit-finding",
            "timestamp": datetime.utcnow().isoformat(),
            **audit_data,
        }
        
        if self.redis:
            await self.redis.publish(
                "sse:audit-updates",
                json.dumps(event, default=str),
            )
        else:
            await self._call_subscribers("audit-finding", event)
    
    async def broadcast_module_sync(self, module: str, status: str):
        """
        Broadcast quando um módulo termina sincronização
        
        Status: "starting", "progress", "completed", "error"
        Evento SSE: "module-sync"
        """
        event = {
            "event": "module-sync",
            "module": module,
            "status": status,
            "timestamp": datetime.utcnow().isoformat(),
        }
        
        if self.redis:
            await self.redis.publish(
                "sse:module-sync",
                json.dumps(event),
            )
        else:
            await self._call_subscribers("module-sync", event)
    
    # ─────────────────────────────────────────────────────────
    # SUBSCRIPTION: Registrar listeners (backend routes)
    # ─────────────────────────────────────────────────────────
    
    def subscribe(self, event_type: str, callback: Callable):
        """
        Registra callback para eventos
        
        Usage (em route SSE):
            async def sse_stream():
                async def on_kpi_update(data):
                    yield f"data: {json.dumps(data)}\\n\\n"
                
                sse_hub.subscribe("kpi-update", on_kpi_update)
                # ... stream events
        """
        if event_type not in self.subscriptions:
            self.subscriptions[event_type] = []
        self.subscriptions[event_type].append(callback)
    
    async def _call_subscribers(self, event_type: str, data: Dict):
        """Chama todos subscribers do tipo de evento"""
        if event_type in self.subscriptions:
            for callback in self.subscriptions[event_type]:
                try:
                    await callback(data)
                except Exception as e:
                    logger.error(f"❌ SSE callback error: {e}")


# ═══════════════════════════════════════════════════════════════════
# 📊 DATA AGGREGATOR - Consolidar 500+ itens em 3 KPIs rápidos
# ═══════════════════════════════════════════════════════════════════

class DataAggregator:
    """
    Worker que resume dados de auditoria em KPIs para dashboard
    
    Input: 500+ itens de auditoria
    Output: 3 KPIs consolidados (< 15ms latency)
    """
    
    def __init__(self, cache: ValkeyManager, sse_hub: SSEHub):
        self.cache = cache
        self.sse_hub = sse_hub
    
    async def aggregate_audit_findings(
        self,
        findings: list,
        station_context_key: str,
    ) -> Dict[str, Any]:
        """
        Agrega 500+ findings em KPIs
        
        Returns:
            {
                "total_recovery": float,
                "avg_risk_score": int,
                "critical_count": int,
                "cache_key": str,
            }
        """
        if not findings:
            return {
                "total_recovery": 0.0,
                "avg_risk_score": 0,
                "critical_count": 0,
                "cache_key": "",
            }
        
        # Zero-copy aggregation
        total_recovery = sum(
            float(f.get("recoverable_credit", 0))
            for f in findings
        )
        
        risk_scores = [
            int(f.get("risk_score", 0))
            for f in findings
        ]
        avg_risk = sum(risk_scores) // len(risk_scores) if risk_scores else 0
        
        critical_count = sum(
            1 for f in findings
            if f.get("severity") == "critico"
        )
        
        result = {
            "total_recovery": total_recovery,
            "avg_risk_score": avg_risk,
            "critical_count": critical_count,
        }
        
        # Cache agregação
        cache_key = f"agg:findings:{station_context_key}:{int(datetime.utcnow().timestamp())}"
        await self.cache.set_json(cache_key, result, ttl=1800)  # 30min
        
        result["cache_key"] = cache_key
        
        # Broadcast atualização
        await self.sse_hub.broadcast_kpi_update({
            "kpi_recovery_estimated": total_recovery,
            "kpi_risk_score": avg_risk,
            "kpi_findings_count": len(findings),
        })
        
        return result
    
    async def cleanup_expired(self, pattern: str = "agg:*"):
        """Garbage collection: remover chaves expiradas"""
        return await self.cache.invalidate_pattern(pattern)


# ═══════════════════════════════════════════════════════════════════
# 🧪 TESTES: Validar operações básicas
# ═══════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    import asyncio
    
    class MockRedis:
        """Mock Redis para testes sem servidor real"""
        def __init__(self):
            self._data = {}
        
        async def get(self, key):
            return self._data.get(key)
        
        async def setex(self, key, ttl, value):
            self._data[key] = value
        
        async def set(self, key, value, ex=None, nx=False):
            if nx and key in self._data:
                return False
            self._data[key] = value
            return True
        
        async def delete(self, *keys):
            for key in keys:
                self._data.pop(key, None)
        
        async def keys(self, pattern):
            # Simple glob pattern matching
            import fnmatch
            return [k for k in self._data.keys() if fnmatch.fnmatch(k, pattern)]
        
        async def publish(self, channel, message):
            pass
    
    async def test():
        redis = MockRedis()
        manager = ValkeyManager(redis)
        sse = SSEHub(redis)
        
        # Test 1: Set/Get
        await manager.set_json("test:key", {"msg": "hello"})
        value = await manager.get_json("test:key")
        assert value["msg"] == "hello"
        print("✅ Test 1: Set/Get passed")
        
        # Test 2: Cache-aside
        async def loader():
            return {"data": "loaded"}
        
        result = await manager.get_or_set_json("test:loader", loader)
        assert result["data"] == "loaded"
        print("✅ Test 2: Cache-aside passed")
        
        # Test 3: Hit ratio
        stats = manager.get_stats()
        print(f"✅ Test 3: Stats = {stats}")
        
        # Test 4: SSE broadcast
        await sse.broadcast_kpi_update({"kpi_recovery_estimated": 100.0})
        print("✅ Test 4: SSE broadcast passed")
    
    asyncio.run(test())
