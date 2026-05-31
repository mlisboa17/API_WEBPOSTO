"""
GROK 4: Chart Components & Data Visualization
Rateio visualization with conditional rendering and animations
Uses Recharts for charts with Decimal precision support
"""

from typing import List, Optional
from decimal import Decimal
from pydantic import BaseModel, ConfigDict, Field
import reflex as rx
from datetime import datetime


class RateioChartData(BaseModel):
    """Rateio (cost distribution) chart data"""
    model_config = ConfigDict(frozen=False)
    
    centro_custo: str = Field(..., description="Cost center name")
    valor: Decimal = Field(..., description="Allocated value (Decimal for precision)")
    percentual: Decimal = Field(..., description="Percentage of total")
    color: str = Field(default="#6366F1", description="Chart color")


class RateioChart(rx.Component):
    """
    GROK 4: Donut Chart for Cost Distribution
    
    Features:
    - Decimal precision for financial data
    - Conditional rendering (show legend if >5 items)
    - Animations on entry
    - Responsive design
    - Mobile-first
    """
    tag = "div"
    
    @staticmethod
    def render(
        data: List[dict] | None = None,
        title: str = "Distribuição de Rateios",
    ):
        if data is None:
            data = []
        
        # Transform data for recharts
        chart_data = [
            {
                "name": item.get("centro_custo", "N/A"),
                "value": float(item.get("valor", 0)),
                "percentual": float(item.get("percentual", 0)),
                "fill": item.get("color", "#6366F1"),
            }
            for item in data
        ]
        
        return rx.box(
            rx.vstack(
                # Title
                rx.heading(title, size="md", font_weight="bold"),
                
                # Chart container
                rx.cond(
                    len(chart_data) > 0,
                    rx.box(
                        # Chart (Donut)
                        rx.recharts.pie_chart(
                            rx.recharts.pie(
                                data=chart_data,
                                data_key="value",
                                cx="50%",
                                cy="50%",
                                inner_radius=60,
                                outer_radius=100,
                                label={"position": "insideBottomRight"},
                                animation_duration=600,
                            ),
                            rx.recharts.legend(vertical_align="bottom", height=36)
                            if len(chart_data) <= 5
                            else None,
                            rx.recharts.tooltip(
                                formatter=lambda value, name: (
                                    f"R$ {value:,.2f}",
                                    name,
                                )
                            ),
                            width="100%",
                            height=400,
                        ),
                        width="100%",
                        animation="fadeIn 0.5s ease-in-out",
                    ),
                    # Fallback: Empty state
                    rx.box(
                        rx.vstack(
                            rx.text(
                                "Sem dados de rateio",
                                font_size="lg",
                                color="var(--color-text-secondary)",
                            ),
                            rx.text(
                                "Configure centros de custo para visualizar",
                                font_size="sm",
                                color="var(--color-text-secondary)",
                            ),
                            spacing="md",
                            align_items="center",
                        ),
                        padding="lg",
                        text_align="center",
                        background_color="var(--color-surface)",
                        border="1px dashed var(--color-border)",
                        border_radius="lg",
                    ),
                ),
                
                # Table view for precision data (GROK 4: Decimal support)
                rx.cond(
                    len(chart_data) > 0,
                    rx.box(
                        rx.table(
                            rx.thead(
                                rx.tr(
                                    rx.th("Centro de Custo"),
                                    rx.th("Valor", text_align="right"),
                                    rx.th("%", text_align="right"),
                                )
                            ),
                            rx.tbody(
                                *[
                                    rx.tr(
                                        rx.td(item.get("centro_custo", "N/A")),
                                        rx.td(
                                            f"R$ {item.get('valor', 0):,.2f}",
                                            text_align="right",
                                        ),
                                        rx.td(
                                            f"{item.get('percentual', 0):.2f}%",
                                            text_align="right",
                                        ),
                                    )
                                    for item in data
                                ]
                            ),
                            width="100%",
                            border_collapse="collapse",
                        ),
                        margin_top="md",
                        border="1px solid var(--color-border)",
                        border_radius="md",
                        overflow="auto",
                    ),
                ),
                
                spacing="md",
                width="100%",
            ),
            padding="lg",
            background_color="var(--color-surface)",
            border="1px solid var(--color-border)",
            border_radius="lg",
            box_shadow="var(--shadow-md)",
        )


class TimeSeriesChart(rx.Component):
    """
    GROK 4: Time series chart for sync history
    Shows sync events over time with status coloring
    """
    tag = "div"
    
    @staticmethod
    def render(
        sync_history: List[dict] | None = None,
        title: str = "Histórico de Sincronização",
    ):
        if sync_history is None:
            sync_history = []
        
        return rx.box(
            rx.vstack(
                rx.heading(title, size="md", font_weight="bold"),
                
                rx.cond(
                    len(sync_history) > 0,
                    rx.box(
                        rx.recharts.line_chart(
                            rx.recharts.cartesian_grid(),
                            rx.recharts.x_axis(
                                data_key="timestamp",
                            ),
                            rx.recharts.y_axis(),
                            rx.recharts.tooltip(),
                            rx.recharts.line(
                                data_key="records",
                                stroke="#6366F1",
                                stroke_width=2,
                                dot=True,
                                animation_duration=600,
                            ),
                            data=sync_history,
                            width="100%",
                            height=300,
                            margin={"top": 5, "right": 30, "left": 0, "bottom": 5},
                        ),
                        width="100%",
                    ),
                    rx.text("Sem histórico", text_align="center", padding="lg"),
                ),
                
                spacing="md",
                width="100%",
            ),
            padding="lg",
            background_color="var(--color-surface)",
            border="1px solid var(--color-border)",
            border_radius="lg",
            box_shadow="var(--shadow-md)",
        )


class MetricsGrid(rx.Component):
    """
    GROK 4: Responsive metrics grid
    Shows key metrics in card layout
    Mobile-first responsive design
    """
    tag = "div"
    
    @staticmethod
    def render(metrics: List[dict] | None = None):
        if metrics is None:
            metrics = []
        
        return rx.grid(
            *[
                rx.box(
                    rx.vstack(
                        rx.text(
                            metric.get("label", "N/A"),
                            font_size="xs",
                            font_weight="bold",
                            text_transform="uppercase",
                            color="var(--color-text-secondary)",
                        ),
                        rx.heading(
                            metric.get("value", "0"),
                            size="lg",
                            color=metric.get("color", "var(--color-primary)"),
                        ),
                        rx.text(
                            metric.get("change", ""),
                            font_size="sm",
                            color="var(--color-text-secondary)",
                        ),
                        spacing="sm",
                    ),
                    padding="md",
                    border="1px solid var(--color-border)",
                    border_radius="md",
                    background_color="var(--color-surface)",
                    box_shadow="var(--shadow-sm)",
                )
                for metric in metrics
            ],
            grid_template_columns="repeat(auto-fit, minmax(200px, 1fr))",
            gap="md",
            width="100%",
        )
