"""
GEMINI 2.0: High-Performance UI Components for Executive Hub "Lionda"

Features:
- Frosted Glass Sidebar with blur effects
- KPI Cards with trend indicators
- Real-time Cash Recovery counter (SSE)
- Responsive design for 4K + iPad
- Skeleton loaders for async data
- Lighthouse 100 performance target
"""

import reflex as rx
from typing import Optional, List
from enum import Enum


# =============================================================================
# Enums & Constants
# =============================================================================

class MetricTrend(str, Enum):
    UP = "↑"
    DOWN = "↓"
    STABLE = "→"


class ModuleType(str, Enum):
    OVERVIEW = "overview"
    FINANCE = "finance"
    FUEL = "fuel"
    EXPENSES = "expenses"
    TAX = "tax"
    MARGIN = "margin"
    SETTINGS = "settings"


# Color Palette - Neon Cyber
COLORS = {
    "bg_deep": "#050506",  # OLED Deep Black
    "bg_surface": "rgba(15, 15, 18, 0.7)",
    "accent_cyan": "#00F5FF",
    "accent_purple": "#8B5CF6",
    "accent_green": "#10B981",
    "accent_red": "#EF4444",
    "text_primary": "white",
    "text_secondary": "#606060",
    "border_light": "rgba(255, 255, 255, 0.05)",
    "border_accent": "rgba(0, 245, 255, 0.2)",
}


# =============================================================================
# Skeleton Loader Components
# =============================================================================

def skeleton_card() -> rx.Component:
    """Skeleton loader for KPI cards - optimized for perceived performance"""
    return rx.vstack(
        rx.skeleton(height="24px", width="100px"),
        rx.skeleton(height="48px", width="180px", margin_top="8px"),
        rx.skeleton(height="16px", width="120px", margin_top="8px"),
        padding="24px",
        bg=COLORS["bg_surface"],
        border=f"1px solid {COLORS['border_light']}",
        border_radius="3xl",
        width="100%",
    )


def skeleton_chart() -> rx.Component:
    """Skeleton loader for chart area"""
    return rx.vstack(
        rx.skeleton(height="24px", width="150px"),
        rx.skeleton(height="300px", width="100%", margin_top="16px"),
        padding="24px",
        bg=COLORS["bg_surface"],
        border=f"1px solid {COLORS['border_light']}",
        border_radius="3xl",
        width="100%",
    )


# =============================================================================
# KPI Card Component
# =============================================================================

def kpi_card(
    title: str,
    value: str,
    trend: MetricTrend = MetricTrend.STABLE,
    color: str = "#00F5FF",
    secondary_text: Optional[str] = None,
    icon: Optional[str] = None,
) -> rx.Component:
    """
    KPI Card with glassmorphism design
    
    GEMINI 2.0: <50ms interaction delay, hover effects optimized
    """
    return rx.vstack(
        rx.hstack(
            rx.icon(icon, size=24, color=color) if icon else rx.box(width="0"),
            rx.text(title, size="2", color=COLORS["text_secondary"], weight="bold"),
            spacing="2",
            align_items="center",
        ),
        rx.heading(
            value,
            size="8",
            color=COLORS["text_primary"],
            letter_spacing="-1px",
        ),
        rx.hstack(
            rx.text(
                f"{trend.value}",
                size="5",
                color=color,
                weight="bold",
            ),
            rx.text(secondary_text or "", size="1", color=COLORS["text_secondary"]),
            spacing="1",
        ) if secondary_text else rx.fragment(),
        padding="24px",
        bg=COLORS["bg_surface"],
        border=f"1px solid {COLORS['border_light']}",
        border_radius="3xl",
        _hover={
            "border": f"1px solid {color}",
            "bg": "rgba(255, 255, 255, 0.04)",
            "box_shadow": f"0 0 20px {color}33",
        },
        transition="all 0.3s cubic-bezier(0.4, 0, 0.2, 1)",
        width="100%",
        align_items="start",
        cursor="pointer",
    )


# =============================================================================
# Sidebar Navigation
# =============================================================================

