"""F03.2-A — Workforce Payment Forensics (read-only, in-memory)."""
from __future__ import annotations

import re
import statistics
from collections import Counter, defaultdict
from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal
from typing import Any

import httpx

WORKFORCE_KEYWORDS = (
    r"VALE",
    r"ADIANTAMENTO",
    r"QUINZENA",
    r"SALAR",
    r"SALÁRIO",
    r"FOLGUIST",
    r"\bEXTRA\b",
    r"HORA\s*EXTRA",
    r"EMPREST",
    r"EMPRÉST",
    r"REEMBOLSO",
    r"AJUDA",
    r"PREMI",
    r"PRÊMI",
    r"ACERTO",
    r"FUNCION",
    r"FUNCIONÁRIO",
    r"DIARIA",
    r"DIÁRIA",
    r"FOLHA",
)

WORKFORCE_BLOB_RE = re.compile("|".join(WORKFORCE_KEYWORDS), re.IGNORECASE)

PROVISIONAL_TYPES = (
    "VALE_FUNCIONARIO",
    "QUINZENA",
    "ADIANTAMENTO_SALARIAL",
    "SALARIO",
    "EXTRA_FUNCIONARIO",
    "FOLGUISTA",
    "HORA_EXTRA",
    "EMPRESTIMO_FUNCIONARIO",
    "REEMBOLSO_FUNCIONARIO",
    "PREMIACAO",
    "ACERTO_FUNCIONARIO",
    "OUTROS_FUNCIONARIO",
)

CLASS_RULES: list[tuple[str, list[str], int]] = [
    ("VALE_FUNCIONARIO", [r"VALE\s*FUNC", r"VALE\s*DE\s*FUNC", r"CONSOLIDA[ÇC][AÃ]O\s*DE\s*CAIXA"], 95),
    ("QUINZENA", [r"QUINZENA"], 92),
    ("SALARIO", [r"\bSALAR", r"\bSALÁRIO", r"\bFOLHA\b", r"REF\s*AO\s*SALAR", r"REF\s*A\s*SALAR"], 90),
    ("FOLGUISTA", [r"FOLGUIST", r"FOLGUISTA"], 88),
    ("HORA_EXTRA", [r"HORA\s*EXTRA", r"\bHR\s*EXTRA", r"REF_A_HR_EXTRA", r"REF_HORA_EXTRA"], 88),
    ("EMPRESTIMO_FUNCIONARIO", [r"EMPREST", r"EMPRÉST"], 90),
    ("REEMBOLSO_FUNCIONARIO", [r"REEMBOLSO"], 90),
    ("PREMIACAO", [r"PREMI", r"PRÊMI"], 85),
    ("ACERTO_FUNCIONARIO", [r"\bACERTO\b"], 85),
    ("ADIANTAMENTO_SALARIAL", [r"\bADIANTAMENTO\b"], 82),
    ("EXTRA_FUNCIONARIO", [r"\bEXTRA\b", r"DIARIA", r"DIÁRIA"], 80),
]

PAYROLL_BUCKETS = (
    ("dia_01_05", range(1, 6)),
    ("dia_06_10", range(6, 11)),
    ("dia_11_15", range(11, 16)),
    ("dia_16_20", range(16, 21)),
    ("dia_21_25", range(21, 26)),
    ("dia_26_31", range(26, 32)),
)

OPTIONAL_ENDPOINTS = {
    "FUNCIONARIO_REDE": "/INTEGRACAO/FUNCIONARIO_REDE",
    "VALE_FUNCIONARIO_REDE": "/INTEGRACAO/CONSULTAR_VALE_FUNCIONARIO_REDE",
    "VALE_FUNCIONARIO_REDE_ALT": "/INTEGRACAO/VALE_FUNCIONARIO_REDE",
    "DESPESA_FUNCIONARIO": "/INTEGRACAO/DESPESA_FUNCIONARIO",
    "DESPESA_FUNCIONARIO_REDE": "/INTEGRACAO/CONSULTAR_DESPESA_FUNCIONARIO_REDE",
    "CENTRO_CUSTO_REDE": "/INTEGRACAO/CENTRO_CUSTO_REDE",
    "FORNECEDOR_REDE": "/INTEGRACAO/FORNECEDOR_REDE",
}


