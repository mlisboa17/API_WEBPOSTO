"""Parser de produtos da NF-e — preserva zeros (EAN/NCM/CEST como string)."""

from __future__ import annotations

from decimal import Decimal, InvalidOperation
from typing import Any

from lxml import etree


def _txt(el: etree._Element | None) -> str | None:
    if el is None or el.text is None:
        return None
    return el.text.strip()


def _dec(value: str | None) -> float | None:
    if value is None or value == "":
        return None
    try:
        return float(Decimal(value.replace(",", ".")))
    except (InvalidOperation, ValueError):
        return None


def _ncm(v: str | None) -> str | None:
    if not v:
        return None
    d = "".join(ch for ch in v if ch.isdigit()).zfill(8)[-8:]
    return d if len(d) == 8 else d


def _cest(v: str | None) -> str | None:
    if not v:
        return None
    d = "".join(ch for ch in v if ch.isdigit())
    if not d:
        return None
    return d.zfill(7)[-7:]


def _ean(v: str | None) -> str | None:
    if v is None:
        return None
    s = v.strip()
    if s in {"", "SEM GTIN", "sem gtin"}:
        return None
    # preserva zeros à esquerda — string
    return "".join(ch for ch in s if ch.isdigit()) or s


def _find_tax(prod_parent: etree._Element, *names: str) -> dict[str, Any]:
    out: dict[str, Any] = {}
    imposto = prod_parent.find("{*}imposto")
    if imposto is None:
        return out
    for name in names:
        node = imposto.find(f".//{{*}}{name}")
        if node is not None:
            for child in node.iter():
                if child is node:
                    continue
                local = etree.QName(child).localname
                if child.text and child.text.strip():
                    out[f"{name}.{local}"] = child.text.strip()
    return out


def parse_items_from_xml(data: bytes) -> list[dict[str, Any]]:
    parser = etree.XMLParser(resolve_entities=False, no_network=True, load_dtd=False)
    root = etree.fromstring(data, parser=parser)
    dets = root.findall(".//{*}det")
    items: list[dict[str, Any]] = []
    for det in dets:
        n_item = int(det.get("nItem") or len(items) + 1)
        prod = det.find("{*}prod")
        if prod is None:
            continue
        raw = {
            "cProd": _txt(prod.find("{*}cProd")),
            "xProd": _txt(prod.find("{*}xProd")),
            "cEAN": _ean(_txt(prod.find("{*}cEAN"))),
            "cEANTrib": _ean(_txt(prod.find("{*}cEANTrib"))),
            "NCM": _ncm(_txt(prod.find("{*}NCM"))),
            "CEST": _cest(_txt(prod.find("{*}CEST"))),
            "CFOP": _txt(prod.find("{*}CFOP")),
            "uCom": _txt(prod.find("{*}uCom")),
            "uTrib": _txt(prod.find("{*}uTrib")),
            "qCom": _txt(prod.find("{*}qCom")),
            "qTrib": _txt(prod.find("{*}qTrib")),
            "vUnCom": _txt(prod.find("{*}vUnCom")),
            "vProd": _txt(prod.find("{*}vProd")),
            "vDesc": _txt(prod.find("{*}vDesc")),
            "vFrete": _txt(prod.find("{*}vFrete")),
            "vSeg": _txt(prod.find("{*}vSeg")),
            "vOutro": _txt(prod.find("{*}vOutro")),
            "indTot": _txt(prod.find("{*}indTot")),
            "xPed": _txt(prod.find("{*}xPed")),
        }
        taxes = _find_tax(det, "ICMS", "IPI", "PIS", "COFINS")
        origem = None
        cst = None
        for k, v in taxes.items():
            if k.endswith(".orig"):
                origem = v
            if k.endswith(".CST") or k.endswith(".CSOSN"):
                cst = v

        normalized = {
            "c_prod": raw["cProd"],
            "x_prod": raw["xProd"],
            "c_ean": raw["cEAN"],
            "c_ean_trib": raw["cEANTrib"],
            "ncm": raw["NCM"],
            "cest": raw["CEST"],
            "cfop": raw["CFOP"],
            "origem": origem,
            "cst_csosn": cst,
            "u_com": raw["uCom"],
            "u_trib": raw["uTrib"],
            "q_com": _dec(raw["qCom"]),
            "q_trib": _dec(raw["qTrib"]),
            "v_un_com": _dec(raw["vUnCom"]),
            "v_prod": _dec(raw["vProd"]),
            "v_desc": _dec(raw["vDesc"]),
            "v_frete": _dec(raw["vFrete"]),
            "v_seg": _dec(raw["vSeg"]),
            "v_outro": _dec(raw["vOutro"]),
            "icms": {k: v for k, v in taxes.items() if k.startswith("ICMS")},
            "ipi": {k: v for k, v in taxes.items() if k.startswith("IPI")},
            "pis": {k: v for k, v in taxes.items() if k.startswith("PIS")},
            "cofins": {k: v for k, v in taxes.items() if k.startswith("COFINS")},
        }
        items.append(
            {
                "line_number": n_item,
                "raw_json": raw,
                "normalized_json": normalized,
                **{k: normalized[k] for k in (
                    "c_prod", "x_prod", "c_ean", "c_ean_trib", "ncm", "cest", "cfop",
                    "origem", "cst_csosn", "u_com", "u_trib", "q_com", "q_trib",
                    "v_un_com", "v_prod", "v_desc", "v_frete", "v_seg", "v_outro",
                )},
            }
        )
    return items
