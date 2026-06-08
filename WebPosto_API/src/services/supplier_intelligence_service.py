"""Supplier Intelligence — F01.4-C."""
from __future__ import annotations

import logging
from collections import defaultdict
from decimal import Decimal
from typing import Any

from src.models.response_model import WebPostoResponse
from src.services.corporate_finance_center_service import CorporateFinanceCenterService
from src.services.multiselect_utils import empresa_snapshot_suffix
from src.services.network_financial_overview_service import FinancialOverviewFilters
from src.services.supplier_mdm import (
    build_master_supplier_record,
    canonical_supplier_name,
    compute_supplier_coverage_score,
    extract_supplier_from_expense_description,
    normalize_supplier_key,
)
from src.services.supplier_segmentation import STRATEGIC_HOMOLOGATED, concentration_risk_level, is_strategic_homologated

LOGGER = logging.getLogger(__name__)


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


def _risk_level(share_pct: float, canonical: str = "") -> str | None:
    return concentration_risk_level(share_pct, canonical) or "LOW"


class SupplierIntelligenceService:
    def __init__(self, finance_center: CorporateFinanceCenterService) -> None:
        self._fc = finance_center

    @staticmethod
    def snapshot_key(data_inicial: str, data_final: str, empresa_codigo: str | int | None) -> str:
        suffix = empresa_snapshot_suffix(empresa_codigo)
        return f"finance:suppliers:{data_inicial}:{data_final}:{suffix}"

    async def build(
        self,
        filters: FinancialOverviewFilters,
        empresa_codigo_raw: str | int | None,
    ) -> WebPostoResponse:
        pay_rows, _ = await self._fc._fetch_titulo_pagar_all(filters)
        bank_rows, _ = await self._fc._fetch_movimento_conta_all(filters)
        raw_exp, err = await self._fc._overview._load_filtered_expenses(filters)
        if err is not None:
            return err
        expenses = self._fc._filter_expenses(raw_exp, filters)

        records: list[dict[str, Any]] = []
        for row in pay_rows:
            name = str(row.get("nomeFornecedor") or row.get("fornecedor") or "").strip()
            if not name:
                continue
            val = _dec(row.get("valor"))
            emp = str(row.get("empresaCodigo") or "")
            doc = str(row.get("cpfCnpjFornecedor") or "")
            code = row.get("fornecedorCodigo")
            dt = str(row.get("dataMovimento") or row.get("vencimento") or "")[:10]
            cc = str(row.get("centroCustoDescricao") or row.get("centroCustoCodigo") or "")
            records.append(
                {
                    "source": "TITULO_PAGAR",
                    "supplierName": name,
                    "supplierCode": code,
                    "supplierDocument": doc,
                    "valor": val,
                    "empresaCodigo": emp,
                    "centroCusto": cc,
                    "data": dt,
                    "evidence": f"TITULO_PAGAR:{row.get('tituloPagarCodigo') or row.get('codigo')}",
                }
            )

        for row in expenses:
            raw = row.get("raw") or {}
            desc = str(raw.get("descricaoDocumento") or row.get("planoConta") or "")
            extracted = extract_supplier_from_expense_description(desc)
            if not extracted:
                continue
            records.append(
                {
                    "source": "DESPESAS_REDE_DESC",
                    "supplierName": extracted,
                    "supplierCode": None,
                    "supplierDocument": "",
                    "valor": _dec(row.get("valor")),
                    "empresaCodigo": str(row.get("empresaCodigo") or ""),
                    "centroCusto": "",
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
                    "data": str(row.get("dataMovimento") or "")[:10],
                    "evidence": f"MOVIMENTO_CONTA:{row.get('movimentoContaCodigo') or row.get('codigo')}",
                }
            )

        if not records:
            return WebPostoResponse.ok(self._empty_payload(filters, empresa_codigo_raw, pay_rows, expenses))

        total = sum(r["valor"] for r in records) or Decimal("1")
        by_canonical: dict[str, dict[str, Any]] = {}
        by_raw: dict[str, dict[str, Any]] = {}
        matrix_filial: dict[str, dict[str, Decimal]] = defaultdict(lambda: defaultdict(Decimal))
        matrix_centro: dict[str, dict[str, Decimal]] = defaultdict(lambda: defaultdict(Decimal))
        coverage_scores: list[int] = []

        for rec in records:
            name = rec["supplierName"]
            canonical = canonical_supplier_name(name)
            raw_key = normalize_supplier_key(name)
            val = rec["valor"]
            emp = rec["empresaCodigo"]
            cov = compute_supplier_coverage_score(rec)
            coverage_scores.append(cov)

            if canonical not in by_canonical:
                by_canonical[canonical] = {
                    "supplierCanonicalName": canonical,
                    "valor": Decimal("0"),
                    "count": 0,
                    "filiais": set(),
                    "centros": set(),
                    "aliases": set(),
                    "codes": set(),
                    "documents": set(),
                    "sources": set(),
                    "minValor": val,
                    "maxValor": val,
                    "primeiraData": rec["data"],
                    "ultimaData": rec["data"],
                    "evidence": [],
                }
            agg = by_canonical[canonical]
            agg["valor"] += val
            agg["count"] += 1
            agg["filiais"].add(emp)
            if rec["centroCusto"]:
                agg["centros"].add(rec["centroCusto"])
            agg["aliases"].add(name)
            if rec["supplierCode"]:
                agg["codes"].add(str(rec["supplierCode"]))
            if rec["supplierDocument"]:
                agg["documents"].add(rec["supplierDocument"])
            agg["sources"].add(rec["source"])
            agg["minValor"] = min(agg["minValor"], val)
            agg["maxValor"] = max(agg["maxValor"], val)
            if rec["data"]:
                if not agg["primeiraData"] or rec["data"] < agg["primeiraData"]:
                    agg["primeiraData"] = rec["data"]
                if not agg["ultimaData"] or rec["data"] > agg["ultimaData"]:
                    agg["ultimaData"] = rec["data"]
            agg["evidence"].append(rec["evidence"])
            matrix_filial[canonical][emp] += val
            if rec["centroCusto"]:
                matrix_centro[canonical][rec["centroCusto"]] += val

            if raw_key not in by_raw:
                by_raw[raw_key] = {"name": name, "valor": Decimal("0"), "count": 0}
            by_raw[raw_key]["valor"] += val
            by_raw[raw_key]["count"] += 1

        all_filiais = {r["empresaCodigo"] for r in records if r["empresaCodigo"]}
        n_filiais = len(all_filiais) or 1

        top_suppliers = []
        for canonical, agg in sorted(by_canonical.items(), key=lambda x: -x[1]["valor"])[:20]:
            v = agg["valor"]
            share = float(v / total * 100)
            n_fil = len(agg["filiais"])
            top_suppliers.append(
                {
                    "supplierCanonicalName": canonical,
                    "supplierName": sorted(agg["aliases"])[0],
                    "valorTotal": _q2(v),
                    "participacaoPct": _pct(v, total),
                    "quantidade": agg["count"],
                    "filiaisCount": n_fil,
                    "filiais": sorted(agg["filiais"]),
                    "valorMedio": _q2(v / agg["count"]),
                    "valorMaximo": _q2(agg["maxValor"]),
                    "valorMinimo": _q2(agg["minValor"]),
                    "supplierShare": round(share, 2),
                    "supplierDependencyIndex": round(share / 100, 4),
                    "supplierNetworkPresence": round(n_fil / n_filiais * 100, 1),
                    "sources": sorted(agg["sources"]),
                    "evidenceSample": agg["evidence"][:3],
                }
            )

        leader = top_suppliers[0] if top_suppliers else None
        most_concentrated = max(top_suppliers, key=lambda x: x["supplierShare"], default=None)
        most_present = max(top_suppliers, key=lambda x: x["filiaisCount"], default=None)

        shared = [s for s in top_suppliers if s["filiaisCount"] >= 2]
        exclusive = [s for s in top_suppliers if s["filiaisCount"] == 1]
        network_wide = [s for s in top_suppliers if s["filiaisCount"] >= n_filiais]

        master_dim = []
        for canonical, agg in by_canonical.items():
            primary_name = sorted(agg["aliases"], key=len)[0]
            code = sorted(agg["codes"])[0] if agg["codes"] else None
            doc = sorted(agg["documents"])[0] if agg["documents"] else ""
            cov = round(sum(coverage_scores) / len(coverage_scores), 1) if coverage_scores else 0
            master_dim.append(
                build_master_supplier_record(
                    supplier_code=code,
                    supplier_name=primary_name,
                    supplier_document=doc,
                    empresa_origem=sorted(agg["filiais"])[0] if agg["filiais"] else "",
                    aliases=sorted(agg["aliases"]),
                    primeira_compra=agg["primeiraData"],
                    ultima_compra=agg["ultimaData"],
                    coverage_score=compute_supplier_coverage_score(
                        {
                            "supplierName": primary_name,
                            "supplierDocument": doc,
                            "supplierCode": code,
                            "empresaCodigo": sorted(agg["filiais"])[0] if agg["filiais"] else "",
                        }
                    ),
                )
            )

        risks: list[dict[str, Any]] = []
        for s in top_suppliers:
            share = s["supplierShare"]
            canonical = s["supplierCanonicalName"]
            level = _risk_level(share, canonical)
            if level is None or is_strategic_homologated(canonical):
                continue
            if level in {"HIGH", "CRITICAL", "MEDIUM"}:
                risks.append(
                    {
                        "tipo": "CONCENTRACAO_FORNECEDOR",
                        "severidade": level,
                        "fornecedor": canonical,
                        "supplierShare": share,
                        "valorTotal": s["valorTotal"],
                        "filiais": s["filiais"],
                        "evidence": s["evidenceSample"],
                    }
                )
        if len(by_canonical) == 1 and top_suppliers and not is_strategic_homologated(top_suppliers[0]["supplierCanonicalName"]):
            risks.append(
                {
                    "tipo": "FORNECEDOR_UNICO",
                    "severidade": "HIGH",
                    "fornecedor": top_suppliers[0]["supplierCanonicalName"],
                    "evidence": top_suppliers[0]["evidenceSample"],
                }
            )

        pay_with_supplier = sum(1 for r in pay_rows if r.get("nomeFornecedor") or r.get("fornecedor"))
        pay_total = len(pay_rows) or 1
        supplier_coverage_pct = round(pay_with_supplier / pay_total * 100, 2)
        financial_coverage = round(float(sum(r["valor"] for r in records if r["source"] == "TITULO_PAGAR") / total * 100), 2)

        branch_benchmark = []
        by_emp_val: dict[str, Decimal] = defaultdict(Decimal)
        for rec in records:
            by_emp_val[rec["empresaCodigo"]] += rec["valor"]
        media = sum(by_emp_val.values()) / len(by_emp_val) if by_emp_val else Decimal("1")
        for emp, gasto in sorted(by_emp_val.items(), key=lambda x: -x[1]):
            branch_benchmark.append(
                {
                    "empresaCodigo": emp,
                    "gastoFornecedores": _q2(gasto),
                    "indiceVsMedia": round(float(gasto / media), 4) if media else 0,
                }
            )

        payload = {
            "discovery": {
                "primarySource": "TITULO_PAGAR",
                "secondarySources": ["DESPESAS_REDE_DESC", "MOVIMENTO_CONTA"],
                "blockedSources": ["FORNECEDOR_REDE", "COMPRA_REDE", "PEDIDO_COMPRAS", "NOTA_ENTRADA"],
            },
            "lineage": {
                "supplierCoveragePercent": supplier_coverage_pct,
                "supplierFinancialCoverage": financial_coverage,
                "supplierBranchCoverage": round(len(all_filiais) / max(n_filiais, 1) * 100, 1),
                "supplierHoldingCoverage": supplier_coverage_pct,
                "totalRecords": len(records),
                "tituloPagarRegistros": len(pay_rows),
            },
            "masterSuppliers": {
                "uniqueRaw": len(by_raw),
                "uniqueCanonical": len(by_canonical),
                "averageCoverageScore": round(sum(coverage_scores) / len(coverage_scores), 1) if coverage_scores else 0,
                "suppliers": master_dim[:50],
            },
            "analytics": {
                "topFornecedores": top_suppliers,
                "totalValor": _q2(total),
                "totalRegistros": len(records),
                "leader": leader,
                "mostConcentrated": most_concentrated,
                "mostPresent": most_present,
                "supplierConcentration": most_concentrated["supplierShare"] if most_concentrated else 0,
            },
            "network": {
                "sharedSuppliers": shared[:10],
                "exclusiveSuppliers": exclusive[:10],
                "networkWideSuppliers": network_wide,
                "matrixFornecedorFilial": {
                    k: {e: _q2(v) for e, v in emps.items()} for k, emps in list(matrix_filial.items())[:15]
                },
                "matrixFornecedorCentro": {
                    k: {c: _q2(v) for c, v in cents.items()} for k, cents in list(matrix_centro.items())[:15]
                },
            },
            "risk": {
                "alerts": risks[:20],
                "supplierConcentrationRisk": (
                    0
                    if most_concentrated and is_strategic_homologated(most_concentrated["supplierCanonicalName"])
                    else (most_concentrated["supplierShare"] if most_concentrated else 0)
                ),
                "maxSeverity": risks[0]["severidade"] if risks else "LOW",
                "homologatedSuppliers": sorted(s for s in STRATEGIC_HOMOLOGATED if s in by_canonical),
            },
            "benchmark": {"filiais": branch_benchmark},
            "snapshotKey": self.snapshot_key(filters.data_inicial, filters.data_final, empresa_codigo_raw),
        }
        return WebPostoResponse.ok(payload)

    @staticmethod
    def _empty_payload(
        filters: FinancialOverviewFilters,
        empresa_codigo_raw: str | int | None,
        pay_rows: list,
        expenses: list,
    ) -> dict[str, Any]:
        return {
            "discovery": {"primarySource": "TITULO_PAGAR", "blockedSources": ["FORNECEDOR_REDE"]},
            "lineage": {"supplierCoveragePercent": 0, "totalRecords": 0},
            "masterSuppliers": {"uniqueRaw": 0, "uniqueCanonical": 0, "averageCoverageScore": 0, "suppliers": []},
            "analytics": {"topFornecedores": [], "totalValor": "0.00", "totalRegistros": 0},
            "network": {"sharedSuppliers": [], "exclusiveSuppliers": []},
            "risk": {"alerts": [], "supplierConcentrationRisk": 0},
            "snapshotKey": SupplierIntelligenceService.snapshot_key(
                filters.data_inicial, filters.data_final, empresa_codigo_raw
            ),
            "note": f"TITULO_PAGAR={len(pay_rows)} DESPESAS={len(expenses)} sem fornecedor identificável",
        }
