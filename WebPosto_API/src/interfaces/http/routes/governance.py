"""
Governance API Routes
Rotas FastAPI para governança, auditoria e controle de acesso
"""

from __future__ import annotations

from datetime import datetime
from fastapi import APIRouter, Query
from fastapi.responses import JSONResponse

from src.services.governance import (
    AuditAction,
    AuditStatus,
    UserRole,
    get_audit_service,
    get_rbac_service,
)

router = APIRouter(prefix="/v1/governance", tags=["Governance"])


# ============================================================================
# AUDIT LOG
# ============================================================================

@router.get("/audit-log")
async def get_audit_logs(
    tenant: str = Query(..., description="Tenant ID"),
    limit: int = Query(100, description="Limite de resultados", ge=1, le=500),
    action: str | None = Query(None, description="Filtrar por ação"),
    user_id: str | None = Query(None, description="Filtrar por usuário"),
) -> JSONResponse:
    """
    Busca registros de auditoria
    
    Retorna logs de todas as ações auditadas no sistema.
    """
    try:
        audit_service = get_audit_service()
        
        action_enum = AuditAction(action) if action else None
        
        logs = await audit_service.get_recent_logs(
            tenant_id=tenant,
            limit=limit,
            action=action_enum,
            user_id=user_id,
        )
        
        return JSONResponse(
            content={
                "success": True,
                "tenant": tenant,
                "count": len(logs),
                "logs": logs,
            },
            status_code=200,
        )
    
    except Exception as e:
        return JSONResponse(
            content={
                "success": False,
                "error": {
                    "type": "AUDIT_LOG_ERROR",
                    "message": str(e)[:200],
                },
            },
            status_code=500,
        )


@router.get("/audit-log/stats")
async def get_audit_stats(
    tenant: str = Query(..., description="Tenant ID"),
    days: int = Query(30, description="Número de dias", ge=1, le=90),
) -> JSONResponse:
    """
    Estatísticas de auditoria
    
    Retorna métricas agregadas dos logs de auditoria.
    """
    try:
        audit_service = get_audit_service()
        
        stats = await audit_service.get_stats(tenant_id=tenant, days=days)
        
        return JSONResponse(
            content={
                "success": True,
                "tenant": tenant,
                "period_days": days,
                "stats": stats,
            },
            status_code=200,
        )
    
    except Exception as e:
        return JSONResponse(
            content={
                "success": False,
                "error": {
                    "type": "AUDIT_STATS_ERROR",
                    "message": str(e)[:200],
                },
            },
            status_code=500,
        )


# ============================================================================
# RBAC
# ============================================================================

@router.get("/rbac/user-role")
async def get_user_role(
    tenant: str = Query(..., description="Tenant ID"),
    user_id: str = Query(..., description="User ID"),
) -> JSONResponse:
    """
    Busca role de um usuário
    
    Retorna a role atribuída ao usuário no tenant.
    """
    try:
        rbac_service = get_rbac_service()
        
        role = await rbac_service.get_user_role(tenant_id=tenant, user_id=user_id)
        
        if not role:
            return JSONResponse(
                content={
                    "success": False,
                    "error": {
                        "type": "ROLE_NOT_FOUND",
                        "message": "Usuário não possui role atribuída",
                    },
                },
                status_code=404,
            )
        
        return JSONResponse(
            content={
                "success": True,
                "tenant": tenant,
                "user_id": user_id,
                "role": role.value,
            },
            status_code=200,
        )
    
    except Exception as e:
        return JSONResponse(
            content={
                "success": False,
                "error": {
                    "type": "RBAC_ERROR",
                    "message": str(e)[:200],
                },
            },
            status_code=500,
        )


@router.get("/rbac/user-permissions")
async def get_user_permissions(
    tenant: str = Query(..., description="Tenant ID"),
    user_id: str = Query(..., description="User ID"),
) -> JSONResponse:
    """
    Lista permissões de um usuário
    
    Retorna todas as permissões baseadas na role do usuário.
    """
    try:
        rbac_service = get_rbac_service()
        
        permissions = await rbac_service.list_user_permissions(
            tenant_id=tenant,
            user_id=user_id,
        )
        
        return JSONResponse(
            content={
                "success": True,
                "tenant": tenant,
                "user_id": user_id,
                **permissions,
            },
            status_code=200,
        )
    
    except Exception as e:
        return JSONResponse(
            content={
                "success": False,
                "error": {
                    "type": "PERMISSIONS_ERROR",
                    "message": str(e)[:200],
                },
            },
            status_code=500,
        )


