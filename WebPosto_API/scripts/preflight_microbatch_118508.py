"""Pre-flight fiscal do primeiro microbatch da empresa 118508 (somente leitura).

Quatro produtos com custo ja resolvido pelo DF-e. Nenhum deles entrou com ICMS
substituido, portanto nenhum pode receber a base do NEGRESCO. Este script mede o que e
mensuravel e declara explicitamente o que nao e.

Nao envia POST. Nao imprime credencial.
"""

from __future__ import annotations

import hashlib
import json
import sys
from collections import Counter
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
    find_cost_evidence,
)
from src.operational.product_registration.fiscal_resolver import (  # noqa: E402
    ST_PROVEN,
    EntryEvidence,
    FiscalResolver,
    classify_entry,
)
from src.operational.product_registration.tax_table_matcher import (  # noqa: E402
    MATCH_UNIQUE,
    basis_from_row,
    load_icms_table,
    load_pis_cofins_table,
    match_icms_by_entry_rate,
    match_pis_cofins,
)

BASE_URL = "https://web.qualityautomacao.com.br"
COMPANY_CODE = 118508
COMPANY_CNPJ = "02.080.237/0001-55"
PROFILE = "WEBPOSTO_CONVENIENCIA_24_HORAS_KEY"
GRUPO_CODIGO = 55446
COST_CENTER = 24886
SENTINEL_BONO = 2481160

# Base de ST comprovada (usada apenas quando a NF-e comprova substituicao).
ST_BASIS = {
    "percentualIcmsSaida": 0.0,
    "cstSaida": "060",
    "percentualIcmsEntrada": 0.0,
    "cstEntrada": "060",
    "dsCsosnEntrada": "0",
    "dsCsosnSaida": "0",
    "valorPercentualFcp": 0,
}
ST_BASIS_TABLE = "0000000061"

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

# CFOP conforme a situacao apurada na entrada, nao copiado do NEGRESCO.
CFOP_SUBSTITUTED = ("1.102", "5.405")
CFOP_TAXED = ("1.102", "5.102")

BATCH = [
    {"ean": "7896336000578", "descricao": "AMENDOIM GRELHADITOS SEM PELE SANTA HELENA 60G", "precoVenda": 4.50},
    {"ean": "7892840817978", "descricao": "BATATA ORIGINAL RUFFLES 115G", "precoVenda": 20.50},
    {"ean": "7892840824655", "descricao": "RUFFLES CHURRASCO ONDULADA 32G", "precoVenda": 6.50},
    {"ean": "7892840824396", "descricao": "SALGADINHO CEBOLITOS 91G", "precoVenda": 13.50},
]

BLOCKED_EANS = {"7891000376928", "7891962076317"}
NEGRESCO_EAN = "7891000377130"

TAX_INPUT = ROOT / "data" / "product_registration" / "tax_tables_input"
OUT_DIR = ROOT / "data" / "product_registration" / "microbatch_01_118508"
OUT_DIR.mkdir(parents=True, exist_ok=True)
CHECKPOINT = ROOT / "data" / "product_registration" / "execution" / "checkpoint_118508.json"
TAX_PROBE = ROOT / "data" / "product_registration" / "product_tax_readback_probe_118508.json"


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


def load_entry_item(document_id: str, line_number: int) -> dict[str, Any]:
    for raw in store.load_items(document_id):
        if raw.get("line_number") == line_number:
            return raw.get("normalized_json") or {}
    return {}


