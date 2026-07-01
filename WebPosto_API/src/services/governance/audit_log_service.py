"""
Audit Log Service
Serviço para registro de auditoria de ações
"""

from __future__ import annotations

from datetime import datetime
import logging
from typing import Any

from src.services.governance.schemas import (
    AuditAction,
    AuditLogEntry,
    AuditStatus,
)

LOGGER = logging.getLogger(__name__)


class AuditLogService:
    """Serviço de Audit Log"""
    
    def __init__(self, supabase_client: Any = None):
        """
        Inicializa o serviço
        
        Args:
            supabase_client: Cliente Supabase (opcional)
        """
        self.supabase = supabase_client
    
    async def log(
        self,
        *,
        tenant_id: str,
        action: AuditAction | str,
        status: AuditStatus | str = AuditStatus.SUCCESS,
        user_id: str | None = None,
        user_email: str | None = None,
        entity_type: str | None = None,
        entity_id: str | None = None,
        description: str | None = None,
        metadata: dict[str, Any] | None = None,
        ip_address: str | None = None,
        user_agent: str | None = None,
        request_method: str | None = None,
        request_path: str | None = None,
        error_message: str | None = None,
    ) -> AuditLogEntry | None:
        """
        Registra uma ação no audit log
        
        Args:
            tenant_id: ID do tenant
            action: Ação realizada
            status: Status da ação
            user_id: ID do usuário (opcional)
            user_email: Email do usuário (opcional)
            entity_type: Tipo de entidade (opcional)
            entity_id: ID da entidade (opcional)
            description: Descrição (opcional)
            metadata: Metadados adicionais (opcional)
            ip_address: IP do request (opcional)
            user_agent: User agent (opcional)
            request_method: Método HTTP (opcional)
            request_path: Path do request (opcional)
            error_message: Mensagem de erro (opcional)
        
        Returns:
            AuditLogEntry criado ou None se falhar
        """
        try:
            # Converter strings para enums
            if isinstance(action, str):
                action = AuditAction(action)
            if isinstance(status, str):
                status = AuditStatus(status)
            
            # Criar entry
            entry = AuditLogEntry(
                tenant_id=tenant_id,
                user_id=user_id,
                user_email=user_email,
                action=action,
                entity_type=entity_type,
                entity_id=entity_id,
                description=description,
                metadata=metadata or {},
                ip_address=ip_address,
                user_agent=user_agent,
                request_method=request_method,
                request_path=request_path,
                status=status,
                error_message=error_message,
                created_at=datetime.now(),
            )
            
            # Salvar no banco (se tiver cliente)
            if self.supabase:
                await self._save_to_db(entry)
            
            # Logar estruturado
            LOGGER.info(
                "audit_log",
                extra={
                    "event": "audit_log_created",
                    "tenant_id": tenant_id,
                    "action": action.value,
                    "status": status.value,
                    "user_id": user_id,
                    "entity_type": entity_type,
                    "entity_id": entity_id,
                },
            )
            
            return entry
        
        except Exception as e:
            LOGGER.error(
                f"Erro ao criar audit log: {e}",
                extra={
                    "event": "audit_log_error",
                    "tenant_id": tenant_id,
                    "error": str(e),
                },
            )
            return None
    
    async def _save_to_db(self, entry: AuditLogEntry) -> None:
        """Salva entry no banco de dados"""
        try:
            if not self.supabase:
                return
            
            # Converter para dict
            data = {
                "tenant_id": entry.tenant_id,
                "user_id": entry.user_id,
                "user_email": entry.user_email,
                "action": entry.action.value,
                "entity_type": entry.entity_type,
                "entity_id": entry.entity_id,
                "description": entry.description,
                "metadata": entry.metadata,
                "ip_address": entry.ip_address,
                "user_agent": entry.user_agent,
                "request_method": entry.request_method,
                "request_path": entry.request_path,
                "status": entry.status.value,
                "error_message": entry.error_message,
                "created_at": entry.created_at.isoformat(),
            }
            
            # Inserir
            self.supabase.table("governance.audit_log").insert(data).execute()
        
        except Exception as e:
            LOGGER.error(f"Erro ao salvar audit log no DB: {e}")
    
    async def get_recent_logs(
        self,
        tenant_id: str,
        limit: int = 100,
        action: AuditAction | None = None,
        user_id: str | None = None,
    ) -> list[dict[str, Any]]:
        """
        Busca logs recentes
        
        Args:
            tenant_id: ID do tenant
            limit: Limite de resultados
            action: Filtrar por ação (opcional)
            user_id: Filtrar por usuário (opcional)
        
        Returns:
            Lista de logs
        """
        try:
            if not self.supabase:
                return []
            
            # Construir query
            query = (
                self.supabase.table("governance.audit_log")
                .select("*")
                .eq("tenant_id", tenant_id)
                .order("created_at", desc=True)
                .limit(limit)
            )
            
            if action:
                query = query.eq("action", action.value)
            
            if user_id:
                query = query.eq("user_id", user_id)
            
            # Executar
            response = query.execute()
            return response.data if response.data else []
        
        except Exception as e:
            LOGGER.error(f"Erro ao buscar logs: {e}")
            return []
    
    async def get_stats(
        self,
        tenant_id: str,
        days: int = 30,
    ) -> dict[str, Any]:
        """
        Estatísticas de auditoria
        
        Args:
            tenant_id: ID do tenant
            days: Número de dias para análise
        
        Returns:
            Estatísticas
        """
        try:
            if not self.supabase:
                return {
                    "total_events": 0,
                    "success_count": 0,
                    "failure_count": 0,
                    "unique_users": 0,
                    "top_actions": [],
                }
            
            # TODO: Implementar queries de estatísticas
            # Por ora, estrutura básica
            return {
                "total_events": 0,
                "success_count": 0,
                "failure_count": 0,
                "unique_users": 0,
                "top_actions": [],
            }
        
        except Exception as e:
            LOGGER.error(f"Erro ao obter estatísticas: {e}")
            return {}


# Instância global (singleton)
_audit_service: AuditLogService | None = None


def get_audit_service() -> AuditLogService:
    """Retorna instância do serviço de auditoria"""
    global _audit_service
    if _audit_service is None:
        _audit_service = AuditLogService()
    return _audit_service


async def audit_log(
    tenant_id: str,
    action: AuditAction | str,
    **kwargs: Any,
) -> None:
    """
    Atalho para registrar auditoria
    
    Args:
        tenant_id: ID do tenant
        action: Ação realizada
        **kwargs: Demais parâmetros do log
    """
    service = get_audit_service()
    await service.log(tenant_id=tenant_id, action=action, **kwargs)
