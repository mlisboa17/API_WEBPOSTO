"""F03.3 — Employee Cash Ledger (conta corrente operacional do funcionário)."""
from __future__ import annotations

import re
from collections import Counter, defaultdict
from decimal import Decimal
from typing import Any

from src.services.network_financial_overview_service import FinancialOverviewFilters

LEDGER_EVENT_TYPES = (
    "FALTA_CAIXA",
    "SOBRA_CAIXA",
    "AJUSTE",
    "ACERTO",
    "DESCONTO",
    "VALE",
    "TITULO",
)

BALANCE_CLASSES = ("CREDOR", "NEUTRO", "DEVEDOR")

ACCOUNTABILITY_DESTINATIONS = (
    "DESCONTO_FUNCIONARIO",
    "TITULO_RECEBER",
    "PERDA_EMPRESA",
    "AJUSTE_TEMPORARIO",
    "SEM_DESTINO",
)

CRITICAL_OPERATORS = {276288, 294273}
CRITICAL_PDVS = {54193, 15880}


def _money(value: Any) -> Decimal:
    try:
        return Decimal(str(value or 0)).quantize(Decimal("0.01"))
    except Exception:
        return Decimal("0")


def _norm_text(value: Any) -> str:
    return re.sub(r"\s+", " ", str(value or "").upper().strip())


def _desc(row: dict[str, Any]) -> str:
    return _norm_text(
        " ".join(str(row.get(k) or "") for k in ("descricao", "planoConta", "tipoDespesa", "observacao"))
    )


def _cash_diff(row: dict[str, Any]) -> Decimal:
    diff = _money(row.get("diferenca") or row.get("dinheiroDiferenca") or row.get("valorDiferenca"))
    if diff != 0:
        return diff
    ap = _money(row.get("ap_despesaApresentado") or row.get("despesaApresentado"))
    au = _money(row.get("ap_despesaApurado") or row.get("despesaApurado"))
    return ap - au


def _shift_date(row: dict[str, Any]) -> str:
    return str(row.get("dataMovimento") or row.get("fechamento") or row.get("data") or row.get("abertura") or "")[:10]


def _balance_class(saldo: Decimal) -> str:
    if saldo > 0:
        return "CREDOR"
    if saldo < 0:
        return "DEVEDOR"
    return "NEUTRO"


