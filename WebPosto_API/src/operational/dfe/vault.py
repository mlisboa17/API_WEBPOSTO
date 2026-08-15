"""SecretVault — Fernet com DFE_VAULT_MASTER_KEY exclusiva (sem fallback AES_KEY)."""

from __future__ import annotations

import base64
import os
import threading
import uuid
from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from cryptography.fernet import Fernet, InvalidToken

ROOT = Path(__file__).resolve().parents[3]
SECRETS_DIR = ROOT / "data" / "dfe_store" / "secrets"
_lock = threading.RLock()

MASTER_KEY_ENV = "DFE_VAULT_MASTER_KEY"
CURRENT_KEY_VERSION = 1


class VaultNotConfiguredError(RuntimeError):
    code = "VAULT_NOT_CONFIGURED"

    def __init__(self, message: str = "DFE_VAULT_MASTER_KEY não configurada") -> None:
        super().__init__(message)
        self.message = message


@dataclass
class SecretMeta:
    secret_id: str
    purpose: str
    company_code: int
    encryption_key_version: int
    secret_version: int
    created_at: str
    rotated_at: str | None
    reencrypt_status: str


class SecretVault(ABC):
    @abstractmethod
    def is_configured(self) -> bool: ...

    @abstractmethod
    def put_secret(
        self,
        *,
        company_code: int,
        purpose: str,
        plaintext: bytes,
        secret_version: int = 1,
    ) -> SecretMeta: ...

    @abstractmethod
    def get_secret(self, secret_id: str) -> bytes: ...

    @abstractmethod
    def delete_secret(self, secret_id: str) -> None: ...

    @abstractmethod
    def describe(self, secret_id: str) -> SecretMeta | None: ...


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _read_master_key() -> str | None:
    """Lê somente DFE_VAULT_MASTER_KEY — AES_KEY é proibido como fallback."""
    key = os.environ.get(MASTER_KEY_ENV, "").strip()
    if key:
        return key
    # pydantic-settings pode carregar a var sem exportar em os.environ
    try:
        from src.infrastructure.config.settings import settings

        key = (getattr(settings, "dfe_vault_master_key", None) or "").strip()
        if key:
            return key
    except Exception:
        pass
    # Nunca usar AES_KEY / SECRET_KEY
    return None


class LocalEncryptedSecretVault(SecretVault):
    """Cofre local Fernet. Ciphertext em arquivos sob data/dfe_store/secrets/."""

    def __init__(self, root: Path | None = None) -> None:
        self.root = root or SECRETS_DIR
        self.root.mkdir(parents=True, exist_ok=True)
        self._fernet: Fernet | None = None
        key = _read_master_key()
        if key:
            try:
                # Aceita chave Fernet urlsafe-base64 ou deriva se comprimento inválido for rejeitado
                self._fernet = Fernet(key.encode("utf-8") if isinstance(key, str) else key)
            except Exception:
                self._fernet = None
                self._invalid_key = True
            else:
                self._invalid_key = False
        else:
            self._invalid_key = False

    def is_configured(self) -> bool:
        return self._fernet is not None

    def status(self) -> str:
        if _read_master_key() and self._fernet is None:
            return "VAULT_KEY_INVALID"
        if self._fernet is None:
            return "VAULT_NOT_CONFIGURED"
        return "VAULT_READY"

    def _require(self) -> Fernet:
        if self._fernet is None:
            raise VaultNotConfiguredError()
        return self._fernet

    def put_secret(
        self,
        *,
        company_code: int,
        purpose: str,
        plaintext: bytes,
        secret_version: int = 1,
    ) -> SecretMeta:
        f = self._require()
        secret_id = f"dfe_sec_{uuid.uuid4().hex}"
        token = f.encrypt(plaintext)  # inclui timestamp/nonce próprio por token
        meta = SecretMeta(
            secret_id=secret_id,
            purpose=purpose,
            company_code=company_code,
            encryption_key_version=CURRENT_KEY_VERSION,
            secret_version=secret_version,
            created_at=_now(),
            rotated_at=None,
            reencrypt_status="CURRENT",
        )
        payload = {
            "secret_id": meta.secret_id,
            "purpose": meta.purpose,
            "company_code": meta.company_code,
            "encryption_key_version": meta.encryption_key_version,
            "secret_version": meta.secret_version,
            "created_at": meta.created_at,
            "rotated_at": meta.rotated_at,
            "reencrypt_status": meta.reencrypt_status,
            "ciphertext_b64": base64.b64encode(token).decode("ascii"),
        }
        with _lock:
            path = self.root / f"{secret_id}.bin.json"
            path.write_text(
                __import__("json").dumps(payload, ensure_ascii=False, indent=2),
                encoding="utf-8",
            )
            try:
                os.chmod(path, 0o600)
            except OSError:
                pass
        return meta

    def get_secret(self, secret_id: str) -> bytes:
        f = self._require()
        path = self.root / f"{secret_id}.bin.json"
        if not path.is_file():
            raise FileNotFoundError(secret_id)
        data = __import__("json").loads(path.read_text(encoding="utf-8"))
        token = base64.b64decode(data["ciphertext_b64"])
        try:
            return f.decrypt(token)
        except InvalidToken as exc:
            raise VaultNotConfiguredError("falha ao decriptar segredo (chave inválida?)") from exc

    def delete_secret(self, secret_id: str) -> None:
        path = self.root / f"{secret_id}.bin.json"
        with _lock:
            if path.is_file():
                path.unlink()

    def describe(self, secret_id: str) -> SecretMeta | None:
        path = self.root / f"{secret_id}.bin.json"
        if not path.is_file():
            return None
        data = __import__("json").loads(path.read_text(encoding="utf-8"))
        return SecretMeta(
            secret_id=data["secret_id"],
            purpose=data["purpose"],
            company_code=int(data["company_code"]),
            encryption_key_version=int(data.get("encryption_key_version", 1)),
            secret_version=int(data.get("secret_version", 1)),
            created_at=data.get("created_at") or _now(),
            rotated_at=data.get("rotated_at"),
            reencrypt_status=data.get("reencrypt_status") or "CURRENT",
        )


_default_vault: LocalEncryptedSecretVault | None = None


def get_vault(root: Path | None = None) -> LocalEncryptedSecretVault:
    global _default_vault
    if root is not None:
        return LocalEncryptedSecretVault(root=root)
    if _default_vault is None:
        _default_vault = LocalEncryptedSecretVault()
    return _default_vault


def reset_vault_for_tests(root: Path) -> LocalEncryptedSecretVault:
    global _default_vault
    _default_vault = LocalEncryptedSecretVault(root=root)
    return _default_vault


def vault_public_status() -> dict[str, Any]:
    v = get_vault()
    return {
        "status": v.status(),
        "configured": v.is_configured(),
        "masterKeyEnv": MASTER_KEY_ENV,
        "aesKeyFallback": False,
    }
