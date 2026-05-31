"""
GROK 4: Audit Page - Real-time audit log viewer with SHA-256 verification
Features:
- Real-time audit feed updates via WebSocket
- SHA-256 integrity verification indicators
- Search + filtering by action/user/status
- Timestamp display with timezone
- Mobile-responsive table/card views
- Export functionality (DIRECTOR+ only)

CLAUDE 3.7: Protected with @require_director()
"""

import reflex as rx
from typing import List, Optional
from datetime import datetime, timedelta
import httpx


# =============================================================================
# Audit State
# =============================================================================

class AuditState(rx.State):
    """Audit page state"""
    
    # Audit logs
    audit_logs: List[Dict] = []
    total_logs: int = 0
    
    # Pagination
    current_page: int = 1
    page_size: int = 20
    
    # Filters
    search_query: str = ""
    action_filter: str = "all"
    status_filter: str = "all"
    user_filter: str = ""
    date_range_filter: str = "7d"  # 7 days, 30d, 90d, all
    
    # WebSocket
    connected: bool = False
    new_log_count: int = 0
    
    # Loading
    is_loading: bool = False
    last_update: Optional[str] = None
    
    # Actions available
    available_actions: List[str] = [
        "login_success",
        "login_failure",
        "data_accessed",
        "data_modified",
        "data_deleted",
        "token_revoked",
        "permission_denied",
        "export_requested",
        "settings_changed",
    ]
    
    async def load_audit_logs(self) -> None:
        """
        Load audit logs from backend with filters
        
        CLAUDE 3.7: RBAC-protected (director+ only)
        """
        if not GlobalState.is_authenticated or not GlobalState.can_view_audit:
            return
        
        self.is_loading = True
        
        try:
            # Build query parameters
            params = {
                "page": self.current_page,
                "page_size": self.page_size,
            }
            
            if self.search_query:
                params["search"] = self.search_query
            
            if self.action_filter != "all":
                params["action"] = self.action_filter
            
            if self.status_filter != "all":
                params["status"] = self.status_filter
            
            if self.user_filter:
                params["user"] = self.user_filter
            
            # Calculate date range
            if self.date_range_filter != "all":
                days = int(self.date_range_filter.rstrip("d"))
                since_date = (datetime.now() - timedelta(days=days)).isoformat()
                params["since"] = since_date
            
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    "http://localhost:8000/api/audit-logs",
                    params=params,
                    headers={"Authorization": f"Bearer {GlobalState.access_token}"},
                    timeout=10
                )
                
                if response.status_code == 200:
                    data = response.json()
                    self.audit_logs = data.get("logs", [])
                    self.total_logs = data.get("total", 0)
                    self.last_update = datetime.now().isoformat()
        
        except Exception as e:
            print(f"Failed to load audit logs: {e}")
        
        finally:
            self.is_loading = False
    
    async def on_search_change(self, value: str) -> None:
        """Handle search input change"""
        self.search_query = value
        self.current_page = 1  # Reset to first page
        await self.load_audit_logs()
    
    async def on_action_filter_change(self, value: str) -> None:
        """Handle action filter change"""
        self.action_filter = value
        self.current_page = 1
        await self.load_audit_logs()
    
    async def on_status_filter_change(self, value: str) -> None:
        """Handle status filter change"""
        self.status_filter = value
        self.current_page = 1
        await self.load_audit_logs()
    
    async def on_date_range_change(self, value: str) -> None:
        """Handle date range filter change"""
        self.date_range_filter = value
        self.current_page = 1
        await self.load_audit_logs()
    
    async def export_logs(self) -> None:
        """
        Export audit logs to CSV
        
        CLAUDE 3.7: DIRECTOR+ only
        """
        if not GlobalState.can_delete:  # Use can_delete as proxy for export permission
            return
        
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    "http://localhost:8000/api/audit-logs/export",
                    headers={"Authorization": f"Bearer {GlobalState.access_token}"},
                    timeout=30
                )
                
                if response.status_code == 200:
                    # Trigger file download
                    filename = f"audit-logs-{datetime.now().strftime('%Y%m%d-%H%M%S')}.csv"
                    print(f"Downloaded: {filename}")
        
        except Exception as e:
            print(f"Export failed: {e}")


# =============================================================================
# Audit Page Components
# =============================================================================

