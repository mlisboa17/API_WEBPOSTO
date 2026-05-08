"""
Configuração integrada: webPosto + Logos (Eye, Space, Vorcaro)
Carrega de .env com validação rigorosa
"""

from dotenv import load_dotenv
import os
from typing import Optional

load_dotenv()


class WebPostoSettings:
    """Configurações da API webPosto"""

    BASE_URL: str = os.getenv("WEBPOSTO_BASE_URL", "").rstrip("/")
    BEARER_TOKEN: str = os.getenv("WEBPOSTO_BEARER_TOKEN", "")
    API_KEY: Optional[str] = os.getenv("WEBPOSTO_API_KEY", None)
    API_SECRET: Optional[str] = os.getenv("WEBPOSTO_API_SECRET", None)

    # Endpoints API WebPosto (prefixo /v1)
    ENDPOINT_V1_HEALTH: str = os.getenv("WEBPOSTO_V1_HEALTH", "/v1/health")
    ENDPOINT_V1_DESPESAS: str = os.getenv(
        "WEBPOSTO_V1_DESPESAS", "/v1/financeiro/despesas"
    )
    ENDPOINT_V1_FECHAMENTOS: str = os.getenv(
        "WEBPOSTO_V1_FECHAMENTOS", "/v1/financeiro/fechamentos"
    )
    ENDPOINT_V1_FECHAMENTO_CAIXA: str = os.getenv(
        "WEBPOSTO_V1_FECHAMENTO_CAIXA", "/v1/financeiro/fechamento-caixa"
    )
    ENDPOINT_V1_MOVIMENTACAO_ESPECIE: str = os.getenv(
        "WEBPOSTO_V1_MOVIMENTACAO_ESPECIE", "/v1/financeiro/movimentacao-especie"
    )

    # Exige .env válido + health WebPosto no startup da API (sem dados fictícios)
    STRICT_STARTUP: bool = (
        os.getenv("WEBPOSTO_STRICT_STARTUP", "true").lower() == "true"
    )

    # Network
    TIMEOUT_SECONDS: int = int(os.getenv("WEBPOSTO_TIMEOUT", "30"))
    MAX_RETRIES: int = int(os.getenv("WEBPOSTO_MAX_RETRIES", "3"))
    RETRY_DELAY: float = float(os.getenv("WEBPOSTO_RETRY_DELAY", "1.0"))

    # Unidades (IDs numéricos no WebPosto)
    UNIDADES: list = [1, 2, 3]

    def validate(self):
        """Valida configurações obrigatórias"""
        errors = []
        if not self.BASE_URL:
            errors.append("WEBPOSTO_BASE_URL não configurada")
        if not self.BEARER_TOKEN:
            errors.append("WEBPOSTO_BEARER_TOKEN não configurada")

        if errors:
            raise ValueError(f"Erros de configuração: {', '.join(errors)}")


class LogosSettings:
    """Configurações de integração com ecossistema Logos"""

    # Logos Eye (monitoramento em tempo real)
    EYE_ENABLED: bool = os.getenv("LOGOS_EYE_ENABLED", "true").lower() == "true"
    EYE_URL: str = os.getenv("LOGOS_EYE_URL", "http://localhost:5000").rstrip("/")
    EYE_API_KEY: Optional[str] = os.getenv("LOGOS_EYE_API_KEY", None)

    # Logos Space (persistência + histórico)
    SPACE_ENABLED: bool = os.getenv("LOGOS_SPACE_ENABLED", "true").lower() == "true"
    SPACE_MONGODB_URI: str = os.getenv(
        "LOGOS_SPACE_DB", "mongodb://localhost:27017/logos"
    )
    SPACE_DB_NAME: str = "logos_auditoria"

    # Vorcaro (analytics + BI)
    VORCARO_ENABLED: bool = os.getenv("VORCARO_ENABLED", "false").lower() == "true"
    VORCARO_URL: str = os.getenv("VORCARO_URL", "http://localhost:6000").rstrip("/")
    VORCARO_API_KEY: Optional[str] = os.getenv("VORCARO_API_KEY", None)


class AppSettings:
    """Configurações gerais da aplicação"""

    NAME: str = "Logos Auditoria"
    VERSION: str = "1.0.0"
    DEBUG: bool = os.getenv("DEBUG", "false").lower() == "true"

    # Server
    HOST: str = os.getenv("HOST", "0.0.0.0")
    PORT: int = int(os.getenv("PORT", "8000"))

    # Logging
    LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO")

    # Timezone
    TIMEZONE: str = os.getenv("TZ", "America/Sao_Paulo")


# Instâncias globais
webposto = WebPostoSettings()
logos = LogosSettings()
app = AppSettings()


class _Settings:
    """Compatível com `from config import settings` (base_url + bearer)."""

    @property
    def WEBPOSTO_BASE_URL(self) -> str:
        return webposto.BASE_URL

    @property
    def WEBPOSTO_BEARER_TOKEN(self) -> str:
        return webposto.BEARER_TOKEN


settings = _Settings()


# Validação na inicialização
def initialize_config():
    """Valida e inicializa configurações"""
    try:
        webposto.validate()
        print(f"✓ webPosto: {webposto.BASE_URL}")
        print(f"✓ LogosEye: {webposto.UNIDADES}")
        if logos.EYE_ENABLED:
            print(f"✓ LogosEye: {logos.EYE_URL}")
        if logos.SPACE_ENABLED:
            print("✓ LogosSpace: MongoDB")
        if logos.VORCARO_ENABLED:
            print(f"✓ Vorcaro: {logos.VORCARO_URL}")
        return True
    except ValueError as e:
        print(f"✗ Erro de configuração: {e}")
        return False


if __name__ == "__main__":
    initialize_config()
