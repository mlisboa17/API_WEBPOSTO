from datetime import datetime
from typing import List

from src.domain.entities import CashExpense
from src.domain.exceptions import PostoInativoException, PostoNaoConfiguradoException
from src.infrastructure.cache import CacheManager
from src.infrastructure.repository import PostoCredentialsRepository
from src.infrastructure.webposto_client import WebPostoClient


class FetchExpensesUseCase:
    """Use case orchestration for expense retrieval."""

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
        data_consulta: datetime,
    ) -> List[CashExpense]:
        cached = self.cache.get(posto_id=posto_id, data_consulta=data_consulta)
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

        async with self.webposto_client as client:
            expenses = await client.fetch_deb_expenses(
                base_url=tenant.webposto_base_url,
                api_key=tenant.api_key,
                posto_id=posto_id,
                data_alvo=data_consulta,
            )

        self.cache.set(posto_id=posto_id, data_consulta=data_consulta, value=expenses)
        return expenses
