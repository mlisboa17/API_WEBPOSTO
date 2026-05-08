"""
Configuração do cliente WebPosto.
"""

from dataclasses import dataclass
from typing import Optional
import os


@dataclass
class WebPostoConfig:
    """
    Configuração da integração com o WebPosto.

    Attributes:
        chave: Chave de integração gerada no WebPosto
                (Administração > Integrações > Integração > Incluir > API Integração)
        base_url: URL base da API (padrão: http://web.qualityautomacao.com.br)
        timeout: Timeout das requisições em segundos (padrão: 30)
        empresa_codigo: Código da empresa/filial (opcional, alguns endpoints exigem)
        max_retries: Número máximo de tentativas em caso de erro (padrão: 3)
        verify_ssl: Verificar certificado SSL (padrão: True)
    """

    chave: str
    base_url: str = "http://web.qualityautomacao.com.br"
    timeout: int = 30
    empresa_codigo: Optional[int] = None
    max_retries: int = 3
    verify_ssl: bool = True

    @classmethod
    def from_env(cls) -> "WebPostoConfig":
        """Carrega configuração a partir de variáveis de ambiente."""
        chave = os.environ.get("WEBPOSTO_CHAVE")
        if not chave:
            raise ValueError(
                "Variável de ambiente WEBPOSTO_CHAVE não definida. "
                "Obtenha a chave em: Administração > Integrações > Integração > Incluir > API Integração"
            )

        empresa_codigo_str = os.environ.get("WEBPOSTO_EMPRESA_CODIGO")
        empresa_codigo = int(empresa_codigo_str) if empresa_codigo_str else None

        return cls(
            chave=chave,
            base_url=os.environ.get(
                "WEBPOSTO_BASE_URL", "http://web.qualityautomacao.com.br"
            ),
            timeout=int(os.environ.get("WEBPOSTO_TIMEOUT", "30")),
            empresa_codigo=empresa_codigo,
            max_retries=int(os.environ.get("WEBPOSTO_MAX_RETRIES", "3")),
            verify_ssl=os.environ.get("WEBPOSTO_VERIFY_SSL", "true").lower() == "true",
        )
