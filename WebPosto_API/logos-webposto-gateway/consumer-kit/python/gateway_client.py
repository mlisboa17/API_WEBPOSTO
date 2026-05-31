from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from typing import Any, Optional

import httpx


@dataclass(frozen=True)
class CashExpenseDTO:
    id: Optional[str]
    posto_id: str
    valor: Decimal
    descricao: str
    timestamp: datetime
    origem: str


@dataclass(frozen=True)
class ExpensesResponseDTO:
    posto_id: str
    data_consulta: datetime
    total: int
    items: list[CashExpenseDTO]


class GatewayApiError(RuntimeError):
    pass


class LogosGatewayClient:
    def __init__(
        self,
        base_url: str,
        consumer_token: str,
        timeout_seconds: int = 10,
        max_retries: int = 2,
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self.max_retries = max_retries
        self.client = httpx.Client(
            base_url=self.base_url,
            timeout=httpx.Timeout(timeout_seconds),
            headers={
                "Accept": "application/json",
                "X-Consumer-Token": consumer_token,
            },
        )

    def close(self) -> None:
        self.client.close()

    def _request(self, method: str, path: str, **kwargs: Any) -> httpx.Response:
        last_error: Optional[Exception] = None
        for attempt in range(self.max_retries + 1):
            try:
                response = self.client.request(method, path, **kwargs)
                response.raise_for_status()
                return response
            except (httpx.TimeoutException, httpx.NetworkError, httpx.HTTPStatusError) as exc:
                last_error = exc
                if attempt >= self.max_retries:
                    break
        raise GatewayApiError(f"gateway request failed: {last_error}")

    def health(self) -> dict[str, Any]:
        response = self._request("GET", "/health")
        return response.json()

    def ready(self) -> dict[str, Any]:
        response = self._request("GET", "/ready")
        return response.json()

    def get_expenses(
        self,
        posto_id: str,
        data_consulta: Optional[datetime] = None,
    ) -> ExpensesResponseDTO:
        headers = {"X-Posto-ID": posto_id}
        params: dict[str, str] = {}
        if data_consulta:
            params["data_consulta"] = data_consulta.isoformat()

        response = self._request("GET", "/v1/expenses", headers=headers, params=params)
        payload = response.json()

        items: list[CashExpenseDTO] = []
        for item in payload.get("items", []):
            items.append(
                CashExpenseDTO(
                    id=item.get("id"),
                    posto_id=item["posto_id"],
                    valor=Decimal(str(item["valor"])),
                    descricao=item["descricao"],
                    timestamp=datetime.fromisoformat(item["timestamp"]),
                    origem=item["origem"],
                )
            )

        return ExpensesResponseDTO(
            posto_id=payload["posto_id"],
            data_consulta=datetime.fromisoformat(payload["data_consulta"]),
            total=payload["total"],
            items=items,
        )
