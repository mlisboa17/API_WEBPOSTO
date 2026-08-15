"""Monta a ONDA FINAL sem reconstruir as ondas 1-4 e sem enviar POST.

Classifica os 72 bloqueados restantes, marca SAME_PRODUCT e JA_NO_CATALOGO no
checkpoint, e anexa perfis onda=5 somente para os candidatos liberados.
"""

from __future__ import annotations

import hashlib
import json
import sys
from collections import defaultdict
from dataclasses import replace
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import httpx

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src.operational.product_registration.company_credentials import (  # noqa: E402
    HttpProductReader,
    company_guard,
    resolve_credential,
)
from src.operational.product_registration.dfe_cost_resolver import (  # noqa: E402
    build_authorized_index,
    cost_from_index,
)
from src.operational.product_registration.duplicate_checker import (  # noqa: E402
    find_description_duplicates,
    looks_fabricated_gtin,
)
from src.operational.product_registration.ean_service import (  # noqa: E402
    gtin_prefix_length_conflict,
)
from src.operational.product_registration.entry_evidence_index import (  # noqa: E402
    build_ncm_cest_evidence,
    item_entry_evidence,
    summarize_evidence,
)
from src.operational.product_registration.final_wave import (  # noqa: E402
    LEGITIMATE_VARIANT,
    SAME_PRODUCT,
    UNRESOLVED_DUPLICATE,
    classify_final_duplicate,
    majority_treatment,
    pick_icms_row,
)
from src.operational.product_registration.fiscal_profiles import (  # noqa: E402
    CONFIDENCE_VERY_LOW,
    LEVEL_D,
    LEVEL_SPECIAL,
    RISK_ASSUMED,
    TREATMENT_SUBSTITUTED,
    TREATMENT_TAXED,
    audit_trail,
    build_profile_id,
    special_category,
)
from src.operational.product_registration.fiscal_resolver import (  # noqa: E402
    ST_PROVEN,
    classify_entry,
)
from src.operational.product_registration.fiscal_sheet_loader import load_sheet  # noqa: E402
from src.operational.product_registration.product_family import commercial_family  # noqa: E402
from src.operational.product_registration.tax_table_matcher import (  # noqa: E402
    MATCH_UNIQUE,
    basis_from_row,
    load_icms_table,
    load_pis_cofins_table,
    match_icms,
    match_icms_by_entry_rate,
    match_pis_cofins,
)

BASE_URL = "https://web.qualityautomacao.com.br"
COMPANY_CODE = 118508
PROFILE = "WEBPOSTO_CONVENIENCIA_24_HORAS_KEY"
GRUPO_CODIGO = 55446
COST_CENTER = 24886
REGISTRATION_DIR = ROOT / "data" / "product_registration"
SHEET = REGISTRATION_DIR / "FISCAL_PRODUTOS_A_CADASTRAR_118508.xlsx"
TAX_INPUT = REGISTRATION_DIR / "tax_tables_input"
PROFILES = REGISTRATION_DIR / "fiscal_profiles_118508.json"
CHECKPOINT = REGISTRATION_DIR / "execution" / "checkpoint_118508.json"
CLASSIFICATION = REGISTRATION_DIR / "onda_final_classification_118508.json"
PENDING_PRICE = REGISTRATION_DIR / "pending_price_review_118508.json"

PERMANENT_REASONS = {
    "GTIN_INVALIDO",
    "GTIN_COM_APARENCIA_DE_INVENTADO",
    "GTIN_INCOERENTE_COM_O_PREFIXO",
    "GTIN_TRUNCADO",
    "EXCLUSAO_PERMANENTE",
}
PERMANENT_EANS = {"7891000376928", "7891962076317", "789607405141"}
REMAINING_REASONS = {
    "POSSIVEL_DUPLICIDADE",
    "TABELA_ICMS_SEM_CORRESPONDENCIA_UNICA",
    "CONVERSAO_EMBALAGEM_INDETERMINAVEL",
    "TRATAMENTOS_CONCORRENTES_NA_EVIDENCIA",
    "FAMILIA_COMERCIAL_DIVERGENTE",
    "CONFLITO_NCM_CEST",
    "CUSTO_ACIMA_DA_VENDA",
    "SEM_CEST_E_SEM_NOTA_PROPRIA",
    "JA_NO_CATALOGO",
}

