"""DRE & Despesas Classificadas — leitura rápida de snapshots locais + receita pista.

D0/D-1: sem chamada síncrona pesada ao WebPosto; snapshots + fuel_volumetry (RAM/DB).
"""

from __future__ import annotations

import json
import logging
import time
from collections import defaultdict
from datetime import date
from decimal import Decimal
from pathlib import Path
from typing import Any

from pydantic import BaseModel, Field

from src.utils.filial_normalizer import (
    EMPRESA_CASA_CAIADA,
    EMPRESA_REAL_DOZE,
    EMPRESA_VIP,
    resolve_empresa_codigo,
)

LOGGER = logging.getLogger(__name__)
ROOT = Path(__file__).resolve().parents[2]
SNAPSHOTS = ROOT / "snapshots"

FILIAIS: dict[int, str] = {
    EMPRESA_CASA_CAIADA: "AP CASA CAIADA",
    EMPRESA_VIP: "POSTO VIP",
    EMPRESA_REAL_DOZE: "POSTO REAL / DOZE",
}

EXPENSE_KEYWORD_RULES = [
    ("PESSOAL", ["pessoal", "salario", "salário", "folha", "encargo", "fgts", "inss", "beneficio", "benefício", "comissao", "comissão"]),
    ("OPERACIONAL", ["operacional", "energia", "agua", "água", "manutencao", "manutenção", "frete", "seguranca", "segurança", "aluguel", "limpeza", "telefone", "internet", "mdr", "taxa"]),
    ("ADMINISTRATIVA", ["administrativ", "contabil", "contábil", "escritorio", "escritório"]),
    ("COMPRAS", ["compra", "mercadoria", "estoque", "fornecedor"]),
]


class ExpensesDreResult(BaseModel):
    success: bool = True
    fromCache: bool = True
    fonte: str = ""
    latencyMs: float = 0.0
    periodo: dict[str, str] = Field(default_factory=dict)
    empresaCodigo: int | None = None
    payload: dict[str, Any] = Field(default_factory=dict)
    observacoes: list[str] = Field(default_factory=list)


def _dec(value: Any) -> Decimal:
    try:
        return Decimal(str(value or 0))
    except Exception:
        return Decimal("0")


def _f(value: Any) -> float:
    return float(_dec(value))


def _load_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def _latest_snapshot(glob_pattern: str) -> Path | None:
    matches = sorted(
        SNAPSHOTS.glob(glob_pattern), key=lambda p: p.stat().st_mtime, reverse=True
    )
    return matches[0] if matches else None


def _pick_finance_snapshot(empresa: int | None) -> Path | None:
    """Prefere snapshot de rede (*_all.json); evita pegar arquivo de uma única filial."""
    if empresa is not None:
        filial = _latest_snapshot(f"finance_center/finance_center_all_*_{empresa}.json")
        if filial:
            return filial
    # Rede: termina com _all.json (não _5555.json / _74014.json)
    network = [
        p
        for p in SNAPSHOTS.glob("finance_center/finance_center_all_*.json")
        if p.stem.endswith("_all")
    ]
    if network:
        return sorted(network, key=lambda p: p.stat().st_mtime, reverse=True)[0]
    return _latest_snapshot("finance_center/finance_center_all_*.json")


def _pick_director_snapshot(empresa: int | None) -> Path | None:
    if empresa is not None:
        filial = _latest_snapshot(
            f"director_financial_reconciliation/director-reconciliation_*_{empresa}.json"
        )
        if filial:
            return filial
    network = [
        p
        for p in SNAPSHOTS.glob(
            "director_financial_reconciliation/director-reconciliation_*.json"
        )
        if "network" in p.stem or p.stem.endswith("_all")
    ]
    if network:
        return sorted(network, key=lambda p: p.stat().st_mtime, reverse=True)[0]
    return _latest_snapshot(
        "director_financial_reconciliation/director-reconciliation_*.json"
    )