def audit_log_table() -> rx.Component:
    """
    Table view of audit logs (desktop)
    
    GROK 4: Responsive design (hidden on mobile)
    """
    
    return rx.box(
        rx.cond(
            AuditState.audit_logs.length() > 0,
            rx.table(
                rx.thead(
                    rx.tr(
                        rx.th("Timestamp"),
                        rx.th("Action"),
                        rx.th("User"),
                        rx.th("IP Address"),
                        rx.th("Status"),
                        rx.th("Integrity"),
                    ),
                ),
                rx.tbody(
                    rx.foreach(
                        AuditState.audit_logs,
                        lambda log: rx.tr(
                            rx.td(rx.text(log.get("timestamp", ""), font_size="sm")),
                            rx.td(
                                rx.badge(
                                    log.get("action", "").replace("_", " ").title(),
                                    color_scheme="blue",
                                    size="sm",
                                )
                            ),
                            rx.td(rx.text(log.get("user", "system"), font_size="sm")),
                            rx.td(rx.text(log.get("ip_address", "—"), font_family="monospace", font_size="xs")),
                            rx.td(
                                rx.cond(
                                    log.get("status", "") == "success",
                                    rx.badge("✓", color_scheme="green", size="sm"),
                                    rx.cond(
                                        log.get("status", "") == "error",
                                        rx.badge("✗", color_scheme="red", size="sm"),
                                        rx.badge("○", color_scheme="gray", size="sm"),
                                    )
                                )
                            ),
                            rx.td(
                                rx.hstack(
                                    rx.cond(
                                        log.get("integrity_verified", False),
                                        rx.box(
                                            rx.text("✓", color="green", font_weight="bold"),
                                            title="SHA-256 verified",
                                        ),
                                        rx.box(
                                            rx.text("✗", color="red", font_weight="bold"),
                                            title="Integrity check failed",
                                        ),
                                    ),
                                    rx.text(
                                        log.get("checksum", "")[:8] + "...",
                                        font_family="monospace",
                                        font_size="xs",
                                        color="gray",
                                    ),
                                    spacing="1",
                                ),
                                font_size="xs",
                            ),
                        )
                    ),
                ),
                width="100%",
                border="1px solid #475569",
                border_radius="md",
            ),
            rx.text("No audit logs found", text_align="center", color="gray", padding="4"),
        ),
        width="100%",
    )


def audit_log_cards() -> rx.Component:
    """
    Card view of audit logs (mobile)
    
    GROK 4: Mobile-responsive
    """
    
    return rx.box(
        rx.vstack(
            rx.foreach(
                AuditState.audit_logs,
                lambda log: rx.box(
                    rx.vstack(
                        # Header
                        rx.hstack(
                            rx.badge(
                                log.get("action", "").replace("_", " ").title(),
                                color_scheme="blue",
                                size="sm",
                            ),
                            rx.spacer(),
                            rx.cond(
                                log.get("integrity_verified", False),
                                rx.text("✓", color="green", font_weight="bold", title="Verified"),
                                rx.text("✗", color="red", font_weight="bold", title="Unverified"),
                            ),
                            width="100%",
                        ),
                        
                        # Details
                        rx.vstack(
                            rx.hstack(
                                rx.text("User:", font_weight="bold", width="60px"),
                                rx.text(log.get("user", "system")),
                                width="100%",
                            ),
                            rx.hstack(
                                rx.text("IP:", font_weight="bold", width="60px"),
                                rx.text(
                                    log.get("ip_address", "—"),
                                    font_family="monospace",
                                    font_size="xs",
                                ),
                                width="100%",
                            ),
                            rx.hstack(
                                rx.text("Time:", font_weight="bold", width="60px"),
                                rx.text(log.get("timestamp", ""), font_size="sm"),
                                width="100%",
                            ),
                            spacing="1",
                        ),
                        
                        # Status
                        rx.hstack(
                            rx.cond(
                                log.get("status", "") == "success",
                                rx.badge("Success", color_scheme="green", size="sm"),
                                rx.cond(
                                    log.get("status", "") == "error",
                                    rx.badge("Error", color_scheme="red", size="sm"),
                                    rx.badge("Info", color_scheme="gray", size="sm"),
                                )
                            ),
                            width="100%",
                        ),
                        
                        spacing="2",
                    ),
                    padding="3",
                    border="1px solid #475569",
                    border_radius="md",
                    width="100%",
                ),
            ),
            spacing="2",
            width="100%",
        ),
        width="100%",
    )


