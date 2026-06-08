"""Inteligência Financeira Avançada — F01.4-B."""
from __future__ import annotations

import json
import logging
import math
from collections import defaultdict
from datetime import datetime
from decimal import Decimal
from pathlib import Path
from typing import Any

from src.models.response_model import WebPostoResponse
from src.services.corporate_finance_center_service import CorporateFinanceCenterService
from src.services.multiselect_utils import empresa_snapshot_suffix
from src.services.network_financial_overview_service import FinancialOverviewFilters

LOGGER = logging.getLogger(__name__)
MAPPING_PATH = Path(__file__).resolve().parents[2] / "config" / "account_category_mapping.json"

DRE_LINES = (
    "receitaBruta",
    "cmv",
    "despesasOperacionais",
    "despesasAdministrativas",
    "despesasFinanceiras",
    "despesasTributarias",
    "resultadoOperacional",
    "resultadoLiquido",
)

V3_TO_DRE: dict[str, str] = {
    "OPERACIONAL": "despesasOperacionais",
    "PESSOAL": "despesasOperacionais",
    "ENERGIA": "despesasOperacionais",
    "MANUTENÇÃO": "despesasOperacionais",
    "COMPRAS": "cmv",
    "VEÍCULOS": "despesasOperacionais",
    "FRETES": "despesasOperacionais",
    "SERVIÇOS": "despesasAdministrativas",
    "TECNOLOGIA": "despesasAdministrativas",
    "MARKETING": "despesasOperacionais",
    "ALUGUÉIS": "despesasAdministrativas",
    "FINANCEIRO": "despesasFinanceiras",
    "TRIBUTÁRIO": "despesasTributarias",
    "SEGUROS": "despesasAdministrativas",
    "OUTROS": "despesasOperacionais",
}


def _dec(value: Any) -> Decimal:
    try:
        return Decimal(str(value or 0))
    except Exception:
        return Decimal("0")


def _q2(value: Decimal) -> str:
    return str(value.quantize(Decimal("0.01")))


def _pct(part: Decimal, whole: Decimal) -> str:
    if not whole:
        return "0.00"
    return _q2(part / whole * 100)


def _load_plano_catalog() -> dict[int, dict[str, Any]]:
    if not MAPPING_PATH.exists():
        return {}
    doc = json.loads(MAPPING_PATH.read_text(encoding="utf-8"))
    return {int(m["codigoGerencial"]): m for m in doc.get("mappings") or [] if m.get("codigoGerencial")}


def _benchmark_class(ratio: float) -> str:
    if ratio <= 0.85:
        return "Excelente"
    if ratio <= 1.0:
        return "Bom"
    if ratio <= 1.25:
        return "Medio"
    return "Critico"


def _anomaly_severity(z: float) -> str:
    az = abs(z)
    if az >= 4:
        return "CRITICAL"
    if az >= 3:
        return "HIGH"
    if az >= 2.5:
        return "MEDIUM"
    return "LOW"


