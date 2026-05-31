"""Tests for domain layer"""
import pytest
from datetime import datetime
from decimal import Decimal
from src.domain.entities import CashExpense, PostoCredentials
from src.domain.exceptions import (
    PostoNaoConfiguradoException,
    DadosInvalidosException
)


class TestCashExpense:
    """Unit tests para entidade CashExpense"""
    
    def test_create_cash_expense(self):
        """Deve criar uma instância de CashExpense válida"""
        expense = CashExpense(
            id="exp-001",
            posto_id="23",
            valor=Decimal("150.50"),
            descricao="Combustível",
            timestamp=datetime.utcnow()
        )
        assert expense.id == "exp-001"
        assert expense.posto_id == "23"
        assert expense.valor == Decimal("150.50")
    
    def test_cash_expense_immutability(self):
        """CashExpense deve ser imutável (frozen=True)"""
        expense = CashExpense(
            id="exp-001",
            posto_id="23",
            valor=Decimal("150.50"),
            descricao="Combustível"
        )
        with pytest.raises(Exception):  # Pydantic ValidationError
            expense.valor = Decimal("200.00")


class TestPostoCredentials:
    """Unit tests para entidade PostoCredentials"""
    
    def test_create_posto_credentials(self):
        """Deve criar uma instância de PostoCredentials válida"""
        cred = PostoCredentials(
            id="cred-001",
            posto_id="23",
            api_key="key-abc123",
            api_secret="secret-xyz789",
            status="ativa"
        )
        assert cred.posto_id == "23"
        assert cred.api_key == "key-abc123"


class TestDomainExceptions:
    """Unit tests para exceções do domínio"""
    
    def test_posto_nao_configurado_exception(self):
        """Deve criar exceção quando posto não configurado"""
        with pytest.raises(PostoNaoConfiguradoException):
            raise PostoNaoConfiguradoException(posto_id="999")
    
    def test_dados_invalidos_exception(self):
        """Deve criar exceção para dados inválidos"""
        with pytest.raises(DadosInvalidosException):
            raise DadosInvalidosException(field="valor", message="Deve ser positivo")