def _norm(v: Any) -> str:
    return re.sub(r"\s+", " ", str(v or "").strip().upper())


def _money(v: Any) -> Decimal:
    try:
        return Decimal(str(v or 0)).quantize(Decimal("0.01"))
    except Exception:
        return Decimal("0")


def _rows(payload: Any) -> list[dict[str, Any]]:
    if isinstance(payload, list):
        return [r for r in payload if isinstance(r, dict)]
    if isinstance(payload, dict):
        for key in ("resultados", "data", "items"):
            chunk = payload.get(key)
            if isinstance(chunk, list):
                return [r for r in chunk if isinstance(r, dict)]
    return []


def _desc(row: dict[str, Any]) -> str:
    return _norm(
        " ".join(
            str(row.get(k) or "")
            for k in (
                "descricao",
                "descricaoDocumento",
                "planoConta",
                "planoContaGerencialDescricao",
                "observacao",
            )
        )
    )


def _is_workforce(row: dict[str, Any]) -> bool:
    if row.get("expenseNature") == "ADIANTAMENTO":
        return True
    return bool(WORKFORCE_BLOB_RE.search(_desc(row)))


def _classify_provisional(row: dict[str, Any]) -> tuple[str, int, str]:
    blob = _desc(row)
    if row.get("expenseSubNature") == "VALE_FUNCIONARIO":
        return "VALE_FUNCIONARIO", 95, "semantic_subnature"
    for label, patterns, conf in CLASS_RULES:
        for pat in patterns:
            if re.search(pat, blob, re.I):
                return label, conf, f"pattern:{pat}"
    if row.get("funcionarioCodigo"):
        return "OUTROS_FUNCIONARIO", 60, "funcionario_codigo_only"
    return "OUTROS_FUNCIONARIO", 40, "fallback"


def _day_bucket(day: int) -> str:
    for name, rng in PAYROLL_BUCKETS:
        if day in rng:
            return name
    return "unknown"


@dataclass
class ForensicsContext:
    despesas_rede: list[dict[str, Any]] = field(default_factory=list)
    titulos_pagar: list[dict[str, Any]] = field(default_factory=list)
    titulos_receber: list[dict[str, Any]] = field(default_factory=list)
    movimentos: list[dict[str, Any]] = field(default_factory=list)
    transferencias: list[dict[str, Any]] = field(default_factory=list)
    caixa_rows: list[dict[str, Any]] = field(default_factory=list)
    screen_expenses: list[dict[str, Any]] = field(default_factory=list)
    funcionarios: list[dict[str, Any]] = field(default_factory=list)
    vales_endpoint: list[dict[str, Any]] = field(default_factory=list)
    despesa_funcionario: list[dict[str, Any]] = field(default_factory=list)
    endpoint_probe: dict[str, Any] = field(default_factory=dict)


