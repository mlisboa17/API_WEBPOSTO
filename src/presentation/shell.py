import reflex as rx


class ThemeState(rx.State):
    sidebar_open: bool = True
    active_page: str = "dashboard"
    loading_progress: float = 0.0

    def set_active_page(self, page: str):
        self.active_page = page

    def set_loading(self, value: float):
        self.loading_progress = value

    @rx.var
    def progress_width(self) -> str:
        percent = max(0.0, min(self.loading_progress, 100.0))
        return f"{percent:.0f}%"

    @rx.var
    def page_title(self) -> str:
        return self.active_page.replace("-", " ").title()


def sidebar_item(icon: str, label: str, target: str, href: str = "#"):
    item = rx.hstack(
        rx.icon(icon, size=18),
        rx.vstack(
            rx.text(label, size="3", weight="medium"),
            rx.text("Executive lane", size="1", color="rgba(245,250,255,0.45)"),
            align_items="start",
            spacing="1",
        ),
        rx.spacer(),
        rx.badge(
            "Live" if target == "tax-audit" else "Core",
            style={
                "background": "rgba(0,245,255,0.10)",
                "color": "#98F9FF",
                "border": "1px solid rgba(0,245,255,0.18)",
            },
        ),
        cursor="pointer",
        padding="14px",
        border_radius="20px",
        bg=rx.cond(ThemeState.active_page == target, "rgba(0, 245, 255, 0.08)", "transparent"),
        color=rx.cond(ThemeState.active_page == target, "#F4FEFF", "#A9B3BF"),
        border=rx.cond(ThemeState.active_page == target, "1px solid rgba(0,245,255,0.24)", "1px solid transparent"),
        box_shadow=rx.cond(ThemeState.active_page == target, "0 0 28px rgba(0,245,255,0.12)", "none"),
        _hover={"bg": "rgba(255, 255, 255, 0.04)", "transform": "translateX(4px)", "color": "#FFFFFF"},
        transition="all 0.18s ease",
        width="100%",
        on_click=ThemeState.set_active_page(target),
    )
    return rx.link(item, href=href, width="100%", text_decoration="none")


def glass_card(title: str, value: str, footer: str, color="#00F5FF"):
    return rx.vstack(
        rx.text(title, size="2", color="#A0A0A0"),
        rx.heading(value, size="8", color="white"),
        rx.text(footer, size="1", color=color),
        padding="24px",
        bg="linear-gradient(180deg, rgba(255,255,255,0.05), rgba(255,255,255,0.02))",
        border="1px solid rgba(255, 255, 255, 0.06)",
        border_radius="24px",
        box_shadow=f"0 0 0 1px {color}12 inset, 0 14px 48px rgba(0,0,0,0.34), 0 0 26px rgba(0,245,255,0.08)",
        _hover={"border": f"1px solid {color}", "bg": "rgba(255, 255, 255, 0.06)", "transform": "translateY(-2px)"},
        transition="all 0.3s ease",
        align_items="start",
        width="100%",
    )


def top_progress_bar():
    return rx.box(
        rx.box(
            height="3px",
            width=ThemeState.progress_width,
            background="linear-gradient(90deg, rgba(0,245,255,0.95), rgba(132,245,255,0.85), rgba(0,255,127,0.65))",
            transition="width 0.25s linear",
            position="fixed",
            top="0",
            left="0",
            z_index="9999",
            box_shadow="0 0 24px rgba(0,245,255,0.45)",
        ),
    )


def main_shell(content: rx.Component):
    return rx.box(
        top_progress_bar(),
        rx.hstack(
            rx.vstack(
                rx.text("LOGOS SPACE", size="2", color="rgba(255,255,255,0.50)", letter_spacing="0.24em"),
                rx.heading("Executive Glass", size="7", color="#9BF8FF", padding_y="2"),
                rx.text("Comando tributário em tempo real para operações multi-tenant.", size="2", color="#8B97A3"),
                rx.divider(opacity=0.10, margin_y="8px"),
                sidebar_item("layout-dashboard", "Dashboard", "dashboard", href="/dashboard"),
                sidebar_item("shield-check", "Auditoria Tributária", "tax", href="/audit"),
                sidebar_item("sparkles", "Adelaide", "tax-audit", href="/tax-audit"),
                sidebar_item("trending-up", "Análise de Margem", "margin", href="#"),
                rx.spacer(),
                rx.box(
                    rx.text("Runtime", size="1", color="rgba(255,255,255,0.45)"),
                    rx.heading("Posto Casa Caiada", size="4", color="white"),
                    rx.text("PE • Lucro Real • SSE ativo", size="2", color="#9DEEFF"),
                    padding="18px",
                    border_radius="22px",
                    background="linear-gradient(180deg, rgba(255,255,255,0.08), rgba(255,255,255,0.02))",
                    border="1px solid rgba(0,245,255,0.14)",
                    box_shadow="0 0 24px rgba(0,245,255,0.08)",
                    width="100%",
                ),
                sidebar_item("settings", "Configurações", "settings", href="#"),
                width="280px",
                height="96vh",
                bg="rgba(12, 14, 16, 0.68)",
                backdrop_filter="blur(20px)",
                border="1px solid rgba(255, 255, 255, 0.08)",
                padding="20px",
                margin="2vh",
                border_radius="30px",
                box_shadow="0 10px 60px rgba(0, 0, 0, 0.32), 0 0 30px rgba(0,245,255,0.08)",
            ),
            rx.vstack(
                rx.hstack(
                    rx.vstack(
                        rx.text("Adelaide Command Center", size="1", color="rgba(255,255,255,0.48)", letter_spacing="0.18em"),
                        rx.heading(ThemeState.page_title, size="6"),
                        align_items="start",
                        spacing="1",
                    ),
                    rx.spacer(),
                    rx.badge("90 dias", style={"background": "rgba(255,255,255,0.06)", "color": "#EAFDFF"}),
                    rx.badge("SSE online", style={"background": "rgba(0,245,255,0.10)", "color": "#9BF8FF"}),
                    rx.avatar(fallback="ML", size="3"),
                    width="100%",
                    padding_y="6",
                    padding_x="10",
                ),
                rx.box(
                    content,
                    width="100%",
                    padding_x="10",
                    padding_y="4",
                ),
                flex="1",
                height="100vh",
                overflow_y="auto",
            ),
            spacing="0",
        ),
        bg="#050506",
        color="white",
        min_height="100vh",
        font_family="'Space Grotesk', 'IBM Plex Sans', sans-serif",
        style={
            "background_image": "radial-gradient(circle at top right, rgba(0,245,255,0.10), transparent 28%), radial-gradient(circle at left 20%, rgba(255,255,255,0.04), transparent 18%), linear-gradient(180deg, #050506, #07090B)",
        },
    )


__all__ = ["ThemeState", "sidebar_item", "glass_card", "main_shell"]
