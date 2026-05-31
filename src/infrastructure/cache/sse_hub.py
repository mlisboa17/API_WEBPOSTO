"""
🌊 SSE HUB - Real-time Streaming Backend
Integra Valkey state + SSE events para atualizar UI em tempo real

Responsabilidades:
1. Gerenciar canais SSE para diferentes tipos de dados
2. Broadcast events com persistência em Valkey
3. Cleanup automático de sessões expiradas
"""
from typing import AsyncGenerator, Dict, Any, Optional, Callable
from datetime import datetime
import json
import logging
import asyncio

logger = logging.getLogger(__name__)


class StreamedEvent:
    """Model: Evento SSE estruturado"""
    
    def __init__(
        self,
        event_type: str,
        data: Dict[str, Any],
        channel: str = "default",
    ):
        self.event_type = event_type
        self.data = data
        self.channel = channel
        self.timestamp = datetime.utcnow()
    
    def to_sse_format(self) -> str:
        """Serializa para formato SSE (Server-Sent Events)"""
        return f"data: {json.dumps(self.model_dump(), default=str)}\n\n"
    
    def model_dump(self) -> Dict:
        return {
            "event": self.event_type,
            "timestamp": self.timestamp.isoformat(),
            "channel": self.channel,
            **self.data,
        }


class SSEStream:
    """Gerenciador de stream SSE individual (por cliente)"""
    
    def __init__(
        self,
        stream_id: str,
        channels: list,
        valkey_manager,
    ):
        self.stream_id = stream_id
        self.channels = channels  # Canais inscritos
        self.valkey = valkey_manager
        self.created_at = datetime.utcnow()
        self.events_sent = 0
    
    async def subscribe_to_events(self) -> AsyncGenerator[str, None]:
        """
        Stream infinito de eventos SSE
        
        Yields:
            strings em formato SSE (data: {...}\\n\\n)
        """
        # Recuperar eventos pendentes do Valkey (fila de eventos)
        pending_events = await self.valkey.get_json(
            f"sse:pending:{self.stream_id}"
        )
        
        if pending_events:
            for event_data in pending_events:
                event = StreamedEvent(**event_data)
                yield event.to_sse_format()
                self.events_sent += 1
            
            # Limpar fila
            await self.valkey.delete(f"sse:pending:{self.stream_id}")
        
        # Hearbeat para manter conexão viva
        while True:
            try:
                yield ": heartbeat\n\n"
                await asyncio.sleep(30)  # Enviar heartbeat a cada 30s
            except GeneratorExit:
                break
    
    async def close(self):
        """Encerrar stream e garbage collect"""
        await self.valkey.delete(f"sse:stream:{self.stream_id}")
        logger.info(f"🔌 SSE stream {self.stream_id} closed ({self.events_sent} events sent)")


