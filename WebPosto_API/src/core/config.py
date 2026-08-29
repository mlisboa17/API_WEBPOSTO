from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Mapping

from src.infrastructure.config.settings import settings

ROOT = Path(__file__).resolve().parents[2]
ENV_FILE = ROOT / ".env"

# Aliases preferenciais (novos) + legados por empresa oficial.
OFFICIAL_COMPANY_CREDENTIAL_ALIASES: dict[int, tuple[str, ...]] = {
    5555: (
        "WEBPOSTO_CASA_CAIADA_KEY",
        "WEBPOSTO_API_KEY_POSTO_CASA_CAIADA",
        "WEBPOSTO_API_KEY_CASA_CAIADA",
    ),
    11495: (
        "WEBPOSTO_VIP_KEY",
        "WEBPOSTO_API_KEY_POSTO_VIP_RIO_DOCE",
        "WEBPOSTO_API_KEY_POSTO_VIP",
    ),
    74014: (
        "WEBPOSTO_REAL_DOZE_KEY",
        "WEBPOSTO_API_KEY_POSTO_DOZE_FILIAL_II",
    ),
    118508: (
        "WEBPOSTO_CONVENIENCIA_24_HORAS_KEY",
        "WEBPOSTO_API_GERAL_CONVENIENCIA_KEY",
    ),
}

# Ordem canônica para listagens (VIP, Casa Caiada, Real Doze, Conveniência 24H).
OFFICIAL_WEBPOSTO_TOKEN_ENV_KEYS: tuple[str, ...] = (
    "WEBPOSTO_VIP_KEY",
    "WEBPOSTO_CASA_CAIADA_KEY",
    "WEBPOSTO_REAL_DOZE_KEY",
    "WEBPOSTO_CONVENIENCIA_24_HORAS_KEY",
    # legado
    "WEBPOSTO_API_KEY_POSTO_VIP_RIO_DOCE",
    "WEBPOSTO_API_KEY_POSTO_CASA_CAIADA",
    "WEBPOSTO_API_KEY_POSTO_DOZE_FILIAL_II",
    "WEBPOSTO_API_GERAL_CONVENIENCIA_KEY",
)

# Índice legado (mantido para compatibilidade pontual).
OFFICIAL_COMPANY_TOKEN_INDEX = {11495: 0, 5555: 1, 74014: 2, 118508: 3}

OFFICIAL_COMPANY_CODES: tuple[int, ...] = (5555, 11495, 74014, 118508)


@dataclass(frozen=True)
class CoreConfig:
    webposto_base_url: str
    webposto_api_key: str
    webposto_api_keys: tuple[str, ...]
    webposto_company_keys: Mapping[int, str] = field(default_factory=dict)
    timeout_seconds: float = 10.0
    permission_ttl_seconds: int = 3600
    circuit_fail_threshold: int = 3
    circuit_block_seconds: int = 3600

    def key_for_company(self, empresa_codigo: int) -> str | None:
        """Retorna somente token explicitamente associado à filial solicitada."""
        return self.webposto_company_keys.get(int(empresa_codigo))


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
    settings_attr = key.lower()
    settings_value = getattr(settings, settings_attr, "")
    return (os.getenv(key) or settings_value or _env_file_value(key)).strip()


def resolve_company_api_key(empresa_codigo: int) -> str:
    """Resolve token da filial por aliases exclusivos, sem fallback genérico."""
    aliases = OFFICIAL_COMPANY_CREDENTIAL_ALIASES.get(int(empresa_codigo), ())
    for alias in aliases:
        value = _resolve_env_value(alias)
        if value:
            return value
    return ""


def _official_webposto_api_keys() -> tuple[str, ...]:
    """Lista deduplicada na ordem VIP → Casa Caiada → Real Doze."""
    values: list[str] = []
    seen: set[str] = set()
    for codigo in OFFICIAL_COMPANY_CODES:
        # Prefer preferred alias order for listing
        preferred = OFFICIAL_COMPANY_CREDENTIAL_ALIASES[codigo][0]
        value = _resolve_env_value(preferred) or resolve_company_api_key(codigo)
        if value and value not in seen:
            seen.add(value)
            values.append(value)
    return tuple(values)


def _company_keys_map() -> dict[int, str]:
    mapping: dict[int, str] = {}
    for codigo in OFFICIAL_COMPANY_CODES:
        value = resolve_company_api_key(codigo)
        if value:
            mapping[codigo] = value
    return mapping


def load_core_config() -> CoreConfig:
    base = (
        os.getenv("WEBPOSTO_BASE_URL")
        or os.getenv("WEBPOSTO_API_URL")
        or _env_file_value("WEBPOSTO_BASE_URL")
        or _env_file_value("WEBPOSTO_API_URL")
        or settings.webposto_api_url
        or settings.webposto_base_url
        or "https://web.qualityautomacao.com.br"
    ).strip()
    if base.startswith("http://web.qualityautomacao.com.br"):
        base = base.replace("http://", "https://", 1)

    company_keys = _company_keys_map()
    official_keys = _official_webposto_api_keys()
    primary_key = (
        _resolve_env_value("WEBPOSTO_TOKEN")
        or _resolve_env_value("WEBPOSTO_APP_KEY")
        or _resolve_env_value("WEBPOSTO_API_KEY")
        or (official_keys[0] if official_keys else "")
        or ""
    ).strip()

    keys = official_keys or ((primary_key,) if primary_key else ())
    return CoreConfig(
        webposto_base_url=base.rstrip("/"),
        webposto_api_key=primary_key,
        webposto_api_keys=keys,
        webposto_company_keys=company_keys,
        timeout_seconds=float(os.getenv("WEBPOSTO_TIMEOUT_SECONDS") or 10.0),
    )
