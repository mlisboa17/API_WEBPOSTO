"""
💰 MARGIN MODULE - Margem Real Analytics
Análise de margens de lucro com tributação aplicada
"""
import reflex as rx
from src.presentation.shell_corporate import GlobalState, kpi_card


def margin_metrics_grid():
    """Grid com métricas de margem"""
    return rx.grid(
        rx.box(
            rx.vstack(
                rx.text("Margem Bruta", size="2", color="#A0A0A0"),
                rx.heading("47.3%", size="5", color="#00F5FF"),
                rx.text("↑ 3.2% vs. período anterior", size="1", color="#00AA00"),
                spacing="2",
            ),
            padding="16px",
            bg="rgba(255, 255, 255, 0.03)",
            border="1px solid rgba(0, 245, 255, 0.12)",
            border_radius="xl",
        ),
        rx.box(
            rx.vstack(
                rx.text("Margem Líquida", size="2", color="#A0A0A0"),
                rx.heading("28.5%", size="5", color="#7000FF"),
                rx.text("↑ 1.8% vs. período anterior", size="1", color="#00AA00"),
                spacing="2",
            ),
            padding="16px",
            bg="rgba(255, 255, 255, 0.03)",
            border="1px solid rgba(112, 0, 255, 0.12)",
            border_radius="xl",
        ),
        rx.box(
            rx.vstack(
                rx.text("Custo Tributário", size="2", color="#A0A0A0"),
                rx.heading("18.8%", size="5", color="#FFB84D"),
                rx.text("Reduzível com crédito PIS/COFINS", size="1", color="#FFB84D"),
                spacing="2",
            ),
            padding="16px",
            bg="rgba(255, 255, 255, 0.03)",
            border="1px solid rgba(255, 184, 77, 0.12)",
            border_radius="xl",
        ),
        rx.box(
            rx.vstack(
                rx.text("ROI de Compliance", size="2", color="#A0A0A0"),
                rx.heading("342%", size="5", color="#00DD88"),
                rx.text("Ganho anual com otimização", size="1", color="#00DD88"),
                spacing="2",
            ),
            padding="16px",
            bg="rgba(255, 255, 255, 0.03)",
            border="1px solid rgba(0, 221, 136, 0.12)",
            border_radius="xl",
        ),
        columns="2",
        spacing="4",
        width="100%",
    )


def margin_trends_chart():
    """Gráfico de tendências de margem (placeholder)"""
    return rx.box(
        rx.vstack(
            rx.heading("Tendência de Margens (90 dias)", size="3"),
            rx.text(
                "Gráfico de linha com evolução das margens",
                color="#606060",
                size="2",
            ),
            rx.box(
                height="200px",
                bg="rgba(0, 245, 255, 0.05)",
                border="1px dashed rgba(0, 245, 255, 0.2)",
                border_radius="lg",
                display="flex",
                align_items="center",
                justify_content="center",
            ),
            spacing="4",
            width="100%",
        ),
        padding="20px",
        bg="rgba(255, 255, 255, 0.03)",
        border="1px solid rgba(255, 255, 255, 0.08)",
        border_radius="xl",
        width="100%",
    )


def margin_module():
    """Página MARGIN: Analytics de Margem Real"""
    return rx.vstack(
        # HEADER
        rx.heading(
            "Margem Real",
            size="4",
            letter_spacing="-1px",
        ),
        rx.text(
            "Análise de margens com impacto tributário otimizado",
            size="2",
            color="#A0A0A0",
        ),
        
        # KPI CARDS
        rx.grid(
            kpi_card(
                "Margem Otimizada",
                "47.3",
                "%",
                trend="↑ 3.2%",
                color="#00F5FF",
            ),
            kpi_card(
                "Impacto Tributário",
                "18.8",
                "%",
                trend="Reduzível",
                color="#FFB84D",
            ),
            kpi_card(
                "Produtos Analisados",
                "1,247",
                "SKUs",
                trend="→",
                color="#7000FF",
            ),
            columns="3",
            spacing="4",
            width="100%",
        ),
        
        # METRICS GRID
        margin_metrics_grid(),
        
        # TRENDS CHART
        margin_trends_chart(),
        
        # RECOMMENDATIONS
        rx.vstack(
            rx.heading("Recomendações de Otimização", size="3"),
            rx.vstack(
                rx.hstack(
                    rx.badge("🎯", padding_x="2"),
                    rx.text("Revisar CNAE para categoria: Bebidas Premium", weight="medium"),
                    rx.spacer(),
                    rx.badge("Alto Impacto", color_scheme="green", variant="soft"),
                    width="100%",
                ),
                rx.hstack(
                    rx.badge("📊", padding_x="2"),
                    rx.text("Aplicar diferimento PIS/COFINS em 15 SKUs", weight="medium"),
                    rx.spacer(),
                    rx.badge("Médio Impacto", color_scheme="cyan", variant="soft"),
                    width="100%",
                ),
                rx.hstack(
                    rx.badge("⚠️", padding_x="2"),
                    rx.text("Validar regime para produtos monofásicos", weight="medium"),
                    rx.spacer(),
                    rx.badge("Baixo Impacto", color_scheme="orange", variant="soft"),
                    width="100%",
                ),
                spacing="3",
            ),
            padding="16px",
            bg="rgba(255, 255, 255, 0.03)",
            border="1px solid rgba(255, 255, 255, 0.08)",
            border_radius="xl",
            width="100%",
            spacing="4",
        ),
        
        spacing="8",
        width="100%",
        animation="fadeInUp 0.4s ease-out",
    )
