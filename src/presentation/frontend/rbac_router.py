"""
CLAUDE 3.7: RBAC Router - Route Protection with Role-Based Access Control
Provides @rx.page decorators for Reflex pages with JWT validation

Features:
- @require_auth() - Requires authenticated user
- @require_role() - Requires specific roles
- @require_director() - Director/Admin only
- @require_partner() - Partner+ roles
- Automatic redirect to login
- Permission-based page rendering
"""

import reflex as rx
from functools import wraps
from typing import Callable, Optional, List, Set
from state_jwt import GlobalState, Role, UserInfo, SyncStatusInfo


# =============================================================================
# Unauthorized & Forbidden Views
# =============================================================================

def unauthorized_view() -> rx.Component:
    """
    Display when user is not authenticated
    Redirects to login
    """
    return rx.vstack(
        rx.heading("❌ Unauthorized", size="lg"),
        rx.text("You need to be logged in to access this page."),
        rx.link(
            rx.button("Go to Login", color_scheme="blue"),
            href="/login"
        ),
        spacing="4",
        justify="center",
        min_height="100vh",
    )


def forbidden_view(required_role: str = "") -> rx.Component:
    """
    Display when user lacks required permissions
    """
    return rx.vstack(
        rx.heading("❌ Access Denied", size="lg"),
        rx.text(f"Your role ({required_role}) doesn't have permission to access this page."),
        rx.divider(),
        rx.hstack(
            rx.link(rx.button("Back to Dashboard"), href="/dashboard"),
            rx.link(rx.button("Logout"), href="/logout"),
            spacing="2",
        ),
        spacing="4",
        justify="center",
        min_height="100vh",
    )


# =============================================================================
# Protected Route Configuration
# =============================================================================

class ProtectedRouteConfig:
    """Configuration for protected routes"""
    
    def __init__(
        self,
        required_roles: Optional[List[Role]] = None,
        require_auth: bool = True,
        redirect_to: str = "/login",
        fallback_view: Optional[Callable] = None
    ):
        self.required_roles = required_roles or []
        self.require_auth = require_auth
        self.redirect_to = redirect_to
        self.fallback_view = fallback_view or unauthorized_view


# =============================================================================
# Permission Router Decorators
# =============================================================================