class WorkforceForensicsEngine:
    def discover_workforce(self, ctx: ForensicsContext) -> dict[str, Any]:
        pools: list[tuple[str, list[dict[str, Any]]]] = [
            ("DESPESAS_REDE", ctx.despesas_rede),
            ("TITULO_PAGAR", ctx.titulos_pagar),
            ("TITULO_RECEBER", ctx.titulos_receber),
            ("MOVIMENTO_CONTA", ctx.movimentos),
            ("CAIXA_REDE", ctx.caixa_rows),
            ("SCREEN_EXPENSES", ctx.screen_expenses),
            ("VALE_FUNCIONARIO_REDE", ctx.vales_endpoint),
            ("DESPESA_FUNCIONARIO", ctx.despesa_funcionario),
        ]
        hits: list[dict[str, Any]] = []
        by_source: Counter[str] = Counter()
        desc_counter: Counter[str] = Counter()
        total_valor = Decimal("0")
        with_func_codigo = 0
        with_nome = 0
        with_fornecedor = 0
        with_titulo = 0

        for source, rows in pools:
            for row in rows:
                if not _is_workforce(row) and source not in ("VALE_FUNCIONARIO_REDE", "DESPESA_FUNCIONARIO"):
                    continue
                enriched = {**row, "_source": source}
                hits.append(enriched)
                by_source[source] += 1
                desc_counter[_desc(row)[:80] or "—"] += 1
                total_valor += _money(row.get("valor") or row.get("despesaApurado") or row.get("despesaApresentado"))
                if row.get("funcionarioCodigo"):
                    with_func_codigo += 1
                if row.get("nomeFuncionario") or row.get("funcionarioNome") or row.get("nome"):
                    with_nome += 1
                if row.get("fornecedor") or row.get("nomeFornecedor"):
                    with_fornecedor += 1
                if source.startswith("TITULO"):
                    with_titulo += 1

        top_desc = desc_counter.most_common(30)
        return {
            "totalRecords": len(hits),
            "totalValor": float(total_valor),
            "bySource": dict(by_source),
            "topDescriptions": top_desc,
            "withFuncionarioCodigo": with_func_codigo,
            "withNome": with_nome,
            "withFornecedor": with_fornecedor,
            "withTitulo": with_titulo,
            "pctFuncionarioCodigo": round(with_func_codigo / max(len(hits), 1) * 100, 2),
            "samples": hits[:5],
        }

    def classify_adiantamentos(self, ctx: ForensicsContext) -> dict[str, Any]:
        adiantamentos = [
            r for r in ctx.screen_expenses
            if r.get("expenseNature") == "ADIANTAMENTO" or _is_workforce(r)
        ]
        if not adiantamentos:
            adiantamentos = [r for r in ctx.screen_expenses if _is_workforce(r)]

        by_type: Counter[str] = Counter()
        valor_by_type: dict[str, Decimal] = defaultdict(lambda: Decimal("0"))
        confidences: list[int] = []
        classified_rows: list[dict[str, Any]] = []

        for row in adiantamentos:
            ptype, conf, reason = _classify_provisional(row)
            by_type[ptype] += 1
            valor_by_type[ptype] += _money(row.get("valor"))
            confidences.append(conf)
            classified_rows.append(
                {
                    "provisionalType": ptype,
                    "confidence": conf,
                    "reason": reason,
                    "valor": str(_money(row.get("valor"))),
                    "descricao": row.get("descricao"),
                    "funcionarioCodigo": row.get("funcionarioCodigo"),
                    "data": row.get("data"),
                }
            )

        total = max(len(adiantamentos), 1)
        pct = {k: round(v / total * 100, 2) for k, v in by_type.items()}
        avg_conf = round(sum(confidences) / len(confidences), 1) if confidences else 0.0
        unknown = by_type.get("OUTROS_FUNCIONARIO", 0)

        return {
            "totalAdiantamentos": len(adiantamentos),
            "byProvisionalType": dict(by_type),
            "valorByProvisionalType": {k: float(v) for k, v in valor_by_type.items()},
            "pctByProvisionalType": pct,
            "avgConfidence": avg_conf,
            "unknownCount": unknown,
            "unknownPct": round(unknown / total * 100, 2),
            "samplesByType": {
                t: [r for r in classified_rows if r["provisionalType"] == t][:3]
                for t in PROVISIONAL_TYPES
                if by_type.get(t)
            },
        }

    def payroll_calendar(self, ctx: ForensicsContext) -> dict[str, Any]:
        workforce = [r for r in ctx.screen_expenses if _is_workforce(r) or r.get("expenseNature") == "ADIANTAMENTO"]
        by_bucket: Counter[str] = Counter()
        valor_bucket: dict[str, Decimal] = defaultdict(lambda: Decimal("0"))
        by_day: Counter[int] = Counter()
        by_emp_val: dict[Any, list[float]] = defaultdict(list)

        for row in workforce:
            dt = str(row.get("data") or "")[:10]
            try:
                day = int(dt[8:10])
            except ValueError:
                continue
            bucket = _day_bucket(day)
            by_bucket[bucket] += 1
            valor_bucket[bucket] += _money(row.get("valor"))
            by_day[day] += 1
            emp = row.get("funcionarioCodigo")
            if emp:
                by_emp_val[emp].append(float(_money(row.get("valor"))))

        recurring_fixed: list[dict[str, Any]] = []
        for emp, vals in by_emp_val.items():
            if len(vals) >= 3:
                stdev = statistics.pstdev(vals) if len(vals) > 1 else 0.0
                if stdev < max(statistics.mean(vals) * 0.05, 1.0):
                    recurring_fixed.append(
                        {"funcionarioCodigo": emp, "ocorrencias": len(vals), "valorMedio": round(statistics.mean(vals), 2)}
                    )

        d15 = by_bucket.get("dia_11_15", 0)
        d_end = by_bucket.get("dia_26_31", 0)
        total = max(sum(by_bucket.values()), 1)

        return {
            "byBucket": dict(by_bucket),
            "valorByBucket": {k: float(v) for k, v in valor_bucket.items()},
            "pctByBucket": {k: round(v / total * 100, 2) for k, v in by_bucket.items()},
            "byDay": dict(sorted(by_day.items())),
            "concentrationDay15": round(d15 / total * 100, 2),
            "concentrationEndMonth": round(d_end / total * 100, 2),
            "quinzenalPattern": d15 > total * 0.15,
            "endMonthPattern": d_end > total * 0.20,
            "recurringFixedByEmployee": sorted(recurring_fixed, key=lambda x: x["ocorrencias"], reverse=True)[:20],
            "payrollPeriodCaptured": total > 0,
        }

    def employee_match(self, ctx: ForensicsContext) -> dict[str, Any]:
        workforce = [r for r in ctx.screen_expenses if _is_workforce(r)]
        total = max(len(workforce), 1)
        with_code = sum(1 for r in workforce if r.get("funcionarioCodigo"))
        with_name = sum(1 for r in workforce if r.get("nomeFuncionario") or r.get("funcionarioNome"))
        desc_match = 0
        titulo_match = 0
        for row in workforce:
            blob = _desc(row)
            if any(_norm(f.get("nome") or f.get("nomeFuncionario") or "")[:4] in blob for f in ctx.funcionarios if f.get("nome")):
                desc_match += 1
            val = float(_money(row.get("valor")))
            emp = row.get("empresaCodigo")
            for t in ctx.titulos_pagar + ctx.titulos_receber:
                if t.get("empresaCodigo") == emp and abs(float(_money(t.get("valor"))) - val) < 0.02:
                    titulo_match += 1
                    break

        unlinked = total - with_code - desc_match
        blocked = [k for k, v in ctx.endpoint_probe.items() if v.get("status") in (401, 403, 404)]

        return {
            "totalWorkforce": len(workforce),
            "pctFuncionarioCodigo": round(with_code / total * 100, 2),
            "pctNome": round(with_name / total * 100, 2),
            "pctDescMatch": round(desc_match / total * 100, 2),
            "pctTituloMatch": round(titulo_match / total * 100, 2),
            "pctUnlinked": round(max(unlinked, 0) / total * 100, 2),
            "funcionariosCatalogo": len(ctx.funcionarios),
            "blockedEndpoints": blocked,
            "endpointProbe": ctx.endpoint_probe,
        }

    def cash_loss_accountability(self, ctx: ForensicsContext) -> dict[str, Any]:
        losses: list[dict[str, Any]] = []
        for row in ctx.caixa_rows:
            diff = _money(row.get("diferenca") or row.get("dinheiroDiferenca") or row.get("valorDiferenca"))
            if diff == 0:
                ap = _money(row.get("ap_despesaApresentado") or row.get("despesaApresentado"))
                au = _money(row.get("ap_despesaApurado") or row.get("despesaApurado"))
                diff = ap - au
            if diff == 0:
                continue
            if diff > 0:
                continue
            losses.append(
                {
                    "empresaCodigo": row.get("empresaCodigo"),
                    "caixaCodigo": row.get("caixaCodigo"),
                    "funcionarioCodigo": row.get("funcionarioCodigo"),
                    "pdvCodigo": row.get("pdvCodigo"),
                    "turnoCodigo": row.get("turnoCodigo"),
                    "data": str(row.get("data") or row.get("fechamento") or "")[:10],
                    "valorDiferenca": float(abs(diff)),
                    "diferenca": float(diff),
                }
            )

        semantic_adjustments = [
            r for r in ctx.screen_expenses if r.get("expenseNature") == "AJUSTE_OPERACIONAL"
            or re.search(r"QUEBRA|DIFEREN", _desc(r), re.I)
        ]

        destinations: Counter[str] = Counter()
        traced = 0
        for loss in losses:
            dest = self._resolve_cash_loss_dest(loss, ctx)
            destinations[dest] += 1
            if dest != "SEM_DESTINO_IDENTIFICADO":
                traced += 1

        total_losses = max(len(losses), 1)
        total_valor = sum(l["valorDiferenca"] for l in losses)

        return {
            "cashShortages": len(losses),
            "totalShortageValor": round(total_valor, 2),
            "semanticAjustes": len(semantic_adjustments),
            "destinations": dict(destinations),
            "pctTraced": round(traced / total_losses * 100, 2) if losses else 0.0,
            "pctUntraced": round((len(losses) - traced) / total_losses * 100, 2) if losses else 0.0,
            "generatesTituloReceber": destinations.get("TITULO_RECEBER_FUNCIONARIO", 0),
            "generatesDescontoFuncionario": destinations.get("DESCONTO_FUNCIONARIO", 0),
            "inDespesasRede": destinations.get("DESPESA_FUNCIONARIO", 0) + destinations.get("PERDA_OPERACIONAL_EMPRESA", 0),
            "onlyOperational": destinations.get("AJUSTE_TEMPORARIO", 0) + destinations.get("SEM_DESTINO_IDENTIFICADO", 0),
            "samples": losses[:10],
        }

    def _resolve_cash_loss_dest(self, loss: dict[str, Any], ctx: ForensicsContext) -> str:
        emp = loss.get("funcionarioCodigo")
        val = loss.get("valorDiferenca")
        data = loss.get("data")
        empresa = loss.get("empresaCodigo")

        for t in ctx.titulos_receber:
            if t.get("empresaCodigo") == empresa and abs(float(_money(t.get("valor"))) - val) < 1.0:
                if emp and t.get("funcionarioCodigo") == emp:
                    return "TITULO_RECEBER_FUNCIONARIO"
                return "TITULO_RECEBER_FUNCIONARIO"

        for d in ctx.despesa_funcionario:
            if abs(float(_money(d.get("valor"))) - val) < 1.0:
                return "DESCONTO_FUNCIONARIO"

        for d in ctx.despesas_rede:
            blob = _desc(d)
            if re.search(r"QUEBRA|DIFEREN|DESCONT", blob, re.I) and abs(float(_money(d.get("valor"))) - val) < 5.0:
                return "DESPESA_FUNCIONARIO" if emp else "PERDA_OPERACIONAL_EMPRESA"

        for m in ctx.movimentos:
            if abs(float(_money(m.get("valor"))) - val) < 1.0:
                return "PERDA_OPERACIONAL_EMPRESA"

        if emp:
            return "AJUSTE_TEMPORARIO"
        return "SEM_DESTINO_IDENTIFICADO"

    def financial_impact(self, classification: dict[str, Any], cash_loss: dict[str, Any]) -> dict[str, Any]:
        vb = classification.get("valorByProvisionalType") or {}
        return {
            "totalAdiantamentos": classification.get("totalAdiantamentos"),
            "valorVales": vb.get("VALE_FUNCIONARIO", 0),
            "valorQuinzenas": vb.get("QUINZENA", 0),
            "valorSalarios": vb.get("SALARIO", 0),
            "valorExtras": vb.get("EXTRA_FUNCIONARIO", 0) + vb.get("HORA_EXTRA", 0),
            "valorFolguistas": vb.get("FOLGUISTA", 0),
            "valorEmprestimos": vb.get("EMPRESTIMO_FUNCIONARIO", 0),
            "valorPerdasCaixa": cash_loss.get("totalShortageValor", 0),
            "valorPotencialDescontoFuncionario": cash_loss.get("totalShortageValor", 0)
            * (cash_loss.get("pctTraced", 0) / 100),
            "valorAbsorvidoEmpresa": cash_loss.get("totalShortageValor", 0)
            * (cash_loss.get("pctUntraced", 0) / 100),
        }

    def management_prep(self, classification: dict[str, Any]) -> dict[str, Any]:
        mapping = []
        for ptype, count in (classification.get("byProvisionalType") or {}).items():
            if ptype in ("SALARIO", "QUINZENA", "FOLGUISTA", "HORA_EXTRA", "EXTRA_FUNCIONARIO", "PREMIACAO"):
                mgmt = "PESSOAL"
                group = "RH"
                dre = True
            elif ptype in ("VALE_FUNCIONARIO", "ADIANTAMENTO_SALARIAL", "EMPRESTIMO_FUNCIONARIO"):
                mgmt = "PESSOAL_VALE"
                group = "TESOURARIA"
                dre = False
            elif ptype == "REEMBOLSO_FUNCIONARIO":
                mgmt = "PESSOAL_REEMBOLSO"
                group = "ADMINISTRATIVO"
                dre = True
            else:
                mgmt = "OUTROS_FUNCIONARIO"
                group = "OPERACAO_CAIXA"
                dre = False
            mapping.append(
                {
                    "expenseNature": "ADIANTAMENTO",
                    "expenseSubNature": ptype,
                    "expenseManagementClass": mgmt,
                    "expenseManagementGroup": group,
                    "impactsDRE": dre,
                    "count": count,
                }
            )
        return {"mapping": mapping, "recommendedTaxonomy": list({m["expenseManagementClass"] for m in mapping})}

    def payroll_separation(self, classification: dict[str, Any], cash_loss: dict[str, Any]) -> dict[str, Any]:
        return {
            "despesaPessoal": ["SALARIO", "QUINZENA", "FOLGUISTA", "HORA_EXTRA", "EXTRA_FUNCIONARIO", "PREMIACAO"],
            "adiantamento": ["VALE_FUNCIONARIO", "ADIANTAMENTO_SALARIAL", "EMPRESTIMO_FUNCIONARIO"],
            "contasReceberFuncionario": ["EMPRESTIMO_FUNCIONARIO"],
            "perdaOperacional": ["PERDA_CAIXA_EMPRESA", "PERDA_CAIXA_FUNCIONARIO"],
            "impactsDRE": ["SALARIO", "QUINZENA", "FOLGUISTA", "SERVICOS_PESSOAL"],
            "notImpactsDRE": ["VALE_FUNCIONARIO", "ADIANTAMENTO_SALARIAL", "MOVIMENTACAO_CAIXA"],
            "cashLossTracedPct": cash_loss.get("pctTraced"),
        }


