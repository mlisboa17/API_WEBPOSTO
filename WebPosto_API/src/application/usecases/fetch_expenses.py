from __future__ import annotations

import hashlib
import os
from datetime import date, datetime
from decimal import Decimal

from src.domain.entities.gateway_cash_expense import CashExpense
from src.domain.exceptions.posto_nao_configurado import PostoNaoConfiguradoException
from src.infrastructure.caching.gateway_cache import GatewayCache
from src.infrastructure.clients.gateway_webposto_client import GatewayWebPostoClient
from src.infrastructure.config.settings import settings
from src.infrastructure.repositories.gateway_credentials_repository import GatewayCredentialsRepository


class FetchExpensesUseCase:
    def __init__(
        self,
        credentials_repo: GatewayCredentialsRepository,
        webposto_client: GatewayWebPostoClient,
        cache: GatewayCache,
    ) -> None:
        self._credentials_repo = credentials_repo
        self._webposto_client = webposto_client
        self._cache = cache

    @staticmethod
    def _normalize_base_url(url: str) -> str:
        u = (url or "").strip().rstrip("/")
        if not u:
            return "https://web.qualityautomacao.com.br"
        if u.startswith("http://web.qualityautomacao.com.br"):
            return u.replace("http://", "https://", 1)
        return u

    @staticmethod
    def _cache_key(posto_id: str, data_consulta: date) -> str:
        return f"expenses:{posto_id}:{data_consulta.isoformat()}"

    @staticmethod
    def _build_id(posto_id: str, descricao: str, valor: Decimal, ts: datetime) -> str:
        raw = f"{posto_id}|{descricao.lower().strip()}|{valor}|{ts.isoformat()}"
        return hashlib.sha256(raw.encode("utf-8")).hexdigest()

    @staticmethod
    def _env_fallback_credentials(posto_id: str) -> dict[str, str] | None:
        env_posto = os.getenv("GATEWAY_DEFAULT_POSTO_ID", "POSTO_VIP").strip().upper()
        if posto_id.strip().upper() != env_posto:
            return None

        api_key = (os.getenv("WEBPOSTO_API_KEY") or settings.webposto_api_key or "").strip()
        base_url = (
            os.getenv("WEBPOSTO_BASE_URL")
            or settings.webposto_base_url
            or "http://web.qualityautomacao.com.br"
        ).strip()

        if not api_key:
            return None

        return {
            "posto_id": env_posto,
            "api_key": api_key,
            "base_url": FetchExpensesUseCase._normalize_base_url(base_url),
        }

    async def execute(self, posto_id: str, data_consulta: date) -> list[CashExpense]:
        cache_key = self._cache_key(posto_id, data_consulta)
        cached = self._cache.get(cache_key)
        if cached is not None:
            return [CashExpense.model_validate(item) for item in cached]

        credentials = await self._credentials_repo.find_by_posto_id(posto_id)
        if not credentials:
            credentials = self._env_fallback_credentials(posto_id)

        if not credentials:
            raise PostoNaoConfiguradoException(
                f"Posto '{posto_id}' nao configurado no banco local"
            )

        rows = await self._webposto_client.fetch_expenses(
            posto_id=posto_id,
            data_consulta=data_consulta,
            base_url=self._normalize_base_url(credentials["base_url"]),
            api_key=credentials["api_key"],
        )

        result: list[CashExpense] = []
        for row in rows:
            descricao_raw = (
                row.get("descricao")
                or row.get("historico")
                or row.get("produto")
                or row.get("produtoDescricao")
                or row.get("codigoProduto")
            )
            valor_raw = (
                row.get("valor")
                or row.get("valorDespesa")
                or row.get("valorTotal")
                or row.get("total")
            )
            ts_raw = (
                row.get("timestamp")
                or row.get("data")
                or row.get("dataFiscal")
                or row.get("dataAbastecimento")
                or row.get("dataHoraAbastecimento")
                or row.get("dataMovimento")
            )
            if descricao_raw is None or valor_raw is None or ts_raw is None:
                # Somente dados reais completos.
                continue
            descricao = str(descricao_raw)
            valor = Decimal(str(valor_raw))
            ts = datetime.fromisoformat(str(ts_raw).replace("Z", "+00:00"))
            result.append(
                CashExpense(
                    id=self._build_id(posto_id, descricao, valor, ts),
                    posto_id=posto_id,
                    valor=valor,
                    descricao=descricao,
                    timestamp=ts,
                )
            )

        self._cache.set(cache_key, [item.model_dump(mode="json") for item in result])
        return result
