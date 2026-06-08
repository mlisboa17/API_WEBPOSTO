"""Supplier Segmentation + Corporate Cost Matrix — F01.4-D."""
from __future__ import annotations

import json
import logging
from collections import defaultdict
from decimal import Decimal
from pathlib import Path
from typing import Any

from src.models.response_model import WebPostoResponse
from src.services.corporate_finance_center_service import CorporateFinanceCenterService
from src.services.multiselect_utils import empresa_snapshot_suffix
from src.services.network_financial_overview_service import FinancialOverviewFilters
from src.services.supplier_mdm import (
    canonical_supplier_name,
    compute_supplier_coverage_score,
    extract_supplier_from_expense_description,
    normalize_supplier_key,
)
from src.services.supplier_segmentation import (
    classify_supplier_segment,
    concentration_risk_level,
    detect_procurement_opportunities,
    is_strategic_homologated,
    procurement_readiness_score,
    strategic_supplier_score,
    supplier_confidence_score,
)

LOGGER = logging.getLogger(__name__)
MAPPING_PATH = Path(__file__).resolve().parents[2] / "config" / "account_category_mapping.json"


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


class SupplierSegmentationService:
    def __init__(self, finance_center: CorporateFinanceCenterService) -> None:
        self._fc = finance_center

    @staticmethod
    def snapshot_key(data_inicial: str, data_final: str, empresa_codigo: str | int | None) -> str:
        suffix = empresa_snapshot_suffix(empresa_codigo)
        return f"finance:supplier-segmentation:{data_inicial}:{data_final}:{suffix}"

    async def _collect_records(
        self,
        filters: FinancialOverviewFilters,
    ) -> tuple[list[dict[str, Any]], list, list, list]:
        pay_rows, _ = await self._fc._fetch_titulo_pagar_all(filters)
        bank_rows, _ = await self._fc._fetch_movimento_conta_all(filters)
        raw_exp, err = await self._fc._overview._load_filtered_expenses(filters)
        if err is not None:
            return [], pay_rows, bank_rows, []
        expenses = self._fc._filter_expenses(raw_exp, filters)
        plano_catalog = _load_plano_catalog()
        records: list[dict[str, Any]] = []

        for row in pay_rows:
            name = str(row.get("nomeFornecedor") or row.get("fornecedor") or "").strip()
            if not name:
                continue
            pc_code = row.get("planoContaGerencialCodigo")
            pc_desc = str(row.get("planoContaGerencialDescricao") or "")
            cat_v3 = ""
            if pc_code and int(pc_code) in plano_catalog:
                cat_v3 = str(plano_catalog[int(pc_code)].get("categoriaLogosV3") or "")
                if not pc_desc:
                    pc_desc = str(plano_catalog[int(pc_code)].get("descricaoGerencial") or "")
            cc = str(row.get("centroCustoDescricao") or row.get("centroCustoCodigo") or "")
            records.append(
                {
                    "source": "TITULO_PAGAR",
                    "supplierName": name,
                    "supplierCode": row.get("fornecedorCodigo"),
                    "supplierDocument": str(row.get("cpfCnpjFornecedor") or ""),
                    "valor": _dec(row.get("valor")),
                    "empresaCodigo": str(row.get("empresaCodigo") or ""),
                    "centroCusto": cc,
                    "planoConta": pc_desc,
                    "planoContaCodigo": pc_code,
                    "categoriaLogosV3": cat_v3,
                    "descricao": str(row.get("descricao") or ""),
                    "data": str(row.get("dataMovimento") or row.get("vencimento") or "")[:10],
                    "evidence": f"TITULO_PAGAR:{row.get('tituloPagarCodigo') or row.get('codigo')}",
                }
            )

        for row in expenses:
            raw = row.get("raw") or {}
            desc = str(raw.get("descricaoDocumento") or row.get("planoConta") or "")
            extracted = extract_supplier_from_expense_description(desc)
            if not extracted:
                continue
            pc_code = raw.get("planoContaGerencialCodigo") or row.get("planoContaCodigo")
            pc_desc = str(row.get("planoConta") or "")
            cat_v3 = str(row.get("categoriaLogosV3") or "")
            if pc_code and int(pc_code) in plano_catalog and not cat_v3:
                cat_v3 = str(plano_catalog[int(pc_code)].get("categoriaLogosV3") or "")
            records.append(
                {
                    "source": "DESPESAS_REDE_DESC",
                    "supplierName": extracted,
                    "supplierCode": None,
                    "supplierDocument": "",
                    "valor": _dec(row.get("valor")),
                    "empresaCodigo": str(row.get("empresaCodigo") or ""),
                    "centroCusto": str(row.get("centroCusto") or ""),
                    "planoConta": pc_desc,
                    "planoContaCodigo": pc_code,
                    "categoriaLogosV3": cat_v3,
                    "descricao": desc,
                    "data": str(row.get("data") or "")[:10],
                    "evidence": f"DESPESAS_REDE:{desc[:80]}",
                }
            )

        for row in bank_rows:
            if str(row.get("tipoPessoa") or "").casefold() not in {"f", "fornecedor", "fornecedores"}:
                continue
            name = str(row.get("descricao") or "").strip()
            if not name:
                continue
            records.append(
                {
                    "source": "MOVIMENTO_CONTA",
                    "supplierName": name,
                    "supplierCode": row.get("codigoPessoa"),
                    "supplierDocument": "",
                    "valor": abs(_dec(row.get("valor"))),
                    "empresaCodigo": str(row.get("empresaCodigo") or ""),
                    "centroCusto": str(row.get("centroCustoCodigo") or ""),
                    "planoConta": str(row.get("planoContaGerencialDescricao") or ""),
                    "planoContaCodigo": row.get("planoContaGerencialCodigo"),
                    "categoriaLogosV3": "",
                    "descricao": name,
                    "data": str(row.get("dataMovimento") or "")[:10],
                    "evidence": f"MOVIMENTO_CONTA:{row.get('movimentoContaCodigo') or row.get('codigo')}",
                }
            )

        return records, pay_rows, bank_rows, expenses

    async def build(
        self,
        filters: FinancialOverviewFilters,
        empresa_codigo_raw: str | int | None,
    ) -> WebPostoResponse:
        records, pay_rows, _, _ = await self._collect_records(filters)
        if not records:
            return WebPostoResponse.ok({"segmentationV2": {}, "snapshotKey": self.snapshot_key(filters.data_inicial, filters.data_final, empresa_codigo_raw)})

        total = sum(r["valor"] for r in records) or Decimal("1")
        all_filiais = {r["empresaCodigo"] for r in records if r["empresaCodigo"]}
        n_filiais = len(all_filiais) or 1

        by_canonical: dict[str, dict[str, Any]] = {}
        cost_matrix: list[dict[str, Any]] = []
        confidence_scores: list[int] = []

        for rec in records:
            canonical = canonical_supplier_name(rec["supplierName"])
            seg = classify_supplier_segment(
                plano_conta=rec.get("planoConta") or "",
                plano_categoria_v3=rec.get("categoriaLogosV3") or "",
                centro_custo=rec.get("centroCusto") or "",
                supplier_name=rec["supplierName"],
                descricao=rec.get("descricao") or "",
            )
            if is_strategic_homologated(canonical):
                seg["supplierStrategic"] = True
                seg["supplierCategory"] = "ESTRATEGICOS"
                seg["supplierSubcategory"] = "Combustiveis"

            conf = supplier_confidence_score(
                fornecedor_identificado=bool(rec.get("supplierName")),
                plano_conta=bool(rec.get("planoConta") or rec.get("planoContaCodigo")),
                centro_custo=bool(rec.get("centroCusto")),
                movimento_financeiro=rec.get("source") in {"TITULO_PAGAR", "MOVIMENTO_CONTA"},
            )
            confidence_scores.append(conf["supplierConfidenceScore"])

            if canonical not in by_canonical:
                by_canonical[canonical] = {
                    "valor": Decimal("0"),
                    "count": 0,
                    "filiais": set(),
                    "sources": set(),
                    "segment": seg,
                    "aliases": set(),
                    "centros": defaultdict(Decimal),
                    "planos": defaultdict(Decimal),
                    "evidence": [],
                }
            agg = by_canonical[canonical]
            agg["valor"] += rec["valor"]
            agg["count"] += 1
            agg["filiais"].add(rec["empresaCodigo"])
            agg["sources"].add(rec["source"])
            agg["aliases"].add(rec["supplierName"])
            agg["evidence"].append(rec["evidence"])
            if rec.get("centroCusto"):
                agg["centros"][rec["centroCusto"]] += rec["valor"]
            if rec.get("planoConta"):
                agg["planos"][rec["planoConta"]] += rec["valor"]

            cost_matrix.append(
                {
                    "fornecedor": canonical,
                    "planoConta": rec.get("planoConta") or "—",
                    "centroCusto": rec.get("centroCusto") or "—",
                    "filial": rec.get("empresaCodigo") or "—",
                    "valor": _q2(rec["valor"]),
                    "categoria": seg["supplierCategory"],
                    "subcategoria": seg["supplierSubcategory"],
                    "evidence": rec["evidence"],
                }
            )

        strategic_suppliers = []
        for canonical, agg in sorted(by_canonical.items(), key=lambda x: -x[1]["valor"]):
            v = agg["valor"]
            share = float(v / total * 100)
            seg = agg["segment"]
            score = strategic_supplier_score(
                valor=v,
                total=total,
                filiais_count=len(agg["filiais"]),
                n_filiais=n_filiais,
                transaction_count=agg["count"],
                supplier_strategic=seg.get("supplierStrategic", False),
            )
            readiness = procurement_readiness_score(agg["sources"], has_catalog=False)
            strategic_suppliers.append(
                {
                    "supplierCanonicalName": canonical,
                    "supplierCategory": seg["supplierCategory"],
                    "supplierSubcategory": seg["supplierSubcategory"],
                    "supplierStrategic": seg["supplierStrategic"],
                    "strategicHomologated": is_strategic_homologated(canonical),
                    "valorTotal": _q2(v),
                    "participacaoPct": _pct(v, total),
                    "filiaisCount": len(agg["filiais"]),
                    "readinessScore": readiness,
                    **score,
                    "evidenceSample": agg["evidence"][:3],
                }
            )

        top_strategic = [s for s in strategic_suppliers if s["supplierStrategic"]][:10]

        by_category: dict[str, dict[str, Any]] = defaultdict(
            lambda: {"valor": Decimal("0"), "count": 0, "suppliers": set(), "filiais": set(), "lancamentos": 0}
        )
        for canonical, agg in by_canonical.items():
            cat = agg["segment"]["supplierCategory"]
            by_category[cat]["valor"] += agg["valor"]
            by_category[cat]["count"] += 1
            by_category[cat]["suppliers"].add(canonical)
            by_category[cat]["filiais"].update(agg["filiais"])
            by_category[cat]["lancamentos"] += agg["count"]

        category_analytics = []
        for cat, info in sorted(by_category.items(), key=lambda x: -x[1]["valor"]):
            category_analytics.append(
                {
                    "supplierCategory": cat,
                    "valorTotal": _q2(info["valor"]),
                    "participacaoPct": _pct(info["valor"], total),
                    "fornecedoresCount": len(info["suppliers"]),
                    "filiaisCount": len(info["filiais"]),
                    "lancamentosCount": info["lancamentos"],
                }
            )

        strategic_total = sum(
            by_canonical[c]["valor"] for c in by_canonical if by_canonical[c]["segment"].get("supplierStrategic")
        )
        non_strategic_total = total - strategic_total
        strategic_index = round(float(strategic_total / total * 100), 2) if total else 0

        non_strategic_share = max(
            (
                float(by_canonical[c]["valor"] / total * 100)
                for c in by_canonical
                if not is_strategic_homologated(c) and not by_canonical[c]["segment"].get("supplierStrategic")
            ),
            default=0,
        )

        top_plano = max(
            ((p, v) for agg in by_canonical.values() for p, v in agg["planos"].items()),
            key=lambda x: x[1],
            default=("—", Decimal("0")),
        )
        top_centro = max(
            ((c, v) for agg in by_canonical.values() for c, v in agg["centros"].items()),
            key=lambda x: x[1],
            default=("—", Decimal("0")),
        )

        opportunities = detect_procurement_opportunities(by_canonical, total)
        economia_potencial = sum(_dec(o.get("economiaPotencialPeriodo")) for o in opportunities if o.get("economiaPotencialPeriodo"))

        risks = []
        for s in strategic_suppliers[:20]:
            share = float(s["participacaoPct"])
            level = concentration_risk_level(share, s["supplierCanonicalName"])
            if level and level in {"HIGH", "CRITICAL", "MEDIUM"}:
                risks.append(
                    {
                        "tipo": "CONCENTRACAO_FORNECEDOR",
                        "severidade": level,
                        "fornecedor": s["supplierCanonicalName"],
                        "supplierShare": share,
                        "evidence": s["evidenceSample"],
                    }
                )

        vibra = next((s for s in strategic_suppliers if s["supplierCanonicalName"] == "VIBRA"), None)
        max_cat = max(category_analytics, key=lambda x: float(x["participacaoPct"]), default={})
        max_dep_cat = max(category_analytics, key=lambda x: x["fornecedoresCount"], default={})

        avg_confidence = round(sum(confidence_scores) / len(confidence_scores), 1) if confidence_scores else 0
        pay_cov = round(sum(1 for r in pay_rows if r.get("nomeFornecedor")) / max(len(pay_rows), 1) * 100, 2)

        payload = {
            "segmentationV2": {
                "taxonomy": {
                    "categories": ["ESTRATEGICOS", "OPERACIONAL", "FINANCEIRO", "RH", "TRIBUTARIO", "OUTROS"],
                    "priority": ["PLANO_CONTA", "CENTRO_CUSTO", "FORNECEDOR", "DESCRICAO"],
                },
                "suppliers": strategic_suppliers[:50],
                "topStrategic": top_strategic,
                "categoryAnalytics": category_analytics,
                "corporateCostMatrix": sorted(cost_matrix, key=lambda x: -float(x["valor"]))[:100],
                "procurementOpportunities": opportunities,
                "procurementReadiness": [
                    {
                        "fornecedor": s["supplierCanonicalName"],
                        "readinessScore": s["readinessScore"],
                        "sources": list(by_canonical[s["supplierCanonicalName"]]["sources"]),
                    }
                    for s in strategic_suppliers[:30]
                ],
                "kpis": {
                    "strategicSupplierIndex": strategic_index,
                    "supplierDependencyIndex": round(non_strategic_share, 2),
                    "corporateCostIndex": round(100 - non_strategic_share, 2),
                    "supplierCoverageIndex": pay_cov,
                    "averageSupplierConfidenceScore": avg_confidence,
                    "economiaPotencialPeriodo": _q2(economia_potencial),
                    "economiaPotencialAnualEstimada": _q2(economia_potencial * 52),
                },
                "highlights": {
                    "vibraStrategicScore": vibra.get("strategicSupplierScore") if vibra else None,
                    "vibraHomologated": True,
                    "vibraConcentrationAlertSuppressed": True,
                    "maiorCategoriaConsumo": max_cat.get("supplierCategory"),
                    "maiorCategoriaDependencia": max_dep_cat.get("supplierCategory"),
                    "maiorPlanoConta": top_plano[0],
                    "maiorCentroCusto": top_centro[0],
                },
                "risk": {
                    "alerts": risks[:20],
                    "homologatedMonitoring": [
                        {
                            "fornecedor": "VIBRA",
                            "monitorar": ["prazo", "volume", "exposicao", "crescimento", "condicoes"],
                            "alertaConcentracaoSuprimido": True,
                        }
                    ]
                    if vibra
                    else [],
                },
            },
            "snapshotKey": self.snapshot_key(filters.data_inicial, filters.data_final, empresa_codigo_raw),
        }
        return WebPostoResponse.ok(payload)
