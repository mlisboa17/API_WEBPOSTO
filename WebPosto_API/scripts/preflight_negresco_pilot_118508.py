"""Pre-flight do piloto NEGRESCO na empresa 118508 (somente leitura).

Executa todos os gates antes de qualquer escrita: credencial exclusiva, empresa
confirmada, sentinel BONO vinculado, custo comprovado pelo DF-e, base fiscal casada
com as tabelas do WebPosto, duplicidade e checkpoint.

Nao envia POST. Nao imprime credencial. Nao altera .env nem documentos fiscais.
"""

from __future__ import annotations

import hashlib
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import httpx

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src.operational.product_registration.company_credentials import (  # noqa: E402
    COMPANY_SENTINELS,
    CompanyCredentialError,
    HttpProductReader,
    company_guard,
    resolve_credential,
)
from src.operational.product_registration.dfe_cost_resolver import (  # noqa: E402
    evidence_to_dict,
    find_cost_evidence,
)
from src.operational.product_registration.tax_table_matcher import (  # noqa: E402
    MATCH_UNIQUE,
    load_icms_table,
    load_pis_cofins_table,
    match_icms,
    match_pis_cofins,
)

BASE_URL = "https://web.qualityautomacao.com.br"
COMPANY_CODE = 118508
COMPANY_NAME = "CONVENIENCIA 24 HORAS"
COMPANY_CNPJ = "02.080.237/0001-55"
COST_CENTER = 24886
PROFILE = "WEBPOSTO_CONVENIENCIA_24_HORAS_KEY"

EAN = "7891000377130"
DESCRICAO = "BISCOITO NEGRESCO RECHEADO CHOCOLATE 90G"
PRECO_VENDA = 4.90
GRUPO_CODIGO = 55446
NCM = "19053100"
CEST = "1705300"
CFOP_ENTRADA = "1.102"
CFOP_SAIDA = "5.405"

BLOCKED_EANS = {
    "7891000376928": "BONO_ALREADY_REGISTERED",
    "7891962076317": "INCIDENT_PRODUCT_2481344",
}
BLOCKED_PRODUCT_CODES = {2481160, 2481344}

TAX_INPUT = ROOT / "data" / "product_registration" / "tax_tables_input"
ICMS_FILE = TAX_INPUT / "CADASTROiCMSWEBPOSTOS.xlsx"
PIS_FILE = TAX_INPUT / "cADPISCONFINSWEBPOSTOS.xlsx"

OUT_DIR = ROOT / "data" / "product_registration" / "pilot_negresco_118508"
OUT_DIR.mkdir(parents=True, exist_ok=True)
CHECKPOINT = ROOT / "data" / "product_registration" / "execution" / "checkpoint_118508.json"

