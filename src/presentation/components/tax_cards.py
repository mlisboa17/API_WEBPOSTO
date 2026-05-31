import reflex as rx
from decimal import Decimal

class CashRecoveryCard(rx.Component):
    def __init__(self, value_getter):
        self.value_getter = value_getter

    def __call__(self) -> rx.Component:
        return rx.box(
            rx.vstack(
                rx.text('Cash Recovery (PIS/COFINS)', size='sm', color='gray'),
                rx.heading(lambda: f"R$ {Decimal(self.value_getter()):,.4f}", size='2xl'),
            ),
            padding='4', border='1px solid #e2e8f0', border_radius='md', bg='linear-gradient(90deg,#08121b,#0b2431)'
        )


class RiskBadge(rx.Component):
    def __call__(self) -> rx.Component:
        # sample badges for risk indicators
        return rx.hstack(
            rx.vstack(rx.text('NCM Missing', size='xs'), rx.badge('12', color_scheme='red')),
            rx.vstack(rx.text('High Impact', size='xs'), rx.badge('5', color_scheme='yellow')),
            rx.vstack(rx.text('OK', size='xs'), rx.badge('9983', color_scheme='green')),
            spacing='4'
        )
