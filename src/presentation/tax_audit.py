import reflex as rx
from src.presentation.shell import ThemeState, glass_card
from typing import List


class TaxAuditState(rx.State):
    recovery_total: float = 0.0
    is_auditing: bool = False
    products: List[dict] = []

    @classmethod
    async def run_audit(cls):
        cls.is_auditing = True
        # Placeholder: in production this would trigger background processing
        # and stream updates via SSE; here we simulate progress.
        for i in range(5):
            await rx.sleep(0.2)
            cls.recovery_total += 125.34 * (i + 1)
            cls.set_loading(min(1.0, cls.recovery_total / 20000))
        cls.is_auditing = False

    @classmethod
    def set_loading(cls, v: float):
        ThemeState.set_loading(v)


def stat_card(label, value, color="#00F5FF"):
    return glass_card(label, value, color)


def tax_audit_page():
    return rx.vstack(
        rx.hstack(
            rx.vstack(
                rx.heading("Auditoria Tributária", size="9"),
                rx.text("Recuperação de Créditos e Validação de NCM", color="#A0A0A0"),
                align_items="start",
            ),
            rx.spacer(),
            rx.button(
                "Iniciar Nova Auditoria",
                on_click=TaxAuditState.run_audit,
                is_loading=TaxAuditState.is_auditing,
                size="4",
                bg="#00F5FF",
                color="black",
                _hover={"bg": "#00D1D1"},
            ),
            width="100%",
            padding_bottom="8",
        ),
        rx.grid(
            stat_card("Crédito Recuperável (90 dias)", rx.text(lambda: f"R$ {TaxAuditState.recovery_total:,.2f}")),
            stat_card("Divergências de NCM", "0 Itens", color="#FF4D4D"),
            stat_card("Monofásicos Corretos", "0%", color="#00FF7F"),
            columns="3",
            spacing="4",
            width="100%",
        ),
        rx.box(
            rx.vstack(
                rx.text("Detalhamento de Inconsistências", size="5", weight="bold"),
                rx.divider(alpha=0.1),
                width="100%",
                padding="6",
            ),
            bg="rgba(255, 255, 255, 0.02)",
            border="1px solid rgba(255, 255, 255, 0.05)",
            border_radius="3xl",
            width="100%",
            margin_top="8",
        ),
        width="100%",
    )


__all__ = ["TaxAuditState", "tax_audit_page"]