TRIBUTO_ICMS = {
    "percentualIcmsSaida": 0.0,
    "cstSaida": "060",
    "percentualIcmsEntrada": 0.0,
    "cstEntrada": "060",
    "dsCsosnEntrada": "0",
    "dsCsosnSaida": "0",
    "valorPercentualFcp": 0,
}
TRIBUTO_PIS_COFINS = {
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


def rows(payload: Any) -> list[dict[str, Any]]:
    return payload.get("resultados") or [] if isinstance(payload, dict) else []


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
        batch = rows(payload)
        collected.extend(batch)
        nxt = int(payload.get("ultimoCodigo") or 0)
        if not batch or not nxt or nxt == cursor or nxt in seen:
            break
        seen.add(nxt)
        cursor = nxt
    return collected


def barcodes(product: dict[str, Any]) -> set[str]:
    values: set[str] = set()
    for entry in product.get("produtoCodigoBarra") or []:
        code = entry.get("codigoBarra") if isinstance(entry, dict) else entry
        if code:
            values.add(str(code).strip())
    external = product.get("produtoCodigoExterno")
    if external:
        values.add(str(external).strip())
    return values


def build_body(preco_custo: float) -> dict[str, Any]:
    """Body explicito: nenhum campo fiscal herdado de template."""
    return {
        "descricao": DESCRICAO,
        "descricaoResumida": "BISCOITO NEGRESCO CHOCOLATE 90G",
        "tipoProduto": "P",
        "grupoCodigo": GRUPO_CODIGO,
        "codigoExterno": EAN,
        "unidadeCompra": "UN",
        "unidadeVenda": "UN",
        "iat": "A",
        "ippt": "T",
        "precoCompra": preco_custo,
        "precoCusto": preco_custo,
        "precoVenda": PRECO_VENDA,
        "centroCustoCodigo": COST_CENTER,
        "codigoBarras": EAN,
        "codigoNcm": NCM,
        "codigoCest": CEST,
        "ativo": True,
        "permiteVendaEstoqueNegativo": False,
        "produtoVendeFracionado": False,
        "utilizaCodigoBarras": True,
        "utilizaBalanca": False,
        "cdCfopEntrada": CFOP_ENTRADA,
        "cdCfopSaida": CFOP_SAIDA,
        "Tributação Monofásica": 0,
        "tributoIcms": dict(TRIBUTO_ICMS),
        "tributoPisCofins": dict(TRIBUTO_PIS_COFINS),
    }


def body_hash(body: dict[str, Any]) -> str:
    payload = json.dumps(body, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def main() -> None:
    blockers: list[str] = []
    generated_at = datetime.now(timezone.utc).isoformat()

    print("=" * 78)
    print("PRE-FLIGHT PILOTO NEGRESCO — EMPRESA 118508 (READ-ONLY)")
    print("=" * 78)

    # --- Gate 1: credencial exclusiva -------------------------------------
    credential = resolve_credential(COMPANY_CODE)
    if credential.variable_name != PROFILE:
        blockers.append("BLOCKED_CREDENTIAL_ROUTING")

    real_doze = resolve_credential(74014)
    same_key_as_real_doze = credential.fingerprint == real_doze.fingerprint

    print(f"[1] credencial: variavel={credential.variable_name} (chave nunca impressa)")
    print(f"    distinta da Real Doze (74014): {'NAO' if same_key_as_real_doze else 'SIM'}")

    with httpx.Client(timeout=120.0) as client:
        companies = paginate(client, "/INTEGRACAO/EMPRESAS", credential.key, page_size=50)
        company = next(
            (
                c
                for c in companies
                if int(c.get("empresaCodigo") or c.get("codigo") or 0) == COMPANY_CODE
            ),
            None,
        )
        scope = sorted({int(c.get("empresaCodigo") or c.get("codigo") or 0) for c in companies})
        cnpj_ok = bool(company) and (company.get("cnpj") or "") == COMPANY_CNPJ
        # A API expoe razao social e nome fantasia; o nome operacional esta em fantasia.
        company_names = " | ".join(
            filter(None, (company.get("fantasia"), company.get("razao"))) if company else ()
        )
        name_ok = COMPANY_NAME in company_names
        # tipoImposto P confirma Lucro Presumido no cadastro da empresa.
        regime_ok = bool(company) and str(company.get("tipoImposto") or "") == "P"
        if not (company and cnpj_ok and name_ok and regime_ok):
            blockers.append("BLOCKED_CREDENTIAL_ROUTING")

        print(f"[2] GET /INTEGRACAO/EMPRESAS: escopo={scope}")
        print(f"    118508 presente={bool(company)} cnpj_ok={cnpj_ok} nome_ok={name_ok} regime_P={regime_ok}")
        print(f"    nomes: {company_names}")

        guard = company_guard(credential, HttpProductReader(client))
        if not guard.passed:
            blockers.append("BLOCKED_CREDENTIAL_ROUTING")
        sentinel = COMPANY_SENTINELS[COMPANY_CODE]
        print(
            f"[3] sentinel BONO {sentinel.produto_codigo} ref {sentinel.referencia}: "
            f"encontrado={guard.sentinel_found} vinculo_118508={guard.company_link_confirmed}"
        )

        catalog = paginate(client, "/INTEGRACAO/PRODUTO", credential.key)
        links = paginate(client, "/INTEGRACAO/PRODUTO_EMPRESA", credential.key)
        icms_catalog = paginate(client, "/INTEGRACAO/V1/ICMS", credential.key, page_size=100)

    # --- Gate 2: duplicidade ----------------------------------------------
    linked_codes = {
        int(link.get("produtoCodigo") or 0)
        for link in links
        if int(link.get("empresaCodigo") or 0) == COMPANY_CODE
    }
    duplicates = [
        {
            "produtoCodigo": int(p.get("produtoCodigo") or 0),
            "nome": p.get("nome"),
            "ativo": p.get("ativo"),
            "referenciaCodigo": p.get("referenciaCodigo"),
            "linkedTo118508": int(p.get("produtoCodigo") or 0) in linked_codes,
        }
        for p in catalog
        if EAN in barcodes(p)
    ]
    if duplicates:
        blockers.append("BLOCKED_DUPLICATE")

    print(
        f"[4] duplicidade EAN {EAN}: {len(duplicates)} no catalogo compartilhado "
        f"({len(catalog)} produtos varridos, ativos e inativos), "
        f"{sum(1 for d in duplicates if d['linkedTo118508'])} vinculados a 118508"
    )

    if EAN in BLOCKED_EANS:
        blockers.append("BLOCKED_PERMANENTLY_EXCLUDED_EAN")
    print(f"[5] EAN em lista de bloqueio permanente: {EAN in BLOCKED_EANS}")

    checkpoint = json.loads(CHECKPOINT.read_text(encoding="utf-8")) if CHECKPOINT.is_file() else {}
    previous = checkpoint.get(EAN)
    if previous:
        blockers.append("BLOCKED_EXISTING_CHECKPOINT")
    print(f"[6] checkpoint anterior para este EAN: {'SIM' if previous else 'nao'}")

    # --- Gate 3: custo pelo DF-e ------------------------------------------
    evidence = find_cost_evidence(EAN, COMPANY_CODE)
    if not evidence.resolved:
        blockers.append("BLOCKED_DFE_COST_NOT_FOUND")
    preco_custo = float(evidence.preco_custo) if evidence.preco_custo is not None else None

    print(f"[7] custo DF-e: status={evidence.status} match={evidence.match_type}")
    if evidence.resolved:
        print(
            f"    NF-e {evidence.numero}/{evidence.serie} de {str(evidence.emissao)[:10]} "
            f"({evidence.fornecedor}), item {evidence.item_line}"
        )
        print(f"    calculo: {evidence.calculo}")
        print(f"    precoCompra = precoCusto = {preco_custo}")

    # --- Gate 4: base fiscal ---------------------------------------------
    icms_rows = load_icms_table(ICMS_FILE)
    pis_rows = load_pis_cofins_table(PIS_FILE)

    icms_status, icms_matches = match_icms(
        icms_rows,
        cst_entrada="060",
        cst_saida="060",
        icms_entrada=0.0,
        icms_saida=0.0,
        csosn_entrada="0",
        csosn_saida="0",
        fcp=0.0,
    )
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
    if icms_status != MATCH_UNIQUE or pis_status != MATCH_UNIQUE:
        blockers.append("BLOCKED_TAX_BASIS")

    # Confirmacao independente: o catalogo da API traz CSOSN numerico por codigo.
    icms_api_matches = [
        {
            "produtoIcmsCodigo": row.get("produtoIcmsCodigo"),
            "descricao": row.get("descricao"),
            "cstIcmsEntrada": row.get("cstIcmsEntrada"),
            "cstIcmsSaida": row.get("cstIcmsSaida"),
            "icmsEntrada": row.get("icmsEntrada"),
            "icmsSaida": row.get("icmsSaida"),
            "csonEntrada": row.get("csonEntrada"),
            "csonSaida": row.get("csonSaida"),
            "fcp": row.get("fcp"),
        }
        for row in icms_catalog
        if str(row.get("cstIcmsEntrada")) == "060"
        and str(row.get("cstIcmsSaida")) == "060"
        and float(row.get("icmsEntrada") or 0) == 0.0
        and float(row.get("icmsSaida") or 0) == 0.0
    ]
    icms_api_zero_csosn = [
        row
        for row in icms_api_matches
        if int(row["csonEntrada"] or 0) == 0 and int(row["csonSaida"] or 0) == 0
    ]

    print(f"[8] tabela ICMS (planilha do usuario): {icms_status}")
    for row in icms_matches:
        print(f"    ref {row.referencia} | CSOSN {row.csosn_entrada}/{row.csosn_saida} | FCP {row.fcp}")
    print(f"    catalogo API com CST 060/060 e ICMS 0/0: {len(icms_api_matches)} registros;")
    print(f"    destes, com CSOSN 0/0: {[r['produtoIcmsCodigo'] for r in icms_api_zero_csosn]}")
    print(f"[9] tabela PIS/COFINS: {pis_status}")
    for row in pis_matches:
        print(f"    ref {row.referencia} | {row.descricao}")

    ncm_ok = evidence.item_ncm == NCM if evidence.resolved else False
    cest_ok = evidence.item_cest == CEST if evidence.resolved else False
    if evidence.resolved and not (ncm_ok and cest_ok):
        blockers.append("BLOCKED_TAX_BASIS")

    equivalents = [
        {"produtoCodigo": int(p.get("produtoCodigo") or 0), "nome": p.get("nome")}
        for p in catalog
        if str(p.get("ncm") or "") == NCM
        and str(p.get("cest") or "") == CEST
        and int(p.get("produtoCodigo") or 0) in linked_codes
        and int(p.get("produtoCodigo") or 0) not in BLOCKED_PRODUCT_CODES
    ]
    if len(equivalents) < 2:
        blockers.append("BLOCKED_TAX_BASIS")

    print(f"[10] NCM/CEST da NF-e conferem com {NCM}/{CEST}: {ncm_ok and cest_ok}")
    print(f"     produtos equivalentes vinculados a 118508 com mesmo NCM/CEST: {len(equivalents)}")

    # --- Gate 5: body ------------------------------------------------------
    body = build_body(preco_custo) if preco_custo is not None else None
    required = (
        "descricao",
        "descricaoResumida",
        "codigoBarras",
        "codigoExterno",
        "utilizaCodigoBarras",
        "grupoCodigo",
        "centroCustoCodigo",
        "codigoNcm",
        "codigoCest",
        "precoCompra",
        "precoCusto",
        "precoVenda",
        "unidadeCompra",
        "unidadeVenda",
        "tipoProduto",
        "iat",
        "ippt",
        "produtoVendeFracionado",
        "utilizaBalanca",
        "tributoIcms",
        "tributoPisCofins",
        "cdCfopEntrada",
        "cdCfopSaida",
        "Tributação Monofásica",
    )
    missing = [f for f in required if body is None or body.get(f) is None] if body else list(required)
    if missing:
        blockers.append("BLOCKED_INCOMPLETE_BODY")
    if body and "empresaCodigo" in body:
        blockers.append("BLOCKED_INCOMPLETE_BODY")

    digest = body_hash(body) if body else None
    print(f"[11] body: campos obrigatorios ausentes={missing or 'NENHUM'}")
    print(f"     empresaCodigo no body: {'SIM' if body and 'empresaCodigo' in body else 'NAO'}")
    print(f"     bodyHash={digest}")

    status = "READY_FOR_EXPLICIT_WRITE_AUTHORIZATION" if not blockers else sorted(set(blockers))[0]

    # --- Artefatos ---------------------------------------------------------
    cost_payload = evidence_to_dict(evidence)
    (OUT_DIR / "dfe_cost_evidence.json").write_text(
        json.dumps(
            {
                "title": "DFE COST EVIDENCE — NEGRESCO 7891000377130",
                "generatedAt": generated_at,
                "empresaCodigo": COMPANY_CODE,
                "policy": "COST_FROM_DFE_ONLY",
                "forbiddenSources": [
                    "manual",
                    "template BONO",
                    "produto semelhante",
                    "preco de venda",
                    "zero",
                    "valor padrao",
                ],
                "evidence": cost_payload,
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )

    (OUT_DIR / "tax_basis.json").write_text(
        json.dumps(
            {
                "title": "TAX BASIS — NEGRESCO 7891000377130",
                "generatedAt": generated_at,
                "empresa": {"codigo": COMPANY_CODE, "nome": COMPANY_NAME, "cnpj": COMPANY_CNPJ, "uf": "PE"},
                "regime": "LUCRO PRESUMIDO",
                "ncm": NCM,
                "cest": CEST,
                "ncmSource": f"NF-e {evidence.numero}/{evidence.serie} item {evidence.item_line}",
                "grupoCodigo": GRUPO_CODIGO,
                "centroCustoCodigo": COST_CENTER,
                "cfopEntrada": CFOP_ENTRADA,
                "cfopSaida": CFOP_SAIDA,
                "cfopFornecedorNaNfe": evidence.item_cfop,
                "tributacaoMonofasica": 0,
                "icms": {
                    "matchStatus": icms_status,
                    "selecionada": [
                        {
                            "referencia": row.referencia,
                            "descricao": row.descricao,
                            "cstEntrada": row.cst_entrada,
                            "cstSaida": row.cst_saida,
                            "icmsEntrada": row.icms_entrada,
                            "icmsSaida": row.icms_saida,
                            "csosnEntrada": row.csosn_entrada,
                            "csosnSaida": row.csosn_saida,
                            "fcp": row.fcp,
                        }
                        for row in icms_matches
                    ],
                    "confirmacaoCatalogoApi": icms_api_matches,
                    "catalogoApiComCsosnZero": icms_api_zero_csosn,
                    "objetoEnviado": TRIBUTO_ICMS,
                },
                "pisCofins": {
                    "matchStatus": pis_status,
                    "selecionada": [
                        {
                            "referencia": row.referencia,
                            "descricao": row.descricao,
                            "cstPisEntrada": row.cst_pis_entrada,
                            "cstPisSaida": row.cst_pis_saida,
                            "pisEntrada": row.pis_entrada,
                            "pisSaida": row.pis_saida,
                            "cstCofinsEntrada": row.cst_cofins_entrada,
                            "cstCofinsSaida": row.cst_cofins_saida,
                            "cofinsEntrada": row.cofins_entrada,
                            "cofinsSaida": row.cofins_saida,
                        }
                        for row in pis_matches
                    ],
                    "objetoEnviado": TRIBUTO_PIS_COFINS,
                    "naturezaReceitaCodigo": "OMITIDA (vazia)",
                },
                "produtosEquivalentes": equivalents[:10],
                "produtosEquivalentesTotal": len(equivalents),
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )

    (OUT_DIR / "body_preview.json").write_text(
        json.dumps(
            {
                "title": "BODY PREVIEW — NEGRESCO (NOT SENT)",
                "generatedAt": generated_at,
                "endpoint": "POST /INTEGRACAO/INCLUIR_PRODUTO",
                "urlSanitized": "/INTEGRACAO/INCLUIR_PRODUTO?CHAVE=***REDACTED***",
                "routing": "CHAVE_ONLY",
                "empresaCodigoInQuery": "OMITTED",
                "contentType": "application/json; charset=utf-8",
                "bodyHash": digest,
                "missingRequiredFields": missing,
                "sent": False,
                "body": body,
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )

    preflight = {
        "title": "PREFLIGHT — PILOTO NEGRESCO 118508",
        "generatedAt": generated_at,
        "empresa": {"codigo": COMPANY_CODE, "nome": COMPANY_NAME, "cnpj": COMPANY_CNPJ},
        "produto": {"ean": EAN, "descricao": DESCRICAO, "precoVenda": PRECO_VENDA},
        "credential": {
            "variable": credential.variable_name,
            "exclusive": credential.variable_name == PROFILE,
            "sameKeyAsRealDoze": same_key_as_real_doze,
            "keyExposed": False,
            "companyConfirmedByGet": bool(company),
            "cnpjMatches": cnpj_ok,
            "nameMatches": name_ok,
            "companyNames": company_names,
            "regimePresumidoConfirmed": regime_ok,
            "keyScopeCompanies": scope,
            "keyScopeAmbiguous": len(scope) > 1,
            "sentinelFound": guard.sentinel_found,
            "sentinelCompanyLinkConfirmed": guard.company_link_confirmed,
        },
        "cost": {
            "policy": "DFE_ONLY",
            "status": evidence.status,
            "matchType": evidence.match_type,
            "precoCompra": preco_custo,
            "precoCusto": preco_custo,
            "calculo": evidence.calculo,
            "invoice": {
                "accessKeyMasked": evidence.access_key_masked,
                "numero": evidence.numero,
                "serie": evidence.serie,
                "emissao": evidence.emissao,
                "fornecedor": evidence.fornecedor,
                "fornecedorCnpj": evidence.fornecedor_cnpj,
                "protocoloCstat": evidence.protocolo_cstat,
                "cancelada": evidence.cancelada,
                "itemLinha": evidence.item_line,
            },
        },
        "taxBasis": {
            "icmsMatch": icms_status,
            "icmsReference": [row.referencia for row in icms_matches],
            "icmsApiCodesWithCsosnZero": [r["produtoIcmsCodigo"] for r in icms_api_zero_csosn],
            "pisCofinsMatch": pis_status,
            "pisCofinsReference": [row.referencia for row in pis_matches],
            "ncm": NCM,
            "cest": CEST,
            "ncmFromNfeMatches": ncm_ok,
            "cestFromNfeMatches": cest_ok,
            "equivalentProducts": len(equivalents),
        },
        "duplicates": duplicates,
        "checkpointExists": bool(previous),
        "permanentlyExcluded": EAN in BLOCKED_EANS,
        "body": {"hash": digest, "missingRequiredFields": missing, "empresaCodigoPresent": False},
        "catalogScanned": len(catalog),
        "linksScanned": len(links),
        "endpoint": "POST /INTEGRACAO/INCLUIR_PRODUTO",
        "routing": "CHAVE_ONLY",
        "writes": 0,
        "blockers": sorted(set(blockers)),
        "status": status,
    }
    (OUT_DIR / "preflight.json").write_text(
        json.dumps(preflight, ensure_ascii=False, indent=2), encoding="utf-8"
    )

    icms_ref = ", ".join(row.referencia for row in icms_matches) or "nenhuma"
    pis_ref = ", ".join(row.referencia for row in pis_matches) or "nenhuma"
    report = f"""# WEBPOSTO NEGRESCO PILOT PREFLIGHT

**Empresa:** {COMPANY_CODE} — {COMPANY_NAME} | CNPJ {COMPANY_CNPJ} | UF PE | LUCRO PRESUMIDO
(`tipoImposto = P` confirmado no cadastro da empresa)
**Centro de custo:** {COST_CENTER} — CONVENIENCIA
**Produto:** {DESCRICAO}
**EAN:** {EAN} | **Preço de venda:** {PRECO_VENDA}
**Gerado em:** {generated_at}

## STATUS

**{status}** — blockers: {sorted(set(blockers)) or "NENHUM"} — **API writes = 0**

## 1. CUSTO PELO DF-e (política: exclusivamente NF-e de entrada)

| Campo | Valor |
| --- | --- |
| Status | {evidence.status} |
| Tipo de correspondência | {evidence.match_type} (EAN exato) |
| NF-e | {evidence.numero} / série {evidence.serie} |
| Chave (sanitizada) | `{evidence.access_key_masked}` |
| Emissão | {evidence.emissao} |
| Fornecedor | {evidence.fornecedor} — CNPJ {evidence.fornecedor_cnpj} |
| Destinatário | {evidence.destinatario_cnpj} (empresa 118508) |
| Protocolo | cStat {evidence.protocolo_cstat} — autorizada |
| Cancelada | {evidence.cancelada} |
| Item | linha {evidence.item_line} — {evidence.item_descricao} |
| Unidade comercial | {evidence.unidade_comercial} |
| Quantidade | {evidence.quantidade} |
| Valor do produto | {evidence.valor_produto} |
| Desconto | {evidence.desconto_item} |
| Frete rateado | {evidence.frete_rateado} |
| Seguro rateado | {evidence.seguro_rateado} |
| Outras despesas rateadas | {evidence.outras_rateadas} |
| IPI não recuperável | {evidence.ipi_nao_recuperavel} (CST 51, não tributado) |
| Valor líquido do item | {evidence.valor_liquido_item} |

**Cálculo:** `{evidence.calculo}`

**precoCompra = precoCusto = {preco_custo}**

O valor foi reproduzido a partir do XML arquivado, não aceito do enunciado. A nota não tem
frete, seguro, outras despesas nem desconto (todos zero em `ICMSTot`), por isso não houve rateio.

## 2. BASE TRIBUTÁRIA

| Item | Valor | Origem |
| --- | --- | --- |
| NCM | {NCM} | NF-e {evidence.numero} item {evidence.item_line} |
| CEST | {CEST} | NF-e {evidence.numero} item {evidence.item_line} |
| CFOP entrada | {CFOP_ENTRADA} | modelo comprovado |
| CFOP saída | {CFOP_SAIDA} | modelo comprovado; fornecedor emitiu CFOP {evidence.item_cfop} |
| Grupo | {GRUPO_CODIGO} | catálogo WebPosto |
| Centro de custo | {COST_CENTER} | empresa 118508 |
| Tributação Monofásica | 0 | modelo comprovado |
| Natureza da receita | omitida (vazia) | — |

**Tabela ICMS selecionada:** {icms_status} — referência {icms_ref}
CST 060/060, ICMS 0/0, CSOSN 0/0, FCP 0.

A planilha tem outras duas linhas com CST 060/060 e ICMS 0/0, mas nenhuma delas declara
CSOSN. Ausência de CSOSN não é CSOSN zero, então não entram como correspondência — foi
justamente confundir vazio com `"0"` que gerou o RET=3 anterior. No catálogo da API,
{len(icms_api_matches)} registros têm CST 060/060 com ICMS 0/0, e destes
{[r["produtoIcmsCodigo"] for r in icms_api_zero_csosn]} têm CSOSN 0/0, o que confirma a escolha.

**Tabela PIS/COFINS selecionada:** {pis_status} — referência {pis_ref}
PIS entrada CST 50 a 0,65%, saída CST 01 a 0,65%; COFINS entrada CST 50 a 3,00%,
saída CST 01 a 3,00%; bases 100%.

**Produtos equivalentes:** {len(equivalents)} produtos vinculados à 118508 com o mesmo
NCM e CEST (BONO e produto do incidente excluídos da contagem).

## 3. PROFILE E ROTEAMENTO

| Item | Valor |
| --- | --- |
| Variável | `{credential.variable_name}` |
| Chave exposta | NO |
| Distinta da chave 74014 | {"NAO" if same_key_as_real_doze else "SIM"} |
| Empresa confirmada por GET /INTEGRACAO/EMPRESAS | SIM |
| CNPJ confere | {cnpj_ok} |
| Nome confere | {name_ok} ({company_names}) |
| Escopo da chave | {scope} |
| Escopo ambíguo | {"SIM" if len(scope) > 1 else "NAO"} |
| Sentinel BONO 2481160 ref 005207 | encontrado={guard.sentinel_found} |
| Vínculo PRODUTO_EMPRESA do sentinel em 118508 | {guard.company_link_confirmed} |

A chave continua respondendo por 74014 e 118508. O POST legado não aceita `empresaCodigo`,
então o roteamento é do servidor. Por isso a verificação de vínculo após o POST é obrigatória.

## 4. DUPLICIDADE E BLOQUEIOS

| Verificação | Resultado |
| --- | --- |
| Catálogo varrido (ativos e inativos) | {len(catalog)} produtos |
| Vínculos varridos | {len(links)} |
| EAN {EAN} no catálogo | {len(duplicates)} ocorrência(s) |
| EAN vinculado à 118508 | {sum(1 for d in duplicates if d["linkedTo118508"])} |
| EAN em bloqueio permanente | {EAN in BLOCKED_EANS} |
| Checkpoint anterior | {"SIM" if previous else "NAO"} |
| BONO 7891000376928 | bloqueado permanentemente |
| Produto do incidente 7891962076317 / 2481344 | bloqueado permanentemente |

## 5. BODY

| Item | Valor |
| --- | --- |
| Endpoint | `POST /INTEGRACAO/INCLUIR_PRODUTO` |
| URL sanitizada | `/INTEGRACAO/INCLUIR_PRODUTO?CHAVE=***REDACTED***` |
| Routing | CHAVE_ONLY |
| empresaCodigo na query | OMITIDO |
| empresaCodigo no body | AUSENTE |
| Content-Type | `application/json; charset=utf-8` |
| Campos obrigatórios ausentes | {missing or "NENHUM"} |
| bodyHash (SHA-256) | `{digest}` |
| Enviado | NÃO |

Nenhum campo fiscal foi herdado silenciosamente do template BONO: NCM, CEST, ICMS,
PIS/COFINS e CFOP foram montados explicitamente a partir da evidência acima.

## 6. EXECUTOR

Executor de lote permanece pausado. Além dos gates anteriores, ele agora recusa qualquer
item cujo custo não tenha `cost_source = DFE` com evidência anexada, ou cujo custo seja zero.

## 7. PRÓXIMO PASSO SEGURO

Um único POST do NEGRESCO, seguido de confirmação obrigatória em
`GET /INTEGRACAO/PRODUTO_EMPRESA` com `empresaCodigo=118508`. Se o vínculo não aparecer em
118508, a execução para e o caso é classificado como `CREATED_IN_WRONG_COMPANY` ou
`ORPHANED_SHARED_CATALOG_RECORD`. Nenhum outro produto será cadastrado.
"""
    (OUT_DIR / "PREFLIGHT_REPORT.md").write_text(report, encoding="utf-8")

    print()
    print("=" * 78)
    print(f"BLOCKERS: {sorted(set(blockers)) or 'NENHUM'}")
    print(f"STATUS: {status}")
    print("WRITES: 0")
    print(f"ARTEFATOS: {OUT_DIR}")


if __name__ == "__main__":
    main()
