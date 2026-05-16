import pytest
from unittest.mock import AsyncMock

from src.application.dto.cliente_dto import ClienteCreateDTO, ClienteUpdateDTO
from src.application.services.cliente_service import ClienteService
from src.domain.entities.cliente import Cliente


class TestClienteService:
    """Testes unitários para ClienteService."""

    @pytest.fixture
    def mocked_dependencies(self):
        """Fixture: Dependências mockadas."""
        repository = AsyncMock()
        event_bus = AsyncMock()
        service = ClienteService(repository, event_bus)
        return service, repository, event_bus

    @pytest.mark.asyncio
    async def test_criar_cliente(self, mocked_dependencies):
        """Deve criar um novo cliente."""
        service, repository, event_bus = mocked_dependencies

        dto = ClienteCreateDTO(
            nome="Cliente Teste", cnpj="12345678901234", webposto_id="WP001"
        )

        resultado = await service.criar_cliente(dto)

        assert resultado.nome == dto.nome
        assert resultado.cnpj == dto.cnpj
        assert resultado.ativo is True
        assert repository.save.called
        assert event_bus.publish.called

    @pytest.mark.asyncio
    async def test_obter_cliente_existente(self, mocked_dependencies, cliente_dict):
        """Deve obter um cliente existente."""
        service, repository, event_bus = mocked_dependencies

        cliente = Cliente(**cliente_dict)
        repository.find_by_id.return_value = cliente

        resultado = await service.obter_cliente(cliente_dict["id"])

        assert resultado is not None
        assert resultado.nome == cliente.nome
        repository.find_by_id.assert_called_once_with(cliente_dict["id"])

    @pytest.mark.asyncio
    async def test_obter_cliente_nao_existente(self, mocked_dependencies):
        """Deve retornar None para cliente não existente."""
        service, repository, event_bus = mocked_dependencies

        repository.find_by_id.return_value = None

        resultado = await service.obter_cliente("id-inexistente")

        assert resultado is None

    @pytest.mark.asyncio
    async def test_listar_clientes(self, mocked_dependencies):
        """Deve listar clientes com paginação."""
        service, repository, event_bus = mocked_dependencies

        clientes = [
            Cliente(id="1", nome="Cliente 1", cnpj="12345678901234"),
            Cliente(id="2", nome="Cliente 2", cnpj="98765432109876"),
        ]
        repository.find_all.return_value = clientes

        resultado = await service.listar_clientes(skip=0, limit=10)

        assert len(resultado) == 2
        assert resultado[0].nome == "Cliente 1"
        repository.find_all.assert_called_once_with(0, 10)

    @pytest.mark.asyncio
    async def test_atualizar_cliente(self, mocked_dependencies, cliente_dict):
        """Deve atualizar um cliente existente."""
        service, repository, event_bus = mocked_dependencies

        cliente = Cliente(**cliente_dict)
        repository.find_by_id.return_value = cliente

        dto = ClienteUpdateDTO(nome="Nome Atualizado")

        resultado = await service.atualizar_cliente(cliente_dict["id"], dto)

        assert resultado is not None
        assert resultado.nome == "Nome Atualizado"
        assert repository.update.called
        assert event_bus.publish.called

    @pytest.mark.asyncio
    async def test_deletar_cliente(self, mocked_dependencies):
        """Deve deletar um cliente."""
        service, repository, event_bus = mocked_dependencies

        repository.delete.return_value = True

        resultado = await service.deletar_cliente("id-para-deletar")

        assert resultado is True
        repository.delete.assert_called_once_with("id-para-deletar")

    @pytest.mark.asyncio
    async def test_deletar_cliente_nao_existente(self, mocked_dependencies):
        """Deve retornar False ao tentar deletar cliente não existente."""
        service, repository, event_bus = mocked_dependencies

        repository.delete.return_value = False

        resultado = await service.deletar_cliente("id-inexistente")

        assert resultado is False
