from __future__ import annotations

import os

import httpx
import reflex as rx

from src.presentation.shell import main_shell
from src.presentation.theme import styles


ADELAIDE_API_URL = os.getenv("ADELAIDE_API_URL", "http://127.0.0.1:8010")


class AdelaideState(rx.State):
    """Executive state for the Adelaide audit dashboard."""

    is_processing: bool = False
    recovery_estimated: float = 0.0
    recovery_target: float = 45280.50
    risk_score: int = 0
    regime: str = "Lucro Real"
    cnpj: str = "12.345.678/0001-99"
    uf: str = "PE"
    current_page: str = "tax-audit"
    job_id: str = ""
    latest_sku: str = ""
    processed: int = 0
    total: int = 0

    async def start_deep_audit(self):
        self.is_processing = True
        self.recovery_estimated = 0.0
        self.risk_score = 12
        self.job_id = ""
        self.latest_sku = ""
        self.processed = 0
        self.total = 0
        payload = {
            "context": {
                "cnpj": self.cnpj,
                "regime": self.regime.upper().replace(" ", "_"),
                "cnae": "4731800",
                "uf": self.uf,
            },
            "products": [],
        }
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(f"{ADELAIDE_API_URL}/api/adelaide/run", json=payload)
            response.raise_for_status()
            body = response.json()
            self.job_id = body["job_id"]
            self.total = int(body.get("total", 0))
        self.is_processing = False
        return rx.call_script(f"window.startAdelaideStream('{ADELAIDE_API_URL}/api/adelaide/stream/{self.job_id}')")

    @rx.var
    def formatted_recovery(self) -> str:
        return f"R$ {self.recovery_estimated:,.2f}"

    @rx.var
    def progress_label(self) -> str:
        if self.total <= 0:
            return "Aguardando lote"
        return f"{self.processed}/{self.total} itens"

    @rx.var
    def latest_sku_label(self) -> str:
        return f"Último SKU: {self.latest_sku or '-'}"

    @rx.var
    def risk_color(self) -> str:
        if self.risk_score >= 70:
            return styles.RED
        if self.risk_score >= 40:
            return styles.AMBER
        return styles.GREEN


RISK_ROWS: list[tuple[str, str, str, str, str, str]] = [
    (
        f"SKU-{index:05d}",
        "CERV SKOL LATA 350ML" if index % 3 == 0 else "REFRIGERANTE ZERO 2L",
        "22030000" if index % 4 else "00000000",
        "critico" if index % 9 == 0 else ("credito" if index % 4 == 0 else "ok"),
        "NCM de conveniência incompatível com descrição" if index % 9 == 0 else "CST indica oportunidade monofásica",
        "4731800" if index % 2 == 0 else "4711302",
    )
    for index in range(1, 61)
]


def executive_card(title: str, value: rx.Component | str, caption: str, accent: str) -> rx.Component:
    return rx.box(
        rx.vstack(
            rx.text(title, size="2", color=styles.TEXT_MUTED),
            value if isinstance(value, rx.Component) else rx.heading(value, size="8", color="white"),
            rx.text(caption, size="1", color=accent),
            align_items="start",
            spacing="2",
        ),
        padding="22px",
        width="100%",
        background="linear-gradient(180deg, rgba(255,255,255,0.035), rgba(255,255,255,0.015))",
        border_radius="24px",
        border=f"1px solid {accent}33",
        box_shadow=f"0 0 0 1px {accent}18 inset, 0 10px 40px rgba(0,0,0,0.25)",
    )


def skeleton_rows() -> rx.Component:
    return rx.vstack(
        rx.foreach(
            [1, 2, 3, 4, 5, 6],
            lambda _: rx.hstack(
                rx.skeleton(width="28%", height="16px"),
                rx.skeleton(width="14%", height="16px"),
                rx.skeleton(width="12%", height="16px"),
                rx.skeleton(width="18%", height="24px"),
                rx.skeleton(width="16%", height="16px"),
                width="100%",
                padding_y="12px",
                align_items="center",
            ),
        ),
        id="adelaide-rows-skeleton",
        display="none",
        width="100%",
        spacing="3",
    )