def _auto_classify(director: dict[str, Any]) -> dict[str, Any]:
    facts = director.get("data", {}).get("reviewableFacts", []) or []
    unclassified: list[dict[str, Any]] = []
    for fact in facts:
        if not isinstance(fact, dict):
            continue
        taxonomy = fact.get("taxonomySuggestion", {}) or {}
        method = fact.get("method", "")
        if method == "NO_EVIDENCE" or taxonomy.get("requires_review") is True:
            unclassified.append(fact)

    classified: list[dict[str, Any]] = []
    by_category: dict[str, Decimal] = defaultdict(lambda: Decimal("0"))
    by_company_category: dict[int, dict[str, Decimal]] = defaultdict(
        lambda: defaultdict(lambda: Decimal("0"))
    )
    remaining = 0

    for fact in unclassified:
        text = " ".join(
            str(x)
            for x in [fact.get("document"), fact.get("description"), fact.get("supplier")]
            if x
        ).lower()
        account = str(fact.get("managementAccountCode") or "")
        category: str | None = None
        for cat, keywords in EXPENSE_KEYWORD_RULES:
            if any(kw in text or kw in account for kw in keywords):
                category = cat
                break
        if category is None:
            taxonomy_cat = taxonomy.get("category")
            if taxonomy_cat and taxonomy_cat not in (
                "AGUARDANDO CLASSIFICACAO",
                "SEM EVIDENCIA SUFICIENTE",
            ):
                category = str(taxonomy_cat)
        if category is None:
            remaining += 1
            category = "AGUARDANDO CLASSIFICACAO"

        amount = _dec(fact.get("amount"))
        company = int(fact.get("companyCode") or 0)
        classified.append(
            {
                "fact_id": fact.get("factId"),
                "company_code": company,
                "company_name": fact.get("companyName")
                or FILIAIS.get(company, f"Filial {company}"),
                "date": fact.get("date"),
                "amount": float(amount),
                "category": category,
                "original_taxonomy": taxonomy.get("category"),
                "text": text[:200],
            }
        )
        by_category[category] += amount
        by_company_category[company][category] += amount

    return {
        "classified": classified,
        "by_category": {k: float(v) for k, v in by_category.items()},
        "by_company_category": {
            k: {ck: float(cv) for ck, cv in v.items()} for k, v in by_company_category.items()
        },
        "count": len(classified),
        "remaining": remaining,
    }


