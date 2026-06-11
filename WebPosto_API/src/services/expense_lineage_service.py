"""F03.1-B — Expense Lineage Intelligence (read-only enrichment)."""
from __future__ import annotations

import re
from collections import Counter, defaultdict
from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal
from typing import Any

from src.services.network_financial_overview_service import FinancialOverviewFilters, NetworkFinancialOverviewService

SOURCE_TAXONOMY = {
    "DESPESAS_REDE": {"grupo": "Financeiro", "endpoint": "DESPESAS_FINANCEIRO_REDE"},
    "TITULO_PAGAR": {"grupo": "Financeiro", "endpoint": "TITULO_PAGAR"},
    "TITULO_RECEBER": {"grupo": "Financeiro", "endpoint": "TITULO_RECEBER"},
    "CAIXA_APRESENTADO": {"grupo": "Caixa", "endpoint": "CAIXA_APRESENTADO"},
    "CAIXA_APRESENTADO_REDE": {"grupo": "Caixa", "endpoint": "CAIXA_APRESENTADO_REDE"},
    "CAIXA": {"grupo": "PDV", "endpoint": "CAIXA"},
    "CAIXA_REDE": {"grupo": "PDV", "endpoint": "CAIXA_REDE"},
    "MOVIMENTO_CONTA": {"grupo": "Tesouraria", "endpoint": "MOVIMENTO_CONTA"},
    "TRANSFERENCIA_BANCARIA": {"grupo": "Tesouraria", "endpoint": "TRANSFERENCIA_BANCARIA"},
}

# Agente 0 — matriz oficial de campos por origem de negócio
SOURCE_FIELD_MATRIX: dict[str, dict[str, str]] = {
    "Valor": {
        "Financeiro": "Sim — DESPESAS_REDE.valor",
        "Caixa": "Sim — CAIXA_APRESENTADO.despesaApresentado",
        "PDV": "Sim — CAIXA_APRESENTADO.despesaApurado",
        "Tesouraria": "Sim — MOVIMENTO_CONTA / TRANSFERENCIA_BANCARIA",
    },
    "Fornecedor": {
        "Financeiro": "Parcial — DESPESAS_REDE + TITULO_PAGAR",
        "Caixa": "Não — agregado por fechamento",
        "PDV": "Não — agregado por fechamento",
        "Tesouraria": "Parcial — MOVIMENTO_CONTA",
    },
    "Plano Conta": {
        "Financeiro": "Sim — planoContaGerencialDescricao",
        "Caixa": "Não — inferido via match financeiro",
        "PDV": "Não — inferido via match financeiro",
        "Tesouraria": "Parcial — quando disponível",
    },
    "Centro Custo": {
        "Financeiro": "Parcial — frequentemente null (401 CENTRO_CUSTO_REDE)",
        "Caixa": "Não",
        "PDV": "Não",
        "Tesouraria": "Parcial",
    },
    "Operador": {
        "Financeiro": "Parcial — quando presente no lançamento",
        "Caixa": "Sim — funcionarioCodigo",
        "PDV": "Sim — funcionarioCodigo",
        "Tesouraria": "Não",
    },
    "PDV": {
        "Financeiro": "Parcial — quando vinculado",
        "Caixa": "Sim — pdvCodigo",
        "PDV": "Sim — pdvCodigo",
        "Tesouraria": "Não",
    },
    "Turno": {
        "Financeiro": "Parcial",
        "Caixa": "Sim — turnoCodigo / turno",
        "PDV": "Sim — turnoCodigo / turno",
        "Tesouraria": "Não",
    },
}

MANDATORY_CASE_PATTERNS: list[tuple[str, str]] = [
    ("BOBINA", "BOBINA TERMICA"),
    ("VALE\\s*FUNC", "VALE FUNCIONARIO"),
    ("FUNDO\\s*DE\\s*CAIXA|FUNDO\\s*CAIXA", "FUNDO DE CAIXA"),
    ("TROCO\\s*INIC", "TROCO"),
    ("LIMPEZA|MATERIAL\\s*LIMPEZA", "LIMPEZA"),
    ("BOBINA|COPO|DESCART|MANUTEN|FARDAMENT", "MATERIAL OPERACIONAL"),
]