async def probe_optional_endpoints(base_url: str, api_key: str, di: str, df: str) -> dict[str, Any]:
    results: dict[str, Any] = {}
    params = {"dataInicial": di, "dataFinal": df, "CHAVE": api_key}
    async with httpx.AsyncClient(base_url=base_url, timeout=30.0) as client:
        for key, path in OPTIONAL_ENDPOINTS.items():
            try:
                resp = await client.get(path, params=params)
                rows = _rows(resp.json() if resp.headers.get("content-type", "").startswith("application/json") else [])
                results[key] = {
                    "path": path,
                    "status": resp.status_code,
                    "rowCount": len(rows),
                    "sample": rows[:2],
                }
            except Exception as exc:
                results[key] = {"path": path, "status": 0, "error": str(exc)[:120]}
    return results


async def load_context(
    overview: Any,
    lineage: Any,
    semantic: Any,
    filters: Any,
    config: Any,
    endpoint_probe: dict[str, Any] | None = None,
    funcionarios: list[dict[str, Any]] | None = None,
    vales_endpoint: list[dict[str, Any]] | None = None,
    despesa_funcionario: list[dict[str, Any]] | None = None,
) -> ForensicsContext:
    import asyncio

    ctx = ForensicsContext()
    ctx.screen_expenses, err = await overview._load_screen_expenses(filters)
    if err:
        ctx.screen_expenses = []

    lineage_ctx = await lineage.build_context(overview, filters)
    ctx.despesas_rede = lineage_ctx.despesas_rede
    ctx.titulos_pagar = lineage_ctx.titulos
    ctx.movimentos = lineage_ctx.movimentos
    ctx.transferencias = lineage_ctx.transferencias
    ctx.caixa_rows = list(lineage_ctx.closure_by_key.values())

    tr_resp = await overview.client.call_endpoint(
        "titulo_receber",
        params={"dataInicial": filters.data_inicial, "dataFinal": filters.data_final},
    )
    if tr_resp.success:
        ctx.titulos_receber = overview._rows(tr_resp.data)

    for row in ctx.screen_expenses:
        enriched = semantic.classify_row(lineage.enrich_row(row, lineage_ctx))
        row.update(enriched)

    ctx.endpoint_probe = endpoint_probe or {}
    ctx.funcionarios = funcionarios or []
    ctx.vales_endpoint = vales_endpoint or []
    ctx.despesa_funcionario = despesa_funcionario or []

    return ctx


