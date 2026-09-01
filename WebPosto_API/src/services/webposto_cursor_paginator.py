"""Paginação por ultimoCodigo com prova explícita de completude."""

from __future__ import annotations

import json
from typing import Any

from src.models.error_model import WebPostoError
from src.models.response_model import WebPostoResponse


class WebPostoCursorPaginator:
    def __init__(self, client: Any, *, max_pages: int = 1000, batch_size: int = 200) -> None:
        self._client = client
        self._max_pages = max_pages
        self._batch_size = batch_size

    @staticmethod
    def _rows(payload: Any) -> list[dict[str, Any]]:
        if isinstance(payload, list):
            return [row for row in payload if isinstance(row, dict)]
        if isinstance(payload, dict):
            for key in ("resultados", "data", "items"):
                value = payload.get(key)
                if isinstance(value, list):
                    return [row for row in value if isinstance(row, dict)]
        return []

    @staticmethod
    def _has_supported_shape(payload: Any) -> bool:
        if isinstance(payload, list):
            return True
        if isinstance(payload, dict):
            return any(isinstance(payload.get(key), list) for key in ("resultados", "data", "items"))
        return False

    @staticmethod
    def _cursor(payload: Any, rows: list[dict[str, Any]], cursor_field: str) -> Any:
        if isinstance(payload, dict) and payload.get("ultimoCodigo") not in (None, ""):
            return payload["ultimoCodigo"]
        if rows:
            return rows[-1].get(cursor_field)
        return None

    async def _call_with_fallback(
        self,
        primary_key: str,
        fallback_key: str,
        params: dict[str, Any],
    ) -> WebPostoResponse:
        primary = await self._client.call_endpoint(primary_key, params=params)
        if primary.success:
            return primary
        return await self._client.call_endpoint(fallback_key, params=params)

    async def collect(
        self,
        primary_key: str,
        fallback_key: str,
        base_params: dict[str, Any],
        *,
        cursor_field: str = "codigo",
    ) -> WebPostoResponse:
        results: list[dict[str, Any]] = []
        seen: set[str] = set()
        cursor: Any = None
        pages = 0
        duplicates = 0

        for _ in range(self._max_pages):
            params = dict(base_params)
            if cursor is not None:
                params["ultimoCodigo"] = cursor

            response = await self._call_with_fallback(primary_key, fallback_key, params)
            if not response.success:
                return response

            payload = response.data
            if not self._has_supported_shape(payload):
                return WebPostoResponse.fail(
                    WebPostoError(
                        endpoint=fallback_key,
                        type="UNSUPPORTED_PAGINATION_PAYLOAD",
                        message="Resposta paginada sem lista em resultados, data ou items",
                    )
                )
            batch = self._rows(payload)
            pages += 1
            if not batch:
                return WebPostoResponse.ok(
                    {
                        "resultados": results,
                        "pagination": {
                            "complete": True,
                            "termination": "EMPTY_BATCH",
                            "pages": pages,
                            "duplicatesRemoved": duplicates,
                            "ultimoCodigo": cursor,
                        },
                        "synthetic": False,
                    }
                )

            for row in batch:
                marker = json.dumps(row, sort_keys=True, ensure_ascii=False, default=str)
                if marker in seen:
                    duplicates += 1
                    continue
                seen.add(marker)
                results.append(row)

            next_cursor = self._cursor(payload, batch, cursor_field)
            if next_cursor in (None, "") or next_cursor == cursor:
                return WebPostoResponse.fail(
                    WebPostoError(
                        endpoint=fallback_key,
                        type="CURSOR_STALLED",
                        message="Paginação interrompida sem prova de completude",
                    )
                )

            cursor = next_cursor
            if len(batch) < self._batch_size:
                return WebPostoResponse.ok(
                    {
                        "resultados": results,
                        "pagination": {
                            "complete": True,
                            "termination": "SHORT_BATCH",
                            "pages": pages,
                            "duplicatesRemoved": duplicates,
                            "ultimoCodigo": cursor,
                        },
                        "synthetic": False,
                    }
                )

        return WebPostoResponse.fail(
            WebPostoError(
                endpoint=fallback_key,
                type="PAGINATION_SAFETY_LIMIT",
                message=f"Coleta excedeu o limite de {self._max_pages} páginas sem provar término",
            )
        )
