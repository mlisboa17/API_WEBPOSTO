"""Gera os perfis fiscais da planilha da empresa 118508 (somente leitura).

Agrupa os produtos ainda nao processados por familia comercial, NCM, CEST, tratamento
observado na entrada e referencias tributarias, e marca o canario de cada perfil. Perfil
que ja tem produto criado e verificado por este pipeline, com base identica, nasce com o
canario satisfeito.

Tambem enfileira os produtos cujo codigo de barras e novo mas o produto ja existe, para
operacao propria de inclusao de codigo adicional.

Nao envia POST.
"""

from __future__ import annotations

import hashlib
import json
import sys
from collections import defaultdict
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
    SAME_PRODUCT_NEW_GTIN,
    classify_duplicate,
    find_description_duplicates,
    looks_fabricated_gtin,
)
from src.operational.product_registration.entry_evidence_index import (  # noqa: E402
    build_ncm_cest_evidence,
    item_entry_evidence,
    summarize_evidence,
)
from src.operational.product_registration.fiscal_profiles import (  # noqa: E402
    CONFIDENCE_HIGH,
    CONFIDENCE_LOW,
    CONFIDENCE_VERY_LOW,
    LEVEL_A,
    LEVEL_D,
    LEVEL_SPECIAL,
    RISK_ASSUMED,
    TREATMENT_SUBSTITUTED,
    TREATMENT_TAXED,
    WAVE_BY_LEVEL,
    Profile,
    build_profile_id,
    place_from_evidence,
    read_evidence,
    resolve_profile_family,
    special_category,
    weakest_level,
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
CHECKPOINT = REGISTRATION_DIR / "execution" / "checkpoint_118508.json"
PROFILES_OUT = REGISTRATION_DIR / "fiscal_profiles_118508.json"
BARCODES_OUT = REGISTRATION_DIR / "pending_additional_barcodes_118508.json"

PERMANENT_EXCLUSIONS = {"7891000376928", "7891962076317"}
IMPLAUSIBLE_MARGIN_FACTOR = 8.0

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


def verified_bases(checkpoint: dict[str, Any]) -> dict[tuple[str, str, str], dict[str, Any]]:
    """Bases fiscais já provadas em producao, por NCM, CEST e referencia de ICMS.

    Produto criado e verificado por este pipeline dispensa novo canario para a mesma base.
    Os lotes antigos nao gravavam NCM e CEST no checkpoint, entao a base vem do preflight
    que originou cada envio; o checkpoint continua sendo a prova de que foi verificado.
    """
    verified = {
        ean: record
        for ean, record in checkpoint.items()
        if record.get("status") == "CREATED_AND_VERIFIED"
    }
    found: dict[tuple[str, str, str], dict[str, Any]] = {}

    def remember(ean: str, ncm: Any, cest: Any, reference: Any) -> None:
        if not (ncm and reference) or ean not in verified:
            return
        key = (str(ncm), str(cest or ""), str(reference))
        found.setdefault(key, {"ean": ean, **verified[ean]})

    for ean, record in verified.items():
        remember(ean, record.get("ncm"), record.get("cest"), record.get("icms_table_reference"))
    for selection in sorted(REGISTRATION_DIR.glob("microbatch_*/*.json")):
        if selection.name in ("execution_result.json", "batch_lock.json"):
            continue
        try:
            payload = json.loads(selection.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            continue
        for product in payload.get("products") or []:
            body = (product.get("body") or {}).get("preview") or {}
            remember(
                str(product.get("ean") or ""),
                body.get("codigoNcm"),
                body.get("codigoCest"),
                (product.get("baseFiscal") or {}).get("icmsTableReference"),
            )
    return found


def build_body(row, *, cost: float, icms: dict[str, Any], cfop: tuple[str, str]) -> dict[str, Any]:
    entrada, saida = cfop
    return {
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
        "codigoCest": row.cest,
        "ativo": True,
        "permiteVendaEstoqueNegativo": False,
        "produtoVendeFracionado": False,
        "utilizaCodigoBarras": True,
        "utilizaBalanca": False,
        "cdCfopEntrada": entrada,
        "cdCfopSaida": saida,
        "Tributação Monofásica": 0,
        "tributoIcms": icms,
        "tributoPisCofins": PIS_COFINS_BASIS,
    }


def main() -> None:
    generated_at = datetime.now(timezone.utc).isoformat()

    print("=" * 78)
    print("PERFIS FISCAIS — EMPRESA 118508 (READ-ONLY)")
    print("=" * 78)

    rows = load_sheet(SHEET)
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
    pis_reference = pis_matches[0].referencia if pis_status == MATCH_UNIQUE else None
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
    st_basis = basis_from_row(st_matches[0]) if st_status == MATCH_UNIQUE else None
    st_reference = st_matches[0].referencia if st_status == MATCH_UNIQUE else None
    print(f"tabela ST: {st_status} ref={st_reference} | PIS/COFINS: {pis_status} ref={pis_reference}")

    taxed_cache: dict[float, tuple[dict[str, Any] | None, str | None]] = {}

    def taxed_basis_for(rate: float) -> tuple[dict[str, Any] | None, str | None]:
        key = round(rate, 4)
        if key not in taxed_cache:
            status, matched = match_icms_by_entry_rate(
                icms_rows, cst_entrada="000", icms_entrada=key, icms_saida=key
            )
            taxed_cache[key] = (
                (basis_from_row(matched[0]), matched[0].referencia)
                if status == MATCH_UNIQUE
                else (None, None)
            )
        return taxed_cache[key]

    dfe_index = build_authorized_index(COMPANY_CODE)
    evidence_by_ncm_cest = build_ncm_cest_evidence(COMPANY_CODE)
    print(f"indice DF-e: {len(dfe_index)} EANs | pares NCM+CEST: {len(evidence_by_ncm_cest)}")

    with httpx.Client(timeout=120.0) as client:
        guard = company_guard(credential, HttpProductReader(client))
        if not guard.passed:
            raise SystemExit("sentinel BONO nao confirmado na empresa 118508")
        catalog = paginate(client, "/INTEGRACAO/PRODUTO", credential.key)
        links = paginate(client, "/INTEGRACAO/PRODUTO_EMPRESA", credential.key)

    linked_codes = {
        int(link.get("produtoCodigo") or 0)
        for link in links
        if int(link.get("empresaCodigo") or 0) == COMPANY_CODE
    }
    catalog_barcodes = {code for product in catalog for code in barcodes(product)}
    checkpoint = json.loads(CHECKPOINT.read_text(encoding="utf-8")) if CHECKPOINT.is_file() else {}
    print(f"sentinel BONO: ok | catalogo: {len(catalog)} | vinculos: {len(linked_codes)}"
          f" | checkpoint: {len(checkpoint)}")
    print()

    staged: list[dict[str, Any]] = []
    blocked: list[dict[str, Any]] = []
    barcode_queue: list[dict[str, Any]] = []
    blocked_counts: dict[str, int] = defaultdict(int)

    def block(row, reason: str, detail: str | None = None) -> None:
        blocked_counts[reason] += 1
        blocked.append(
            {
                "linha": row.line,
                "ean": row.ean,
                "descricao": row.descricao,
                "motivo": reason,
                "detalhe": detail,
            }
        )

    def register(
        row,
        *,
        level: str,
        treatment: str,
        icms_basis: dict[str, Any],
        icms_reference: str | None,
        cfop: tuple[str, str],
        confidence: str,
        family: str | None,
        cost: float,
        cost_info: dict[str, Any],
        evidence: dict[str, Any],
        special: str | None = None,
    ) -> None:
        body = build_body(row, cost=cost, icms=icms_basis, cfop=cfop)
        staged.append(
            {
                "level": level,
                "treatment": treatment,
                "icms_basis": icms_basis,
                "icms_reference": icms_reference,
                "cfop": cfop,
                "confidence": confidence,
                "family": family,
                "special": special,
                "evidence": evidence,
                "produto": {
                    "linha": row.line,
                    "ean": row.ean,
                    "descricao": row.descricao,
                    "familiaComercial": family,
                    "precoVenda": row.preco_venda,
                    "ncm": row.ncm,
                    "cest": row.cest,
                    "custo": cost_info,
                    "body": {"ready": True, "hash": body_hash(body), "preview": body},
                    "categoria": "READY_HIGH_CONFIDENCE"
                    if confidence == CONFIDENCE_HIGH
                    else "READY_ASSUMED_RISK",
                },
            }
        )

    for row in rows:
        if not row.ean_valid:
            block(row, "GTIN_INVALIDO")
            continue
        fabricated = looks_fabricated_gtin(row.ean)
        if fabricated:
            block(row, "GTIN_COM_APARENCIA_DE_INVENTADO", fabricated)
            continue
        if row.ean in PERMANENT_EXCLUSIONS:
            block(row, "EXCLUSAO_PERMANENTE")
            continue
        if row.ean in checkpoint:
            block(row, "JA_PROCESSADO", f"produto {checkpoint[row.ean].get('codProduto')}")
            continue
        if row.ean in catalog_barcodes:
            block(row, "JA_NO_CATALOGO")
            continue
        if not row.has_price:
            block(row, "SEM_PRECO")
            continue
        if not row.ncm or len(row.ncm) != 8:
            block(row, "NCM_INVALIDO")
            continue

        family = commercial_family(row.descricao)
        matches = find_description_duplicates(row.descricao, catalog)
        if matches:
            label, reason = classify_duplicate(
                row.descricao,
                matches[0].get("nome") or "",
                candidate_family=family,
                existing_family=commercial_family(matches[0].get("nome") or ""),
            )
            block(row, "POSSIVEL_DUPLICIDADE", f"{label}: {reason}")
            if label == SAME_PRODUCT_NEW_GTIN:
                barcode_queue.append(
                    {
                        "linha": row.line,
                        "eanNovo": row.ean,
                        "descricaoPlanilha": row.descricao,
                        "produtoExistente": {
                            "produtoCodigo": matches[0].get("produtoCodigo"),
                            "nome": matches[0].get("nome"),
                            "ncm": matches[0].get("ncm"),
                            "cest": matches[0].get("cest"),
                            "codigosBarra": sorted(barcodes(matches[0])),
                            "vinculadoA118508": int(matches[0].get("produtoCodigo") or 0)
                            in linked_codes,
                        },
                        "justificativa": reason,
                        "operacao": "INCLUIR_CODIGO_BARRAS_ADICIONAL",
                        "status": "PENDENTE_OPERACAO_PROPRIA",
                    }
                )
            continue

        special = special_category(row.ncm)
        hit = dfe_index.get(row.ean)

        # --- Custo -----------------------------------------------------------------
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
        entry_item: dict[str, Any] = {}
        if hit is not None:
            evidence_cost = cost_from_index(row.ean, dfe_index)
            entry_item = hit[2].get("normalized_json") or {}
            if not evidence_cost.resolved:
                block(row, "CONVERSAO_EMBALAGEM_INDETERMINAVEL", evidence_cost.reason)
                continue
            cost = float(evidence_cost.preco_custo)
            if cost > row.preco_venda:
                block(row, "CUSTO_ACIMA_DA_VENDA", f"custo {cost} venda {row.preco_venda}")
                continue
            if cost > 0 and row.preco_venda / cost > IMPLAUSIBLE_MARGIN_FACTOR:
                block(row, "MARGEM_IMPLAUSIVEL", f"custo {cost} venda {row.preco_venda}")
                continue
            ncm_nfe = str(entry_item.get("ncm") or "").strip()
            cest_nfe = str(entry_item.get("cest") or "").strip()
            if (ncm_nfe and ncm_nfe != row.ncm) or (cest_nfe and cest_nfe != row.cest):
                block(
                    row,
                    "CONFLITO_NCM_CEST",
                    f"planilha {row.ncm}/{row.cest} nota {ncm_nfe}/{cest_nfe}",
                )
                continue
            cost_info = {
                "valor": cost,
                "source": "DFE",
                "cost_status": "RESOLVED",
                "requires_cost_update": False,
                "unidadeComercial": evidence_cost.unidade_comercial,
                "origemQuantidade": evidence_cost.quantidade_origem,
                "quantidade": float(evidence_cost.quantidade or 0),
                "calculo": evidence_cost.calculo,
                "icmsStCobrado": float(evidence_cost.icms_st_cobrado or 0),
                "nfe": {
                    "numero": evidence_cost.numero,
                    "serie": evidence_cost.serie,
                    "emissao": evidence_cost.emissao,
                    "fornecedor": evidence_cost.fornecedor,
                    "accessKeyMasked": evidence_cost.access_key_masked,
                    "protocoloCstat": evidence_cost.protocolo_cstat,
                },
            }

        # --- Base fiscal -----------------------------------------------------------
        if hit is not None:
            entry = item_entry_evidence(
                entry_item, f"{cost_info['nfe']['numero']}/{cost_info['nfe']['serie']}"
            )
            classification = classify_entry(entry)
            if classification == ST_PROVEN:
                if st_basis is None:
                    block(row, "SEM_TABELA_ST")
                    continue
                icms_basis, icms_reference = st_basis, st_reference
                treatment, cfop = TREATMENT_SUBSTITUTED, CFOP_SUBSTITUTED
            else:
                rate = (entry_item.get("icms") or {}).get("ICMS.pICMS")
                if rate is None:
                    block(row, "ALIQUOTA_DE_ENTRADA_AUSENTE")
                    continue
                icms_basis, icms_reference = taxed_basis_for(float(rate))
                if icms_basis is None:
                    block(row, "TABELA_ICMS_SEM_CORRESPONDENCIA_UNICA", f"aliquota {rate}")
                    continue
                treatment, cfop = TREATMENT_TAXED, CFOP_TAXED
            register(
                row,
                level=LEVEL_A if not special else LEVEL_SPECIAL,
                treatment=treatment,
                icms_basis=icms_basis,
                icms_reference=icms_reference,
                cfop=cfop,
                confidence=CONFIDENCE_HIGH if classification == ST_PROVEN else CONFIDENCE_LOW,
                family=family,
                cost=cost,
                cost_info=cost_info,
                evidence={
                    "origem": "NF_E_DO_PRODUTO",
                    "classificacaoEntrada": classification,
                    "cstEntrada": entry.cst_icms,
                    "aliquotaEntrada": (entry_item.get("icms") or {}).get("ICMS.pICMS"),
                    "nfe": f"{cost_info['nfe']['numero']}/{cost_info['nfe']['serie']}",
                    "fornecedor": cost_info["nfe"]["fornecedor"],
                },
                special=special,
            )
            continue

        if not row.has_cest:
            block(row, "SEM_CEST_E_SEM_NOTA_PROPRIA")
            continue

        entries = evidence_by_ncm_cest.get((row.ncm, row.cest)) or []
        if entries:
            reading = read_evidence(entries, summarize_evidence(entries), family)
            placement = place_from_evidence(reading)
            if placement.level is None:
                block(row, placement.blocked_reason or "EVIDENCIA_INDEFINIDA")
                continue
            if placement.treatment == TREATMENT_SUBSTITUTED:
                if st_basis is None:
                    block(row, "SEM_TABELA_ST")
                    continue
                icms_basis, icms_reference = st_basis, st_reference
                cfop = CFOP_SUBSTITUTED
            else:
                icms_basis, icms_reference = taxed_basis_for(float(placement.entry_rate or 0))
                if icms_basis is None:
                    block(row, "TABELA_ICMS_SEM_CORRESPONDENCIA_UNICA")
                    continue
                cfop = CFOP_TAXED
            register(
                row,
                level=placement.level if not special else LEVEL_SPECIAL,
                treatment=placement.treatment or TREATMENT_SUBSTITUTED,
                icms_basis=icms_basis,
                icms_reference=icms_reference,
                cfop=cfop,
                confidence=CONFIDENCE_LOW,
                family=family,
                cost=cost,
                cost_info=cost_info,
                evidence={
                    "origem": "ANALOGIA_NCM_CEST",
                    "itens": reading.items,
                    "notasDistintas": reading.invoices,
                    "fornecedoresDistintos": reading.suppliers,
                    "distribuicaoCst": reading.cst_distribution,
                    "familiasObservadas": reading.families,
                    "familiaCandidato": family,
                    "familiaEvidencia": reading.family_evidence,
                    "tratamento": placement.treatment,
                    "aliquotaEntrada": placement.entry_rate,
                    "amostra": [
                        {
                            "descricao": e.get("descricao"),
                            "familiaComercial": e.get("familiaComercial"),
                            "cstIcms": e.get("cstIcms"),
                            "nfe": e.get("nfe"),
                            "fornecedor": e.get("fornecedor"),
                        }
                        for e in entries[:8]
                    ],
                },
                special=special,
            )
            continue

        # Sem nota propria e sem evidencia: a correspondencia mais especifica disponivel e
        # a base de ST do CEST informado na planilha. Confianca minima e risco declarado.
        if st_basis is None:
            block(row, "SEM_TABELA_ST")
            continue
        register(
            row,
            level=LEVEL_D if not special else LEVEL_SPECIAL,
            treatment=TREATMENT_SUBSTITUTED,
            icms_basis=st_basis,
            icms_reference=st_reference,
            cfop=CFOP_SUBSTITUTED,
            confidence=CONFIDENCE_VERY_LOW,
            family=family,
            cost=cost,
            cost_info=cost_info,
            evidence={
                "origem": "TABELA_LOCAL_POR_CEST",
                "observacao": (
                    "Nenhuma NF-e da empresa contem este EAN nem itens com este NCM e CEST; "
                    "base escolhida pela correspondencia de ST do CEST informado na planilha"
                ),
            },
            special=special,
        )

    # --- Agrupamento -----------------------------------------------------------------
    # A base fiscal e a chave do perfil. Produtos de mesmo NCM, CEST, tratamento e
    # referencias compartilham a mesma decisao, ainda que a descricao de um deles nao
    # permita reconhecer a familia. Duas familias reconhecidas diferentes ficam separadas.
    grouped: dict[tuple, list[dict[str, Any]]] = defaultdict(list)
    for item in staged:
        grouped[
            (
                item["produto"]["ncm"],
                item["produto"]["cest"] or "",
                item["treatment"],
                item["icms_reference"] or "",
                item["cfop"],
                item["special"] or "",
            )
        ].append(item)

    profiles: dict[str, Profile] = {}
    for key, items in grouped.items():
        families = [item["family"] for item in items]
        resolved_family = resolve_profile_family(families)
        clusters: dict[str | None, list[dict[str, Any]]] = defaultdict(list)
        if resolved_family is False:
            for item in items:
                clusters[item["family"]].append(item)
        else:
            clusters[resolved_family] = items

        for family, cluster in clusters.items():
            level = weakest_level([item["level"] for item in cluster])
            # O perfil declara a menor confianca do grupo, porque a aprovacao vale para
            # todos os produtos dele.
            confidence = max(
                (item["confidence"] for item in cluster),
                key=lambda value: {
                    CONFIDENCE_HIGH: 0,
                    CONFIDENCE_LOW: 1,
                    CONFIDENCE_VERY_LOW: 2,
                }[value],
            )
            first = cluster[0]
            ncm, cest, treatment, icms_reference, cfop, special = key
            profile_id = build_profile_id(level, family, ncm, cest or None, icms_reference)
            if special:
                profile_id = f"{profile_id}-{special}"
            profile = Profile(
                profile_id=profile_id,
                level=level,
                descricao=(
                    f"{family or 'familia nao reconhecida'} | NCM {ncm} | "
                    f"CEST {cest or 'ausente'} | entrada {treatment} | ICMS {icms_reference}"
                    + (f" | categoria {special}" if special else "")
                ),
                familias_permitidas=sorted({f for f in families if f}) or [],
                ncms=[ncm],
                cests=[cest] if cest else [],
                tratamento_observado=treatment,
                referencia_icms=icms_reference or None,
                referencia_pis_cofins=pis_reference,
                cfop_entrada=cfop[0],
                cfop_saida=cfop[1],
                tributacao_monofasica=0,
                tributo_icms=first["icms_basis"],
                tributo_pis_cofins=PIS_COFINS_BASIS,
                evidencias=first["evidence"],
                confidence=confidence,
                fiscal_risk=RISK_ASSUMED if confidence != CONFIDENCE_HIGH else None,
                requires_accountant_review=confidence != CONFIDENCE_HIGH,
                onda=WAVE_BY_LEVEL[LEVEL_SPECIAL] if special else WAVE_BY_LEVEL[level],
            )
            profile.produtos = [item["produto"] for item in cluster]
            profiles[profile_id] = profile

    # --- Canario ---------------------------------------------------------------------
    checkpoint_by_reference = verified_bases(checkpoint)

    for profile in profiles.values():
        satisfied = None
        for ncm in profile.ncms:
            for cest in profile.cests or [""]:
                found = checkpoint_by_reference.get((ncm, cest, str(profile.referencia_icms or "")))
                if found:
                    satisfied = found
                    break
            if satisfied:
                break
        if satisfied:
            profile.profile_canary_status = "VERIFIED"
            profile.canario_ean = satisfied["ean"]
            profile.canario_produto_codigo = satisfied.get("codProduto")
            profile.canario_origem = "PRODUTO_JA_CRIADO_E_VERIFICADO_COM_BASE_IDENTICA"
        else:
            profile.produtos.sort(key=lambda p: p["precoVenda"])
            profile.canario_ean = profile.produtos[0]["ean"] if profile.produtos else None
            profile.profile_canary_status = "PENDING"
            profile.canario_origem = "MENOR_PRECO_DE_VENDA_DO_PERFIL"

    ordered = sorted(
        profiles.values(), key=lambda p: (p.onda, p.level, -p.candidatos, p.profile_id)
    )

    print("PERFIS POR ONDA")
    for wave in (1, 2, 4):
        wave_profiles = [p for p in ordered if p.onda == wave]
        if not wave_profiles:
            continue
        total = sum(p.candidatos for p in wave_profiles)
        print(f"   ONDA {wave}: {len(wave_profiles)} perfis | {total} produtos")
        for profile in wave_profiles:
            print(f"      {profile.profile_id}")
            print(f"         nivel {profile.level} | {profile.candidatos} produto(s) | "
                  f"canario {profile.profile_canary_status} | confianca {profile.confidence}")
            print(f"         {profile.descricao}")
            evidence = profile.evidencias
            if evidence.get("origem") == "ANALOGIA_NCM_CEST":
                print(f"         evidencia: {evidence['itens']} itens | "
                      f"{evidence['notasDistintas']} notas | "
                      f"{evidence['fornecedoresDistintos']} fornecedores")
            elif evidence.get("origem") == "NF_E_DO_PRODUTO":
                print(f"         evidencia: NF-e {evidence['nfe']} | CST {evidence['cstEntrada']}")
            else:
                print("         evidencia: tabela local pelo CEST da planilha")
        print()

    print("BLOQUEADOS")
    for reason, count in sorted(blocked_counts.items(), key=lambda kv: -kv[1]):
        print(f"   {reason:42} {count:>4}")
    print()

    payload = {
        "title": "PERFIS FISCAIS — 118508",
        "generatedAt": generated_at,
        "sheet": SHEET.name,
        "empresa": COMPANY_CODE,
        "centroCusto": COST_CENTER,
        "credential": {"variable": credential.variable_name, "keyExposed": False},
        "referencias": {"icmsSt": st_reference, "pisCofins": pis_reference},
        "criterios": {
            "analogiaForte": {"notas": 3, "fornecedores": 2},
            "analogiaReduzida": "uma ou duas notas, ou fornecedor unico, sem concorrencia",
            "fracaoMinimaMesmaFamilia": 0.7,
            "familiaNuncaAtravessada": True,
        },
        "totais": {
            "planilha": len(rows),
            "emPerfis": sum(p.candidatos for p in ordered),
            "bloqueados": len(blocked),
            "perfis": len(ordered),
        },
        "profiles": [p.to_dict() for p in ordered],
        "blocked": blocked,
        "blockedCounts": dict(blocked_counts),
        "apiWrites": 0,
    }
    PROFILES_OUT.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    BARCODES_OUT.write_text(
        json.dumps(
            {
                "title": "CODIGOS DE BARRAS ADICIONAIS PENDENTES — 118508",
                "generatedAt": generated_at,
                "observacao": (
                    "Produto ja existe no catalogo com outro codigo de barras. Nao criar "
                    "produto novo. A inclusao do codigo adicional exige operacao propria."
                ),
                "quantidade": len(barcode_queue),
                "itens": barcode_queue,
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )

    print("=" * 78)
    print(f"perfis: {len(ordered)} | produtos em perfil: {sum(p.candidatos for p in ordered)}"
          f" | bloqueados: {len(blocked)}")
    print(f"fila de codigo de barras adicional: {len(barcode_queue)}")
    print("API WRITES: 0")
    print(f"artefatos: {PROFILES_OUT.name}, {BARCODES_OUT.name}")


if __name__ == "__main__":
    main()
