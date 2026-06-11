"""F03.2 — Expense Semantic Intelligence & Business Classification."""
from __future__ import annotations

import re
from collections import Counter, defaultdict
from decimal import Decimal
from typing import Any

from src.services.network_financial_overview_service import FinancialOverviewFilters, NetworkFinancialOverviewService

EXPENSE_NATURES = (
    "DESPESA_FINANCEIRA",
    "DESPESA_OPERACIONAL",
    "MOVIMENTACAO_CAIXA",
    "ADIANTAMENTO",
    "AJUSTE_OPERACIONAL",
)

NATURE_LABELS = {
    "DESPESA_FINANCEIRA": "Despesa Financeira",
    "DESPESA_OPERACIONAL": "Despesa Operacional",
    "MOVIMENTACAO_CAIXA": "Movimentação Caixa",
    "ADIANTAMENTO": "Adiantamento",
    "AJUSTE_OPERACIONAL": "Ajuste Operacional",
}

# Prioridade: ajuste > adiantamento > movimentação > financeiro/operacional
NATURE_RULES: list[tuple[str, list[str]]] = [
    (
        "AJUSTE_OPERACIONAL",
        [
            r"QUEBRA\s*DE\s*CAIXA|QUEBRA\s*CAIXA",
            r"DIFEREN[ÇC]A\s*DE\s*FECHAMENTO|DIF\s*FECHAMENTO",
            r"AJUSTE\s*MANUAL|\bAJUSTE\b",
            r"\bCORRE[ÇC][AÃ]O\b|\bCORRIG",
        ],
    ),
    (
        "ADIANTAMENTO",
        [
            r"VALE\s*FUNC|VALE\s*DE\s*FUNC",
            r"EMPREST\w*\s*FUNC|EMPREST\w*\s*FUNCION",
            r"\bADIANTAMENTO\b",
            r"REF\s*AO\s*SALAR|REF\s*A\s*SALAR|SALARIO|SALÁRIO",
        ],
    ),
    (
        "MOVIMENTACAO_CAIXA",
        [
            r"TROCO\s*INIC|\bTROCO\b",
            r"FUNDO\s*DE\s*CAIXA|FUNDO\s*CAIXA",
            r"\bSUPRIMENT",
            r"\bSANGRIA\b",
            r"\bRECOLHIMENT",
        ],
    ),
]

FINANCIAL_SUBNATURE_RULES: list[tuple[str, str]] = [
    ("BOBINA_TERMICA", r"BOBINA"),
    ("ENERGIA", r"ENERG|LUZ|ELETRIC"),
    ("AGUA", r"\bAGUA\b|\bÁGUA\b"),
    ("SERVICOS", r"SERVI[ÇC]O|TERCEIRIZ"),
    ("MANUTENCAO", r"MANUTEN"),
    ("IMPOSTOS", r"IMPOST|DAS\b|ISS\b|ICMS\b|FGTS\b|INSS\b"),
    ("CONTABILIDADE", r"CONTAB|ESCRITOR"),
    ("TELEFONIA", r"TELEFON|CELULAR|INTERNET|TIM\b|VIVO\b|CLARO\b"),
    ("ALUGUEL", r"ALUGUEL|LOCACAO|LOCAÇÃO"),
    ("COMBUSTIVEL", r"COMBUST|DIESEL|GASOLINA"),
    ("ALIMENTACAO", r"ALMO[ÇC]O|LANCHE|CAF[EÉ]|REFEI"),
    ("TRANSPORTE", r"UBER|TAXI|PASSAGEM|TRANSPORT"),
]

OPERATIONAL_SUBNATURE_RULES: list[tuple[str, str]] = [
    ("LIMPEZA", r"LIMPEZA|MATERIAL\s*LIMPEZA"),
    ("MATERIAL_OPERACIONAL", r"MATERIAL\s*OPER|BOBINA|COPO|DESCART|INSUMO|FARDAMENT"),
    ("EXPEDIENTE", r"EXPEDIENT|LANCHE|CAF[EÉ]"),
    ("CONSUMO_INTERNO", r"CONSUMO\s*INTERNO|AGUA\s*PARA\s*CONSUMO"),
]

CASH_MOVEMENT_SUBNATURES: dict[str, str] = {
    "Troco Inicial": "TROCO",
    "Troco": "TROCO",
    "Fundo de Caixa": "FUNDO_DE_CAIXA",
    "Suprimento": "SUPRIMENTO",
    "Sangria": "SANGRIA",
    "Empréstimo": "EMPRESTIMO_FUNCIONARIO",
    "Vale Funcionário": "VALE_FUNCIONARIO",
}

ADJUSTMENT_SUBNATURES: dict[str, str] = {
    "Quebra de Caixa": "QUEBRA_DE_CAIXA",
}