@router.post("/rbac/assign-role")
async def assign_role(
    tenant: str = Query(..., description="Tenant ID"),
    user_id: str = Query(..., description="User ID"),
    user_email: str = Query(..., description="User email"),
    role: str = Query(..., description="Role (OWNER, ADMIN, MANAGER, FINANCE, OPERATIONS, VIEWER)"),
) -> JSONResponse:
    """
    Atribui role a um usuário
    
    Atribui ou atualiza a role de um usuário no tenant.
    """
    try:
        # Validar role
        try:
            role_enum = UserRole(role.upper())
        except ValueError:
            return JSONResponse(
                content={
                    "success": False,
                    "error": {
                        "type": "INVALID_ROLE",
                        "message": f"Role inválida: {role}. Use: OWNER, ADMIN, MANAGER, FINANCE, OPERATIONS, VIEWER",
                    },
                },
                status_code=400,
            )
        
        rbac_service = get_rbac_service()
        
        success = await rbac_service.assign_role(
            tenant_id=tenant,
            user_id=user_id,
            user_email=user_email,
            role=role_enum,
        )
        
        if not success:
            return JSONResponse(
                content={
                    "success": False,
                    "error": {
                        "type": "ROLE_ASSIGNMENT_FAILED",
                        "message": "Falha ao atribuir role",
                    },
                },
                status_code=500,
            )
        
        return JSONResponse(
            content={
                "success": True,
                "tenant": tenant,
                "user_id": user_id,
                "role": role_enum.value,
                "message": f"Role {role_enum.value} atribuída com sucesso",
            },
            status_code=200,
        )
    
    except Exception as e:
        return JSONResponse(
            content={
                "success": False,
                "error": {
                    "type": "ROLE_ASSIGNMENT_ERROR",
                    "message": str(e)[:200],
                },
            },
            status_code=500,
        )


@router.get("/rbac/check-permission")
async def check_permission(
    tenant: str = Query(..., description="Tenant ID"),
    user_id: str = Query(..., description="User ID"),
    module: str = Query(..., description="Módulo (ex: financial, operations)"),
    action: str = Query(..., description="Ação (ex: read, create, update, delete)"),
) -> JSONResponse:
    """
    Verifica se usuário tem permissão
    
    Verifica se o usuário pode executar uma ação em um módulo.
    """
    try:
        rbac_service = get_rbac_service()
        
        has_access = await rbac_service.can_user_access(
            tenant_id=tenant,
            user_id=user_id,
            module=module,
            action=action,
        )
        
        return JSONResponse(
            content={
                "success": True,
                "tenant": tenant,
                "user_id": user_id,
                "module": module,
                "action": action,
                "has_permission": has_access,
            },
            status_code=200,
        )
    
    except Exception as e:
        return JSONResponse(
            content={
                "success": False,
                "error": {
                    "type": "PERMISSION_CHECK_ERROR",
                    "message": str(e)[:200],
                },
            },
            status_code=500,
        )


# ============================================================================
# SECURITY EVENTS
# ============================================================================

@router.get("/security/events")
async def get_security_events(
    tenant: str = Query(..., description="Tenant ID"),
    limit: int = Query(50, description="Limite de resultados", ge=1, le=200),
    severity: str | None = Query(None, description="Filtrar por severidade (LOW, MEDIUM, HIGH, CRITICAL)"),
) -> JSONResponse:
    """
    Busca eventos de segurança
    
    Retorna eventos de segurança (falhas de login, acessos suspeitos, etc).
    """
    try:
        # TODO: Implementar service de security events
        # Por ora, estrutura básica
        return JSONResponse(
            content={
                "success": True,
                "tenant": tenant,
                "count": 0,
                "events": [],
                "message": "Security events - em implementação",
            },
            status_code=200,
        )
    
    except Exception as e:
        return JSONResponse(
            content={
                "success": False,
                "error": {
                    "type": "SECURITY_EVENTS_ERROR",
                    "message": str(e)[:200],
                },
            },
            status_code=500,
        )


# ============================================================================
# GOVERNANCE DASHBOARD
# ============================================================================

@router.get("/dashboard")
async def get_governance_dashboard(
    tenant: str = Query(..., description="Tenant ID"),
) -> JSONResponse:
    """
    Dashboard de Governança
    
    Retorna KPIs e métricas de governança do tenant.
    """
    try:
        audit_service = get_audit_service()
        
        # Buscar estatísticas
        audit_stats = await audit_service.get_stats(tenant_id=tenant, days=30)
        
        # TODO: Buscar outras métricas (approvals, security events, etc)
        
        return JSONResponse(
            content={
                "success": True,
                "tenant": tenant,
                "kpis": {
                    "total_audit_events": audit_stats.get("total_events", 0),
                    "active_users": audit_stats.get("unique_users", 0),
                    "pending_approvals": 0,  # TODO
                    "security_events": 0,    # TODO
                    "copilot_queries": 0,    # TODO
                },
                "audit": audit_stats,
            },
            status_code=200,
        )
    
    except Exception as e:
        return JSONResponse(
            content={
                "success": False,
                "error": {
                    "type": "DASHBOARD_ERROR",
                    "message": str(e)[:200],
                },
            },
            status_code=500,
        )
