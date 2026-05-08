"""
WebPosto API Client
Integração com a API REST do sistema webPosto (Quality Automação).

Base URL: http://web.qualityautomacao.com.br
Auth: query param ?CHAVE=<integration_key>
Docs: https://web.qualityautomacao.com.br/webjars/swagger-ui/index.html?configUrl=/v3/api-docs/swagger-config
"""

from .client import WebPostoClient
from .config import WebPostoConfig
from .exceptions import WebPostoError, AuthError, NotFoundError, ServerError

__version__ = "1.0.0"
__all__ = [
    "WebPostoClient",
    "WebPostoConfig",
    "WebPostoError",
    "AuthError",
    "NotFoundError",
    "ServerError",
]
