import reflex as rx
from typing import List

"""Tax Audit Dashboard UI

Features:
- Traffic-light rows for SKU status
- Dynamic filters (category, cost center, tax status)
- Batch select + Homologate action
- SSE sync button
"""

from src.presentation.components.filters import MultiSelectFilter


class TaxAuditState(rx.State):
    loading: bool = True
    items: List[dict] = []
    selected: List[str] = []

    async def load(self, filters: dict | None = None):
        self.loading = True
        # placeholder: in production call backend `/api/tax/list` with filters
        def _fill():
            self.items = [
                {'sku': f'P{i:05d}', 'name': f'Produto {i}', 'status': 'ok' if i % 10 else 'error', 'impact': 0.0}
                for i in range(1, 501)
            ]
            self.loading = False
        rx.run_later(_fill, 0.1)

    async def toggle_select(self, sku: str):
        if sku in self.selected:
            self.selected = [s for s in self.selected if s != sku]
        else:
            self.selected = self.selected + [sku]

    async def homologate_selected(self):
        # POST to backend to homologate; placeholder simulation
        await rx.run_async(lambda: None)
        self.selected = []


@rx.page(route='/tax-audit', title='Tax Audit - Logos')
def tax_audit_dashboard() -> rx.Component:
    cat_filter = MultiSelectFilter(label='Grupo de Produtos', options=['Bebidas', 'Alimentos', 'Tabacaria', 'Conveniencia'], on_change=lambda: TaxAuditState.load())
    cc_filter = MultiSelectFilter(label='Centro de Custo', options=['Center A', 'Center B', 'Center C'], on_change=lambda: TaxAuditState.load())
    status_filter = MultiSelectFilter(label='Status Tributário', options=['ok', 'divergent', 'error'], on_change=lambda: TaxAuditState.load())

    header = rx.hstack(rx.heading('Tax Audit Dashboard', size='lg'), rx.spacer(), rx.button('Sincronizar com Nuvem Tributária', on_click=lambda: rx.event_source('/tax/sync/stream')))

    # Virtual scroll placeholder
    rows = rx.box(
        *(rx.hstack(
            rx.checkbox(is_checked=lambda sku=item['sku']: item['sku'] in TaxAuditState.selected, on_change=lambda _, sku=item['sku']: TaxAuditState.toggle_select(sku)),
            rx.text(item['sku'], width='15%'),
            rx.text(item['name'], width='45%'),
            rx.badge(item['status'], color_scheme=('green' if item['status']=='ok' else 'red' if item['status']=='error' else 'yellow')),
            rx.text(f"Impact: R$ {item['impact']}", width='20%'),
        ) for item in TaxAuditState.items),
        overflow_y='auto', max_height='700px', border='1px solid #e2e8f0', border_radius='md'
    )

    return rx.vstack(
        header,
        rx.box(rx.vstack(cat_filter, cc_filter, status_filter), padding='4'),
        rx.hstack(rx.button('Homologar Selecionados', color_scheme='blue', on_click=TaxAuditState.homologate_selected), rx.button('Exportar Inconsistências', color_scheme='green')),
        rows,
        width='100%', padding='6'
    )
