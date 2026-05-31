"""
🏠 HOME MODULE - Executive Overview Dashboard
Consolidada view de todos 3 módulos com KPIs in tempo real
"""
import reflex as rx
from src.presentation.shell_corporate import GlobalState, kpi_card


def module_status_card(module_name: str, status: str, icon: str):
    """Card de status de um módulo"""
    color = "#00F5FF" if status == "ready" else "#FFB84D"
    
    return rx.vstack(
        rx.hstack(
            rx.icon(icon, size=32, color=color),
            rx.vstack(
                rx.text(module_name, size="4", weight="bold"),
                rx.badge(
                    status.upper(),
                    color_scheme=rx.cond(
                        status == "ready",
                        "green",
                        "orange",
                    ),
                    variant="soft",
                    padding_x="2",
                ),
                spacing="1",
            ),
            width="100%",
            justify="between",
        ),
        padding="16px",
        bg="rgba(255, 255, 255, 0.04)",
        border="1px solid rgba(255, 255, 255, 0.08)",
        border_radius="xl",
        _hover={
            "bg": "rgba(255, 255, 255, 0.06)",
            "border": f"1px solid {color}44",
        },
        cursor="pointer",
        transition="all 0.3s ease",
    )


def home_module():
    """Página HOME: Overview Executivo Consolidado"""
    return rx.vstack(
        # HEADER
        rx.heading(
            "Executive Dashboard",
            size="4",
            letter_spacing="-1px",
        ),
        rx.text(
            "Visão consolidada de auditoria, margens e tributos",
            size="2",
            color="#A0A0A0",
        ),
        
        # KPI CARDS (3 colunas)
        rx.grid(
            kpi_card(
                "Crédito Recuperável",
                "R$ 93,48",
                "mil",
                trend="↑ 12%",
                color="#00F5FF",
            ),
            kpi_card(
                "Risk Score",
                "81",
                "crítico",
                trend="↓ 8%",
                color="#FFB84D",
            ),
            kpi_card(
                "Findings",
                "25",
                "itens",
                trend="→",
                color="#7000FF",
            ),
            columns="3",
            spacing="4",
            width="100%",
        ),
        
        # MODULE STATUS
        rx.vstack(
            rx.heading("Status dos Módulos", size="3", letter_spacing="-1px"),
            rx.grid(
                module_status_card("Auditoria Adelaide", "ready", "shield-alert"),
                module_status_card("Margem Real", "ready", "trending-up"),
                module_status_card("Análise Tributária", "ready", "file-text"),
                columns="3",
                spacing="4",
                width="100%",
            ),
            spacing="4",
            width="100%",
        ),
        
        # QUICK ACTIONS
        rx.vstack(
            rx.heading("Ações Rápidas", size="3", letter_spacing="-1px"),
            rx.hstack(
                rx.button(
                    "🔄 Sincronizar Tudo",
                    on_click=GlobalState.start_sync,
                    is_loading=GlobalState.is_syncing,
                    size="3",
                    color_scheme="cyan",
                ),
                rx.button(
                    "📊 Exportar Report",
                    size="3",
                    variant="outline",
                ),
                rx.button(
                    "⚙️ Configurações",
                    size="3",
                    variant="soft",
                ),
                spacing="4",
            ),
            spacing="4",
            width="100%",
        ),
        
        spacing="8",
        width="100%",
        animation="fadeInUp 0.4s ease-out",
    )