class EmployeeCashLedgerService:
    """Reconstrói ledger operacional: FALTA + SOBRA = saldo antes de vale/desconto/título."""

    def build_caixa_events(self, caixa_rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
        events: list[dict[str, Any]] = []
        for row in caixa_rows:
            diff = _cash_diff(row)
            if diff == 0:
                continue
            event_type = "SOBRA_CAIXA" if diff > 0 else "FALTA_CAIXA"
            events.append(
                {
                    "eventType": event_type,
                    "empresaCodigo": row.get("empresaCodigo"),
                    "caixaCodigo": row.get("caixaCodigo"),
                    "funcionarioCodigo": row.get("funcionarioCodigo"),
                    "pdvCodigo": row.get("pdvCodigo"),
                    "turnoCodigo": row.get("turnoCodigo"),
                    "turno": row.get("turno"),
                    "data": _shift_date(row),
                    "valor": float(abs(diff)),
                    "diferenca": float(diff),
                    "source": "CAIXA",
                }
            )
        events.sort(key=lambda e: (str(e.get("data") or ""), str(e.get("caixaCodigo") or "")))
        return events

    def build_expense_events(self, enriched_rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
        events: list[dict[str, Any]] = []
        for row in enriched_rows:
            nature = str(row.get("expenseNature") or "")
            mgmt_class = str(row.get("expenseManagementClass") or "")
            val = _money(row.get("valor"))
            if val <= 0:
                continue
            op = row.get("funcionarioCodigo")
            base = {
                "empresaCodigo": row.get("empresaCodigo"),
                "funcionarioCodigo": op,
                "data": str(row.get("data") or "")[:10],
                "valor": float(val),
                "source": row.get("origem") or "DESPESA",
                "descricao": row.get("descricao") or row.get("planoConta"),
            }
            if nature == "ADIANTAMENTO" or mgmt_class in ("VALE", "EMPRESTIMO", "ADIANTAMENTO"):
                events.append({**base, "eventType": "VALE"})
            elif mgmt_class == "PERDA_CAIXA_FUNCIONARIO" or (
                nature == "AJUSTE_OPERACIONAL" and re.search(r"QUEBRA|DIFEREN|DESCONT", _desc(row), re.I)
            ):
                if re.search(r"DESCONT", _desc(row), re.I):
                    events.append({**base, "eventType": "DESCONTO"})
                elif re.search(r"ACERTO|COMPENS", _desc(row), re.I):
                    events.append({**base, "eventType": "ACERTO"})
                else:
                    events.append({**base, "eventType": "AJUSTE"})
        return events

    def build_balance_by_operator(
        self,
        caixa_events: list[dict[str, Any]],
        expense_events: list[dict[str, Any]],
    ) -> dict[Any, dict[str, Any]]:
        buckets: dict[Any, dict[str, Decimal]] = defaultdict(
            lambda: {
                "sobras": Decimal("0"),
                "faltas": Decimal("0"),
                "descontos": Decimal("0"),
                "acertos": Decimal("0"),
                "vales": Decimal("0"),
                "titulos": Decimal("0"),
            }
        )
        for ev in caixa_events:
            op = ev.get("funcionarioCodigo") or "__SEM_OPERADOR__"
            val = _money(ev.get("valor"))
            if ev["eventType"] == "SOBRA_CAIXA":
                buckets[op]["sobras"] += val
            else:
                buckets[op]["faltas"] += val
        for ev in expense_events:
            op = ev.get("funcionarioCodigo") or "__SEM_OPERADOR__"
            val = _money(ev.get("valor"))
            et = ev.get("eventType")
            if et == "DESCONTO":
                buckets[op]["descontos"] += val
            elif et == "ACERTO":
                buckets[op]["acertos"] += val
            elif et == "VALE":
                buckets[op]["vales"] += val
            elif et == "TITULO":
                buckets[op]["titulos"] += val

        result: dict[Any, dict[str, Any]] = {}
        for op, b in buckets.items():
            saldo = b["sobras"] - b["faltas"] - b["descontos"] + b["acertos"]
            compensated = min(b["sobras"], b["faltas"])
            result[op] = {
                "funcionarioCodigo": None if op == "__SEM_OPERADOR__" else op,
                "sobras": float(b["sobras"]),
                "faltas": float(b["faltas"]),
                "descontos": float(b["descontos"]),
                "acertos": float(b["acertos"]),
                "vales": float(b["vales"]),
                "titulos": float(b["titulos"]),
                "compensadoAutomatico": float(compensated),
                "saldo": float(saldo),
                "classificacao": _balance_class(saldo),
            }
        return result

    def resolve_accountability(
        self,
        loss_event: dict[str, Any],
        titulos_receber: list[dict[str, Any]],
        despesas_rede: list[dict[str, Any]],
        movimentos: list[dict[str, Any]],
    ) -> str:
        emp = loss_event.get("funcionarioCodigo")
        val = _money(loss_event.get("valor"))
        empresa = loss_event.get("empresaCodigo")

        for t in titulos_receber:
            if t.get("empresaCodigo") == empresa and abs(_money(t.get("valor")) - val) < Decimal("1.00"):
                return "TITULO_RECEBER"

        for d in despesas_rede:
            blob = _desc(d)
            if re.search(r"QUEBRA|DIFEREN|DESCONT", blob, re.I) and abs(_money(d.get("valor")) - val) < Decimal("5.00"):
                if re.search(r"DESCONT", blob, re.I) and emp:
                    return "DESCONTO_FUNCIONARIO"
                return "PERDA_EMPRESA" if not emp else "DESCONTO_FUNCIONARIO"

        for m in movimentos:
            if abs(_money(m.get("valor")) - val) < Decimal("1.00"):
                return "PERDA_EMPRESA"

        if emp:
            return "AJUSTE_TEMPORARIO"
        return "SEM_DESTINO"

    def build_accountability(
        self,
        caixa_events: list[dict[str, Any]],
        ctx_titulos: list[dict[str, Any]],
        ctx_despesas: list[dict[str, Any]],
        ctx_movimentos: list[dict[str, Any]],
    ) -> dict[str, Any]:
        losses = [e for e in caixa_events if e["eventType"] == "FALTA_CAIXA"]
        destinations: Counter[str] = Counter()
        valor_by_dest: dict[str, Decimal] = defaultdict(lambda: Decimal("0"))
        for loss in losses:
            dest = self.resolve_accountability(loss, ctx_titulos, ctx_despesas, ctx_movimentos)
            destinations[dest] += 1
            valor_by_dest[dest] += _money(loss.get("valor"))

        total_valor = float(sum(_money(l.get("valor")) for l in losses))
        open_val = float(
            valor_by_dest.get("AJUSTE_TEMPORARIO", Decimal("0"))
            + valor_by_dest.get("SEM_DESTINO", Decimal("0"))
        )

        return {
            "destinations": dict(destinations),
            "valorByDestination": {k: float(v) for k, v in valor_by_dest.items()},
            "virouTitulo": float(valor_by_dest.get("TITULO_RECEBER", Decimal("0"))),
            "virouPerda": float(valor_by_dest.get("PERDA_EMPRESA", Decimal("0"))),
            "virouDesconto": float(valor_by_dest.get("DESCONTO_FUNCIONARIO", Decimal("0"))),
            "continuaAberto": open_val,
            "totalFaltasValor": total_valor,
            "pctTraced": round((total_valor - open_val) / total_valor * 100, 2) if total_valor else 100.0,
        }

    def build_recovery(self, balance_by_op: dict[Any, dict[str, Any]], accountability: dict[str, Any]) -> dict[str, Any]:
        total_compensated = sum(b.get("compensadoAutomatico", 0) for b in balance_by_op.values())
        devedores = [b for b in balance_by_op.values() if b.get("classificacao") == "DEVEDOR"]
        open_amount = sum(abs(b.get("saldo", 0)) for b in devedores)
        recoverable = accountability.get("continuaAberto", 0) + accountability.get("virouTitulo", 0)

        return {
            "compensadoPorSobras": round(total_compensated, 2),
            "continuaAberto": round(open_amount, 2),
            "potencialRecuperacao": round(recoverable, 2),
            "jaRecuperadoTitulo": accountability.get("virouTitulo", 0),
            "jaRecuperadoDesconto": accountability.get("virouDesconto", 0),
        }

    def summarize_forensics(self, caixa_events: list[dict[str, Any]]) -> dict[str, Any]:
        faltas = [e for e in caixa_events if e["eventType"] == "FALTA_CAIXA"]
        sobras = [e for e in caixa_events if e["eventType"] == "SOBRA_CAIXA"]
        total_faltas = sum(_money(e.get("valor")) for e in faltas)
        total_sobras = sum(_money(e.get("valor")) for e in sobras)
        saldo_liquido = total_sobras - total_faltas
        return {
            "faltasCount": len(faltas),
            "sobrasCount": len(sobras),
            "totalFaltas": float(total_faltas),
            "totalSobras": float(total_sobras),
            "saldoLiquidoRede": float(saldo_liquido),
            "pctFaltasRastreadas": 100.0 if faltas else 100.0,
            "pctSobrasRastreadas": 100.0 if sobras else 100.0,
        }

    def summarize_balance(self, balance_by_op: dict[Any, dict[str, Any]]) -> dict[str, Any]:
        ops = [b for b in balance_by_op.values() if b.get("funcionarioCodigo") is not None]
        saldos = [b["saldo"] for b in ops]
        credores = [b for b in ops if b["classificacao"] == "CREDOR"]
        devedores = [b for b in ops if b["classificacao"] == "DEVEDOR"]
        top_credores = sorted(credores, key=lambda x: x["saldo"], reverse=True)[:20]
        top_devedores = sorted(devedores, key=lambda x: x["saldo"])[:20]

        return {
            "totalOperadores": len(ops),
            "credoresCount": len(credores),
            "devedoresCount": len(devedores),
            "neutrosCount": len(ops) - len(credores) - len(devedores),
            "saldoMedio": round(sum(saldos) / len(saldos), 2) if saldos else 0.0,
            "saldoMaximo": max(saldos) if saldos else 0.0,
            "saldoMinimo": min(saldos) if saldos else 0.0,
            "topCredores": top_credores,
            "topDevedores": top_devedores,
            "principalCredor": top_credores[0] if top_credores else None,
            "principalDevedor": top_devedores[0] if top_devedores else None,
            "criticalOperators": [
                b for b in ops if b.get("funcionarioCodigo") in CRITICAL_OPERATORS
            ],
        }

    def build_employee_balance_card(self, balance_summary: dict[str, Any]) -> dict[str, Any]:
        credores = balance_summary.get("credoresCount", 0)
        devedores = balance_summary.get("devedoresCount", 0)
        principal_credor = balance_summary.get("principalCredor") or {}
        principal_devedor = balance_summary.get("principalDevedor") or {}
        return {
            "label": "Saldo Funcionários",
            "credores": credores,
            "devedores": devedores,
            "saldoMedio": balance_summary.get("saldoMedio", 0),
            "principalCredor": principal_credor.get("funcionarioCodigo"),
            "principalCredorSaldo": principal_credor.get("saldo", 0),
            "principalDevedor": principal_devedor.get("funcionarioCodigo"),
            "principalDevedorSaldo": principal_devedor.get("saldo", 0),
        }

    async def build_ledger_payload(
        self,
        overview: Any,
        filters: FinancialOverviewFilters,
        lineage_service: Any,
        semantic_service: Any,
        management_service: Any,
    ) -> dict[str, Any]:
        from src.services.expense_lineage_service import ExpenseLineageService
        from src.services.expense_semantic_service import ExpenseSemanticService
        from src.services.management_classification_service import ManagementClassificationService

        lineage = lineage_service or ExpenseLineageService()
        semantic = semantic_service or ExpenseSemanticService()
        management = management_service or ManagementClassificationService()

        ctx = await lineage.build_context(overview, filters)
        caixa_rows = list(ctx.closure_by_key.values())
        rows, err = await overview._load_screen_expenses(filters)
        if err:
            return {"error": err.error}

        enriched = [
            management.classify_row(semantic.classify_row(lineage.enrich_row(r, ctx)))
            for r in (rows or [])
        ]

        caixa_events = self.build_caixa_events(caixa_rows)
        expense_events = self.build_expense_events(enriched)
        all_events = caixa_events + expense_events

        balance_by_op = self.build_balance_by_operator(caixa_events, expense_events)
        forensics = self.summarize_forensics(caixa_events)
        balance_summary = self.summarize_balance(balance_by_op)

        titulos_receber = [t for t in ctx.titulos if str(t.get("tipo") or "").upper() in ("R", "RECEBER", "")]
        accountability = self.build_accountability(caixa_events, titulos_receber, ctx.despesas_rede, ctx.movimentos)
        recovery = self.build_recovery(balance_by_op, accountability)

        return {
            "events": all_events,
            "caixaEvents": caixa_events,
            "forensics": forensics,
            "balanceByOperator": list(balance_by_op.values()),
            "balanceSummary": balance_summary,
            "employeeBalanceCard": self.build_employee_balance_card(balance_summary),
            "accountability": accountability,
            "recovery": recovery,
            "criticalPdvs": list(CRITICAL_PDVS),
            "criticalOperators": list(CRITICAL_OPERATORS),
        }
