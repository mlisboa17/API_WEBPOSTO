"""Cadastro/validação offline de certificados fiscais A1."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from src.operational.dfe import store
from src.operational.dfe.pynfe_provider import PyNFeDistributionProvider
from src.operational.dfe.vault import VaultNotConfiguredError, get_vault


class CertificateError(Exception):
    def __init__(self, code: str, message: str, status_code: int = 400) -> None:
        super().__init__(message)
        self.code = code
        self.message = message
        self.status_code = status_code


def _digits(v: str | None) -> str:
    return "".join(ch for ch in str(v or "") if ch.isdigit())


def upload_and_validate(
    *,
    company_code: int,
    cnpj: str,
    uf: str,
    pfx_bytes: bytes,
    password: str,
    legal_name: str | None = None,
    tax_regime: str | None = None,
    actor: str = "system",
    role: str = "operator",
) -> dict[str, Any]:
    if role not in {"admin", "approver", "operator", "director"}:
        raise CertificateError("FORBIDDEN", "sem permissão para upload", 403)

    vault = get_vault()
    if not vault.is_configured():
        raise CertificateError("VAULT_NOT_CONFIGURED", "DFE_VAULT_MASTER_KEY não configurada", 503)

    provider = PyNFeDistributionProvider(allow_sefaz_queries=False)
    result = provider.validate_certificate(
        pfx_bytes, password, expected_cnpj=_digits(cnpj) or None
    )

    if result.status == "INVALID_PASSWORD":
        store.append_audit(
            company_code=company_code,
            action="CERT_VALIDATE_FAIL",
            actor=actor,
            detail={"status": result.status},
        )
        raise CertificateError(result.status, result.error_sanitized or "senha inválida", 400)

    if not result.ok:
        store.append_audit(
            company_code=company_code,
            action="CERT_VALIDATE_FAIL",
            actor=actor,
            detail={"status": result.status},
        )
        raise CertificateError(
            result.status,
            result.error_sanitized or "certificado não aprovado",
            400,
        )

    # store secrets separately
    try:
        pfx_meta = vault.put_secret(company_code=company_code, purpose="PFX", plaintext=pfx_bytes)
        pwd_meta = vault.put_secret(
            company_code=company_code, purpose="PASSWORD", plaintext=password.encode("utf-8")
        )
    except VaultNotConfiguredError as exc:
        raise CertificateError("VAULT_NOT_CONFIGURED", str(exc), 503) from exc

    now = datetime.now(timezone.utc).isoformat()
    cert_id = store.new_id("dfe_cert")
    doc = {
        "id": cert_id,
        "company_code": company_code,
        "cnpj": _digits(cnpj),
        "legal_name": legal_name,
        "uf": uf.upper(),
        "tax_regime": tax_regime,
        "certificate_type": "A1_PFX",
        "pfx_secret_id": pfx_meta.secret_id,
        "password_secret_id": pwd_meta.secret_id,
        "serial_number": result.serial_number,
        "issuer": result.issuer,
        "subject": result.subject,
        "extracted_cnpj": result.extracted_cnpj,
        "valid_from": result.valid_from,
        "valid_to": result.valid_to,
        "fingerprint_sha256": result.fingerprint_sha256,
        "status": result.status if result.ok or result.status == "EXPIRING_SOON" else result.status,
        "days_to_expiry": result.days_to_expiry,
        "encryption_key_version": pfx_meta.encryption_key_version,
        "secret_version": pfx_meta.secret_version,
        "reencrypt_status": "CURRENT",
        "last_checked_at": now,
        "last_error_sanitized": result.error_sanitized,
        "created_at": now,
        "rotated_at": None,
        "updated_at": now,
        "disabled": False,
        "client_auth": result.client_auth,
        "chain_ok": result.chain_ok,
        "has_private_key": result.has_private_key,
    }
    # If CNPJ mismatch / expired — still store metadata? Spec: validate; we persist with status
    store.save_certificate(doc)
    store.append_audit(
        company_code=company_code,
        action="CERT_UPLOAD",
        actor=actor,
        target_type="certificate",
        target_id=cert_id,
        detail={"status": doc["status"], "fingerprint": doc["fingerprint_sha256"]},
    )
    return store.certificate_public_view(doc)


def list_company_certificates(company_code: int | None = None) -> list[dict[str, Any]]:
    return [store.certificate_public_view(c) for c in store.list_certificates(company_code)]


def delete_certificate(*, cert_id: str, actor: str, role: str) -> dict[str, Any]:
    if role not in {"admin", "approver"}:
        raise CertificateError("FORBIDDEN", "exclusão requer administrador", 403)
    doc = store.load_certificate(cert_id)
    if not doc:
        raise CertificateError("NOT_FOUND", "certificado não encontrado", 404)
    vault = get_vault()
    for sid in (doc.get("pfx_secret_id"), doc.get("password_secret_id")):
        if sid and vault.is_configured():
            try:
                vault.delete_secret(sid)
            except Exception:
                pass
    path = store._root() / "certificates" / f"{cert_id}.json"
    if path.is_file():
        path.unlink()
    store.append_audit(
        company_code=doc.get("company_code"),
        action="CERT_DELETE",
        actor=actor,
        target_type="certificate",
        target_id=cert_id,
        detail={"fingerprint": doc.get("fingerprint_sha256")},
    )
    return {"success": True, "certificateId": cert_id}


def validate_only(
    *,
    pfx_bytes: bytes,
    password: str,
    expected_cnpj: str | None = None,
) -> dict[str, Any]:
    """Validação offline em memória — não persiste."""
    provider = PyNFeDistributionProvider(allow_sefaz_queries=False)
    r = provider.validate_certificate(pfx_bytes, password, expected_cnpj=_digits(expected_cnpj) or None)
    return {
        "ok": r.ok,
        "status": r.status,
        "cnpj": r.extracted_cnpj,
        "sujeito": r.subject,
        "emissor": r.issuer,
        "numeroSerie": r.serial_number,
        "fingerprintSha256": r.fingerprint_sha256,
        "validadeInicial": r.valid_from,
        "validadeFinal": r.valid_to,
        "diasParaVencimento": r.days_to_expiry,
        "hasPrivateKey": r.has_private_key,
        "clientAuth": r.client_auth,
        "chainOk": r.chain_ok,
        "error": r.error_sanitized,
        "revocation": "NOT_CHECKED",
    }