def recovery_counter() -> rx.Component:
    return rx.vstack(
        rx.text("Crédito Recuperável Estimado", size="2", color=styles.TEXT_MUTED),
        rx.heading(AdelaideState.formatted_recovery, id="adelaide-recovery-counter", size="9", color=styles.GREEN),
        rx.text(AdelaideState.progress_label, id="adelaide-progress-label", size="1", color=styles.CYAN),
        rx.text(AdelaideState.latest_sku_label, id="adelaide-latest-sku", size="1", color="#7DD3FC"),
        align_items="start",
        width="100%",
    )


def risk_radar() -> rx.Component:
    axes = [
        ("CNAE", 76),
        ("NCM", 84),
        ("CST", 61),
        ("PIS/COFINS", 72),
        ("SEFAZ", 58),
    ]
    return rx.box(
        rx.vstack(
            rx.text("Radar de Risco Sefaz", size="2", color=styles.TEXT_MUTED),
            rx.hstack(
                rx.center(
                    rx.box(
                        rx.vstack(
                            rx.text("Exposição", size="1", color=styles.TEXT_MUTED),
                            rx.heading("0%", id="adelaide-risk-score", size="8", color=styles.RED),
                            rx.text("SEFAZ PE", size="2", color="#D5D7DA"),
                            spacing="1",
                            align_items="center",
                        ),
                        id="adelaide-risk-orb",
                        width="170px",
                        height="170px",
                        border_radius="999px",
                        display="flex",
                        align_items="center",
                        justify_content="center",
                        background="conic-gradient(from 180deg, rgba(255,77,77,0.90) 0deg, rgba(255,176,32,0.88) 140deg, rgba(0,245,255,0.92) 260deg, rgba(255,255,255,0.16) 360deg)",
                        box_shadow="0 0 30px rgba(0,245,255,0.14)",
                        border="1px solid rgba(255,255,255,0.08)",
                    ),
                    width="210px",
                ),
                rx.vstack(
                    rx.foreach(
                        axes,
                        lambda axis: rx.hstack(
                            rx.text(axis[0], width="92px", color="#D5D7DA", size="2"),
                            rx.progress(value=axis[1], color_scheme="cyan", width="100%", height="8px"),
                            rx.text(f"{axis[1]}%", width="42px", text_align="right", color=styles.CYAN, size="2"),
                            width="100%",
                        ),
                    ),
                    width="100%",
                    spacing="3",
                    align_items="stretch",
                ),
                width="100%",
                align_items="center",
                spacing="5",
            ),
            align_items="start",
            width="100%",
            spacing="3",
        ),
        padding="22px",
        width="100%",
        **styles.glass_panel_style(),
    )


def status_badge(status: str) -> rx.Component:
    return rx.cond(
        status == "critico",
        rx.badge(
            "Crítico",
            style={"background": "rgba(255,77,77,0.12)", "color": styles.RED, "border": "1px solid rgba(255,77,77,0.28)"},
        ),
        rx.cond(
            status == "credito",
            rx.badge(
                "Crédito",
                style={"background": "rgba(0,255,127,0.12)", "color": styles.GREEN, "border": "1px solid rgba(0,255,127,0.28)"},
            ),
            rx.badge(
                "OK",
                style={"background": "rgba(0,245,255,0.12)", "color": styles.CYAN, "border": "1px solid rgba(0,245,255,0.28)"},
            ),
        ),
    )


def risk_table_rows() -> rx.Component:
    return rx.foreach(
        RISK_ROWS,
        lambda item: rx.tooltip(
            rx.hstack(
                rx.vstack(
                    rx.text(item[0], weight="bold", color="white"),
                    rx.text(item[1], size="2", color=styles.TEXT_MUTED),
                    align_items="start",
                    width="32%",
                ),
                rx.text(item[2], width="14%", color="#E6E8EC"),
                rx.text(item[5], width="12%", color="#E6E8EC"),
                status_badge(item[3]),
                rx.spacer(),
                rx.text(
                    "Pulse",
                    color=rx.cond(item[3] == "critico", styles.RED, styles.CYAN),
                    animation=rx.cond(item[3] == "critico", "pulse 1.3s infinite", "none"),
                ),
                width="100%",
                padding_y="12px",
                padding_x="10px",
                border_bottom="1px solid rgba(255,255,255,0.06)",
            ),
            content=item[4],
        ),
    )


