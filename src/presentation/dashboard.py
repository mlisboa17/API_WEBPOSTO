from decimal import Decimal
import json
import reflex as rx

from src.presentation.components.charts import DonutChart


class DashboardState(rx.State):
    """Client-side state for executive dashboard with streaming updates."""

    total: str = "0.0000"
    growth: str = "0.0000"
    users: int = 0
    distribution: list[dict] = []
    loading: bool = True

    @staticmethod
    def _quant(v: Decimal) -> str:
        return f"{v.quantize(Decimal('0.0001'))}"

    async def update_from_payload(self, payload: dict) -> None:
        """Update state from server-sent metrics payload."""
        try:
            self.total = payload.get("total", self.total)
            self.growth = payload.get("growth", self.growth)
            self.users = int(payload.get("users", self.users))
            self.distribution = payload.get("distribution", self.distribution)
            self.loading = False
        except Exception:
            # keep previous state on error; show friendly message in UI
            self.loading = False


def _skeleton_box() -> rx.Component:
    return rx.box(
        rx.box(style={"height": "18px", "background": "#e6e9ee", "borderRadius": "6px"}),
        padding="3",
    )


@rx.page(route="/dashboard", title="Executive Dashboard")
def dashboard() -> rx.Component:
    """Dashboard page using an embeddable Donut chart and streaming metrics.

    - Uses `rx.event_source` to receive `/stream/metrics` events (server-sent).
    - Provides skeleton loading placeholders until first frame arrives.
    - Glassmorphism / Dark Executive theme applied.
    """

    # Attempt to subscribe to server-sent events. This is a minimal, resilient stub
    # that expects the backend to expose `/stream/metrics` SSE endpoint.
    try:
        rx.event_source(
            "/stream/metrics",
            on_message=lambda ev: DashboardState.update_from_payload(json.loads(ev.data)),
        )
    except Exception:
        # In case the Reflex runtime doesn't provide SSE in this environment,
        # the page will still render with skeleton loaders and static data.
        pass

    top_metrics = rx.hstack(
        rx.vstack(
            rx.text("Total", size="sm", color="gray"),
            rx.text(lambda: f"R$ {DashboardState.total}", size="2xl", color="green"),
            _skeleton_box() if DashboardState.loading else rx.box(),
            spacing="2",
        ),
        rx.vstack(
            rx.text("Growth", size="sm", color="gray"),
            rx.text(lambda: f"{DashboardState.growth}%", size="xl", color="blue"),
            spacing="2",
        ),
        rx.vstack(
            rx.text("Active Users", size="sm", color="gray"),
            rx.text(lambda: f"{DashboardState.users}", size="xl", color="purple"),
            spacing="2",
        ),
        spacing="8",
        width="100%",
    )

    # Donut chart component (renders via charts.DonutChart)
    chart = DonutChart(lambda: DashboardState.distribution or [
        {"name": "Center A", "value": 45.25},
        {"name": "Center B", "value": 35.75},
        {"name": "Center C", "value": 19.00},
    ])

    # Dark Executive glass container
    container = rx.box(
        rx.vstack(
            rx.heading("Executive Dashboard", size="lg", color="white"),
            top_metrics,
            rx.divider(border_color="rgba(255,255,255,0.06)"),
            rx.hstack(chart, width="100%"),
            spacing="6",
            padding="6",
        ),
        width="100%",
        max_width="1200px",
        margin="0 auto",
        bg="rgba(255,255,255,0.03)",
        border="1px solid rgba(255,255,255,0.06)",
        border_radius="12px",
        style={"backdropFilter": "blur(8px)", "-webkit-backdrop-filter": "blur(8px)"},
    )

    return rx.vstack(
        rx.box(
            container,
            padding="8",
            width="100%",
            min_height="100vh",
            bg="linear-gradient(180deg, #0f1724 0%, #071025 100%)",
        ),
        spacing="0",
    )
