"""
🏢 SHELL CORPORATIVO LIONDA - Executive Hub Premium
Design Glassmorphism OLED + Adelaide AI Intelligence

Responsabilidades:
- Navigation SPA (home, tax, margin, audit)
- Glassmorphic sidebar com blur 30px
- Real-time KPI badges via SSE
- Persistence de contexto via Valkey
"""
import reflex as rx
from typing import Optional


class GlobalState(rx.State):
    """Estado Mestre de Navegação e Contexto Adelaide"""
    
    # Navigation
    current_module: str = "home"  # home, tax, margin, audit
    
    # Station Context (persist in Valkey)
    station_name: str = "Posto Casa Caiada"
    station_cnpj: str = "12.345.678/0001-99"
    station_regime: str = "LUCRO_REAL"
    station_cnae: str = "4731800"
    station_uf: str = "PE"
    
    # UI State
    is_syncing: bool = False
    sidebar_collapsed: bool = False
    last_sync_ts: str = ""
    
    # Real-time KPIs (updated via SSE)
    kpi_recovery_estimated: float = 0.0
    kpi_risk_score: int = 0
    kpi_findings_count: int = 0
    
    def set_module(self, module: str):
        """Navegar para módulo (persiste contexto)"""
        self.current_module = module
    
    def toggle_sidebar(self):
        """Colapsar/expandir sidebar"""
        self.sidebar_collapsed = not self.sidebar_collapsed
    
    def set_station_context(self, cnpj: str, regime: str, cnae: str, uf: str, name: str = ""):
        """Atualizar contexto do Posto (DDD pattern)"""
        self.station_cnpj = cnpj
        self.station_regime = regime
        self.station_cnae = cnae
        self.station_uf = uf
        if name:
            self.station_name = name
    
    def start_sync(self):
        """Iniciar sincronização com backend Adelaide"""
        self.is_syncing = True
        return rx.call_script(
            f"window.startAdelaideSync('{self.station_cnpj}', '{self.station_regime}')"
        )
    
    @rx.var
    def sidebar_width(self) -> str:
        return "48px" if self.sidebar_collapsed else "280px"
    
    @rx.var
    def content_margin(self) -> str:
        return "ml-12" if self.sidebar_collapsed else "ml-72"


def sidebar_button(icon: str, label: str, target: str, badge_text: str = ""):
    """Botão de navegação sidebar com badge inteligente"""
    is_active = GlobalState.current_module == target
    
    return rx.hstack(
        rx.icon(icon, size=24, color=rx.cond(is_active, "#00F5FF", "#606060")),
        rx.cond(
            GlobalState.sidebar_collapsed,
            rx.box(height="0"),  # Hidden when collapsed
            rx.vstack(
                rx.text(label, size="3", weight="bold" if is_active else "medium"),
                rx.text(badge_text, size="1", color="#808080") if badge_text else rx.box(),
                align_items="start",
                spacing="1",
            ),
        ),
        rx.spacer(),
        rx.cond(
            GlobalState.sidebar_collapsed,
            rx.box(),
            rx.badge(
                "LIVE" if target == "tax" else "Ready",
                color_scheme=rx.cond(is_active, "cyan", "gray"),
                variant="soft",
                padding_x="2",
            ),
        ),
        on_click=lambda: GlobalState.set_module(target),
        padding="16px",
        border_radius="xl",
        bg=rx.cond(is_active, "rgba(0, 245, 255, 0.12)", "transparent"),
        color=rx.cond(is_active, "#F4FEFF", "#808080"),
        cursor="pointer",
        _hover={
            "bg": "rgba(255, 255, 255, 0.06)",
            "color": "#00F5FF",
            "transform": "translateX(4px) scaleY(1.02)",
        },
        transition="all 0.2s cubic-bezier(0.34, 1.56, 0.64, 1)",
        width="100%",
        box_shadow=rx.cond(
            is_active,
            "0 0 32px rgba(0, 245, 255, 0.15), inset 0 0 24px rgba(0, 245, 255, 0.08)",
            "none",
        ),
    )


def kpi_card(title: str, value: str, unit: str, trend: str = "↑ 12%", color: str = "#00F5FF"):
    """Card KPI com glassmorphism e animação"""
    return rx.box(
        rx.vstack(
            rx.hstack(
                rx.text(title, size="2", color="#A0A0A0", weight="medium"),
                rx.badge(trend, color_scheme="green", variant="soft", padding_x="2"),
                justify="between",
                width="100%",
            ),
            rx.hstack(
                rx.heading(value, size="6", color=color, letter_spacing="-2px"),
                rx.text(unit, size="3", color="#808080", weight="medium"),
                align_items="end",
            ),
            spacing="4",
        ),
        padding="20px",
        bg="rgba(255, 255, 255, 0.03)",
        border="1px solid rgba(255, 255, 255, 0.08)",
        border_radius="2xl",
        backdrop_filter="blur(25px)",
        box_shadow="0 8px 32px rgba(0, 0, 0, 0.3)",
        _hover={
            "bg": "rgba(255, 255, 255, 0.06)",
            "border": "1px solid rgba(0, 245, 255, 0.2)",
            "box_shadow": f"0 0 32px rgba(0, 245, 255, 0.1), inset 0 0 24px rgba({color}, 0.05)",
        },
        transition="all 0.3s ease-in-out",
        cursor="pointer",
    )


