"""
Exceções customizadas para o cliente WebPosto.
"""

from typing import Optional


class WebPostoError(Exception):
    """Erro base do WebPosto."""

    def __init__(
        self,
        message: str,
        status_code: Optional[int] = None,
        response_body: Optional[str] = None,
    ):
        super().__init__(message)
        self.status_code = status_code
        self.response_body = response_body

    def __str__(self):
        base = super().__str__()
        if self.status_code:
            return f"[HTTP {self.status_code}] {base}"
        return base


class AuthError(WebPostoError):
    """Chave de integração inválida ou não autorizada (HTTP 401/403)."""

    pass


class NotFoundError(WebPostoError):
    """Recurso não encontrado (HTTP 404)."""

    pass


class BadRequestError(WebPostoError):
    """Requisição inválida — parâmetros incorretos (HTTP 400)."""

    pass


class ServerError(WebPostoError):
    """Erro interno no servidor WebPosto (HTTP 500)."""

    pass


class TimeoutError(WebPostoError):
    """Timeout na requisição."""

    pass


class ConnectionError(WebPostoError):
    """Erro de conexão com o servidor."""

    pass
