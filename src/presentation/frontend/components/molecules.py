"""
CLAUDE 3.7: Atomic Design Components - Molecule Level
Composed of multiple atoms, self-contained features
"""

from typing import Optional
from pydantic import BaseModel, ConfigDict, Field
from datetime import datetime
import reflex as rx
from .atoms import Card, Badge, SkeletonLoader, LoadingSpinner


class SyncProgressBarProps(BaseModel):
    """Sync progress bar properties"""
    model_config = ConfigDict(frozen=False)
    
    status: str = Field(default="idle", description="Sync status")
    progress: int = Field(default=0, ge=0, le=100, description="Progress %")
    records_synced: int = Field(default=0, ge=0)
    total_records: int | None = Field(default=None)
    error_message: str | None = Field(default=None)


class SyncProgressBar(rx.Component):
    """
    Atomic Design: MOLECULE
    Real-time sync progress indicator
    Shows status, progress bar, and record count
    """
    tag = "div"
    
    status: rx.Var[str] = "idle"
    progress: rx.Var[int] = 0
    records_synced: rx.Var[int] = 0
    total_records: rx.Var[int | None] = None
    
    @staticmethod
    def render(
        status: str = "idle",
        progress: int = 0,
        records_synced: int = 0,
        total_records: int | None = None,
    ):
        status_color = {
            "idle": "#6B7280",
            "syncing": "#F59E0B",
            "success": "#10B981",
            "error": "#EF4444",
            "partial": "#F59E0B",
        }
        
        return rx.vstack(
            # Status header
            rx.hstack(
                rx.heading("Sincronização", size="sm", font_weight="bold"),
                Badge.render(status.upper()),
                width="100%",
                justify_content="space-between",
            ),
            
            # Progress bar
            rx.progress(
                value=progress,
                color_scheme="blue" if status == "syncing" else "green",
                width="100%",
                height="8px",
            ),
            
            # Details
            rx.hstack(
                rx.text(
                    f"{progress}% concluído",
                    font_size="xs",
                    color="var(--color-text-secondary)",
                ),
                rx.cond(
                    total_records is not None,
                    rx.text(
                        f"{records_synced}/{total_records} registros",
                        font_size="xs",
                        color="var(--color-text-secondary)",
                    ),
                ),
                width="100%",
                justify_content="space-between",
            ),
            
            # Error message
            rx.cond(
                status == "error",
                rx.box(
                    rx.text(
                        f"Erro: {rx.Var.create('error_message')}",
                        font_size="xs",
                        color="var(--color-danger)",
                    ),
                    background_color="rgba(239, 68, 68, 0.1)",
                    padding="sm",
                    border_radius="md",
                ),
            ),
            
            spacing="md",
            width="100%",
        )


class CompanySelectorProps(BaseModel):
    """Company selector properties"""
    model_config = ConfigDict(frozen=False)
    
    companies: list[dict] = Field(default_factory=list, description="Available companies")
    active_company: str | None = Field(default=None, description="Active company ID")
    on_change: Optional[str] = Field(default=None, description="Change handler")


class CompanySelector(rx.Component):
    """
    Atomic Design: MOLECULE
    Dropdown for company selection
    Supports search and quick switch
    """
    tag = "div"
    
    companies: rx.Var[list]
    active_company: rx.Var[str | None]
    
    @staticmethod
    def render(
        companies: list = None,
        active_company: str | None = None,
    ):
        if companies is None:
            companies = []
        
        return rx.box(
            rx.vstack(
                rx.heading("Empresa Ativa", size="xs", text_transform="uppercase"),
                
                # Company dropdown
                rx.select(
                    values=[c.get("name", "") for c in companies],
                    value=active_company or "",
                    placeholder="Selecione uma empresa",
                    on_change=rx.Var.create("on_company_change"),
                ),
                
                spacing="sm",
                width="100%",
            ),
            padding="md",
            border="1px solid var(--color-border)",
            border_radius="md",
            background_color="var(--color-surface)",
        )


class DashboardCard(rx.Component):
    """
    Atomic Design: MOLECULE
    Dashboard card with metric and status
    Used for displaying key metrics (sync status, record count, etc.)
    """
    tag = "div"
    
    @staticmethod
    def render(
        title: str,
        metric: str | int,
        subtitle: str | None = None,
        status: str = "default",
        icon: str | None = None,
    ):
        status_colors = {
            "success": "var(--color-success)",
            "warning": "var(--color-warning)",
            "error": "var(--color-danger)",
            "info": "var(--color-primary)",
            "default": "var(--color-text-secondary)",
        }
        
        return rx.box(
            rx.vstack(
                # Title
                rx.text(
                    title,
                    font_size="xs",
                    font_weight="bold",
                    text_transform="uppercase",
                    color="var(--color-text-secondary)",
                ),
                
                # Metric (large number)
                rx.heading(
                    str(metric),
                    size="lg",
                    font_weight="bold",
                    color=status_colors.get(status, status_colors["default"]),
                ),
                
                # Subtitle
                rx.cond(
                    subtitle is not None,
                    rx.text(
                        subtitle,
                        font_size="sm",
                        color="var(--color-text-secondary)",
                    ),
                ),
                
                spacing="sm",
                width="100%",
            ),
            border="1px solid var(--color-border)",
            border_radius="lg",
            padding="md",
            background_color="var(--color-surface)",
            box_shadow="var(--shadow-sm)",
            _hover={
                "box_shadow": "var(--shadow-md)",
                "transform": "translateY(-2px)",
                "transition": "all 0.2s ease",
            },
        )


class AuditFeedItem(rx.Component):
    """
    Atomic Design: MOLECULE
    Single audit log entry
    """
    tag = "li"
    
    @staticmethod
    def render(
        action: str,
        timestamp: datetime,
        user: str,
        details: str | None = None,
    ):
        return rx.box(
            rx.hstack(
                # Timestamp
                rx.vstack(
                    rx.text(
                        timestamp.strftime("%H:%M"),
                        font_size="sm",
                        font_weight="bold",
                    ),
                    rx.text(
                        timestamp.strftime("%d/%m"),
                        font_size="xs",
                        color="var(--color-text-secondary)",
                    ),
                    spacing="xs",
                ),
                
                # Action details
                rx.vstack(
                    rx.text(action, font_weight="bold"),
                    rx.text(
                        f"por {user}",
                        font_size="sm",
                        color="var(--color-text-secondary)",
                    ),
                    rx.cond(
                        details is not None,
                        rx.text(
                            details,
                            font_size="xs",
                            font_style="italic",
                            color="var(--color-text-secondary)",
                        ),
                    ),
                    spacing="xs",
                    flex="1",
                ),
                
                width="100%",
                spacing="md",
                align_items="flex-start",
            ),
            border_left="3px solid var(--color-primary)",
            padding="md",
            padding_left="md",
        )
