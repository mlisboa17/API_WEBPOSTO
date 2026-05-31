"""
CLAUDE 3.7: Organism Level Components (Pages)
Complete page layouts combining multiple molecules and atoms
"""

from typing import Optional
import reflex as rx
from .molecules import SyncProgressBar, CompanySelector, DashboardCard, AuditFeedItem
from .charts import RateioChart, MetricsGrid
from ..state import GlobalState


class Dashboard(rx.Component):
    """
    Atomic Design: ORGANISM (Page Level)
    Main dashboard showing company overview, sync status, and key metrics
    """
    tag = "div"
    
    @staticmethod
    def render():
        state = GlobalState()
        
        return rx.box(
            rx.vstack(
                # Header
                rx.hstack(
                    rx.heading(
                        "Dashboard",
                        size="xl",
                        font_weight="bold",
                    ),
                    rx.spacer(),
                    rx.button(
                        "Sincronizar Agora",
                        on_click=rx.Var.create("on_sync_click"),
                        color_scheme="blue",
                    ),
                    width="100%",
                ),
                
                # Company selector
                CompanySelector.render(
                    companies=state.available_companies or [],
                    active_company=state.active_company.empresa_id if state.active_company else None,
                ),
                
                # Sync status
                SyncProgressBar.render(
                    status=state.sync_status.status.value,
                    progress=state.sync_status.progress_percent,
                    records_synced=state.sync_status.records_synced,
                    total_records=state.sync_status.total_records,
                ),
                
                # Metrics grid
                rx.heading("Métricas Principais", size="md", font_weight="bold"),
                MetricsGrid.render(
                    metrics=[
                        {
                            "label": "Empresas Sincronizadas",
                            "value": len(state.available_companies),
                            "color": "var(--color-success)",
                        },
                        {
                            "label": "Última Sincronização",
                            "value": state.sync_status.last_sync.strftime("%d/%m/%Y %H:%M") if state.sync_status.last_sync else "Nunca",
                            "color": "var(--color-primary)",
                        },
                        {
                            "label": "Status",
                            "value": state.sync_status.status.value.capitalize(),
                            "color": "var(--color-warning)" if state.sync_status.status.value == "syncing" else "var(--color-success)",
                        },
                    ]
                ),
                
                # Rateio distribution chart
                rx.heading("Distribuição de Rateios", size="md", font_weight="bold"),
                RateioChart.render(
                    data=[
                        {
                            "centro_custo": "Centro 1",
                            "valor": 1000.50,
                            "percentual": 33.33,
                            "color": "#6366F1",
                        },
                        {
                            "centro_custo": "Centro 2",
                            "valor": 2000.75,
                            "percentual": 66.67,
                            "color": "#8B5CF6",
                        },
                    ]
                ),
                
                spacing="lg",
                width="100%",
                padding="lg",
            ),
            background_color="var(--color-background)",
            min_height="100vh",
        )


class AuditLogPage(rx.Component):
    """
    ORGANISM: Audit log viewer
    Shows all system events with filtering and search
    """
    tag = "div"
    
    @staticmethod
    def render():
        return rx.box(
            rx.vstack(
                # Header
                rx.heading("Registro de Auditoria", size="xl", font_weight="bold"),
                
                # Search and filter
                rx.hstack(
                    rx.input(
                        placeholder="Buscar por usuário ou ação...",
                        width="100%",
                    ),
                    rx.select(
                        values=["Todos", "Criação", "Atualização", "Exclusão"],
                        placeholder="Filtrar por tipo",
                    ),
                    width="100%",
                ),
                
                # Audit feed
                rx.box(
                    rx.vstack(
                        *[
                            AuditFeedItem.render(
                                action="Sincronização iniciada",
                                timestamp=rx.Var.create("now"),
                                user="Sistema",
                                details="1000 registros processados",
                            ),
                            AuditFeedItem.render(
                                action="Empresa atualizada",
                                timestamp=rx.Var.create("now"),
                                user="João Silva",
                                details="Empresa #123 - Centro de Custo adicionado",
                            ),
                            AuditFeedItem.render(
                                action="Relatório exportado",
                                timestamp=rx.Var.create("now"),
                                user="Maria Santos",
                                details="Período: Jan/2024 - Formato: PDF",
                            ),
                        ],
                        spacing="sm",
                    ),
                    border="1px solid var(--color-border)",
                    border_radius="lg",
                    padding="md",
                    max_height="600px",
                    overflow_y="auto",
                ),
                
                spacing="lg",
                width="100%",
                padding="lg",
            ),
            background_color="var(--color-background)",
            min_height="100vh",
        )


class SettingsPage(rx.Component):
    """
    ORGANISM: Settings/Configuration page
    User preferences, company settings, etc.
    """
    tag = "div"
    
    @staticmethod
    def render():
        state = GlobalState()
        
        return rx.box(
            rx.vstack(
                # Header
                rx.heading("Configurações", size="xl", font_weight="bold"),
                
                # Theme toggle
                rx.card(
                    rx.vstack(
                        rx.heading("Aparência", size="md"),
                        rx.hstack(
                            rx.text("Modo Escuro", flex="1"),
                            rx.checkbox(
                                checked=state.is_dark_mode,
                                on_change=rx.Var.create("on_theme_toggle"),
                            ),
                            width="100%",
                            justify_content="space-between",
                        ),
                        spacing="md",
                    )
                ),
                
                # Notification settings
                rx.card(
                    rx.vstack(
                        rx.heading("Notificações", size="md"),
                        rx.checkbox(
                            label="Notificar ao completar sincronização",
                            default_is_checked=True,
                        ),
                        rx.checkbox(
                            label="Alertas de erro",
                            default_is_checked=True,
                        ),
                        spacing="md",
                    )
                ),
                
                # User info
                rx.cond(
                    state.user is not None,
                    rx.card(
                        rx.vstack(
                            rx.heading("Informações do Usuário", size="md"),
                            rx.text(f"Nome: {state.user.name}"),
                            rx.text(f"Email: {state.user.email}"),
                            rx.text(f"Função: {state.user.role.value.capitalize()}"),
                            spacing="sm",
                        )
                    ),
                ),
                
                # Danger zone
                rx.box(
                    rx.vstack(
                        rx.heading("Zona de Perigo", size="md", color="var(--color-danger)"),
                        rx.button(
                            "Fazer Logout",
                            on_click=rx.Var.create("on_logout"),
                            color_scheme="red",
                        ),
                        spacing="md",
                    ),
                    border="1px solid var(--color-danger)",
                    border_radius="md",
                    padding="md",
                    background_color="rgba(239, 68, 68, 0.05)",
                ),
                
                spacing="lg",
                width="100%",
                max_width="800px",
                padding="lg",
            ),
            background_color="var(--color-background)",
            min_height="100vh",
        )
