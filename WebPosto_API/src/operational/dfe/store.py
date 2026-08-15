"""Persistência local DF-e (metadados JSON + referências a segredos/XML cifrados)."""

from __future__ import annotations

import json
import threading
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[3]
STORE_DIR = ROOT / "data" / "dfe_store"
DOCS_DIR = STORE_DIR / "documents"
ITEMS_DIR = STORE_DIR / "items"
CERTS_DIR = STORE_DIR / "certificates"
SYNC_DIR = STORE_DIR / "sync_state"
AUDIT_DIR = STORE_DIR / "audit"

_lock = threading.RLock()
_store_root: Path | None = None


def _root() -> Path:
    return _store_root or STORE_DIR


def store_root() -> Path:
    """Raiz atual do store DF-e (produção ou isolamento de teste)."""
    return _root()


def reset_store_for_tests(tmp: Path) -> None:
    global _store_root
    _store_root = tmp
    for sub in ("documents", "items", "certificates", "sync_state", "audit"):
        (tmp / sub).mkdir(parents=True, exist_ok=True)


def restore_store_after_tests() -> None:
    global _store_root
    _store_root = None


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def new_id(prefix: str) -> str:
    return f"{prefix}_{uuid.uuid4().hex[:12]}"


def _ensure() -> None:
    r = _root()
    for sub in ("documents", "items", "certificates", "sync_state", "audit"):
        (r / sub).mkdir(parents=True, exist_ok=True)


def _atomic(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(payload, ensure_ascii=False, indent=2, default=str), encoding="utf-8")
    tmp.replace(path)


SENSITIVE_KEYS = {
    "password",
    "senha",
    "pfx",
    "pfx_bytes",
    "pfxBase64",
    "certificate_bytes",
    "ciphertext",
    "ciphertext_b64",
    "private_key",
    "apiKey",
    "token",
    "CHAVE",
}


def redact(doc: dict[str, Any]) -> dict[str, Any]:
    out = json.loads(json.dumps(doc, default=str))

    def _walk(o: Any) -> Any:
        if isinstance(o, dict):
            return {k: ("***" if k in SENSITIVE_KEYS else _walk(v)) for k, v in o.items() if k not in SENSITIVE_KEYS or k.endswith("_id")}
        if isinstance(o, list):
            return [_walk(x) for x in o]
        return o

    cleaned = _walk(out)
    # garantir remoção total
    if isinstance(cleaned, dict):
        for k in list(cleaned.keys()):
            if k in SENSITIVE_KEYS:
                cleaned.pop(k, None)
    return cleaned


def append_audit(
    *,
    company_code: int | None,
    action: str,
    actor: str,
    target_type: str | None = None,
    target_id: str | None = None,
    detail: dict[str, Any] | None = None,
) -> dict[str, Any]:
    with _lock:
        _ensure()
        entry = {
            "id": new_id("dfe_aud"),
            "company_code": company_code,
            "action": action,
            "actor": actor,
            "target_type": target_type,
            "target_id": target_id,
            "detail_json": redact(detail or {}),
            "created_at": _now(),
        }
        _atomic(_root() / "audit" / f"{entry['id']}.json", entry)
        return entry


def save_certificate(doc: dict[str, Any]) -> dict[str, Any]:
    with _lock:
        _ensure()
        clean = redact(doc)
        # never persist raw secrets
        for k in ("pfx_bytes", "password", "pfxBase64", "senha"):
            clean.pop(k, None)
        _atomic(_root() / "certificates" / f"{clean['id']}.json", clean)
        return clean


def load_certificate(cert_id: str) -> dict[str, Any] | None:
    path = _root() / "certificates" / f"{cert_id}.json"
    if not path.is_file():
        return None
    return json.loads(path.read_text(encoding="utf-8"))


def list_certificates(company_code: int | None = None) -> list[dict[str, Any]]:
    _ensure()
    items = []
    for path in (_root() / "certificates").glob("dfe_cert_*.json"):
        try:
            doc = json.loads(path.read_text(encoding="utf-8"))
        except Exception:
            continue
        if company_code is not None and int(doc.get("company_code") or 0) != company_code:
            continue
        items.append(doc)
    return sorted(items, key=lambda x: x.get("created_at") or "", reverse=True)