class FinancialIntelligenceAdvancedService:
    def __init__(self, finance_center: CorporateFinanceCenterService) -> None:
        self._fc = finance_center

    @staticmethod
    def snapshot_key(data_inicial: str, data_final: str, empresa_codigo: str | int | None) -> str:
        suffix = empresa_snapshot_suffix(empresa_codigo)
        return f"finance:advanced:{data_inicial}:{data_final}:{suffix}"

    async def build(
        self,
        filters: FinancialOverviewFilters,
        empresa_codigo_raw: str | int | None,
    ) -> WebPostoResponse:
        raw, err = await self._fc._overview._load_filtered_expenses(filters)
        if err is not None:
            return err
        expenses = self._fc._filter_expenses(raw, filters)
        pay_rows, _ = await self._fc._fetch_titulo_pagar_all(filters)

        plano_catalog = _load_plano_catalog()
        total = Decimal("0")
        by_plano: dict[int, dict[str, Any]] = {}
        by_empresa: dict[str, Decimal] = defaultdict(Decimal)
        by_day: dict[str, Decimal] = defaultdict(Decimal)
        by_centro: dict[str, dict[str, Any]] = defaultdict(
            lambda: {"valor": Decimal("0"), "count": 0, "empresas": set()}
        )
        matrix_centro_filial: dict[str, dict[str, Decimal]] = defaultdict(lambda: defaultdict(Decimal))

        dq = {"planoConta": 0, "centroCusto": 0, "fornecedor": 0, "categoriaV3": 0, "classificationSource": 0}
        n = len(expenses) or 1

        for row in expenses:
            val = _dec(row.get("valor"))
            total += val
            emp = str(row.get("empresaCodigo") or "")
            by_empresa[emp] += val
            day = str(row.get("data") or "")[:10]
            by_day[day] += val

            raw_row = row.get("raw") or {}
            pc = raw_row.get("planoContaGerencialCodigo") or row.get("planoContaCodigo")
            if pc:
                dq["planoConta"] += 1
                code = int(pc)
                if code not in by_plano:
                    cat = plano_catalog.get(code, {})
                    by_plano[code] = {
                        "planoContaCodigo": code,
                        "descricao": cat.get("descricaoGerencial") or row.get("planoConta") or str(code),
                        "categoriaLogosV3": row.get("categoriaLogosV3") or cat.get("categoriaLogosV3"),
                        "valor": Decimal("0"),
                        "quantidade": 0,
                        "porFilial": defaultdict(Decimal),
                    }
                by_plano[code]["valor"] += val
                by_plano[code]["quantidade"] += 1
                by_plano[code]["porFilial"][emp] += val

            if row.get("categoriaLogosV3") and row.get("categoriaLogosV3") != "OUTROS":
                dq["categoriaV3"] += 1
            src = str(row.get("classificationSource") or "")
            if src and src != "OUTROS":
                dq["classificationSource"] += 1
            if raw_row.get("fornecedor") or raw_row.get("fornecedorNome"):
                dq["fornecedor"] += 1

        for prow in pay_rows:
            cc = str(prow.get("centroCustoDescricao") or prow.get("centroCustoCodigo") or "")
            if not cc:
                continue
            val = _dec(prow.get("valor"))
            emp = str(prow.get("empresaCodigo") or "")
            by_centro[cc]["valor"] += val
            by_centro[cc]["count"] += 1
            by_centro[cc]["empresas"].add(emp)
            matrix_centro_filial[cc][emp] += val
            dq["centroCusto"] += 1

        top_planos = []
        for code, info in sorted(by_plano.items(), key=lambda x: -x[1]["valor"])[:20]:
            v = info["valor"]
            top_planos.append(
                {
                    "planoContaCodigo": code,
                    "descricao": info["descricao"],
                    "categoriaLogosV3": info["categoriaLogosV3"],
                    "valorTotal": _q2(v),
                    "quantidade": info["quantidade"],
                    "participacaoPct": _pct(v, total),
                    "pesoRedePct": _pct(v, total),
                    "crescimentoPct": "0.00",
                    "porFilial": {k: _q2(vv) for k, vv in info["porFilial"].items()},
                }
            )

        top_centros = []
        centro_total = sum(c["valor"] for c in by_centro.values()) or Decimal("1")
        for cc, info in sorted(by_centro.items(), key=lambda x: -x[1]["valor"])[:20]:
            v = info["valor"]
            top_centros.append(
                {
                    "centroCusto": cc,
                    "valorTotal": _q2(v),
                    "quantidade": info["count"],
                    "participacaoPct": _pct(v, centro_total),
                    "filiais": sorted(info["empresas"]),
                }
            )

        media_rede = total / len(by_empresa) if by_empresa else Decimal("0")
        best_emp = min(by_empresa.items(), key=lambda x: x[1])[0] if by_empresa else None
        best_val = by_empresa.get(best_emp or "", media_rede) or Decimal("1")

        benchmark = []
        for emp, gasto in sorted(by_empresa.items(), key=lambda x: -x[1]):
            idx_rede = float(gasto / media_rede) if media_rede else 0
            idx_melhor = float(gasto / best_val) if best_val else 0
            benchmark.append(
                {
                    "empresaCodigo": emp,
                    "gasto": _q2(gasto),
                    "indiceBenchmarkRede": round(idx_rede, 4),
                    "indiceBenchmarkMelhor": round(idx_melhor, 4),
                    "classificacaoRede": _benchmark_class(idx_rede),
                    "classificacaoMelhor": _benchmark_class(idx_melhor),
                }
            )

        daily_vals = [float(v) for v in by_day.values()]
        anomalies: list[dict[str, Any]] = []
        if len(daily_vals) >= 2:
            mean = sum(daily_vals) / len(daily_vals)
            var = sum((x - mean) ** 2 for x in daily_vals) / len(daily_vals)
            std = math.sqrt(var) if var > 0 else 1.0
            for day, val in sorted(by_day.items()):
                z = (float(val) - mean) / std if std else 0
                if abs(z) >= 2.5:
                    anomalies.append(
                        {
                            "tipo": "DESVIO_DIARIO",
                            "severidade": _anomaly_severity(z),
                            "periodo": day,
                            "valor": _q2(val),
                            "zScore": round(z, 2),
                            "descricao": f"Desvio {z:.1f}σ vs média período (nota: janela {len(daily_vals)}d; MA 3m pendente A04)",
                        }
                    )

        for row in expenses:
            val = _dec(row.get("valor"))
            if total and val > total / max(len(expenses), 1) * 5:
                anomalies.append(
                    {
                        "tipo": "DESPESA_ANORMAL",
                        "severidade": "HIGH",
                        "descricao": row.get("planoConta"),
                        "valor": row.get("valor"),
                        "empresaCodigo": row.get("empresaCodigo"),
                        "planoContaCodigo": row.get("planoContaCodigo"),
                        "categoriaLogosV3": row.get("categoriaLogosV3"),
                    }
                )

        dre_mapped: dict[str, Decimal] = defaultdict(Decimal)
        dre_coverage = 0
        dre_total = 0
        for row in expenses:
            cat = str(row.get("categoriaLogosV3") or "OUTROS")
            line = V3_TO_DRE.get(cat, "despesasOperacionais")
            dre_mapped[line] += _dec(row.get("valor"))
            dre_total += 1
            pc = row.get("planoContaCodigo") or (row.get("raw") or {}).get("planoContaGerencialCodigo")
            if pc and int(pc) in plano_catalog and plano_catalog[int(pc)].get("apuraDre"):
                dre_coverage += 1

        for prow in pay_rows:
            val = _dec(prow.get("valor"))
            situacao = str(prow.get("situacao") or "").casefold()
            if "receita" in situacao or val < 0:
                dre_mapped["receitaBruta"] += abs(val)

        dre_pct = round(dre_coverage / max(dre_total, 1) * 100, 2)
        dre_lines_detail = {
            line: {"valor": _q2(dre_mapped.get(line, Decimal("0"))), "coberturaPct": dre_pct if line.startswith("despesas") else 0}
            for line in DRE_LINES
        }

        data_quality_score = round(
            sum(
                [
                    dq["planoConta"] / n * 25,
                    dq["centroCusto"] / max(len(pay_rows), 1) * 25 if pay_rows else 0,
                    dq["fornecedor"] / n * 15,
                    dq["categoriaV3"] / n * 20,
                    dq["classificationSource"] / n * 15,
                ]
            ),
            1,
        )

        payload = {
            "accountAnalytics": {
                "topPlanosConta": top_planos,
                "totalValor": _q2(total),
                "totalRegistros": len(expenses),
            },
            "costCenterAnalytics": {
                "topCentrosCusto": top_centros,
                "matrizCentroFilial": {
                    cc: {e: _q2(v) for e, v in emps.items()} for cc, emps in list(matrix_centro_filial.items())[:15]
                },
                "fonte": "TITULO_PAGAR",
            },
            "benchmark": {"filiais": benchmark, "mediaRede": _q2(media_rede), "melhorFilial": best_emp},
            "anomalies": sorted(anomalies, key=lambda x: x.get("severidade", ""), reverse=True)[:30],
            "dreReadiness": {
                "coberturaPct": dre_pct,
                "metaFuturaPct": 85,
                "lacunasPct": round(100 - dre_pct, 2),
                "linhas": dre_lines_detail,
                "bloqueios": [
                    "LANCAMENTO_CONTABIL vazio no período",
                    "CENTRO_CUSTO_REDE HTTP 401",
                    "Receita via TITULO_PAGAR parcial",
                ],
                "plano85": "Integrar receitas TITULO_RECEBER + catálogo contábil completo na A04",
            },
            "dataQuality": {
                "score": data_quality_score,
                "components": {k: round(v / n * 100, 1) if k != "centroCusto" else round(v / max(len(pay_rows), 1) * 100, 1) for k, v in dq.items()},
            },
            "snapshotKey": self.snapshot_key(filters.data_inicial, filters.data_final, empresa_codigo_raw),
        }
        return WebPostoResponse.ok(payload)
