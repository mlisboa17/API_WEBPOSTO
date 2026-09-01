from fastapi import FastAPI
from fastapi.testclient import TestClient

from src.infrastructure.config.settings import Settings, settings
from src.infrastructure.security.passwords import hash_password
from src.infrastructure.security.jwt_utils import decode_token
from src.interfaces.http.routes import auth

_TEST_EMAIL = "qa.local@logos.test"
_TEST_PASSWORD = "TestLocalPassword-NotUsedInProd"
_PROBE_EMAIL = "sonda-nao-configurada@exemplo.local"
_PROBE_PASSWORD = "sonda-senha-nao-configurada"


def _build_client() -> TestClient:
    app = FastAPI()
    app.include_router(auth.router)
    return TestClient(app)


def _configure_plaintext_auth(monkeypatch) -> None:
    monkeypatch.setattr(settings, "auth_user_email", _TEST_EMAIL)
    monkeypatch.setattr(settings, "auth_user_password", _TEST_PASSWORD)
    monkeypatch.setattr(settings, "auth_user_password_hash", "")
    monkeypatch.setattr(settings, "auth_user_role", "director")
    monkeypatch.setattr(settings, "auth_cookie_secure", False)


def _assert_no_secrets(response, caplog=None, *extras: str) -> None:
    blob = response.text
    forbidden = [
        _TEST_PASSWORD,
        _PROBE_PASSWORD,
        _PROBE_EMAIL,
        settings.secret_key,
        settings.auth_user_password_hash,
        *extras,
    ]
    for item in forbidden:
        if item:
            assert item not in blob
    lowered = blob.casefold()
    assert "pbkdf2_sha256" not in lowered
    assert "auth_user_password" not in lowered
    if caplog is not None:
        log_blob = caplog.text
        for item in forbidden:
            if item:
                assert item not in log_blob


def test_local_auth_configured_exige_email_e_segredo():
    empty = Settings.model_construct(auth_user_email="", auth_user_password="", auth_user_password_hash="")
    assert empty.local_auth_configured() is False

    only_email = Settings.model_construct(
        auth_user_email=_TEST_EMAIL, auth_user_password="", auth_user_password_hash=""
    )
    assert only_email.local_auth_configured() is False

    with_password = Settings.model_construct(
        auth_user_email=_TEST_EMAIL,
        auth_user_password=_TEST_PASSWORD,
        auth_user_password_hash="",
    )
    assert with_password.local_auth_configured() is True

    with_hash = Settings.model_construct(
        auth_user_email=_TEST_EMAIL,
        auth_user_password="",
        auth_user_password_hash="pbkdf2_sha256$salt$hash",
    )
    assert with_hash.local_auth_configured() is True


def test_configuracao_ausente_bloqueia_login(monkeypatch, caplog):
    monkeypatch.setattr(settings, "auth_user_email", "")
    monkeypatch.setattr(settings, "auth_user_password", "")
    monkeypatch.setattr(settings, "auth_user_password_hash", "")
    client = _build_client()

    response = client.post(
        "/auth/login",
        json={"email": _PROBE_EMAIL, "password": _PROBE_PASSWORD},
    )

    assert response.status_code == 503
    assert response.json()["detail"] == auth.LOCAL_AUTH_UNCONFIGURED
    assert "access_token" not in response.cookies
    assert "refresh_token" not in response.cookies
    _assert_no_secrets(response, caplog)


def test_somente_email_sem_senha_bloqueia_login(monkeypatch, caplog):
    monkeypatch.setattr(settings, "auth_user_email", _TEST_EMAIL)
    monkeypatch.setattr(settings, "auth_user_password", "")
    monkeypatch.setattr(settings, "auth_user_password_hash", "")
    client = _build_client()

    response = client.post(
        "/auth/login",
        json={"email": _TEST_EMAIL, "password": _TEST_PASSWORD},
    )

    assert response.status_code == 503
    assert response.json()["detail"] == auth.LOCAL_AUTH_UNCONFIGURED
    _assert_no_secrets(response, caplog, _TEST_EMAIL, _TEST_PASSWORD)


