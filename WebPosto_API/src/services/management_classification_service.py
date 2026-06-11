"""F03.3 — Management Classification Intelligence (camada gerencial aditiva)."""
from __future__ import annotations

import re
from collections import Counter, defaultdict
from decimal import Decimal
from typing import Any

from src.services.network_financial_overview_service import FinancialOverviewFilters

MANAGEMENT_GROUPS = (
    "OPERACIONAL",
    "PESSOAL",
    "TESOURARIA",
    "PERDAS",
    "ADMINISTRATIVO",
    "FINANCEIRO",
)

MANAGEMENT_CLASSES = (
    "SALARIO",
    "QUINZENA",
    "VALE",
    "EXTRA",
    "FOLGUISTA",
    "PERDA_CAIXA_FUNCIONARIO",
    "PERDA_CAIXA_EMPRESA",
    "ENERGIA",
    "AGUA",
    "TELEFONIA",
    "BOBINA",
    "EMPRESTIMO",
    "ADIANTAMENTO",
    "MOVIMENTACAO_CAIXA",
    "AJUSTE_OPERACIONAL",
    "OUTROS",
)

GROUP_LABELS = {
    "OPERACIONAL": "Operacional",
    "PESSOAL": "Pessoal",
    "TESOURARIA": "Tesouraria",
    "PERDAS": "Perdas",
    "ADMINISTRATIVO": "Administrativo",
    "FINANCEIRO": "Financeiro",
}

CLASS_LABELS = {
    "SALARIO": "Salário",
    "QUINZENA": "Quinzena",
    "VALE": "Vale",
    "EXTRA": "Extra / Hora Extra",
    "FOLGUISTA": "Folguista",
    "PERDA_CAIXA_FUNCIONARIO": "Perda Caixa Funcionário",
    "PERDA_CAIXA_EMPRESA": "Perda Caixa Empresa",
    "ENERGIA": "Energia",
    "AGUA": "Água",
    "TELEFONIA": "Telefonia",
    "BOBINA": "Bobina",
    "EMPRESTIMO": "Empréstimo",
    "ADIANTAMENTO": "Adiantamento",
    "MOVIMENTACAO_CAIXA": "Movimentação Caixa",
    "AJUSTE_OPERACIONAL": "Ajuste Operacional",
    "OUTROS": "Outros",
}

DRE_IMPACTS = ("SIM", "NAO", "PARCIAL")
CASHFLOW_IMPACTS = ("SIM", "NAO", "PARCIAL")

_SUB_TO_CLASS: dict[str, str] = {
    "BOBINA_TERMICA": "BOBINA",
    "ENERGIA": "ENERGIA",
    "AGUA": "AGUA",
    "TELEFONIA": "TELEFONIA",
    "VALE_FUNCIONARIO": "VALE",
    "ADIANTAMENTO": "ADIANTAMENTO",
    "EMPRESTIMO_FUNCIONARIO": "EMPRESTIMO",
    "QUEBRA_CAIXA": "PERDA_CAIXA_FUNCIONARIO",
    "DIFERENCA_FECHAMENTO": "PERDA_CAIXA_FUNCIONARIO",
    "AJUSTE_MANUAL": "AJUSTE_OPERACIONAL",
    "MOVIMENTACAO_CAIXA": "MOVIMENTACAO_CAIXA",
    "TROCO": "MOVIMENTACAO_CAIXA",
    "FUNDO_CAIXA": "MOVIMENTACAO_CAIXA",
    "SANGRIA": "MOVIMENTACAO_CAIXA",
    "SUPRIMENTO": "MOVIMENTACAO_CAIXA",
}

_DRE_BY_CLASS: dict[str, str] = {
    "SALARIO": "SIM",
    "QUINZENA": "SIM",
    "VALE": "NAO",
    "EXTRA": "SIM",
    "FOLGUISTA": "SIM",
    "PERDA_CAIXA_FUNCIONARIO": "NAO",
    "PERDA_CAIXA_EMPRESA": "SIM",
    "ENERGIA": "SIM",
    "AGUA": "SIM",
    "TELEFONIA": "SIM",
    "BOBINA": "SIM",
    "EMPRESTIMO": "NAO",
    "ADIANTAMENTO": "NAO",
    "MOVIMENTACAO_CAIXA": "NAO",
    "AJUSTE_OPERACIONAL": "PARCIAL",
    "OUTROS": "PARCIAL",
}

_CASHFLOW_BY_CLASS: dict[str, str] = {
    "SALARIO": "SIM",
    "QUINZENA": "SIM",
    "VALE": "SIM",
    "EXTRA": "SIM",
    "FOLGUISTA": "SIM",
    "PERDA_CAIXA_FUNCIONARIO": "NAO",
    "PERDA_CAIXA_EMPRESA": "SIM",
    "ENERGIA": "SIM",
    "AGUA": "SIM",
    "TELEFONIA": "SIM",
    "BOBINA": "SIM",
    "EMPRESTIMO": "SIM",
    "ADIANTAMENTO": "SIM",
    "MOVIMENTACAO_CAIXA": "SIM",
    "AJUSTE_OPERACIONAL": "PARCIAL",
    "OUTROS": "PARCIAL",
}


