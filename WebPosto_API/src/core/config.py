from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from typing import Tuple

from src.infrastructure.config.settings import settings

ROOT = Path(__file__).resolve().parents[2]
ENV_FILE = ROOT / ".env"

OFFICIAL_WEBPOSTO_TOKEN_ENV_KEYS: tuple[str, ...] = (
    "WEBPOSTO_API_KEY_POSTO_VIP_RIO_DOCE",
    "WEBPOSTO_API_KEY_POSTO_CASA_CAIADA",
    "WEBPOSTO_API_KEY_POSTO_DOZE_FILIAL_II",
)


@dataclass(frozen=True)
class CoreConfig:
    webposto_base_url: str
    webposto_api_key: str
    webposto_api_keys: Tuple[str, ...]
    timeout_seconds: float = 10.0
    permission_ttl_seconds: int = 3600
    circuit_fail_threshold: int = 3
    circuit_block_seconds: int = 3600


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


def _official_webposto_api_keys() -> tuple[str, ...]:
    values: list[str] = []
    seen: set[str] = set()
    for key in OFFICIAL_WEBPOSTO_TOKEN_ENV_KEYS:
        settings_value = getattr(settings, key.lower(), "")
        value = (os.getenv(key) or settings_value or _env_file_value(key)).strip()
        if value and value not in seen:
            seen.add(value)
            values.append(value)
    return tuple(values)


def load_core_config() -> CoreConfig:
    base = (
        os.getenv("WEBPOSTO_BASE_URL")
        or _env_file_value("WEBPOSTO_BASE_URL")
        or settings.webposto_base_url
        or "https://web.qualityautomacao.com.br"
    ).strip()
    if base.startswith("http://web.qualityautomacao.com.br"):
        base = base.replace("http://", "https://", 1)
    official_keys = _official_webposto_api_keys()
    primary_key = official_keys[0] if official_keys else ""
    return CoreConfig(
        webposto_base_url=base.rstrip("/"),
        webposto_api_key=primary_key,
        webposto_api_keys=official_keys,
        timeout_seconds=float(os.getenv("WEBPOSTO_TIMEOUT_SECONDS") or 10.0),
    )
