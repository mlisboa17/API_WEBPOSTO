"""Pre-flight dos 257 produtos da planilha fiscal da empresa 118508 (somente leitura).

Cruza cada EAN com o catalogo completo, os vinculos da empresa, o checkpoint de todos os
lotes e o armazenamento de DF-e. Resolve custo pelo DF-e e base fiscal pela evidencia de
entrada, sem herdar tributacao por NCM.

Ao final seleciona o proximo microbatch de no maximo 5 produtos. Nao envia POST.
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

from src.operational.product_registration.company_credentials import (  # noqa: E402
    HttpProductReader,
    company_guard,
    resolve_credential,
)
from src.operational.product_registration.dfe_cost_resolver import (  # noqa: E402
    build_authorized_index,
    cost_from_index,
)
from src.operational.product_registration.fiscal_resolver import (  # noqa: E402
    CONFIDENCE_HIGH,
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
MICROBATCH_SIZE = 5

SHEET = ROOT / "data" / "product_registration" / "FISCAL_PRODUTOS_A_CADASTRAR_118508.xlsx"
TAX_INPUT = ROOT / "data" / "product_registration" / "tax_tables_input"
OUT_DIR = ROOT / "data" / "product_registration" / "microbatch_02_118508"
OUT_DIR.mkdir(parents=True, exist_ok=True)
CHECKPOINT = ROOT / "data" / "product_registration" / "execution" / "checkpoint_118508.json"

# Exclusoes permanentes: BONO, NEGRESCO e os quatro do microbatch 01.
PERMANENT_EXCLUSIONS = {
    "7891000376928": "BONO_MODELO_FISCAL",
    "7891000377130": "NEGRESCO_PILOTO",
    "7891962076317": "PRODUTO_DO_INCIDENTE",
    "7896336000578": "MICROBATCH_01",
    "7892840817978": "MICROBATCH_01",
    "7892840824655": "MICROBATCH_01",
    "7892840824396": "MICROBATCH_01",
}

# Capitulos com regime proprio (bebida alcoolica, tabaco, farmacos, combustivel,
# pirotecnicos): FCP, monofasia e ST especifica exigem decisao contabil dedicada.
SENSITIVE_NCM_CHAPTERS = {"22": "BEBIDA_ALCOOLICA", "24": "TABACO", "30": "FARMACO", "27": "COMBUSTIVEL", "36": "PIROTECNICO"}

ST_BASIS_TABLE_HINT = "0000000061"

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

# Categorias reportadas
ALREADY_REGISTERED = "ALREADY_REGISTERED"
INVALID_GTIN = "INVALID_GTIN"
READY_HIGH = "READY_HIGH_CONFIDENCE"
READY_RISK = "READY_ASSUMED_RISK"
PENDING_DFE = "PENDING_DFE"
TAX_REVIEW = "TAX_REVIEW_REQUIRED"
MISSING_CEST = "MISSING_CEST"
MISSING_PRICE = "MISSING_PRICE"
COST_REVIEW = "COST_REVIEW_REQUIRED"

# Acima deste multiplo, a diferenca entre custo e venda indica erro de unidade na NF-e,
# nao margem real. Serve como rede de seguranca contra custo por embalagem.
IMPLAUSIBLE_MARGIN_FACTOR = 8.0


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


def render_report(
    payload: dict[str, Any],
    selection: list[dict[str, Any]],
    counts: Counter[str],
    generated_at: str,
) -> None:
    """Relatorio fiscal individual dos produtos selecionados, em markdown."""
    lines: list[str] = [
        "# Pre-flight fiscal — planilha 257 produtos — empresa 118508",
        "",
        f"- Gerado em: {generated_at}",
        f"- Planilha: `{payload['sheet']}` ({payload['sheetRows']} produtos, 1 cabecalho descartado)",
        f"- Credencial: `{payload['credential']['variable']}` (chave nunca exposta, sem fallback)",
        f"- Sentinela BONO vinculada a 118508: {payload['credential']['sentinelCompanyLinkConfirmed']}",
        f"- Catalogo lido: {payload['catalogScanned']} produtos | vinculos 118508: {payload['linkedTo118508']}",
        f"- EANs indexados em NF-e autorizadas: {payload['dfeIndexedEans']}",
        f"- Tabela ICMS-ST: `{payload['taxTables']['stReference']}` | PIS/COFINS: `{payload['taxTables']['pisCofinsReference']}`",
        "- Escritas na API neste pre-flight: **0**",
        "",
        "## Quantidades",
        "",
        "| Categoria | Produtos |",
        "| --- | --- |",
    ]
    for category in (
        ALREADY_REGISTERED,
        INVALID_GTIN,
        READY_HIGH,
        READY_RISK,
        PENDING_DFE,
        TAX_REVIEW,
        MISSING_CEST,
        MISSING_PRICE,
        COST_REVIEW,
    ):
        lines.append(f"| {category} | {counts.get(category, 0)} |")
    lines.append(f"| **TOTAL** | **{payload['sheetRows']}** |")

    lines += [
        "",
        "## Microbatch selecionado",
        "",
        f"{len(selection)} produtos (teto de {MICROBATCH_SIZE}), todos com custo comprovado por "
        "NF-e, unidade comercial unitaria, margem plausivel e base de ST com correspondencia "
        "integral na tabela local.",
        "",
    ]
    for index, item in enumerate(selection, start=1):
        cost = item["custo"]
        basis = item["baseFiscal"]
        nfe = cost["nfe"] or {}
        lines += [
            f"### {index}. {item['descricao']}",
            "",
            f"- Linha na planilha: {item['linha']}",
            f"- EAN: `{item['ean']}`",
            f"- NCM: `{item['ncm']}` | CEST: `{item['cest']}` (confirmados na NF-e quando declarados)",
            f"- Preco de venda (planilha): R$ {item['precoVenda']}",
            f"- Custo apurado no DF-e: R$ {cost['valor']} — `{cost['calculo']}`",
            f"- Unidade comercial da nota: `{cost['unidadeComercial']}` (unitaria: {cost['unidadeAtomica']}), "
            f"quantidade {cost['quantidade']}",
            f"- NF-e: {nfe.get('numero')}/{nfe.get('serie')} de {nfe.get('emissao')}, "
            f"fornecedor {nfe.get('fornecedor')}, cStat {nfe.get('protocoloCstat')}, "
            f"chave mascarada `{nfe.get('accessKeyMasked')}`",
            f"- Classificacao da entrada: **{basis['classificacaoEntrada']}** "
            f"(CST {basis['cstIcmsEntrada']}, ICMS-ST retido {basis['icmsStRetido']})",
            f"- Base ICMS: tabela `{basis['icmsTableReference']}` — saida CST "
            f"{basis['tributoIcms']['cstSaida']}, aliquota {basis['tributoIcms']['percentualIcmsSaida']}%, "
            f"FCP {basis['tributoIcms']['valorPercentualFcp']}%",
            f"- Base PIS/COFINS: tabela `{basis['pisCofinsTableReference']}` — "
            f"saida PIS {basis['tributoPisCofins']['cstPisSaida']} / COFINS "
            f"{basis['tributoPisCofins']['cstCofinsSaida']}",
            f"- CFOP: entrada {basis['cfopEntrada']} | saida {basis['cfopSaida']}",
            f"- Confianca: {basis['confidence']} | risco fiscal: {basis['fiscalRisk']} | "
            f"revisao contabil: {basis['requiresAccountantReview']}",
            f"- Justificativa: {basis['justificativa']}",
            f"- Hash do body: `{item['body']['hash']}`",
            "",
            "Body sanitizado (sem `empresaCodigo`, roteamento por CHAVE apenas):",
            "",
            "```json",
            json.dumps(item["body"]["preview"], ensure_ascii=False, indent=2),
            "```",
            "",
        ]

    (OUT_DIR / "PREFLIGHT_REPORT.md").write_text("\n".join(lines), encoding="utf-8")


def main() -> None:
    generated_at = datetime.now(timezone.utc).isoformat()
    resolver = FiscalResolver()

    print("=" * 78)
    print("PRE-FLIGHT PLANILHA FISCAL — 257 PRODUTOS — EMPRESA 118508 (READ-ONLY)")
    print("=" * 78)

    rows = load_sheet(SHEET)
    print(f"planilha: {SHEET.name} | produtos: {len(rows)}")

    credential = resolve_credential(COMPANY_CODE)
    if credential.variable_name != PROFILE:
        raise SystemExit(f"credencial fora do profile exigido: {credential.variable_name}")
    print(f"credencial: {credential.variable_name} (nunca impressa)")

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
    print(f"indice DF-e: {len(dfe_index)} EANs em notas autorizadas")

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
    print(f"catalogo: {len(catalog)} produtos | vinculos 118508: {len(linked_codes)} | checkpoint: {len(checkpoint)} EANs")
    print()

    evaluated: list[dict[str, Any]] = []
    counts: Counter[str] = Counter()

    for row in rows:
        flags: list[str] = []
        entry: dict[str, Any] = {
            "linha": row.line,
            "codigoPlanilha": row.raw_code,
            "ean": row.ean,
            "descricao": row.descricao,
            "precoVenda": row.preco_venda,
            "ncm": row.ncm,
            "cest": row.cest,
            "ncmZeroPreenchido": row.ncm_padded,
            "cestZeroPreenchido": row.cest_padded,
        }

        # 1. GTIN
        if not row.ean_valid:
            entry["categoria"] = INVALID_GTIN
            entry["motivo"] = row.ean_issues
            counts[INVALID_GTIN] += 1
            evaluated.append(entry)
            continue

        ean = row.ean

        # 2. Exclusoes e cadastro previo
        existing = catalog_by_barcode.get(ean)
        excluded = PERMANENT_EXCLUSIONS.get(ean)
        in_checkpoint = ean in checkpoint
        entry["exclusaoPermanente"] = excluded
        entry["existeNoCatalogo"] = bool(existing)
        entry["produtoCodigoExistente"] = int(existing.get("produtoCodigo") or 0) if existing else None
        entry["vinculadoA118508"] = bool(existing) and int(existing.get("produtoCodigo") or 0) in linked_codes
        entry["emCheckpoint"] = in_checkpoint

        if excluded or existing or in_checkpoint:
            entry["categoria"] = ALREADY_REGISTERED
            entry["motivo"] = excluded or ("EXISTE_NO_CATALOGO" if existing else "EM_CHECKPOINT")
            counts[ALREADY_REGISTERED] += 1
            evaluated.append(entry)
            continue

        # 3. Preco
        if not row.has_price:
            flags.append(MISSING_PRICE)

        # 4. Custo pelo DF-e
        cost_evidence = cost_from_index(ean, dfe_index)
        cost = float(cost_evidence.preco_custo) if cost_evidence.preco_custo is not None else None
        entry["custo"] = {
            "status": cost_evidence.status,
            "valor": cost,
            "source": "DFE" if cost_evidence.resolved else "PENDING_DFE",
            "unidadeComercial": cost_evidence.unidade_comercial,
            "unidadeAtomica": cost_evidence.unidade_atomica,
            "quantidade": float(cost_evidence.quantidade) if cost_evidence.quantidade else None,
            "motivoRevisao": cost_evidence.reason,
            "calculo": cost_evidence.calculo,
            "nfe": (
                {
                    "numero": cost_evidence.numero,
                    "serie": cost_evidence.serie,
                    "emissao": cost_evidence.emissao,
                    "fornecedor": cost_evidence.fornecedor,
                    "accessKeyMasked": cost_evidence.access_key_masked,
                    "itemLinha": cost_evidence.item_line,
                    "protocoloCstat": cost_evidence.protocolo_cstat,
                }
                if cost_evidence.resolved
                else None
            ),
        }
        if not cost_evidence.resolved:
            # Unidade nao unitaria e custo ausente sao situacoes distintas.
            flags.append(COST_REVIEW if cost is not None else PENDING_DFE)
        elif row.has_price:
            # Rede de seguranca contra custo por embalagem que passou pelos filtros.
            if cost > row.preco_venda:
                flags.append(COST_REVIEW)
                entry["custo"]["alerta"] = "CUSTO_ACIMA_DO_PRECO_DE_VENDA"
            elif cost > 0 and row.preco_venda / cost > IMPLAUSIBLE_MARGIN_FACTOR:
                flags.append(COST_REVIEW)
                entry["custo"]["alerta"] = (
                    f"MARGEM_IMPLAUSIVEL_{row.preco_venda / cost:.1f}x"
                )

        # 5. CEST
        if not row.has_cest:
            flags.append(MISSING_CEST)

        # 6. Categoria sensivel por capitulo de NCM
        chapter = (row.ncm or "")[:2]
        sensitive = SENSITIVE_NCM_CHAPTERS.get(chapter)
        entry["categoriaSensivel"] = sensitive

        # 7. Base fiscal pela evidencia de entrada
        item = (dfe_index.get(ean) or (None, None, {}))[2] or {}
        normalized = item.get("normalized_json") or {}
        icms_node = normalized.get("icms") or {}
        st_retido = icms_node.get("ICMS.vICMSSTRet")
        entry_rate = icms_node.get("ICMS.pICMS")
        evidence = EntryEvidence(
            cst_icms=icms_node.get("ICMS.CST"),
            icms_st_retido=float(st_retido) if st_retido else None,
            cest=normalized.get("cest") or row.cest,
            ncm=normalized.get("ncm") or row.ncm,
            cfop_fornecedor=normalized.get("cfop"),
            cst_pis=(normalized.get("pis") or {}).get("PIS.CST"),
            cst_cofins=(normalized.get("cofins") or {}).get("COFINS.CST"),
            invoice_reference=f"{cost_evidence.numero}/{cost_evidence.serie}"
            if cost_evidence.resolved
            else None,
        )
        classification = classify_entry(evidence)

        taxed_basis = None
        taxed_reference = None
        rate_match = "NOT_APPLICABLE"
        if classification != ST_PROVEN and entry_rate is not None:
            rate = float(entry_rate)
            rate_match, rate_rows = match_icms_by_entry_rate(
                icms_rows, cst_entrada="000", icms_entrada=rate, icms_saida=rate
            )
            if rate_match == MATCH_UNIQUE:
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
        cfop_entrada, cfop_saida = CFOP_SUBSTITUTED if classification == ST_PROVEN else CFOP_TAXED

        # NCM e CEST da NF-e prevalecem quando divergem da planilha.
        ncm_final = normalized.get("ncm") or row.ncm
        cest_final = normalized.get("cest") or row.cest
        entry["ncmDaNfe"] = normalized.get("ncm")
        entry["cestDaNfe"] = normalized.get("cest")
        entry["ncmDivergeDaPlanilha"] = bool(normalized.get("ncm")) and normalized["ncm"] != row.ncm
        entry["cestDivergeDaPlanilha"] = bool(normalized.get("cest")) and normalized["cest"] != row.cest

        # Escolher entre CEST da planilha e da NF-e e decisao fiscal, nao automatica.
        if entry["cestDivergeDaPlanilha"] or entry["ncmDivergeDaPlanilha"]:
            flags.append(TAX_REVIEW)
            entry["divergenciaClassificacao"] = (
                f"planilha NCM={row.ncm} CEST={row.cest} vs "
                f"NF-e NCM={normalized.get('ncm')} CEST={normalized.get('cest')}"
            )

        entry["baseFiscal"] = {
            "classificacaoEntrada": classification,
            "cstIcmsEntrada": evidence.cst_icms,
            "aliquotaIcmsEntrada": entry_rate,
            "icmsStRetido": evidence.icms_st_retido,
            "matchTabelaPorAliquota": rate_match,
            "icmsTableReference": decision.icms_table_reference,
            "tributoIcms": decision.icms_basis,
            "pisCofinsTableReference": decision.pis_cofins_table_reference,
            "tributoPisCofins": decision.pis_cofins_basis,
            "cfopEntrada": cfop_entrada,
            "cfopSaida": cfop_saida,
            "confidence": decision.confidence,
            "fiscalRisk": decision.fiscal_risk,
            "requiresAccountantReview": decision.requires_accountant_review,
            "justificativa": decision.justification,
            "blockers": decision.blockers,
        }

        if not decision.can_register:
            flags.append(TAX_REVIEW)
        if sensitive:
            flags.append(TAX_REVIEW)
            entry["baseFiscal"]["blockers"] = list(decision.blockers) + [
                f"CATEGORIA_SENSIVEL_{sensitive}"
            ]

        # 8. Body somente quando tudo esta resolvido
        body = None
        if not flags and cost_evidence.resolved and cost is not None and cest_final:
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
                "precoCompra": cost,
                "precoCusto": cost,
                "precoVenda": row.preco_venda,
                "centroCustoCodigo": COST_CENTER,
                "codigoBarras": ean,
                "codigoNcm": ncm_final,
                "codigoCest": cest_final,
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

        entry["body"] = {"ready": body is not None, "hash": body_hash(body) if body else None, "preview": body}

        if flags:
            # A categoria primaria segue a ordem de gravidade declarada.
            for category in (MISSING_PRICE, PENDING_DFE, COST_REVIEW, MISSING_CEST, TAX_REVIEW):
                if category in flags:
                    entry["categoria"] = category
                    break
            entry["flags"] = sorted(set(flags))
        else:
            entry["categoria"] = (
                READY_HIGH if decision.confidence == CONFIDENCE_HIGH else READY_RISK
            )
            entry["flags"] = []

        counts[entry["categoria"]] += 1
        for flag in set(flags):
            if flag != entry["categoria"]:
                counts[f"flag:{flag}"] += 1
        evaluated.append(entry)

    # --- Selecao do microbatch -------------------------------------------
    candidates = [
        e
        for e in evaluated
        if e["categoria"] in (READY_HIGH, READY_RISK) and e["body"]["ready"]
    ]
    candidates.sort(
        key=lambda e: (
            0 if e["categoria"] == READY_HIGH else 1,
            0 if e["baseFiscal"]["classificacaoEntrada"] == ST_PROVEN else 1,
            e["linha"],
        )
    )
    selection = candidates[:MICROBATCH_SIZE]

    print("QUANTIDADES")
    for category in (
        ALREADY_REGISTERED,
        INVALID_GTIN,
        READY_HIGH,
        READY_RISK,
        PENDING_DFE,
        TAX_REVIEW,
        MISSING_CEST,
        MISSING_PRICE,
        COST_REVIEW,
    ):
        print(f"   {category:24} {counts.get(category, 0):>4}")
    print("   --- flags adicionais (produto contado em outra categoria primaria) ---")
    for key, value in sorted(counts.items()):
        if key.startswith("flag:"):
            print(f"   {key:24} {value:>4}")
    print(f"   {'TOTAL':24} {sum(v for k, v in counts.items() if not k.startswith('flag:')):>4}")
    print()

    print(f"CANDIDATOS ELEGIVEIS: {len(candidates)} | MICROBATCH SELECIONADO: {len(selection)}")
    for item in selection:
        basis = item["baseFiscal"]
        margin = item["precoVenda"] / item["custo"]["valor"] if item["custo"]["valor"] else 0
        print(f"   linha {item['linha']:>4} | {item['ean']} | {item['descricao'][:40]}")
        print(f"        custo {item['custo']['valor']} ({item['custo']['unidadeComercial']}) | venda {item['precoVenda']}"
              f" | margem {margin:.2f}x | NCM {item['ncm']} CEST {item['cest']}")
        print(f"        entrada {basis['classificacaoEntrada']} CST {basis['cstIcmsEntrada']} | ICMS ref {basis['icmsTableReference']}"
              f" | conf {basis['confidence']} | risco {basis['fiscalRisk']}")
        print(f"        CFOP {basis['cfopEntrada']}/{basis['cfopSaida']} | hash {item['body']['hash'][:16]}...")
    print()

    payload = {
        "title": "PREFLIGHT PLANILHA FISCAL 257 — 118508",
        "generatedAt": generated_at,
        "sheet": SHEET.name,
        "sheetRows": len(rows),
        "empresa": COMPANY_CODE,
        "credential": {
            "variable": credential.variable_name,
            "keyExposed": False,
            "sentinelFound": guard.sentinel_found,
            "sentinelCompanyLinkConfirmed": guard.company_link_confirmed,
        },
        "taxTables": {
            "stReference": st_reference,
            "stMatch": st_status,
            "pisCofinsReference": pis_reference,
            "pisCofinsMatch": pis_status,
            "icmsRowsLoaded": len(icms_rows),
        },
        "dfeIndexedEans": len(dfe_index),
        "catalogScanned": len(catalog),
        "linkedTo118508": len(linked_codes),
        "checkpointEans": len(checkpoint),
        "counts": {k: v for k, v in sorted(counts.items())},
        "products": evaluated,
        "microbatchCandidates": len(candidates),
        "microbatch": selection,
        "apiWrites": 0,
        # O limite de 5 e teto, nao piso: um lote menor que passe todas as guardas
        # esta apto a escrita.
        "status": "READY_FOR_WRITE" if selection else "NOTHING_TO_WRITE",
    }
    (OUT_DIR / "preflight_sheet_257.json").write_text(
        json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    (OUT_DIR / "microbatch_selection.json").write_text(
        json.dumps(
            {
                "title": "MICROBATCH 02 SELECTION — 118508",
                "generatedAt": generated_at,
                "size": len(selection),
                "maxSize": MICROBATCH_SIZE,
                "apiWrites": 0,
                "products": selection,
                "status": payload["status"],
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )

    render_report(payload, selection, counts, generated_at)

    print("=" * 78)
    print(f"STATUS: {payload['status']}")
    print("API WRITES: 0")
    print(f"artefatos: {OUT_DIR}")


if __name__ == "__main__":
    main()
