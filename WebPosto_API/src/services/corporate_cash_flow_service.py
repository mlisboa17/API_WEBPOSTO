"""Fluxo de Caixa Corporativo — apenas fatos WebPosto (F01.2)."""
from __future__ import annotations

import logging
from collections import defaultdict
from dataclasses import dataclass
from datetime import date, datetime, timedelta
from decimal import Decimal
from typing import Any

from src.models.response_model import WebPostoResponse
from src.services.corporate_finance_center_service import CorporateFinanceCenterService
from src.services.multiselect_utils import empresa_snapshot_suffix
from src.services.money_normalizer import normalize_webposto_account_value
from src.services.network_financial_overview_service import FinancialOverviewFilters

LOGGER = logging.getLogger(__name__)

ALLOWED_SOURCES = frozenset(
    {"TITULO_PAGAR", "TITULO_RECEBER", "MOVIMENTO_CONTA", "CAIXA_APRESENTADO"}
)
FORBIDDEN_SOURCES = frozenset({"DESPESAS_REDE", "FINANCEIRO_EXCLUSAO"})

AGING_KEYS = ("vencido", "hoje", "7d", "15d", "30d", "acima30")


@dataclass(frozen=True)
class CashFlowMeta:
    data_inicial: str
    data_final: str
    empresa_codigo: str | int | None

    def snapshot_key(self, granularity: str) -> str:
        suffix = empresa_snapshot_suffix(self.empresa_codigo)
        return f"cashflow:{granularity}:{self.data_inicial}:{self.data_final}:{suffix}"


def _parse_date(value: Any) -> date | None:
    text = str(value or "").strip()[:10]
    if not text:
        return None
    try:
        return date.fromisoformat(text)
    except ValueError:
        return None


def _dec(value: Any) -> Decimal:
    try:
        return Decimal(str(value or 0))
    except Exception:
        return Decimal("0")


def _q2(value: Decimal) -> str:
    return str(value.quantize(Decimal("0.01")))


def _aging_band(due: date, ref: date) -> str:
    delta = (due - ref).days
    if delta < 0:
        return "vencido"
    if delta == 0:
        return "hoje"
    if delta <= 7:
        return "7d"
    if delta <= 15:
        return "15d"
    if delta <= 30:
        return "30d"
    return "acima30"


def _empty_aging() -> dict[str, dict[str, Any]]:
    return {k: {"count": 0, "valor": "0.00"} for k in AGING_KEYS}


def _bucket_add(buckets: dict, key: str, valor: Decimal) -> None:
    b = buckets[key]
    b["count"] += 1
    b["valor"] = _q2(_dec(b["valor"]) + valor)


def _iter_days(start: date, end: date):
    current = start
    while current <= end:
        yield current
        current += timedelta(days=1)


def _week_key(d: date) -> str:
    iso = d.isocalendar()
    return f"{iso.year}-W{iso.week:02d}"


def _month_key(d: date) -> str:
    return d.strftime("%Y-%m")


