"""Indice de tributacao de entrada agrupada por NCM e CEST.

Serve para sustentar a base fiscal de produto que nao tem NF-e propria. O CEST e o
codigo que identifica a mercadoria no regime de substituicao tributaria, portanto itens
de mesmo NCM e CEST recebem o mesmo tratamento. Quando os itens de um par divergem, ha
mais de uma base plausivel e o produto nao pode ser resolvido por analogia.
"""

from __future__ import annotations

from collections import defaultdict
from typing import Any

from src.operational.dfe import store

from .fiscal_resolver import EntryEvidence, classify_entry
from .product_family import commercial_family


def _mask_cnpj(cnpj: str | None) -> str | None:
    digits = "".join(c for c in str(cnpj or "") if c.isdigit())
    if len(digits) < 8:
        return None
    return f"{digits[:2]}***{digits[-4:]}"


def item_entry_evidence(item: dict[str, Any], invoice_reference: str | None = None) -> EntryEvidence:
    """Extrai a tributacao de entrada declarada em um item de NF-e."""
    icms = item.get("icms") or {}
    st_retido = icms.get("ICMS.vICMSSTRet")
    return EntryEvidence(
        cst_icms=icms.get("ICMS.CST"),
        icms_st_retido=float(st_retido) if st_retido else None,
        cest=str(item.get("cest") or "").strip() or None,
        ncm=str(item.get("ncm") or "").strip() or None,
        cfop_fornecedor=item.get("cfop"),
        cst_pis=(item.get("pis") or {}).get("PIS.CST"),
        cst_cofins=(item.get("cofins") or {}).get("COFINS.CST"),
        invoice_reference=invoice_reference,
    )


def build_ncm_cest_evidence(company_code: int) -> dict[tuple[str, str], list[dict[str, Any]]]:
    """Agrupa itens de NF-e autorizadas por (NCM, CEST) com a classificacao da entrada.

    Notas canceladas ou nao autorizadas ficam de fora. Item sem NCM ou sem CEST nao
    sustenta analogia e e ignorado: ausencia de CEST nao e CEST zero.
    """
    grouped: dict[tuple[str, str], list[dict[str, Any]]] = defaultdict(list)
    for document in store.list_documents(company_code):
        protocol = document.get("protocol") or {}
        if protocol.get("cancelled") is True or str(protocol.get("cStat") or "") != "100":
            continue
        reference = f"{document.get('nNF')}/{document.get('serie')}"
        for raw_item in store.load_items(document["id"]):
            item = raw_item.get("normalized_json") or {}
            ncm = str(item.get("ncm") or "").strip()
            cest = str(item.get("cest") or "").strip()
            if not ncm or not cest:
                continue
            evidence = item_entry_evidence(item, reference)
            icms = item.get("icms") or {}
            descricao = item.get("x_prod")
            grouped[(ncm, cest)].append(
                {
                    "classification": classify_entry(evidence),
                    "cstIcms": icms.get("ICMS.CST"),
                    "aliquotaEntrada": icms.get("ICMS.pICMS"),
                    "icmsStRetido": icms.get("ICMS.vICMSSTRet"),
                    "icmsStCobrado": icms.get("ICMS.vICMSST"),
                    "descricao": descricao,
                    "familiaComercial": commercial_family(descricao or ""),
                    "nfe": reference,
                    "fornecedor": document.get("issuer_name"),
                    "fornecedorCnpjMascarado": _mask_cnpj(document.get("issuer_cnpj")),
                    "ean": item.get("c_ean"),
                }
            )
    return grouped


def summarize_evidence(entries: list[dict[str, Any]]) -> dict[str, Any]:
    """Resume a evidência de um par NCM+CEST para registro e decisão.

    Contar itens não basta: uma nota com dez itens do mesmo fornecedor não diz mais sobre
    o regime da mercadoria do que uma nota com um item. Por isso notas e fornecedores
    são contados separadamente.
    """
    cst_distribution: dict[str, int] = defaultdict(int)
    families: dict[str, int] = defaultdict(int)
    for entry in entries:
        cst_distribution[str(entry.get("cstIcms") or "SEM_CST")] += 1
        families[str(entry.get("familiaComercial") or "NAO_RECONHECIDA")] += 1
    return {
        "itens": len(entries),
        "notasDistintas": len({e.get("nfe") for e in entries}),
        "fornecedoresDistintos": len(
            {e.get("fornecedorCnpjMascarado") for e in entries if e.get("fornecedorCnpjMascarado")}
        ),
        "classificacoes": sorted({e["classification"] for e in entries}),
        "distribuicaoCst": dict(sorted(cst_distribution.items())),
        "familiasObservadas": dict(sorted(families.items(), key=lambda kv: -kv[1])),
        "itensComStRetida": sum(1 for e in entries if e.get("icmsStRetido")),
        "itensComStCobrada": sum(1 for e in entries if e.get("icmsStCobrado")),
    }
