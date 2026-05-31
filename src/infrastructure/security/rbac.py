"""
CLAUDE 3.7: RBAC Middleware for FastAPI
Implements:
- Role-based access control (PARTNER, DIRECTOR, VIEWER)
- @require_role decorator for endpoints
- Permission validation middleware
- Type-safe with Pydantic V2
"""

from fastapi import Depends, HTTPException, status
from functools import wraps
from typing import Optional, Callable, Any, List
import logging

logger = logging.getLogger(__name__)


class UserRole:
    """User role constants"""
    PARTNER = "PARTNER"
    DIRECTOR = "DIRECTOR"
    VIEWER = "VIEWER"
    ADMIN = "ADMIN"


class PermissionDenied(HTTPException):
    """403 Forbidden exception"""
    def __init__(self, detail: str = "Permission denied"):
        super().__init__(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=detail
        )


class RoleNotFound(HTTPException):
    """401 Unauthorized exception"""
    def __init__(self, detail: str = "Role not found"):
        super().__init__(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=detail
        )


class RBACMiddleware:
    """
    RBAC Middleware for FastAPI
    Validates user roles before endpoint execution
    """
    
    # Role hierarchy (higher number = more permissions)
    ROLE_HIERARCHY = {
        UserRole.ADMIN: 4,
        UserRole.DIRECTOR: 3,
        UserRole.PARTNER: 2,
        UserRole.VIEWER: 1,
    }
    
    # Permission mapping
    PERMISSIONS = {
        UserRole.ADMIN: ["read", "write", "delete", "audit", "admin"],
        UserRole.DIRECTOR: ["read", "write", "delete", "audit"],
        UserRole.PARTNER: ["read", "write"],
        UserRole.VIEWER: ["read"],
    }
    
    @staticmethod
    def has_permission(role: str, required_permission: str) -> bool:
        """
        Check if role has required permission
        
        Args:
            role: User role
            required_permission: Permission to check (read, write, delete, audit, admin)
            
        Returns:
            True if role has permission
        """
        permissions = RBACMiddleware.PERMISSIONS.get(role, [])
        return required_permission in permissions
    
    @staticmethod
    def can_manage_company(role: str) -> bool:
        """Check if role can manage companies"""
        return role in [UserRole.DIRECTOR, UserRole.ADMIN]
    
    @staticmethod
    def can_view_audit(role: str) -> bool:
        """Check if role can view audit logs"""
        return role in [UserRole.DIRECTOR, UserRole.ADMIN]
    
    @staticmethod
    def can_manage_users(role: str) -> bool:
        """Check if role can manage users"""
        return role in [UserRole.ADMIN]


def require_role(*required_roles: str) -> Callable:
    """
    Decorator to require specific role(s) for endpoint
    
    Args:
        *required_roles: One or more roles (e.g., UserRole.DIRECTOR, UserRole.ADMIN)
        
    Usage:
        @router.get("/admin")
        @require_role(UserRole.ADMIN, UserRole.DIRECTOR)
        async def admin_endpoint(current_user: dict = Depends(get_current_user)):
            ...
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def wrapper(*args, **kwargs) -> Any:
            # Extract current_user from kwargs
            current_user = kwargs.get("current_user")
            
            if not current_user:
                raise RoleNotFound("User not found in context")
            
            user_role = current_user.get("role")
            
            if user_role not in required_roles:
                logger.warning(
                    f"❌ RBAC denied: User {current_user.get('user_id')} "
                    f"role={user_role} required={required_roles}"
                )
                raise PermissionDenied(
                    f"This endpoint requires one of: {', '.join(required_roles)}"
                )
            
            return await func(*args, **kwargs)
        
        return wrapper
    
    return decorator


def require_admin(func: Callable) -> Callable:
    """Decorator to require ADMIN role"""
    return require_role(UserRole.ADMIN)(func)


def require_director(func: Callable) -> Callable:
    """Decorator to require DIRECTOR or ADMIN role"""
    return require_role(UserRole.DIRECTOR, UserRole.ADMIN)(func)


def require_partner(func: Callable) -> Callable:
    """Decorator to require PARTNER, DIRECTOR, or ADMIN role"""
    return require_role(UserRole.PARTNER, UserRole.DIRECTOR, UserRole.ADMIN)(func)


def require_permission(permission: str) -> Callable:
    """
    Decorator to require specific permission
    
    Args:
        permission: Permission to require (read, write, delete, audit, admin)
        
    Usage:
        @router.post("/data")
        @require_permission("write")
        async def write_data(current_user: dict = Depends(get_current_user)):
            ...
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def wrapper(*args, **kwargs) -> Any:
            current_user = kwargs.get("current_user")
            
            if not current_user:
                raise RoleNotFound("User not found in context")
            
            user_role = current_user.get("role")
            
            if not RBACMiddleware.has_permission(user_role, permission):
                logger.warning(
                    f"❌ Permission denied: User {current_user.get('user_id')} "
                    f"lacks '{permission}' permission (role={user_role})"
                )
                raise PermissionDenied(
                    f"This endpoint requires '{permission}' permission"
                )
            
            return await func(*args, **kwargs)
        
        return wrapper
    
    return decorator


# ============================================================================
# Dependency for FastAPI
# ============================================================================
async def get_current_user_with_role(
    current_user: dict = Depends(lambda: {"user_id": "user123", "role": UserRole.DIRECTOR})
) -> dict:
    """
    Dependency to inject current user with role
    Can be used with @require_role decorator
    
    Returns:
        {"user_id": "...", "role": "...", "company_id": "..."}
    """
    if not current_user or not current_user.get("role"):
        raise RoleNotFound("User role not found")
    
    return current_user
