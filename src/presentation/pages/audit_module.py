"""
📋 AUDIT MODULE - Análise Tributária Detalhada
Relatório consolidado de achados e recomendações de conformidade
"""
import reflex as rx
from src.presentation.shell_corporate import GlobalState


def finding_item(
    sku: str,
    category: str,
    issue: str,
    severity: str,
    impact: float,
):
    """Item de achado de auditoria"""
    color_map = {
        "critico": ("#FF4444", "red"),
        "alerta": ("#FFB84D", "orange"),
        "ok": ("#00DD88", "green"),
    }
    color, scheme = color_map.get(severity, ("#A0A0A0", "gray"))
    
    return rx.hstack(
        rx.box(
            width="4px",
            height="100%",
            bg=color,
            border_radius="full",
        ),
        rx.vstack(
            rx.hstack(
                rx.text(f"SKU: {sku}", size="3", weight="bold"),
                rx.badge(category, variant="soft", padding_x="2"),
                rx.spacer(),
                rx.badge(
                    severity.upper(),
                    color_scheme=scheme,
                    variant="soft",
                ),
                width="100%",
            ),
            rx.text(issue, size="2", color="#A0A0A0"),
            rx.hstack(
                rx.text(f"Impacto: R$ {impact:.2f}", size="2", weight="medium"),
                rx.spacer(),
                rx.button(
                    "Ver Detalhes",
                    size="1",
                    variant="outline",
                ),
                width="100%",
            ),
            spacing="2",
            width="100%",
        ),
        padding="12px",
        bg="rgba(255, 255, 255, 0.02)",
        border="1px solid rgba(255, 255, 255, 0.08)",
        border_radius="lg",
        width="100%",
        spacing="3",
    )


def audit_summary_stats():
    """Estatísticas resumidas da auditoria"""
    return rx.grid(
        rx.box(
            rx.vstack(
                rx.text("Achados Críticos", size="2", color="#A0A0A0"),
                rx.heading("12", size="6", color="#FF4444"),
                rx.text("requerem ação imediata", size="1", color="#606060"),
                spacing="2",
            ),
            padding="16px",
            bg="rgba(255, 68, 68, 0.08)",
            border="1px solid rgba(255, 68, 68, 0.2)",
            border_radius="xl",
        ),
        rx.box(
            rx.vstack(
                rx.text("Achados de Alerta", size="2", color="#A0A0A0"),
                rx.heading("8", size="6", color="#FFB84D"),
                rx.text("requerem revisão", size="1", color="#606060"),
                spacing="2",
            ),
            padding="16px",
            bg="rgba(255, 184, 77, 0.08)",
            border="1px solid rgba(255, 184, 77, 0.2)",
            border_radius="xl",
        ),
        rx.box(
            rx.vstack(
                rx.text("Conformidade", size="2", color="#A0A0A0"),
                rx.heading("5", size="6", color="#00DD88"),
                rx.text("validados e ok", size="1", color="#606060"),
                spacing="2",
            ),
            padding="16px",
            bg="rgba(0, 221, 136, 0.08)",
            border="1px solid rgba(0, 221, 136, 0.2)",
            border_radius="xl",
        ),
        columns="3",
        spacing="4",
        width="100%",
    )


def audit_module():
    """Página AUDIT: Análise Tributária Detalhada"""
    return rx.vstack(
        # HEADER
        rx.heading(
            "Análise Tributária",
            size="4",
            letter_spacing="-1px",
        ),
        rx.text(
            "Relatório consolidado de conformidade tributária e achados de auditoria",
            size="2",
            color="#A0A0A0",
        ),
        
        # SUMMARY STATS
        audit_summary_stats(),
        
        # FILTERS
        rx.hstack(
            rx.select(
                ["Todos", "Críticos", "Alertas", "OK"],
                default_value="Todos",
                placeholder="Filtrar por severidade",
            ),
            rx.select(
                ["Todos", "CNAE", "NCM", "Regime", "CST"],
                default_value="Todos",
                placeholder="Filtrar por tipo",
            ),
            rx.input(
                placeholder="Buscar por SKU...",
                size="3",
            ),
            rx.spacer(),
            rx.button(
                "🔄 Atualizar",
                size="2",
                variant="soft",
            ),
            width="100%",
            spacing="3",
        ),
        
        # FINDINGS LIST
        rx.vstack(
            finding_item(
                "SKU-00001",
                "Bebidas",
                "NCM divergente da descrição do produto",
                "critico",
                492.00,
            ),
            finding_item(
                "SKU-00003",
                "Bebidas",
                "Possível bitributação de PIS/COFINS monofásico",
                "alerta",
                312.50,
            ),
            finding_item(
                "SKU-00005",
                "Bebidas",
                "NCM divergente da descrição do produto",
                "critico",
                492.00,
            ),
            finding_item(
                "SKU-00008",
                "Bebidas",
                "NCM validado - Conformidade OK",
                "ok",
                0.00,
            ),
            spacing="3",
            width="100%",
        ),
        
        # RECOMMENDATIONS PANEL
        rx.vstack(
            rx.hstack(
                rx.heading("Plano de Ação", size="3"),
                rx.spacer(),
                rx.button(
                    "📥 Importar em Massa",
                    size="1",
                    variant="outline",
                ),
                width="100%",
            ),
            rx.vstack(
                rx.checkbox(
                    rx.text("Corrigir 12 NCMs conforme audit trail"),
                    default_checked=False,
                ),
                rx.checkbox(
                    rx.text("Revisar regime tributário para 8 SKUs"),
                    default_checked=False,
                ),
                rx.checkbox(
                    rx.text("Validar CST/CFOP em próxima integração"),
                    default_checked=False,
                ),
                spacing="2",
            ),
            padding="16px",
            bg="rgba(255, 255, 255, 0.03)",
            border="1px solid rgba(255, 255, 255, 0.08)",
            border_radius="xl",
            width="100%",
            spacing="3",
        ),
        
        # EXPORT BUTTON
        rx.hstack(
            rx.button(
                "📊 Exportar PDF",
                size="3",
                color_scheme="cyan",
            ),
            rx.button(
                "📋 Copiar Relatório",
                size="3",
                variant="outline",
            ),
            rx.spacer(),
            width="100%",
        ),
        
        spacing="8",
        width="100%",
        animation="fadeInUp 0.4s ease-out",
    )
