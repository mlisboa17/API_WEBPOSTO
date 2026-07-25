import pytest

from src.infrastructure.config.settings import Settings


def test_production_rejects_insecure_defaults():
    config = Settings(
        _env_file=None,
        environment="production",
        debug=True,
        secret_key="short",
        consumer_token="dev-consumer-token",
        admin_token="dev-admin-token",
        auth_user_password="password",
        auth_user_password_hash="",
        auth_cookie_secure=False,
        cors_allowed_origins="*",
    )

    with pytest.raises(RuntimeError, match="INSECURE_PRODUCTION_CONFIGURATION"):
        config.validate_production_security()


def test_production_accepts_hardened_configuration():
    config = Settings(
        _env_file=None,
        environment="production",
        debug=False,
        secret_key="a" * 48,
        consumer_token="consumer-production-token",
        admin_token="admin-production-token",
        auth_user_password="",
        auth_user_password_hash="$2b$12$configured-hash",
        auth_cookie_secure=True,
        cors_allowed_origins="https://app.example.com",
    )

    config.validate_production_security()
    assert config.allowed_origins() == ["https://app.example.com"]
