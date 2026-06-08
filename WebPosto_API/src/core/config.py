from __future__ import annotations

import os
from dataclasses import dataclass

from src.infrastructure.config.settings import settings


@dataclass(frozen=True)
class CoreConfig:
    webposto_base_url: str
    webposto_api_key: str
    timeout_seconds: float = 10.0
    permission_ttl_seconds: int = 3600
    circuit_fail_threshold: int = 3
    circuit_block_seconds: int = 3600



def load_core_config() -> CoreConfig:
    base = (
        os.getenv("WEBPOSTO_BASE_URL")
        or settings.webposto_base_url
        or "https://web.qualityautomacao.com.br"
    ).strip()
    if base.startswith("http://web.qualityautomacao.com.br"):
        base = base.replace("http://", "https://", 1)
    return CoreConfig(
        webposto_base_url=base.rstrip("/"),
        webposto_api_key=(os.getenv("WEBPOSTO_API_KEY") or settings.webposto_api_key or "").strip(),
        timeout_seconds=float(os.getenv("WEBPOSTO_TIMEOUT_SECONDS") or 10.0),
    )