class CorporateCashFlowService:
    """Projeção rastreável: títulos + movimento bancário + caixa apresentado."""

    def __init__(self, finance_center: CorporateFinanceCenterService) -> None:
        self._fc = finance_center

    @staticmethod
    def _is_open_payable(row: dict[str, Any]) -> bool:
        return not CorporateFinanceCenterService._is_pago_payable(row)

    @staticmethod
    def _is_open_receivable(row: dict[str, Any]) -> bool:
        return not CorporateFinanceCenterService._is_recebido(row)

    @staticmethod
    def _build_top_opportunities(
        payables_future: list[dict[str, Any]],
        receivables_future: list[dict[str, Any]],
        critical_days: list[dict[str, Any]],
        bank_classified: dict[str, Any],
    ) -> list[dict[str, Any]]:
        opps: list[dict[str, Any]] = []
        for item in sorted(
            (x for x in receivables_future if x.get("aging") == "vencido"),
            key=lambda x: _dec(x.get("valor")),
            reverse=True,
        )[:8]:
            opps.append(
                {
                    "tipo": "COBRANCA_VENCIDA",
                    "descricao": item.get("descricao") or "",
                    "valor": item.get("valor"),
                    "vencimento": item.get("vencimento"),
                    "acao": "Priorizar recebimento de título vencido",
                }
            )
        for item in sorted(
            (x for x in payables_future if x.get("aging") == "vencido"),
            key=lambda x: _dec(x.get("valor")),
            reverse=True,
        )[:8]:
            opps.append(
                {
                    "tipo": "RENEGOCIACAO_CP",
                    "descricao": item.get("descricao") or "",
                    "valor": item.get("valor"),
                    "vencimento": item.get("vencimento"),
                    "acao": "Renegociar ou programar pagamento vencido",
                }
            )
        for day in critical_days[:3]:
            saldo = _dec(day.get("saldoAcumulado"))
            if saldo >= 0:
                continue
            opps.append(
                {
                    "tipo": "DIA_CRITICO",
                    "descricao": f"Saldo acumulado negativo em {day.get('periodo')}",
                    "valor": day.get("saldoAcumulado"),
                    "vencimento": day.get("periodo"),
                    "acao": "Antecipar recebíveis ou postergar pagamentos neste dia",
                }
            )
        tarifa_items = (bank_classified.get("tarifas") or {}).get("items") or []
        for item in sorted(tarifa_items, key=lambda x: _dec(x.get("valor")), reverse=True)[:4]:
            opps.append(
                {
                    "tipo": "TARIFA_BANCARIA",
                    "descricao": item.get("descricao") or item.get("historico") or "Tarifa bancária",
                    "valor": _q2(_dec(item.get("valor"))),
                    "vencimento": item.get("dataMovimento"),
                    "acao": "Revisar tarifa evitável ou conta bancária",
                }
            )
        return opps[:20]

    @staticmethod
    def _build_semantic_breakdown(
        payables_future: list[dict[str, Any]],
        receivables_future: list[dict[str, Any]],
        pay_rows: list[dict[str, Any]],
        rec_rows: list[dict[str, Any]],
    ) -> dict[str, Any]:
        despesas_map: dict[str, Decimal] = defaultdict(Decimal)
        receitas_map: dict[str, Decimal] = defaultdict(Decimal)

        for row in pay_rows:
            nature = str(row.get("nomeFornecedor") or row.get("fornecedor") or row.get("descricao") or "CP")
            despesas_map[nature] += _dec(normalize_webposto_account_value(row.get("valor")))

        for row in rec_rows:
            nature = str(row.get("nomeCliente") or row.get("cliente") or row.get("descricao") or "CR")
            receitas_map[nature] += _dec(normalize_webposto_account_value(row.get("valor")))

        despesas = [
            {"natureza": k, "valor": _q2(v)}
            for k, v in sorted(despesas_map.items(), key=lambda item: item[1], reverse=True)[:20]
        ]
        receitas = [
            {"natureza": k, "valor": _q2(v)}
            for k, v in sorted(receitas_map.items(), key=lambda item: item[1], reverse=True)[:20]
        ]
        return {
            "despesas": despesas,
            "receitas": receitas,
            "despesasPrevistas": [
                {"tipo": item.get("tipo"), "descricao": item.get("descricao"), "valor": item.get("valor")}
                for item in payables_future[:30]
            ],
            "receitasPrevistas": [
                {"tipo": item.get("tipo"), "descricao": item.get("descricao"), "valor": item.get("valor")}
                for item in receivables_future[:30]
            ],
        }

    async def build(
        self,
        filters: FinancialOverviewFilters,
        empresa_codigo_raw: str | int | None,
    ) -> WebPostoResponse:
        ref = _parse_date(filters.data_final) or date.today()
        start = _parse_date(filters.data_inicial) or ref
        end = _parse_date(filters.data_final) or ref

        pay_rows, ms_pay = await self._fc._fetch_titulo_pagar_all(filters)
        rec_rows, ms_rec = await self._fc._fetch_titulo_receber_all(filters)
        bank_rows, ms_bank = await self._fc._fetch_movimento_conta_all(filters)
        _, apresentado_rows, ms_cx = await self._fc._fetch_caixa_all(filters)

        daily: dict[str, dict[str, Decimal]] = defaultdict(
            lambda: {"entradasPrevistas": Decimal("0"), "saidasPrevistas": Decimal("0")}
        )

        payables_future: list[dict[str, Any]] = []
        receivables_future: list[dict[str, Any]] = []
        overdue_events: list[dict[str, Any]] = []
        pay_aging = _empty_aging()
        rec_aging = _empty_aging()

        for row in pay_rows:
            if not self._is_open_payable(row):
                continue
            valor = normalize_webposto_account_value(row.get("valor"))
            if valor is None:
                continue
            v = _dec(valor)
            due = _parse_date(row.get("vencimento"))
            if not due:
                continue
            band = _aging_band(due, ref)
            _bucket_add(pay_aging, band, v)
            item = {
                "tipo": "TITULO_PAGAR",
                "empresaCodigo": row.get("empresaCodigo"),
                "codigo": row.get("tituloPagarCodigo") or row.get("codigo"),
                "descricao": row.get("nomeFornecedor") or row.get("fornecedor") or "",
                "vencimento": due.isoformat(),
                "valor": _q2(v),
                "aging": band,
            }
            payables_future.append(item)
            if band == "vencido":
                overdue_events.append({**item, "direcao": "saida"})
            if start <= due <= end:
                key = due.isoformat()
                daily[key]["saidasPrevistas"] += v

        for row in rec_rows:
            if not self._is_open_receivable(row):
                continue
            valor = normalize_webposto_account_value(row.get("valor"))
            if valor is None:
                continue
            v = _dec(valor)
            due = _parse_date(row.get("dataVencimento") or row.get("vencimento"))
            if not due:
                continue
            band = _aging_band(due, ref)
            _bucket_add(rec_aging, band, v)
            item = {
                "tipo": "TITULO_RECEBER",
                "empresaCodigo": row.get("empresaCodigo"),
                "codigo": row.get("tituloCodigo") or row.get("codigo"),
                "descricao": row.get("nomeCliente") or row.get("cliente") or "",
                "vencimento": due.isoformat(),
                "valor": _q2(v),
                "aging": band,
            }
            receivables_future.append(item)
            if band == "vencido":
                overdue_events.append({**item, "direcao": "entrada"})
            if start <= due <= end:
                key = due.isoformat()
                daily[key]["entradasPrevistas"] += v

        for row in bank_rows:
            mov_date = _parse_date(row.get("dataMovimento"))
            if not mov_date or not (start <= mov_date <= end):
                continue
            v = _dec(row.get("valor"))
            key = mov_date.isoformat()
            tipo = str(row.get("tipo") or "").casefold()
            if "crédito" in tipo or "credito" in tipo:
                daily[key]["entradasPrevistas"] += v
            elif "débito" in tipo or "debito" in tipo:
                daily[key]["saidasPrevistas"] += v

        for row in apresentado_rows:
            cx_date = _parse_date(row.get("data") or row.get("dataMovimento"))
            if not cx_date or not (start <= cx_date <= end):
                continue
            key = cx_date.isoformat()
            for field in ("despesaApurado", "valeFunApurado", "emprestimoApurado"):
                amt = _dec(row.get(field))
                if amt > 0:
                    daily[key]["saidasPrevistas"] += amt

        daily_series: list[dict[str, Any]] = []
        acumulado = Decimal("0")
        total_ent = Decimal("0")
        total_sai = Decimal("0")
        for day in _iter_days(start, end):
            key = day.isoformat()
            ent = daily[key]["entradasPrevistas"]
            sai = daily[key]["saidasPrevistas"]
            net = ent - sai
            acumulado += net
            total_ent += ent
            total_sai += sai
            daily_series.append(
                {
                    "periodo": key,
                    "entradasPrevistas": _q2(ent),
                    "saidasPrevistas": _q2(sai),
                    "saldoProjetado": _q2(net),
                    "saldoAcumulado": _q2(acumulado),
                }
            )

        weekly_map: dict[str, dict[str, Decimal]] = defaultdict(
            lambda: {"entradasPrevistas": Decimal("0"), "saidasPrevistas": Decimal("0")}
        )
        for row in daily_series:
            wk = _week_key(_parse_date(row["periodo"]) or start)
            weekly_map[wk]["entradasPrevistas"] += _dec(row["entradasPrevistas"])
            weekly_map[wk]["saidasPrevistas"] += _dec(row["saidasPrevistas"])

        weekly_series: list[dict[str, Any]] = []
        w_acum = Decimal("0")
        for wk in sorted(weekly_map.keys()):
            ent = weekly_map[wk]["entradasPrevistas"]
            sai = weekly_map[wk]["saidasPrevistas"]
            net = ent - sai
            w_acum += net
            weekly_series.append(
                {
                    "periodo": wk,
                    "entradasPrevistas": _q2(ent),
                    "saidasPrevistas": _q2(sai),
                    "saldoProjetado": _q2(net),
                    "saldoAcumulado": _q2(w_acum),
                }
            )

        monthly_map: dict[str, dict[str, Decimal]] = defaultdict(
            lambda: {"entradasPrevistas": Decimal("0"), "saidasPrevistas": Decimal("0")}
        )
        for row in daily_series:
            mk = _month_key(_parse_date(row["periodo"]) or start)
            monthly_map[mk]["entradasPrevistas"] += _dec(row["entradasPrevistas"])
            monthly_map[mk]["saidasPrevistas"] += _dec(row["saidasPrevistas"])

        monthly_series: list[dict[str, Any]] = []
        m_acum = Decimal("0")
        for mk in sorted(monthly_map.keys()):
            ent = monthly_map[mk]["entradasPrevistas"]
            sai = monthly_map[mk]["saidasPrevistas"]
            net = ent - sai
            m_acum += net
            monthly_series.append(
                {
                    "periodo": mk,
                    "entradasPrevistas": _q2(ent),
                    "saidasPrevistas": _q2(sai),
                    "saldoProjetado": _q2(net),
                    "saldoAcumulado": _q2(m_acum),
                }
            )

        bank_classified = self._fc._classify_bank_movements(bank_rows)
        treasury = {
            "creditos": {k: v for k, v in bank_classified["creditos"].items() if k != "items"},
            "debitos": {k: v for k, v in bank_classified["debitos"].items() if k != "items"},
            "tarifas": {k: v for k, v in bank_classified["tarifas"].items() if k != "items"},
            "transferencias": {k: v for k, v in bank_classified["transferencias"].items() if k != "items"},
        }

        critical_days = sorted(
            daily_series,
            key=lambda r: _dec(r["saldoAcumulado"]),
        )[:5]
        top_opportunities = self._build_top_opportunities(
            payables_future,
            receivables_future,
            critical_days,
            bank_classified,
        )

        meta = CashFlowMeta(filters.data_inicial, filters.data_final, empresa_codigo_raw)
        payload = {
            "sources": sorted(ALLOWED_SOURCES),
            "forbiddenSourcesUsed": [],
            "referenceDate": ref.isoformat(),
            "cards": {
                "entradasPrevistas": _q2(total_ent),
                "saidasPrevistas": _q2(total_sai),
                "saldoProjetado": _q2(total_ent - total_sai),
                "saldoAcumulado": _q2(acumulado),
            },
            "daily": daily_series,
            "weekly": weekly_series,
            "monthly": monthly_series,
            "payablesAging": pay_aging,
            "receivablesAging": rec_aging,
            "payablesFuture": payables_future,
            "receivablesFuture": receivables_future,
            "overdueEvents": overdue_events,
            "treasury": treasury,
            "insights": {
                "criticalDays": critical_days,
                "payablesVencidoValor": pay_aging["vencido"]["valor"],
                "receivablesVencidoValor": rec_aging["vencido"]["valor"],
                "tarifasValor": treasury["tarifas"].get("valor", "0"),
                "topOpportunities": top_opportunities,
            },
            "semanticBreakdown": self._build_semantic_breakdown(
                payables_future,
                receivables_future,
                pay_rows,
                rec_rows,
            ),
            "snapshotKeys": {
                "daily": meta.snapshot_key("daily"),
                "weekly": meta.snapshot_key("weekly"),
                "monthly": meta.snapshot_key("monthly"),
            },
            "performanceMs": {
                "payables": ms_pay,
                "receivables": ms_rec,
                "bank": ms_bank,
                "caixaApresentado": ms_cx,
            },
        }
        return WebPostoResponse.ok(payload)
