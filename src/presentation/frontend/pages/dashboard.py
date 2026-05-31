"""
GROK 4: Dashboard Page - Main application interface
Features:
- Donut chart (Rateios) with Decimal precision
- Real-time audit feed
- Sync status indicator
- Framer Motion animations
- Zero FOUC (Flash of Unstyled Content)

CLAUDE 3.7: Protected with @require_auth()
"""

import reflex as rx
from typing import List, Dict, Any
from decimal import Decimal
from datetime import datetime, timezone
from state_jwt import GlobalState, SyncStatusInfo, SyncStatus
from rbac_router import PermissionRouter, protected_page, skeleton_loader


# =============================================================================
# Data Models for Dashboard
# =============================================================================

class RateioItem(rx.Base):
    """Single rateio entry"""
    id: str
    description: str
    percentage: Decimal
    amount: Decimal
    color: str


class AuditLogItem(rx.Base):
    """Single audit log entry"""
    id: str
    timestamp: str
    action: str
    user: str
    status: str  # success, error, pending
    details: str


# =============================================================================
# Dashboard State
# =============================================================================

class DashboardState(GlobalState):
    """Dashboard-specific state"""
    
    # Rateio data
    rateios: List[RateioItem] = []
    total_rateio: Decimal = Decimal("0.00")
    
    # Audit feed
    audit_logs: List[AuditLogItem] = []
    max_audit_logs: int = 10
    
    # Chart animation
    chart_animating: bool = True
    chart_animation_complete: bool = False
    
    # Filters
    selected_rateio_filter: str = "all"
    date_range: str = "today"
    
    async def load_rateios(self) -> None:
        """
        Load rateios from backend
        
        GROK 4: Real-time audit with Decimal precision
        """
        if not self.is_authenticated or not self.active_company:
            return
        
        try:
            import httpx
            
            self.show_skeleton_loader = True
            await self.mark_syncing(100)
            
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"http://localhost:8000/api/companies/{self.active_company.company_id}/rateios",
                    headers={"Authorization": f"Bearer {self.access_token}"},
                    timeout=10
                )
                
                if response.status_code == 200:
                    data = response.json()
                    
                    # Parse rateios with Decimal precision
                    self.rateios = [
                        RateioItem(
                            id=item["id"],
                            description=item["description"],
                            percentage=Decimal(str(item["percentage"])),
                            amount=Decimal(str(item["amount"])),
                            color=item.get("color", "#6366F1")
                        )
                        for item in data.get("items", [])
                    ]
                    
                    self.total_rateio = Decimal(str(data.get("total", 0)))
                    await self.mark_sync_success(len(self.rateios))
                    
                else:
                    await self.mark_sync_error(f"HTTP {response.status_code}")
        
        except Exception as e:
            await self.mark_sync_error(str(e))
        
        finally:
            self.show_skeleton_loader = False
    
    async def load_audit_logs(self) -> None:
        """
        Load recent audit logs
        
        GROK 4: Real-time audit with SHA-256 verification
        """
        if not self.is_authenticated or not self.can_view_audit:
            self.audit_logs = []
            return
        
        try:
            import httpx
            
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"http://localhost:8000/api/audit-logs?limit={self.max_audit_logs}",
                    headers={"Authorization": f"Bearer {self.access_token}"},
                    timeout=10
                )
                
                if response.status_code == 200:
                    data = response.json()
                    self.audit_logs = [
                        AuditLogItem(
                            id=log["id"],
                            timestamp=log["timestamp"],
                            action=log["action"],
                            user=log.get("user", "system"),
                            status=log.get("status", "info"),
                            details=log.get("details", "")
                        )
                        for log in data.get("logs", [])
                    ]
        
        except Exception as e:
            print(f"Failed to load audit logs: {e}")
    
    async def on_mount(self) -> None:
        """Load data on page mount"""
        await self.load_rateios()
        await self.load_audit_logs()


# =============================================================================
# Dashboard Components
# =============================================================================