EVENT_PATTERNS: list[tuple[str, str]] = [
    (r"TROCO\s*INIC", "Troco Inicial"),
    (r"FUNDO\s*DE\s*CAIXA|FUNDO\s*CAIXA", "Fundo de Caixa"),
    (r"VALE\s*FUNC", "Vale Funcionário"),
    (r"EMPREST", "Empréstimo"),
    (r"QUEBRA\s*DE\s*CAIXA|QUEBRA\s*CAIXA", "Quebra de Caixa"),
    (r"SANGRIA", "Sangria"),
    (r"SUPRIMENT", "Suprimento"),
    (r"BOBINA", "Material Operacional"),
    (r"LIMPEZA|MATERIAL\s*LIMPEZA", "Limpeza"),
    (r"EXPEDIENT", "Expediente"),
    (r"COPO|DESCART", "Material Operacional"),
    (r"LANCHE|CAF[EÉ]", "Expediente"),
    (r"MANUTEN", "Material Operacional"),
    (r"FARDAMENT", "Material Operacional"),
]

CONFIDENCE_BY_MATCH = {
    "MATCH_EXATO": 100,
    "MATCH_DOCUMENTO": 80,
    "MATCH_PARCIAL": 60,
    "MATCH_FINANCEIRO": 80,
    "MATCH_HEURISTICO": 40,
    "SEM_MATCH": 0,
}


def _norm_text(v: Any) -> str:
    return re.sub(r"\s+", " ", str(v or "").strip().upper())


def _money(v: Any) -> Decimal:
    try:
        return Decimal(str(v or 0)).quantize(Decimal("0.01"))
    except Exception:
        return Decimal("0")


def _norm_date(v: Any) -> str:
    return str(v or "")[:10]


def _date_near(d1: str, d2: str, days: int = 2) -> bool:
    try:
        a = datetime.fromisoformat(d1[:10])
        b = datetime.fromisoformat(d2[:10])
        return abs((a - b).days) <= days
    except ValueError:
        return d1 == d2


def _rede_desc(row: dict[str, Any]) -> str:
    return str(
        row.get("descricaoDocumento")
        or row.get("descricao")
        or row.get("planoContaGerencialDescricao")
        or row.get("planoConta")
        or ""
    ).strip()


def _detect_event(text: str) -> str | None:
    blob = _norm_text(text)
    for pattern, label in EVENT_PATTERNS:
        if re.search(pattern, blob, re.IGNORECASE):
            return label
    return None


def _match_operational_to_finance(
    emp: Any,
    data: str,
    valor: float,
    caixa_codigo: Any,
    ctx: "LineageContext",
) -> tuple[str, dict[str, Any] | None]:
    """Classifica vínculo operacional → financeiro."""
    by_exact = ctx.rede_by_key.get((emp, data, valor), [])
    for candidate in by_exact:
        doc = str(candidate.get("codigo") or candidate.get("documento") or candidate.get("caixaCodigo") or "")
        if caixa_codigo and doc and str(caixa_codigo) == doc:
            return "MATCH_DOCUMENTO", candidate
        return "MATCH_EXATO", candidate

    by_val = ctx.rede_by_key.get((emp, valor), [])
    for candidate in by_val:
        rdt = _norm_date(candidate.get("data") or candidate.get("dataMovimento"))
        if _date_near(data, rdt, 2):
            return "MATCH_PARCIAL", candidate

    return "SEM_MATCH", None


@dataclass
class LineageContext:
    despesas_rede: list[dict[str, Any]] = field(default_factory=list)
    titulos: list[dict[str, Any]] = field(default_factory=list)
    movimentos: list[dict[str, Any]] = field(default_factory=list)
    transferencias: list[dict[str, Any]] = field(default_factory=list)
    closure_by_key: dict[tuple[Any, ...], dict[str, Any]] = field(default_factory=dict)
    titulo_by_val: dict[tuple[Any, ...], list[dict[str, Any]]] = field(default_factory=dict)
    rede_by_key: dict[tuple[Any, ...], list[dict[str, Any]]] = field(default_factory=dict)


