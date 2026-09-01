from datetime import datetime, timedelta
from typing import Dict, Any

import jwt

from src.infrastructure.config.settings import settings


def create_access_token(subject: str, extra: Dict[str, Any] | None = None) -> str:
    now = datetime.utcnow()
    exp = now + timedelta(minutes=settings.access_token_expire_minutes)
    payload = {
        "sub": subject,
        "exp": exp,
        "iat": now,
    }
    if extra:
        payload.update(extra)
    token = jwt.encode(payload, settings.secret_key, algorithm=settings.jwt_algorithm)
    return token


def create_refresh_token(subject: str, extra: Dict[str, Any] | None = None) -> str:
    now = datetime.utcnow()
    exp = now + timedelta(days=settings.refresh_token_expire_days)
    payload = {"sub": subject, "exp": exp, "iat": now}
    if extra:
        payload.update(extra)
    token = jwt.encode(payload, settings.secret_key, algorithm=settings.jwt_algorithm)
    return token


def decode_token(token: str) -> Dict[str, Any]:
    try:
        if token.startswith("Bearer "):
            token = token[7:]
        payload = jwt.decode(token, settings.secret_key, algorithms=[settings.jwt_algorithm])
        if not isinstance(payload, dict):
            raise ValueError("Token payload is not a dict")
        return payload
    except jwt.ExpiredSignatureError:
        raise
    except Exception:
        raise
