from datetime import datetime, timedelta
from decimal import Decimal
from typing import Any, Dict, List, Optional, Set, Tuple

import anyio
import httpx

from src.domain.entities import CashExpense
from src.domain.exceptions import WebPostoIntegracaoException


class WebPostoClient:
    """Async client for external WebPosto API with basic resilience."""

    def __init__(self, timeout: int = 10):
        self.timeout = min(timeout, 10)
        self.client: Optional[httpx.AsyncClient] = None
        self._failure_count = 0
        self._breaker_open_until: Optional[datetime] = None
        self._failure_threshold = 3
        self._cooldown_seconds = 30

    async def __aenter__(self) -> "WebPostoClient":
        self.client = httpx.AsyncClient(
            timeout=httpx.Timeout(self.timeout),
            limits=httpx.Limits(max_keepalive_connections=10, max_connections=20),
        )
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:
        if self.client:
            await self.client.aclose()

    def _build_headers(self, api_key: str, posto_id: str) -> Dict[str, str]:
        return {
            "X-API-Key": api_key,
            "Accept": "application/json",
            "Content-Type": "application/json",
            "X-Posto-ID": posto_id,
        }

    def _ensure_breaker_closed(self) -> None:
        if self._breaker_open_until and datetime.utcnow() < self._breaker_open_until:
            raise WebPostoIntegracaoException(
                "circuit breaker open for WebPosto API",
                status_code=503,
            )

    def _record_failure(self) -> None:
        self._failure_count += 1
        if self._failure_count >= self._failure_threshold:
            self._breaker_open_until = datetime.utcnow() + timedelta(seconds=self._cooldown_seconds)

    def _record_success(self) -> None:
        self._failure_count = 0
        self._breaker_open_until = None

    @staticmethod
    def _extract_items(payload: Any) -> List[Dict[str, Any]]:
        if isinstance(payload, dict):
            items = (
                payload.get("itens")
                or payload.get("items")
                or payload.get("data")
                or payload.get("movimentos")
                or []
            )
        elif isinstance(payload, list):
            items = payload
        else:
            items = []
        return [item for item in items if isinstance(item, dict)]

    @staticmethod
    def _is_financeiro_exclusao(item: Dict[str, Any]) -> bool:
        joined = " ".join(
            str(item.get(k, ""))
            for k in (
                "origem",
                "tipo_lancamento",
                "historico",
                "evento",
                "schema",
                "endpoint",
            )
        ).upper()
        return "EXCLUSAO" in joined or "FINANCEIRO_EXCLUSAO" in joined

    @staticmethod
    def _dedupe_key(item: Dict[str, Any]) -> Tuple[str, str, str, str]:
        business_id = str(
            item.get("id_vinculo")
            or item.get("id_original")
            or item.get("financeiro_id")
            or item.get("id")
            or ""
        )
        amount = str(abs(Decimal(str(item.get("valor", 0)))))
        date_ref = str(item.get("data") or item.get("timestamp") or "")[:10]
        hist = str(item.get("historico") or item.get("descricao") or "").strip().lower()
        return (business_id, amount, date_ref, hist)

    @staticmethod
    def _parse_response_payload(payload: Any, posto_id: str, dedupe_seen: Set[Tuple[str, str, str, str]]) -> List[CashExpense]:
        items = WebPostoClient._extract_items(payload)

        expenses: List[CashExpense] = []
        for item in items:
            if str(item.get("tipo", "")).upper() != "DEBITO":
                continue

            if WebPostoClient._is_financeiro_exclusao(item):
                key = WebPostoClient._dedupe_key(item)
                if key in dedupe_seen:
                    continue
                dedupe_seen.add(key)

            raw_id = item.get("id") or item.get("expense_id") or item.get("codigo")
            raw_desc = item.get("historico") or item.get("descricao") or item.get("description") or "Despesa de Caixa"
            raw_ts = item.get("timestamp") or item.get("data") or datetime.utcnow().isoformat()
            raw_val = item.get("valor") or item.get("amount") or item.get("total") or "0"

            try:
                expense = CashExpense(
                    id=f"wp_{raw_id}" if raw_id is not None else None,
                    posto_id=posto_id,
                    valor=Decimal(str(raw_val)),
                    descricao=str(raw_desc),
                    timestamp=datetime.fromisoformat(str(raw_ts).replace("Z", "+00:00")),
                    origem="webposto",
                )
                expenses.append(expense)
            except Exception:
                # Skip malformed rows to keep parsing robust.
                continue

        return expenses

    async def fetch_deb_expenses(
        self,
        base_url: str,
        api_key: str,
        posto_id: str,
        data_alvo: datetime,
    ) -> List[CashExpense]:
        self._ensure_breaker_closed()
        headers = self._build_headers(api_key=api_key, posto_id=posto_id)

        if self.client is None:
            raise WebPostoIntegracaoException("WebPostoClient must be used as an async context manager")

        last_error: Optional[Exception] = None
        dedupe_seen: Set[Tuple[str, str, str, str]] = set()
        for attempt in range(3):
            try:
                expenses: List[CashExpense] = []
                page = 1
                while True:
                    url = f"{base_url.rstrip('/')}/INTEGRACAO/MOVIMENTO_CONTA"
                    params = {"data": data_alvo.date().isoformat(), "pagina": page}
                    response = await self.client.get(url, headers=headers, params=params)
                    response.raise_for_status()
                    payload = response.json()
                    page_items = self._parse_response_payload(payload, posto_id, dedupe_seen)
                    expenses.extend(page_items)

                    has_next = False
                    if isinstance(payload, dict):
                        has_next = bool(
                            payload.get("proximaPagina")
                            or payload.get("hasNext")
                            or payload.get("nextPage")
                            or payload.get("paginaAtual", 1) < payload.get("totalPaginas", 1)
                        )
                    if not has_next:
                        break
                    page += 1

                self._record_success()
                return expenses
            except (httpx.TimeoutException, httpx.HTTPStatusError, httpx.NetworkError) as exc:
                last_error = exc
                self._record_failure()
                if attempt < 2:
                    await anyio.sleep(0.2 * (2**attempt))

        raise WebPostoIntegracaoException(
            f"failed to fetch expenses from WebPosto: {last_error}",
            status_code=502,
        )

    @staticmethod
    def _extract_product_items(payload: Any) -> List[Dict[str, Any]]:
        if isinstance(payload, dict):
            items = (
                payload.get("produtos")
                or payload.get("itens")
                or payload.get("items")
                or payload.get("data")
                or []
            )
        elif isinstance(payload, list):
            items = payload
        else:
            items = []
        return [item for item in items if isinstance(item, dict)]

    @staticmethod
    def _normalize_product_item(item: Dict[str, Any]) -> Dict[str, Any]:
        return {
            "id": item.get("id") or item.get("produto_id") or item.get("codigo"),
            "codigo": item.get("codigo") or item.get("codProduto") or item.get("sku"),
            "sku": item.get("sku") or item.get("codigoInterno") or item.get("codigo"),
            "nome": item.get("nome") or item.get("descricao") or item.get("descricaoCompleta"),
            "descricao": item.get("descricao") or item.get("nome"),
            "unidade": item.get("unidade") or item.get("und"),
            "grupo": item.get("grupo") or item.get("nomeGrupo"),
            "subgrupo": item.get("subgrupo") or item.get("nomeSubgrupo"),
            "categoria": item.get("categoria"),
            "preco_venda": item.get("preco_venda") or item.get("precoVenda") or item.get("valorVenda"),
            "preco_custo": item.get("preco_custo") or item.get("precoCusto") or item.get("valorCusto"),
            "ativo": item.get("ativo", True),
            "ean": item.get("ean") or item.get("codigo_barras") or item.get("codBarras"),
            "ncm": item.get("ncm"),
            "cest": item.get("cest"),
            "raw": item,
        }

    async def fetch_products_catalog(
        self,
        base_url: str,
        api_key: str,
        posto_id: str,
        include_inactive: bool = False,
        endpoint_path: str = "/INTEGRACAO/PRODUTOS",
    ) -> Dict[str, Any]:
        self._ensure_breaker_closed()
        headers = self._build_headers(api_key=api_key, posto_id=posto_id)

        if self.client is None:
            raise WebPostoIntegracaoException("WebPostoClient must be used as an async context manager")

        last_error: Optional[Exception] = None
        for attempt in range(3):
            try:
                all_items: List[Dict[str, Any]] = []
                page = 1
                while True:
                    if page > 100:
                        raise WebPostoIntegracaoException(
                            "products pagination exceeded safe limit (100 pages)",
                            status_code=502,
                        )
                    url = f"{base_url.rstrip('/')}{endpoint_path}"
                    params = {"pagina": page}
                    response = await self.client.get(
                        url,
                        headers=headers,
                        params=params,
                        timeout=httpx.Timeout(10.0),
                    )
                    response.raise_for_status()
                    payload = response.json()

                    page_items = self._extract_product_items(payload)
                    all_items.extend(page_items)

                    has_next = False
                    if isinstance(payload, dict):
                        has_next = bool(
                            payload.get("proximaPagina")
                            or payload.get("hasNext")
                            or payload.get("nextPage")
                            or payload.get("paginaAtual", 1) < payload.get("totalPaginas", 1)
                        )
                    if not has_next:
                        break
                    page += 1

                deduped: Dict[str, Dict[str, Any]] = {}
                for item in all_items:
                    key = str(item.get("id") or item.get("produto_id") or item.get("codigo") or len(deduped))
                    normalized = self._normalize_product_item(item)
                    if not include_inactive and normalized.get("ativo") is False:
                        continue
                    deduped[key] = normalized

                self._record_success()
                items = list(deduped.values())
                return {
                    "posto_id": posto_id,
                    "total": len(items),
                    "items": items,
                }
            except (httpx.TimeoutException, httpx.HTTPStatusError, httpx.NetworkError) as exc:
                last_error = exc
                self._record_failure()
                if attempt < 2:
                    await anyio.sleep(0.2 * (2**attempt))

        raise WebPostoIntegracaoException(
            f"failed to fetch products catalog from WebPosto: {last_error}",
            status_code=502,
        )
