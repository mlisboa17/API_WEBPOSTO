"""Importação manual de XML/ZIP com proteções XXE, ZIP bomb e path traversal."""

from __future__ import annotations

import hashlib
import io
import os
import re
import zipfile
from dataclasses import dataclass, field
from typing import Any

from lxml import etree

# Defaults seguros (documentar; não alterar .env nesta entrega)
MAX_UPLOAD_BYTES = int(os.environ.get("DFE_MAX_UPLOAD_BYTES", str(50 * 1024 * 1024)))
MAX_XML_BYTES = int(os.environ.get("DFE_MAX_XML_BYTES", str(5 * 1024 * 1024)))
MAX_ZIP_BYTES = int(os.environ.get("DFE_MAX_ZIP_BYTES", str(50 * 1024 * 1024)))
MAX_FILES_IN_UPLOAD = int(os.environ.get("DFE_MAX_FILES_IN_UPLOAD", "30"))
MAX_ENTRIES_IN_ZIP = int(os.environ.get("DFE_MAX_ENTRIES_IN_ZIP", "500"))
MAX_XML_IN_ZIP = int(os.environ.get("DFE_MAX_XML_IN_ZIP", "400"))
MAX_UNCOMPRESSED_TOTAL = int(os.environ.get("DFE_MAX_UNCOMPRESSED_TOTAL", str(100 * 1024 * 1024)))
MAX_UNCOMPRESSED_RATIO = float(os.environ.get("DFE_MAX_UNCOMPRESSED_RATIO", "200"))
MAX_ZIP_DEPTH = int(os.environ.get("DFE_MAX_ZIP_DEPTH", "8"))
ALLOW_NESTED_ZIP = os.environ.get("DFE_ALLOW_NESTED_ZIP", "false").lower() in {"1", "true", "yes"}

_ACCESS_KEY_RE = re.compile(r"^\d{44}$")


class ImportErrorDFe(Exception):
    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code
        self.message = message


@dataclass
class ExpandedEntry:
    """Uma entrada candidata (XML) ou ignorada/rejeitada do ZIP/upload."""

    source_file: str
    relative_path: str
    status: str  # READY | IGNORED_NON_XML | FAILED | …
    data: bytes | None = None
    size: int = 0
    message: str | None = None
    code: str | None = None


@dataclass
class ExpandResult:
    source_file: str
    source_kind: str  # XML | ZIP
    entries: list[ExpandedEntry] = field(default_factory=list)
    fatal_code: str | None = None
    fatal_message: str | None = None

    @property
    def xml_ready(self) -> list[ExpandedEntry]:
        return [e for e in self.entries if e.status == "READY" and e.data is not None]


def _safe_parser() -> etree.XMLParser:
    return etree.XMLParser(
        resolve_entities=False,
        no_network=True,
        dtd_validation=False,
        load_dtd=False,
        huge_tree=False,
    )


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def mask_access_key(key: str | None) -> str | None:
    if not key:
        return None
    digits = "".join(ch for ch in key if ch.isdigit())
    if len(digits) < 12:
        return "***"
    return f"{digits[:6]}…{digits[-4:]}"


def sanitize_zip_path(raw: str) -> str | None:
    """Normaliza caminho ZIP; retorna None se perigoso."""
    name = (raw or "").replace("\\", "/").strip()
    if not name or name.endswith("/"):
        return None
    # strip leading ./
    while name.startswith("./"):
        name = name[2:]
    if name.startswith("/") or name.startswith("../") or "/../" in f"/{name}/" or name == "..":
        return None
    if ".." in name.split("/"):
        return None
    if ":" in name:  # Windows absolute / drive
        return None
    parts = [p for p in name.split("/") if p and p != "."]
    if not parts:
        return None
    if len(parts) > MAX_ZIP_DEPTH + 1:
        return None
    # ignora metadados macOS
    if parts[0] == "__MACOSX" or any(p.startswith("._") for p in parts):
        return None
    return "/".join(parts)


