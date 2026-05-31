from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any, Dict, Optional

import requests


@dataclass(frozen=True)
class GatewayConfig:
    base_url: str
    consumer_token: str
    posto_id: str
    timeout_seconds: int = 15


class LogosGatewayClient:
    def __init__(self, config: GatewayConfig):
        self.config = config

    @property
    def _headers(self) -> Dict[str, str]:
        return {
            "X-Consumer-Token": self.config.consumer_token,
            "X-Posto-ID": self.config.posto_id,
            "Accept": "application/json",
        }

    def _get(self, path: str, params: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        url = f"{self.config.base_url.rstrip('/')}{path}"
        response = requests.get(
            url,
            headers=self._headers,
            params=params,
            timeout=self.config.timeout_seconds,
        )
        response.raise_for_status()
        return response.json()

    def ready(self) -> Dict[str, Any]:
        url = f"{self.config.base_url.rstrip('/')}/ready"
        response = requests.get(url, timeout=self.config.timeout_seconds)
        response.raise_for_status()
        return response.json()

    def health(self) -> Dict[str, Any]:
        url = f"{self.config.base_url.rstrip('/')}/health"
        response = requests.get(url, timeout=self.config.timeout_seconds)
        response.raise_for_status()
        return response.json()

    def get_expenses(self, data_consulta: Optional[datetime] = None) -> Dict[str, Any]:
        params: Dict[str, Any] = {}
        if data_consulta is not None:
            params["data_consulta"] = data_consulta.isoformat()
        return self._get("/v1/expenses", params=params or None)

    def get_products(self, include_inactive: bool = False, force_refresh: bool = False) -> Dict[str, Any]:
        return self._get(
            "/v1/products",
            params={
                "include_inactive": str(include_inactive).lower(),
                "force_refresh": str(force_refresh).lower(),
            },
        )