class SSEHubV2:
    """
    🌊 HUB SSE VERSÃO 2 - Production Grade
    Integrado com Valkey para distribuição, persistência e replay
    """
    
    def __init__(self, valkey_manager):
        """
        Args:
            valkey_manager: ValkeyManager (cache/pubsub)
        """
        self.valkey = valkey_manager
        self.active_streams: Dict[str, SSEStream] = {}
        self.listeners: Dict[str, list] = {}  # {channel -> [callbacks]}
    
    # ─────────────────────────────────────────────────────────
    # CLIENT MANAGEMENT
    # ─────────────────────────────────────────────────────────
    
    async def create_stream(
        self,
        stream_id: str,
        channels: list = None,
    ) -> SSEStream:
        """
        Criar novo stream SSE para cliente
        
        Args:
            stream_id: ID único (ex: "stream-director-001")
            channels: Canais inscritos (ex: ["kpi-update", "audit-finding"])
        
        Returns:
            SSEStream gerenciado
        """
        if channels is None:
            channels = ["kpi-update", "audit-finding", "module-sync"]
        
        stream = SSEStream(stream_id, channels, self.valkey)
        self.active_streams[stream_id] = stream
        
        # Persist stream metadata
        await self.valkey.set_json(
            f"sse:stream:{stream_id}",
            {
                "stream_id": stream_id,
                "channels": channels,
                "created_at": datetime.utcnow().isoformat(),
            },
            ttl=86400,
        )
        
        logger.info(f"📡 SSE stream created: {stream_id} (channels: {channels})")
        return stream
    
    async def close_stream(self, stream_id: str):
        """Encerrar stream"""
        if stream_id in self.active_streams:
            await self.active_streams[stream_id].close()
            del self.active_streams[stream_id]
    
    # ─────────────────────────────────────────────────────────
    # EVENT BROADCASTING
    # ─────────────────────────────────────────────────────────
    
    async def broadcast_event(
        self,
        event_type: str,
        data: Dict[str, Any],
        channel: str = "default",
        persist: bool = True,
    ):
        """
        Broadcast evento para todos streams do channel
        
        Args:
            event_type: ex "kpi-update", "audit-finding"
            data: Payload do evento
            channel: Canal de destino
            persist: Salvar em Valkey para replay/audit
        """
        event = StreamedEvent(event_type, data, channel)
        
        # ─ Persistir em Valkey para audit/replay
        if persist:
            await self.valkey.set_json(
                f"sse:event:{channel}:{event.timestamp.timestamp()}",
                event.model_dump(),
                ttl=604800,  # Keep 7 dias
            )
        
        # ─ Enviar para streams inscritos
        for stream_id, stream in self.active_streams.items():
            if channel in stream.channels or "default" in stream.channels:
                # Enfileirar evento no Valkey para entrega
                pending = await self.valkey.get_json(f"sse:pending:{stream_id}") or []
                pending.append(event.model_dump())
                await self.valkey.set_json(
                    f"sse:pending:{stream_id}",
                    pending,
                    ttl=3600,
                )
        
        # ─ Chamar callbacks locais (in-memory)
        if channel in self.listeners:
            for callback in self.listeners[channel]:
                try:
                    await callback(event)
                except Exception as e:
                    logger.error(f"❌ SSE listener error: {e}")
    
    # ─────────────────────────────────────────────────────────
    # CONVENIENT BROADCAST METHODS
    # ─────────────────────────────────────────────────────────
    
    async def broadcast_kpi_update(self, kpis: Dict[str, Any]):
        """Broadcast KPI update para home"""
        await self.broadcast_event(
            "kpi-update",
            kpis,
            channel="kpi-updates",
        )
    
    async def broadcast_audit_finding(
        self,
        sku: str,
        severity: str,
        recovery: float,
        message: str,
    ):
        """Broadcast quando novo finding detectado"""
        await self.broadcast_event(
            "audit-finding",
            {
                "sku": sku,
                "severity": severity,
                "recoverable_credit": recovery,
                "message": message,
            },
            channel="audit-updates",
        )
    
    async def broadcast_module_sync_start(self, module: str):
        """Módulo iniciou sincronização"""
        await self.broadcast_event(
            "module-sync",
            {"module": module, "status": "starting"},
            channel="module-sync",
        )
    
    async def broadcast_module_sync_progress(
        self,
        module: str,
        progress_pct: int,
        items_processed: int,
    ):
        """Atualização de progresso de sincronização"""
        await self.broadcast_event(
            "module-sync",
            {
                "module": module,
                "status": "progress",
                "progress_pct": progress_pct,
                "items_processed": items_processed,
            },
            channel="module-sync",
        )
    
    async def broadcast_module_sync_complete(
        self,
        module: str,
        total_items: int,
        summary: Dict,
    ):
        """Módulo completou sincronização"""
        await self.broadcast_event(
            "module-sync",
            {
                "module": module,
                "status": "completed",
                "total_items": total_items,
                "summary": summary,
            },
            channel="module-sync",
        )
    
    # ─────────────────────────────────────────────────────────
    # SUBSCRIPTION (LOCAL CALLBACKS)
    # ─────────────────────────────────────────────────────────
    
    def subscribe(self, channel: str, callback: Callable):
        """Registrar callback para eventos de um channel"""
        if channel not in self.listeners:
            self.listeners[channel] = []
        self.listeners[channel].append(callback)
        logger.debug(f"📡 Subscribed to channel: {channel}")
    
    # ─────────────────────────────────────────────────────────
    # MONITORING & CLEANUP
    # ─────────────────────────────────────────────────────────
    
    def get_active_streams_count(self) -> int:
        """Total de streams ativos"""
        return len(self.active_streams)
    
    async def cleanup_expired_streams(self):
        """Garbage collection: remover streams expirados"""
        expired = []
        for stream_id, stream in self.active_streams.items():
            age = (datetime.utcnow() - stream.created_at).total_seconds()
            if age > 86400:  # 24h
                expired.append(stream_id)
        
        for stream_id in expired:
            await self.close_stream(stream_id)
        
        if expired:
            logger.info(f"🗑️ Cleaned up {len(expired)} expired streams")
        
        return len(expired)
    
    async def cleanup_expired_events(self):
        """Garbage collection: remover eventos expirados"""
        return await self.valkey.invalidate_pattern("sse:event:*")