def body_hash(body: dict[str, Any]) -> str:
    payload = json.dumps(body, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def main() -> None:
    generated_at = datetime.now(timezone.utc).isoformat()
    resolver = FiscalResolver()
    print("=" * 78)
    print("PRE-FLIGHT FISCAL — MICROBATCH 01 — EMPRESA 118508 (READ-ONLY)")
    print("=" * 78)

    credential = resolve_credential(COMPANY_CODE)
    routing_ok = credential.variable_name == PROFILE
    print(f"credencial: {credential.variable_name} (nunca impressa) | exclusiva={routing_ok}")

    pis_rows = load_pis_cofins_table(TAX_INPUT / "cADPISCONFINSWEBPOSTOS.xlsx")
    icms_rows = load_icms_table(TAX_INPUT / "CADASTROiCMSWEBPOSTOS.xlsx")
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
    print(f"tabela PIS/COFINS: {pis_status} ref={pis_reference}")

    # A base ICMS efetiva de cada produto nao e legivel pela API: sem essa leitura,
    # a distribuicao de bases entre equivalentes nao pode ser medida.
    probe = json.loads(TAX_PROBE.read_text(encoding="utf-8")) if TAX_PROBE.is_file() else {}
    basis_readable = probe.get("answer") == "YES"
    outbound_invoices = sum(
        1
        for doc in store.list_documents(COMPANY_CODE)
        if str(doc.get("issuer_cnpj") or "") == "02080237000155"
    )
    print(f"base fiscal por produto legivel na API: {'SIM' if basis_readable else 'NAO'}")
    print(f"notas de saida da empresa no DF-e: {outbound_invoices}")

    with httpx.Client(timeout=120.0) as client:
        guard = company_guard(credential, HttpProductReader(client))
        print(f"sentinel BONO {SENTINEL_BONO}: encontrado={guard.sentinel_found} vinculo={guard.company_link_confirmed}")
        catalog = paginate(client, "/INTEGRACAO/PRODUTO", credential.key)
        links = paginate(client, "/INTEGRACAO/PRODUTO_EMPRESA", credential.key)

    linked_codes = {
        int(link.get("produtoCodigo") or 0)
        for link in links
        if int(link.get("empresaCodigo") or 0) == COMPANY_CODE
    }
    checkpoint = json.loads(CHECKPOINT.read_text(encoding="utf-8")) if CHECKPOINT.is_file() else {}

    print(f"catalogo varrido: {len(catalog)} | vinculos 118508: {len(linked_codes)}")
    print()

    results = []
    for product in BATCH:
        ean = product["ean"]
        entry: dict[str, Any] = {
            "ean": ean,
            "descricao": product["descricao"],
            "precoVenda": product["precoVenda"],
        }
        blockers: list[str] = []

        if ean in BLOCKED_EANS or ean == NEGRESCO_EAN:
            blockers.append("PERMANENTLY_EXCLUDED")

        # Custo pelo DF-e
        evidence = find_cost_evidence(ean, COMPANY_CODE)
        if not evidence.resolved:
            blockers.append("BLOCKED_DFE_COST_NOT_FOUND")
        cost = float(evidence.preco_custo) if evidence.preco_custo is not None else None
        entry["custo"] = {
            "status": evidence.status,
            "precoCompra": cost,
            "precoCusto": cost,
            "source": "DFE",
            "calculo": evidence.calculo,
            "nfe": {
                "numero": evidence.numero,
                "serie": evidence.serie,
                "emissao": evidence.emissao,
                "fornecedor": evidence.fornecedor,
                "fornecedorCnpj": evidence.fornecedor_cnpj,
                "accessKeyMasked": evidence.access_key_masked,
                "protocoloCstat": evidence.protocolo_cstat,
                "cancelada": evidence.cancelada,
                "itemLinha": evidence.item_line,
            },
        }

        # Evidencia de tributacao na entrada
        item = load_entry_item(evidence.document_id, evidence.item_line) if evidence.resolved else {}
        icms_node = item.get("icms") or {}
        st_retido = icms_node.get("ICMS.vICMSSTRet")
        entry_evidence = EntryEvidence(
            cst_icms=icms_node.get("ICMS.CST"),
            icms_st_retido=float(st_retido) if st_retido else None,
            cest=item.get("cest"),
            ncm=item.get("ncm"),
            cfop_fornecedor=item.get("cfop"),
            cst_pis=(item.get("pis") or {}).get("PIS.CST"),
            cst_cofins=(item.get("cofins") or {}).get("COFINS.CST"),
            invoice_reference=f"{evidence.numero}/{evidence.serie}",
        )
        classification = classify_entry(entry_evidence)
        entry["tributacaoEntrada"] = {
            "cstIcms": entry_evidence.cst_icms,
            "icmsStRetido": entry_evidence.icms_st_retido,
            "cfopFornecedor": entry_evidence.cfop_fornecedor,
            "cstPis": entry_evidence.cst_pis,
            "cstCofins": entry_evidence.cst_cofins,
            "ipiCst": (item.get("ipi") or {}).get("IPI.CST"),
            "classificacao": classification,
        }
        entry["ncm"] = entry_evidence.ncm
        entry["cest"] = entry_evidence.cest

        # Equivalentes na propria empresa
        equivalents = [
            p
            for p in catalog
            if str(p.get("ncm") or "") == str(entry_evidence.ncm or "")
            and str(p.get("cest") or "") == str(entry_evidence.cest or "")
            and int(p.get("produtoCodigo") or 0) in linked_codes
        ]
        equivalents_same_ncm = [
            p
            for p in catalog
            if str(p.get("ncm") or "") == str(entry_evidence.ncm or "")
            and int(p.get("produtoCodigo") or 0) in linked_codes
        ]
        entry["equivalentes"] = {
            "mesmoNcmCest": len(equivalents),
            "mesmoNcm": len(equivalents_same_ncm),
            "exemplos": [
                {"produtoCodigo": p.get("produtoCodigo"), "nome": p.get("nome")}
                for p in equivalents[:5]
            ],
            "distribuicaoDeBases": {},
            "distribuicaoMensuravel": False,
            "motivoNaoMensuravel": (
                "A API nao expoe a tabela ICMS/PIS-COFINS vinculada a cada produto "
                "(endpoints de tributo por produto retornam 401 e PRODUTO/V1/PRODUTOS "
                "expoem apenas NCM e CEST); o DF-e local nao contem notas de saida da "
                "empresa que revelariam o CST praticado na venda"
            ),
        }

        # Tabela ICMS pela aliquota efetivamente destacada na NF-e de entrada.
        entry_rate = icms_node.get("ICMS.pICMS")
        taxed_basis = None
        taxed_reference = None
        icms_rate_status = "NOT_APPLICABLE"
        if classification != ST_PROVEN and entry_rate is not None:
            rate = float(entry_rate)
            icms_rate_status, rate_matches = match_icms_by_entry_rate(
                icms_rows,
                cst_entrada="000",
                icms_entrada=rate,
                icms_saida=rate,
            )
            if icms_rate_status == MATCH_UNIQUE:
                taxed_basis = basis_from_row(rate_matches[0])
                taxed_reference = rate_matches[0].referencia
        entry["tributacaoEntrada"]["aliquotaIcmsEntrada"] = entry_rate
        entry["tributacaoEntrada"]["icmsDestacado"] = icms_node.get("ICMS.vICMS")
        entry["tributacaoEntrada"]["matchTabelaPorAliquota"] = icms_rate_status

        # Decisao fiscal: base de ST somente quando comprovada
        decision = resolver.decide(
            entry_evidence,
            substituted_basis=ST_BASIS if classification == ST_PROVEN else None,
            substituted_table_reference=ST_BASIS_TABLE if classification == ST_PROVEN else None,
            taxed_basis=taxed_basis,
            taxed_table_reference=taxed_reference,
            pis_cofins_basis=PIS_COFINS_BASIS if pis_reference else None,
            pis_cofins_table_reference=pis_reference,
            equivalents_distribution={},
            basis_catalog={row.referencia: row for row in icms_rows},
        )
        blockers.extend(decision.blockers)

        cfop_entrada, cfop_saida = (
            CFOP_SUBSTITUTED if classification == ST_PROVEN else CFOP_TAXED
        )
        entry["baseFiscal"] = {
            "classificacao": decision.st_classification,
            "icmsBasis": decision.icms_basis,
            "icmsTableReference": decision.icms_table_reference,
            "pisCofinsBasis": decision.pis_cofins_basis,
            "pisCofinsTableReference": decision.pis_cofins_table_reference,
            "confidence": decision.confidence,
            "fiscalRisk": decision.fiscal_risk,
            "requiresAccountantReview": decision.requires_accountant_review,
            "justificativa": decision.justification,
            "cfopEntrada": cfop_entrada,
            "cfopSaida": cfop_saida,
            "cfopObservacao": (
                "CFOP de saida 5.102 (venda tributada) e nao 5.405 (venda de mercadoria "
                "substituida), porque a entrada veio tributada integralmente"
            )
            if classification != ST_PROVEN
            else "CFOP de saida 5.405, coerente com mercadoria substituida",
        }

        # Duplicidade e checkpoint
        duplicates = [
            {"produtoCodigo": p.get("produtoCodigo"), "nome": p.get("nome")}
            for p in catalog
            if ean in barcodes(p)
        ]
        if duplicates:
            blockers.append("BLOCKED_DUPLICATE")
        if ean in checkpoint:
            blockers.append("BLOCKED_EXISTING_CHECKPOINT")
        entry["duplicidade"] = {"ocorrencias": len(duplicates), "detalhe": duplicates}
        entry["checkpointExistente"] = ean in checkpoint

        if not product["precoVenda"] or product["precoVenda"] <= 0:
            blockers.append("BLOCKED_INVALID_PRICE")

        # Body: montado apenas quando a base fiscal esta completa
        body = None
        if decision.can_register and cost is not None:
            body = {
                "descricao": product["descricao"],
                "descricaoResumida": product["descricao"][:32],
                "tipoProduto": "P",
                "grupoCodigo": GRUPO_CODIGO,
                "codigoExterno": ean,
                "unidadeCompra": "UN",
                "unidadeVenda": "UN",
                "iat": "A",
                "ippt": "T",
                "precoCompra": cost,
                "precoCusto": cost,
                "precoVenda": product["precoVenda"],
                "centroCustoCodigo": COST_CENTER,
                "codigoBarras": ean,
                "codigoNcm": entry_evidence.ncm,
                "codigoCest": entry_evidence.cest,
                "ativo": True,
                "permiteVendaEstoqueNegativo": False,
                "produtoVendeFracionado": False,
                "utilizaCodigoBarras": True,
                "utilizaBalanca": False,
                "cdCfopEntrada": cfop_entrada,
                "cdCfopSaida": cfop_saida,
                "Tributação Monofásica": 0,
                "tributoIcms": decision.icms_basis,
                "tributoPisCofins": decision.pis_cofins_basis,
            }
        else:
            blockers.append("BLOCKED_INCOMPLETE_BODY")

        entry["body"] = {
            "ready": body is not None,
            "hash": body_hash(body) if body else None,
            "preview": body,
        }
        entry["blockers"] = sorted(set(blockers))
        entry["status"] = "READY_FOR_WRITE" if not blockers else "BLOCKED"
        results.append(entry)

        print(f"{ean} — {product['descricao']}")
        print(f"   custo DF-e {cost} | NF-e {evidence.numero}/{evidence.serie} | venda {product['precoVenda']}")
        print(f"   NCM {entry_evidence.ncm} CEST {entry_evidence.cest} | entrada CST {entry_evidence.cst_icms}"
              f" | ST retido {entry_evidence.icms_st_retido}")
        print(f"   classificacao: {classification} | aliquota entrada {entry_rate}% | match tabela {icms_rate_status}")
        print(f"   equivalentes NCM+CEST vinculados a 118508: {len(equivalents)} (distribuicao de bases NAO mensuravel)")
        print(f"   base ICMS: ref {decision.icms_table_reference or 'NAO DEFINIDA'} | confidence {decision.confidence}"
              f" | risco {decision.fiscal_risk}")
        print(f"   CFOP {cfop_entrada}/{cfop_saida} | PIS/COFINS ref {pis_reference}")
        print(f"   status: {entry['status']} | blockers: {entry['blockers'] or 'NENHUM'}")
        print()

    ready = [r for r in results if r["status"] == "READY_FOR_WRITE"]
    batch_status = "READY_FOR_WRITE" if len(ready) == len(results) else "BLOCKED_TAX_BASIS"

    payload = {
        "title": "PREFLIGHT MICROBATCH 01 — 118508",
        "generatedAt": generated_at,
        "empresa": {"codigo": COMPANY_CODE, "cnpj": COMPANY_CNPJ},
        "credential": {
            "variable": credential.variable_name,
            "exclusive": routing_ok,
            "keyExposed": False,
            "sentinelFound": guard.sentinel_found,
            "sentinelCompanyLinkConfirmed": guard.company_link_confirmed,
        },
        "inferenceFeasibility": {
            "productBasisReadableFromApi": basis_readable,
            "outboundInvoicesInDfe": outbound_invoices,
            "equivalentBasisDistributionMeasurable": False,
            "consequence": (
                "O critério de 5 equivalentes com 80% na mesma base não pode ser avaliado: "
                "não há fonte que revele qual tabela cada produto usa"
            ),
        },
        "taxTables": {
            "icmsFile": "CADASTROiCMSWEBPOSTOS.xlsx",
            "pisCofinsFile": "cADPISCONFINSWEBPOSTOS.xlsx",
            "cfopFile": "CFOP_WEbPOSTO.xlsx",
            "pisCofinsMatch": pis_status,
            "pisCofinsReference": pis_reference,
        },
        "products": results,
        "readyCount": len(ready),
        "blockedCount": len(results) - len(ready),
        "apiWrites": 0,
        "status": batch_status,
    }
    (OUT_DIR / "preflight_microbatch.json").write_text(
        json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8"
    )

    print("=" * 78)
    print(f"PRONTOS PARA ESCRITA: {len(ready)}/{len(results)}")
    print(f"STATUS DO LOTE: {batch_status}")
    print("API WRITES: 0")
    print(f"artefato: {OUT_DIR / 'preflight_microbatch.json'}")


if __name__ == "__main__":
    main()