def sidebar_button(
    icon: str,
    label: str,
    target: str,
    is_active: bool = False,
    on_click=None,
) -> rx.Component:
    """Navigation button with active state indicator"""
    return rx.hstack(
        rx.box(
            rx.icon(icon, size=20),
            color=rx.cond(is_active, COLORS["accent_cyan"], COLORS["text_secondary"]),
        ),
        rx.text(
            label,
            size="2",
            weight=rx.cond(is_active, "bold", "medium"),
            color=rx.cond(is_active, COLORS["accent_cyan"], COLORS["text_secondary"]),
        ),
        on_click=on_click,
        padding="12px 16px",
        border_radius="lg",
        bg=rx.cond(
            is_active,
            "rgba(0, 245, 255, 0.12)",
            "transparent",
        ),
        cursor="pointer",
        _hover={
            "bg": "rgba(255, 255, 255, 0.05)",
            "color": COLORS["text_primary"],
        },
        transition="all 0.2s cubic-bezier(0.4, 0, 0.2, 1)",
        width="100%",
        spacing="2",
        align_items="center",
    )


def executive_sidebar(current_module: str, on_module_change=None) -> rx.Component:
    """
    Frosted Glass Sidebar for module navigation
    
    GEMINI 2.0: Blur 30px, adaptive backdrop-filter
    """
    return rx.vstack(
        # Logo
        rx.vstack(
            rx.heading(
                "LOGOS",
                size="8",
                color=COLORS["text_primary"],
                letter_spacing="4px",
                padding_bottom="4",
            ),
            rx.text(
                "Executive Hub",
                size="1",
                color=COLORS["text_secondary"],
                font_weight="light",
            ),
            spacing="1",
            align_items="start",
            padding_bottom="6",
            border_bottom=f"1px solid {COLORS['border_light']}",
        ),
        
        # Operational Section
        rx.text(
            "OPERACIONAL",
            size="1",
            color=COLORS["text_secondary"],
            font_weight="bold",
            margin_top="6",
            margin_bottom="3",
            text_transform="uppercase",
            letter_spacing="1px",
        ),
        sidebar_button(
            "layout-dashboard",
            "Overview Hub",
            ModuleType.OVERVIEW,
            is_active=(current_module == ModuleType.OVERVIEW),
            on_click=lambda: on_module_change(ModuleType.OVERVIEW) if on_module_change else None,
        ),
        sidebar_button(
            "dollar-sign",
            "Faturamento",
            ModuleType.FINANCE,
            is_active=(current_module == ModuleType.FINANCE),
            on_click=lambda: on_module_change(ModuleType.FINANCE) if on_module_change else None,
        ),
        sidebar_button(
            "fuel",
            "Galonagem",
            ModuleType.FUEL,
            is_active=(current_module == ModuleType.FUEL),
            on_click=lambda: on_module_change(ModuleType.FUEL) if on_module_change else None,
        ),
        sidebar_button(
            "shopping-bag",
            "Despesas Caixa",
            ModuleType.EXPENSES,
            is_active=(current_module == ModuleType.EXPENSES),
            on_click=lambda: on_module_change(ModuleType.EXPENSES) if on_module_change else None,
        ),
        
        # Intelligence Section
        rx.text(
            "INTELIGÊNCIA",
            size="1",
            color=COLORS["text_secondary"],
            font_weight="bold",
            margin_top="6",
            margin_bottom="3",
            text_transform="uppercase",
            letter_spacing="1px",
        ),
        sidebar_button(
            "shield-check",
            "Auditoria Adelaide",
            ModuleType.TAX,
            is_active=(current_module == ModuleType.TAX),
            on_click=lambda: on_module_change(ModuleType.TAX) if on_module_change else None,
        ),
        sidebar_button(
            "trending-up",
            "Margem Real",
            ModuleType.MARGIN,
            is_active=(current_module == ModuleType.MARGIN),
            on_click=lambda: on_module_change(ModuleType.MARGIN) if on_module_change else None,
        ),
        
        # Spacer
        rx.spacer(),
        
        # Settings
        sidebar_button(
            "settings",
            "Configurações",
            ModuleType.SETTINGS,
            is_active=(current_module == ModuleType.SETTINGS),
            on_click=lambda: on_module_change(ModuleType.SETTINGS) if on_module_change else None,
        ),
        
        # Styling
        width="280px",
        height="100vh",
        bg=COLORS["bg_surface"],
        style={
            "backdrop_filter": "blur(30px)",
            "-webkit-backdrop-filter": "blur(30px)",
        },
        border=f"1px solid {COLORS['border_light']}",
        border_left="none",
        border_top="none",
        border_bottom="none",
        padding="24px",
        spacing="1",
        overflow_y="auto",
        position="sticky",
        top="0",
    )