def status_banner():
    """Banner de status com animação pulsante"""
    return rx.box(
        rx.hstack(
            rx.box(
                width="8px",
                height="8px",
                bg="#00F5FF",
                border_radius="50%",
                animation="pulse 2s cubic-bezier(0.4, 0, 0.6, 1) infinite",
            ),
            rx.text(
                "Adelaide AI Online • " + GlobalState.last_sync_ts,
                size="2",
                color="#A0A0A0",
            ),
            rx.spacer(),
            rx.button(
                "Sincronizar",
                on_click=GlobalState.start_sync,
                color_scheme="cyan",
                variant="soft",
                size="1",
                is_loading=GlobalState.is_syncing,
            ),
            width="100%",
            padding="12px 16px",
        ),
        bg="rgba(0, 245, 255, 0.05)",
        border="1px solid rgba(0, 245, 255, 0.12)",
        border_radius="lg",
        margin_bottom="4",
    )


def navbar():
    """Top navigation bar executiva"""
    return rx.hstack(
        rx.vstack(
            rx.text(
                GlobalState.current_module.upper(),
                size="2",
                color="#606060",
                weight="medium",
            ),
            rx.heading(GlobalState.station_name, size="5", letter_spacing="-1px"),
            align_items="start",
            spacing="1",
        ),
        rx.spacer(),
        rx.hstack(
            rx.badge(f"CNPJ: {GlobalState.station_cnpj}", variant="soft"),
            rx.badge(f"UF: {GlobalState.station_uf}", color_scheme="cyan", variant="soft"),
            rx.badge(
                "ADELAIDE AI ACTIVE",
                color_scheme="cyan",
                variant="solid",
                animation="pulse 2s cubic-bezier(0.4, 0, 0.6, 1) infinite",
            ),
            rx.avatar(fallback="ML", size="3", border="2px solid #00F5FF"),
            spacing="4",
        ),
        width="100%",
        padding="16px 20px",
        bg="rgba(255, 255, 255, 0.02)",
        border_bottom="1px solid rgba(255, 255, 255, 0.08)",
    )


def main_executive_shell(content: rx.Component):
    """
    🏢 MAIN SHELL - Orquestra toda navegação corporativa
    
    Args:
        content: Componente da página ativa (home, tax, margin, audit)
    
    Returns:
        rx.Component: Shell completo com sidebar + navbar + conteúdo
    """
    return rx.box(
        rx.script(
            """
            @keyframes pulse {
                0%, 100% { opacity: 1; }
                50% { opacity: 0.5; }
            }
            @keyframes fadeInUp {
                0% { opacity: 0; transform: translateY(20px); }
                100% { opacity: 1; transform: translateY(0); }
            }
            @keyframes slideInLeft {
                0% { opacity: 0; transform: translateX(-20px); }
                100% { opacity: 1; transform: translateX(0); }
            }
            """
        ),
        rx.hstack(
            # ╔═══════════════════════════════════════════════════════════╗
            # ║          SIDEBAR EXECUTIVO (Glassmorphism)                ║
            # ╚═══════════════════════════════════════════════════════════╝
            rx.vstack(
                # Logo + Branding
                rx.hstack(
                    rx.box(
                        width="32px",
                        height="32px",
                        bg="linear-gradient(135deg, #00F5FF, #7000FF)",
                        border_radius="xl",
                    ),
                    rx.cond(
                        GlobalState.sidebar_collapsed,
                        rx.box(),
                        rx.vstack(
                            rx.heading(
                                "LOGOS",
                                size="6",
                                color="white",
                                letter_spacing="2px",
                                margin="0",
                            ),
                            rx.text("SPACE", size="1", color="#606060", letter_spacing="1px"),
                            spacing="0",
                        ),
                    ),
                    width="100%",
                    padding_y="8px",
                    spacing="3",
                ),
                rx.divider(border_color="rgba(255, 255, 255, 0.06)"),
                
                # Navigation Items
                sidebar_button("home", "Overview", "home", "Dashboard"),
                sidebar_button("shield-alert", "Auditoria Adelaide", "tax", "Intel"),
                sidebar_button("trending-up", "Margem Real", "margin", "Analytics"),
                sidebar_button("file-text", "Tributos", "audit", "Reports"),
                
                rx.spacer(),
                rx.divider(border_color="rgba(255, 255, 255, 0.06)"),
                
                # Settings
                sidebar_button("settings", "Config", "settings", "Admin"),
                
                width=GlobalState.sidebar_width,
                height="100vh",
                bg="rgba(5, 5, 6, 0.8)",
                backdrop_filter="blur(30px)",
                border_right="1px solid rgba(255, 255, 255, 0.05)",
                padding="20px 12px",
                spacing="3",
                position="sticky",
                top="0",
                overflow_y="auto",
                transition="width 0.3s ease-in-out",
            ),
            
            # ╔═══════════════════════════════════════════════════════════╗
            # ║             MAIN CONTENT AREA (Dynamic Pages)              ║
            # ╚═══════════════════════════════════════════════════════════╝
            rx.vstack(
                navbar(),
                status_banner(),
                
                # Dynamic Page Content
                rx.box(
                    content,
                    width="100%",
                    flex="1",
                    padding="20px",
                    overflow_y="auto",
                    animation="fadeInUp 0.4s ease-out",
                ),
                
                flex="1",
                height="100vh",
                spacing="0",
            ),
            
            spacing="0",
            width="100%",
        ),
        
        # Global Background
        bg="#050506",
        min_height="100vh",
        color="white",
        font_family="'Inter', sans-serif",
    )


# ═══════════════════════════════════════════════════════════════════
# PROXY FUNCTION: Para compatibilidade com pages.py
# ═══════════════════════════════════════════════════════════════════
def executive_shell_wrapper(content: rx.Component = None):
    """Wrapper para compatibilidade com routing existente"""
    if content is None:
        content = rx.vstack(
            rx.heading("Hub Executivo", size="1"),
            rx.text("Selecione um módulo à esquerda", color="#A0A0A0"),
        )
    return main_executive_shell(content)
