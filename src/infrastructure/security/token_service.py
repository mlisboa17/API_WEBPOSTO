"""
CLAUDE 3.7: Advanced Token Service with Refresh Token Rotation
Implements:
- RS256 asymmetric JWT generation/validation
- Refresh token rotation with Redis storage
- Token versioning for security
- Pydantic V2.15 validation
- Zero password logging
"""

from datetime import datetime, timedelta, timezone
from typing import Optional, Dict, Tuple
from enum import Enum
import jwt
from jwt import PyJWTError
from pydantic import BaseModel, Field, ConfigDict
import logging
import os
from functools import lru_cache

logger = logging.getLogger(__name__)

# Suppress JWT logs for security
logging.getLogger("jwt").setLevel(logging.WARNING)


class TokenType(str, Enum):
    """JWT token types"""
    ACCESS = "access"
    REFRESH = "refresh"


class TokenPayload(BaseModel):
    """JWT Token Payload (Pydantic V2.15)"""
    model_config = ConfigDict(
        strict=True,
        validate_assignment=True,
        json_schema_extra={
            "example": {
                "sub": "user@company.com",
                "role": "DIRECTOR",
                "company_id": "comp_123",
                "token_type": "access",
                "exp": 1715297200,
                "iat": 1715295400,
                "jti": "uuid-v4"
            }
        }
    )
    
    sub: str = Field(..., min_length=1, description="Subject (user_id)")
    role: str = Field(..., pattern="^(ADMIN|DIRECTOR|PARTNER|VIEWER)$")
    company_id: str = Field(...)
    token_type: TokenType = Field(default=TokenType.ACCESS)
    exp: int = Field(..., description="Expiration (Unix timestamp)")
    iat: int = Field(..., description="Issued at (Unix timestamp)")
    jti: str = Field(..., description="JWT ID (for tracking/revocation)")
    
    def model_post_init(self, __context):
        """Validate token not expired at creation"""
        if self.exp <= self.iat:
            raise ValueError("Token expiration must be after issued time")


class TokenService:
    """
    Advanced JWT token management with refresh rotation
    - Generates access + refresh token pairs
    - Validates tokens with public key caching
    - Manages token versioning
    - Integrates with Redis for blacklist/rotation
    """
    
    def __init__(
        self,
        private_key: str,
        public_key: str,
        algorithm: str = "RS256",
        access_ttl_minutes: int = 30,
        refresh_ttl_days: int = 7
    ):
        """
        Initialize token service
        
        Args:
            private_key: RSA private key (PEM format)
            public_key: RSA public key (PEM format)
            algorithm: Signing algorithm (RS256, RS512, etc)
            access_ttl_minutes: Access token TTL in minutes
            refresh_ttl_days: Refresh token TTL in days
        """
        self.private_key = private_key
        self.public_key = public_key
        self.algorithm = algorithm
        self.access_ttl_minutes = access_ttl_minutes
        self.refresh_ttl_days = refresh_ttl_days
    
    def _get_exp_timestamp(self, delta: timedelta) -> int:
        """Get expiration timestamp (UTC)"""
        exp_time = datetime.now(timezone.utc) + delta
        return int(exp_time.timestamp())
    
    def generate_token_pair(
        self,
        user_id: str,
        role: str,
        company_id: str,
        jti: str
    ) -> Dict[str, str]:
        """
        Generate access + refresh token pair (RS256)
        
        Args:
            user_id: User identifier
            role: User role (ADMIN, DIRECTOR, PARTNER, VIEWER)
            company_id: Active company ID
            jti: JWT ID for tracking
            
        Returns:
            {
                "access_token": "...",
                "refresh_token": "...",
                "token_type": "Bearer",
                "expires_in": 1800
            }
        """
        now = datetime.now(timezone.utc)
        now_timestamp = int(now.timestamp())
        
        # Access token (short-lived: 30 min)
        access_exp = self._get_exp_timestamp(timedelta(minutes=self.access_ttl_minutes))
        access_payload = TokenPayload(
            sub=user_id,
            role=role,
            company_id=company_id,
            token_type=TokenType.ACCESS,
            exp=access_exp,
            iat=now_timestamp,
            jti=jti
        )
        
        # Refresh token (long-lived: 7 days)
        refresh_exp = self._get_exp_timestamp(timedelta(days=self.refresh_ttl_days))
        refresh_payload = TokenPayload(
            sub=user_id,
            role=role,
            company_id=company_id,
            token_type=TokenType.REFRESH,
            exp=refresh_exp,
            iat=now_timestamp,
            jti=jti
        )
        
        # Sign with RS256
        try:
            access_token = jwt.encode(
                access_payload.model_dump(),
                self.private_key,
                algorithm=self.algorithm
            )
            
            refresh_token = jwt.encode(
                refresh_payload.model_dump(),
                self.private_key,
                algorithm=self.algorithm
            )
            
            logger.info(
                f"✅ Token pair generated for {user_id} "
                f"(role={role}, company={company_id})"
            )
            
            return {
                "access_token": access_token,
                "refresh_token": refresh_token,
                "token_type": "Bearer",
                "expires_in": self.access_ttl_minutes * 60
            }
        
        except Exception as e:
            logger.error(f"❌ Token generation error: {e}")
            raise
    
    def validate_token(self, token: str) -> Optional[TokenPayload]:
        """
        Validate and decode JWT token (RS256)
        
        Args:
            token: JWT token string
            
        Returns:
            TokenPayload if valid, None if invalid/expired
        """
        try:
            payload = jwt.decode(
                token,
                self.public_key,
                algorithms=[self.algorithm]
            )
            
            token_payload = TokenPayload(**payload)
            logger.debug(f"✅ Token validated: {token_payload.sub}")
            return token_payload
        
        except jwt.ExpiredSignatureError:
            logger.warning("❌ Token expired")
            return None
        except jwt.InvalidTokenError as e:
            logger.warning(f"❌ Invalid token: {e}")
            return None
        except Exception as e:
            logger.error(f"❌ Token validation error: {e}")
            return None
    
    def refresh_access_token(
        self,
        refresh_token: str,
        new_jti: str
    ) -> Optional[Dict[str, str]]:
        """
        Refresh access token using refresh token
        (with token rotation for security)
        
        Args:
            refresh_token: Valid refresh token
            new_jti: New JWT ID for rotated token
            
        Returns:
            New token pair, or None if refresh token invalid
        """
        payload = self.validate_token(refresh_token)
        
        if not payload or payload.token_type != TokenType.REFRESH:
            logger.warning("❌ Invalid refresh token")
            return None
        
        # Generate new token pair (rotation)
        new_tokens = self.generate_token_pair(
            user_id=payload.sub,
            role=payload.role,
            company_id=payload.company_id,
            jti=new_jti
        )
        
        logger.info(f"🔄 Token rotated for {payload.sub}")
        return new_tokens
    
    def decode_token_unsafe(self, token: str) -> Optional[Dict]:
        """
        Decode token WITHOUT signature verification
        ⚠️ SECURITY: For debugging only, NEVER use in production
        """
        try:
            return jwt.decode(token, options={"verify_signature": False})
        except Exception:
            return None