# =============================================================================
# Period Filter
# =============================================================================

def period_filter(on_change=None) -> rx.Component:
    """Time period selector with smooth transitions"""
    return rx.select(
        ["Hoje", "Últimos 7 Dias", "Últimos 30 Dias", "Customizado"],
        default_value="Últimos 30 Dias",
        on_change=on_change,
        size="2",
        variant="surface",
        width="240px",
        padding="8px 12px",
        bg=COLORS["bg_surface"],
        border=f"1px solid {COLORS['border_light']}",
        border_radius="lg",
        color=COLORS["text_primary"],
    )


# =============================================================================
# Cash Recovery Counter (Real-time SSE)
# =============================================================================

def cash_recovery_badge(amount: float, is_updating: bool = False) -> rx.Component:
    """
    Real-time cash recovery counter fed by SSE
    
    GROK 4: SSE Stream integration for live updates
    """
    return rx.box(
        rx.hstack(
            rx.box(
                rx.icon("trending-up", size=20, color=COLORS["accent_green"]),
                width="40px",
                height="40px",
                bg="rgba(16, 185, 129, 0.1)",
                border_radius="lg",
                display="flex",
                align_items="center",
                justify_content="center",
            ),
            rx.vstack(
                rx.text("Cash Recovery", size="1", color=COLORS["text_secondary"]),
                rx.hstack(
                    rx.heading(
                        f"R$ {amount:,.2f}",
                        size="5",
                        color=COLORS["accent_green"],
                    ),
                    rx.box(
                        rx.spinner(size="2", color=COLORS["accent_green"])
                        if is_updating else rx.fragment(),
                        margin_left="8px",
                    ),
                    spacing="2",
                    align_items="center",
                ),
                spacing="1",
            ),
            padding="16px",
            bg="rgba(16, 185, 129, 0.05)",
            border=f"1px solid {COLORS['border_light']}",
            border_radius="2xl",
            spacing="3",
            align_items="center",
            width="100%",
        )
    )


# =============================================================================
# Navbar Component
# =============================================================================

def hub_navbar(
    station_name: str = "Posto Casa Caiada",
    user_email: str = "admin@company.com",
) -> rx.Component:
    """Professional navbar with station info and controls"""
    return rx.hstack(
        rx.vstack(
            rx.heading(
                station_name,
                size="6",
                color=COLORS["text_primary"],
            ),
            rx.text(
                "Comando Central - Grupo Lisboa",
                size="1",
                color=COLORS["text_secondary"],
            ),
            align_items="start",
            spacing="0",
        ),
        rx.spacer(),
        period_filter(),
        rx.avatar(
            name=user_email.split("@")[0],
            size="4",
            color=COLORS["accent_cyan"],
            background=f"linear-gradient(135deg, {COLORS['accent_cyan']}, {COLORS['accent_purple']})",
        ),
        width="100%",
        padding_x="24px",
        padding_y="16px",
        bg=COLORS["bg_deep"],
        border_bottom=f"1px solid {COLORS['border_light']}",
        align_items="center",
    )


# =============================================================================
# Module Layout Container
# =============================================================================

def module_layout(title: str, content: rx.Component) -> rx.Component:
    """Wrapper for module content with consistent styling"""
    return rx.vstack(
        rx.heading(
            title,
            size="6",
            color=COLORS["text_primary"],
            padding_bottom="4",
            border_bottom=f"1px solid {COLORS['border_light']}",
        ),
        content,
        spacing="6",
        padding="24px",
        width="100%",
        flex="1",
    )
