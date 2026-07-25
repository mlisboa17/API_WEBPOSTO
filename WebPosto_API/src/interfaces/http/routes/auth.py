import hmac

from fastapi import APIRouter, Depends, HTTPException, Response, status, Request
from pydantic import BaseModel

from src.infrastructure.config.settings import settings
from src.infrastructure.security.jwt_utils import (
    create_access_token,
    create_refresh_token,
    decode_token,
)
from src.infrastructure.security.passwords import verify_password

router = APIRouter(prefix="/auth", tags=["auth"]) 


class LoginPayload(BaseModel):
    email: str
    password: str


def _validate_credentials(email: str, password: str) -> bool:
    if email != settings.auth_user_email:
        return False

    if settings.auth_user_password_hash:
        return verify_password(password, settings.auth_user_password_hash)

    return hmac.compare_digest(password, settings.auth_user_password)


@router.post("/login")
async def login(payload: LoginPayload, response: Response):
    """Validate credentials and issue access/refresh tokens."""
    if not _validate_credentials(payload.email, payload.password):
        raise HTTPException(status_code=401, detail="Invalid credentials")

    # subject can be user id or email
    subject = payload.email
    access_token = create_access_token(subject, extra={"role": settings.auth_user_role})
    refresh_token = create_refresh_token(
        subject,
        extra={"role": settings.auth_user_role},
    )

    # Set HttpOnly Secure cookies
    response.set_cookie(
        "access_token",
        access_token,
        httponly=True,
        secure=settings.auth_cookie_secure,
        samesite="lax",
        max_age=60 * settings.access_token_expire_minutes,
        path="/",
    )
    response.set_cookie(
        "refresh_token",
        refresh_token,
        httponly=True,
        secure=settings.auth_cookie_secure,
        samesite="lax",
        max_age=60 * 60 * 24 * settings.refresh_token_expire_days,
        path="/auth/refresh",
    )

    # Return tokens and user info to frontend
    return {
        "access_token": access_token,
        "refresh_token": refresh_token,
        "token_type": "Bearer",
        "expires_in": settings.access_token_expire_minutes * 60,
        "user": {
            "sub": payload.email,
            "email": payload.email,
            "role": settings.auth_user_role,
            "company_id": settings.auth_user_company_id,
            "permissions": ["READ", "WRITE", "DELETE", "AUDIT", "EXPORT"]
        }
    }


@router.post("/refresh")
async def refresh(request: Request, response: Response):
    refresh_token = request.cookies.get("refresh_token")
    if not refresh_token:
        raise HTTPException(status_code=401, detail="Missing refresh token")
    try:
        payload = decode_token(refresh_token)
    except Exception:
        raise HTTPException(status_code=401, detail="Invalid refresh token")

    subject = payload.get("sub")
    role = payload.get("role") or settings.auth_user_role
    access_token = create_access_token(subject, extra={"role": role})
    response.set_cookie(
        "access_token",
        access_token,
        httponly=True,
        secure=settings.auth_cookie_secure,
        samesite="lax",
        max_age=60 * settings.access_token_expire_minutes,
        path="/",
    )
    return {"email": subject}


@router.post("/logout")
async def logout(response: Response):
    # Clear cookies
    response.delete_cookie("access_token", path="/")
    response.delete_cookie("refresh_token", path="/auth/refresh")
    return {"ok": True}