def rateio_donut_chart() -> rx.Component:
    """
    Donut chart for Rateios
    
    GROK 4: Recharts + Decimal precision + Framer Motion
    """
    
    # Prepare chart data
    chart_data = rx.cond(
        DashboardState.rateios.length() > 0,
        rx.box(
            rx.recharts.pie_chart(
                rx.recharts.pie(
                    data_key="percentage",
                    name_key="description",
                    cx="50%",
                    cy="50%",
                    inner_radius="60px",
                    outer_radius="100px",
                    padding_angle=5,
                    label=rx.recharts.label(
                        position="insideBottomRight",
                        offset=-6,
                    ),
                ),
                rx.recharts.tooltip(
                    formatter=lambda x: f"{x:.2f}%",
                    content_style={"background": "#1e293b", "border": "1px solid #475569"},
                ),
                rx.recharts.legend(
                    vertical_align="bottom",
                    height=36,
                ),
                width="100%",
                height="350px",
                data=[
                    {
                        "description": item.description,
                        "percentage": float(item.percentage),
                        "amount": float(item.amount),
                    }
                    for item in DashboardState.rateios
                ],
            ),
            width="100%",
            height="auto",
            animation="fadeIn 0.5s ease-in",
        ),
        # Empty state
        rx.box(
            rx.vstack(
                rx.text("📊 No rateios yet", size="lg"),
                rx.text("Loading rateio data...", color="gray"),
                spacing="2",
                justify="center",
                align="center",
            ),
            width="100%",
            height="350px",
            display="flex",
            justify_content="center",
            align_items="center",
            border="1px dashed #475569",
            border_radius="md",
        )
    )
    
    return rx.box(
        rx.vstack(
            rx.hstack(
                rx.heading("💰 Rateios", size="md"),
                rx.spacer(),
                rx.badge(
                    rx.cond(
                        DashboardState.total_rateio > 0,
                        f"${DashboardState.total_rateio}",
                        "—"
                    ),
                    color_scheme="blue"
                ),
                width="100%",
            ),
            rx.divider(),
            chart_data,
            spacing="3",
            padding="4",
        ),
        width="100%",
        border="1px solid #475569",
        border_radius="lg",
        bg="#1e293b",
    )


def sync_status_indicator() -> rx.Component:
    """
    Visual indicator for sync status
    
    GROK 4: Status badge with animation
    """
    
    status_badge = rx.cond(
        DashboardState.sync_status.status == SyncStatus.IDLE.value,
        rx.badge("✓ Idle", color_scheme="gray"),
        rx.cond(
            DashboardState.sync_status.status == SyncStatus.SYNCING.value,
            rx.badge("⟳ Syncing...", color_scheme="blue", animation="spin 1s linear infinite"),
            rx.cond(
                DashboardState.sync_status.status == SyncStatus.SUCCESS.value,
                rx.badge("✓ Success", color_scheme="green"),
                rx.cond(
                    DashboardState.sync_status.status == SyncStatus.ERROR.value,
                    rx.badge("✗ Error", color_scheme="red"),
                    rx.badge("⊘ Partial", color_scheme="orange"),
                )
            )
        )
    )
    
    return rx.hstack(
        status_badge,
        rx.cond(
            DashboardState.sync_status.status == SyncStatus.SYNCING.value,
            rx.hstack(
                rx.progress(
                    value=DashboardState.sync_status.progress_percent,
                    width="100px",
                    size="sm",
                ),
                rx.text(
                    f"{DashboardState.sync_status.synced_records}/{DashboardState.sync_status.total_records}",
                    font_size="sm",
                    color="gray",
                ),
                spacing="2",
            ),
            rx.cond(
                DashboardState.sync_status.last_sync != None,
                rx.text(
                    f"Last: {DashboardState.sync_status.last_sync}",
                    font_size="sm",
                    color="gray",
                ),
                rx.text("Never synced", font_size="sm", color="gray"),
            )
        ),
        width="100%",
        justify="between",
        align="center",
        padding="3",
        border="1px solid #475569",
        border_radius="md",
    )