def certificate_public_view(doc: dict[str, Any]) -> dict[str, Any]:
    """Resposta API — somente metadados."""
    return {
        "certificateId": doc.get("id"),
        "empresaCodigo": doc.get("company_code"),
        "cnpj": doc.get("extracted_cnpj") or doc.get("cnpj"),
        "sujeito": doc.get("subject"),
        "emissor": doc.get("issuer"),
        "numeroSerie": doc.get("serial_number"),
        "fingerprintSha256": doc.get("fingerprint_sha256"),
        "validadeInicial": doc.get("valid_from"),
        "validadeFinal": doc.get("valid_to"),
        "status": doc.get("status"),
        "diasParaVencimento": doc.get("days_to_expiry"),
        "ultimaValidacao": doc.get("last_checked_at"),
        "encryptionKeyVersion": doc.get("encryption_key_version"),
        "secretVersion": doc.get("secret_version"),
        "reencryptStatus": doc.get("reencrypt_status"),
        "disabled": bool(doc.get("disabled")),
    }


def save_document(doc: dict[str, Any]) -> dict[str, Any]:
    with _lock:
        _ensure()
        clean = redact(doc)
        _atomic(_root() / "documents" / f"{clean['id']}.json", clean)
        return clean


def load_document(doc_id: str) -> dict[str, Any] | None:
    path = _root() / "documents" / f"{doc_id}.json"
    if not path.is_file():
        return None
    return json.loads(path.read_text(encoding="utf-8"))


def list_documents(company_code: int | None = None) -> list[dict[str, Any]]:
    _ensure()
    items = []
    for path in (_root() / "documents").glob("dfe_doc_*.json"):
        try:
            doc = json.loads(path.read_text(encoding="utf-8"))
        except Exception:
            continue
        if company_code is not None and int(doc.get("company_code") or 0) != company_code:
            continue
        items.append(doc)
    return sorted(items, key=lambda x: x.get("received_at") or "", reverse=True)


def find_duplicate(
    *,
    company_code: int,
    access_key: str | None,
    document_type: str,
    xml_sha256: str,
    nsu: str | None = None,
) -> dict[str, Any] | None:
    for doc in list_documents(company_code):
        if nsu and doc.get("nsu") == nsu:
            return doc
        # Idempotência por hash do XML (mesmo sem chave)
        if doc.get("xml_sha256") == xml_sha256 and doc.get("document_type") == document_type:
            return doc
        if (
            access_key
            and doc.get("access_key") == access_key
            and doc.get("document_type") == document_type
        ):
            return doc
    return None


def save_items(document_id: str, items: list[dict[str, Any]]) -> list[dict[str, Any]]:
    with _lock:
        _ensure()
        payload = {"document_id": document_id, "items": items, "updated_at": _now()}
        _atomic(_root() / "items" / f"{document_id}.json", payload)
        return items


def load_items(document_id: str) -> list[dict[str, Any]]:
    path = _root() / "items" / f"{document_id}.json"
    if not path.is_file():
        return []
    return json.loads(path.read_text(encoding="utf-8")).get("items") or []


def get_sync_state(company_code: int, environment: str = "PRODUCTION") -> dict[str, Any]:
    _ensure()
    path = _root() / "sync_state" / f"{company_code}_{environment}.json"
    if path.is_file():
        return json.loads(path.read_text(encoding="utf-8"))
    doc = {
        "company_code": company_code,
        "environment": environment,
        "last_nsu": "000000000000000",
        "max_nsu": "000000000000000",
        "last_query_at": None,
        "next_allowed_query_at": None,
        "status": "IDLE",
        "consecutive_failures": 0,
        "last_status_code": None,
        "last_error_sanitized": None,
        "lease_owner": None,
        "lease_expires_at": None,
        "documents_received": 0,
        "documents_imported": 0,
        "duplicates": 0,
        "quarantined": 0,
        "updated_at": _now(),
    }
    _atomic(path, doc)
    return doc


def save_sync_state(doc: dict[str, Any]) -> dict[str, Any]:
    with _lock:
        _ensure()
        doc["updated_at"] = _now()
        env = doc.get("environment") or "PRODUCTION"
        path = _root() / "sync_state" / f"{doc['company_code']}_{env}.json"
        _atomic(path, doc)
        return doc
