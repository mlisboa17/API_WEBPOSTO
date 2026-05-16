from datetime import timedelta
from typing import Dict

from fastapi import APIRouter, Depends, HTTPException, Response, status, Request
from pydantic import BaseModel

from src.infrastructure.config.settings import settings
from src.infrastructure.security.jwt_utils import (
    create_access_token,
    create_refresh_token,
    decode_token,
)

router = APIRouter(prefix="/auth", tags=["auth"]) 


class LoginPayload(BaseModel):
    email: str
    password: str


@router.post("/login")
async def login(payload: LoginPayload, response: Response):
    """Mock login: validate credentials, set HttpOnly cookies (access + refresh)."""
    # TODO: Replace with real user validation (DB)
    if payload.email != "admin@company.com" or payload.password != "password":
        raise HTTPException(status_code=401, detail="Invalid credentials")

    # subject can be user id or email
    subject = payload.email
    access_token = create_access_token(subject, extra={"role": "director"})
    refresh_token = create_refresh_token(subject)

    # Set HttpOnly Secure cookies
    response.set_cookie(
        "access_token",
        access_token,
        httponly=True,
        secure=False,
        samesite="lax",
        max_age=60 * settings.access_token_expire_minutes,
        path="/",
    )
    response.set_cookie(
        "refresh_token",
        refresh_token,
        httponly=True,
        secure=False,
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
            "role": "director",
            "company_id": "default-company",
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
    access_token = create_access_token(subject)
    response.set_cookie(
        "access_token",
        access_token,
        httponly=True,
        secure=False,
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
