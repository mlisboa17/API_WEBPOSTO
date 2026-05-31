"""
WebPosto API Client: Async HTTP client com connection pooling e retry.

Implementa comunicação com API WebPosto para recuperar lançamentos e centros de custo.
"""

from typing import Optional, Dict, Any, List
from datetime import datetime
import logging

import httpx
from tenacity import (
    retry,
    stop_after_attempt,
    wait_exponential,
    retry_if_exception_type
)

logger = logging.getLogger(__name__)


class WebPostoClientException(Exception):
    """Exceção da API WebPosto."""
    pass


class WebPostoClient:
    """
    Cliente assíncrono para API WebPosto.
    
    Features:
    - Connection pooling
    - Retry automático com backoff exponencial
    - Timeout configurável
    - Logging completo
    """
    
    def __init__(
        self,
        base_url: str,
        api_key: str,
        timeout: float = 30.0,
        max_retries: int = 3,
        pool_size: int = 10
    ):
        """
        Inicializar cliente.
        
        Args:
            base_url: URL base da API (ex: https://webposto.com.br/api)
            api_key: Chave de autenticação
            timeout: Timeout em segundos
            max_retries: Número máximo de retries
            pool_size: Tamanho do connection pool
        """
        self.base_url = base_url.rstrip('/')
        self.api_key = api_key
        self.timeout = timeout
        self.max_retries = max_retries
        
        # Configurar client com connection pooling
        self.client: Optional[httpx.AsyncClient] = None
        self.pool_limits = httpx.Limits(
            max_connections=pool_size,
            max_keepalive_connections=pool_size
        )
    
    async def __aenter__(self):
        """Context manager entry."""
        await self.connect()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        await self.disconnect()
    
    async def connect(self) -> None:
        """Estabelecer conexão com pool."""
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        
        self.client = httpx.AsyncClient(
            base_url=self.base_url,
            timeout=self.timeout,
            headers=headers,
            limits=self.pool_limits
        )
        
        logger.info(f"WebPosto Client conectado: {self.base_url}")
    
    async def disconnect(self) -> None:
        """Fechar conexão."""
        if self.client:
            await self.client.aclose()
            logger.info("WebPosto Client desconectado")
    
    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        retry=retry_if_exception_type((httpx.TimeoutException, httpx.NetworkError)),
        reraise=True
    )
    async def _fazer_requisicao(
        self,
        method: str,
        endpoint: str,
        **kwargs
    ) -> Dict[str, Any]:
        """
        Fazer requisição com retry automático.
        
        Args:
            method: GET, POST, PUT, DELETE
            endpoint: Caminho da API (ex: /lancamentos)
            **kwargs: Argumentos adicionais (params, json, etc)
        
        Returns:
            Response JSON
        
        Raises:
            WebPostoClientException: Erros da API
        """
        if not self.client:
            raise WebPostoClientException("Cliente não conectado")
        
        try:
            url = f"/{endpoint.lstrip('/')}"
            response = await self.client.request(method, url, **kwargs)
            response.raise_for_status()
            
            return response.json()
        
        except httpx.HTTPStatusError as e:
            logger.error(
                f"Erro HTTP {e.response.status_code}: {e.response.text}"
            )
            raise WebPostoClientException(
                f"HTTP {e.response.status_code}: {e.response.text}"
            )
        
        except httpx.TimeoutException as e:
            logger.error(f"Timeout na requisição: {endpoint}")
            raise
        
        except httpx.NetworkError as e:
            logger.error(f"Erro de rede: {e}")
            raise
    
    async def obter_lancamentos(
        self,
        empresa_id: str,
        desde: Optional[datetime] = None,
        ate: Optional[datetime] = None,
        limite: int = 1000
    ) -> List[Dict[str, Any]]:
        """
        Obter lançamentos de uma empresa.
        
        Args:
            empresa_id: ID da empresa
            desde: Data inicial (opcional)
            ate: Data final (opcional)
            limite: Limite de registros
        
        Returns:
            Lista de lançamentos
        """
        params = {
            "limite": limite,
            "offset": 0
        }
        
        if desde:
            params["desde"] = desde.isoformat()
        if ate:
            params["ate"] = ate.isoformat()
        
        logger.info(f"Recuperando lançamentos para empresa {empresa_id}")
        
        resultado = await self._fazer_requisicao(
            "GET",
            f"/empresas/{empresa_id}/lancamentos",
            params=params
        )
        
        return resultado.get("lancamentos", [])
    
    async def obter_centros_custo(
        self,
        empresa_id: str
    ) -> List[Dict[str, Any]]:
        """
        Obter centros de custo de uma empresa.
        
        Args:
            empresa_id: ID da empresa
        
        Returns:
            Lista de centros de custo
        """
        logger.info(f"Recuperando centros de custo para empresa {empresa_id}")
        
        resultado = await self._fazer_requisicao(
            "GET",
            f"/empresas/{empresa_id}/centros-custo"
        )
        
        return resultado.get("centros_custo", [])
    
    async def obter_empresas(
        self,
        ativo: bool = True
    ) -> List[Dict[str, Any]]:
        """
        Obter lista de empresas.
        
        Args:
            ativo: Apenas empresas ativas
        
        Returns:
            Lista de empresas
        """
        logger.info("Recuperando lista de empresas")
        
        params = {"ativo": "true" if ativo else "false"}
        
        resultado = await self._fazer_requisicao(
            "GET",
            "/empresas",
            params=params
        )
        
        return resultado.get("empresas", [])
    
    async def registrar_rateio(
        self,
        empresa_id: str,
        rateio_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Registrar rateio na API.
        
        Args:
            empresa_id: ID da empresa
            rateio_data: Dados do rateio
        
        Returns:
            Resposta da API
        """
        logger.info(f"Registrando rateio para empresa {empresa_id}")
        
        resultado = await self._fazer_requisicao(
            "POST",
            f"/empresas/{empresa_id}/rateios",
            json=rateio_data
        )
        
        return resultado
    
    async def validar_conexao(self) -> bool:
        """
        Validar conectividade com API.
        
        Returns:
            True se conectada
        """
        try:
            resultado = await self._fazer_requisicao("GET", "/health")
            logger.info("WebPosto API respondendo: OK")
            return resultado.get("status") == "ok"
        
        except Exception as e:
            logger.error(f"WebPosto API indisponível: {e}")
            return False


class WebPostoClientFactory:
    """Factory para criar instâncias do cliente WebPosto."""
    
    @staticmethod
    def criar_cliente(
        base_url: str,
        api_key: str,
        **kwargs
    ) -> WebPostoClient:
        """
        Criar novo cliente WebPosto.
        
        Args:
            base_url: URL base
            api_key: Chave de API
            **kwargs: Argumentos adicionais
        
        Returns:
            Instância do cliente
        """
        return WebPostoClient(base_url=base_url, api_key=api_key, **kwargs)
