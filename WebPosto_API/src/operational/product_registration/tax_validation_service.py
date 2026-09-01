"""Verificação tributária por consenso — somente leitura, sem inventar valores."""

from __future__ import annotations

import re
from collections import Counter
from decimal import Decimal
from typing import Any

from src.operational.price_update.company_service import list_empresas
from src.operational.price_update.cost_center_resolver import (
    KNOWN_118508_CONVENIENCIA,
    resolve_for_empty,
)
from src.operational.product_registration.ean_service import (
    find_ean_duplicates,
    validate_ean_strict,
)
from src.operational.product_registration.reference_finder import find_tax_reference_products


Classification = str  # CONSENSUS | MAJORITY | CONFLICT | MISSING | NOT_APPLICABLE | UNKNOWN


def _norm_ncm(v: Any) -> str | None:
    digits = re.sub(r"\D", "", str(v or ""))
    if len(digits) != 8:
        return None
    return digits


def _norm_cest(v: Any) -> str | None:
    digits = re.sub(r"\D", "", str(v or ""))
    if not digits:
        return None
    if len(digits) != 7:
        return None
    return digits


def classify_field(values: list[Any]) -> dict[str, Any]:
    cleaned = []
    for v in values:
        if v is None or v == "" or v == {}:
            continue
        if isinstance(v, dict):
            # chave estável
            cleaned.append(tuple(sorted((str(k), str(val)) for k, val in v.items() if val not in (None, ""))))
        else:
            cleaned.append(str(v))
    if not cleaned:
        return {"classification": "MISSING", "value": None, "counts": {}}
    counts = Counter(cleaned)
    top, n = counts.most_common(1)[0]
    total = len(cleaned)
    if len(counts) == 1:
        value = _revive(top)
        return {"classification": "CONSENSUS", "value": value, "counts": dict(counts)}
    if n > total / 2:
        return {
            "classification": "MAJORITY",
            "value": _revive(top),
            "counts": {str(k): v for k, v in counts.items()},
        }
    return {
        "classification": "CONFLICT",
        "value": None,
        "counts": {str(k): v for k, v in counts.items()},
    }


def _revive(key: Any) -> Any:
    if isinstance(key, tuple):
        return {k: v for k, v in key}
    return key


TAX_FIELDS = (
    "codigoNcm",
    "codigoCest",
    "tributoIcms",
    "tributoPisCofins",
    "cdCfopEntrada",
    "cdCfopSaida",
    "naturezaReceitaCodigo",
    "tributacaoMonofasica",
    "tributoCbsIbs",
)


