from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Configurações da aplicação. Lê do .env."""

    # Ambiente
    environment: str = "development"
    debug: bool = True

    # webPosto API
    # Aliases aceitos no .env: WEBPOSTO_API_URL (= WEBPOSTO_BASE_URL),
    # WEBPOSTO_TOKEN / WEBPOSTO_APP_KEY (= WEBPOSTO_API_KEY).
    webposto_base_url: str = "https://web.qualityautomacao.com.br"
    webposto_api_url: str = ""  # alias opcional de WEBPOSTO_API_URL
    webposto_api_key: str = ""
    webposto_token: str = ""  # alias opcional de WEBPOSTO_TOKEN
    webposto_app_key: str = ""  # alias opcional de WEBPOSTO_APP_KEY
    webposto_api_key_posto_vip_rio_doce: str = ""
    webposto_api_key_posto_casa_caiada: str = ""
    webposto_api_key_posto_doze_filial_ii: str = ""
    # Aliases oficiais por filial (preferenciais)
    webposto_casa_caiada_key: str = ""  # 5555
    webposto_vip_key: str = ""  # 11495
    webposto_real_doze_key: str = ""  # 74014
    webposto_vip_posto_id: str = "VIP"
    webposto_vip_posto_nome: str = "POSTO_VIP"
    webposto_sync_interval_seconds: int = 3600
    webposto_timeout_seconds: int = 30
    webposto_money_debug: bool = False
    # Opt-in: sem HTTP ao ERP; só cache/SQLite/snapshot. Default false = online.
    webposto_offline_mode: bool = False

    # Indicadores externos de mercado (USD, Brent, Esalq)
    market_data_api_key: str = ""  # AwesomeAPI token (opcional)
    market_data_timeout_seconds: float = 12.0
    market_data_cache_ttl_seconds: int = 300

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
    # Com pista_sync_worker_enabled=True, main.py força 1 processo (cache RAM único).
    api_workers: int = 1
    api_title: str = "webPosto Service API"
    api_version: str = "0.1.0"

    # Sprint 01 — monta rotas cash/operator (/cash/operations, /performance, …)
    enable_operational_routes: bool = True

    # Cockpit 30s — cache RAM + worker asyncio (sem Redis)
    pista_sync_worker_enabled: bool = True
    pista_sync_interval_seconds: int = 30

    # Rate Limiting
    rate_limit_requests: int = 100
    rate_limit_window_seconds: int = 60

    # Security / Auth
    secret_key: str = "logos-dev-hs256-local-only-not-for-prod!"
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 15
    refresh_token_expire_days: int = 7
    consumer_token: str = "dev-consumer-token"
    admin_token: str = "dev-admin-token"
    auth_user_email: str = ""
    auth_user_password: str = ""
    auth_user_password_hash: str = ""
    auth_user_role: str = "director"
    auth_user_company_id: str = "default-company"
    auth_cookie_secure: bool = False
    cors_allowed_origins: str = "http://127.0.0.1:8040,http://localhost:8040,http://localhost:3000,http://127.0.0.1:3000,http://localhost:3006,http://127.0.0.1:3006"

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
    departmental_scheduler_enabled: bool = False
    departmental_scheduler_poll_seconds: int = 60
    # Arquitetura híbrida — consolidação D-1 às 03:00 AM (cron 0 3 * * *)
    data_sync_scheduler_enabled: bool = True
    data_sync_catchup_enabled: bool = True
    data_sync_catchup_on_boot: bool = True
    data_sync_catchup_max_days: int = 7
    data_sync_day_timeout_seconds: float = 40
    data_sync_day_retries: int = 2
    # O WebPosto pode ultrapassar 8 s mesmo em partições diárias da empresa 74014.
    # Mantém a tentativa limitada, mas permite concluir uma chamada diária válida.
    sales_live_timeout_seconds: int = 20
    sales_total_budget_seconds: int = 30
    stock_live_timeout_seconds: int = 8
    stock_total_budget_seconds: int = 22

    # Guardião WhatsApp — alertas anti-fraude em tempo real (Sprint 6)
    whatsapp_alerts_enabled: bool = False
    whatsapp_webhook_url: str = ""
    whatsapp_frontend_base_url: str = "http://localhost:3000"

    # DF-e / NF-e entrada — defaults seguros (não alterar .env nesta entrega)
    # Documentar: DFE_AUTO_SYNC_ENABLED, DFE_MANIFESTATION_ENABLED, DFE_VAULT_MASTER_KEY
    dfe_auto_sync_enabled: bool = False
    dfe_manifestation_enabled: bool = False
    dfe_vault_master_key: str = ""  # espelho; vault lê os.environ DFE_VAULT_MASTER_KEY

    # HMAC da conta bancária no módulo de depósito em dinheiro (VIP 11495)
    cash_deposit_account_hash_key: str = ""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    def allowed_origins(self) -> list[str]:
        return [
            origin.strip()
            for origin in self.cors_allowed_origins.split(",")
            if origin.strip()
        ]

    def local_auth_configured(self) -> bool:
        """Login local só vale com e-mail e senha ou hash definidos no ambiente."""
        if not (self.auth_user_email or "").strip():
            return False
        if (self.auth_user_password_hash or "").strip():
            return True
        return bool((self.auth_user_password or "").strip())

    def validate_production_security(self) -> None:
        if self.environment.strip().lower() not in {"production", "prod"}:
            return
        failures: list[str] = []
        if self.debug:
            failures.append("DEBUG_ENABLED")
        if self.secret_key in {
            "changeme_replace_in_env",
            "logos-dev-hs256-local-only-not-for-prod!",
        } or len(self.secret_key.encode("utf-8")) < 32:
            failures.append("WEAK_SECRET_KEY")
        if self.consumer_token == "dev-consumer-token":
            failures.append("DEFAULT_CONSUMER_TOKEN")
        if self.admin_token == "dev-admin-token":
            failures.append("DEFAULT_ADMIN_TOKEN")
        if self.auth_user_password or not self.auth_user_password_hash:
            failures.append("PASSWORD_HASH_REQUIRED")
        if not self.auth_cookie_secure:
            failures.append("SECURE_COOKIE_REQUIRED")
        if "*" in self.allowed_origins():
            failures.append("WILDCARD_CORS_FORBIDDEN")
        if not self.cash_deposit_account_hash_key.strip():
            failures.append("CASH_DEPOSIT_ACCOUNT_HASH_KEY_MISSING")
        if failures:
            raise RuntimeError(
                "INSECURE_PRODUCTION_CONFIGURATION:" + ",".join(failures)
            )


# Instância global de settings
settings = Settings()
