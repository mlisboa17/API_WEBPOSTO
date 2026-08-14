"""Pre-flight do piloto unico sem custo DF-e (empresa 118508, somente leitura).

Seleciona UM produto da planilha que nao tem NF-e de entrada, para destravar a fila de
PENDING_DFE com risco controlado. Custo vai zero e declarado como pendente.

Sem compra registrada nao ha como provar substituicao pelo proprio produto. A base de
ICMS e sustentada pela convergencia de tributacao entre itens de NF-e autorizadas que
compartilham NCM e CEST exatos com o candidato: o CEST e o codigo que identifica a
mercadoria no regime de ST, portanto itens de mesmo NCM e CEST recebem o mesmo
tratamento. Divergencia entre esses itens bloqueia o produto.

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

from src.operational.dfe import store  # noqa: E402
from src.operational.product_registration.company_credentials import (  # noqa: E402
    HttpProductReader,
    company_guard,
    resolve_credential,
)
from src.operational.product_registration.dfe_cost_resolver import (  # noqa: E402
    build_authorized_index,
)
from src.operational.product_registration.fiscal_resolver import (  # noqa: E402
    ST_PROVEN,
    EntryEvidence,
    FiscalResolver,
    classify_entry,
)
from src.operational.product_registration.fiscal_sheet_loader import load_sheet  # noqa: E402
from src.operational.product_registration.tax_table_matcher import (  # noqa: E402
    MATCH_UNIQUE,
    basis_from_row,
    load_icms_table,
    load_pis_cofins_table,
    match_icms,
    match_pis_cofins,
)

BASE_URL = "https://web.qualityautomacao.com.br"
COMPANY_CODE = 118508
PROFILE = "WEBPOSTO_CONVENIENCIA_24_HORAS_KEY"
GRUPO_CODIGO = 55446
COST_CENTER = 24886

SHEET = ROOT / "data" / "product_registration" / "FISCAL_PRODUTOS_A_CADASTRAR_118508.xlsx"
TAX_INPUT = ROOT / "data" / "product_registration" / "tax_tables_input"
OUT_DIR = ROOT / "data" / "product_registration" / "microbatch_03_118508"
OUT_DIR.mkdir(parents=True, exist_ok=True)
CHECKPOINT = ROOT / "data" / "product_registration" / "execution" / "checkpoint_118508.json"

PERMANENT_EXCLUSIONS = {
    "7891000376928",
    "7891000377130",
    "7891962076317",
    "7896336000578",
    "7892840817978",
    "7892840824655",
    "7892840824396",
    "7896104993927",
    "7891079001011",
    "7891079001004",
}

# Capitulos de NCM com regime proprio ficam fora de cadastro automatico.
SENSITIVE_NCM_CHAPTERS = {
    "22": "BEBIDA_ALCOOLICA",
    "24": "TABACO",
    "30": "FARMACO",
    "27": "COMBUSTIVEL",
    "36": "PIROTECNICO",
}

# Minimo de itens de NF-e com o mesmo NCM e CEST para a base ser considerada sustentada.
MIN_SUPPORTING_ITEMS = 3

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


def paginate(client: httpx.Client, path: str, key: str, page_size: int = 200) -> list[dict[str, Any]]:
    collected: list[dict[str, Any]] = []
    cursor = 0
    seen: set[int] = set()
    for _ in range(400):
        params: dict[str, Any] = {"CHAVE": key, "tamanhoPagina": page_size}
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


def build_ncm_cest_evidence(company_code: int) -> dict[tuple[str, str], list[dict[str, Any]]]:
    """Agrupa itens de NF-e autorizadas por (NCM, CEST) com a classificacao da entrada."""
    grouped: dict[tuple[str, str], list[dict[str, Any]]] = defaultdict(list)
    for document in store.list_documents(company_code):
        protocol = document.get("protocol") or {}
        if protocol.get("cancelled") is True or str(protocol.get("cStat") or "") != "100":
            continue
        for raw_item in store.load_items(document["id"]):
            item = raw_item.get("normalized_json") or {}
            ncm = str(item.get("ncm") or "").strip()
            cest = str(item.get("cest") or "").strip()
            if not ncm or not cest:
                continue
            icms = item.get("icms") or {}
            st_retido = icms.get("ICMS.vICMSSTRet")
            evidence = EntryEvidence(
                cst_icms=icms.get("ICMS.CST"),
                icms_st_retido=float(st_retido) if st_retido else None,
                cest=cest,
                ncm=ncm,
                invoice_reference=f"{document.get('nNF')}/{document.get('serie')}",
            )
            grouped[(ncm, cest)].append(
                {
                    "classification": classify_entry(evidence),
                    "cstIcms": icms.get("ICMS.CST"),
                    "aliquotaEntrada": icms.get("ICMS.pICMS"),
                    "descricao": item.get("x_prod"),
                    "nfe": evidence.invoice_reference,
                    "ean": item.get("c_ean"),
                }
            )
    return grouped


def body_hash(body: dict[str, Any]) -> str:
    payload = json.dumps(body, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def main() -> None:
    generated_at = datetime.now(timezone.utc).isoformat()
    resolver = FiscalResolver()

    print("=" * 78)
    print("PRE-FLIGHT PILOTO SEM CUSTO DF-e — EMPRESA 118508 (READ-ONLY)")
    print("=" * 78)

    rows = load_sheet(SHEET)
    credential = resolve_credential(COMPANY_CODE)
    if credential.variable_name != PROFILE:
        raise SystemExit(f"credencial fora do profile exigido: {credential.variable_name}")
    print(f"planilha: {len(rows)} produtos | credencial: {credential.variable_name} (nunca impressa)")

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

    dfe_index = build_authorized_index(COMPANY_CODE)
    evidence_by_ncm_cest = build_ncm_cest_evidence(COMPANY_CODE)
    print(
        f"indice DF-e: {len(dfe_index)} EANs | pares NCM+CEST com evidencia: "
        f"{len(evidence_by_ncm_cest)}"
    )

    with httpx.Client(timeout=120.0) as client:
        guard = company_guard(credential, HttpProductReader(client))
        if not guard.passed:
            raise SystemExit("sentinel BONO nao confirmado na empresa 118508")
        print(f"sentinel BONO: encontrado={guard.sentinel_found} vinculo={guard.company_link_confirmed}")
        catalog = paginate(client, "/INTEGRACAO/PRODUTO", credential.key)
        links = paginate(client, "/INTEGRACAO/PRODUTO_EMPRESA", credential.key)

    linked_codes = {
        int(link.get("produtoCodigo") or 0)
        for link in links
        if int(link.get("empresaCodigo") or 0) == COMPANY_CODE
    }
    catalog_by_barcode: dict[str, dict[str, Any]] = {}
    for product in catalog:
        for code in barcodes(product):
            catalog_by_barcode.setdefault(code, product)
    checkpoint = json.loads(CHECKPOINT.read_text(encoding="utf-8")) if CHECKPOINT.is_file() else {}
    print(f"catalogo: {len(catalog)} | vinculos: {len(linked_codes)} | checkpoint: {len(checkpoint)}")
    print()

    candidates: list[dict[str, Any]] = []
    rejections: dict[str, int] = defaultdict(int)

    for row in rows:
        def reject(reason: str) -> None:
            rejections[reason] += 1

        if not row.ean_valid:
            reject("GTIN_INVALIDO")
            continue
        ean = row.ean
        if ean in PERMANENT_EXCLUSIONS:
            reject("EXCLUSAO_PERMANENTE")
            continue
        if ean in checkpoint:
            reject("EM_CHECKPOINT")
            continue
        existing = catalog_by_barcode.get(ean)
        if existing:
            reject("JA_NO_CATALOGO")
            continue
        if not row.has_price:
            reject("SEM_PRECO")
            continue
        if not row.ncm or len(row.ncm) != 8:
            reject("NCM_INVALIDO")
            continue
        if not row.has_cest:
            reject("SEM_CEST")
            continue
        # O piloto existe para destravar produtos sem custo: com NF-e, segue o fluxo normal.
        if ean in dfe_index:
            reject("TEM_CUSTO_DFE")
            continue
        sensitive = SENSITIVE_NCM_CHAPTERS.get(row.ncm[:2])
        if sensitive:
            reject(f"CATEGORIA_SENSIVEL_{sensitive}")
            continue
        blocked = resolver.check_blocked(row.descricao)
        if blocked:
            reject(blocked)
            continue

        supporting = evidence_by_ncm_cest.get((row.ncm, row.cest)) or []
        if len(supporting) < MIN_SUPPORTING_ITEMS:
            reject("EVIDENCIA_NCM_CEST_INSUFICIENTE")
            continue

        classifications = {item["classification"] for item in supporting}
        if classifications != {ST_PROVEN}:
            # Itens do mesmo NCM+CEST com tratamentos diferentes: mais de uma base
            # plausivel, portanto o produto nao entra no piloto.
            reject("EVIDENCIA_NCM_CEST_DIVERGENTE")
            continue
        if st_basis is None or st_reference is None:
            reject("SEM_TABELA_ST")
            continue

        evidence = EntryEvidence(
            cst_icms=None,
            icms_st_retido=None,
            cest=row.cest,
            ncm=row.ncm,
            invoice_reference=None,
        )
        decision = resolver.decide(
            evidence,
            no_evidence_candidates=[(st_reference, st_basis)],
            pis_cofins_basis=PIS_COFINS_BASIS if pis_reference else None,
            pis_cofins_table_reference=pis_reference,
        )
        if not decision.can_register:
            reject("DECISAO_FISCAL_BLOQUEADA")
            continue

        body = {
            "descricao": row.descricao,
            "descricaoResumida": row.descricao[:32].strip(),
            "tipoProduto": "P",
            "grupoCodigo": GRUPO_CODIGO,
            "codigoExterno": ean,
            "unidadeCompra": "UN",
            "unidadeVenda": "UN",
            "iat": "A",
            "ippt": "T",
            "precoCompra": 0,
            "precoCusto": 0,
            "precoVenda": row.preco_venda,
            "centroCustoCodigo": COST_CENTER,
            "codigoBarras": ean,
            "codigoNcm": row.ncm,
            "codigoCest": row.cest,
            "ativo": True,
            "permiteVendaEstoqueNegativo": False,
            "produtoVendeFracionado": False,
            "utilizaCodigoBarras": True,
            "utilizaBalanca": False,
            "cdCfopEntrada": "1.102",
            "cdCfopSaida": "5.405",
            "Tributação Monofásica": 0,
            "tributoIcms": decision.icms_basis,
            "tributoPisCofins": decision.pis_cofins_basis,
        }

        candidates.append(
            {
                "linha": row.line,
                "ean": ean,
                "descricao": row.descricao,
                "precoVenda": row.preco_venda,
                "ncm": row.ncm,
                "cest": row.cest,
                "inexistencia": {
                    "noCatalogoCompleto": False,
                    "vinculadoA118508": False,
                    "emCheckpoint": False,
                    "catalogoLido": len(catalog),
                    "vinculosLidos": len(linked_codes),
                },
                "custo": {
                    "valor": 0,
                    "source": "PENDING_DFE",
                    "cost_status": "PENDING",
                    "cost_risk": "ASSUMED_BY_OWNER",
                    "requires_cost_update": True,
                    "motivoRevisao": "Nenhuma NF-e autorizada da empresa contem este EAN",
                    "nfe": None,
                },
                "baseFiscal": {
                    "classificacaoEntrada": decision.st_classification,
                    "cstIcmsEntrada": None,
                    "aliquotaIcmsEntrada": None,
                    "icmsStRetido": None,
                    "icmsTableReference": decision.icms_table_reference,
                    "tributoIcms": decision.icms_basis,
                    "pisCofinsTableReference": decision.pis_cofins_table_reference,
                    "tributoPisCofins": decision.pis_cofins_basis,
                    "cfopEntrada": "1.102",
                    "cfopSaida": "5.405",
                    "confidence": decision.confidence,
                    "fiscalRisk": decision.fiscal_risk,
                    "requiresAccountantReview": decision.requires_accountant_review,
                    "camposInferidos": decision.inferred_fields,
                    "justificativa": decision.justification,
                    "blockers": decision.blockers,
                    "evidenciaNcmCest": {
                        "itens": len(supporting),
                        "classificacoes": sorted(classifications),
                        "amostra": supporting[:8],
                    },
                },
                "body": {"ready": True, "hash": body_hash(body), "preview": body},
                "categoria": "READY_ASSUMED_RISK",
            }
        )

    # Maior sustentacao documental primeiro; entre iguais, o de menor valor.
    candidates.sort(
        key=lambda c: (-c["baseFiscal"]["evidenciaNcmCest"]["itens"], c["precoVenda"])
    )
    selection = candidates[:1]

    print("MOTIVOS DE EXCLUSAO")
    for reason, count in sorted(rejections.items(), key=lambda kv: -kv[1]):
        print(f"   {reason:38} {count:>4}")
    print(f"   {'CANDIDATOS APROVADOS':38} {len(candidates):>4}")
    print()

    print("CANDIDATOS APROVADOS, POR SUSTENTACAO")
    for item in candidates:
        support = item["baseFiscal"]["evidenciaNcmCest"]
        print(
            f"   {support['itens']:>3} itens | NCM {item['ncm']} CEST {item['cest']}"
            f" | R$ {item['precoVenda']:>7} | {item['descricao'][:44]}"
        )
    print()

    if not selection:
        print("Nenhum produto elegivel para o piloto.")
    for item in selection:
        basis = item["baseFiscal"]
        support = basis["evidenciaNcmCest"]
        print("PRODUTO SELECIONADO")
        print(f"   linha {item['linha']} | EAN {item['ean']}")
        print(f"   {item['descricao']}")
        print(f"   preco de venda R$ {item['precoVenda']} | NCM {item['ncm']} | CEST {item['cest']}")
        print(f"   custo: {item['custo']['valor']} ({item['custo']['cost_status']}, {item['custo']['source']})")
        print(f"   base ICMS: tabela {basis['icmsTableReference']} | saida CST "
              f"{basis['tributoIcms']['cstSaida']} | aliquota {basis['tributoIcms']['percentualIcmsSaida']}%")
        print(f"   PIS/COFINS: tabela {basis['pisCofinsTableReference']}")
        print(f"   CFOP {basis['cfopEntrada']}/{basis['cfopSaida']}")
        print(f"   sustentacao: {support['itens']} itens de NF-e com mesmo NCM+CEST, "
              f"todos {support['classificacoes']}")
        for sample in support["amostra"]:
            print(f"      - {sample['descricao'][:44]} | CST {sample['cstIcms']} | NF {sample['nfe']}")
        print(f"   confianca {basis['confidence']} | risco {basis['fiscalRisk']} | "
              f"revisao contabil {basis['requiresAccountantReview']}")
        print(f"   campos inferidos: {basis['camposInferidos']}")
        print(f"   hash do body: {item['body']['hash']}")
        print()
        print("   RISCOS ASSUMIDOS:")
        print("      1. Custo zero: margem e CMV ficam distorcidos ate a primeira compra entrar.")
        print("      2. Base de ICMS inferida por NCM+CEST, sem NF-e do proprio produto.")
        print("      3. Correcao posterior de custo depende de PUT, hoje proibido.")
        print("      4. CFOP de saida 5.405 pressupoe mercadoria substituida.")
        print()

    payload = {
        "title": "PREFLIGHT PILOTO SEM CUSTO DF-e — 118508",
        "generatedAt": generated_at,
        "sheet": SHEET.name,
        "empresa": COMPANY_CODE,
        "credential": {
            "variable": credential.variable_name,
            "keyExposed": False,
            "sentinelFound": guard.sentinel_found,
            "sentinelCompanyLinkConfirmed": guard.company_link_confirmed,
        },
        "costPolicy": {
            "precoCompra": 0,
            "precoCusto": 0,
            "cost_source": "PENDING_DFE",
            "cost_status": "PENDING",
            "cost_risk": "ASSUMED_BY_OWNER",
            "requires_cost_update": True,
            "requiredFlag": "ALLOW_PENDING_DFE_COST=true",
        },
        "minSupportingItems": MIN_SUPPORTING_ITEMS,
        "rejections": dict(rejections),
        "candidates": len(candidates),
        "products": selection,
        "apiWrites": 0,
        "status": "READY_FOR_WRITE" if selection else "NOTHING_TO_WRITE",
    }
    (OUT_DIR / "pilot_selection.json").write_text(
        json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8"
    )

    print("=" * 78)
    print(f"STATUS: {payload['status']}")
    print("API WRITES: 0")
    print(f"artefato: {OUT_DIR / 'pilot_selection.json'}")


if __name__ == "__main__":
    main()
