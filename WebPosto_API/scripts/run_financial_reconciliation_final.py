from __future__ import annotations

from pathlib import Path

from src.services.financial_reconciliation_engine import FinancialReconciliationEngine
from src.services.financial_snapshot_service import FinancialSnapshotService, SnapshotPeriod


def format_money(value: str) -> str:
    text = str(value)
    if "." not in text:
        text = f"{text}.00"
    inteiro, frac = text.split(".", 1)
    inteiro_fmt = f"{int(inteiro):,}".replace(",", ".")
    return f"R$ {inteiro_fmt},{frac[:2].ljust(2, '0')}"


def build_markdown(results: list[dict]) -> str:
    lines: list[str] = []
    lines.append("# Financial Reconciliation Final")
    lines.append("")
    lines.append("## Escopo")
    lines.append("- Reconciliação determinística por snapshot local")
    lines.append("- Sem dependência do navegador")
    lines.append("- Períodos: 06/06/2026 e 01/06/2026 a 07/06/2026")
    lines.append("")

    all_equal = True

    for item in results:
        period = item.get("period") or {}
        totals = item.get("totals") or {}
        diffs = item.get("diffs") or {}
        equal = bool(item.get("allEqual"))
        all_equal = all_equal and equal

        label = f"{period.get('dataInicial')} até {period.get('dataFinal')}"
        lines.append(f"## Período {label}")
        lines.append("")
        lines.append("### Evidência Matemática")

        despesas = totals.get("despesas") or {}
        contas = totals.get("contas") or {}
        vendas = totals.get("vendas") or {}
        kpi = totals.get("kpi") or {}
        dre = totals.get("dre") or {}

        lines.append(f"- Tabela Despesas: {format_money(despesas.get('table', '0'))}")
        lines.append(f"- CSV Despesas: {format_money(despesas.get('csv', '0'))}")
        lines.append(f"- PDF Despesas: {format_money(despesas.get('pdf', '0'))}")
        lines.append(f"- Analytics Despesas: {format_money(despesas.get('analytics', '0'))}")
        lines.append(f"- Tabela Contas: {format_money(contas.get('table', '0'))}")
        lines.append(f"- CSV Contas: {format_money(contas.get('csv', '0'))}")
        lines.append(f"- PDF Contas: {format_money(contas.get('pdf', '0'))}")
        lines.append(f"- Tabela Vendas: {format_money(vendas.get('table', '0'))}")
        lines.append(f"- CSV Vendas: {format_money(vendas.get('csv', '0'))}")
        lines.append(f"- PDF Vendas: {format_money(vendas.get('pdf', '0'))}")
        lines.append(f"- Analytics Vendas: {format_money(vendas.get('analytics', '0'))}")
        lines.append(f"- KPI Receita: {format_money(kpi.get('receita', '0'))}")
        lines.append(f"- KPI Despesa: {format_money(kpi.get('despesa', '0'))}")
        lines.append(f"- KPI Resultado: {format_money(kpi.get('resultado', '0'))}")
        lines.append(f"- KPI Ticket Médio: {format_money(kpi.get('ticketMedio', '0'))}")
        lines.append(f"- DRE Receitas: {format_money(dre.get('receitas', '0'))}")
        lines.append(f"- DRE Custos: {format_money(dre.get('custos', '0'))}")
        lines.append(f"- DRE Despesas: {format_money(dre.get('despesas', '0'))}")
        lines.append(f"- DRE Resultado: {format_money(dre.get('resultado', '0'))}")
        lines.append("")

        lines.append("### Diferenças")
        for key, value in diffs.items():
            lines.append(f"- {key}: {value}")
        lines.append("")
        lines.append(f"### Conclusão do período: {'OK' if equal else 'DIVERGENTE'}")
        lines.append("")

    lines.append("## Resultado Final")
    lines.append(f"- Existe divergência financeira? {'NÃO' if all_equal else 'SIM'}")
    lines.append("")
    lines.append("## Critério de aceite")
    lines.append("- Tabela = CSV = PDF = Analytics = KPI = DRE")
    lines.append("- Diferença exigida: 0,00")

    return "\n".join(lines)


def main() -> None:
    snapshot_service = FinancialSnapshotService(base_url="http://127.0.0.1:8041", timeout=20)
    engine = FinancialReconciliationEngine()

    periods = [
        SnapshotPeriod(data_inicial="2026-06-06", data_final="2026-06-06", empresa_codigo=11495),
        SnapshotPeriod(data_inicial="2026-06-01", data_final="2026-06-07", empresa_codigo=11495),
    ]

    snapshots_dir = Path("snapshots")
    snapshots_dir.mkdir(parents=True, exist_ok=True)

    results: list[dict] = []
    for period in periods:
        snapshot = snapshot_service.collect_snapshot(period)
        snapshot_service.save_snapshot(snapshot, period, output_dir=snapshots_dir)
        results.append(engine.reconcile(snapshot))

    markdown = build_markdown(results)
    Path("financial_reconciliation_final.md").write_text(markdown, encoding="utf-8")

    print(markdown)


if __name__ == "__main__":
    main()
