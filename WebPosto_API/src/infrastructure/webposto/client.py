from typing import Any, Dict, List, Optional

import httpx
from tenacity import (
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

from src.infrastructure.config.settings import settings
from src.shared.logger import get_logger

logger = get_logger(__name__)


class WebPostoClient:
    """Cliente HTTP para a API REST do webPosto."""

    def __init__(self, api_key: Optional[str] = None, base_url: Optional[str] = None):
        self.api_key = api_key or settings.webposto_api_key
        self.base_url = base_url or settings.webposto_base_url
        self.timeout = settings.webposto_timeout_seconds
        self.client = httpx.AsyncClient(
            base_url=self.base_url,
            timeout=self.timeout,
            trust_env=False,
            headers={"Accept": "application/json", "Content-Type": "application/json"},
        )

    async def close(self):
        """Fecha a sessão do cliente HTTP."""
        await self.client.aclose()

    @retry(
        retry=retry_if_exception_type((httpx.HTTPError, httpx.TimeoutException)),
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=2, min=2, max=10),
    )
    async def _request(self, method: str, endpoint: str, **kwargs) -> Dict[str, Any]:
        """Executa requisição HTTP com retry automático."""
        params = kwargs.pop("params", {})
        params["CHAVE"] = self.api_key

        try:
            logger.info(f"Requisição {method} para {endpoint}", endpoint=endpoint)
            response = await self.client.request(
                method, endpoint, params=params, **kwargs
            )
            response.raise_for_status()
            data = response.json()
            logger.info(
                f"Requisição bem-sucedida: {endpoint}", status=response.status_code
            )
            return data
        except httpx.HTTPStatusError as e:
            logger.error(
                f"Erro HTTP: {e.status_code}",
                status=e.status_code,
                endpoint=endpoint,
                detail=e.response.text,
            )
            raise
        except httpx.TimeoutException:
            logger.warning(f"Timeout em {endpoint}")
            raise
        except Exception as e:
            logger.error(f"Erro inesperado em {endpoint}: {str(e)}")
            raise

    # ========== MÉTODOS GET ==========

    async def get_clientes(self, skip: int = 0, limit: int = 100) -> List[Dict]:
        """GET /api/v1/clientes - Lista clientes."""
        data = await self._request(
            "GET", "/api/v1/clientes", params={"skip": skip, "limit": limit}
        )
        return data.get("data", [])

    async def get_cliente(self, cliente_id: str) -> Dict:
        """GET /api/v1/clientes/{id} - Obtém um cliente."""
        return await self._request("GET", f"/api/v1/clientes/{cliente_id}")

    async def get_produtos(self, skip: int = 0, limit: int = 100) -> List[Dict]:
        """GET /api/v1/produtos - Lista produtos."""
        data = await self._request(
            "GET", "/api/v1/produtos", params={"skip": skip, "limit": limit}
        )
        return data.get("data", [])

    async def get_abastecimentos(self, skip: int = 0, limit: int = 100) -> List[Dict]:
        """GET /api/v1/abastecimentos - Lista abastecimentos."""
        data = await self._request(
            "GET", "/api/v1/abastecimentos", params={"skip": skip, "limit": limit}
        )
        return data.get("data", [])

    async def get_financeiro(self, skip: int = 0, limit: int = 100) -> List[Dict]:
        """GET /api/v1/financeiro/titulos-receber - Lista financeiro."""
        data = await self._request(
            "GET",
            "/api/v1/financeiro/titulos-receber",
            params={"skip": skip, "limit": limit},
        )
        return data.get("data", [])

    async def get_caixa(self, skip: int = 0, limit: int = 100) -> List[Dict]:
        """GET /api/v1/caixa/movimentos - Lista movimentos de caixa."""
        data = await self._request(
            "GET", "/api/v1/caixa/movimentos", params={"skip": skip, "limit": limit}
        )
        return data.get("data", [])

    async def get_relatorios(self, skip: int = 0, limit: int = 100) -> List[Dict]:
        """GET /api/v1/relatorios - Lista relatórios."""
        data = await self._request(
            "GET", "/api/v1/relatorios", params={"skip": skip, "limit": limit}
        )
        return data.get("data", [])

    # ========== MÉTODOS POST ==========

    async def criar_cliente(self, dados: Dict[str, Any]) -> Dict:
        """POST /api/v1/clientes - Cria um novo cliente."""
        return await self._request("POST", "/api/v1/clientes", json=dados)

    async def criar_abastecimento(self, dados: Dict[str, Any]) -> Dict:
        """POST /api/v1/abastecimentos - Cria um novo abastecimento."""
        return await self._request("POST", "/api/v1/abastecimentos", json=dados)

    async def criar_lancamento_financeiro(self, dados: Dict[str, Any]) -> Dict:
        """POST /api/v1/financeiro/titulos-receber - Cria lançamento."""
        return await self._request(
            "POST", "/api/v1/financeiro/titulos-receber", json=dados
        )

    # ========== MÉTODOS PUT ==========

    async def atualizar_cliente(self, cliente_id: str, dados: Dict[str, Any]) -> Dict:
        """PUT /api/v1/clientes/{id} - Atualiza cliente."""
        return await self._request("PUT", f"/api/v1/clientes/{cliente_id}", json=dados)

    async def atualizar_financeiro(
        self, financeiro_id: str, dados: Dict[str, Any]
    ) -> Dict:
        """PUT /api/v1/financeiro/titulos-receber/{id} - Atualiza financeiro."""
        return await self._request(
            "PUT", f"/api/v1/financeiro/titulos-receber/{financeiro_id}", json=dados
        )

    async def health_check(self) -> Dict:
        """GET /health - Verifica saúde da API."""
        try:
            return await self._request("GET", "/health")
        except Exception as e:
            logger.error(f"Health check falhou: {str(e)}")
            return {"status": "unhealthy"}
