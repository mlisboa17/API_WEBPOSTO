"""
RBAC Service - Role-Based Access Control
Gerenciamento de roles e permissões
"""

from __future__ import annotations

import logging
from typing import Any

from src.services.governance.schemas import UserRole

LOGGER = logging.getLogger(__name__)


# Mapa de permissões por role
ROLE_PERMISSIONS = {
    UserRole.OWNER: {
        # Acesso total
        "modules": "*",
        "actions": "*",
    },
    UserRole.ADMIN: {
        # Quase tudo, exceto deletar tenant
        "modules": "*",
        "actions": ["create", "read", "update", "export", "import"],
        "forbidden": ["delete_tenant"],
    },
    UserRole.MANAGER: {
        # Operações + relatórios
        "modules": [
            "dashboard",
            "financial",
            "operations",
            "reports",
            "analytics",
            "copilot",
        ],
        "actions": ["read", "create", "update", "export"],
    },
    UserRole.FINANCE: {
        # Apenas financeiro
        "modules": [
            "dashboard",
            "financial",
            "accounts_payable",
            "accounts_receivable",
            "cards",
            "reports",
        ],
        "actions": ["read", "create", "update", "export"],
    },
    UserRole.OPERATIONS: {
        # Apenas operacional
        "modules": [
            "dashboard",
            "operations",
            "fuel",
            "inventory",
            "sales",
            "reports",
        ],
        "actions": ["read", "create", "update"],
    },
    UserRole.VIEWER: {
        # Apenas visualização
        "modules": [
            "dashboard",
            "reports",
            "analytics",
        ],
        "actions": ["read"],
    },
}


class RBACService:
    """Serviço de controle de acesso baseado em roles"""
    
    def __init__(self, supabase_client: Any = None):
        """
        Inicializa o serviço
        
        Args:
            supabase_client: Cliente Supabase (opcional)
        """
        self.supabase = supabase_client
    
    async def get_user_role(
        self,
        tenant_id: str,
        user_id: str,
    ) -> UserRole | None:
        """
        Busca role de um usuário
        
        Args:
            tenant_id: ID do tenant
            user_id: ID do usuário
        
        Returns:
            UserRole ou None se não encontrado
        """
        try:
            if not self.supabase:
                # Fallback: assume VIEWER
                return UserRole.VIEWER
            
            response = (
                self.supabase.table("governance.user_roles")
                .select("role")
                .eq("tenant_id", tenant_id)
                .eq("user_id", user_id)
                .eq("is_active", True)
                .single()
                .execute()
            )
            
            if response.data:
                return UserRole(response.data["role"])
            
            return None
        
        except Exception as e:
            LOGGER.error(f"Erro ao buscar role do usuário: {e}")
            return None
    
    async def assign_role(
        self,
        tenant_id: str,
        user_id: str,
        user_email: str,
        role: UserRole,
    ) -> bool:
        """
        Atribui role a um usuário
        
        Args:
            tenant_id: ID do tenant
            user_id: ID do usuário
            user_email: Email do usuário
            role: Role a atribuir
        
        Returns:
            True se sucesso
        """
        try:
            if not self.supabase:
                return False
            
            # Verificar se já existe
            existing = (
                self.supabase.table("governance.user_roles")
                .select("id")
                .eq("tenant_id", tenant_id)
                .eq("user_id", user_id)
                .execute()
            )
            
            data = {
                "tenant_id": tenant_id,
                "user_id": user_id,
                "user_email": user_email,
                "role": role.value,
                "is_active": True,
            }
            
            if existing.data:
                # Atualizar
                self.supabase.table("governance.user_roles").update(data).eq("tenant_id", tenant_id).eq("user_id", user_id).execute()
            else:
                # Inserir
                self.supabase.table("governance.user_roles").insert(data).execute()
            
            LOGGER.info(
                f"Role atribuída: {role.value}",
                extra={
                    "event": "role_assigned",
                    "tenant_id": tenant_id,
                    "user_id": user_id,
                    "role": role.value,
                },
            )
            
            return True
        
        except Exception as e:
            LOGGER.error(f"Erro ao atribuir role: {e}")
            return False
    
    def has_permission(
        self,
        role: UserRole,
        module: str,
        action: str,
    ) -> bool:
        """
        Verifica se role tem permissão para ação em módulo
        
        Args:
            role: Role do usuário
            module: Nome do módulo (ex: "financial")
            action: Ação (ex: "read", "create", "delete")
        
        Returns:
            True se tem permissão
        """
        try:
            permissions = ROLE_PERMISSIONS.get(role, {})
            
            # OWNER tem tudo
            if role == UserRole.OWNER:
                return True
            
            # Verificar módulo
            allowed_modules = permissions.get("modules", [])
            if allowed_modules != "*" and module not in allowed_modules:
                return False
            
            # Verificar ação
            allowed_actions = permissions.get("actions", [])
            if allowed_actions != "*" and action not in allowed_actions:
                return False
            
            # Verificar ações proibidas
            forbidden = permissions.get("forbidden", [])
            if action in forbidden:
                return False
            
            return True
        
        except Exception as e:
            LOGGER.error(f"Erro ao verificar permissão: {e}")
            return False
    
    async def can_user_access(
        self,
        tenant_id: str,
        user_id: str,
        module: str,
        action: str,
    ) -> bool:
        """
        Verifica se usuário pode acessar módulo/ação
        
        Args:
            tenant_id: ID do tenant
            user_id: ID do usuário
            module: Nome do módulo
            action: Ação
        
        Returns:
            True se pode acessar
        """
        role = await self.get_user_role(tenant_id, user_id)
        
        if not role:
            # Sem role = sem acesso
            return False
        
        return self.has_permission(role, module, action)
    
    async def list_user_permissions(
        self,
        tenant_id: str,
        user_id: str,
    ) -> dict[str, Any]:
        """
        Lista todas as permissões de um usuário
        
        Args:
            tenant_id: ID do tenant
            user_id: ID do usuário
        
        Returns:
            Dicionário com permissões
        """
        role = await self.get_user_role(tenant_id, user_id)
        
        if not role:
            return {
                "role": None,
                "permissions": {},
            }
        
        return {
            "role": role.value,
            "permissions": ROLE_PERMISSIONS.get(role, {}),
        }


# Instância global
_rbac_service: RBACService | None = None


def get_rbac_service() -> RBACService:
    """Retorna instância do serviço RBAC"""
    global _rbac_service
    if _rbac_service is None:
        _rbac_service = RBACService()
    return _rbac_service