def _norm_text(v: Any) -> str:
    return re.sub(r"\s+", " ", str(v or "").strip().upper())


def _money(v: Any) -> Decimal:
    try:
        return Decimal(str(v or 0)).quantize(Decimal("0.01"))
    except Exception:
        return Decimal("0")


def _blob(row: dict[str, Any]) -> str:
    parts = [
        row.get("descricao"),
        row.get("planoConta"),
        row.get("categoriaOperacional"),
        row.get("eventoOperacional"),
        row.get("tipoDespesa"),
    ]
    return _norm_text(" ".join(str(p) for p in parts if p))


def _match_rules(blob: str, rules: list[tuple[str, list[str]]]) -> str | None:
    for nature, patterns in rules:
        for pattern in patterns:
            if re.search(pattern, blob, re.IGNORECASE):
                return nature
    return None


def _subnature_from_rules(blob: str, rules: list[tuple[str, str]]) -> str | None:
    for sub, pattern in rules:
        if re.search(pattern, blob, re.IGNORECASE):
            return sub
    return None


def _subnature_from_event(evento: str | None, mapping: dict[str, str], default: str) -> str:
    if not evento:
        return default
    return mapping.get(str(evento), default)


class ExpenseSemanticService:
    """Motor de classificação semântica — DESPESA ≠ MOVIMENTAÇÃO ≠ ADIANTAMENTO ≠ AJUSTE."""

    def classify_row(self, row: dict[str, Any]) -> dict[str, Any]:
        blob = _blob(row)
        evento = row.get("eventoOperacional")
        origem = str(row.get("origem") or "")
        origem_real = str(row.get("origemReal") or "")

        nature = _match_rules(blob, NATURE_RULES)
        confidence = 95
        reason = "pattern"

        if not nature:
            if origem == "financeiro" or origem_real == "Financeiro":
                nature = "DESPESA_FINANCEIRA"
                confidence = 90
                reason = "origem_financeira"
            else:
                nature = "DESPESA_OPERACIONAL"
                confidence = 85
                reason = "origem_operacional"

        sub = self._resolve_subnature(nature, blob, evento, row)
        if sub == "OUTROS" and reason == "origem_operacional":
            confidence = 80
        elif sub == "OUTROS":
            confidence = min(confidence, 75)

        return {
            **row,
            "expenseNature": nature,
            "expenseSubNature": sub,
            "expenseNatureLabel": NATURE_LABELS.get(nature, nature),
            "semanticConfidence": confidence,
            "semanticReason": reason,
            "impactsFinancialResult": nature == "DESPESA_FINANCEIRA",
        }

    def _resolve_subnature(
        self,
        nature: str,
        blob: str,
        evento: str | None,
        row: dict[str, Any],
    ) -> str:
        if nature == "DESPESA_FINANCEIRA":
            sub = _subnature_from_rules(blob, FINANCIAL_SUBNATURE_RULES)
            if sub:
                return sub
            plano = _norm_text(row.get("planoConta") or "")
            if plano and plano not in ("—", "-", "?"):
                return re.sub(r"[^A-Z0-9]+", "_", plano)[:40].strip("_") or "OUTROS"
            return "OUTROS"

        if nature == "DESPESA_OPERACIONAL":
            sub = _subnature_from_rules(blob, OPERATIONAL_SUBNATURE_RULES)
            if sub:
                return sub
            if evento:
                return re.sub(r"[^A-Z0-9]+", "_", _norm_text(evento))[:40] or "OUTROS"
            return "OUTROS"

        if nature == "MOVIMENTACAO_CAIXA":
            return _subnature_from_event(str(evento) if evento else None, CASH_MOVEMENT_SUBNATURES, "MOVIMENTACAO_CAIXA")

        if nature == "ADIANTAMENTO":
            if re.search(r"EMPREST", blob, re.I):
                return "EMPRESTIMO_FUNCIONARIO"
            if re.search(r"ADIANTAMENTO", blob, re.I):
                return "ADIANTAMENTO"
            return "VALE_FUNCIONARIO"

        if nature == "AJUSTE_OPERACIONAL":
            return _subnature_from_event(str(evento) if evento else None, ADJUSTMENT_SUBNATURES, "AJUSTE_OPERACIONAL")

        return "OUTROS"

    @staticmethod
    def filter_by_natures(rows: list[dict[str, Any]], filters: FinancialOverviewFilters) -> list[dict[str, Any]]:
        natures = filters.expense_natures
        if not natures:
            return rows
        allowed = {str(n).strip().upper() for n in natures}
        return [r for r in rows if str(r.get("expenseNature") or "").upper() in allowed]

    def summarize(self, rows: list[dict[str, Any]]) -> dict[str, Any]:
        total = len(rows)
        if total == 0:
            return {
                "totalRecords": 0,
                "classifiedRecords": 0,
                "unclassifiedRecords": 0,
                "classificationPct": 100.0,
                "avgSemanticConfidence": 0.0,
                "byNature": {},
                "bySubNature": {},
                "valorByNature": {},
                "pctByNature": {},
                "pctFinancialImpact": 0.0,
                "pctOperationalOnly": 0.0,
                "pctCashMovement": 0.0,
                "pctAdvance": 0.0,
                "pctAdjustment": 0.0,
                "topSubNatures": [],
            }

        classified = [r for r in rows if r.get("expenseNature")]
        unclassified = total - len(classified)
        confidences = [int(r.get("semanticConfidence") or 0) for r in classified]
        avg_conf = round(sum(confidences) / len(confidences), 1) if confidences else 0.0

        by_nature: Counter[str] = Counter()
        by_sub: Counter[str] = Counter()
        valor_by_nature: dict[str, Decimal] = defaultdict(lambda: Decimal("0"))
        total_valor = Decimal("0")

        for row in rows:
            nature = str(row.get("expenseNature") or "UNCLASSIFIED")
            sub = str(row.get("expenseSubNature") or "OUTROS")
            val = _money(row.get("valor"))
            by_nature[nature] += 1
            by_sub[sub] += 1
            valor_by_nature[nature] += val
            total_valor += val

        pct_by_nature = {
            k: round(v / total * 100, 2) for k, v in by_nature.items()
        }
        pct_valor = {
            k: round(float(valor_by_nature[k] / total_valor * 100), 2) if total_valor else 0.0
            for k in by_nature
        }

        fin_impact_valor = valor_by_nature.get("DESPESA_FINANCEIRA", Decimal("0"))
        pct_fin_impact = round(float(fin_impact_valor / total_valor * 100), 2) if total_valor else 0.0

        return {
            "totalRecords": total,
            "classifiedRecords": len(classified),
            "unclassifiedRecords": unclassified,
            "classificationPct": round(len(classified) / total * 100, 2) if total else 100.0,
            "avgSemanticConfidence": avg_conf,
            "byNature": dict(by_nature),
            "bySubNature": dict(by_sub.most_common(50)),
            "valorByNature": {k: float(v) for k, v in valor_by_nature.items()},
            "pctByNature": pct_by_nature,
            "pctValorByNature": pct_valor,
            "pctFinancialImpact": pct_fin_impact,
            "pctOperationalOnly": pct_by_nature.get("DESPESA_OPERACIONAL", 0.0),
            "pctCashMovement": pct_by_nature.get("MOVIMENTACAO_CAIXA", 0.0),
            "pctAdvance": pct_by_nature.get("ADIANTAMENTO", 0.0),
            "pctAdjustment": pct_by_nature.get("AJUSTE_OPERACIONAL", 0.0),
            "topSubNatures": by_sub.most_common(20),
            "realExpenseValor": float(fin_impact_valor + valor_by_nature.get("DESPESA_OPERACIONAL", Decimal("0"))),
            "nonExpenseValor": float(
                valor_by_nature.get("MOVIMENTACAO_CAIXA", Decimal("0"))
                + valor_by_nature.get("ADIANTAMENTO", Decimal("0"))
                + valor_by_nature.get("AJUSTE_OPERACIONAL", Decimal("0"))
            ),
        }

    def build_resumo_cards(self, summary: dict[str, Any]) -> dict[str, dict[str, Any]]:
        valor = summary.get("valorByNature") or {}
        counts = summary.get("byNature") or {}
        cards = {}
        for nature in EXPENSE_NATURES:
            cards[nature] = {
                "label": NATURE_LABELS[nature],
                "count": counts.get(nature, 0),
                "valor": str(Decimal(str(valor.get(nature, 0))).quantize(Decimal("0.01"))),
                "pct": summary.get("pctByNature", {}).get(nature, 0.0),
            }
        return cards

    async def build_semantic_payload(
        self,
        overview: NetworkFinancialOverviewService,
        filters: FinancialOverviewFilters,
        lineage_service: Any,
    ) -> dict[str, Any]:
        from src.services.expense_lineage_service import ExpenseLineageService

        lineage = lineage_service or ExpenseLineageService()
        ctx = await lineage.build_context(overview, filters)
        rows, err = await overview._load_screen_expenses(filters)
        if err:
            return {"error": err.error, "rows": [], "summary": {}}
        enriched = [self.classify_row(lineage.enrich_row(r, ctx)) for r in rows]
        summary = self.summarize(enriched)
        return {
            "rows": enriched,
            "summary": summary,
            "cards": self.build_resumo_cards(summary),
            "taxonomy": {
                "natures": list(EXPENSE_NATURES),
                "labels": NATURE_LABELS,
                "principle": "DESPESA ≠ MOVIMENTAÇÃO DE CAIXA ≠ ADIANTAMENTO ≠ AJUSTE OPERACIONAL",
            },
        }