def _norm_text(value: Any) -> str:
    return re.sub(r"\s+", " ", str(value or "").upper().strip())


def _money(value: Any) -> Decimal:
    try:
        return Decimal(str(value or 0)).quantize(Decimal("0.01"))
    except Exception:
        return Decimal("0")


def _resolve_class(nature: str, sub: str, blob: str) -> str:
    if sub in _SUB_TO_CLASS:
        return _SUB_TO_CLASS[sub]
    if nature == "ADIANTAMENTO":
        if re.search(r"QUINZENA", blob, re.I):
            return "QUINZENA"
        if re.search(r"SALAR", blob, re.I):
            return "SALARIO"
        if re.search(r"FOLGUIST|FOLGA", blob, re.I):
            return "FOLGUISTA"
        if re.search(r"EXTRA|HORA\s*EXTRA", blob, re.I):
            return "EXTRA"
        if re.search(r"EMPREST", blob, re.I):
            return "EMPRESTIMO"
        return "VALE"
    if nature == "AJUSTE_OPERACIONAL":
        if re.search(r"QUEBRA|DIFEREN", blob, re.I):
            return "PERDA_CAIXA_FUNCIONARIO"
        return "AJUSTE_OPERACIONAL"
    if nature == "MOVIMENTACAO_CAIXA":
        return "MOVIMENTACAO_CAIXA"
    if sub in ("ENERGIA", "AGUA", "TELEFONIA", "BOBINA_TERMICA"):
        return _SUB_TO_CLASS.get(sub, sub.replace("_TERMICA", ""))
    return "OUTROS"


def _resolve_group(nature: str, mgmt_class: str) -> str:
    if mgmt_class in ("SALARIO", "QUINZENA", "EXTRA", "FOLGUISTA"):
        return "PESSOAL"
    if mgmt_class in ("VALE", "EMPRESTIMO", "ADIANTAMENTO"):
        return "TESOURARIA"
    if mgmt_class in ("PERDA_CAIXA_FUNCIONARIO", "PERDA_CAIXA_EMPRESA", "AJUSTE_OPERACIONAL"):
        return "PERDAS"
    if mgmt_class == "MOVIMENTACAO_CAIXA":
        return "OPERACIONAL"
    if nature == "DESPESA_OPERACIONAL":
        return "OPERACIONAL"
    if nature == "DESPESA_FINANCEIRA":
        if mgmt_class in ("ENERGIA", "AGUA", "TELEFONIA", "BOBINA"):
            return "ADMINISTRATIVO"
        return "FINANCEIRO"
    return "OPERACIONAL"


def _employee_accountability(mgmt_class: str, row: dict[str, Any]) -> bool:
    if mgmt_class == "PERDA_CAIXA_FUNCIONARIO":
        return True
    if mgmt_class in ("VALE", "EMPRESTIMO", "ADIANTAMENTO") and row.get("funcionarioCodigo"):
        return True
    return False


