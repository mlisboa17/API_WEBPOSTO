import reflex as rx
from decimal import Decimal

"""Deep-dive executive margin view with SKU horizontal bars and export."""


class MarginState(rx.State):
    loading: bool = True
    items: list[dict] = []

    async def load(self, filters: dict | None = None):
        self.loading = True
        # placeholder: in production call backend `/api/margins` with filters
        def _fill():
            self.items = [
                {'sku': f'PROD-{i:04d}', 'cost': Decimal('1.23') + i * Decimal('0.01'), 'price': Decimal('2.50') + i * Decimal('0.02')} for i in range(1, 21)
            ]
            self.loading = False
        rx.run_later(_fill, 0.2)


def margin_bar_list() -> rx.Component:
    return rx.vstack(
        *(rx.hstack(rx.text(item['sku'], width='20%'), rx.box(rx.text(f"R$ {item['price'] - item['cost']:.4f}"), width='80%')) for item in MarginState.items),
        spacing='2'
    )


@rx.page(route='/executive-margin', title='Executive Margin - Logos')
def executive_margin_view() -> rx.Component:
    return rx.vstack(
        rx.heading('Executive Margin Deep-Dive', size='lg'),
        rx.button('Refresh', on_click=lambda: MarginState.load()),
        rx.cond(MarginState.loading, rx.text('Loading...'), margin_bar_list()),
        width='100%', padding='6'
    )
