"""Geração do dossiê final PDF de uma auditoria aprovada."""

from __future__ import annotations

from io import BytesIO
from xml.sax.saxutils import escape

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import (
    PageBreak,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

from src.services.periodic_audit_run_service import PeriodicAuditRun


class PeriodicAuditDossierService:
    def generate(self, run: PeriodicAuditRun) -> bytes:
        if run.status != "APROVADO":
            raise ValueError("DOSSIER_REQUIRES_APPROVED_RUN")
        output = BytesIO()
        styles = getSampleStyleSheet()
        styles.add(ParagraphStyle(
            name="DossierTitle", parent=styles["Title"], alignment=TA_CENTER,
            textColor=colors.HexColor("#12372A"), spaceAfter=8,
        ))
        doc = SimpleDocTemplate(
            output, pagesize=A4, leftMargin=18 * mm, rightMargin=18 * mm,
            topMargin=20 * mm, bottomMargin=18 * mm,
            title=f"Dossiê de Auditoria {run.id}",
            author="LOGOS SPACE",
        )
        story = [
            Paragraph("LOGOS SPACE", styles["DossierTitle"]),
            Paragraph("Dossiê Final de Auditoria de Prestação de Contas", styles["Heading1"]),
            Paragraph(
                f"Execução <b>{escape(run.id)}</b> - documento gerado a partir da trilha "
                "imutável da aplicação.", styles["BodyText"],
            ),
            Spacer(1, 8),
            self._table([
                ["Empresa", run.empresa_codigo],
                ["Centro de custo", run.centro_custo],
                ["Periodo", f"{run.data_inicial} a {run.data_final}"],
                ["Status", run.status],
                ["Aprovado por", run.aprovado_por or "-"],
                ["Aprovado em", run.aprovado_em.isoformat() if run.aprovado_em else "-"],
            ], [45 * mm, 120 * mm]),
            Spacer(1, 12),
            Paragraph("Checklist e evidências", styles["Heading2"]),
        ]
        checklist = [["Item", "Severidade", "Status", "Responsavel", "Evidencia"]]
        checklist.extend([
            [
                Paragraph(escape(item.titulo), styles["BodyText"]),
                item.severidade,
                item.status,
                item.responsavel or "-",
                Paragraph(escape(item.evidencia or "-"), styles["BodyText"]),
            ]
            for item in run.itens
        ])
        story.extend([self._table(checklist, [60 * mm, 22 * mm, 25 * mm, 28 * mm, 35 * mm]), Spacer(1, 12)])

        story.append(Paragraph("Conciliações documentais", styles["Heading2"]))
        if not run.reconciliacoes:
            story.append(Paragraph("Nenhum PDF foi anexado a esta auditoria.", styles["BodyText"]))
        for reconciliation in run.reconciliacoes:
            story.extend([
                Paragraph(
                    f"<b>Documento:</b> {escape(reconciliation.evidence_id)}<br/>"
                    f"<b>SHA-256:</b> {escape(reconciliation.sha256)}<br/>"
                    f"<b>Resultado:</b> {escape(reconciliation.status)}<br/>"
                    f"<b>Revisado por:</b> {escape(reconciliation.reviewed_by or '-')}<br/>"
                    f"<b>Justificativa:</b> {escape(reconciliation.review_justification or '-')}",
                    styles["BodyText"],
                ),
                Spacer(1, 5),
            ])
            comparisons = [["Metrica", "PDF", "API", "Diferenca", "Status"]]
            comparisons.extend([
                [
                    str(item.get("metric") or "-"),
                    str(item.get("pdf") or "-"),
                    str(item.get("api") or "-"),
                    str(item.get("difference") or "-"),
                    str(item.get("status") or "-"),
                ]
                for item in reconciliation.comparisons
            ])
            story.extend([self._table(comparisons, [36 * mm, 32 * mm, 32 * mm, 32 * mm, 34 * mm]), Spacer(1, 10)])

        story.extend([PageBreak(), Paragraph("Trilha de auditoria", styles["Heading1"])])
        events = [["Data/hora", "Ação", "Autor", "Referência"]]
        events.extend([
            [
                Paragraph(event.at.strftime("%d/%m/%Y %H:%M:%S"), styles["BodyText"]),
                Paragraph(escape(event.action), styles["BodyText"]),
                Paragraph(escape(event.actor), styles["BodyText"]),
                Paragraph(escape(event.evidence or event.item_id or "-"), styles["BodyText"]),
            ]
            for event in run.eventos
        ])
        story.append(self._table(events, [38 * mm, 42 * mm, 35 * mm, 55 * mm]))
        story.extend([
            Spacer(1, 14),
            Paragraph(
                "Este dossiê registra a decisão humana e suas evidências. O PDF anexado "
                "não substitui os fatos coletados da API WebPosto.", styles["BodyText"],
            ),
        ])
        doc.build(story, onFirstPage=self._footer, onLaterPages=self._footer)
        return output.getvalue()

    @staticmethod
    def _table(data: list[list], widths: list[float]) -> Table:
        table = Table(data, colWidths=widths, repeatRows=1 if len(data) > 2 else 0)
        table.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#DDE9E4")),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.HexColor("#12372A")),
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
            ("FONTNAME", (0, 1), (-1, -1), "Helvetica"),
            ("FONTSIZE", (0, 0), (-1, -1), 8),
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#AAB7B1")),
            ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#F7F9F8")]),
            ("LEFTPADDING", (0, 0), (-1, -1), 5),
            ("RIGHTPADDING", (0, 0), (-1, -1), 5),
            ("TOPPADDING", (0, 0), (-1, -1), 4),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
        ]))
        return table

    @staticmethod
    def _footer(canvas, doc) -> None:
        canvas.saveState()
        canvas.setFont("Helvetica", 8)
        canvas.setFillColor(colors.HexColor("#667085"))
        canvas.drawString(18 * mm, 10 * mm, "LOGOS SPACE - Dossiê de Auditoria")
        canvas.drawRightString(192 * mm, 10 * mm, f"Página {doc.page}")
        canvas.restoreState()