class ExpensesDreService:
    async def build(
        self,
        data_inicial: str,
        data_final: str,
        empresa_codigo: int | None = None,
        regime: str | None = None,
    ) -> ExpensesDreResult:
        from src.services.dre_regime import (
            classify_period_lock,
            filter_rows_by_regime,
            normalize_regime,
            regime_label,
        )

        t0 = time.perf_counter()
        empresa = resolve_empresa_codigo(empresa_codigo)
        regime_norm = normalize_regime(regime)
        period_lock = classify_period_lock(data_inicial, data_final)
        obs: list[str] = [
            f"empresa={'TODAS' if empresa is None else empresa}",
            f"regime={regime_norm}",
            f"periodLock={period_lock.get('mode')}",
            "Fonte: snapshots locais (finance_center + director) + receita pista rápida",
        ]

        finance_path = _pick_finance_snapshot(empresa)
        director_path = _pick_director_snapshot(empresa)

        finance = _load_json(finance_path) if finance_path else {}
        director = _load_json(director_path) if director_path else {}
        if finance_path:
            obs.append(f"finance_snapshot={finance_path.name}")
        if director_path:
            obs.append(f"director_snapshot={director_path.name}")

        center = finance.get("center", {}) if isinstance(finance, dict) else {}
        summary = center.get("summary", {}) or {}
        expenses_summary = (center.get("expenses", {}) or {}).get("resumo", {}) or {}

        auto = _auto_classify(director)
        classified = list(auto["classified"])
        if empresa is not None:
            classified = [c for c in classified if int(c.get("company_code") or 0) == empresa]
        # Snapshot director: filtra por data efetiva do regime quando disponível
        classified = filter_rows_by_regime(
            [
                {
                    **c,
                    "data": c.get("date") or c.get("data") or c.get("effective_date"),
                    "dataPagamento": c.get("dataPagamento") or c.get("payment_date"),
                    "dataCompetencia": c.get("date") or c.get("data") or c.get("effective_date"),
                }
                for c in classified
            ],
            data_inicial,
            data_final,
            regime_norm,
        ) or classified
        obs.append(f"regimeLabel={regime_label(regime_norm)}")

        # Receita + CPV pista real (D0 RAM / D-1 DB) — margem em R$/L
        receita_pista = 0.0
        litros_pista = 0.0
        cpv_pista = 0.0
        margem_pista = 0.0
        margem_rs_litro = 0.0
        custo_medio_l = 0.0
        try:
            from src.services.fuel_cpv_engine import compute_fuel_cpv
            from src.services.fuel_volumetry_service import get_fuel_volumetry_service

            fuel = await get_fuel_volumetry_service().build(
                data_inicial=data_inicial,
                data_final=data_final,
                empresa_codigo=empresa,
            )
            receita_pista = float(fuel.total_valor or 0)
            litros_pista = float(fuel.total_litros or 0)
            fuel_cpv = compute_fuel_cpv(
                litros_total=litros_pista,
                faturamento_combustivel=receita_pista,
                products=[r.model_dump() for r in (fuel.por_produto or [])],
            )
            cpv_pista = float(fuel_cpv["cpv"])
            margem_pista = float(fuel_cpv["margem_bruta"])
            margem_rs_litro = float(fuel_cpv["margem_bruta_rs_litro"])
            custo_medio_l = float(fuel_cpv["custo_medio_rs_litro"])
            obs.append(
                f"receita_pista={receita_pista:.2f} cpv={cpv_pista:.2f} "
                f"margem_rs_l={margem_rs_litro:.4f} fonte_fuel={fuel.fonte}"
            )
        except Exception as exc:
            LOGGER.warning("receita/CPV pista falhou: %s", exc)
            obs.append(f"receita_pista indisponível: {exc}")

        por_empresa_raw = expenses_summary.get("porEmpresa") or {}
        por_empresa: list[dict[str, Any]] = []
        total_desp = 0.0
        for emp_key, val in por_empresa_raw.items():
            emp = int(emp_key)
            if empresa is not None and emp != empresa:
                continue
            v = _f(val)
            total_desp += v
            por_empresa.append(
                {
                    "empresa_codigo": emp,
                    "nome": FILIAIS.get(emp, f"Filial {emp}"),
                    "valor": v,
                }
            )

        # Categorias: se filial, prefere breakdown auto-classificado da filial; senão snapshot
        por_categoria: list[dict[str, Any]] = []
        if empresa is not None and auto["by_company_category"].get(empresa):
            for cat, val in sorted(
                auto["by_company_category"][empresa].items(),
                key=lambda x: -x[1],
            ):
                por_categoria.append({"categoria": cat, "valor": val})
            if not total_desp:
                total_desp = sum(c["valor"] for c in por_categoria)
        else:
            cats = expenses_summary.get("porCategoriaLogos") or {}
            network_total = _f(expenses_summary.get("totalValor")) or sum(
                _f(v) for v in por_empresa_raw.values()
            )
            scale = 1.0
            if empresa is not None and network_total > 0 and total_desp > 0:
                scale = total_desp / network_total
            for cat, val in cats.items():
                por_categoria.append({"categoria": cat, "valor": round(_f(val) * scale, 2)})
            if empresa is None:
                total_desp = _f(expenses_summary.get("totalValor")) or total_desp

        # DRE departments
        lines = (director.get("data", {}) or {}).get("executiveSummary", []) or []
        departments: list[dict[str, Any]] = []
        for line in lines:
            if not isinstance(line, dict):
                continue
            emp = int(line.get("companyCode") or 0)
            if empresa is not None and emp != empresa:
                continue
            departments.append(
                {
                    "empresa_codigo": emp,
                    "nome": line.get("companyName") or FILIAIS.get(emp, f"Filial {emp}"),
                    "departamento": line.get("department") or "",
                    "confirmed_dre_amount": _f(line.get("confirmedDreAmount")),
                    "confirmed_matches": int(line.get("confirmedMatches", 0) or 0),
                    "unmatched": int(line.get("unmatched", 0) or 0),
                }
            )

        remaining = auto["remaining"]
        if empresa is not None:
            # remanescentes aproximados na filial
            remaining = sum(
                1
                for c in classified
                if c.get("category") == "AGUARDANDO CLASSIFICACAO"
            )

        from src.services.dre_analytics import vertical_analysis
        from src.services.dre_variance import pista_metrics

        despesas_fixas = max(0.0, float(total_desp) - float(cpv_pista))
        metricas_pista = pista_metrics(
            margem_bruta_combustivel=margem_pista,
            litros=litros_pista,
            despesas_operacionais_fixas=despesas_fixas,
        )
        analise_vertical = vertical_analysis(
            {
                "receita": receita_pista,
                "cpv": cpv_pista,
                "margemBruta": margem_pista,
                "despesas": total_desp,
                "despesasOperacionais": despesas_fixas,
                "resultado": receita_pista - total_desp,
            },
            receita_liquida=receita_pista,
        )

        periodo = {"inicio": data_inicial, "fim": data_final}
        payload = {
            "gerado_em": date.today().isoformat(),
            "sprint": "Sprint2.5-health-synthesis",
            "periodo_principal": periodo,
            "metricas_pista": metricas_pista,
            "analise_vertical_pct_rl": analise_vertical,
            "filiais_monitoradas": [
                {"empresa_codigo": k, "nome": v} for k, v in FILIAIS.items()
            ],
            "bloco_1_combustiveis": {
                "titulo": "Pista — Receita, CPV e Margem R$/L",
                "status": "OK",
                "periodo": periodo,
                "resumo": {
                    "total_litros": litros_pista,
                    "total_valor": receita_pista,
                    "cpv_real": cpv_pista,
                    "margem_bruta": margem_pista,
                    "margem_bruta_rs_litro": margem_rs_litro,
                    "custo_medio_rs_litro": custo_medio_l,
                    "total_transacoes": 0,
                    "por_filial": [],
                    "por_produto": [],
                    "observacao": (
                        "Margem Bruta (Pista) = Receita − CPV (litros × custo aquisição "
                        "distribuidora/CPM). Indicador: R$/Litro."
                    ),
                },
                "ranking_filial": [],
            },
            "bloco_3_margens": {
                "periodo": periodo,
                "pista": {
                    "faturamento": receita_pista,
                    "volume_litros": litros_pista,
                    "cpv": cpv_pista,
                    "margem_bruta": margem_pista,
                    "margem_bruta_rs_litro": margem_rs_litro,
                },
                "conveniencia": {
                    "faturamento": 0,
                    "cpv": 0,
                    "margem_bruta": 0,
                    "margem_bruta_pct": 0,
                    "observacao": "Conveniência via composition na DRE Executiva",
                },
            },
            "bloco_4_conveniencia": {
                "receita_total": 0,
                "observacao": "Conveniência omitida no path rápido (não bloqueia KPIs)",
            },
            "bloco_5_dre": {
                "titulo": "DRE Consolidada",
                "status": "DISPONÍVEL" if remaining == 0 else "PARCIAL",
                "periodo": periodo,
                "departamentos_confirmados": departments,
                "despesas_auto_classificadas": classified,
                "resumo_auto_classificacao": {
                    "total_classificadas": len(classified),
                    "remanescentes_nao_classificadas": remaining,
                    "valor_por_categoria": auto["by_category"],
                    "valor_por_filial_categoria": auto["by_company_category"],
                },
                "observacao": "Snapshot director_financial_reconciliation",
            },
            "bloco_6_despesas": {
                "titulo": "Despesas Classificadas",
                "status": "OK",
                "periodo": periodo,
                "total_despesas_gerenciais": round(total_desp, 2),
                "por_categoria": por_categoria,
                "por_empresa": por_empresa,
                # UI tipa como AutoClassifiedExpense[] — envia fatos, não só categorias
                "auto_classificadas": classified,
                "contas_pagar": summary.get("contasPagar", {}),
                "contas_receber": summary.get("contasReceber", {}),
            },
            "regime": regime_norm,
            "regimeLabel": regime_label(regime_norm),
            "periodLock": period_lock,
            "fonte": "snapshots+fuel_volumetry",
            "fromCache": True,
            "observacoes": obs,
        }

        latency = round((time.perf_counter() - t0) * 1000.0, 3)
        return ExpensesDreResult(
            fromCache=True,
            fonte="snapshots+fuel_volumetry",
            latencyMs=latency,
            periodo=periodo,
            empresaCodigo=empresa,
            payload=payload,
            observacoes=obs,
        )


_svc: ExpensesDreService | None = None


def get_expenses_dre_service() -> ExpensesDreService:
    global _svc
    if _svc is None:
        _svc = ExpensesDreService()
    return _svc
