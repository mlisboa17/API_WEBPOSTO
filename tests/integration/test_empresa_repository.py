"""
Integration Test: PostgresEmpresaRepository
"""
import asyncio
import pytest
from src.infrastructure.database import get_session
from src.infrastructure.persistence.models import Empresa
from src.infrastructure.persistence.repositories import PostgresEmpresaRepository
import uuid

@pytest.mark.asyncio
async def test_insert_and_get_empresa():
    async with get_session() as session:
        repo = PostgresEmpresaRepository(session)
        empresa_id = str(uuid.uuid4())
        empresa = Empresa(
            empresa_id=empresa_id,
            nome="Posto Teste",
            config_tipo_rateio="padrao",
            validar_soma_100=True,
            ativo=True
        )
        await repo.save(empresa)
        loaded = await repo.get_by_id(empresa_id)
        assert loaded is not None
        assert loaded.empresa_id.valor == empresa_id
        assert loaded.nome == "Posto Teste"