def test_login_com_credenciais_validas(monkeypatch, caplog):
    _configure_plaintext_auth(monkeypatch)
    client = _build_client()

    response = client.post(
        "/auth/login",
        json={"email": _TEST_EMAIL, "password": _TEST_PASSWORD},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["user"]["email"] == _TEST_EMAIL
    assert payload["user"]["role"] == "director"
    assert "access_token" in response.cookies
    assert "refresh_token" in response.cookies
    assert _TEST_PASSWORD not in response.text
    assert settings.secret_key not in response.text
    assert _TEST_PASSWORD not in caplog.text


def test_login_rejeita_credenciais_invalidas(monkeypatch, caplog):
    _configure_plaintext_auth(monkeypatch)
    client = _build_client()

    response = client.post(
        "/auth/login",
        json={"email": _TEST_EMAIL, "password": "senha_incorreta"},
    )

    assert response.status_code == 401
    assert response.json()["detail"] == "Invalid credentials"
    assert "access_token" not in response.cookies
    _assert_no_secrets(response, caplog, "senha_incorreta")


def test_login_com_hash_de_senha(monkeypatch, caplog):
    client = _build_client()
    senha = "SenhaMuitoForte@123"
    senha_hash = hash_password(senha)

    monkeypatch.setattr(settings, "auth_user_email", "secure@company.com")
    monkeypatch.setattr(settings, "auth_user_password", "")
    monkeypatch.setattr(settings, "auth_user_password_hash", senha_hash)

    response = client.post(
        "/auth/login",
        json={"email": "secure@company.com", "password": senha},
    )

    assert response.status_code == 200
    assert response.json()["user"]["email"] == "secure@company.com"
    assert senha not in response.text
    assert senha_hash not in response.text
    assert senha not in caplog.text
    assert senha_hash not in caplog.text


def test_refresh_exige_cookie():
    client = _build_client()

    response = client.post("/auth/refresh")

    assert response.status_code == 401
    assert response.json()["detail"] == "Missing refresh token"


def test_ciclo_login_refresh_logout(monkeypatch):
    _configure_plaintext_auth(monkeypatch)
    client = _build_client()

    login = client.post(
        "/auth/login",
        json={"email": _TEST_EMAIL, "password": _TEST_PASSWORD},
    )
    refresh = client.post("/auth/refresh")
    refreshed_payload = decode_token(client.cookies.get("access_token"))
    logout = client.post("/auth/logout")
    refresh_after_logout = client.post("/auth/refresh")

    assert login.status_code == 200
    assert refresh.status_code == 200
    assert refresh.json()["email"] == _TEST_EMAIL
    assert refreshed_payload["role"] == "director"
    assert logout.status_code == 200
    assert logout.json() == {"ok": True}
    assert refresh_after_logout.status_code == 401
    assert _TEST_PASSWORD not in login.text
    assert _TEST_PASSWORD not in refresh.text


def test_login_uses_secure_cookie_when_configured(monkeypatch):
    _configure_plaintext_auth(monkeypatch)
    client = _build_client()
    monkeypatch.setattr(settings, "auth_cookie_secure", True)

    response = client.post(
        "/auth/login",
        json={"email": _TEST_EMAIL, "password": _TEST_PASSWORD},
    )

    assert response.status_code == 200
    assert "Secure" in response.headers["set-cookie"]
    assert _TEST_PASSWORD not in response.text


def test_login_cookie_local_http_sem_secure(monkeypatch):
    _configure_plaintext_auth(monkeypatch)
    client = _build_client()

    response = client.post(
        "/auth/login",
        json={"email": _TEST_EMAIL, "password": _TEST_PASSWORD},
    )

    assert response.status_code == 200
    assert "Secure" not in response.headers["set-cookie"]