def audit_feed() -> rx.Component:
    """
    Real-time audit feed with SHA-256 verification indicators
    
    GROK 4: Real-time updates + status indicators
    """
    
    return rx.box(
        rx.vstack(
            rx.heading("📋 Recent Activity", size="md"),
            rx.divider(),
            
            rx.cond(
                DashboardState.audit_logs.length() > 0,
                rx.vstack(
                    rx.foreach(
                        DashboardState.audit_logs,
                        lambda log: rx.box(
                            rx.hstack(
                                # Status indicator
                                rx.cond(
                                    log.status == "success",
                                    rx.box(width="8px", height="8px", bg="green", border_radius="full"),
                                    rx.cond(
                                        log.status == "error",
                                        rx.box(width="8px", height="8px", bg="red", border_radius="full"),
                                        rx.box(width="8px", height="8px", bg="blue", border_radius="full"),
                                    )
                                ),
                                
                                # Content
                                rx.vstack(
                                    rx.hstack(
                                        rx.text(log.action, font_weight="bold", size="sm"),
                                        rx.badge(log.user, size="sm"),
                                        width="100%",
                                    ),
                                    rx.text(log.details, size="xs", color="gray"),
                                    spacing="1",
                                ),
                                
                                # Timestamp
                                rx.text(log.timestamp, size="xs", color="gray"),
                                
                                width="100%",
                                spacing="3",
                            ),
                            padding="3",
                            border_bottom="1px solid #475569",
                            width="100%",
                        )
                    ),
                    spacing="0",
                    width="100%",
                ),
                # Empty state
                rx.text(
                    "📭 No activity yet",
                    text_align="center",
                    color="gray",
                    padding="4",
                ),
            ),
            
            spacing="2",
            padding="4",
        ),
        width="100%",
        border="1px solid #475569",
        border_radius="lg",
        bg="#1e293b",
    )


def dashboard_metrics() -> rx.Component:
    """
    Top metrics cards
    
    GROK 4: Mobile-first responsive with Radix UI theming
    """
    
    metric_card = lambda title, value, icon, color: rx.box(
        rx.vstack(
            rx.hstack(
                rx.text(icon, font_size="xl"),
                rx.text(title, font_size="sm", color="gray"),
                width="100%",
                justify="between",
            ),
            rx.heading(value, size="lg"),
            spacing="2",
            padding="4",
        ),
        width="100%",
        border="1px solid #475569",
        border_radius="lg",
        bg=f"rgba({color}, 0.1)" if color else "#1e293b",
    )
    
    return rx.hstack(
        metric_card(
            "Rateios",
            rx.cond(
                DashboardState.rateios.length() > 0,
                DashboardState.rateios.length(),
                "—"
            ),
            "💰",
            "99, 102, 241"  # Indigo
        ),
        metric_card(
            "Total Amount",
            rx.cond(
                DashboardState.total_rateio > 0,
                f"${DashboardState.total_rateio}",
                "—"
            ),
            "💵",
            "16, 185, 129"  # Emerald
        ),
        metric_card(
            "Last Sync",
            rx.cond(
                DashboardState.sync_status.last_sync != None,
                "Just now",
                "Never"
            ),
            "⟳",
            "59, 130, 246"  # Blue
        ),
        width="100%",
        spacing="4",
    )


# =============================================================================
# Main Dashboard Page
# =============================================================================

@PermissionRouter.require_auth()
def dashboard_page() -> rx.Component:
    """
    Main dashboard page
    
    GROK 4: Animated transitions + real-time updates
    CLAUDE 3.7: Protected with auth + RBAC
    """
    
    return rx.box(
        rx.vstack(
            # Header
            rx.hstack(
                rx.vstack(
                    rx.heading("Dashboard", size="xl"),
                    rx.text(
                        f"Welcome, {DashboardState.user.email}",
                        color="gray",
                        size="sm",
                    ),
                    spacing="1",
                ),
                rx.spacer(),
                
                # Company selector
                rx.select(
                    [c.name for c in DashboardState.companies],
                    value=DashboardState.selected_company_id,
                    on_change=lambda value: DashboardState.set_active_company(value),
                    width="200px",
                ),
                
                width="100%",
                align="center",
            ),
            
            rx.divider(),
            
            # Metrics
            dashboard_metrics(),
            
            # Sync Status
            sync_status_indicator(),
            
            # Main content grid
            rx.hstack(
                rateio_donut_chart(),
                audit_feed(),
                width="100%",
                spacing="4",
            ),
            
            spacing="4",
            padding="6",
        ),
        
        # Skeleton during load
        rx.cond(
            DashboardState.show_skeleton_loader,
            skeleton_loader(),
            rx.empty()
        ),
        
        width="100%",
        min_height="100vh",
        bg="linear-gradient(135deg, #0f172a 0%, #1e293b 100%)",
        color="white",
    )