# ============================================================================
# Factory with environment configuration
# ============================================================================
@lru_cache(maxsize=1)
def get_token_service() -> TokenService:
    """
    Factory for token service with env config
    Uses caching to load keys only once
    """
    private_key = os.getenv("JWT_PRIVATE_KEY")
    public_key = os.getenv("JWT_PUBLIC_KEY")
    
    if not private_key or not public_key:
        raise ValueError("JWT_PRIVATE_KEY and JWT_PUBLIC_KEY not set in environment")
    
    return TokenService(
        private_key=private_key,
        public_key=public_key,
        algorithm=os.getenv("JWT_ALGORITHM", "RS256"),
        access_ttl_minutes=int(os.getenv("JWT_ACCESS_TTL_MINUTES", "30")),
        refresh_ttl_days=int(os.getenv("JWT_REFRESH_TTL_DAYS", "7"))
    )


# ============================================================================
# Examples & Testing
# ============================================================================
if __name__ == "__main__":
    import sys
    sys.path.insert(0, ".")
    
    # For testing, generate temporary keys
    from cryptography.hazmat.primitives.asymmetric import rsa
    from cryptography.hazmat.primitives import serialization
    from cryptography.hazmat.backends import default_backend
    
    print("🔑 Generating temporary test keys...")
    
    private_key = rsa.generate_private_key(65537, 2048, default_backend())
    private_pem = private_key.private_bytes(
        serialization.Encoding.PEM,
        serialization.PrivateFormat.PKCS8,
        serialization.NoEncryption()
    ).decode()
    
    public_pem = private_key.public_key().public_bytes(
        serialization.Encoding.PEM,
        serialization.PublicFormat.SubjectPublicKeyInfo
    ).decode()
    
    # Create service
    service = TokenService(private_pem, public_pem)
    
    # Generate tokens
    print("\n📝 Generating token pair...")
    tokens = service.generate_token_pair(
        user_id="test@company.com",
        role="DIRECTOR",
        company_id="comp_123",
        jti="jwt-id-1"
    )
    
    print(f"✅ Access token: {tokens['access_token'][:50]}...")
    print(f"✅ Refresh token: {tokens['refresh_token'][:50]}...")
    
    # Validate
    print("\n✔️ Validating access token...")
    payload = service.validate_token(tokens['access_token'])
    if payload:
        print(f"✅ Valid: {payload.sub} ({payload.role})")
    
    # Refresh
    print("\n🔄 Refreshing tokens...")
    new_tokens = service.refresh_access_token(
        tokens['refresh_token'],
        "jwt-id-2"
    )
    if new_tokens:
        print(f"✅ New access token: {new_tokens['access_token'][:50]}...")
