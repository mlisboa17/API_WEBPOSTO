"""Monta somente os perfis da ONDA 3 (sem CEST), sem reconstruir os demais.

Le os EANs ja bloqueados por SEM_CEST_E_SEM_NOTA_PROPRIA, resolve a base pelo NCM
exato e pela familia comercial, e anexa perfis onda=3 ao arquivo existente.
Nao inventa CEST. Nao envia POST.
"""

from __future__ import annotations

import hashlib
import json
import sys
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src.operational.product_registration.dfe_cost_resolver import (  # noqa: E402
    build_authorized_index,
    cost_from_index,
)
from src.operational.product_registration.fiscal_profiles import (  # noqa: E402
    CONFIDENCE_VERY_LOW,
    LEVEL_D,
    RISK_ASSUMED,
    TREATMENT_SUBSTITUTED,
    audit_trail,
    build_profile_id,
    special_category,
)
from src.operational.product_registration.fiscal_sheet_loader import load_sheet  # noqa: E402
from src.operational.product_registration.product_family import commercial_family  # noqa: E402
from src.operational.product_registration.tax_table_matcher import (  # noqa: E402
    MATCH_UNIQUE,
    basis_from_row,
    load_icms_table,
    load_pis_cofins_table,
    match_icms,
    match_pis_cofins,
)

COMPANY_CODE = 118508
GRUPO_CODIGO = 55446
COST_CENTER = 24886
REGISTRATION_DIR = ROOT / "data" / "product_registration"
SHEET = REGISTRATION_DIR / "FISCAL_PRODUTOS_A_CADASTRAR_118508.xlsx"
TAX_INPUT = REGISTRATION_DIR / "tax_tables_input"
PROFILES = REGISTRATION_DIR / "fiscal_profiles_118508.json"
CHECKPOINT = REGISTRATION_DIR / "execution" / "checkpoint_118508.json"

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


def body_hash(body: dict[str, Any]) -> str:
    payload = json.dumps(body, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def build_body(row, *, cost: float, icms: dict[str, Any]) -> dict[str, Any]:
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
        "codigoNcm": row.ncm,
        "ativo": True,
        "permiteVendaEstoqueNegativo": False,
        "produtoVendeFracionado": False,
        "utilizaCodigoBarras": True,
        "utilizaBalanca": False,
        "cdCfopEntrada": CFOP_SUBSTITUTED[0],
        "cdCfopSaida": CFOP_SUBSTITUTED[1],
        "Tributação Monofásica": 0,
        "tributoIcms": icms,
        "tributoPisCofins": PIS_COFINS_BASIS,
    }
    # CEST ausente permanece ausente: o campo nao e enviado.
    return body


def bases_for_ncm_family(profiles: list[dict[str, Any]], ncm: str, family: str | None) -> set[str]:
    refs: set[str] = set()
    for profile in profiles:
        if profile.get("onda") == 3:
            continue
        if ncm not in (profile.get("ncms") or []):
            continue
        families = profile.get("familias_permitidas") or []
        if family and families and family not in families:
            continue
        if profile.get("referencia_icms"):
            refs.add(str(profile["referencia_icms"]))
    return refs


