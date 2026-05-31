"""
🏠 HOME MODULE - Versão Simplificada para Debug
Eliminando componentes complexos que podem causar "render is not a function"
"""
import reflex as rx


def home_module_simple():
    """Versão minimalista para testar renderização"""
    return rx.vstack(
        rx.heading("🏠 Hub Executivo", size="4"),
        rx.text("Bem-vindo ao LOGOS Space", size="2", color="#A0A0A0"),
        spacing="4",
        width="100%",
    )
