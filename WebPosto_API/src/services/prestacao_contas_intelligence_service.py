"""F03.4-B — Prestação de Contas Intelligence (READ ONLY, camada aditiva)."""
from __future__ import annotations

import re
import statistics
import time
from collections import Counter, defaultdict
from decimal import Decimal
from typing import Any

from src.models.response_model import WebPostoResponse
from src.services.cash_operations_service import CashOperationsService, _dec, _round2
from src.services.network_financial_overview_service import FinancialOverviewFilters

# Campos típicos do documento "Prestação de Contas - Não Consolida"
PRESTACAO_FIELD_CATALOG: dict[str, str] = {
    "funcionarioNome": "Funcionário nominalmente identificado",
    "funcionarioCodigo": "Código do funcionário",
    "diferencaIndividual": "Diferença individual por operador",
    "participacaoIndividual": "Participação % individual no turno",
    "produtividadeFuncionario": "Produtividade por funcionário",
    "vendasFuncionario": "Vendas por funcionário",
    "vendasProduto": "Vendas por produto",
    "cartaoDetalhado": "Cartões detalhados (bandeira/operadora)",
    "valeFuncionario": "Vale Funcionário",
    "despesaCaixa": "Despesa lançada diretamente no caixa",
    "sangria": "Sangria / retirada física",
    "fundoCaixa": "Fundo de Caixa (abertura)",
    "prePago": "Pré-pago detalhado",
    "emprestimo": "Empréstimo funcionário",
    "suprimento": "Suprimento de caixa",
    "deposito": "Depósito bancário vinculado",
    "transferencia": "Transferência entre contas/caixa",
    "movimentoConta": "Movimentação bancária",
    "formaPagamento": "Formas de pagamento apresentadas",
    "combustivel": "Combustível por produto",
    "turno": "Turno operacional",
    "pdv": "PDV / ponto de venda",
    "filial": "Filial / empresa",
}

# Cobertura conhecida via API WebPosto (endpoints LOGOS)
API_FIELD_COVERAGE: dict[str, dict[str, Any]] = {
    "funcionarioCodigo": {"endpoint": "CAIXA/CAIXA_REDE", "granularity": "turno", "available": True},
    "funcionarioNome": {"endpoint": "—", "granularity": "—", "available": False},
    "diferencaIndividual": {"endpoint": "CAIXA", "granularity": "turno", "available": True},
    "participacaoIndividual": {"endpoint": "—", "granularity": "—", "available": False},
    "produtividadeFuncionario": {"endpoint": "—", "granularity": "—", "available": False},
    "vendasFuncionario": {"endpoint": "VENDA/VENDA_ITEM", "granularity": "parcial", "available": "partial"},
    "vendasProduto": {"endpoint": "VENDA_ITEM", "granularity": "item", "available": True},
    "cartaoDetalhado": {"endpoint": "CAIXA_APRESENTADO", "granularity": "forma agregada", "available": "partial"},
    "valeFuncionario": {"endpoint": "CAIXA_APRESENTADO + DESPESAS", "granularity": "turno agregado", "available": True},
    "despesaCaixa": {"endpoint": "CAIXA_APRESENTADO + DESPESAS_REDE", "granularity": "turno/plano", "available": True},
    "sangria": {"endpoint": "DESPESAS_REDE (semântico)", "granularity": "lançamento", "available": "partial"},
    "fundoCaixa": {"endpoint": "—", "granularity": "—", "available": False},
    "prePago": {"endpoint": "CAIXA_APRESENTADO", "granularity": "forma agregada", "available": "partial"},
    "emprestimo": {"endpoint": "CAIXA_APRESENTADO", "granularity": "turno agregado", "available": True},
    "suprimento": {"endpoint": "MOVIMENTO_CONTA", "granularity": "movimento", "available": "partial"},
    "deposito": {"endpoint": "MOVIMENTO_CONTA", "granularity": "movimento", "available": "partial"},
    "transferencia": {"endpoint": "TRANSFERENCIA_BANCARIA", "granularity": "movimento", "available": True},
    "movimentoConta": {"endpoint": "MOVIMENTO_CONTA", "granularity": "movimento", "available": True},
    "formaPagamento": {"endpoint": "CAIXA_APRESENTADO", "granularity": "forma", "available": True},
    "combustivel": {"endpoint": "VENDA_ITEM/ANALISE_COMB", "granularity": "produto", "available": True},
    "turno": {"endpoint": "CAIXA", "granularity": "turno", "available": True},
    "pdv": {"endpoint": "CAIXA", "granularity": "turno", "available": True},
    "filial": {"endpoint": "CAIXA/EMPRESAS", "granularity": "empresa", "available": True},
}

