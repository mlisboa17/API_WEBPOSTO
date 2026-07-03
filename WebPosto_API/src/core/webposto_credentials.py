"""Credenciais WebPosto configuradas no ambiente — sem hardcode de tenants."""

from __future__ import annotations

import os
from dataclasses import dataclass

from src.core.config import ENV_FILE, OFFICIAL_WEBPOSTO_TOKEN_ENV_KEYS
from src.infrastructure.config.settings import settings


@dataclass(frozen=True)
class WebPostoCredential:
    env_key: str
    api_key: str

    @property
    def masked_token(self) -> str:
        value = (self.api_key or "").strip()
        if len(value) >= 8:
            return f"****{value[-4:]}"
        return "****" if value else ""


def _env_file_value(key: str) -> str:
    if not ENV_FILE.is_file():
        return ""
    for line in ENV_FILE.read_text(encoding="utf-8").splitlines():
        raw = line.strip()
        if not raw or raw.startswith("#") or "=" not in raw:
            continue
        name, _, value = raw.partition("=")
        if name.strip() == key:
            return value.strip().strip('"').strip("'")
    return ""


def _resolve_env_value(key: str) -> str:
    settings_value = getattr(settings, key.lower(), "")
    return (os.getenv(key) or settings_value or _env_file_value(key)).strip()


def list_webposto_credentials() -> tuple[WebPostoCredential, ...]:
    """Retorna credenciais oficiais deduplicadas por valor de token."""
    credentials: list[WebPostoCredential] = []
    seen_values: set[str] = set()

    for env_key in OFFICIAL_WEBPOSTO_TOKEN_ENV_KEYS:
        value = _resolve_env_value(env_key)
        if not value or value in seen_values:
            continue
        seen_values.add(value)
        credentials.append(WebPostoCredential(env_key=env_key, api_key=value))

    return tuple(credentials)