def risk_table() -> rx.Component:
    return rx.box(
        rx.vstack(
            rx.hstack(
                rx.text("Tabela Raio-X", size="4", weight="bold"),
                rx.spacer(),
                rx.badge("Adelaide Insights", style={"background": f"{styles.CYAN}18", "color": styles.CYAN}),
                width="100%",
            ),
            rx.text("Radar fiscal com semáforo tributário para 90 dias de vendas e trilha de inconsistências.", size="2", color=styles.TEXT_MUTED),
            skeleton_rows(),
            rx.box(risk_table_rows(), id="adelaide-rows-table", width="100%"),
            width="100%",
            spacing="0",
        ),
        padding="26px",
        margin_top="20px",
        width="100%",
        max_height="560px",
        overflow_y="auto",
        background="linear-gradient(180deg, rgba(255,255,255,0.025), rgba(255,255,255,0.012))",
        border="1px solid rgba(255,255,255,0.06)",
        border_radius="30px",
        backdrop_filter="blur(18px)",
    )


def unified_shell(content: rx.Component) -> rx.Component:
    return main_shell(content)


def tax_audit_view() -> rx.Component:
    content = rx.vstack(
        rx.script(
            """
window.__adelaideAnimatedRecovery = window.__adelaideAnimatedRecovery || 0;
window.__adelaideLastReport = window.__adelaideLastReport || null;

window.animateAdelaideRecovery = function(targetValue) {
    const node = document.getElementById('adelaide-recovery-counter');
    if (!node) return;
    const startValue = Number(window.__adelaideAnimatedRecovery || 0);
    const endValue = Number(targetValue || 0);
    const startTime = performance.now();
    const duration = 480;

    function tick(now) {
        const progress = Math.min((now - startTime) / duration, 1);
        const eased = 1 - Math.pow(1 - progress, 3);
        const current = startValue + ((endValue - startValue) * eased);
        node.textContent = `R$ ${current.toLocaleString('pt-BR', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;
        if (progress < 1) {
            requestAnimationFrame(tick);
            return;
        }
        window.__adelaideAnimatedRecovery = endValue;
    }

    requestAnimationFrame(tick);
}

window.exportAdelaideReport = function() {
    const report = window.__adelaideLastReport;
    if (!report) {
        window.alert('O relatório ainda não foi concluído.');
        return;
    }
    const blob = new Blob([JSON.stringify(report, null, 2)], { type: 'application/json' });
    const url = URL.createObjectURL(blob);
    const anchor = document.createElement('a');
    anchor.href = url;
    anchor.download = 'relatorio-diretoria-adelaide.json';
    anchor.click();
    URL.revokeObjectURL(url);
}

window.startAdelaideStream = function(url) {
    const skeleton = document.getElementById('adelaide-rows-skeleton');
    const table = document.getElementById('adelaide-rows-table');
    if (skeleton) skeleton.style.display = 'flex';
    if (table) table.style.display = 'none';
    if (window.__adelaideSource) {
        window.__adelaideSource.close();
    }
    const source = new EventSource(url);
    window.__adelaideSource = source;
    source.onmessage = function(event) {
        const payload = JSON.parse(event.data);
        const progress = document.getElementById('adelaide-progress-label');
        const sku = document.getElementById('adelaide-latest-sku');
        const risk = document.getElementById('adelaide-risk-score');
        const riskBar = document.getElementById('adelaide-risk-bar');
        const orb = document.getElementById('adelaide-risk-orb');
        if (payload.recovery_estimated !== undefined) window.animateAdelaideRecovery(Number(payload.recovery_estimated));
        if (progress && payload.processed !== undefined && payload.total !== undefined) progress.textContent = `${payload.processed}/${payload.total} itens`;
        if (sku && payload.latest_sku) sku.textContent = `Último SKU: ${payload.latest_sku}`;
        if (risk && payload.risk_score !== undefined) risk.textContent = `${payload.risk_score}%`;
        if (riskBar && payload.risk_score !== undefined) riskBar.value = payload.risk_score;
        if (orb && payload.risk_score !== undefined) orb.style.background = `conic-gradient(from 180deg, rgba(255,77,77,0.92) 0deg, rgba(255,176,32,0.88) ${Math.max(90, payload.risk_score * 2.2)}deg, rgba(0,245,255,0.92) 300deg, rgba(255,255,255,0.16) 360deg)`;
        if (payload.event === 'done') {
            window.__adelaideLastReport = payload.report || null;
            if (skeleton) skeleton.style.display = 'none';
            if (table) table.style.display = 'block';
            source.close();
        }
    };
}
            """
        ),
        rx.hstack(
            rx.vstack(
                rx.heading("Adelaide Tax Intelligence", size="9", color=styles.CYAN),
                rx.text(f"Auditoria para {AdelaideState.cnpj} | {AdelaideState.regime} | {AdelaideState.uf}", color=styles.TEXT_MUTED),
                align_items="start",
            ),
            rx.spacer(),
            rx.button(
                "Executar Auditoria Profunda",
                on_click=AdelaideState.start_deep_audit,
                loading=AdelaideState.is_processing,
                bg=styles.CYAN,
                color="#050506",
                size="4",
                border_radius="18px",
                _hover={"bg": "#00D6E6", "transform": "translateY(-1px) scale(1.01)"},
            ),
            rx.button(
                "Exportar Relatório para Diretoria",
                on_click=rx.call_script("window.exportAdelaideReport()"),
                variant="outline",
                border="1px solid rgba(255,255,255,0.16)",
                color="#F5FBFF",
                background="linear-gradient(135deg, rgba(255,255,255,0.10), rgba(0,245,255,0.08))",
                border_radius="18px",
                padding_x="20px",
                _hover={"transform": "translateY(-1px)", "boxShadow": "0 0 28px rgba(0,245,255,0.12)"},
            ),
            width="100%",
        ),
        rx.grid(
            executive_card("Crédito Recuperável", recovery_counter(), "Monofásico + bitributação em 90 dias", styles.GREEN),
            executive_card(
                "Risco de Autuação",
                rx.vstack(
                    rx.heading(f"{AdelaideState.risk_score}%", size="9", color=AdelaideState.risk_color),
                    rx.progress(value=AdelaideState.risk_score, id="adelaide-risk-bar", width="100%", color_scheme="red", height="8px"),
                    align_items="start",
                    width="100%",
                ),
                "SEFAZ/RFB com radar por CNAE, NCM e CEST",
                styles.RED,
            ),
            executive_card("Cadastros Inconsistentes", "184 itens", "Semáforo tributário Verde/Amarelo/Vermelho", styles.CYAN),
            columns="3",
            spacing="5",
            width="100%",
        ),
        rx.grid(
            risk_radar(),
            rx.box(
                rx.vstack(
                    rx.text("Pipeline UI", size="2", color=styles.TEXT_MUTED),
                    rx.text("Skeleton loaders assumem o processamento dos 90 dias enquanto o SSE atualiza o valor executivo no browser.", color="#E6E8EC"),
                    rx.text("A camada de apresentação evita render-blocking e movimenta a animação do contador no cliente para preservar fluidez.", color=styles.TEXT_MUTED, size="2"),
                    align_items="start",
                    spacing="3",
                ),
                padding="22px",
                **styles.glass_panel_style(),
            ),
            columns="2",
            spacing="5",
            width="100%",
        ),
        risk_table(),
        width="100%",
        spacing="5",
        align_items="stretch",
    )
    return unified_shell(content)


__all__ = ["AdelaideState", "tax_audit_view", "unified_shell"]