class ExpenseLineageService:
    def __init__(self, overview: NetworkFinancialOverviewService | None = None) -> None:
        self._overview = overview

    async def build_context(self, client_service: NetworkFinancialOverviewService, filters: FinancialOverviewFilters) -> LineageContext:
        import asyncio

        ctx = LineageContext()
        despesas_resp = await client_service._fetch_despesas_rede(filters)
        if despesas_resp.success:
            ctx.despesas_rede = client_service._rows(despesas_resp.data)

        caixa_rede, caixa, apresentado, apresentado_rede = await asyncio.gather(
            client_service._fetch_paginated_endpoint("caixa_rede", filters),
            client_service._fetch_paginated_endpoint("caixa", filters),
            client_service._fetch_paginated_endpoint("caixa_apresentado", filters),
            client_service._fetch_paginated_endpoint("caixa_apresentado_rede", filters),
        )
        ap_map = {
            (r.get("empresaCodigo"), r.get("caixaCodigo")): r
            for r in (apresentado + apresentado_rede)
        }
        caixa_rows = caixa_rede or caixa
        if caixa_rede and caixa:
            seen = {(r.get("empresaCodigo"), r.get("caixaCodigo")) for r in caixa_rede}
            caixa_rows = caixa_rede + [
                r for r in caixa if (r.get("empresaCodigo"), r.get("caixaCodigo")) not in seen
            ]
        caixa_rows = client_service._dedupe_closure_source_rows(caixa_rows)
        for row in caixa_rows:
            ap = ap_map.get((row.get("empresaCodigo"), row.get("caixaCodigo")), {})
            merged = {**row, **{f"ap_{k}": v for k, v in ap.items()}}
            key = client_service._closure_key(merged)
            ctx.closure_by_key[key] = merged

        empresas, err = await client_service._resolve_empresas(filters)
        if not err and empresas:
            titulo_tasks = [
                client_service._fetch_titulo_pagar(filters, int(emp["empresaCodigo"]))
                for emp in empresas
                if emp.get("empresaCodigo") is not None
            ]
            if titulo_tasks:
                for resp in await asyncio.gather(*titulo_tasks):
                    if resp.success:
                        ctx.titulos.extend(client_service._rows(resp.data))

        mov_resp = await client_service.client.call_endpoint(
            "movimento_conta",
            params={"dataInicial": filters.data_inicial, "dataFinal": filters.data_final},
        )
        if mov_resp.success:
            ctx.movimentos = client_service._rows(mov_resp.data)

        tr_resp = await client_service.client.call_endpoint(
            "transferencia_bancaria",
            params={"dataInicial": filters.data_inicial, "dataFinal": filters.data_final},
        )
        if tr_resp.success:
            ctx.transferencias = client_service._rows(tr_resp.data)

        for row in ctx.despesas_rede:
            emp = row.get("empresaCodigo")
            dt = _norm_date(row.get("data") or row.get("dataMovimento") or row.get("dataLancamento"))
            val = float(_money(row.get("valor")))
            ctx.rede_by_key.setdefault((emp, dt, val), []).append(row)
            ctx.rede_by_key.setdefault((emp, val), []).append(row)

        for row in ctx.titulos:
            ctx.titulo_by_val.setdefault((row.get("empresaCodigo"), float(_money(row.get("valor")))), []).append(row)

        return ctx

    def enrich_row(self, row: dict[str, Any], ctx: LineageContext) -> dict[str, Any]:
        origem = str(row.get("origem") or "")
        descricao = str(row.get("descricao") or row.get("planoConta") or "")
        valor = float(_money(row.get("valor")))
        emp = row.get("empresaCodigo")
        data = _norm_date(row.get("data"))
        evento = _detect_event(descricao) or _detect_event(row.get("planoConta") or "")

        lineage_path: list[str] = ["DESPESA"]
        origem_tecnica = ""
        origem_negocio = ""
        origem_real = "PDV"
        classificacao = "Operacional"
        documento = ""
        fornecedor = ""
        match_type = "SEM_MATCH"
        rede_match: dict[str, Any] | None = None
        closure: dict[str, Any] = {}

        if origem == "financeiro":
            origem_real = "Financeiro"
            origem_negocio = "Financeiro"
            origem_tecnica = "DESPESAS_REDE"
            classificacao = "Financeira"
            match_type = "MATCH_FINANCEIRO"
            lineage_path.extend(["Origem Técnica:DESPESAS_REDE", "Origem Negócio:Financeiro"])
            raw = row.get("raw") if isinstance(row.get("raw"), dict) else {}
            documento = str(
                raw.get("documento") or raw.get("numeroDocumento") or raw.get("codigo") or raw.get("despesaCodigo") or ""
            )
            fornecedor = str(raw.get("fornecedor") or raw.get("nomeFornecedor") or raw.get("razaoFornecedor") or "")
            titulo_hits = ctx.titulo_by_val.get((emp, valor), [])
            if titulo_hits:
                t = titulo_hits[0]
                fornecedor = fornecedor or str(t.get("fornecedor") or t.get("nomeFornecedor") or "")
                documento = documento or str(t.get("tituloPagarCodigo") or t.get("codigo") or "")
                origem_tecnica = "DESPESAS_REDE+TITULO_PAGAR"
                lineage_path.append("TITULO_PAGAR")
                match_type = "MATCH_DOCUMENTO" if documento else "MATCH_FINANCEIRO"
                classificacao = "Fornecedor" if fornecedor else "Financeira"
        else:
            caixa = row.get("caixaCodigo")
            key = (emp, data, caixa, row.get("turnoCodigo"), row.get("pdvCodigo"))
            closure = ctx.closure_by_key.get(key) or {}
            apurado = closure.get("ap_despesaApurado") or closure.get("despesaApurado")
            apresentado = closure.get("ap_despesaApresentado") or closure.get("despesaApresentado")
            origem_tecnica = "CAIXA_REDE+CAIXA_APRESENTADO"
            origem_negocio = "PDV" if apurado not in (None, "", 0) else "Caixa"
            origem_real = origem_negocio
            classificacao = "PDV" if origem_negocio == "PDV" else "Caixa"
            documento = str(caixa or "")
            lineage_path.extend(["Origem Técnica:CAIXA_REDE", "Origem Negócio:" + origem_negocio])

            match_type, rede_match = _match_operational_to_finance(emp, data, valor, caixa, ctx)
            if rede_match:
                descricao = descricao or _rede_desc(rede_match)
                fornecedor = str(rede_match.get("fornecedor") or rede_match.get("nomeFornecedor") or "")
                lineage_path.extend([f"Match:{match_type}", _rede_desc(rede_match)[:40] or "Documento"])
                row = {**row, "matchFinanceiro": True}
            elif row.get("matchFinanceiro"):
                match_type, rede_match = _match_operational_to_finance(emp, data, valor, caixa, ctx)
                if rede_match:
                    lineage_path.append(f"Match:{match_type}")

        if evento:
            lineage_path.append(f"Evento:{evento}")

        lineage_path.extend(
            [
                f"Documento:{documento or '?'}",
                f"Fornecedor:{fornecedor or '?'}",
                f"Plano:{row.get('planoConta') or '?'}",
                f"Centro:{row.get('centroCusto') or '?'}",
                f"PDV:{row.get('pdvCodigo') or '?'}",
                f"Turno:{row.get('turnoCodigo') or row.get('turno') or '?'}",
                f"Operador:{row.get('funcionarioCodigo') or '?'}",
            ]
        )

        if origem != "financeiro" and not closure and not ctx.closure_by_key:
            rastreavel = False
            confidence = 0
        elif origem != "financeiro" and match_type == "SEM_MATCH":
            rastreavel = True
            confidence = CONFIDENCE_BY_MATCH["MATCH_HEURISTICO"]
        elif origem == "financeiro":
            rastreavel = True
            confidence = 100 if match_type == "MATCH_DOCUMENTO" else 90
        else:
            rastreavel = True
            confidence = CONFIDENCE_BY_MATCH.get(match_type, 60)

        categoria_operacional = evento or (
            "Financeiro" if origem == "financeiro" else ("Operacional" if rede_match else origem_negocio)
        )

        return {
            **row,
            "origemReal": origem_real,
            "origemNegocio": origem_negocio or origem_real,
            "origemTecnica": origem_tecnica,
            "categoriaOperacional": categoria_operacional,
            "classificacaoLineage": classificacao,
            "documento": documento or None,
            "fornecedor": fornecedor or None,
            "eventoOperacional": evento,
            "primarySource": origem_tecnica,
            "operationalFinancialMatch": match_type,
            "lineageConfidence": confidence,
            "lineagePath": lineage_path,
            "rastreabilidadeOk": rastreavel,
        }

    def analyze_operational_financial(self, enriched: list[dict[str, Any]]) -> dict[str, Any]:
        operational = [r for r in enriched if r.get("origem") != "financeiro"]
        counts = Counter(str(r.get("operationalFinancialMatch") or "SEM_MATCH") for r in operational)
        total = max(len(operational), 1)
        with_fin = sum(1 for r in operational if r.get("operationalFinancialMatch") != "SEM_MATCH")
        without = len(operational) - with_fin
        return {
            "totalOperational": len(operational),
            "counts": dict(counts),
            "pct": {k: round(v / total * 100, 2) for k, v in counts.items()},
            "pctWithFinancial": round(with_fin / total * 100, 2),
            "pctWithoutFinancial": round(without / total * 100, 2),
            "allOperationalGenerateFinancial": with_fin == len(operational) if operational else True,
        }

    def analyze_case_studies(self, enriched: list[dict], ctx: LineageContext) -> list[dict[str, Any]]:
        studies: list[dict[str, Any]] = []
        for pattern, label in MANDATORY_CASE_PATTERNS:
            hits = [
                r for r in enriched
                if re.search(pattern, _norm_text(r.get("descricao") or r.get("planoConta") or ""), re.I)
            ]
            if not hits and label != "MATERIAL OPERACIONAL":
                continue
            if label == "MATERIAL OPERACIONAL" and not hits:
                hits = [r for r in enriched if r.get("eventoOperacional") == "Material Operacional"]
            empresas = sorted({r.get("empresaCodigo") for r in hits})
            has_titulo = sum(1 for r in hits if r.get("origemTecnica", "").find("TITULO") >= 0)
            has_fin = sum(1 for r in hits if r.get("origem") == "financeiro" or r.get("matchFinanceiro"))
            studies.append(
                {
                    "label": label,
                    "frequencia": len(hits),
                    "empresas": empresas,
                    "fornecedores": sorted({str(r.get("fornecedor")) for r in hits if r.get("fornecedor")}),
                    "planos": sorted({str(r.get("planoConta")) for r in hits if r.get("planoConta")})[:5],
                    "centros": sorted({str(r.get("centroCusto")) for r in hits if r.get("centroCusto")})[:5],
                    "origens": Counter(str(r.get("origemReal")) for r in hits),
                    "comTitulo": has_titulo,
                    "comDespesaFinanceira": has_fin,
                    "comEventoOperacional": sum(1 for r in hits if r.get("eventoOperacional")),
                    "amostra": hits[:3],
                }
            )
        return studies

    def summarize(self, enriched: list[dict[str, Any]]) -> dict[str, Any]:
        total = len(enriched)
        traced = sum(1 for r in enriched if r.get("rastreabilidadeOk"))
        confidences = [int(r.get("lineageConfidence") or 0) for r in enriched]
        avg_conf = round(sum(confidences) / len(confidences), 1) if confidences else 0.0

        financeiro_rows = [r for r in enriched if r.get("origem") == "financeiro"]
        oper_rows = [r for r in enriched if r.get("origem") != "financeiro"]
        fin_traced = sum(1 for r in financeiro_rows if r.get("rastreabilidadeOk"))
        op_traced = sum(1 for r in oper_rows if r.get("rastreabilidadeOk"))

        total_valor = sum(_money(r.get("valor")) for r in enriched)
        financeiro_valor = sum(_money(r.get("valor")) for r in financeiro_rows)
        caixa_valor = sum(_money(r.get("valor")) for r in oper_rows if r.get("origemReal") == "Caixa")
        pdv_valor = sum(_money(r.get("valor")) for r in oper_rows if r.get("origemReal") == "PDV")
        tesouraria_valor = Decimal("0")

        by_origem_real = Counter(str(r.get("origemReal") or "?") for r in enriched)
        by_class = Counter(str(r.get("classificacaoLineage") or "?") for r in enriched)
        by_event = Counter(str(r.get("eventoOperacional") or "Outros") for r in enriched)

        desc_counter: Counter[str] = Counter()
        for r in enriched:
            desc_counter[str(r.get("descricao") or r.get("planoConta") or "—")] += 1

        operators: dict[Any, dict[str, Any]] = defaultdict(
            lambda: {"count": 0, "valor": Decimal("0"), "diff": Decimal("0")}
        )
        pdvs: dict[Any, dict[str, Any]] = defaultdict(lambda: {"count": 0, "valor": Decimal("0")})
        for r in enriched:
            op = r.get("funcionarioCodigo")
            if op:
                operators[op]["count"] += 1
                operators[op]["valor"] += _money(r.get("valor"))
                operators[op]["diff"] += _money(r.get("despesaDiferenca"))
            pdv = r.get("pdvCodigo")
            if pdv:
                pdvs[pdv]["count"] += 1
                pdvs[pdv]["valor"] += _money(r.get("valor"))

        op_fin = self.analyze_operational_financial(enriched)
        suppliers = Counter(str(r.get("fornecedor") or "") for r in enriched if r.get("fornecedor"))

        never_fin = [
            cat for cat, _ in by_event.items()
            if cat not in ("Outros",) and op_fin.get("pctWithoutFinancial", 0) > 0
        ]

        return {
            "totalRecords": total,
            "tracedRecords": traced,
            "coveragePct": round(traced / total * 100, 2) if total else 0.0,
            "coverageFinanceiraPct": round(fin_traced / len(financeiro_rows) * 100, 2) if financeiro_rows else 100.0,
            "coverageOperacionalPct": round(op_traced / len(oper_rows) * 100, 2) if oper_rows else 100.0,
            "avgLineageConfidence": avg_conf,
            "byOrigemReal": dict(by_origem_real),
            "byClassificacao": dict(by_class),
            "byEvento": dict(by_event),
            "pctFinanceiro": round(float(financeiro_valor / total_valor * 100), 2) if total_valor else 0.0,
            "pctCaixa": round(float(caixa_valor / total_valor * 100), 2) if total_valor else 0.0,
            "pctPdv": round(float(pdv_valor / total_valor * 100), 2) if total_valor else 0.0,
            "pctTesouraria": round(float(tesouraria_valor / total_valor * 100), 2) if total_valor else 0.0,
            "pctOperacional": round(float((caixa_valor + pdv_valor) / total_valor * 100), 2) if total_valor else 0.0,
            "operationalFinancial": op_fin,
            "topDescriptions": desc_counter.most_common(100),
            "topSuppliers": suppliers.most_common(20),
            "topOperators": sorted(
                [
                    {"funcionarioCodigo": k, **{kk: float(vv) if isinstance(vv, Decimal) else vv for kk, vv in v.items()}}
                    for k, v in operators.items()
                ],
                key=lambda x: x["valor"],
                reverse=True,
            )[:20],
            "topPdvs": sorted(
                [{"pdvCodigo": k, "count": v["count"], "valor": float(v["valor"])} for k, v in pdvs.items()],
                key=lambda x: x["valor"],
                reverse=True,
            ),
            "totalValor": float(total_valor),
            "categoriesNeverFinancial": never_fin[:10],
            "categoriesAlwaysFinancial": ["Financeiro"],
        }

    async def build_lineage_payload(
        self,
        overview: NetworkFinancialOverviewService,
        filters: FinancialOverviewFilters,
    ) -> dict[str, Any]:
        ctx = await self.build_context(overview, filters)
        rows, err = await overview._load_screen_expenses(filters)
        if err:
            return {"error": err.error, "rows": [], "summary": {}}
        enriched = [self.enrich_row(r, ctx) for r in rows]
        summary = self.summarize(enriched)
        case_studies = self.analyze_case_studies(enriched, ctx)
        return {
            "rows": enriched,
            "summary": summary,
            "caseStudies": case_studies,
            "sourceFieldMatrix": SOURCE_FIELD_MATRIX,
            "contextSizes": {
                "despesasRede": len(ctx.despesas_rede),
                "titulos": len(ctx.titulos),
                "closures": len(ctx.closure_by_key),
                "movimentos": len(ctx.movimentos),
                "transferencias": len(ctx.transferencias),
            },
        }
