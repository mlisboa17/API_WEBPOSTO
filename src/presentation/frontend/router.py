"""
GROK 4: Security UI - Route Protection HOC
JWT validation and role-based access control for frontend routes
"""

from typing import Callable, Type
from functools import wraps
from pydantic import BaseModel, ConfigDict, Field
import reflex as rx
from ..state import GlobalState, UserRole


class ProtectedRouteConfig(BaseModel):
    """Protected route configuration"""
    model_config = ConfigDict(frozen=True)
    
    path: str = Field(..., description="Route path")
    required_role: UserRole | list[UserRole] = Field(default=UserRole.VIEWER)
    allow_unauthenticated: bool = Field(default=False)
    fallback_url: str = Field(default="/login")


class PermissionRouter:
    """
    GROK 4: Route protection with JWT validation
    HOC (Higher-Order Component) pattern for Reflex
    """
    
    _protected_routes: dict[str, ProtectedRouteConfig] = {}
    
    @classmethod
    def register_protected_route(
        cls,
        path: str,
        required_role: UserRole | list[UserRole] = UserRole.VIEWER,
        allow_unauthenticated: bool = False,
    ):
        """Register a protected route"""
        cls._protected_routes[path] = ProtectedRouteConfig(
            path=path,
            required_role=required_role,
            allow_unauthenticated=allow_unauthenticated,
        )
    
    @classmethod
    def protect_component(
        cls,
        component: Callable,
        required_role: UserRole | list[UserRole] = UserRole.VIEWER,
        fallback: Callable | None = None,
    ) -> Callable:
        """
        HOC: Wrap a component to require authentication/authorization
        
        Usage:
            @PermissionRouter.protect_component(required_role=UserRole.DIRECTOR)
            def AdminDashboard():
                return rx.heading("Admin Area")
        """
        @wraps(component)
        def wrapper(state: GlobalState):
            # Check authentication
            if not state.is_authenticated():
                return fallback() if fallback else _unauthorized_view()
            
            # Check permission
            user_role = state.get_user_role()
            if isinstance(required_role, list):
                has_permission = user_role in required_role
            else:
                has_permission = user_role == required_role or user_role == UserRole.DIRECTOR
            
            if not has_permission:
                return fallback() if fallback else _forbidden_view()
            
            # Render component
            return component()
        
        return wrapper
    
    @classmethod
    def create_auth_page_wrapper(
        cls,
        page_component: Callable,
        required_role: UserRole | list[UserRole] = UserRole.VIEWER,
    ) -> Callable:
        """
        Create a page wrapper that checks JWT before rendering
        For use with Reflex page routing
        """
        @wraps(page_component)
        def wrapper() -> rx.Component:
            state = GlobalState()
            
            if not state.is_authenticated():
                return rx.redirect("/login")
            
            # Check role permission
            user_role = state.get_user_role()
            if isinstance(required_role, list):
                has_permission = user_role in required_role
            else:
                has_permission = user_role == required_role or user_role == UserRole.DIRECTOR
            
            if not has_permission:
                return _forbidden_view()
            
            return page_component()
        
        return wrapper


def _unauthorized_view() -> rx.Component:
    """Fallback: Unauthorized (not authenticated) view"""
    return rx.center(
        rx.vstack(
            rx.icon("lock", size=48, color="var(--color-danger)"),
            rx.heading("Acesso Negado", size="lg"),
            rx.text(
                "Você precisa estar autenticado para acessar esta página.",
                text_align="center",
            ),
            rx.button(
                "Fazer Login",
                on_click=rx.redirect("/login"),
                color_scheme="blue",
            ),
            spacing="lg",
            align_items="center",
            padding="lg",
        ),
        height="100vh",
    )


def _forbidden_view() -> rx.Component:
    """Fallback: Forbidden (insufficient permissions) view"""
    return rx.center(
        rx.vstack(
            rx.icon("shield-x", size=48, color="var(--color-danger)"),
            rx.heading("Acesso Proibido", size="lg"),
            rx.text(
                "Você não tem permissão para acessar este conteúdo.",
                text_align="center",
            ),
            rx.text(
                "Entre em contato com o administrador se acha que é um erro.",
                font_size="sm",
                color="var(--color-text-secondary)",
                text_align="center",
            ),
            rx.button(
                "Voltar ao Dashboard",
                on_click=rx.redirect("/dashboard"),
                color_scheme="blue",
            ),
            spacing="lg",
            align_items="center",
            padding="lg",
        ),
        height="100vh",
    )


# Decorator for components
def require_auth(
    required_role: UserRole | list[UserRole] = UserRole.VIEWER,
    fallback: Callable | None = None,
):
    """
    Decorator: Require authentication for a component
    
    Usage:
        @require_auth(required_role=UserRole.DIRECTOR)
        def AdminPanel():
            return rx.heading("Admin")
    """
    def decorator(func: Callable) -> Callable:
        return PermissionRouter.protect_component(func, required_role, fallback)
    return decorator


def require_director(fallback: Callable | None = None):
    """Decorator: Require director role"""
    return require_auth(required_role=UserRole.DIRECTOR, fallback=fallback)


def require_partner(fallback: Callable | None = None):
    """Decorator: Require partner or director role"""
    return require_auth(required_role=[UserRole.PARTNER, UserRole.DIRECTOR], fallback=fallback)