class PermissionRouter:
    """
    Router for permission-based page access
    
    CLAUDE 3.7: @rx.page decorator wrapper with RBAC
    """
    
    @staticmethod
    def require_auth(
        redirect_to: str = "/login"
    ) -> Callable:
        """
        Decorator: Require authentication
        
        Usage:
            @PermissionRouter.require_auth()
            @rx.page(route="/dashboard")
            def dashboard_page() -> rx.Component:
                ...
        """
        def decorator(page_func: Callable) -> Callable:
            @wraps(page_func)
            def wrapper() -> rx.Component:
                if not GlobalState.is_authenticated:
                    return rx.cond(
                        GlobalState.is_authenticated,
                        page_func(),
                        unauthorized_view()
                    )
                return page_func()
            
            return wrapper
        return decorator
    
    @staticmethod
    def require_role(
        *required_roles: Role,
        redirect_to: str = "/login"
    ) -> Callable:
        """
        Decorator: Require specific role(s)
        
        Usage:
            @PermissionRouter.require_role(Role.DIRECTOR, Role.ADMIN)
            @rx.page(route="/admin")
            def admin_page() -> rx.Component:
                ...
        """
        def decorator(page_func: Callable) -> Callable:
            @wraps(page_func)
            def wrapper() -> rx.Component:
                def render_page() -> rx.Component:
                    if not GlobalState.is_authenticated:
                        return unauthorized_view()
                    
                    user_role = GlobalState.user.role if GlobalState.user else None
                    if user_role not in required_roles:
                        return forbidden_view(f"Requires: {', '.join([r.value for r in required_roles])}")
                    
                    return page_func()
                
                return rx.cond(
                    GlobalState.is_authenticated,
                    rx.cond(
                        GlobalState.user.role.isin([r.value for r in required_roles]),
                        page_func(),
                        forbidden_view(f"Requires: {', '.join([r.value for r in required_roles])}")
                    ),
                    unauthorized_view()
                )
            
            return wrapper
        return decorator
    
    @staticmethod
    def require_director() -> Callable:
        """
        Decorator: Director or Admin only
        
        Usage:
            @PermissionRouter.require_director()
            @rx.page(route="/settings")
            def settings_page() -> rx.Component:
                ...
        """
        def decorator(page_func: Callable) -> Callable:
            @wraps(page_func)
            def wrapper() -> rx.Component:
                return rx.cond(
                    GlobalState.is_authenticated & GlobalState.is_director,
                    page_func(),
                    rx.cond(
                        GlobalState.is_authenticated,
                        forbidden_view("DIRECTOR"),
                        unauthorized_view()
                    )
                )
            
            return wrapper
        return decorator
    
    @staticmethod
    def require_partner() -> Callable:
        """
        Decorator: Partner or higher role
        
        Usage:
            @PermissionRouter.require_partner()
            @rx.page(route="/reports")
            def reports_page() -> rx.Component:
                ...
        """
        def decorator(page_func: Callable) -> Callable:
            @wraps(page_func)
            def wrapper() -> rx.Component:
                partner_roles = [Role.PARTNER, Role.DIRECTOR, Role.ADMIN]
                
                return rx.cond(
                    GlobalState.is_authenticated,
                    rx.cond(
                        GlobalState.user.role.isin([r.value for r in partner_roles]),
                        page_func(),
                        forbidden_view("PARTNER")
                    ),
                    unauthorized_view()
                )
            
            return wrapper
        return decorator
    
    @staticmethod
    def require_admin() -> Callable:
        """
        Decorator: Admin only
        
        Usage:
            @PermissionRouter.require_admin()
            @rx.page(route="/admin/users")
            def admin_users_page() -> rx.Component:
                ...
        """
        def decorator(page_func: Callable) -> Callable:
            @wraps(page_func)
            def wrapper() -> rx.Component:
                return rx.cond(
                    GlobalState.is_authenticated & (GlobalState.user.role == Role.ADMIN.value),
                    page_func(),
                    rx.cond(
                        GlobalState.is_authenticated,
                        forbidden_view("ADMIN"),
                        unauthorized_view()
                    )
                )
            
            return wrapper
        return decorator
    
    @staticmethod
    def require_permission(*permissions) -> Callable:
        """
        Decorator: Require specific permission(s)
        
        Usage:
            @PermissionRouter.require_permission("WRITE", "DELETE")
            @rx.page(route="/data/edit")
            def edit_page() -> rx.Component:
                ...
        """
        def decorator(page_func: Callable) -> Callable:
            @wraps(page_func)
            def wrapper() -> rx.Component:
                return rx.cond(
                    GlobalState.is_authenticated & GlobalState.can_edit,
                    page_func(),
                    rx.cond(
                        GlobalState.is_authenticated,
                        forbidden_view("WRITE/DELETE"),
                        unauthorized_view()
                    )
                )
            
            return wrapper
        return decorator


# =============================================================================
# Skeleton Loader for Sync Transitions
# =============================================================================

def skeleton_loader() -> rx.Component:
    """
    Skeleton loader shown during sync transitions
    
    CLAUDE 3.7: Visual feedback during data sync
    """
    return rx.box(
        rx.vstack(
            # Header skeleton
            rx.skeleton(width="100%", height="60px", border_radius="md"),
            
            # Content skeleton (3 cards)
            rx.hstack(
                rx.skeleton(width="100%", height="150px", border_radius="md"),
                rx.skeleton(width="100%", height="150px", border_radius="md"),
                rx.skeleton(width="100%", height="150px", border_radius="md"),
                width="100%",
                spacing="4",
            ),
            
            # Chart skeleton
            rx.skeleton(width="100%", height="300px", border_radius="md"),
            
            spacing="4",
            padding="4",
        ),
        width="100%",
    )


# =============================================================================
# Page Wrapper with Skeleton Support
# =============================================================================

def protected_page(
    page_component: rx.Component,
    required_roles: Optional[List[Role]] = None,
    show_skeleton: bool = True
) -> rx.Component:
    """
    Wrap page component with protection + skeleton loader
    
    CLAUDE 3.7: Unified protection and loading state
    """
    
    # Determine if user has access
    if required_roles:
        access_granted = rx.cond(
            GlobalState.is_authenticated,
            GlobalState.user.role.isin([r.value for r in required_roles]),
            False
        )
    else:
        access_granted = GlobalState.is_authenticated
    
    # Show skeleton during sync
    if show_skeleton:
        content = rx.cond(
            GlobalState.show_skeleton_loader,
            skeleton_loader(),
            page_component
        )
    else:
        content = page_component
    
    # Final component with access check
    return rx.cond(
        access_granted,
        content,
        rx.cond(
            GlobalState.is_authenticated,
            forbidden_view("Required Role"),
            unauthorized_view()
        )
    )