class ManagementClassificationService:
    """Camada gerencial aditiva — preserva expenseNature/expenseSubNature."""

    def classify_row(self, row: dict[str, Any]) -> dict[str, Any]:
        nature = str(row.get("expenseNature") or "")
        sub = str(row.get("expenseSubNature") or "")
        blob = _norm_text(
            " ".join(
                str(row.get(k) or "")
                for k in ("descricao", "planoConta", "tipoDespesa", "eventoOperacional", "categoriaOperacional")
            )
        )
        mgmt_class = _resolve_class(nature, sub, blob)
        mgmt_group = _resolve_group(nature, mgmt_class)
        dre = _DRE_BY_CLASS.get(mgmt_class, "PARCIAL")
        cashflow = _CASHFLOW_BY_CLASS.get(mgmt_class, "PARCIAL")
        accountability = _employee_accountability(mgmt_class, row)

        return {
            **row,
            "expenseManagementGroup": mgmt_group,
            "expenseManagementClass": mgmt_class,
            "expenseManagementGroupLabel": GROUP_LABELS.get(mgmt_group, mgmt_group),
            "expenseManagementClassLabel": CLASS_LABELS.get(mgmt_class, mgmt_class),
            "dreImpact": dre,
            "cashFlowImpact": cashflow,
            "employeeAccountability": accountability,
        }

    @staticmethod
    def filter_rows(rows: list[dict[str, Any]], filters: FinancialOverviewFilters) -> list[dict[str, Any]]:
        out = rows
        groups = filters.expense_management_groups
        if groups:
            allowed = {g.strip().upper() for g in groups}
            out = [r for r in out if str(r.get("expenseManagementGroup") or "").upper() in allowed]
        classes = filters.expense_management_classes
        if classes:
            allowed = {c.strip().upper() for c in classes}
            out = [r for r in out if str(r.get("expenseManagementClass") or "").upper() in allowed]
        if filters.dre_impact:
            dre = str(filters.dre_impact).strip().upper()
            out = [r for r in out if str(r.get("dreImpact") or "").upper() == dre]
        if filters.cashflow_impact:
            cf = str(filters.cashflow_impact).strip().upper()
            out = [r for r in out if str(r.get("cashFlowImpact") or "").upper() == cf]
        return out

    def summarize(self, rows: list[dict[str, Any]]) -> dict[str, Any]:
        total = len(rows)
        if total == 0:
            return {
                "totalRecords": 0,
                "byGroup": {},
                "byClass": {},
                "valorByGroup": {},
                "valorByClass": {},
                "pctByGroup": {},
                "dreImpact": {"SIM": 0, "NAO": 0, "PARCIAL": 0},
                "valorDreSim": 0.0,
                "valorDreNao": 0.0,
                "cashFlowImpact": {"SIM": 0, "NAO": 0, "PARCIAL": 0},
                "valorCashflowSim": 0.0,
                "employeeAccountabilityCount": 0,
            }

        by_group: Counter[str] = Counter()
        by_class: Counter[str] = Counter()
        valor_group: dict[str, Decimal] = defaultdict(lambda: Decimal("0"))
        valor_class: dict[str, Decimal] = defaultdict(lambda: Decimal("0"))
        dre_counts: Counter[str] = Counter()
        dre_valor: dict[str, Decimal] = defaultdict(lambda: Decimal("0"))
        cf_counts: Counter[str] = Counter()
        accountability = 0
        total_valor = Decimal("0")

        for row in rows:
            grp = str(row.get("expenseManagementGroup") or "OUTROS")
            cls = str(row.get("expenseManagementClass") or "OUTROS")
            val = _money(row.get("valor"))
            total_valor += val
            by_group[grp] += 1
            by_class[cls] += 1
            valor_group[grp] += val
            valor_class[cls] += val
            dre = str(row.get("dreImpact") or "PARCIAL")
            dre_counts[dre] += 1
            dre_valor[dre] += val
            cf = str(row.get("cashFlowImpact") or "PARCIAL")
            cf_counts[cf] += 1
            if row.get("employeeAccountability"):
                accountability += 1

        pct_group = {
            k: round(by_group[k] / total * 100, 2) for k in MANAGEMENT_GROUPS if by_group.get(k)
        }

        return {
            "totalRecords": total,
            "byGroup": dict(by_group),
            "byClass": dict(by_class.most_common(30)),
            "valorByGroup": {k: float(v) for k, v in valor_group.items()},
            "valorByClass": {k: float(v) for k, v in valor_class.items()},
            "pctByGroup": pct_group,
            "dreImpact": dict(dre_counts),
            "valorDreSim": float(dre_valor.get("SIM", Decimal("0"))),
            "valorDreNao": float(dre_valor.get("NAO", Decimal("0"))),
            "valorDreParcial": float(dre_valor.get("PARCIAL", Decimal("0"))),
            "cashFlowImpact": dict(cf_counts),
            "valorCashflowSim": float(
                sum(_money(r.get("valor")) for r in rows if r.get("cashFlowImpact") == "SIM")
            ),
            "employeeAccountabilityCount": accountability,
            "totalValor": float(total_valor),
        }

    def build_resumo_cards(self, summary: dict[str, Any]) -> dict[str, dict[str, Any]]:
        valor = summary.get("valorByGroup") or {}
        counts = summary.get("byGroup") or {}
        pct = summary.get("pctByGroup") or {}
        cards = {}
        for group in MANAGEMENT_GROUPS:
            cards[group] = {
                "label": GROUP_LABELS[group],
                "count": counts.get(group, 0),
                "valor": str(Decimal(str(valor.get(group, 0))).quantize(Decimal("0.01"))),
                "pct": pct.get(group, 0.0),
            }
        return cards

    async def build_management_payload(
        self,
        overview: Any,
        filters: FinancialOverviewFilters,
        lineage_service: Any,
        semantic_service: Any,
    ) -> dict[str, Any]:
        from src.services.expense_lineage_service import ExpenseLineageService
        from src.services.expense_semantic_service import ExpenseSemanticService

        lineage = lineage_service or ExpenseLineageService()
        semantic = semantic_service or ExpenseSemanticService()
        ctx = await lineage.build_context(overview, filters)
        rows, err = await overview._load_screen_expenses(filters)
        if err:
            return {"error": err.error, "rows": [], "summary": {}}
        enriched = [
            self.classify_row(semantic.classify_row(lineage.enrich_row(r, ctx)))
            for r in rows
        ]
        summary = self.summarize(enriched)
        return {
            "rows": enriched,
            "summary": summary,
            "cards": self.build_resumo_cards(summary),
            "taxonomy": {
                "groups": list(MANAGEMENT_GROUPS),
                "classes": list(MANAGEMENT_CLASSES),
                "groupLabels": GROUP_LABELS,
                "classLabels": CLASS_LABELS,
                "dreImpacts": list(DRE_IMPACTS),
                "cashFlowImpacts": list(CASHFLOW_IMPACTS),
            },
        }