EXPENSE_ORIGIN_CLASSES = (
    "DESPESA_FINANCEIRA",
    "DESPESA_OPERACIONAL",
    "DESPESA_DE_CAIXA",
    "DESPESA_FUNCIONARIO",
    "PERDA_OPERACIONAL",
)

VALE_CLASSES = (
    "VALE_FUNCIONARIO",
    "VALE_PRODUTO",
    "VALE_CLIENTE",
    "VALE_OPERACIONAL",
)

SANGRIA_FLOW = ("ABERTURA", "SUPRIMENTO", "SANGRIA", "FECHAMENTO", "DEPOSITO")


def _money(value: Any) -> Decimal:
    try:
        return Decimal(str(value or 0)).quantize(Decimal("0.01"))
    except Exception:
        return Decimal("0")


def _norm(value: Any) -> str:
    return re.sub(r"\s+", " ", str(value or "").upper().strip())


class PrestacaoContasIntelligenceService:
    """Prestação de Contas Intelligence — não altera WebPosto nem módulos F02/F03."""

    def __init__(self, cash_ops: CashOperationsService | None = None) -> None:
        self._cash = cash_ops or CashOperationsService()

    @staticmethod
    def _center_aliases(centro_custo: str | None) -> tuple[str, ...]:
        normalized = _norm(centro_custo)
        if normalized in {"PISTA", "COMBUSTIVEIS", "COMBUSTÍVEIS"}:
            return ("PISTA", "COMBUST")
        if normalized in {"CONVENIENCIA", "CONVENIÊNCIA", "LOJA"}:
            return ("CONVENIENCIA", "CONVENIÊNCIA", "LOJA")
        return (normalized,) if normalized else ()

    @classmethod
    def _filter_center_rows(
        cls,
        rows: list[dict[str, Any]],
        centro_custo: str | None,
    ) -> tuple[list[dict[str, Any]], dict[str, Any]]:
        aliases = cls._center_aliases(centro_custo)
        if not aliases:
            return rows, {"requested": None, "status": "NAO_APLICAVEL", "sourceRows": len(rows), "matchedRows": len(rows), "withoutCenter": 0}

        def center_of(row: dict[str, Any]) -> str:
            return _norm(row.get("centroCusto") or row.get("descricaoCentroCusto") or row.get("subCentro") or row.get("ap_centroCusto"))

        without_center = sum(1 for row in rows if not center_of(row))
        matched = [row for row in rows if any(alias in center_of(row) for alias in aliases)]
        status = "COMPROVADA" if rows and without_center == 0 else "PENDENTE_EVIDENCIA_CENTRO"
        return matched, {
            "requested": centro_custo,
            "status": status,
            "sourceRows": len(rows),
            "matchedRows": len(matched),
            "withoutCenter": without_center,
        }

    async def _enriched_expenses(
        self,
        filters: FinancialOverviewFilters,
    ) -> tuple[list[dict[str, Any]], dict[str, Any]]:
        from src.services.employee_cash_ledger_service import EmployeeCashLedgerService
        from src.services.expense_lineage_service import ExpenseLineageService
        from src.services.expense_semantic_service import ExpenseSemanticService
        from src.services.management_classification_service import ManagementClassificationService

        lineage = ExpenseLineageService()
        semantic = ExpenseSemanticService()
        mgmt = ManagementClassificationService()
        ctx = await lineage.build_context(self._cash._overview, filters)
        rows, err = await self._cash._overview._load_screen_expenses(filters)
        if err:
            return [], {"error": err.error}
        enriched = [
            mgmt.classify_row(semantic.classify_row(lineage.enrich_row(r, ctx)))
            for r in (rows or [])
        ]
        caixa_rows = list(ctx.closure_by_key.values())
        ledger = EmployeeCashLedgerService()
        caixa_events = ledger.build_caixa_events(caixa_rows)
        expense_events = ledger.build_expense_events(enriched)
        balance_by_op = ledger.build_balance_by_operator(caixa_events, expense_events)
        forensics = ledger.summarize_forensics(caixa_events)
        balance = ledger.summarize_balance(balance_by_op)
        accountability = ledger.build_accountability(
            caixa_events, ctx.titulos, ctx.despesas_rede, ctx.movimentos
        )
        recovery = ledger.build_recovery(balance_by_op, accountability)
        return enriched, {
            "caixa_rows": caixa_rows,
            "caixa_events": caixa_events,
            "expense_events": expense_events,
            "balance_by_op": balance_by_op,
            "forensics": forensics,
            "balance": balance,
            "accountability": accountability,
            "recovery": recovery,
            "lineage_ctx": ctx,
        }

    @staticmethod
    def discovery_report() -> dict[str, Any]:
        only_prestacao = [
            k for k, cov in API_FIELD_COVERAGE.items() if cov.get("available") is False
        ]
        partial = [k for k, cov in API_FIELD_COVERAGE.items() if cov.get("available") == "partial"]
        superior = [
            k
            for k, cov in API_FIELD_COVERAGE.items()
            if cov.get("available") is True and k in {
                "vendasProduto",
                "movimentoConta",
                "transferencia",
            }
        ]
        return {
            "catalog": PRESTACAO_FIELD_CATALOG,
            "apiCoverage": API_FIELD_COVERAGE,
            "onlyInPrestacao": only_prestacao,
            "notInApi": only_prestacao,
            "superiorGranularityInPrestacao": [
                "participacaoIndividual",
                "produtividadeFuncionario",
                "vendasFuncionario",
                "cartaoDetalhado",
                "sangria",
                "fundoCaixa",
                "diferencaIndividual",
            ],
            "superiorGranularityInApi": superior,
            "partialInApi": partial,
            "answers": {
                "1_camposApenasPrestacao": only_prestacao,
                "2_camposNaoExistemApi": only_prestacao,
                "3_granularidadeSuperiorPrestacao": [
                    "participacaoIndividual",
                    "produtividadeFuncionario",
                    "diferencaIndividualNominal",
                    "sangriaDestino",
                    "fundoCaixa",
                ],
            },
        }

    @staticmethod
    def employee_accountability(ledger_ctx: dict[str, Any]) -> dict[str, Any]:
        balance = ledger_ctx.get("balance") or {}
        forensics = ledger_ctx.get("forensics") or {}
        balance_by_op = ledger_ctx.get("balance_by_op") or {}
        compensators = [
            op
            for op, b in balance_by_op.items()
            if float(b.get("compensadoAutomatico") or 0) > 0 and float(b.get("faltas") or 0) > 0
        ]
        return {
            "modelo": [
                "FALTA_CAIXA",
                "SOBRA_CAIXA",
                "VALE_FUNCIONARIO",
                "DESCONTO",
                "EMPRESTIMO",
                "SALDO_FUNCIONARIO",
            ],
            "forensics": forensics,
            "balanceSummary": balance,
            "topDevedores": balance.get("topDevedores") or [],
            "topCredores": balance.get("topCredores") or [],
            "compensamFaltasComSobras": compensators[:20],
            "answers": {
                "quemDeve": balance.get("topDevedores"),
                "quemTemCredito": balance.get("topCredores"),
                "quemCompensa": compensators,
            },
        }

    @staticmethod
    def cash_expense_origin(enriched: list[dict[str, Any]]) -> dict[str, Any]:
        by_origin: dict[str, list[dict]] = defaultdict(list)
        bobina: list[dict] = []
        for row in enriched:
            mgmt_group = str(row.get("expenseManagementGroup") or "")
            mgmt_class = str(row.get("expenseManagementClass") or "")
            nature = str(row.get("expenseNature") or "")
            semantic = str(row.get("expenseSubNature") or row.get("expenseSemanticClass") or "")
            desc = _norm(row.get("descricao") or row.get("planoConta"))
            val = float(_money(row.get("valor")))

            if "BOBINA" in desc or semantic == "BOBINA_TERMICA" or mgmt_class == "BOBINA":
                origin = "DESPESA_OPERACIONAL"
                bobina.append({**row, "originClass": origin})
            elif mgmt_group == "TESOURARIA" or mgmt_class == "SANGRIA":
                origin = "DESPESA_DE_CAIXA"
            elif mgmt_class in ("VALE", "EMPRESTIMO", "ADIANTAMENTO") or nature == "ADIANTAMENTO":
                origin = "DESPESA_FUNCIONARIO"
            elif mgmt_class == "PERDA_CAIXA_FUNCIONARIO":
                origin = "PERDA_OPERACIONAL"
            elif mgmt_group == "FINANCEIRO":
                origin = "DESPESA_FINANCEIRA"
            else:
                origin = "DESPESA_OPERACIONAL"
            by_origin[origin].append({"valor": val, "descricao": desc, "funcionarioCodigo": row.get("funcionarioCodigo")})

        totals = {k: _round2(sum(x["valor"] for x in v)) for k, v in by_origin.items()}
        bobina_case = bobina[0] if bobina else {}
        return {
            "byOrigin": {k: {"count": len(v), "valor": totals.get(k, 0.0)} for k, v in by_origin.items()},
            "totals": totals,
            "bobinaTermica": {
                "count": len(bobina),
                "valor": _round2(sum(float(_money(r.get("valor"))) for r in bobina)),
                "nasceuNoCaixa": any(r.get("origem") == "caixa" for r in bobina),
                "virouDespesaFinanceira": any(r.get("origem") == "financeiro" for r in bobina),
                "virouTitulo": any(r.get("lineageTitulo") for r in bobina),
                "amostra": bobina_case,
            },
            "answers": {
                "bobinaNasceuCaixa": "Parcial — espelho operacional quando match caixa",
                "bobinaVirouFinanceira": True,
                "bobinaVirouTitulo": "Parcial via TITULO_PAGAR",
            },
        }

    @staticmethod
    def vale_forensics(enriched: list[dict[str, Any]]) -> dict[str, Any]:
        vales: list[dict[str, Any]] = []
        for row in enriched:
            desc = _norm(row.get("descricao") or row.get("planoConta"))
            mgmt = str(row.get("expenseManagementClass") or "")
            nature = str(row.get("expenseNature") or "")
            if mgmt not in ("VALE", "EMPRESTIMO", "ADIANTAMENTO") and nature != "ADIANTAMENTO":
                if "VALE" not in desc and "EMPREST" not in desc:
                    continue
            if "CLIENTE" in desc:
                cls = "VALE_CLIENTE"
            elif "PRODUTO" in desc or "COMBUST" in desc:
                cls = "VALE_PRODUTO"
            elif mgmt == "EMPRESTIMO" or "EMPREST" in desc:
                cls = "VALE_FUNCIONARIO"
            elif mgmt in ("VALE", "ADIANTAMENTO") or "VALE" in desc:
                cls = "VALE_FUNCIONARIO"
            else:
                cls = "VALE_OPERACIONAL"
            subtype = "ADIANTAMENTO" if nature == "ADIANTAMENTO" or mgmt == "ADIANTAMENTO" else (
                "CONSUMO" if "PRODUTO" in desc else "DESCONTO_FUTURO"
            )
            vales.append(
                {
                    "funcionarioCodigo": row.get("funcionarioCodigo"),
                    "valor": float(_money(row.get("valor"))),
                    "data": row.get("data"),
                    "classe": cls,
                    "subtipo": subtype,
                    "descricao": row.get("descricao") or row.get("planoConta"),
                }
            )
        by_class: dict[str, float] = defaultdict(float)
        for v in vales:
            by_class[v["classe"]] += v["valor"]
        return {
            "total": len(vales),
            "valorTotal": _round2(sum(v["valor"] for v in vales)),
            "byClass": {k: _round2(v) for k, v in by_class.items()},
            "amostra": vales[:20],
            "answers": {
                "adiantamento": sum(1 for v in vales if v["subtipo"] == "ADIANTAMENTO"),
                "consumo": sum(1 for v in vales if v["subtipo"] == "CONSUMO"),
                "descontoFuturo": sum(1 for v in vales if v["subtipo"] == "DESCONTO_FUTURO"),
            },
        }

    @staticmethod
    def sangria_intelligence(
        enriched: list[dict[str, Any]],
        merged: list[dict[str, Any]],
        movimentos: list[dict[str, Any]],
    ) -> dict[str, Any]:
        sangrias = [
            r
            for r in enriched
            if "SANGRIA" in _norm(r.get("descricao") or r.get("planoConta"))
            or str(r.get("expenseManagementClass") or "") == "SANGRIA"
        ]
        aberturas = len(merged)
        fechamentos = sum(1 for r in merged if _dec(r.get("diferenca")) != 0)
        depositos = [
            m
            for m in movimentos
            if "DEPOS" in _norm(m.get("historico") or m.get("descricao") or "")
            or "SANGRIA" in _norm(m.get("historico") or "")
        ]
        valor_sangria = _round2(sum(float(_money(r.get("valor"))) for r in sangrias))
        valor_deposito = _round2(sum(float(_money(m.get("valor"))) for m in depositos))
        rastreabilidade = abs(valor_sangria - valor_deposito) < max(valor_sangria * 0.15, 50) if valor_sangria else None
        return {
            "fluxo": {
                "ABERTURA": {"turnos": aberturas},
                "SUPRIMENTO": {"estimado": "via MOVIMENTO_CONTA crédito caixa"},
                "SANGRIA": {"count": len(sangrias), "valor": valor_sangria},
                "FECHAMENTO": {"quebras": fechamentos},
                "DEPOSITO": {"count": len(depositos), "valor": valor_deposito},
            },
            "sangrias": sangrias[:15],
            "depositos": depositos[:15],
            "answers": {
                "destinoSangria": "MOVIMENTO_CONTA / tesouraria (parcial)",
                "depositoCorrespondente": rastreabilidade,
                "quebraRastreabilidade": rastreabilidade is False,
            },
        }

    @staticmethod
    def productivity_score(
        merged: list[dict[str, Any]],
        balance_by_op: dict[Any, dict],
        enriched: list[dict[str, Any]],
    ) -> dict[str, Any]:
        vol_by_op: dict[Any, float] = defaultdict(float)
        diff_by_op: dict[Any, float] = defaultdict(float)
        for row in merged:
            op = row.get("funcionarioCodigo")
            vol_by_op[op] += abs(_dec(row.get("apurado") or row.get("volumeApurado")))
            diff_by_op[op] += abs(_dec(row.get("diferenca")))

        vale_by_op: dict[Any, float] = defaultdict(float)
        for row in enriched:
            if str(row.get("expenseManagementClass") or "") in ("VALE", "EMPRESTIMO"):
                vale_by_op[row.get("funcionarioCodigo")] += float(_money(row.get("valor")))

        scores: list[dict[str, Any]] = []
        for op in set(vol_by_op) | set(balance_by_op):
            if op is None:
                continue
            vol = vol_by_op.get(op, 0)
            diff = diff_by_op.get(op, 0)
            bal = balance_by_op.get(op) or {}
            saldo = float(bal.get("saldo") or 0)
            vales = vale_by_op.get(op, 0)
            vol_score = min(100, vol / 1000) if vol else 50
            diff_penalty = min(40, diff / 10)
            vale_penalty = min(20, vales / 50)
            saldo_penalty = min(20, abs(saldo) / 50) if saldo < 0 else 0
            ops_score = _round2(max(0, min(100, vol_score - diff_penalty - vale_penalty - saldo_penalty)))
            scores.append(
                {
                    "funcionarioCodigo": op,
                    "operationalPerformanceScore": ops_score,
                    "volumeApurado": _round2(vol),
                    "diferencaAbsoluta": _round2(diff),
                    "vales": _round2(vales),
                    "saldoLedger": _round2(saldo),
                }
            )
        scores.sort(key=lambda x: x["operationalPerformanceScore"], reverse=True)
        return {
            "formula": "volume - quebras - vales - saldo devedor",
            "ranking": scores[:20],
            "scoreMedio": _round2(statistics.mean([s["operationalPerformanceScore"] for s in scores])) if scores else 0,
        }

    @staticmethod
    def document_lineage(
        enriched: list[dict[str, Any]],
        caixa_events: list[dict[str, Any]],
    ) -> dict[str, Any]:
        total = max(len(enriched), 1)
        with_lineage = sum(1 for r in enriched if r.get("lineageSteps") or r.get("lineageConfidence"))
        with_caixa = sum(1 for e in caixa_events)
        with_titulo = sum(1 for r in enriched if r.get("lineageTitulo") or "TITULO" in _norm(r.get("lineageDestino")))
        coverage = _round2(100 * with_lineage / total)
        breaks = _round2(100 * (total - with_lineage) / total)
        confidence_vals = [
            float(r.get("lineageConfidence") or r.get("confidenceScore") or 0)
            for r in enriched
            if r.get("lineageConfidence") or r.get("confidenceScore")
        ]
        confidence = _round2(statistics.mean(confidence_vals)) if confidence_vals else 72.0
        return {
            "fluxo": [
                "Prestação de Contas",
                "Caixa",
                "Caixa Apresentado",
                "Movimento Conta",
                "Despesa",
                "Título",
            ],
            "coberturaPct": coverage,
            "quebrasPct": breaks,
            "confiancaPct": confidence,
            "eventosCaixa": with_caixa,
            "comTitulo": with_titulo,
        }

    @staticmethod
    def prestacao_vs_api(discovery: dict[str, Any]) -> dict[str, Any]:
        only_doc = discovery.get("onlyInPrestacao") or []
        only_api = [
            "movimentoContaDetalhado",
            "tituloPagarAberto",
            "classificacaoLogosV3",
            "snapshotTTL",
        ]
        return {
            "pdfNotInApi": only_doc,
            "apiNotInPdf": only_api,
            "fonteMaisConfiavel": {
                "operacional": "PRESTACAO_DE_CONTAS",
                "financeiroAutomatizado": "API",
                "accountability": "PRESTACAO_DE_CONTAS",
                "dreTitulos": "API",
            },
            "answers": {
                "1_pdfNaoApi": only_doc,
                "2_apiNaoPdf": only_api,
                "3_fonteConfiavel": "Híbrida — Prestação operacional, API financeira",
            },
        }

    @staticmethod
    def executive_consolidation(
        discovery: dict[str, Any],
        accountability: dict[str, Any],
        expense_origin: dict[str, Any],
        vale: dict[str, Any],
        sangria: dict[str, Any],
        lineage: dict[str, Any],
        recovery: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        forensics = accountability.get("forensics") or {}
        balance = accountability.get("balanceSummary") or {}
        top_dev = balance.get("topDevedores") or []
        top_cred = balance.get("topCredores") or []
        if not top_dev and balance.get("principalDevedor"):
            top_dev = [balance["principalDevedor"]]
        if not top_cred and balance.get("principalCredor"):
            top_cred = [balance["principalCredor"]]
        rec = recovery or {}
        prestacao_richer = len(discovery.get("onlyInPrestacao") or []) >= 4
        rastreavel_pct = _round2(
            100
            * (
                float(forensics.get("pctFaltasRastreadas") or 100)
                + float(forensics.get("pctSobrasRastreadas") or 100)
            )
            / 200
        )
        primary_source = "PRESTACAO_DE_CONTAS" if prestacao_richer else "API"
        return {
            "1_prestacaoMaisInformacao": prestacao_richer,
            "2_pctDiferencaRastreavel": rastreavel_pct,
            "3_maioresDevedores": top_dev[:5],
            "4_maioresCredores": top_cred[:5],
            "5_totalVales": vale.get("valorTotal"),
            "6_totalFaltas": forensics.get("totalFaltas"),
            "7_totalSobras": forensics.get("totalSobras"),
            "8_despesasCaixa": expense_origin.get("totals", {}).get("DESPESA_DE_CAIXA"),
            "9_recuperavel": rec.get("potencialRecuperacao") or rec.get("continuaAberto"),
            "10_f04ConsumirPrestacao": prestacao_richer,
            "decisaoFontePrimaria": primary_source,
            "decisaoModulos": {
                "caixa": primary_source,
                "operadores": primary_source,
                "vales": primary_source,
                "accountability": primary_source,
                "perdas": primary_source,
                "recuperacao": primary_source,
            },
            "lineageCobertura": lineage.get("coberturaPct"),
            "sangriaRastreavel": sangria.get("answers", {}).get("depositoCorrespondente"),
        }

    async def build(
        self,
        data_inicial: str,
        data_final: str,
        empresa_codigo: str | int | None = None,
        centro_custo: str | None = None,
    ) -> WebPostoResponse:
        t0 = time.perf_counter()
        from src.services.analytics_multiselect import build_finance_center_filters

        filters = build_finance_center_filters(data_inicial, data_final, empresa_codigo, centro_custo=centro_custo)
        enriched, ledger_ctx = await self._enriched_expenses(filters)
        if ledger_ctx.get("error"):
            return WebPostoResponse.fail(str(ledger_ctx["error"]))

        enriched, expense_center_coverage = self._filter_center_rows(enriched, centro_custo)

        cash_resp = await self._cash.build(data_inicial, data_final, empresa_codigo)
        merged: list[dict[str, Any]] = []
        if cash_resp.success and cash_resp.data:
            merged, _, _ = await self._cash._fetch_merged(filters)
        merged, cash_center_coverage = self._filter_center_rows(merged, centro_custo)

        mov_resp = await self._cash._client.call_endpoint(
            "movimento_conta",
            params={"dataInicial": data_inicial, "dataFinal": data_final},
        )
        movimentos = self._cash._rows(mov_resp.data if mov_resp.success else [])
        movimentos, bank_center_coverage = self._filter_center_rows(movimentos, centro_custo)

        discovery = self.discovery_report()
        # A prestação por centro de custo não pode reutilizar o ledger geral da
        # empresa: títulos e movimentos ainda não trazem centro comprovado.
        # Para Pista/Conveniência, mostramos apenas a forense reconstruída com
        # caixas e despesas do próprio centro e bloqueamos a responsabilização.
        scoped_ledger_ctx = ledger_ctx
        accountability_blocked = False
        if centro_custo:
            from src.services.employee_cash_ledger_service import EmployeeCashLedgerService

            ledger = EmployeeCashLedgerService()
            scoped_caixa_events = ledger.build_caixa_events(merged)
            scoped_expense_events = ledger.build_expense_events(enriched)
            scoped_balance_by_op = ledger.build_balance_by_operator(
                scoped_caixa_events, scoped_expense_events
            )
            scoped_ledger_ctx = {
                "caixa_events": scoped_caixa_events,
                "expense_events": scoped_expense_events,
                "balance_by_op": scoped_balance_by_op,
                "forensics": ledger.summarize_forensics(scoped_caixa_events),
                "balance": ledger.summarize_balance(scoped_balance_by_op),
                "recovery": None,
            }
            accountability_blocked = True

        accountability = self.employee_accountability(scoped_ledger_ctx)
        if accountability_blocked:
            accountability.update({
                "status": "BLOQUEADO_EVIDENCIA_CENTRO",
                "motivo": (
                    "Títulos, descontos e documentos de funcionário ainda não possuem "
                    "centro de custo comprovado; não foram rateados entre Pista e Conveniência."
                ),
            })
        expense_origin = self.cash_expense_origin(enriched)
        vale = self.vale_forensics(enriched)
        sangria = self.sangria_intelligence(enriched, merged, movimentos)
        productivity = self.productivity_score(
            merged, scoped_ledger_ctx.get("balance_by_op") or {}, enriched
        )
        lineage = self.document_lineage(enriched, scoped_ledger_ctx.get("caixa_events") or [])
        vs_api = self.prestacao_vs_api(discovery)
        executive = self.executive_consolidation(
            discovery,
            accountability,
            expense_origin,
            vale,
            sangria,
            lineage,
            scoped_ledger_ctx.get("recovery"),
        )

        total_ms = round((time.perf_counter() - t0) * 1000, 1)
        payload = {
            "periodo": {"dataInicial": data_inicial, "dataFinal": data_final},
            "scope": {
                "empresaCodigo": empresa_codigo,
                "centroCusto": centro_custo,
                "centerCoverage": {
                    "despesas": expense_center_coverage,
                    "caixas": cash_center_coverage,
                    "banco": bank_center_coverage,
                },
                "publicationStatus": (
                    "BLOQUEADO_EVIDENCIA_CENTRO"
                    if centro_custo and any(
                        coverage["status"] != "COMPROVADA"
                        for coverage in (expense_center_coverage, cash_center_coverage)
                    )
                    else "PRONTO_PARA_CONFERENCIA"
                ),
            },
            "discovery": discovery,
            "employeeAccountability": accountability,
            "cashExpenseOrigin": expense_origin,
            "valeForensics": vale,
            "sangriaIntelligence": sangria,
            "productivityIntelligence": productivity,
            "documentLineage": lineage,
            "prestacaoVsApi": vs_api,
            "executive": executive,
            "performanceMs": {"total": total_ms},
        }
        return WebPostoResponse.ok(payload)
