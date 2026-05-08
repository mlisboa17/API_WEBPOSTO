import pytest

from src.domain.entities.cliente import Cliente
from src.domain.events.cliente_events import ClienteAdicionado


class TestClienteEntity:
    """Testes unitários para a entidade Cliente."""

    def test_criar_cliente_valido(self, cliente_dict):
        """Deve criar um cliente com dados válidos."""
        cliente = Cliente(**cliente_dict)

        assert cliente.id == cliente_dict["id"]
        assert cliente.nome == cliente_dict["nome"]
        assert cliente.cnpj == cliente_dict["cnpj"]
        assert cliente.ativo is True

    def test_cliente_nome_vazio_deve_falhar(self, cliente_dict):
        """Deve falhar ao criar cliente com nome vazio."""
        cliente_dict["nome"] = "   "
        with pytest.raises(ValueError, match="Nome do cliente não pode ser vazio"):
            Cliente(**cliente_dict)

    def test_cliente_cnpj_invalido_deve_falhar(self, cliente_dict):
        """Deve falhar ao criar cliente com CNPJ inválido."""
        cliente_dict["cnpj"] = "123"
        with pytest.raises(ValueError, match="CNPJ inválido"):
            Cliente(**cliente_dict)

    def test_ativar_cliente(self, cliente_dict):
        """Deve ativar um cliente desativado."""
        cliente_dict["ativo"] = False
        cliente = Cliente(**cliente_dict)

        cliente.ativar()
        assert cliente.ativo is True

    def test_desativar_cliente(self, cliente_dict):
        """Deve desativar um cliente ativado."""
        cliente = Cliente(**cliente_dict)
        assert cliente.ativo is True

        cliente.desativar()
        assert cliente.ativo is False

    def test_atualizar_dados_cliente(self, cliente_dict):
        """Deve atualizar dados do cliente."""
        cliente = Cliente(**cliente_dict)
        novo_nome = "Novo Nome"
        novo_cnpj = "98765432109876"

        cliente.atualizar_dados(nome=novo_nome, cnpj=novo_cnpj)

        assert cliente.nome == novo_nome
        assert cliente.cnpj == novo_cnpj

    def test_adicionar_evento_a_cliente(self, cliente_dict):
        """Deve adicionar evento ao cliente."""
        cliente = Cliente(**cliente_dict)
        evento = ClienteAdicionado(nome=cliente.nome, cnpj=cliente.cnpj)

        cliente.adicionar_evento(evento)

        assert len(cliente.obter_eventos()) == 1
        assert cliente.obter_eventos()[0].event_name == "ClienteAdicionado"

    def test_limpar_eventos(self, cliente_dict):
        """Deve limpar eventos após obtê-los."""
        cliente = Cliente(**cliente_dict)
        evento = ClienteAdicionado(nome=cliente.nome, cnpj=cliente.cnpj)
        cliente.adicionar_evento(evento)

        eventos = cliente.limpar_eventos()

        assert len(eventos) == 1
        assert len(cliente.obter_eventos()) == 0
