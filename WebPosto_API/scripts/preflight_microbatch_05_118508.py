"""Pre-flight do microbatch 05 da empresa 118508 (somente leitura, ate 5 produtos).

Prioridade: custo apurado em NF-e com unidade convertida com seguranca, depois custo
apurado sem conflito fiscal, depois custo pendente com evidencia fiscal consistente.

Para custo pendente, a analogia por NCM e CEST exige NCM e CEST exatos, no minimo tres
notas e dois fornecedores distintos, mesma familia comercial, tratamento convergente e
nenhuma nota indicando tratamento concorrente.

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
    find_description_duplicates,
)
from src.operational.product_registration.entry_evidence_index import (  # noqa: E402
    build_ncm_cest_evidence,
    item_entry_evidence,
    summarize_evidence,
)
from src.operational.product_registration.fiscal_resolver import (  # noqa: E402
    ST_PROVEN,
    EntryEvidence,
    FiscalResolver,
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
BATCH_SIZE = 5

SHEET = ROOT / "data" / "product_registration" / "FISCAL_PRODUTOS_A_CADASTRAR_118508.xlsx"
TAX_INPUT = ROOT / "data" / "product_registration" / "tax_tables_input"
OUT_DIR = ROOT / "data" / "product_registration" / "microbatch_05_118508"
OUT_DIR.mkdir(parents=True, exist_ok=True)
CHECKPOINT = ROOT / "data" / "product_registration" / "execution" / "checkpoint_118508.json"

PERMANENT_EXCLUSIONS = {"7891000376928", "7891962076317"}

SENSITIVE_NCM_CHAPTERS = {
    "22": "BEBIDA_ALCOOLICA",
    "24": "TABACO",
    "30": "FARMACO",
    "27": "COMBUSTIVEL",
    "36": "PIROTECNICO",
}

MIN_SUPPORTING_ITEMS = 3
MIN_SUPPORTING_INVOICES = 3
MIN_SUPPORTING_SUPPLIERS = 2
# Fracao minima dos itens de evidencia que precisa ser da familia comercial do candidato.
MIN_FAMILY_SHARE = 0.7
IMPLAUSIBLE_MARGIN_FACTOR = 8.0

COST_DFE = "DFE"
COST_PENDING = "PENDING_DFE"

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


def build_body(row, *, cost: float, decision, cfop: tuple[str, str]) -> dict[str, Any]:
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
        "tributoIcms": decision.icms_basis,
        "tributoPisCofins": decision.pis_cofins_basis,
    }


def evidence_verdict(
    summary: dict[str, Any], entries: list[dict[str, Any]], candidate_family: str | None
) -> tuple[bool, str]:
    """Aprova ou recusa a analogia por NCM e CEST, com o motivo da recusa."""
    if summary["itens"] < MIN_SUPPORTING_ITEMS:
        return False, "EVIDENCIA_NCM_CEST_INSUFICIENTE"
    if summary["classificacoes"] != [ST_PROVEN]:
        return False, "BASES_CONCORRENTES"
    if summary["notasDistintas"] < MIN_SUPPORTING_INVOICES:
        return False, "EVIDENCIA_CONCENTRADA_EM_POUCAS_NOTAS"
    if summary["fornecedoresDistintos"] < MIN_SUPPORTING_SUPPLIERS:
        return False, "EVIDENCIA_CONCENTRADA_EM_UM_FORNECEDOR"
    # Um unico CST divergente ja indica tratamento concorrente para a mesma mercadoria.
    if len([cst for cst in summary["distribuicaoCst"] if cst != "SEM_CST"]) > 1:
        return False, "CST_DIVERGENTE_NA_EVIDENCIA"
    if not candidate_family:
        return False, "FAMILIA_COMERCIAL_NAO_RECONHECIDA"
    same_family = sum(1 for e in entries if e.get("familiaComercial") == candidate_family)
    if same_family / len(entries) < MIN_FAMILY_SHARE:
        return False, "FAMILIA_COMERCIAL_DIVERGENTE"
    return True, "OK"


def main() -> None:
    generated_at = datetime.now(timezone.utc).isoformat()
    resolver = FiscalResolver()

    print("=" * 78)
    print("PRE-FLIGHT MICROBATCH 05 — EMPRESA 118508 (READ-ONLY)")
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
    print(f"indice DF-e: {len(dfe_index)} EANs | pares NCM+CEST: {len(evidence_by_ncm_cest)}")

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
    catalog_barcodes = {code for product in catalog for code in barcodes(product)}
    checkpoint = json.loads(CHECKPOINT.read_text(encoding="utf-8")) if CHECKPOINT.is_file() else {}
    print(f"catalogo: {len(catalog)} | vinculos: {len(linked_codes)} | checkpoint: {len(checkpoint)}")
    print()

    tier1: list[dict[str, Any]] = []
    tier3: list[dict[str, Any]] = []
    rejections: dict[str, int] = defaultdict(int)
    rejected_detail: list[dict[str, Any]] = []

    def reject(row, reason: str, detail: str | None = None) -> None:
        rejections[reason] += 1
        rejected_detail.append(
            {
                "linha": row.line,
                "ean": row.ean,
                "descricao": row.descricao,
                "motivo": reason,
                "detalhe": detail,
            }
        )

    for row in rows:
        if not row.ean_valid:
            reject(row, "GTIN_INVALIDO")
            continue
        ean = row.ean
        if ean in PERMANENT_EXCLUSIONS:
            reject(row, "EXCLUSAO_PERMANENTE")
            continue
        if ean in checkpoint:
            reject(row, "EM_CHECKPOINT", f"produto {checkpoint[ean].get('codProduto')}")
            continue
        if ean in catalog_barcodes:
            reject(row, "JA_NO_CATALOGO")
            continue
        if not row.has_price:
            reject(row, "SEM_PRECO")
            continue
        if not row.ncm or len(row.ncm) != 8:
            reject(row, "NCM_INVALIDO")
            continue
        if not row.has_cest:
            reject(row, "SEM_CEST")
            continue
        sensitive = SENSITIVE_NCM_CHAPTERS.get(row.ncm[:2])
        if sensitive:
            reject(row, "CATEGORIA_FISCAL_ESPECIAL", sensitive)
            continue
        blocked = resolver.check_blocked(row.descricao)
        if blocked:
            reject(row, "PALAVRA_BLOQUEADA", blocked)
            continue
        same_product = find_description_duplicates(row.descricao, catalog)
        if same_product:
            reject(
                row,
                "POSSIVEL_DUPLICIDADE",
                f"produto {same_product[0].get('produtoCodigo')} '{same_product[0].get('nome')}'",
            )
            continue

        candidate_family = commercial_family(row.descricao)
        hit = dfe_index.get(ean)

        if hit is not None:
            cost_evidence = cost_from_index(ean, dfe_index)
            item = (hit[2].get("normalized_json") or {})
            if not cost_evidence.resolved:
                reject(row, "CONVERSAO_EMBALAGEM_DESCONHECIDA", cost_evidence.reason)
                continue
            cost = float(cost_evidence.preco_custo)
            if cost > row.preco_venda:
                reject(row, "CUSTO_ACIMA_DA_VENDA", f"custo {cost} venda {row.preco_venda}")
                continue
            if cost > 0 and row.preco_venda / cost > IMPLAUSIBLE_MARGIN_FACTOR:
                reject(row, "MARGEM_IMPLAUSIVEL", f"custo {cost} venda {row.preco_venda}")
                continue
            ncm_nfe = str(item.get("ncm") or "").strip()
            cest_nfe = str(item.get("cest") or "").strip()
            if (ncm_nfe and ncm_nfe != row.ncm) or (cest_nfe and cest_nfe != row.cest):
                reject(
                    row,
                    "NCM_CEST_DIVERGENTE",
                    f"planilha {row.ncm}/{row.cest} nota {ncm_nfe}/{cest_nfe}",
                )
                continue

            evidence = item_entry_evidence(item, f"{cost_evidence.numero}/{cost_evidence.serie}")
            classification = classify_entry(evidence)
            taxed_basis = None
            taxed_reference = None
            entry_rate = (item.get("icms") or {}).get("ICMS.pICMS")
            if classification != ST_PROVEN and entry_rate is not None:
                rate = float(entry_rate)
                rate_status, rate_rows = match_icms_by_entry_rate(
                    icms_rows, cst_entrada="000", icms_entrada=rate, icms_saida=rate
                )
                if rate_status == MATCH_UNIQUE:
                    taxed_basis = basis_from_row(rate_rows[0])
                    taxed_reference = rate_rows[0].referencia
            decision = resolver.decide(
                evidence,
                substituted_basis=st_basis if classification == ST_PROVEN else None,
                substituted_table_reference=st_reference if classification == ST_PROVEN else None,
                taxed_basis=taxed_basis,
                taxed_table_reference=taxed_reference,
                pis_cofins_basis=PIS_COFINS_BASIS if pis_reference else None,
                pis_cofins_table_reference=pis_reference,
                equivalents_distribution={},
            )
            if not decision.can_register:
                reject(row, "EVIDENCIA_FISCAL_CONFLITANTE", "; ".join(decision.blockers))
                continue

            cfop = CFOP_SUBSTITUTED if classification == ST_PROVEN else CFOP_TAXED
            body = build_body(row, cost=cost, decision=decision, cfop=cfop)
            tier1.append(
                {
                    "prioridade": "1_CUSTO_DFE",
                    "linha": row.line,
                    "ean": ean,
                    "descricao": row.descricao,
                    "familiaComercial": candidate_family,
                    "precoVenda": row.preco_venda,
                    "ncm": row.ncm,
                    "cest": row.cest,
                    "inexistencia": {
                        "noCatalogoCompleto": False,
                        "vinculadoA118508": False,
                        "emCheckpoint": False,
                        "duplicidadePorDescricao": False,
                        "catalogoLido": len(catalog),
                        "vinculosLidos": len(linked_codes),
                    },
                    "custo": {
                        "valor": cost,
                        "source": COST_DFE,
                        "cost_status": "RESOLVED",
                        "requires_cost_update": False,
                        "unidadeComercial": cost_evidence.unidade_comercial,
                        "unidadeAtomica": cost_evidence.unidade_atomica,
                        "origemQuantidade": cost_evidence.quantidade_origem,
                        "observacaoConversao": cost_evidence.reason,
                        "quantidade": float(cost_evidence.quantidade or 0),
                        "calculo": cost_evidence.calculo,
                        "icmsStCobrado": float(cost_evidence.icms_st_cobrado or 0),
                        "nfe": {
                            "numero": cost_evidence.numero,
                            "serie": cost_evidence.serie,
                            "emissao": cost_evidence.emissao,
                            "fornecedor": cost_evidence.fornecedor,
                            "accessKeyMasked": cost_evidence.access_key_masked,
                            "protocoloCstat": cost_evidence.protocolo_cstat,
                        },
                    },
                    "baseFiscal": {
                        "classificacaoEntrada": classification,
                        "cstIcmsEntrada": evidence.cst_icms,
                        "aliquotaIcmsEntrada": entry_rate,
                        "icmsStRetido": evidence.icms_st_retido,
                        "icmsTableReference": decision.icms_table_reference,
                        "tributoIcms": decision.icms_basis,
                        "pisCofinsTableReference": decision.pis_cofins_table_reference,
                        "tributoPisCofins": decision.pis_cofins_basis,
                        "cfopEntrada": cfop[0],
                        "cfopSaida": cfop[1],
                        "confidence": decision.confidence,
                        "fiscalRisk": decision.fiscal_risk,
                        "requiresAccountantReview": decision.requires_accountant_review,
                        "camposInferidos": decision.inferred_fields,
                        "justificativa": decision.justification,
                    },
                    "body": {"ready": True, "hash": body_hash(body), "preview": body},
                    "categoria": "READY_HIGH_CONFIDENCE"
                    if decision.confidence == "HIGH"
                    else "READY_ASSUMED_RISK",
                }
            )
            continue

        entries = evidence_by_ncm_cest.get((row.ncm, row.cest)) or []
        if not entries:
            reject(row, "SEM_EVIDENCIA_NCM_CEST")
            continue
        summary = summarize_evidence(entries)
        approved, verdict = evidence_verdict(summary, entries, candidate_family)
        if not approved:
            reject(
                row,
                verdict,
                f"{summary['itens']} itens, {summary['notasDistintas']} notas, "
                f"{summary['fornecedoresDistintos']} fornecedores, "
                f"familias {list(summary['familiasObservadas'])[:3]}",
            )
            continue
        if st_basis is None or st_reference is None:
            reject(row, "SEM_TABELA_ST")
            continue

        evidence = EntryEvidence(
            cst_icms=None, icms_st_retido=None, cest=row.cest, ncm=row.ncm, invoice_reference=None
        )
        decision = resolver.decide(
            evidence,
            no_evidence_candidates=[(st_reference, st_basis)],
            pis_cofins_basis=PIS_COFINS_BASIS if pis_reference else None,
            pis_cofins_table_reference=pis_reference,
        )
        if not decision.can_register:
            reject(row, "EVIDENCIA_FISCAL_CONFLITANTE", "; ".join(decision.blockers))
            continue
        if decision.confidence != "LOW":
            reject(row, "CONFIANCA_INESPERADA_SEM_NOTA_PROPRIA", decision.confidence)
            continue

        body = build_body(row, cost=0, decision=decision, cfop=CFOP_SUBSTITUTED)
        tier3.append(
            {
                "prioridade": "3_PENDING_DFE",
                "linha": row.line,
                "ean": ean,
                "descricao": row.descricao,
                "familiaComercial": candidate_family,
                "precoVenda": row.preco_venda,
                "ncm": row.ncm,
                "cest": row.cest,
                "inexistencia": {
                    "noCatalogoCompleto": False,
                    "vinculadoA118508": False,
                    "emCheckpoint": False,
                    "duplicidadePorDescricao": False,
                    "catalogoLido": len(catalog),
                    "vinculosLidos": len(linked_codes),
                },
                "custo": {
                    "valor": 0,
                    "source": COST_PENDING,
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
                    "cfopEntrada": CFOP_SUBSTITUTED[0],
                    "cfopSaida": CFOP_SUBSTITUTED[1],
                    "confidence": decision.confidence,
                    "fiscalRisk": decision.fiscal_risk,
                    "requiresAccountantReview": decision.requires_accountant_review,
                    "camposInferidos": decision.inferred_fields,
                    "justificativa": decision.justification,
                    "evidenciaNcmCest": {
                        **summary,
                        "familiaCandidato": candidate_family,
                        "amostra": [
                            {
                                "descricao": e.get("descricao"),
                                "familiaComercial": e.get("familiaComercial"),
                                "cstIcms": e.get("cstIcms"),
                                "nfe": e.get("nfe"),
                                "fornecedor": e.get("fornecedor"),
                                "fornecedorCnpjMascarado": e.get("fornecedorCnpjMascarado"),
                            }
                            for e in entries[:10]
                        ],
                    },
                },
                "body": {"ready": True, "hash": body_hash(body), "preview": body},
                "categoria": "READY_ASSUMED_RISK",
            }
        )

    # Dentro do custo apurado, unidade atomica e base comprovada vem primeiro.
    tier1.sort(
        key=lambda c: (
            0 if c["custo"]["unidadeAtomica"] else 1,
            0 if c["baseFiscal"]["classificacaoEntrada"] == ST_PROVEN else 1,
            c["precoVenda"],
        )
    )
    tier3.sort(
        key=lambda c: (
            -c["baseFiscal"]["evidenciaNcmCest"]["fornecedoresDistintos"],
            -c["baseFiscal"]["evidenciaNcmCest"]["notasDistintas"],
            c["precoVenda"],
        )
    )
    selection = (tier1 + tier3)[:BATCH_SIZE]
    pending_selected = sum(1 for s in selection if s["prioridade"] == "3_PENDING_DFE")

    print("MOTIVOS DE EXCLUSAO")
    for reason, count in sorted(rejections.items(), key=lambda kv: -kv[1]):
        print(f"   {reason:42} {count:>4}")
    print(f"   {'ELEGIVEIS COM CUSTO DF-e':42} {len(tier1):>4}")
    print(f"   {'ELEGIVEIS PENDING_DFE':42} {len(tier3):>4}")
    print()

    print(f"MICROBATCH SELECIONADO: {len(selection)} de {BATCH_SIZE} "
          f"({len(selection) - pending_selected} com custo DF-e, {pending_selected} pendentes)")
    print()
    for index, item in enumerate(selection, start=1):
        basis = item["baseFiscal"]
        cost = item["custo"]
        print(f"--- {index}. {item['descricao']}")
        print(f"    prioridade {item['prioridade']} | linha {item['linha']} | EAN {item['ean']}"
              f" | familia {item['familiaComercial']}")
        print(f"    venda R$ {item['precoVenda']} | NCM {item['ncm']} | CEST {item['cest']}")
        if cost["source"] == COST_DFE:
            nfe = cost["nfe"]
            print(f"    custo R$ {cost['valor']} | unidade {cost['unidadeComercial']}"
                  f" | quantidade {cost['quantidade']} obtida de {cost['origemQuantidade']}")
            if cost["observacaoConversao"]:
                print(f"    conversao: {cost['observacaoConversao']}")
            print(f"    calculo: {cost['calculo']}")
            print(f"    NF-e {nfe['numero']}/{nfe['serie']} de {nfe['emissao']} | {nfe['fornecedor']}"
                  f" | cStat {nfe['protocoloCstat']} | chave {nfe['accessKeyMasked']}")
        else:
            ev = basis["evidenciaNcmCest"]
            print(f"    custo R$ 0 ({cost['cost_status']}, {cost['source']})")
            print(f"    evidencia: {ev['itens']} itens | {ev['notasDistintas']} notas | "
                  f"{ev['fornecedoresDistintos']} fornecedores | CST {ev['distribuicaoCst']}")
            print(f"    ST retida em {ev['itensComStRetida']} itens | ST cobrada em "
                  f"{ev['itensComStCobrada']} itens | familias {ev['familiasObservadas']}")
            for sample in ev["amostra"][:4]:
                print(f"       - {(sample['descricao'] or '')[:42]} | CST {sample['cstIcms']}"
                      f" | NF {sample['nfe']} | {(sample['fornecedor'] or '')[:24]}")
        print(f"    entrada {basis['classificacaoEntrada']} | ICMS tabela {basis['icmsTableReference']}"
              f" | PIS/COFINS tabela {basis['pisCofinsTableReference']}")
        print(f"    CFOP {basis['cfopEntrada']}/{basis['cfopSaida']} | confianca {basis['confidence']}"
              f" | risco {basis['fiscalRisk']} | revisao {basis['requiresAccountantReview']}")
        print(f"    hash {item['body']['hash'][:32]}...")
        print()

    payload = {
        "title": "PREFLIGHT MICROBATCH 05 — 118508",
        "generatedAt": generated_at,
        "sheet": SHEET.name,
        "empresa": COMPANY_CODE,
        "centroCusto": COST_CENTER,
        "credential": {
            "variable": credential.variable_name,
            "keyExposed": False,
            "sentinelFound": guard.sentinel_found,
            "sentinelCompanyLinkConfirmed": guard.company_link_confirmed,
        },
        "criteriosEvidenciaPendente": {
            "minItens": MIN_SUPPORTING_ITEMS,
            "minNotas": MIN_SUPPORTING_INVOICES,
            "minFornecedores": MIN_SUPPORTING_SUPPLIERS,
            "fracaoMinimaMesmaFamilia": MIN_FAMILY_SHARE,
            "cstUnicoObrigatorio": True,
        },
        "batchSize": BATCH_SIZE,
        "eligibleWithCost": len(tier1),
        "eligiblePending": len(tier3),
        "selectedWithCost": len(selection) - pending_selected,
        "selectedPending": pending_selected,
        "pendingCostFlagRequired": bool(pending_selected),
        "requiredFlag": "ALLOW_PENDING_DFE_COST=true" if pending_selected else None,
        "rejections": dict(rejections),
        "rejectedDetail": rejected_detail,
        "products": selection,
        "apiWrites": 0,
        "status": "READY_FOR_WRITE" if selection else "NOTHING_TO_WRITE",
    }
    (OUT_DIR / "microbatch_selection.json").write_text(
        json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8"
    )

    print("=" * 78)
    print(f"STATUS: {payload['status']}")
    if pending_selected:
        print(f"ATENCAO: {pending_selected} produto(s) com custo pendente exigem "
              f"ALLOW_PENDING_DFE_COST=true na execucao")
    print("API WRITES: 0")
    print(f"artefato: {OUT_DIR / 'microbatch_selection.json'}")


if __name__ == "__main__":
    main()
