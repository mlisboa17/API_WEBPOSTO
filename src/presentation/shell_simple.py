"""
🏢 SHELL MÍNIMO - Debug version
Eliminando todas features complexas para testar renderização básica
"""
import reflex as rx


class GlobalStateSimple(rx.State):
    """Estado mínimo"""
    current_module: str = "home"


def main_executive_shell_simple(content: rx.Component):
    """Shell ultrasimples"""
    return rx.box(
        rx.vstack(
            rx.heading("LOGOS SPACE", size="4"),
            content,
            spacing="4",
            padding="20px",
        ),
        bg="#050506",
        color="white",
        min_height="100vh",
    )
