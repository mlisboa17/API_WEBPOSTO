"""Master Supplier MDM — normalização e deduplicação F01.4-C."""
from __future__ import annotations

import re
import unicodedata
from typing import Any

CANONICAL_GROUPS: dict[str, tuple[str, ...]] = {
    "IPIRANGA": ("IPIRANGA", "IPIRANGA S.A", "IPIRANGA DISTRIBUIDORA", "IPIRANGA DISTRIBUIDORA DE PETROLEO"),
    "AMBEV": ("AMBEV", "AMBEV S.A", "CIA DE BEBIDAS AMBEV", "COMPANHIA DE BEBIDAS AMBEV"),
    "VIBRA": ("VIBRA ENERGIA", "VIBRA ENERGIA S.A", "VIBRA"),
    "BR DISTRIBUIDORA": ("BR DISTRIBUIDORA", "PETROBRAS DISTRIBUIDORA", "BR DISTRIBUIDORA S.A"),
}

_SUFFIXES = (
    r"\bS\.?A\.?\b",
    r"\bLTDA\.?\b",
    r"\bME\b",
    r"\bEPP\b",
    r"\bEIRELI\b",
    r"\bCIA\b",
    r"\bCOMPANHIA\b",
    r"\bDE\b",
    r"\bDO\b",
    r"\bDA\b",
    r"\bDOS\b",
    r"\bDAS\b",
)


def _strip_accents(text: str) -> str:
    nfkd = unicodedata.normalize("NFKD", text)
    return "".join(c for c in nfkd if not unicodedata.combining(c))


def normalize_supplier_key(name: str) -> str:
    """Chave determinística para agrupamento — sem inferência externa."""
    if not name:
        return ""
    s = _strip_accents(str(name).upper().strip())
    s = re.sub(r"[^\w\s]", " ", s)
    for pat in _SUFFIXES:
        s = re.sub(pat, " ", s, flags=re.IGNORECASE)
    s = re.sub(r"\s+", " ", s).strip()
    return s


def canonical_supplier_name(name: str) -> str:
    """Nome canônico rastreável via regras determinísticas."""
    key = normalize_supplier_key(name)
    if not key:
        return ""
    for canonical, aliases in CANONICAL_GROUPS.items():
        alias_keys = {normalize_supplier_key(a) for a in aliases}
        if key in alias_keys or any(key.startswith(a) or a.startswith(key) for a in alias_keys if len(a) >= 4):
            return canonical
    tokens = key.split()
    if len(tokens) >= 2 and tokens[0] in {"REF", "NF"}:
        return " ".join(tokens[: min(4, len(tokens))])
    return " ".join(tokens[:3]) if len(tokens) > 3 else key


def extract_supplier_from_expense_description(descricao: str) -> str | None:
    """Extrai fornecedor de descricaoDocumento quando padrão REF NF é explícito."""
    if not descricao:
        return None
    text = str(descricao).strip()
    if "REF NF:" not in text.upper() and " - " not in text:
        return None
    parts = [p.strip() for p in text.split(" - ") if p.strip()]
    if len(parts) >= 2 and parts[0].upper().startswith("REF NF"):
        candidate = parts[1] if len(parts) > 1 else parts[-1]
        return candidate if len(candidate) >= 3 else None
    return None


def supplier_type_from_document(documento: str) -> str:
    digits = re.sub(r"\D", "", documento or "")
    if len(digits) == 14:
        return "CNPJ"
    if len(digits) == 11:
        return "CPF"
    return "NAO_IDENTIFICADO"


def compute_supplier_coverage_score(row: dict[str, Any]) -> int:
    score = 0
    if row.get("supplierName") or row.get("nomeFornecedor") or row.get("fornecedor"):
        score += 25
    doc = row.get("supplierDocument") or row.get("cpfCnpjFornecedor") or row.get("documento")
    if doc and re.sub(r"\D", "", str(doc)):
        score += 25
    if row.get("supplierCode") or row.get("fornecedorCodigo"):
        score += 25
    if row.get("empresaCodigo"):
        score += 25
    return min(100, score)


def build_master_supplier_record(
    *,
    supplier_code: str | int | None,
    supplier_name: str,
    supplier_document: str = "",
    empresa_origem: str = "",
    aliases: list[str] | None = None,
    primeira_compra: str = "",
    ultima_compra: str = "",
    coverage_score: int = 0,
    ativo: bool = True,
) -> dict[str, Any]:
    canonical = canonical_supplier_name(supplier_name)
    key = normalize_supplier_key(supplier_name)
    alias_set = sorted({supplier_name, canonical, *(aliases or [])} - {""})
    return {
        "supplierId": str(supplier_code) if supplier_code else key[:32] or canonical,
        "supplierCode": str(supplier_code or ""),
        "supplierName": supplier_name,
        "supplierCanonicalName": canonical,
        "supplierAlias": alias_set,
        "supplierGroup": canonical,
        "supplierDocument": supplier_document,
        "supplierType": supplier_type_from_document(supplier_document),
        "ativo": ativo,
        "primeiraCompra": primeira_compra,
        "ultimaCompra": ultima_compra,
        "empresaOrigem": empresa_origem,
        "supplierCoverageScore": coverage_score,
    }