async def bootstrap_optional_sources(
    config: Any,
    di: str,
    df: str,
) -> tuple[dict[str, Any], list[dict[str, Any]], list[dict[str, Any]], list[dict[str, Any]]]:
    probe = await probe_optional_endpoints(config.webposto_base_url, config.webposto_api_key, di, df)
    funcionarios: list[dict[str, Any]] = []
    vales: list[dict[str, Any]] = []
    desp_func: list[dict[str, Any]] = []
    if probe.get("FUNCIONARIO_REDE", {}).get("status") == 200:
        funcionarios = await _fetch_probe_full(config, "/INTEGRACAO/FUNCIONARIO_REDE", di, df)
    for vk in ("VALE_FUNCIONARIO_REDE", "VALE_FUNCIONARIO_REDE_ALT"):
        p = probe.get(vk, {})
        if p.get("status") == 200 and p.get("rowCount", 0) > 0:
            vales = await _fetch_probe_full(config, p["path"], di, df)
            break
    for dk in ("DESPESA_FUNCIONARIO", "DESPESA_FUNCIONARIO_REDE"):
        p = probe.get(dk, {})
        if p.get("status") == 200 and p.get("rowCount", 0) > 0:
            desp_func = await _fetch_probe_full(config, p["path"], di, df)
            break
    return probe, funcionarios, vales, desp_func


async def _fetch_probe_full(config: Any, path: str, di: str, df: str) -> list[dict[str, Any]]:
    params = {"dataInicial": di, "dataFinal": df, "CHAVE": config.webposto_api_key}
    async with httpx.AsyncClient(base_url=config.webposto_base_url, timeout=60.0) as client:
        resp = await client.get(path, params=params)
        if resp.status_code != 200:
            return []
        return _rows(resp.json())
