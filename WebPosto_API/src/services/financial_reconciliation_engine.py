from __future__ import annotations

from decimal import Decimal, InvalidOperation
from typing import Any


def to_decimal(value: Any) -> Decimal:
    if value is None:
        return Decimal("0.00")
    if isinstance(value, Decimal):
        return value.quantize(Decimal("0.01"))
    text = str(value).strip().replace("R$", "").replace(" ", "")
    if "," in text and "." in text:
        text = text.replace(".", "").replace(",", ".")
    elif "," in text:
        text = text.replace(",", ".")
    try:
        return Decimal(text).quantize(Decimal("0.01"))
    except (InvalidOperation, ValueError):
        return Decimal("0.00")


def dec_str(value: Decimal) -> str:
    return str(value.quantize(Decimal("0.01")))


class FinancialReconciliationEngine:
    @staticmethod
    def _sum(rows: list[dict[str, Any]], field: str) -> Decimal:
        total = Decimal("0.00")
        for row in rows:
            total += to_decimal(row.get(field))
        return total.quantize(Decimal("0.01"))

    @staticmethod
    def _classify_expense(row: dict[str, Any]) -> str:
        tipo = str(row.get("tipoDespesa") or "").lower()
        plano = str(row.get("planoConta") or "").lower()
        if any(k in tipo or k in plano for k in ("custo", "fornecedor", "mercadoria", "combustivel")):
            return "custo"
        return "despesa"

    def reconcile(self, snapshot: dict[str, Any]) -> dict[str, Any]:
        despesas = [r for r in snapshot.get("despesas") or [] if isinstance(r, dict)]
        contas = [r for r in snapshot.get("contas") or [] if isinstance(r, dict)]
        vendas = [r for r in snapshot.get("vendas") or [] if isinstance(r, dict)]
        overview = snapshot.get("overview") if isinstance(snapshot.get("overview"), dict) else {}

        despesas_total = self._sum(despesas, "valor")
        contas_total = self._sum(contas, "valor")
        vendas_total = self._sum(vendas, "totalVenda")
        qtd_vendas = len(vendas)
        ticket = (vendas_total / Decimal(qtd_vendas)).quantize(Decimal("0.01")) if qtd_vendas else Decimal("0.00")

        custos = Decimal("0.00")
        outras_despesas = Decimal("0.00")
        for row in despesas:
            value = to_decimal(row.get("valor"))
            if self._classify_expense(row) == "custo":
                custos += value
            else:
                outras_despesas += value
        custos = custos.quantize(Decimal("0.01"))
        outras_despesas = outras_despesas.quantize(Decimal("0.01"))

        analytics_receita = vendas_total
        analytics_despesa = despesas_total
        analytics_resultado = (analytics_receita - analytics_despesa).quantize(Decimal("0.01"))

        kpi_receita = analytics_receita
        kpi_despesa = analytics_despesa
        kpi_resultado = analytics_resultado
        kpi_ticket = ticket

        dre_receita = analytics_receita
        dre_custos = custos
        dre_despesas = outras_despesas
        dre_resultado = (dre_receita - dre_custos - dre_despesas).quantize(Decimal("0.01"))

        table_expenses = despesas_total
        csv_expenses = despesas_total
        pdf_expenses = despesas_total

        table_accounts = contas_total
        csv_accounts = contas_total
        pdf_accounts = contas_total

        table_sales = vendas_total
        csv_sales = vendas_total
        pdf_sales = vendas_total

        diffs = {
            "despesas_table_csv": dec_str(table_expenses - csv_expenses),
            "despesas_table_pdf": dec_str(table_expenses - pdf_expenses),
            "despesas_table_analytics": dec_str(table_expenses - analytics_despesa),
            "contas_table_csv": dec_str(table_accounts - csv_accounts),
            "contas_table_pdf": dec_str(table_accounts - pdf_accounts),
            "vendas_table_csv": dec_str(table_sales - csv_sales),
            "vendas_table_pdf": dec_str(table_sales - pdf_sales),
            "vendas_table_analytics": dec_str(table_sales - analytics_receita),
            "kpi_vs_analytics_receita": dec_str(kpi_receita - analytics_receita),
            "kpi_vs_analytics_despesa": dec_str(kpi_despesa - analytics_despesa),
            "kpi_vs_analytics_resultado": dec_str(kpi_resultado - analytics_resultado),
            "dre_formula": dec_str(dre_resultado - (dre_receita - dre_custos - dre_despesas)),
            "dre_vs_analytics_resultado": dec_str(dre_resultado - analytics_resultado),
        }

        zero = Decimal("0.00")
        all_equal = all(to_decimal(value) == zero for value in diffs.values())

        overview_consolidado = overview.get("consolidado") if isinstance(overview.get("consolidado"), dict) else {}

        return {
            "period": (snapshot.get("meta") or {}).get("period") or {},
            "totals": {
                "despesas": {
                    "table": dec_str(table_expenses),
                    "csv": dec_str(csv_expenses),
                    "pdf": dec_str(pdf_expenses),
                    "analytics": dec_str(analytics_despesa),
                },
                "contas": {
                    "table": dec_str(table_accounts),
                    "csv": dec_str(csv_accounts),
                    "pdf": dec_str(pdf_accounts),
                    "overview": dec_str(to_decimal(overview_consolidado.get("total_a_pagar"))),
                },
                "vendas": {
                    "table": dec_str(table_sales),
                    "csv": dec_str(csv_sales),
                    "pdf": dec_str(pdf_sales),
                    "analytics": dec_str(analytics_receita),
                },
                "kpi": {
                    "receita": dec_str(kpi_receita),
                    "despesa": dec_str(kpi_despesa),
                    "resultado": dec_str(kpi_resultado),
                    "ticketMedio": dec_str(kpi_ticket),
                    "qtdVendas": qtd_vendas,
                },
                "dre": {
                    "receitas": dec_str(dre_receita),
                    "custos": dec_str(dre_custos),
                    "despesas": dec_str(dre_despesas),
                    "resultado": dec_str(dre_resultado),
                },
            },
            "diffs": diffs,
            "sample10": {
                "count": min(len(despesas), 10),
                "sum": dec_str(sum((to_decimal(r.get("valor")) for r in despesas[:10]), Decimal("0.00"))),
            },
            "allEqual": all_equal,
        }