PIS_COFINS_BASIS = {
    "percentualCofinsEntrada": 3.0,
    "percentualBaseCalculoCofinsEntrada": 100,
    "cstCofinsEntrada": "50",
    "percentualCofinsSaida": 3.0,
    "percentualBaseCalculoCofinsSaida": 100,
    "cstCofinsSaida": "01",
    "percentualPisEntrada": 0.65,
    "percentualBaseCalculoPisEntrada": 100,
    "cstPisEntrada": "50",
    "percentualPisSaida": 0.65,
    "percentualBaseCalculoPisSaida": 100,
    "cstPisSaida": "01",
}
CFOP_SUBSTITUTED = ("1.102", "5.405")
CFOP_TAXED = ("1.102", "5.102")


def paginate(client: httpx.Client, path: str, key: str) -> list[dict[str, Any]]:
    collected: list[dict[str, Any]] = []
    cursor = 0
    seen: set[int] = set()
    for _ in range(400):
        params: dict[str, Any] = {"CHAVE": key, "tamanhoPagina": 200}
        if cursor:
            params["ultimoCodigo"] = cursor
        response = client.get(f"{BASE_URL}{path}", params=params)
        response.raise_for_status()
        payload = response.json()
        batch = payload.get("resultados") or []
        collected.extend(batch)
        nxt = int(payload.get("ultimoCodigo") or 0)
        if not batch or not nxt or nxt == cursor or nxt in seen:
            break
        seen.add(nxt)
        cursor = nxt
    return collected


def barcodes(product: dict[str, Any]) -> set[str]:
    values = {
        str((e.get("codigoBarra") if isinstance(e, dict) else e) or "").strip()
        for e in product.get("produtoCodigoBarra") or []
    }
    external = product.get("produtoCodigoExterno")
    if external:
        values.add(str(external).strip())
    return {v for v in values if v}