def detect_document_type(root: etree._Element) -> tuple[str, str]:
    tag = etree.QName(root).localname if isinstance(root.tag, str) else str(root.tag)
    text = etree.tostring(root, encoding="unicode")
    if "procEventoNFe" in text or tag.endswith("procEventoNFe"):
        return "PROC_EVENTO_NFE", "procEventoNFe"
    if "resNFe" in text or tag.endswith("resNFe"):
        return "RES_NFE", "resNFe"
    if "nfeProc" in text or "procNFe" in text or tag in {"nfeProc", "NFe"}:
        return "PROC_NFE", "procNFe"
    return "OTHER", tag


def extract_access_key(root: etree._Element) -> str | None:
    for xpath in (".//{*}chNFe", ".//{*}infNFe"):
        nodes = root.findall(xpath)
        for n in nodes:
            if etree.QName(n).localname == "chNFe" and n.text:
                key = "".join(ch for ch in n.text if ch.isdigit())
                if _ACCESS_KEY_RE.match(key):
                    return key
            if etree.QName(n).localname == "infNFe":
                wid = n.get("Id") or ""
                key = "".join(ch for ch in wid if ch.isdigit())
                if _ACCESS_KEY_RE.match(key):
                    return key
    return None


def extract_parties(root: etree._Element) -> dict[str, str | None]:
    def _txt(path: str) -> str | None:
        nodes = root.findall(path)
        for n in nodes:
            if n.text and n.text.strip():
                return n.text.strip()
        return None

    def _cnpj(path: str) -> str | None:
        t = _txt(path)
        if not t:
            return None
        d = "".join(ch for ch in t if ch.isdigit())
        return d if len(d) == 14 else None

    return {
        "issuer_cnpj": _cnpj(".//{*}emit/{*}CNPJ"),
        "issuer_name": _txt(".//{*}emit/{*}xNome") or _txt(".//{*}emit/{*}xFant"),
        "recipient_cnpj": _cnpj(".//{*}dest/{*}CNPJ"),
        "nNF": _txt(".//{*}ide/{*}nNF"),
        "serie": _txt(".//{*}ide/{*}serie"),
        "vNF": _txt(".//{*}total/{*}ICMSTot/{*}vNF") or _txt(".//{*}vNF"),
    }


def extract_protocol(root: etree._Element) -> dict[str, Any]:
    c_stat = None
    n_prot = None
    for n in root.findall(".//{*}cStat"):
        c_stat = (n.text or "").strip()
        break
    for n in root.findall(".//{*}nProt"):
        n_prot = (n.text or "").strip()
        break
    cancelled = False
    for n in root.findall(".//{*}tpEvento"):
        if (n.text or "").strip() in {"110111", "110112"}:
            cancelled = True
    return {"cStat": c_stat, "nProt": n_prot, "cancelled": cancelled}


def parse_xml_bytes(data: bytes) -> dict[str, Any]:
    if len(data) > MAX_XML_BYTES:
        raise ImportErrorDFe("XML_TOO_LARGE", "XML excede limite")
    head = data[:4000].upper()
    if b"<!DOCTYPE" in head or b"<!ENTITY" in head:
        raise ImportErrorDFe("INVALID_XML", "DOCTYPE/ENTITY não permitido (proteção XXE)")
    try:
        root = etree.fromstring(data, parser=_safe_parser())
    except etree.XMLSyntaxError as exc:
        raise ImportErrorDFe("INVALID_XML", "XML mal formado") from exc

    doc_type, schema = detect_document_type(root)
    access_key = extract_access_key(root)
    parties = extract_parties(root)
    proto = extract_protocol(root)
    issued_at = None
    for n in root.findall(".//{*}dhEmi") + root.findall(".//{*}dEmi"):
        issued_at = (n.text or "").strip()
        break

    status = "VALIDATED"
    if proto.get("cancelled"):
        status = "CANCELLED"
    elif doc_type == "PROC_NFE" and proto.get("cStat") and proto["cStat"] not in {"100", "150"}:
        status = "REJECTED"
    elif doc_type == "OTHER":
        status = "UNSUPPORTED_SCHEMA"

    v_nf = None
    if parties.get("vNF"):
        try:
            v_nf = float(parties["vNF"].replace(",", "."))
        except ValueError:
            v_nf = None

    return {
        "document_type": doc_type,
        "schema_name": schema,
        "access_key": access_key,
        "access_key_masked": mask_access_key(access_key),
        "issuer_cnpj": parties.get("issuer_cnpj"),
        "issuer_name": parties.get("issuer_name"),
        "recipient_cnpj": parties.get("recipient_cnpj"),
        "nNF": parties.get("nNF"),
        "serie": parties.get("serie"),
        "vNF": v_nf,
        "issued_at": issued_at,
        "protocol": proto,
        "status": status,
        "xml_sha256": sha256_bytes(data),
        "root_tag": etree.QName(root).localname if isinstance(root.tag, str) else "unknown",
    }