def build_field_matrix(references: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    matrix: dict[str, dict[str, Any]] = {}
    for field in TAX_FIELDS:
        values = []
        for r in references:
            if field == "codigoNcm":
                values.append(r.get("ncm") or r.get("codigoNcm"))
            elif field == "codigoCest":
                values.append(r.get("cest") or r.get("codigoCest"))
            else:
                values.append(r.get(field))
        matrix[field] = classify_field(values)
    return matrix


def validate_ncm_cest(ncm: str | None, cest: str | None, references: list[dict[str, Any]]) -> list[str]:
    gates: list[str] = []
    n = _norm_ncm(ncm)
    if not n:
        gates.append("BLOCKED_NCM_INVALID")
    c = _norm_cest(cest) if cest not in (None, "", "0") else None
    if cest not in (None, "", "0") and not c:
        gates.append("BLOCKED_CEST_INVALID")
    if n and references:
        cest_set = {
            _norm_cest(r.get("cest") or r.get("codigoCest"))
            for r in references
            if _norm_ncm(r.get("ncm") or r.get("codigoNcm")) == n
        }
        cest_set.discard(None)
        if c and cest_set and c not in cest_set and len(cest_set) >= 1:
            # incompatível com modelos observados
            gates.append("BLOCKED_NCM_CEST_CONFLICT")
        if not c and len(cest_set) > 1:
            gates.append("BLOCKED_NCM_CEST_CONFLICT")
    return gates


def risk_level(*, conflicts: list[str], missing: list[str], warnings: list[str]) -> str:
    if conflicts or any(g.startswith("BLOCKED_") for g in missing):
        return "HIGH"
    if missing or warnings:
        return "MEDIUM"
    return "LOW"


def build_proposed_body(
    *,
    input_data: dict[str, Any],
    matrix: dict[str, dict[str, Any]],
    centro: dict[str, Any],
    ean: str | None,
) -> tuple[dict[str, Any] | None, list[str]]:
    """Monta preview IntegracaoProdutoCadastro; não inventa CONFLICT/MISSING."""
    missing: list[str] = []
    body: dict[str, Any] = {
        "descricao": input_data.get("descricao"),
        "descricaoResumida": input_data.get("descricaoResumida") or input_data.get("descricao"),
        "tipoProduto": input_data.get("tipoProduto") or "P",
        "unidadeCompra": input_data.get("unidadeCompra") or "UN",
        "unidadeVenda": input_data.get("unidadeVenda") or "UN",
        "iat": input_data.get("iat") or "A",
        "ippt": input_data.get("ippt") or "T",
        "precoCusto": str(input_data.get("precoCusto") or "0"),
        "precoCompra": str(input_data.get("precoCompra") or "0"),
        "precoVenda": str(input_data.get("precoVenda") or "0"),
        "codigoNcm": _norm_ncm(input_data.get("codigoNcm")) or "",
        "produtoVendeFracionado": bool(input_data.get("produtoVendeFracionado", False)),
        "utilizaBalanca": bool(input_data.get("utilizaBalanca", False)),
        "permiteVendaEstoqueNegativo": bool(input_data.get("permiteVendaEstoqueNegativo", False)),
        "ativo": bool(input_data.get("ativo", False)),
        "venderSemCodigoBarras": bool(input_data.get("venderSemCodigoBarras", False)),
    }
    if ean:
        body["codigoBarras"] = ean
        body["produtoCodigoBarra"] = [{"codigoBarra": ean, "principal": True}]

    grupo = input_data.get("grupoCodigo")
    if not grupo:
        missing.append("grupoCodigo")
    else:
        body["grupoCodigo"] = int(grupo)

    if not centro.get("codigo"):
        missing.append("centroCustoCodigo")
    else:
        body["centroCustoCodigo"] = int(centro["codigo"])

    for field in (
        "codigoCest",
        "tributoIcms",
        "tributoPisCofins",
        "cdCfopEntrada",
        "cdCfopSaida",
        "naturezaReceitaCodigo",
        "tributacaoMonofasica",
        "tributoCbsIbs",
    ):
        cell = matrix.get(field) or {}
        cls = cell.get("classification")
        if cls == "CONSENSUS" and cell.get("value") not in (None, ""):
            body[field] = cell["value"]
        elif field in {"tributoIcms", "tributoPisCofins", "cdCfopEntrada", "cdCfopSaida", "naturezaReceitaCodigo"}:
            # obrigatórios fiscais para preview seguro
            if cls in {"CONFLICT", "MISSING", "MAJORITY", "UNKNOWN"}:
                missing.append(field)
        elif field == "codigoCest" and cls == "CONFLICT":
            missing.append(field)

    required = [
        "descricao",
        "descricaoResumida",
        "tipoProduto",
        "unidadeCompra",
        "unidadeVenda",
        "iat",
        "ippt",
        "precoCusto",
        "precoCompra",
        "codigoNcm",
        "grupoCodigo",
        "centroCustoCodigo",
        "tributoIcms",
        "tributoPisCofins",
    ]
    for k in required:
        if body.get(k) in (None, "", [], {}):
            if k not in missing:
                missing.append(k)

    if missing:
        return body, missing
    return body, []


class TaxValidationService:
    """Orquestra tax-check read-only. Nunca chama POST/PUT de produto."""

    def run(
        self,
        *,
        empresa_codigo: int,
        input_data: dict[str, Any],
        catalog: list[dict[str, Any]],
        products_by_empresa: dict[int, list[dict[str, Any]]] | None = None,
        centros_custo: list[dict[str, Any]] | None = None,
        empresa_meta: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        write_performed = False
        gates: list[str] = []
        warnings: list[str] = []
        conflicts: list[str] = []
        required_missing: list[str] = []

        emp = empresa_meta or {"empresaCodigo": empresa_codigo}
        if not emp.get("label"):
            nome = emp.get("nomeFantasia") or emp.get("nome") or "SEM NOME"
            emp = {
                **emp,
                "empresaCodigo": empresa_codigo,
                "nomeFantasia": emp.get("nomeFantasia") or nome,
                "label": f"{empresa_codigo} - {nome}",
            }

        # regime
        tipo_imposto = emp.get("tipoImposto") or emp.get("regime") or emp.get("tipo_imposto")
        if not tipo_imposto:
            warnings.append("COMPANY_TAX_REGIME_UNKNOWN")
            # não bloqueia sozinho se modelos internos forem conclusivos

        ean_raw = input_data.get("ean") or input_data.get("codigoBarras")
        ean_check = validate_ean_strict(ean_raw) if ean_raw else {
            "ok": False,
            "ean": None,
            "gate": "BLOCKED_INVALID_EAN",
            "issues": ["EAN_REQUIRED"],
        }
        if not ean_check["ok"]:
            gates.append(ean_check["gate"])

        duplicates = []
        if ean_check.get("ean"):
            duplicates = find_ean_duplicates(
                ean_check["ean"],
                products_by_empresa=products_by_empresa
                or {empresa_codigo: catalog},
            )
            if duplicates:
                gates.append("BLOCKED_EAN_ALREADY_EXISTS")
                ean_check = {
                    **ean_check,
                    "ok": False,
                    "gate": "BLOCKED_EAN_ALREADY_EXISTS",
                    "duplicates": duplicates,
                }

        ncm = _norm_ncm(input_data.get("codigoNcm"))
        cest = _norm_cest(input_data.get("codigoCest")) if input_data.get("codigoCest") else None
        if not ncm:
            gates.append("BLOCKED_NCM_INVALID")

        references = find_tax_reference_products(
            catalog,
            empresa_codigo=empresa_codigo,
            ncm=ncm,
            cest=cest,
            grupo_codigo=input_data.get("grupoCodigo"),
            descricao=input_data.get("descricao"),
            unidade_venda=input_data.get("unidadeVenda") or "UN",
        )
        if not references:
            gates.append("BLOCKED_NO_REFERENCE_PRODUCT")

        ncm_cest_gates = validate_ncm_cest(ncm, cest or input_data.get("codigoCest"), references)
        gates.extend(ncm_cest_gates)

        matrix = build_field_matrix(references)
        for field, cell in matrix.items():
            cls = cell.get("classification")
            if cls == "CONFLICT":
                conflicts.append(field)
                gates.append("BLOCKED_TAX_CONFLICT")
            if cls in {"MISSING", "UNKNOWN"} and field in {
                "tributoIcms",
                "tributoPisCofins",
                "cdCfopEntrada",
                "cdCfopSaida",
                "naturezaReceitaCodigo",
            }:
                required_missing.append(field)
                gates.append("BLOCKED_TAX_FIELDS_MISSING")
            if cls == "MAJORITY" and field in {
                "tributoIcms",
                "tributoPisCofins",
                "cdCfopEntrada",
                "cdCfopSaida",
                "naturezaReceitaCodigo",
                "codigoCest",
            }:
                warnings.append(f"MAJORITY_{field}")
                gates.append("BLOCKED_TAX_CONFLICT")

        if not input_data.get("grupoCodigo"):
            gates.append("BLOCKED_GROUP_NOT_RESOLVED")

        cc = resolve_for_empty(centros_custo or [], empresa_codigo=empresa_codigo)
        centro = {
            "codigo": cc.codigo,
            "label": cc.label or "CONVENIENCIA",
            "gate": cc.gate,
            "reason": cc.reason,
            "known118508": KNOWN_118508_CONVENIENCIA if empresa_codigo == 118508 else None,
        }
        if cc.codigo is None:
            gates.append("BLOCKED_CENTER_COST_NOT_RESOLVED")

        proposed, body_missing = build_proposed_body(
            input_data=input_data,
            matrix=matrix,
            centro=centro,
            ean=ean_check.get("ean"),
        )
        required_missing = sorted(set(required_missing + body_missing))
        if body_missing:
            gates.append("BLOCKED_INCOMPLETE_PRODUCT_BODY")

        unique_gates = sorted(set(gates))
        blocked = bool(unique_gates)
        status = "BLOCKED" if blocked else "TAX_CHECK_READY"
        product_gate = (
            "BLOCKED" if blocked else "READY_FOR_HUMAN_REGISTRATION_APPROVAL"
        )
        risk = risk_level(
            conflicts=conflicts,
            missing=required_missing + unique_gates,
            warnings=warnings,
        )

        return {
            "status": status,
            "empresa": emp,
            "eanCheck": ean_check,
            "input": input_data,
            "referenceProducts": references,
            "fieldMatrix": matrix,
            "requiredMissing": required_missing,
            "conflicts": conflicts,
            "warnings": warnings,
            "gates": unique_gates,
            "centroCusto": centro,
            "proposedBody": proposed,
            "bodyReconstructable": not bool(body_missing) and not blocked,
            "risk": risk,
            "productGate": product_gate,
            "writePerformed": write_performed,
            "mode": "READ_ONLY_TAX_CHECK",
        }


def resolve_empresa_meta(empresa_codigo: int) -> dict[str, Any]:
    for e in list_empresas():
        if int(e.get("empresaCodigo") or 0) == int(empresa_codigo):
            nome = e.get("nomeFantasia") or e.get("nome") or "SEM NOME"
            return {
                **e,
                "label": f"{e['empresaCodigo']} - {nome}",
            }
    return {
        "empresaCodigo": empresa_codigo,
        "nomeFantasia": None,
        "label": f"{empresa_codigo} - (nome indisponível)",
    }
