from __future__ import annotations

import json
from dataclasses import dataclass
from decimal import Decimal, InvalidOperation
from typing import Any

import requests

BASE_URL = "http://127.0.0.1:8041"
TARGET_EMPRESA = 11495


@dataclass
class Period:
    label: str
    data_inicial: str
    data_final: str


def to_decimal(value: Any) -> Decimal:
    if value is None:
        return Decimal("0")
    text = str(value).strip().replace("R$", "").replace(" ", "")
    if "," in text and "." in text:
        text = text.replace(".", "").replace(",", ".")
    elif "," in text:
        text = text.replace(",", ".")
    try:
        return Decimal(text)
    except (InvalidOperation, ValueError):
        return Decimal("0")


def fetch_json(path: str, params: dict[str, Any], timeout: int = 25) -> tuple[dict[str, Any] | None, str | None]:
    url = f"{BASE_URL}{path}"
    try:
        resp = requests.get(url, params=params, timeout=timeout)
        resp.raise_for_status()
        return resp.json(), None
    except Exception as exc:  # noqa: BLE001
        return None, str(exc)


def fetch_paginated(
    path: str,
    base_params: dict[str, Any],
    data_key: str = "data",
    limit: int = 200,
    max_pages: int = 1,
) -> tuple[list[dict[str, Any]], list[str]]:
    rows: list[dict[str, Any]] = []
    errors: list[str] = []
    page = 1
    while True:
        params = {**base_params, "page": page, "limit": limit}
        payload, err = fetch_json(path, params)
        if err:
            errors.append(err)
            break
        if not payload:
            break
        data = payload.get("data") or {}
        page_rows = data.get(data_key) if isinstance(data, dict) else []
        if not isinstance(page_rows, list):
            page_rows = []
        rows.extend([r for r in page_rows if isinstance(r, dict)])
        total = int(data.get("total") or len(rows)) if isinstance(data, dict) else len(rows)
        if len(page_rows) == 0 or len(rows) >= total:
            break
        page += 1
        if page > max_pages:
            errors.append("pagination_limit_reached")
            break
    return rows, errors


