import reflex as rx
from decimal import Decimal
from datetime import date
from typing import List

from src.presentation.components.filters import RangeFilter, MultiSelectFilter

"""Executive dashboard page for directors with filters, deep-dive and export."""


class ExecState(rx.State):
    dark_mode: bool = True
    loading: bool = True
    metrics: dict = {}
    # filters
    date_from: date | None = None
    date_to: date | None = None
    categories: List[str] = []
    cost_centers: List[str] = []

    @classmethod
    def on_filters_change(cls, *_args, **_kwargs) -> None:
        # mark loading and simulate reactive update; real integration should call backend
        cls.loading = True
        # small debounce simulation
        def _done():
            cls.loading = False
        rx.run_later(_done, 0.4)

    async def toggle_theme(self) -> None:
        self.dark_mode = not self.dark_mode
        rx.set_cookie('theme', 'dark' if self.dark_mode else 'light', max_age=60*60*24*365)


def skeleton_card() -> rx.Component:
    return rx.box(
        rx.div(style={'height': '80px', 'background': 'linear-gradient(90deg,#111,#1a1a1a)'}),
        padding='4', border_radius='md'
    )


@rx.page(route='/executive', title='Executive - Logos')
def executive_dashboard() -> rx.Component:
    # SSE source - backend should provide /metrics/stream
    events = rx.event_source('/metrics/stream')

    header = rx.hstack(
        rx.heading('Logos Executive Vision', size='lg'),
        rx.spacer(),
        rx.button('📥 Exportar PDF Executivo', size='sm', on_click=lambda: rx.run_js('window.print()')),
        rx.switch(is_checked=ExecState.dark_mode, on_change=ExecState.toggle_theme),
    )

    # Filters
    date_filter = RangeFilter(
        value_from=ExecState.date_from,
        value_to=ExecState.date_to,
        on_change=ExecState.on_filters_change,
    )

    cat_filter = MultiSelectFilter(
        label='Grupo de Produtos',
        options=['Bebidas', 'Alimentos', 'Tabacaria', 'EV Charging', 'Conveniencia'],
        value=ExecState.categories,
        on_change=ExecState.on_filters_change,
    )

    cc_filter = MultiSelectFilter(
        label='Centro de Custo',
        options=['Center A', 'Center B', 'Center C'],
        value=ExecState.cost_centers,
        on_change=ExecState.on_filters_change,
    )

    # KPI Cards
    cards = rx.grid(
        rx.box(
            rx.vstack(
                rx.text('Revenue / s', size='sm', color='gray'),
                rx.heading(lambda: f"R$ {Decimal(ExecState.metrics.get('rps', '0')):.4f}", size='xl'),
            ),
            padding='4', border='1px solid rgba(255,255,255,0.06)',
            bg='rgba(255,255,255,0.04)', backdrop_filter='blur(10px)', border_radius='md'
        ),
        rx.box(
            rx.vstack(
                rx.text('Margem Média', size='sm', color='gray'),
                rx.heading(lambda: ExecState.metrics.get('avg_margin', '0.00%'), size='xl'),
            ),
            padding='4', border='1px solid rgba(255,255,255,0.06)',
            bg='rgba(255,255,255,0.04)', backdrop_filter='blur(10px)', border_radius='md'
        ),
        rx.box(
            rx.vstack(
                rx.text('Top Seller', size='sm', color='gray'),
                rx.heading(lambda: ExecState.metrics.get('top_seller', '—'), size='xl'),
            ),
            padding='4', border='1px solid rgba(255,255,255,0.06)',
            bg='rgba(255,255,255,0.04)', backdrop_filter='blur(10px)', border_radius='md'
        ),
        template_columns=['repeat(12, 1fr)'], gap='4', width='100%'
    )

    # Deep dive margin component: horizontal bar placeholder
    margin_chart = rx.box(
        rx.vstack(
            rx.heading('Margem por SKU (Deep Dive)', size='md'),
            rx.text('Bar chart (horizontal) will render here - requires Recharts in frontend', color='gray', size='sm'),
        ),
        padding='4', border='1px solid rgba(255,255,255,0.06)',
        bg='rgba(255,255,255,0.03)', border_radius='md'
    )

    # assemble
    return rx.vstack(
        header,
        rx.box(
            rx.vstack(date_filter, rx.hstack(cat_filter, cc_filter), cards, margin_chart, spacing='6', padding='6', width='100%'),
            width='100%', max_width='1400px', margin='0 auto'
        ),
        rx.cond(ExecState.loading, rx.vstack(skeleton_card(), skeleton_card()), rx.box()),
        events,
        width='100%', padding='6', bg=lambda: ('#0f172a' if ExecState.dark_mode else '#ffffff')
    )
