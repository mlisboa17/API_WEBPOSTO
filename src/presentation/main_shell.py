import reflex as rx
from typing import Callable


def sidebar(collapse: bool = False) -> rx.Component:
    return rx.box(
        rx.vstack(
            rx.heading("Logos", size="3", color="indigo"),
            rx.divider(),
            rx.link(rx.button("Dashboard", size="3"), href="/dashboard"),
            rx.link(rx.button("Audit", size="3"), href="/audit"),
            rx.link(rx.button("Margins", size="3"), href="/margins"),
            spacing="3",
        ),
        width="220px" if not collapse else "72px",
        bg="linear-gradient(180deg,#0f172a, #06303a)",
        color="white",
        padding="3",
        box_shadow="md",
        style={"backdropFilter": "blur(8px)"},
    )


def navbar() -> rx.Component:
    return rx.hstack(
        rx.hstack(
            rx.heading("WebPosto", size="3", color="white"),
            rx.text("Executive Dashboard", size="8", color="gray"),
            spacing="3",
        ),
        rx.spacer(),
        rx.hstack(
            rx.icon(name="lucide/Search", size=18),
            rx.icon(name="lucide/Bell", size=18),
            rx.avatar(size="sm"),
            spacing="2",
        ),
        padding="3",
        bg="transparent",
        style={"backdropFilter": "blur(6px)", "borderBottom": "1px solid rgba(255,255,255,0.04)"},
    )


def shell(content: Callable[[], rx.Component], collapse_sidebar: bool = False) -> rx.Component:
    """Main app shell: sidebar + navbar + dynamic slot"""
    return rx.hstack(
        sidebar(collapse_sidebar),
        rx.vstack(
            navbar(),
            rx.box(
                rx.motion.div(
                    content(),
                    animate={"opacity": 1, "y": 0, "scale": 1},
                    initial={"opacity": 0, "y": 8, "scale": 0.98},
                    transition={"duration": 0.28},
                ),
                padding="4",
                width="100%",
            ),
        ),
        width="100%",
        spacing="0",
        bg="linear-gradient(135deg,#071233,#062b20)",
    )


__all__ = ["sidebar", "navbar", "shell"]
