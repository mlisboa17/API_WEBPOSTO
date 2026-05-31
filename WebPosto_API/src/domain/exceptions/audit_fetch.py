"""Erros de busca de dados reais para auditoria — nunca retornar mock."""

from __future__ import annotations


class AuditFetchError(Exception):
    """Falha ao obter dados da API WebPosto."""

    def __init__(self, message: str, *, erros: list[str] | None = None) -> None:
        super().__init__(message)
        self.erros = erros or []