# ═══════════════════════════════════════════════════════════════════
# 🔗 INTEGRATION: FastAPI Route Example
# ═══════════════════════════════════════════════════════════════════

"""
EXEMPLO DE INTEGRAÇÃO EM MAIN.PY:

from fastapi import FastAPI
from fastapi.responses import StreamingResponse
import uuid

app = FastAPI()

# Instanciar SSE hub com Valkey
sse_hub = SSEHubV2(valkey_manager)

@app.get("/api/stream/kpi-updates/{director_id}")
async def stream_kpi_updates(director_id: str):
    '''Stream SSE de atualizações de KPI'''
    
    stream_id = f"stream-{director_id}-{uuid.uuid4()}"
    stream = await sse_hub.create_stream(
        stream_id,
        channels=["kpi-updates", "module-sync"],
    )
    
    try:
        return StreamingResponse(
            stream.subscribe_to_events(),
            media_type="text/event-stream",
        )
    finally:
        await sse_hub.close_stream(stream_id)

@app.post("/api/audit/trigger/{station_cnpj}")
async def trigger_audit(station_cnpj: str):
    '''Dispara auditoria e broadcast via SSE'''
    
    # 1. Iniciar auditoria em background
    await sse_hub.broadcast_module_sync_start("tax")
    
    # 2. Simular progresso (em produção, seria async job)
    for i in range(1, 26):
        await sse_hub.broadcast_module_sync_progress(
            module="tax",
            progress_pct=(i / 25) * 100,
            items_processed=i,
        )
        await asyncio.sleep(0.5)
    
    # 3. Completar com summary
    await sse_hub.broadcast_module_sync_complete(
        module="tax",
        total_items=25,
        summary={
            "total_recovery": 93.48,
            "risk_score": 81,
            "findings": 25,
        },
    )
    
    return {"status": "audit_started"}
"""

# ═══════════════════════════════════════════════════════════════════
# 🧪 TESTES
# ═══════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    import asyncio
    from src.infrastructure.cache.valkey_manager import ValkeyManager, MockRedis
    
    async def test_sse_hub():
        redis = MockRedis()
        valkey = ValkeyManager(redis)
        hub = SSEHubV2(valkey)
        
        # Test 1: Create stream
        stream = await hub.create_stream("stream-test-001", ["kpi-updates"])
        assert stream.stream_id == "stream-test-001"
        print("✅ Test 1: Create stream passed")
        
        # Test 2: Broadcast KPI
        await hub.broadcast_kpi_update({
            "kpi_recovery_estimated": 123.45,
            "kpi_risk_score": 75,
        })
        print("✅ Test 2: Broadcast KPI passed")
        
        # Test 3: Active streams count
        assert hub.get_active_streams_count() == 1
        print("✅ Test 3: Active streams count = 1")
        
        # Test 4: Close stream
        await hub.close_stream("stream-test-001")
        assert hub.get_active_streams_count() == 0
        print("✅ Test 4: Close stream passed")
    
    asyncio.run(test_sse_hub())
