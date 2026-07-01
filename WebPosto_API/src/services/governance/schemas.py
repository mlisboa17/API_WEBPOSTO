"""
Governance Schemas
Define estruturas de dados para governança e auditoria
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from enum import Enum
from typing import Any


# ============================================================================
# ENUMS
# ============================================================================

class AuditAction(str, Enum):
    """Ações auditáveis"""
    # Autenticação
    LOGIN = "LOGIN"
    LOGOUT = "LOGOUT"
    LOGIN_FAILED = "LOGIN_FAILED"
    
    # CRUD
    CREATE = "CREATE"
    READ = "READ"
    UPDATE = "UPDATE"
    DELETE = "DELETE"
    
    # Operações especiais
    EXPORT = "EXPORT"
    IMPORT = "IMPORT"
    BULK_UPDATE = "BULK_UPDATE"
    BULK_DELETE = "BULK_DELETE"
    
    # ETL
    ETL_START = "ETL_START"
    ETL_SUCCESS = "ETL_SUCCESS"
    ETL_FAILURE = "ETL_FAILURE"
    
    # Configuração
    CONFIG_CHANGE = "CONFIG_CHANGE"
    PERMISSION_CHANGE = "PERMISSION_CHANGE"
    
    # Onboarding
    TENANT_ONBOARD = "TENANT_ONBOARD"
    TENANT_OFFBOARD = "TENANT_OFFBOARD"
    
    # Relatórios
    REPORT_GENERATED = "REPORT_GENERATED"
    ALERT_SENT = "ALERT_SENT"


class AuditStatus(str, Enum):
    """Status de ação auditada"""
    SUCCESS = "SUCCESS"
    FAILURE = "FAILURE"
    PENDING = "PENDING"


class ApprovalStatus(str, Enum):
    """Status de aprovação"""
    PENDING = "PENDING"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"
    EXECUTED = "EXECUTED"
    EXPIRED = "EXPIRED"


class SecuritySeverity(str, Enum):
    """Severidade de evento de segurança"""
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


class UserRole(str, Enum):
    """Roles de usuário (RBAC)"""
    OWNER = "OWNER"          # Dono do tenant, acesso total
    ADMIN = "ADMIN"          # Administrador, quase tudo
    MANAGER = "MANAGER"      # Gerente, operações + relatórios
    FINANCE = "FINANCE"      # Financeiro, apenas módulos financeiros
    OPERATIONS = "OPERATIONS"  # Operações, apenas operacional
    VIEWER = "VIEWER"        # Visualizador, apenas leitura


# ============================================================================
# AUDIT LOG
# ============================================================================

@dataclass(frozen=True)
class AuditLogEntry:
    """Entrada de audit log"""
    
    # Identificação
    tenant_id: str
    user_id: str | None
    user_email: str | None
    
    # Ação
    action: AuditAction
    entity_type: str | None
    entity_id: str | None
    
    # Contexto
    description: str | None
    metadata: dict[str, Any]
    
    # Request
    ip_address: str | None
    user_agent: str | None
    request_method: str | None
    request_path: str | None
    
    # Resultado
    status: AuditStatus
    error_message: str | None
    
    # Timestamp
    created_at: datetime
    
    def to_dict(self) -> dict[str, Any]:
        """Converte para dicionário"""
        return {
            "tenant_id": self.tenant_id,
            "user_id": self.user_id,
            "user_email": self.user_email,
            "action": self.action.value,
            "entity_type": self.entity_type,
            "entity_id": self.entity_id,
            "description": self.description,
            "metadata": self.metadata,
            "ip_address": self.ip_address,
            "user_agent": self.user_agent,
            "request_method": self.request_method,
            "request_path": self.request_path,
            "status": self.status.value,
            "error_message": self.error_message,
            "created_at": self.created_at.isoformat(),
        }


# ============================================================================
# APPROVAL REQUEST
# ============================================================================

@dataclass(frozen=True)
class ApprovalRequest:
    """Solicitação de aprovação"""
    
    request_id: str
    tenant_id: str
    
    # Solicitante
    requester_user_id: str
    requester_email: str
    
    # Ação
    action_type: str
    entity_type: str | None
    entity_id: str | None
    action_description: str
    action_payload: dict[str, Any]
    
    # Aprovação
    status: ApprovalStatus
    approver_user_id: str | None
    approver_email: str | None
    approval_comment: str | None
    approved_at: datetime | None
    
    # Execução
    executed_at: datetime | None
    execution_result: dict[str, Any] | None
    execution_error: str | None
    
    # Timestamps
    created_at: datetime
    updated_at: datetime
    expires_at: datetime
    
    def to_dict(self) -> dict[str, Any]:
        """Converte para dicionário"""
        return {
            "request_id": self.request_id,
            "tenant_id": self.tenant_id,
            "requester_user_id": self.requester_user_id,
            "requester_email": self.requester_email,
            "action_type": self.action_type,
            "entity_type": self.entity_type,
            "entity_id": self.entity_id,
            "action_description": self.action_description,
            "action_payload": self.action_payload,
            "status": self.status.value,
            "approver_user_id": self.approver_user_id,
            "approver_email": self.approver_email,
            "approval_comment": self.approval_comment,
            "approved_at": self.approved_at.isoformat() if self.approved_at else None,
            "executed_at": self.executed_at.isoformat() if self.executed_at else None,
            "execution_result": self.execution_result,
            "execution_error": self.execution_error,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
            "expires_at": self.expires_at.isoformat(),
        }


# ============================================================================
# SECURITY EVENT
# ============================================================================

@dataclass(frozen=True)
class SecurityEvent:
    """Evento de segurança"""
    
    tenant_id: str | None
    user_id: str | None
    user_email: str | None
    
    event_type: str
    severity: SecuritySeverity
    description: str
    metadata: dict[str, Any]
    
    ip_address: str | None
    user_agent: str | None
    action_taken: str | None
    
    created_at: datetime
    
    def to_dict(self) -> dict[str, Any]:
        """Converte para dicionário"""
        return {
            "tenant_id": self.tenant_id,
            "user_id": self.user_id,
            "user_email": self.user_email,
            "event_type": self.event_type,
            "severity": self.severity.value,
            "description": self.description,
            "metadata": self.metadata,
            "ip_address": self.ip_address,
            "user_agent": self.user_agent,
            "action_taken": self.action_taken,
            "created_at": self.created_at.isoformat(),
        }


# ============================================================================
# COPILOT AUDIT
# ============================================================================

@dataclass(frozen=True)
class CopilotAuditEntry:
    """Entrada de auditoria do Copilot"""
    
    tenant_id: str
    user_id: str
    user_email: str | None
    session_id: str | None
    
    question: str
    response: str | None
    
    context_used: dict[str, Any] | None
    model_used: str | None
    tokens_prompt: int | None
    tokens_completion: int | None
    tokens_total: int | None
    estimated_cost_usd: Decimal | None
    
    response_time_ms: int | None
    
    user_feedback: str | None
    user_rating: int | None
    
    created_at: datetime
    
    def to_dict(self) -> dict[str, Any]:
        """Converte para dicionário"""
        return {
            "tenant_id": self.tenant_id,
            "user_id": self.user_id,
            "user_email": self.user_email,
            "session_id": self.session_id,
            "question": self.question,
            "response": self.response,
            "context_used": self.context_used,
            "model_used": self.model_used,
            "tokens_prompt": self.tokens_prompt,
            "tokens_completion": self.tokens_completion,
            "tokens_total": self.tokens_total,
            "estimated_cost_usd": str(self.estimated_cost_usd) if self.estimated_cost_usd else None,
            "response_time_ms": self.response_time_ms,
            "user_feedback": self.user_feedback,
            "user_rating": self.user_rating,
            "created_at": self.created_at.isoformat(),
        }


# ============================================================================
# USER ROLE
# ============================================================================

@dataclass(frozen=True)
class UserRoleAssignment:
    """Atribuição de role a usuário"""
    
    tenant_id: str
    user_id: str
    user_email: str
    role: UserRole
    custom_permissions: list[str]
    is_active: bool
    created_at: datetime
    updated_at: datetime
    
    def to_dict(self) -> dict[str, Any]:
        """Converte para dicionário"""
        return {
            "tenant_id": self.tenant_id,
            "user_id": self.user_id,
            "user_email": self.user_email,
            "role": self.role.value,
            "custom_permissions": self.custom_permissions,
            "is_active": self.is_active,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
        }
