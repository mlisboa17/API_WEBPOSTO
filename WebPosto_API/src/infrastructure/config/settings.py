from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Configurações da aplicação. Lê do .env."""

    # Ambiente
    environment: str = "development"
    debug: bool = True

    # webPosto API
    webposto_base_url: str = "http://web.qualityautomacao.com.br"
    webposto_api_key: str = ""
    webposto_api_key_posto_vip_rio_doce: str = ""
    webposto_api_key_posto_casa_caiada: str = ""
    webposto_api_key_posto_doze_filial_ii: str = ""
    webposto_vip_posto_id: str = "VIP"
    webposto_vip_posto_nome: str = "POSTO_VIP"
    webposto_sync_interval_seconds: int = 3600
    webposto_timeout_seconds: int = 30
    webposto_money_debug: bool = False

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
    api_port: int = 8040
    api_workers: int = 4
    api_title: str = "webPosto Service API"
    api_version: str = "0.1.0"

    # Rate Limiting
    rate_limit_requests: int = 100
    rate_limit_window_seconds: int = 60

    # Security / Auth
    secret_key: str = "changeme_replace_in_env"
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 15
    refresh_token_expire_days: int = 7
    consumer_token: str = "dev-consumer-token"
    admin_token: str = "dev-admin-token"
    auth_user_email: str = "admin@company.com"
    auth_user_password: str = "password"
    auth_user_password_hash: str = ""
    auth_user_role: str = "director"
    auth_user_company_id: str = "default-company"

    # Circuit Breaker
    circuit_breaker_threshold: int = 5
    circuit_breaker_timeout: int = 60

    # F08.2 — Financial Auto-Recovery & Snapshot Scheduling
    financial_scheduler_enabled: bool = True
    financial_snapshot_refresh_interval_seconds: int = 3600
    financial_snapshot_retention_days: int = 30
    financial_snapshot_rolling_days: int = 7
    financial_auto_recovery_enabled: bool = True
    financial_auto_recovery_interval_seconds: int = 900
    financial_live_budget_seconds: int = 22
    # O WebPosto pode ultrapassar 8 s mesmo em partições diárias da empresa 74014.
    # Mantém a tentativa limitada, mas permite concluir uma chamada diária válida.
    sales_live_timeout_seconds: int = 20
    sales_total_budget_seconds: int = 30
    stock_live_timeout_seconds: int = 8
    stock_total_budget_seconds: int = 22

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = False
        extra = "ignore"


# Instância global de settings
settings = Settings()