def main() -> None:
    payload = json.loads(PROFILES.read_text(encoding="utf-8"))
    checkpoint = json.loads(CHECKPOINT.read_text(encoding="utf-8")) if CHECKPOINT.is_file() else {}
    existing = [profile for profile in payload["profiles"] if profile.get("onda") != 3]
    sem_cest_eans = {
        item["ean"]
        for item in payload.get("blocked") or []
        if item.get("motivo") == "SEM_CEST_E_SEM_NOTA_PROPRIA"
    }
    rows = [row for row in load_sheet(SHEET) if row.ean in sem_cest_eans]
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

    grouped: dict[tuple, list[dict[str, Any]]] = defaultdict(list)
    skipped: list[dict[str, Any]] = []
    for row in rows:
        if row.ean in checkpoint:
            continue
        if not row.ean_valid or not row.has_price or not row.ncm:
            skipped.append({"ean": row.ean, "motivo": "DADOS_INCOMPLETOS"})
            continue
        if special_category(row.ncm, row.descricao):
            skipped.append({"ean": row.ean, "motivo": "CATEGORIA_ESPECIAL_FORA_DA_ONDA_3"})
            continue
        family = commercial_family(row.descricao)
        refs = bases_for_ncm_family(existing, row.ncm, family)
        if len(refs) > 1:
            skipped.append({"ean": row.ean, "motivo": "MULTIPLAS_BASES_PLAUSIVEIS", "detalhe": sorted(refs)})
            continue
        icms_reference = next(iter(refs)) if refs else st_reference
        cost = 0.0
        cost_info = {
            "valor": 0,
            "source": "PENDING_DFE",
            "cost_status": "PENDING",
            "cost_risk": RISK_ASSUMED,
            "requires_cost_update": True,
            "motivoRevisao": "Nenhuma NF-e autorizada da empresa contem este EAN",
            "nfe": None,
        }
        evidence_cost = cost_from_index(row.ean, dfe_index)
        if evidence_cost.resolved:
            cost = float(evidence_cost.preco_custo or 0)
            if cost > 0 and cost <= float(row.preco_venda):
                cost_info = {
                    "valor": cost,
                    "source": "DFE",
                    "cost_status": "RESOLVED",
                    "requires_cost_update": False,
                    "nfe": None,
                }
        body = build_body(row, cost=cost, icms=st_basis)
        grouped[(row.ncm, family or "", icms_reference)].append(
            {
                "linha": row.line,
                "ean": row.ean,
                "descricao": row.descricao,
                "familiaComercial": family,
                "precoVenda": row.preco_venda,
                "ncm": row.ncm,
                "cest": None,
                "cest_status": "NOT_PROVIDED",
                "custo": cost_info,
                "body": {"ready": True, "hash": body_hash(body), "preview": body},
                "categoria": "READY_ASSUMED_RISK",
            }
        )

    new_profiles: list[dict[str, Any]] = []
    for (ncm, family, icms_reference), products in grouped.items():
        products.sort(key=lambda item: (item["precoVenda"], item["ean"]))
        profile_id = build_profile_id(LEVEL_D, family or None, ncm, None, icms_reference)
        new_profiles.append(
            {
                "profile_id": profile_id,
                "level": LEVEL_D,
                "descricao": (
                    f"{family or 'familia nao reconhecida'} | NCM {ncm} | "
                    f"CEST ausente | entrada ST | ICMS {icms_reference}"
                ),
                "familias_permitidas": [family] if family else [],
                "ncms": [ncm],
                "cests": [],
                "tratamento_observado": TREATMENT_SUBSTITUTED,
                "referencia_icms": icms_reference,
                "referencia_pis_cofins": pis_reference,
                "cfop_entrada": CFOP_SUBSTITUTED[0],
                "cfop_saida": CFOP_SUBSTITUTED[1],
                "tributacao_monofasica": 0,
                "tributo_icms": st_basis,
                "tributo_pis_cofins": PIS_COFINS_BASIS,
                "evidencias": {
                    "origem": "TABELA_LOCAL_POR_NCM_SEM_CEST",
                    "cest_status": "NOT_PROVIDED",
                    **audit_trail("TABELA_LOCAL_POR_CEST", CONFIDENCE_VERY_LOW),
                },
                "confidence": CONFIDENCE_VERY_LOW,
                "fiscal_risk": RISK_ASSUMED,
                "requires_accountant_review": True,
                "onda": 3,
                "quantidade_candidatos": len(products),
                "produto_canario": products[0]["ean"],
                "produto_canario_codigo": None,
                "profile_canary_status": "PENDING",
                "canario_origem": "PRIMEIRO_PRODUTO_SEM_CEST",
                "produtos": products,
            }
        )

    payload["profiles"] = existing + new_profiles
    payload["onda3BuiltAt"] = datetime.now(timezone.utc).isoformat()
    payload["onda3Skipped"] = skipped
    PROFILES.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"ONDA 3: {len(new_profiles)} perfis | {sum(p['quantidade_candidatos'] for p in new_profiles)} produtos")
    print(f"pulados na montagem: {len(skipped)}")
    for item in skipped:
        print(f"   {item['ean']} | {item['motivo']}")
    print("API WRITES: 0")


if __name__ == "__main__":
    main()