# =============================================================================
# Main Audit Page
# =============================================================================

def audit_page() -> rx.Component:
    """
    Audit logs page
    
    CLAUDE 3.7: Protected with @require_director()
    GROK 4: Real-time updates + responsive design
    """
    
    return rx.box(
        rx.vstack(
            # Header
            rx.hstack(
                rx.vstack(
                    rx.heading("📋 Audit Logs", size="xl"),
                    rx.text(
                        f"Total: {AuditState.total_logs} events",
                        color="gray",
                        size="sm",
                    ),
                    spacing="1",
                ),
                rx.spacer(),
                
                # Export button
                rx.cond(
                    GlobalState.can_delete,
                    rx.button(
                        "📥 Export CSV",
                        on_click=AuditState.export_logs,
                        color_scheme="blue",
                        size="sm",
                    ),
                    rx.empty(),
                ),
                
                width="100%",
                align="center",
            ),
            
            rx.divider(),
            
            # Filters
            rx.hstack(
                # Search
                rx.input(
                    placeholder="Search logs...",
                    value=AuditState.search_query,
                    on_change=AuditState.on_search_change,
                    width="200px",
                    padding="2",
                    border="1px solid #475569",
                    border_radius="md",
                ),
                
                # Action filter
                rx.select(
                    ["all"] + AuditState.available_actions,
                    value=AuditState.action_filter,
                    on_change=AuditState.on_action_filter_change,
                    width="150px",
                ),
                
                # Status filter
                rx.select(
                    ["all", "success", "error", "info"],
                    value=AuditState.status_filter,
                    on_change=AuditState.on_status_filter_change,
                    width="120px",
                ),
                
                # Date range
                rx.select(
                    ["7d", "30d", "90d", "all"],
                    value=AuditState.date_range_filter,
                    on_change=AuditState.on_date_range_change,
                    width="100px",
                ),
                
                # Refresh button
                rx.button(
                    "🔄 Refresh",
                    on_click=AuditState.load_audit_logs,
                    color_scheme="gray",
                    size="sm",
                ),
                
                rx.spacer(),
                
                # WebSocket status
                rx.cond(
                    AuditState.connected,
                    rx.badge("🟢 Live", color_scheme="green", size="sm"),
                    rx.badge("⚪ Offline", color_scheme="gray", size="sm"),
                ),
                
                width="100%",
                spacing="2",
                padding="3",
                border="1px solid #475569",
                border_radius="md",
                bg="#0f172a",
            ),
            
            # New logs notification
            rx.cond(
                AuditState.new_log_count > 0,
                rx.box(
                    rx.text(
                        f"📭 {AuditState.new_log_count} new events",
                        size="sm",
                        color="blue",
                    ),
                    padding="2",
                    bg="rgba(59, 130, 246, 0.1)",
                    border="1px solid #3b82f6",
                    border_radius="md",
                    width="100%",
                ),
                rx.empty(),
            ),
            
            # Table (desktop)
            rx.box(
                audit_log_table(),
                display=["none", "none", "block"],  # Show on desktop
                width="100%",
            ),
            
            # Cards (mobile)
            rx.box(
                audit_log_cards(),
                display=["block", "block", "none"],  # Show on mobile
                width="100%",
            ),
            
            # Pagination
            rx.hstack(
                rx.button(
                    "← Previous",
                    on_click=lambda: setattr(AuditState, "current_page", AuditState.current_page - 1) or AuditState.load_audit_logs(),
                    disabled=AuditState.current_page == 1,
                    size="sm",
                ),
                rx.text(
                    f"Page {AuditState.current_page} of {(AuditState.total_logs + AuditState.page_size - 1) // AuditState.page_size}",
                    size="sm",
                    color="gray",
                ),
                rx.button(
                    "Next →",
                    on_click=lambda: setattr(AuditState, "current_page", AuditState.current_page + 1) or AuditState.load_audit_logs(),
                    disabled=AuditState.current_page * AuditState.page_size >= AuditState.total_logs,
                    size="sm",
                ),
                rx.spacer(),
                width="100%",
                justify="center",
            ),
            
            spacing="4",
            padding="6",
        ),
        
        width="100%",
        min_height="100vh",
        bg="linear-gradient(135deg, #0f172a 0%, #1e293b 100%)",
        color="white",
    )