def _is_zip_bytes(data: bytes, filename: str) -> bool:
    name = (filename or "").lower()
    return name.endswith(".zip") or data[:2] == b"PK"


def _is_xml_name(path: str) -> bool:
    return path.lower().endswith(".xml")


def expand_upload_detailed(filename: str, data: bytes) -> ExpandResult:
    """Expande um upload (XML ou ZIP) com resultados por entrada — falha parcial suportada."""
    source = filename or "upload.bin"
    if len(data) > MAX_UPLOAD_BYTES:
        return ExpandResult(
            source_file=source,
            source_kind="UNKNOWN",
            fatal_code="UPLOAD_TOO_LARGE",
            fatal_message="arquivo excede limite de upload",
        )

    if _is_zip_bytes(data, source):
        return _expand_zip(source, data)

    # arquivo avulso
    if not _is_xml_name(source) and not data.lstrip().startswith(b"<?xml") and not data.lstrip().startswith(b"<"):
        return ExpandResult(
            source_file=source,
            source_kind="OTHER",
            entries=[
                ExpandedEntry(
                    source_file=source,
                    relative_path=source,
                    status="IGNORED_NON_XML",
                    size=len(data),
                    code="IGNORED_NON_XML",
                    message="arquivo não é XML",
                )
            ],
        )
    if len(data) > MAX_XML_BYTES:
        return ExpandResult(
            source_file=source,
            source_kind="XML",
            entries=[
                ExpandedEntry(
                    source_file=source,
                    relative_path=source,
                    status="FAILED",
                    size=len(data),
                    code="XML_TOO_LARGE",
                    message="XML excede limite",
                )
            ],
        )
    return ExpandResult(
        source_file=source,
        source_kind="XML",
        entries=[
            ExpandedEntry(
                source_file=source,
                relative_path=os.path.basename(source),
                status="READY",
                data=data,
                size=len(data),
            )
        ],
    )