def body_hash(body: dict[str, Any]) -> str:
    payload = json.dumps(body, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def build_body(row, *, ncm: str, cest: str | None, cost: float, icms: dict[str, Any], cfop: tuple[str, str]) -> dict[str, Any]:
    body = {
        "descricao": row.descricao,
        "descricaoResumida": row.descricao[:32].strip(),
        "tipoProduto": "P",
        "grupoCodigo": GRUPO_CODIGO,
        "codigoExterno": row.ean,
        "unidadeCompra": "UN",
        "unidadeVenda": "UN",
        "iat": "A",
        "ippt": "T",
        "precoCompra": cost,
        "precoCusto": cost,
        "precoVenda": row.preco_venda,
        "centroCustoCodigo": COST_CENTER,
        "codigoBarras": row.ean,
        "codigoNcm": ncm,
        "ativo": True,
        "permiteVendaEstoqueNegativo": False,
        "produtoVendeFracionado": False,
        "utilizaCodigoBarras": True,
        "utilizaBalanca": False,
        "cdCfopEntrada": cfop[0],
        "cdCfopSaida": cfop[1],
        "Tributação Monofásica": 0,
        "tributoIcms": icms,
        "tributoPisCofins": PIS_COFINS_BASIS,
    }
    if cest:
        body["codigoCest"] = cest
    return body


def nfe_payload(evidence: Any) -> dict[str, Any] | None:
    if not evidence or not evidence.numero:
        return None
    return {
        "numero": evidence.numero,
        "serie": evidence.serie,
        "emissao": evidence.emissao,
        "fornecedor": evidence.fornecedor,
        "accessKeyMasked": evidence.access_key_masked,
        "protocoloCstat": evidence.protocolo_cstat,
    }


def verified_icms_refs(checkpoint: dict[str, Any], ncm: str, cest: str | None) -> set[str]:
    refs: set[str] = set()
    for record in checkpoint.values():
        if not isinstance(record, dict) or record.get("status") != "CREATED_AND_VERIFIED":
            continue
        if str(record.get("ncm") or "") != ncm:
            continue
        if str(record.get("cest") or "") != str(cest or ""):
            continue
        if record.get("icms_table_reference"):
            refs.add(str(record["icms_table_reference"]))
    return refs


def verified_profile_for(
    profiles: list[dict[str, Any]], ncm: str, cest: str | None, family: str | None
) -> dict[str, Any] | None:
    matches = []
    for profile in profiles:
        if profile.get("onda") == 5 or profile.get("profile_canary_status") != "VERIFIED":
            continue
        if ncm not in (profile.get("ncms") or []):
            continue
        cests = profile.get("cests") or []
        if bool(cest) != bool(cests):
            continue
        if cest and cest not in cests:
            continue
        families = profile.get("familias_permitidas") or []
        if family and families and family not in families:
            continue
        matches.append(profile)
    if not matches:
        return None
    matches.sort(key=lambda item: item["profile_id"])
    return matches[0]


def choose_icms(
    icms_rows: list[Any],
    *,
    rate: float | None,
    verified: set[str],
    st_basis: dict[str, Any],
    st_reference: str,
) -> tuple[dict[str, Any], str, str]:
    if rate is None:
        return st_basis, st_reference, "LOCAL_ST_TABLE"
    status, matched = match_icms_by_entry_rate(
        icms_rows, cst_entrada="000", icms_entrada=rate, icms_saida=rate
    )
    pool = matched
    if not pool:
        return st_basis, st_reference, "LOCAL_ST_TABLE_AFTER_EMPTY_RATE_MATCH"
    complete = [
        row
        for row in pool
        if row.csosn_entrada is not None and row.csosn_saida is not None and row.fcp is not None
    ]
    if not complete:
        return st_basis, st_reference, "LOCAL_ST_TABLE_NO_COMPLETE_ICMS"
    if status == MATCH_UNIQUE and len(complete) == 1:
        return basis_from_row(complete[0]), complete[0].referencia, "UNIQUE_RATE_MATCH"
    chosen, reason = pick_icms_row(
        complete,
        verified_references=verified,
        expected_cst_entrada="000",
        expected_rate=rate,
    )
    return basis_from_row(chosen), chosen.referencia, reason


def mark_checkpoint(checkpoint: dict[str, Any], ean: str, payload: dict[str, Any]) -> None:
    checkpoint[ean] = payload
    CHECKPOINT.write_text(json.dumps(checkpoint, ensure_ascii=False, indent=2), encoding="utf-8")


def main() -> None:
    generated_at = datetime.now(timezone.utc).isoformat()
    payload = json.loads(PROFILES.read_text(encoding="utf-8"))
    existing = [profile for profile in payload["profiles"] if profile.get("onda") != 5]
    checkpoint = json.loads(CHECKPOINT.read_text(encoding="utf-8")) if CHECKPOINT.is_file() else {}
    if len(checkpoint) < 187:
        raise SystemExit(f"checkpoint abaixo de 187: {len(checkpoint)}")

    blocked = list(payload.get("blocked") or [])
    specials = {
        item["ean"]
        for item in payload.get("onda3Skipped") or []
        if item.get("motivo") == "CATEGORIA_ESPECIAL_FORA_DA_ONDA_3"
    }
    remaining = [
        item
        for item in blocked
        if item.get("ean") not in checkpoint
        and (
            item.get("motivo") in REMAINING_REASONS
            or item.get("motivo") in PERMANENT_REASONS
            or item.get("ean") in PERMANENT_EANS
            or item.get("ean") in specials
        )
    ]
    remaining_eans = {item["ean"] for item in remaining} | {
        ean for ean in specials if ean not in checkpoint
    }
    rows_by_ean = {row.ean: row for row in load_sheet(SHEET) if row.ean in remaining_eans}

    credential = resolve_credential(COMPANY_CODE)
    if credential.variable_name != PROFILE:
        raise SystemExit(f"credencial fora do profile exigido: {credential.variable_name}")

    icms_rows = load_icms_table(TAX_INPUT / "CADASTROiCMSWEBPOSTOS.xlsx")
    pis_rows = load_pis_cofins_table(TAX_INPUT / "cADPISCONFINSWEBPOSTOS.xlsx")
    pis_status, pis_matches = match_pis_cofins(
        pis_rows,
        cst_pis_entrada="50",
        cst_pis_saida="01",
        pis_entrada=0.65,
        pis_saida=0.65,
        cst_cofins_entrada="50",
        cst_cofins_saida="01",
        cofins_entrada=3.0,
        cofins_saida=3.0,
    )
    st_status, st_matches = match_icms(
        icms_rows,
        cst_entrada="060",
        cst_saida="060",
        icms_entrada=0.0,
        icms_saida=0.0,
        csosn_entrada="0",
        csosn_saida="0",
        fcp=0.0,
    )
    if pis_status != MATCH_UNIQUE or st_status != MATCH_UNIQUE:
        raise SystemExit("tabela local sem correspondencia unica de ST ou PIS/COFINS")
    st_basis = basis_from_row(st_matches[0])
    st_reference = st_matches[0].referencia
    pis_reference = pis_matches[0].referencia
    dfe_index = build_authorized_index(COMPANY_CODE)
    evidence_by_ncm_cest = build_ncm_cest_evidence(COMPANY_CODE)

    with httpx.Client(timeout=120.0) as client:
        guard = company_guard(credential, HttpProductReader(client))
        if not guard.passed:
            raise SystemExit("sentinel BONO nao confirmado na empresa 118508")
        catalog = paginate(client, "/INTEGRACAO/PRODUTO", credential.key)

    catalog_by_ean = {code: product for product in catalog for code in barcodes(product)}
    print(f"sentinel BONO: ok | catalogo: {len(catalog)} | checkpoint: {len(checkpoint)}")

    decisions: list[dict[str, Any]] = []
    staged: list[dict[str, Any]] = []
    pending_price = json.loads(PENDING_PRICE.read_text(encoding="utf-8")) if PENDING_PRICE.is_file() else {}

    def decide(item: dict[str, Any], action: str, **extra: Any) -> None:
        decisions.append({"ean": item.get("ean"), "motivoOriginal": item.get("motivo"), "acao": action, **extra})

    seen_eans: set[str] = set()
    work = list(remaining)
    for ean in specials | PERMANENT_EANS:
        if ean in checkpoint or any(item.get("ean") == ean for item in work):
            continue
        motivo = "EXCLUSAO_PERMANENTE" if ean in PERMANENT_EANS else "SEM_CEST_E_SEM_NOTA_PROPRIA"
        if ean == "789607405141":
            motivo = "GTIN_TRUNCADO"
        work.append({"ean": ean, "motivo": motivo, "descricao": ""})

    for item in work:
        ean = item["ean"]
        if ean in seen_eans or ean in checkpoint:
            continue
        seen_eans.add(ean)
        row = rows_by_ean.get(ean)
        original = item.get("motivo") or ""

        if ean in PERMANENT_EANS or original in PERMANENT_REASONS:
            decide(item, "BLOQUEIO_PERMANENTE", detalhe=original)
            continue
        if row is None:
            decide(item, "SKIPPED_PRE_POST", detalhe="LINHA_AUSENTE_NA_PLANILHA")
            continue
        if looks_fabricated_gtin(ean) or gtin_prefix_length_conflict(ean) or not row.ean_valid:
            decide(item, "BLOQUEIO_PERMANENTE", detalhe="GTIN_NAO_FLEXIVEL")
            continue
        if not row.has_price or not row.ncm:
            decide(item, "SKIPPED_PRE_POST", detalhe="DADOS_INCOMPLETOS")
            continue

        if original == "JA_NO_CATALOGO" or ean in catalog_by_ean:
            existing_product = catalog_by_ean.get(ean)
            code = int((existing_product or {}).get("produtoCodigo") or 0)
            mark_checkpoint(
                checkpoint,
                ean,
                {
                    "status": "ALREADY_REGISTERED",
                    "ean": ean,
                    "descricao": row.descricao,
                    "produto_existente": code or None,
                    "produto_existente_descricao": (existing_product or {}).get("nome"),
                    "bloqueio": "Nao cadastrar. Nao alterar o produto existente.",
                    "classificadoEm": generated_at,
                },
            )
            decide(item, "ALREADY_REGISTERED", produtoCodigo=code)
            continue

        family = commercial_family(row.descricao)
        matches = find_description_duplicates(row.descricao, catalog)
        if matches or original == "POSSIVEL_DUPLICIDADE":
            existing_product = matches[0] if matches else None
            if existing_product is None:
                decide(item, "SKIPPED_PRE_POST", detalhe="UNRESOLVED_DUPLICATE:sem cadastro comparavel")
                continue
            label, reason = classify_final_duplicate(
                row.descricao,
                existing_product.get("nome") or "",
                candidate_family=family,
                existing_family=commercial_family(existing_product.get("nome") or ""),
            )
            code = int(existing_product.get("produtoCodigo") or 0)
            if label == SAME_PRODUCT:
                mark_checkpoint(
                    checkpoint,
                    ean,
                    {
                        "status": "ALREADY_REGISTERED_BY_DESCRIPTION",
                        "ean": ean,
                        "descricao": row.descricao,
                        "produto_existente": code,
                        "produto_existente_descricao": existing_product.get("nome"),
                        "bloqueio": "Nao cadastrar. Nao alterar o produto existente.",
                        "classificadoEm": generated_at,
                    },
                )
                decide(item, "SAME_PRODUCT", produtoCodigo=code, detalhe=reason)
                continue
            if label == UNRESOLVED_DUPLICATE:
                decide(item, "SKIPPED_PRE_POST", detalhe=f"UNRESOLVED_DUPLICATE:{reason}", produtoCodigo=code)
                continue
            if label != LEGITIMATE_VARIANT:
                decide(item, "SKIPPED_PRE_POST", detalhe=f"{label}:{reason}")
                continue
            item = {**item, "variante": True, "detalheVariante": reason}

        hit = dfe_index.get(ean)
        evidence_cost = cost_from_index(ean, dfe_index)
        entry_item = (hit[2].get("normalized_json") or {}) if hit is not None else {}
        cost = 0.0
        cost_info: dict[str, Any] = {
            "valor": 0,
            "source": "PENDING_DFE",
            "cost_status": "PENDING",
            "cost_risk": RISK_ASSUMED,
            "requires_cost_update": True,
            "motivoRevisao": "Nenhuma NF-e autorizada da empresa contem este EAN",
            "nfe": None,
        }
        negative_margin = False
        if hit is not None and not evidence_cost.resolved:
            cost_info = {
                "valor": 0,
                "source": "PENDING_DFE_CONVERSION",
                "cost_status": "PENDING",
                "cost_risk": RISK_ASSUMED,
                "requires_cost_update": True,
                "motivoRevisao": evidence_cost.reason,
                "unidadeComercial": evidence_cost.unidade_comercial,
                "nfe": nfe_payload(evidence_cost),
            }
        elif evidence_cost.resolved:
            cost = float(evidence_cost.preco_custo or 0)
            cost_info = {
                "valor": cost,
                "source": "DFE",
                "cost_status": "RESOLVED",
                "requires_cost_update": False,
                "unidadeComercial": evidence_cost.unidade_comercial,
                "origemQuantidade": evidence_cost.quantidade_origem,
                "quantidade": float(evidence_cost.quantidade or 0),
                "calculo": evidence_cost.calculo,
                "nfe": nfe_payload(evidence_cost),
            }
            if cost > float(row.preco_venda):
                negative_margin = True
                cost_info["negative_margin"] = True
                cost_info["commercial_risk"] = "OWNER_ACCEPTED"
                cost_info["requires_price_review"] = True

        ncm = row.ncm
        cest = row.cest
        ncm_source = "PLANILHA"
        if hit is not None:
            ncm_nfe = str(entry_item.get("ncm") or "").strip()
            cest_nfe = str(entry_item.get("cest") or "").strip()
            if ncm_nfe and cest_nfe:
                ncm, cest, ncm_source = ncm_nfe, cest_nfe, "NFE_PROPRIA"
            elif ncm_nfe and not row.has_cest:
                ncm, ncm_source = ncm_nfe, "NFE_PROPRIA_SEM_CEST"
            elif original == "CONFLITO_NCM_CEST" and ncm_nfe and cest_nfe:
                ncm, cest, ncm_source = ncm_nfe, cest_nfe, "NFE_PROPRIA"
        if not ncm or len(ncm) != 8:
            decide(item, "SKIPPED_PRE_POST", detalhe="NCM_INVALIDO")
            continue

        special = special_category(ncm, row.descricao)
        family_evidence = None
        discarded: list[dict[str, Any]] = []
        selection_reason = "LOCAL_ST_TABLE"
        treatment = TREATMENT_SUBSTITUTED
        cfop = CFOP_SUBSTITUTED
        icms_basis, icms_reference = st_basis, st_reference
        verified = verified_icms_refs(checkpoint, ncm, cest)
        entries = evidence_by_ncm_cest.get((ncm, cest or "")) or []

        if hit is not None:
            entry = item_entry_evidence(
                entry_item,
                f"{(cost_info.get('nfe') or {}).get('numero')}/{(cost_info.get('nfe') or {}).get('serie')}",
            )
            classification = classify_entry(entry)
            rate = (entry_item.get("icms") or {}).get("ICMS.pICMS")
            if classification == ST_PROVEN:
                treatment, cfop = TREATMENT_SUBSTITUTED, CFOP_SUBSTITUTED
                icms_basis, icms_reference, selection_reason = st_basis, st_reference, "OWN_NFE_ST"
            else:
                chosen = choose_icms(
                    icms_rows,
                    rate=float(rate) if rate is not None else None,
                    verified=verified,
                    st_basis=st_basis,
                    st_reference=st_reference,
                )
                icms_basis, icms_reference, selection_reason = chosen
                treatment, cfop = (
                    (TREATMENT_SUBSTITUTED, CFOP_SUBSTITUTED)
                    if selection_reason.startswith("LOCAL_ST")
                    else (TREATMENT_TAXED, CFOP_TAXED)
                )
        elif original == "FAMILIA_COMERCIAL_DIVERGENTE":
            family_evidence = "DISCARDED_AS_DIVERGENT"
            verified_profile = verified_profile_for(existing, ncm, cest, None)
            if verified_profile:
                icms_basis = verified_profile["tributo_icms"]
                icms_reference = verified_profile["referencia_icms"]
                treatment = verified_profile["tratamento_observado"]
                cfop = (verified_profile["cfop_entrada"], verified_profile["cfop_saida"])
                selection_reason = "VERIFIED_PROFILE_WITHOUT_DIVERGENT_FAMILY"
            else:
                summary = summarize_evidence(entries) if entries else {}
                rates = {
                    round(float(entry["aliquotaEntrada"]), 4)
                    for entry in entries
                    if entry.get("aliquotaEntrada") is not None
                }
                rate = next(iter(rates)) if len(rates) == 1 else None
                chosen = choose_icms(
                    icms_rows,
                    rate=rate,
                    verified=verified,
                    st_basis=st_basis,
                    st_reference=st_reference,
                )
                icms_basis, icms_reference, selection_reason = chosen
                if rate is not None and not selection_reason.startswith("LOCAL_ST"):
                    treatment, cfop = TREATMENT_TAXED, CFOP_TAXED
                discarded.append({"motivo": "FAMILIA_DIVERGENTE_IGNORADA", "resumo": summary})
        elif original == "TRATAMENTOS_CONCORRENTES_NA_EVIDENCIA":
            same_family = [
                entry
                for entry in entries
                if not family or entry.get("familiaComercial") in {None, family}
            ]
            winner, rate, discarded = majority_treatment(same_family)
            verified_profile = verified_profile_for(existing, ncm, cest, family)
            if winner == ST_PROVEN:
                treatment, cfop = TREATMENT_SUBSTITUTED, CFOP_SUBSTITUTED
                icms_basis, icms_reference, selection_reason = st_basis, st_reference, "MAJORITY_NFE_ST"
            elif winner and rate is not None:
                chosen = choose_icms(
                    icms_rows, rate=rate, verified=verified, st_basis=st_basis, st_reference=st_reference
                )
                icms_basis, icms_reference, selection_reason = chosen
                treatment, cfop = TREATMENT_TAXED, CFOP_TAXED
            elif verified_profile:
                icms_basis = verified_profile["tributo_icms"]
                icms_reference = verified_profile["referencia_icms"]
                treatment = verified_profile["tratamento_observado"]
                cfop = (verified_profile["cfop_entrada"], verified_profile["cfop_saida"])
                selection_reason = "VERIFIED_PIPELINE_PROFILE"
            else:
                icms_basis, icms_reference, selection_reason = (
                    st_basis,
                    st_reference,
                    "OWNER_ACCEPTED_DETERMINISTIC_TIEBREAK",
                )
        elif original == "TABELA_ICMS_SEM_CORRESPONDENCIA_UNICA":
            rate = None
            if entries:
                rates = {
                    round(float(entry["aliquotaEntrada"]), 4)
                    for entry in entries
                    if entry.get("aliquotaEntrada") is not None
                }
                if len(rates) == 1:
                    rate = next(iter(rates))
            chosen = choose_icms(
                icms_rows, rate=rate, verified=verified, st_basis=st_basis, st_reference=st_reference
            )
            icms_basis, icms_reference, selection_reason = chosen
            if rate is not None and not selection_reason.startswith("LOCAL_ST"):
                treatment, cfop = TREATMENT_TAXED, CFOP_TAXED
        elif not cest:
            selection_reason = "ONDA3_CEST_AUSENTE_VALIDADO"
            family_evidence = family_evidence or "NEUTRA"

        resolved_row = replace(row, ncm=ncm, cest=cest)
        body = build_body(resolved_row, ncm=ncm, cest=cest, cost=cost, icms=icms_basis, cfop=cfop)
        product = {
            "linha": row.line,
            "ean": ean,
            "descricao": row.descricao,
            "familiaComercial": family,
            "precoVenda": row.preco_venda,
            "ncm": ncm,
            "cest": cest,
            "cest_status": "NOT_PROVIDED" if not cest else "PROVIDED",
            "custo": cost_info,
            "negative_margin": negative_margin,
            "commercial_risk": "OWNER_ACCEPTED" if negative_margin else None,
            "requires_price_review": negative_margin,
            "body": {"ready": True, "hash": body_hash(body), "preview": body},
            "categoria": "READY_ASSUMED_RISK",
            "varianteLegitima": bool(item.get("variante")),
        }
        if negative_margin:
            pending_price[ean] = {
                "ean": ean,
                "descricao": row.descricao,
                "precoCustoDfe": cost,
                "precoVenda": row.preco_venda,
                "negative_margin": True,
                "commercial_risk": "OWNER_ACCEPTED",
                "requires_price_review": True,
                "criadoEm": generated_at,
            }
        staged.append(
            {
                "treatment": treatment,
                "icms_basis": icms_basis,
                "icms_reference": icms_reference,
                "cfop": cfop,
                "family": family,
                "special": special,
                "ncm": ncm,
                "cest": cest,
                "selection_reason": selection_reason,
                "family_evidence": family_evidence,
                "discarded": discarded,
                "ncm_source": ncm_source,
                "produto": product,
            }
        )
        decide(
            item,
            "ENFILEIRADO",
            variante=bool(item.get("variante")),
            ncm=ncm,
            cest=cest,
            selection_reason=selection_reason,
            custo=cost,
            negative_margin=negative_margin,
        )

    grouped: dict[tuple, list[dict[str, Any]]] = defaultdict(list)
    for item in staged:
        grouped[
            (
                item["ncm"],
                item["cest"] or "",
                item["treatment"],
                item["icms_reference"],
                item["cfop"],
                item["special"] or "",
            )
        ].append(item)

    new_profiles: list[dict[str, Any]] = []
    for (ncm, cest, treatment, icms_reference, cfop, special), cluster in grouped.items():
        cluster.sort(key=lambda item: (item["produto"]["precoVenda"], item["produto"]["ean"]))
        family = next((item["family"] for item in cluster if item["family"]), None)
        level = LEVEL_SPECIAL if special else LEVEL_D
        first = cluster[0]
        profile_id = f"{build_profile_id(level, family, ncm, cest or None, icms_reference)}-ONDA5"
        if special:
            profile_id = f"{profile_id}-{special}"
        verified = verified_icms_refs(checkpoint, ncm, cest or None)
        canary_verified = icms_reference in verified
        new_profiles.append(
            {
                "profile_id": profile_id,
                "level": level,
                "descricao": (
                    f"{family or 'familia nao reconhecida'} | NCM {ncm} | "
                    f"CEST {cest or 'ausente'} | entrada {treatment} | ICMS {icms_reference}"
                ),
                "familias_permitidas": [family] if family else [],
                "ncms": [ncm],
                "cests": [cest] if cest else [],
                "tratamento_observado": treatment,
                "referencia_icms": icms_reference,
                "referencia_pis_cofins": pis_reference,
                "cfop_entrada": cfop[0],
                "cfop_saida": cfop[1],
                "tributacao_monofasica": 0,
                "tributo_icms": first["icms_basis"],
                "tributo_pis_cofins": PIS_COFINS_BASIS,
                "evidencias": {
                    "origem": "ONDA_FINAL_OWNER_ACCEPTED",
                    "selection_reason": first["selection_reason"],
                    "family_evidence": first["family_evidence"],
                    "ncm_cest_source": first["ncm_source"],
                    "alternativasDescartadas": first["discarded"],
                    "cest_status": "NOT_PROVIDED" if not cest else "PROVIDED",
                    **audit_trail("TABELA_LOCAL_POR_CEST", CONFIDENCE_VERY_LOW),
                },
                "confidence": CONFIDENCE_VERY_LOW,
                "fiscal_risk": RISK_ASSUMED,
                "requires_accountant_review": True,
                "onda": 5,
                "quantidade_candidatos": len(cluster),
                "produto_canario": cluster[0]["produto"]["ean"],
                "produto_canario_codigo": None,
                "profile_canary_status": "VERIFIED" if canary_verified else "PENDING",
                "canario_origem": (
                    "BASE_JA_VERIFICADA_NO_PIPELINE" if canary_verified else "ONDA_FINAL"
                ),
                "produtos": [item["produto"] for item in cluster],
            }
        )

    payload["profiles"] = existing + new_profiles
    payload["ondaFinalBuiltAt"] = generated_at
    payload["ondaFinalDecisions"] = decisions
    PROFILES.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    PENDING_PRICE.write_text(json.dumps(pending_price, ensure_ascii=False, indent=2), encoding="utf-8")
    CLASSIFICATION.write_text(
        json.dumps(
            {
                "title": "ONDA FINAL — CLASSIFICACAO 118508",
                "generatedAt": generated_at,
                "analisados": len(decisions),
                "enfileirados": sum(1 for item in decisions if item["acao"] == "ENFILEIRADO"),
                "variantes": sum(1 for item in decisions if item.get("variante")),
                "sameProduct": sum(1 for item in decisions if item["acao"] == "SAME_PRODUCT"),
                "alreadyRegistered": sum(1 for item in decisions if item["acao"] == "ALREADY_REGISTERED"),
                "skipped": sum(1 for item in decisions if item["acao"] == "SKIPPED_PRE_POST"),
                "permanentes": sum(1 for item in decisions if item["acao"] == "BLOQUEIO_PERMANENTE"),
                "perfis": len(new_profiles),
                "checkpoint": len(checkpoint),
                "decisions": decisions,
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )

    counts: dict[str, int] = defaultdict(int)
    for item in decisions:
        counts[item["acao"]] += 1
    print(f"ONDA FINAL montada: {len(new_profiles)} perfis | {sum(p['quantidade_candidatos'] for p in new_profiles)} produtos")
    for action, count in sorted(counts.items()):
        print(f"   {action:28} {count}")
    print(f"checkpoint: {len(checkpoint)}")
    print("API WRITES: 0")


if __name__ == "__main__":
    main()
