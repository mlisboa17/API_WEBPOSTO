"""Pre-flight do microbatch 04 da empresa 118508 (somente leitura, ate 5 produtos).

Prioridade obrigatoria: primeiro produtos com custo apurado em NF-e; o lote so e
completado com produtos sem custo (PENDING_DFE) se nao houver cinco com custo e base
fiscal utilizavel.

Bloqueia embalagem sem fator de conversao, divergencia de NCM ou CEST, categorias de
regime proprio e qualquer produto com mais de uma base fiscal plausivel.

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
OUT_DIR = ROOT / "data" / "product_registration" / "microbatch_04_118508"
OUT_DIR.mkdir(parents=True, exist_ok=True)
CHECKPOINT = ROOT / "data" / "product_registration" / "execution" / "checkpoint_118508.json"

# BONO (sentinela) e o produto do incidente nunca entram em lote.
PERMANENT_EXCLUSIONS = {"7891000376928", "7891962076317"}

SENSITIVE_NCM_CHAPTERS = {
    "22": "BEBIDA_ALCOOLICA",
    "24": "TABACO",
    "30": "FARMACO",
    "27": "COMBUSTIVEL",
    "36": "PIROTECNICO",
}

MIN_SUPPORTING_ITEMS = 3
# Evidencia concentrada em uma ou duas notas pode refletir a pratica de um unico
# fornecedor, e nao o regime da mercadoria. Exigir notas distintas torna a analogia
# independente de quem vendeu.
MIN_SUPPORTING_INVOICES = 3
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


def body_hash(body: dict[str, Any]) -> str:
    payload = json.dumps(body, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def build_body(row, *, cost: float, ncm: str, cest: str, decision, cfop: tuple[str, str]) -> dict[str, Any]:
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
        "codigoNcm": ncm,
        "codigoCest": cest,
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


def main() -> None:
    generated_at = datetime.now(timezone.utc).isoformat()
    resolver = FiscalResolver()

    print("=" * 78)
    print("PRE-FLIGHT MICROBATCH 04 — EMPRESA 118508 (READ-ONLY)")
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
    catalog_by_barcode: dict[str, dict[str, Any]] = {}
    for product in catalog:
        for code in barcodes(product):
            catalog_by_barcode.setdefault(code, product)
    checkpoint = json.loads(CHECKPOINT.read_text(encoding="utf-8")) if CHECKPOINT.is_file() else {}
    print(f"catalogo: {len(catalog)} | vinculos: {len(linked_codes)} | checkpoint: {len(checkpoint)}")
    print()

    with_cost: list[dict[str, Any]] = []
    pending: list[dict[str, Any]] = []
    rejections: dict[str, int] = defaultdict(int)
    duplicate_notes: list[dict[str, Any]] = []

    for row in rows:
        if not row.ean_valid:
            rejections["GTIN_INVALIDO"] += 1
            continue
        ean = row.ean
        if ean in PERMANENT_EXCLUSIONS:
            rejections["EXCLUSAO_PERMANENTE"] += 1
            continue
        if ean in checkpoint:
            rejections["EM_CHECKPOINT"] += 1
            continue
        if ean in catalog_by_barcode:
            rejections["JA_NO_CATALOGO"] += 1
            continue
        # Fabricante que troca o GTIN cria um produto novo aos olhos do EAN, mas o item
        # ja existe no catalogo: cadastrar dividiria estoque e historico.
        same_product = find_description_duplicates(row.descricao, catalog)
        if same_product:
            rejections["POSSIVEL_DUPLICATA_POR_DESCRICAO"] += 1
            duplicate_notes.append(
                {
                    "linha": row.line,
                    "ean": ean,
                    "descricao": row.descricao,
                    "jaCadastrado": [
                        {
                            "produtoCodigo": p.get("produtoCodigo"),
                            "nome": p.get("nome"),
                            "ncm": p.get("ncm"),
                            "cest": p.get("cest"),
                            "codigosBarra": sorted(barcodes(p)),
                        }
                        for p in same_product[:3]
                    ],
                    "acaoNecessaria": (
                        "Avaliar inclusao do novo codigo de barras no produto existente. "
                        "Alterar cadastro existente exige operacao de escrita hoje proibida."
                    ),
                }
            )
            continue
        if not row.has_price:
            rejections["SEM_PRECO"] += 1
            continue
        if not row.ncm or len(row.ncm) != 8:
            rejections["NCM_INVALIDO"] += 1
            continue
        if not row.has_cest:
            rejections["SEM_CEST"] += 1
            continue
        sensitive = SENSITIVE_NCM_CHAPTERS.get(row.ncm[:2])
        if sensitive:
            rejections[f"CATEGORIA_SENSIVEL_{sensitive}"] += 1
            continue
        blocked = resolver.check_blocked(row.descricao)
        if blocked:
            rejections[blocked] += 1
            continue

        cost_evidence = cost_from_index(ean, dfe_index)
        hit = dfe_index.get(ean)
        item = (hit[2].get("normalized_json") if hit else None) or {}

        if hit is not None:
            # --- Caminho A: custo apurado na NF-e do proprio produto -------------
            if not cost_evidence.resolved:
                rejections["CONVERSAO_EMBALAGEM_PENDENTE"] += 1
                continue
            cost = float(cost_evidence.preco_custo)
            if cost > row.preco_venda:
                rejections["CUSTO_ACIMA_DA_VENDA"] += 1
                continue
            if cost > 0 and row.preco_venda / cost > IMPLAUSIBLE_MARGIN_FACTOR:
                rejections["MARGEM_IMPLAUSIVEL"] += 1
                continue

            ncm_nfe = str(item.get("ncm") or "").strip()
            cest_nfe = str(item.get("cest") or "").strip()
            if (ncm_nfe and ncm_nfe != row.ncm) or (cest_nfe and cest_nfe != row.cest):
                rejections["DIVERGENCIA_NCM_OU_CEST"] += 1
                continue

            evidence = item_entry_evidence(
                item, f"{cost_evidence.numero}/{cost_evidence.serie}"
            )
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
                rejections["BASE_FISCAL_NAO_RESOLVIDA"] += 1
                continue

            cfop = CFOP_SUBSTITUTED if classification == ST_PROVEN else CFOP_TAXED
            body = build_body(
                row, cost=cost, ncm=row.ncm, cest=row.cest, decision=decision, cfop=cfop
            )
            with_cost.append(
                {
                    "prioridade": "A_CUSTO_DFE",
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
                        "valor": cost,
                        "source": COST_DFE,
                        "cost_status": "RESOLVED",
                        "requires_cost_update": False,
                        "unidadeComercial": cost_evidence.unidade_comercial,
                        "unidadeAtomica": cost_evidence.unidade_atomica,
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
                        "blockers": decision.blockers,
                    },
                    "body": {"ready": True, "hash": body_hash(body), "preview": body},
                    "categoria": "READY_HIGH_CONFIDENCE"
                    if decision.confidence == "HIGH"
                    else "READY_ASSUMED_RISK",
                }
            )
            continue

        # --- Caminho B: sem NF-e propria, base por analogia NCM+CEST -------------
        supporting = evidence_by_ncm_cest.get((row.ncm, row.cest)) or []
        if len(supporting) < MIN_SUPPORTING_ITEMS:
            rejections["EVIDENCIA_NCM_CEST_INSUFICIENTE"] += 1
            continue
        classifications = {entry["classification"] for entry in supporting}
        if classifications != {ST_PROVEN}:
            rejections["BASES_CONCORRENTES"] += 1
            continue
        supporting_invoices = {entry["nfe"] for entry in supporting}
        if len(supporting_invoices) < MIN_SUPPORTING_INVOICES:
            rejections["EVIDENCIA_CONCENTRADA_EM_POUCAS_NOTAS"] += 1
            continue
        if st_basis is None or st_reference is None:
            rejections["SEM_TABELA_ST"] += 1
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
            rejections["BASE_FISCAL_NAO_RESOLVIDA"] += 1
            continue

        body = build_body(
            row,
            cost=0,
            ncm=row.ncm,
            cest=row.cest,
            decision=decision,
            cfop=CFOP_SUBSTITUTED,
        )
        pending.append(
            {
                "prioridade": "B_PENDING_DFE",
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
                    "blockers": decision.blockers,
                    "evidenciaNcmCest": {
                        "itens": len(supporting),
                        "notasDistintas": len(supporting_invoices),
                        "classificacoes": sorted(classifications),
                        "amostra": supporting[:8],
                    },
                },
                "body": {"ready": True, "hash": body_hash(body), "preview": body},
                "categoria": "READY_ASSUMED_RISK",
            }
        )

    # Dentro de cada prioridade: base comprovada antes de inferida, depois menor valor.
    with_cost.sort(
        key=lambda c: (
            0 if c["baseFiscal"]["classificacaoEntrada"] == ST_PROVEN else 1,
            c["precoVenda"],
        )
    )
    pending.sort(
        key=lambda c: (-c["baseFiscal"]["evidenciaNcmCest"]["itens"], c["precoVenda"])
    )

    selection = with_cost[:BATCH_SIZE]
    completed_with_pending = 0
    if len(selection) < BATCH_SIZE:
        completed_with_pending = BATCH_SIZE - len(selection)
        selection = selection + pending[:completed_with_pending]
    completed_with_pending = sum(1 for s in selection if s["prioridade"] == "B_PENDING_DFE")

    print("MOTIVOS DE EXCLUSAO")
    for reason, count in sorted(rejections.items(), key=lambda kv: -kv[1]):
        print(f"   {reason:38} {count:>4}")
    print(f"   {'ELEGIVEIS COM CUSTO DF-e':38} {len(with_cost):>4}")
    print(f"   {'ELEGIVEIS SEM CUSTO (PENDING)':38} {len(pending):>4}")
    print()

    if duplicate_notes:
        print("PRODUTOS QUE JA EXISTEM NO CATALOGO COM OUTRO CODIGO DE BARRAS")
        for note in duplicate_notes:
            existing = note["jaCadastrado"][0]
            print(f"   linha {note['linha']:>4} | {note['ean']} | {note['descricao'][:40]}")
            print(f"        ja cadastrado como {existing['produtoCodigo']} "
                  f"'{existing['nome']}' | barras {existing['codigosBarra']}")
        print()

    if with_cost:
        print("CANDIDATOS COM CUSTO DF-e")
        for item in with_cost:
            basis = item["baseFiscal"]
            print(
                f"   linha {item['linha']:>4} | {item['ean']} | R$ {item['precoVenda']:>7}"
                f" | custo {item['custo']['valor']:>9} ({item['custo']['unidadeComercial']})"
                f" | {basis['classificacaoEntrada']} | {item['descricao'][:34]}"
            )
        print()

    print(f"MICROBATCH SELECIONADO: {len(selection)} de {BATCH_SIZE} "
          f"({len(selection) - completed_with_pending} com custo DF-e, {completed_with_pending} pendentes)")
    print()
    for index, item in enumerate(selection, start=1):
        basis = item["baseFiscal"]
        cost = item["custo"]
        print(f"--- {index}. {item['descricao']}")
        print(f"    prioridade {item['prioridade']} | linha {item['linha']} | EAN {item['ean']}")
        print(f"    venda R$ {item['precoVenda']} | NCM {item['ncm']} | CEST {item['cest']}")
        if cost["source"] == COST_DFE:
            nfe = cost["nfe"]
            print(f"    custo R$ {cost['valor']} | unidade {cost['unidadeComercial']} x {cost['quantidade']}"
                  f" | ICMS-ST na nota {cost['icmsStCobrado']}")
            print(f"    calculo: {cost['calculo']}")
            print(f"    NF-e {nfe['numero']}/{nfe['serie']} de {nfe['emissao']} | {nfe['fornecedor']}"
                  f" | cStat {nfe['protocoloCstat']} | chave {nfe['accessKeyMasked']}")
            print(f"    margem {item['precoVenda'] / cost['valor']:.2f}x")
        else:
            support = basis["evidenciaNcmCest"]
            print(f"    custo R$ 0 ({cost['cost_status']}, {cost['source']}) — {cost['motivoRevisao']}")
            print(f"    sustentacao: {support['itens']} itens em {support['notasDistintas']} notas "
                  f"distintas com mesmo NCM+CEST, todos {support['classificacoes']}")
            for sample in support["amostra"][:4]:
                print(f"       - {(sample['descricao'] or '')[:46]} | CST {sample['cstIcms']} | NF {sample['nfe']}")
        print(f"    entrada {basis['classificacaoEntrada']} | CST {basis['cstIcmsEntrada']}"
              f" | ICMS tabela {basis['icmsTableReference']} | PIS/COFINS tabela {basis['pisCofinsTableReference']}")
        print(f"    CFOP {basis['cfopEntrada']}/{basis['cfopSaida']} | confianca {basis['confidence']}"
              f" | risco {basis['fiscalRisk']} | revisao {basis['requiresAccountantReview']}")
        if basis["camposInferidos"]:
            print(f"    campos inferidos: {basis['camposInferidos']}")
        print(f"    hash {item['body']['hash'][:32]}...")
        print()

    payload = {
        "title": "PREFLIGHT MICROBATCH 04 — 118508",
        "generatedAt": generated_at,
        "sheet": SHEET.name,
        "empresa": COMPANY_CODE,
        "credential": {
            "variable": credential.variable_name,
            "keyExposed": False,
            "sentinelFound": guard.sentinel_found,
            "sentinelCompanyLinkConfirmed": guard.company_link_confirmed,
        },
        "batchSize": BATCH_SIZE,
        "eligibleWithCost": len(with_cost),
        "eligiblePending": len(pending),
        "selectedWithCost": len(selection) - completed_with_pending,
        "selectedPending": completed_with_pending,
        "pendingCostFlagRequired": bool(completed_with_pending),
        "requiredFlag": "ALLOW_PENDING_DFE_COST=true" if completed_with_pending else None,
        "rejections": dict(rejections),
        "possibleDuplicatesByDescription": duplicate_notes,
        "products": selection,
        "apiWrites": 0,
        "status": "READY_FOR_WRITE" if selection else "NOTHING_TO_WRITE",
    }
    (OUT_DIR / "microbatch_selection.json").write_text(
        json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8"
    )

    print("=" * 78)
    print(f"STATUS: {payload['status']}")
    if completed_with_pending:
        print(f"ATENCAO: {completed_with_pending} produto(s) com custo pendente exigem "
              f"ALLOW_PENDING_DFE_COST=true na execucao")
    print("API WRITES: 0")
    print(f"artefato: {OUT_DIR / 'microbatch_selection.json'}")


if __name__ == "__main__":
    main()
