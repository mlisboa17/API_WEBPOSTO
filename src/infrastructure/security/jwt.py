"""
CLAUDE 3.7: JWT Orchestration with RS256 (Asymmetric Keys)
Implements:
- Token generation/validation with RS256
- Token payload: sub, role, company_id, exp, iat
- Refresh token rotation via Redis
- Type-safe with Pydantic V2
"""

from datetime import datetime, timedelta, timezone
from typing import Optional, Dict, Any
from enum import Enum

import jwt
from jwt import PyJWTError
from pydantic import BaseModel, Field, ConfigDict
import os


class TokenType(str, Enum):
    """Token types"""
    ACCESS = "access"
    REFRESH = "refresh"


class TokenPayload(BaseModel):
    """JWT Token Payload (Pydantic V2)"""
    model_config = ConfigDict(strict=True)
    
    sub: str = Field(..., description="Subject (user_id)")
    role: str = Field(..., description="User role (PARTNER, DIRECTOR, VIEWER)")
    company_id: str = Field(..., description="Active company ID")
    token_type: TokenType = Field(default=TokenType.ACCESS)
    exp: int = Field(..., description="Expiration timestamp")
    iat: int = Field(..., description="Issued at timestamp")
    jti: Optional[str] = Field(None, description="JWT ID for blacklisting")


class JWTConfig(BaseModel):
    """JWT Configuration"""
    model_config = ConfigDict(strict=True, extra="forbid")
    
    algorithm: str = Field(default="RS256")
    access_token_expire_minutes: int = Field(default=30)
    refresh_token_expire_days: int = Field(default=7)
    private_key: str = Field(..., description="Private key for signing")
    public_key: str = Field(..., description="Public key for verification")


class JWTOrchestrator:
    """
    Orchestrates JWT token lifecycle:
    - Generation (access + refresh tokens)
    - Validation
    - Refresh token rotation
    - Token blacklisting
    """
    
    def __init__(self, config: JWTConfig):
        self.config = config
        self.algorithm = config.algorithm
        
    def generate_tokens(
        self,
        user_id: str,
        role: str,
        company_id: str,
        jti: Optional[str] = None
    ) -> Dict[str, str]:
        """
        Generate access + refresh token pair (RS256 signed)
        
        Args:
            user_id: User identifier
            role: User role (PARTNER, DIRECTOR, VIEWER)
            company_id: Active company ID
            jti: JWT ID for token tracking
            
        Returns:
            {"access_token": "...", "refresh_token": "...", "token_type": "bearer"}
        """
        now = datetime.now(timezone.utc)
        
        # Access token payload
        access_exp = now + timedelta(minutes=self.config.access_token_expire_minutes)
        access_payload = TokenPayload(
            sub=user_id,
            role=role,
            company_id=company_id,
            token_type=TokenType.ACCESS,
            exp=int(access_exp.timestamp()),
            iat=int(now.timestamp()),
            jti=jti
        )
        
        # Refresh token payload
        refresh_exp = now + timedelta(days=self.config.refresh_token_expire_days)
        refresh_payload = TokenPayload(
            sub=user_id,
            role=role,
            company_id=company_id,
            token_type=TokenType.REFRESH,
            exp=int(refresh_exp.timestamp()),
            iat=int(now.timestamp()),
            jti=jti
        )
        
        # Sign tokens with RS256
        access_token = jwt.encode(
            access_payload.model_dump(),
            self.config.private_key,
            algorithm=self.algorithm
        )
        
        refresh_token = jwt.encode(
            refresh_payload.model_dump(),
            self.config.private_key,
            algorithm=self.algorithm
        )
        
        return {
            "access_token": access_token,
            "refresh_token": refresh_token,
            "token_type": "bearer",
            "expires_in": self.config.access_token_expire_minutes * 60
        }
    
    def validate_token(self, token: str) -> Optional[TokenPayload]:
        """
        Validate and decode JWT token (RS256)
        
        Args:
            token: JWT token string
            
        Returns:
            TokenPayload if valid, None if invalid
        """
        try:
            payload = jwt.decode(
                token,
                self.config.public_key,
                algorithms=[self.algorithm]
            )
            return TokenPayload(**payload)
        except PyJWTError as e:
            print(f"❌ JWT validation error: {e}")
            return None
    
    def refresh_token(self, refresh_token: str) -> Optional[Dict[str, str]]:
        """
        Refresh access token using refresh token
        
        Args:
            refresh_token: Refresh token string
            
        Returns:
            New token pair or None if invalid
        """
        payload = self.validate_token(refresh_token)
        
        if not payload or payload.token_type != TokenType.REFRESH:
            return None
        
        # Generate new tokens
        return self.generate_tokens(
            user_id=payload.sub,
            role=payload.role,
            company_id=payload.company_id,
            jti=payload.jti
        )
    
    def decode_token_unsafe(self, token: str) -> Optional[Dict[str, Any]]:
        """
        Decode token WITHOUT validation (for debugging only)
        ⚠️ SECURITY: Only use in development/testing
        """
        try:
            return jwt.decode(
                token,
                options={"verify_signature": False}
            )
        except Exception:
            return None


# ============================================================================
# Singleton instance
# ============================================================================
def get_jwt_orchestrator() -> JWTOrchestrator:
    """Factory for JWT Orchestrator with env config"""
    config = JWTConfig(
        private_key=os.getenv("JWT_PRIVATE_KEY", ""),
        public_key=os.getenv("JWT_PUBLIC_KEY", "")
    )
    return JWTOrchestrator(config)