def _expand_zip(source: str, data: bytes) -> ExpandResult:
    result = ExpandResult(source_file=source, source_kind="ZIP")
    if len(data) > MAX_ZIP_BYTES:
        result.fatal_code = "ZIP_TOO_LARGE"
        result.fatal_message = "ZIP excede limite"
        return result
    if data[:2] != b"PK":
        result.fatal_code = "ZIP_INVALID"
        result.fatal_message = "assinatura ZIP inválida"
        return result
    try:
        zf = zipfile.ZipFile(io.BytesIO(data))
    except zipfile.BadZipFile:
        result.fatal_code = "ZIP_INVALID"
        result.fatal_message = "ZIP inválido ou corrompido"
        return result

    infos = zf.infolist()
    if len(infos) > MAX_ENTRIES_IN_ZIP:
        result.fatal_code = "ZIP_TOO_MANY_FILES"
        result.fatal_message = f"ZIP com mais de {MAX_ENTRIES_IN_ZIP} entradas"
        return result

    total_uncomp = 0
    xml_count = 0
    for info in infos:
        if info.is_dir():
            continue
        # symlink / special
        if getattr(info, "external_attr", 0) and (info.external_attr >> 16) & 0o170000 == 0o120000:
            result.entries.append(
                ExpandedEntry(
                    source_file=source,
                    relative_path=info.filename,
                    status="FAILED",
                    code="ZIP_SYMLINK",
                    message="symlink não permitido",
                )
            )
            continue

        safe = sanitize_zip_path(info.filename)
        if safe is None:
            result.entries.append(
                ExpandedEntry(
                    source_file=source,
                    relative_path=info.filename.replace("\\", "/")[:200],
                    status="FAILED",
                    code="ZIP_PATH_TRAVERSAL",
                    message="caminho rejeitado",
                )
            )
            continue

        if not _is_xml_name(safe):
            # ZIP aninhado
            if safe.lower().endswith(".zip") and not ALLOW_NESTED_ZIP:
                result.entries.append(
                    ExpandedEntry(
                        source_file=source,
                        relative_path=safe,
                        status="IGNORED_NON_XML",
                        size=info.file_size,
                        code="NESTED_ZIP_FORBIDDEN",
                        message="ZIP dentro de ZIP não permitido",
                    )
                )
            else:
                result.entries.append(
                    ExpandedEntry(
                        source_file=source,
                        relative_path=safe,
                        status="IGNORED_NON_XML",
                        size=info.file_size,
                        code="IGNORED_NON_XML",
                        message="entrada não XML ignorada",
                    )
                )
            continue

        if info.file_size > MAX_XML_BYTES:
            result.entries.append(
                ExpandedEntry(
                    source_file=source,
                    relative_path=safe,
                    status="FAILED",
                    size=info.file_size,
                    code="ZIP_BOMB",
                    message="XML interno excede limite",
                )
            )
            continue
        if info.compress_size and info.file_size / max(info.compress_size, 1) > MAX_UNCOMPRESSED_RATIO:
            result.entries.append(
                ExpandedEntry(
                    source_file=source,
                    relative_path=safe,
                    status="FAILED",
                    size=info.file_size,
                    code="ZIP_BOMB",
                    message="taxa de compressão suspeita",
                )
            )
            continue

        total_uncomp += info.file_size
        if total_uncomp > MAX_UNCOMPRESSED_TOTAL:
            result.entries.append(
                ExpandedEntry(
                    source_file=source,
                    relative_path=safe,
                    status="FAILED",
                    code="ZIP_BOMB",
                    message="tamanho descompactado excessivo",
                )
            )
            break

        if xml_count >= MAX_XML_IN_ZIP:
            result.entries.append(
                ExpandedEntry(
                    source_file=source,
                    relative_path=safe,
                    status="FAILED",
                    code="ZIP_TOO_MANY_XML",
                    message="limite de XMLs no ZIP atingido",
                )
            )
            continue

        try:
            raw = zf.read(info)
        except Exception:
            result.entries.append(
                ExpandedEntry(
                    source_file=source,
                    relative_path=safe,
                    status="FAILED",
                    code="ZIP_READ_ERROR",
                    message="falha ao ler entrada",
                )
            )
            continue

        xml_count += 1
        result.entries.append(
            ExpandedEntry(
                source_file=source,
                relative_path=safe,
                status="READY",
                data=raw,
                size=len(raw),
            )
        )

    if not result.xml_ready and not result.fatal_code:
        # só ignorados/falhas — ZIP “válido” mas sem XML útil
        result.fatal_code = "ZIP_EMPTY"
        result.fatal_message = "nenhum XML válido encontrado no ZIP"
    return result


def expand_upload(filename: str, data: bytes) -> list[tuple[str, bytes]]:
    """Compat: retorna apenas XMLs READY. Erros fatais levantam ImportErrorDFe."""
    detailed = expand_upload_detailed(filename, data)
    if detailed.fatal_code and not detailed.xml_ready:
        raise ImportErrorDFe(detailed.fatal_code, detailed.fatal_message or "falha no upload")
    return [(e.relative_path, e.data or b"") for e in detailed.xml_ready]