def reconcile_period(period: Period) -> dict[str, Any]:
    print(f"[reconcile] period={period.label} {period.data_inicial}..{period.data_final}")
    params = {
        "dataInicial": period.data_inicial,
        "dataFinal": period.data_final,
        "empresaCodigo": TARGET_EMPRESA,
    }

    expenses_rows, expenses_errors = fetch_paginated("/v1/financial/expenses", params)
    accounts_rows, accounts_errors = fetch_paginated("/v1/financial/accounts-payable", params)
    sales_rows, sales_errors = fetch_paginated("/v1/sales", params)

    sales_head, sales_head_err = fetch_json("/v1/sales", {**params, "page": 1, "limit": 1})
    overview, overview_err = fetch_json("/v1/financial/overview", params)
    kpi, kpi_err = fetch_json("/api/v1/kpis", params)
    dre, dre_err = fetch_json("/api/v1/dre", params)

    expenses_sum = sum((to_decimal(r.get("valor")) for r in expenses_rows), Decimal("0"))
    accounts_sum = sum((to_decimal(r.get("valor")) for r in accounts_rows), Decimal("0"))
    sales_sum = sum((to_decimal(r.get("totalVenda")) for r in sales_rows), Decimal("0"))
    sales_items_sum = sum((to_decimal(r.get("itens")) for r in sales_rows), Decimal("0"))

    sales_consolidado = (((sales_head or {}).get("data") or {}).get("consolidado") or {}) if sales_head else {}
    sales_consolidado_total = to_decimal(sales_consolidado.get("total_vendas"))
    sales_consolidado_qtd = int(sales_consolidado.get("qtd_vendas") or 0)

    kpi_data = (kpi or {}).get("data") if isinstance(kpi, dict) else None
    dre_data = (dre or {}).get("data") if isinstance(dre, dict) else None
    ov_data = (overview or {}).get("data") if isinstance(overview, dict) else None

    kpi_faturamento = to_decimal((kpi_data or {}).get("faturamento"))
    kpi_despesas = to_decimal((kpi_data or {}).get("despesasTotais"))
    kpi_resultado = to_decimal((kpi_data or {}).get("resultadoOperacional"))
    kpi_ticket = to_decimal((kpi_data or {}).get("ticketMedio"))
    kpi_qtd_vendas = int((kpi_data or {}).get("qtdVendas") or 0)

    dre_receitas = to_decimal((dre_data or {}).get("receitas"))
    dre_custos = to_decimal((dre_data or {}).get("custosProduto"))
    dre_despesas = to_decimal((dre_data or {}).get("outrasDespesas"))
    dre_resultado = to_decimal((dre_data or {}).get("resultadoOperacional"))

    overview_consolidado = (ov_data or {}).get("consolidado") if isinstance(ov_data, dict) else {}
    ov_total_despesas = to_decimal((overview_consolidado or {}).get("total_despesas"))
    ov_total_a_pagar = to_decimal((overview_consolidado or {}).get("total_a_pagar"))

    dre_formula_result = dre_receitas - dre_custos - dre_despesas
    kpi_formula_result = kpi_faturamento - kpi_despesas
    kpi_formula_ticket = (kpi_faturamento / Decimal(kpi_qtd_vendas)) if kpi_qtd_vendas else Decimal("0")

    sample_10 = expenses_rows[:10]
    sample_10_sum = sum((to_decimal(r.get("valor")) for r in sample_10), Decimal("0"))

    return {
        "period": {
            "label": period.label,
            "dataInicial": period.data_inicial,
            "dataFinal": period.data_final,
        },
        "rows": {
            "expenses": len(expenses_rows),
            "accountsPayable": len(accounts_rows),
            "sales": len(sales_rows),
        },
        "totals": {
            "expensesTableSum": str(expenses_sum),
            "accountsTableSum": str(accounts_sum),
            "salesTableSum": str(sales_sum),
            "salesItemsTableSum": str(sales_items_sum),
            "salesConsolidadoTotal": str(sales_consolidado_total),
            "salesConsolidadoQtd": sales_consolidado_qtd,
            "overviewTotalDespesas": str(ov_total_despesas),
            "overviewTotalAPagar": str(ov_total_a_pagar),
            "kpiFaturamento": str(kpi_faturamento),
            "kpiDespesas": str(kpi_despesas),
            "kpiResultado": str(kpi_resultado),
            "kpiTicketMedio": str(kpi_ticket),
            "kpiQtdVendas": kpi_qtd_vendas,
            "dreReceitas": str(dre_receitas),
            "dreCustos": str(dre_custos),
            "dreOutrasDespesas": str(dre_despesas),
            "dreResultado": str(dre_resultado),
        },
        "checks": {
            "salesTableVsConsolidado": str(sales_sum - sales_consolidado_total),
            "kpiReceitaVsSalesConsolidado": str(kpi_faturamento - sales_consolidado_total),
            "kpiDespesaVsExpensesTable": str(kpi_despesas - expenses_sum),
            "kpiFormulaResultadoDiff": str(kpi_resultado - kpi_formula_result),
            "kpiFormulaTicketDiff": str(kpi_ticket - kpi_formula_ticket),
            "dreFormulaDiff": str(dre_resultado - dre_formula_result),
            "dreReceitasVsSalesConsolidado": str(dre_receitas - sales_consolidado_total),
            "overviewDespesasVsExpensesTable": str(ov_total_despesas - expenses_sum),
            "overviewAPagarVsAccountsTable": str(ov_total_a_pagar - accounts_sum),
        },
        "sample10": {
            "count": len(sample_10),
            "sum": str(sample_10_sum),
            "rows": [
                {
                    "data": r.get("data"),
                    "filial": r.get("filial"),
                    "planoConta": r.get("planoConta"),
                    "valor": r.get("valor"),
                }
                for r in sample_10
            ],
        },
        "errors": {
            "expenses": expenses_errors,
            "accountsPayable": accounts_errors,
            "sales": sales_errors,
            "overview": overview_err,
            "kpi": kpi_err,
            "dre": dre_err,
            "salesConsolidado": sales_head_err,
        },
    }


def main() -> None:
    periods = [
        Period(label="dia_2026_06_06", data_inicial="2026-06-06", data_final="2026-06-06"),
        Period(label="semana_2026_06_01_ate_2026_06_07", data_inicial="2026-06-01", data_final="2026-06-07"),
    ]

    print("[reconcile] starting")
    report = {
        "baseUrl": BASE_URL,
        "empresaCodigo": TARGET_EMPRESA,
        "periods": [reconcile_period(p) for p in periods],
    }

    with open("financial_reconciliation_result.json", "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)

    print("[reconcile] done -> financial_reconciliation_result.json")
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
