"""Credenciais WebPosto configuradas no ambiente — sem hardcode de tenants."""

from __future__ import annotations

from dataclasses import dataclass

from src.core.config import (
    OFFICIAL_COMPANY_CODES,
    OFFICIAL_COMPANY_CREDENTIAL_ALIASES,
    OFFICIAL_WEBPOSTO_TOKEN_ENV_KEYS,
    resolve_company_api_key,
    _resolve_env_value,
)


@dataclass(frozen=True)
class WebPostoCredential:
    env_key: str
    api_key: str
    empresa_codigo: int | None = None

    @property
    def masked_token(self) -> str:
        value = (self.api_key or "").strip()
        if len(value) >= 8:
            return f"****{value[-4:]}"
        return "****" if value else ""


def list_webposto_credentials() -> tuple[WebPostoCredential, ...]:
    """Retorna credenciais oficiais deduplicadas (preferência pelos aliases novos)."""
    credentials: list[WebPostoCredential] = []
    seen_values: set[str] = set()

    for codigo in OFFICIAL_COMPANY_CODES:
        preferred = OFFICIAL_COMPANY_CREDENTIAL_ALIASES[codigo][0]
        value = resolve_company_api_key(codigo)
        if not value or value in seen_values:
            continue
        seen_values.add(value)
        # Usa o alias efetivamente resolvido quando possível
        env_key = preferred
        for alias in OFFICIAL_COMPANY_CREDENTIAL_ALIASES[codigo]:
            if _resolve_env_value(alias) == value:
                env_key = alias
                break
        credentials.append(
            WebPostoCredential(env_key=env_key, api_key=value, empresa_codigo=codigo)
        )

    # Inclui chaves legadas listadas se ainda não cobertas
    for env_key in OFFICIAL_WEBPOSTO_TOKEN_ENV_KEYS:
        value = _resolve_env_value(env_key)
        if not value or value in seen_values:
            continue
        seen_values.add(value)
        credentials.append(WebPostoCredential(env_key=env_key, api_key=value))

    return tuple(credentials)
