import os
from typing import Any, Dict

from src.domain.exceptions import PostoInativoException, PostoNaoConfiguradoException
from src.infrastructure.cache import CacheManager
from src.infrastructure.repository import PostoCredentialsRepository
from src.infrastructure.webposto_client import WebPostoClient


class FetchProductsUseCase:
    def __init__(
        self,
        repository: PostoCredentialsRepository,
        webposto_client: WebPostoClient,
        cache: CacheManager,
    ) -> None:
        self.repository = repository
        self.webposto_client = webposto_client
        self.cache = cache

    async def execute(
        self,
        posto_id: str,
        include_inactive: bool = False,
        force_refresh: bool = False,
    ) -> Dict[str, Any]:
        cache_key = f"{posto_id}:{'all' if include_inactive else 'active'}"
        if not force_refresh:
            cached = self.cache.get_by_key(namespace="products_catalog", identifier=cache_key)
            if cached is not None:
                return cached

        tenant = await self.repository.get_tenant_by_posto_id(posto_id)
        if tenant is None:
            raise PostoNaoConfiguradoException(posto_id=posto_id)
        if not tenant.ativo:
            raise PostoInativoException(posto_id=posto_id)
        if not tenant.webposto_base_url or not tenant.webposto_base_url.strip():
            raise PostoNaoConfiguradoException(posto_id=posto_id)
        if not tenant.api_key or not tenant.api_key.strip():
            raise PostoNaoConfiguradoException(posto_id=posto_id)

        endpoint_path = os.getenv("WEBPOSTO_PRODUCTS_ENDPOINT", "/INTEGRACAO/PRODUTOS")
        async with self.webposto_client as client:
            result = await client.fetch_products_catalog(
                base_url=tenant.webposto_base_url,
                api_key=tenant.api_key,
                posto_id=posto_id,
                include_inactive=include_inactive,
                endpoint_path=endpoint_path,
            )

        if force_refresh:
            self.cache.invalidate(namespace="products_catalog")

        self.cache.set_by_key(namespace="products_catalog", identifier=cache_key, value=result)
        return result
