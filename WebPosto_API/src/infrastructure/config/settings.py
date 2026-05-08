from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Configurações da aplicação. Lê do .env."""

    # Ambiente
    environment: str = "development"
    debug: bool = True

    # webPosto API
    webposto_base_url: str = "http://web.qualityautomacao.com.br"
    webposto_api_key: str = ""
    webposto_sync_interval_seconds: int = 3600
    webposto_timeout_seconds: int = 30

    # Banco de Dados
    database_url: str = "postgresql+asyncpg://postgres:postgres@localhost:5432/webposto"
    database_pool_size: int = 20
    database_max_overflow: int = 40
    database_echo: bool = False

    # Redis
    redis_url: str = "redis://localhost:6379/0"
    redis_timeout: int = 30

    # Logging
    log_level: str = "INFO"
    log_format: str = "json"

    # API
    api_host: str = "0.0.0.0"
    api_port: int = 8000
    api_workers: int = 4
    api_title: str = "webPosto Service API"
    api_version: str = "0.1.0"

    # Rate Limiting
    rate_limit_requests: int = 100
    rate_limit_window_seconds: int = 60

    # Circuit Breaker
    circuit_breaker_threshold: int = 5
    circuit_breaker_timeout: int = 60

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = False


# Instância global de settings
settings = Settings()
