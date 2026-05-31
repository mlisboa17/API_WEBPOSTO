"""
GROK 4: Token Bucket Rate Limiter with Redis
Implements:
- Token bucket algorithm for smooth rate limiting
- Sub-millisecond response times
- Automatic IP blocking after failed attempts
- Redis-backed distributed rate limiting
"""

import redis
import time
import math
from typing import Tuple, Optional
import logging

logger = logging.getLogger(__name__)


class TokenBucketLimiter:
    """
    Token bucket rate limiter using Redis
    - Smooth rate limiting (not sliding window)
    - Distributed across instances
    - Sub-millisecond performance
    """
    
    def __init__(
        self,
        redis_url: str = "redis://localhost:6379/2",
        capacity: int = 5,  # tokens in bucket
        refill_rate: float = 0.1,  # tokens per second (1 token per 10 seconds)
    ):
        """
        Initialize token bucket limiter
        
        Args:
            redis_url: Redis connection URL
            capacity: Bucket capacity (max tokens)
            refill_rate: Tokens refilled per second
        """
        self.redis = redis.from_url(redis_url)
        self.capacity = capacity
        self.refill_rate = refill_rate
        
        try:
            self.redis.ping()
            logger.info("✅ Redis token bucket initialized")
        except Exception as e:
            logger.error(f"❌ Redis connection failed: {e}")
            raise
    
    def _get_bucket_key(self, identifier: str) -> str:
        """Get Redis key for bucket"""
        return f"bucket:{identifier}"
    
    def _get_last_refill_key(self, identifier: str) -> str:
        """Get Redis key for last refill timestamp"""
        return f"refill:{identifier}"
    
    def _get_blocked_key(self, identifier: str) -> str:
        """Get Redis key for block status"""
        return f"blocked:{identifier}"
    
    def allow_request(self, identifier: str) -> Tuple[bool, dict]:
        """
        Check if request is allowed (token bucket algorithm)
        
        Args:
            identifier: Client identifier (IP address, user ID)
            
        Returns:
            (allowed: bool, info: dict with remaining tokens)
        """
        bucket_key = self._get_bucket_key(identifier)
        refill_key = self._get_last_refill_key(identifier)
        blocked_key = self._get_blocked_key(identifier)
        
        # Check if blocked
        if self.redis.exists(blocked_key):
            ttl = self.redis.ttl(blocked_key)
            logger.warning(f"🔒 Request blocked: {identifier} (TTL: {ttl}s)")
            return False, {
                "allowed": False,
                "reason": "ip_blocked",
                "block_remaining_seconds": ttl
            }
        
        now = time.time()
        
        # Get current bucket state
        current_tokens_str = self.redis.get(bucket_key)
        last_refill_str = self.redis.get(refill_key)
        
        if current_tokens_str is None:
            # Initialize bucket
            current_tokens = float(self.capacity)
            last_refill = now
        else:
            current_tokens = float(current_tokens_str)
            last_refill = float(last_refill_str)
        
        # Calculate tokens to add (refill)
        time_passed = now - last_refill
        tokens_to_add = time_passed * self.refill_rate
        current_tokens = min(self.capacity, current_tokens + tokens_to_add)
        
        # Check if request allowed
        if current_tokens >= 1.0:
            # Allow request
            current_tokens -= 1.0
            
            # Store updated state (with TTL to clean old buckets)
            pipe = self.redis.pipeline()
            pipe.setex(bucket_key, 86400, str(current_tokens))  # 24h TTL
            pipe.setex(refill_key, 86400, str(now))
            pipe.execute()
            
            logger.debug(
                f"✅ Request allowed: {identifier} "
                f"(tokens: {current_tokens:.2f}/{self.capacity})"
            )
            
            return True, {
                "allowed": True,
                "tokens_remaining": current_tokens,
                "capacity": self.capacity
            }
        else:
            # Reject request
            logger.warning(
                f"❌ Rate limit exceeded: {identifier} "
                f"(tokens: {current_tokens:.2f})"
            )
            
            return False, {
                "allowed": False,
                "reason": "rate_limit_exceeded",
                "tokens_remaining": current_tokens,
                "capacity": self.capacity,
                "refill_after_seconds": (1.0 - current_tokens) / self.refill_rate
            }
    
    def block_identifier(self, identifier: str, duration_seconds: int = 900) -> bool:
        """
        Manually block identifier (after failed login attempts)
        
        Args:
            identifier: Client to block
            duration_seconds: Block duration (default 15 min)
            
        Returns:
            True if blocked
        """
        blocked_key = self._get_blocked_key(identifier)
        self.redis.setex(blocked_key, duration_seconds, "1")
        logger.info(f"🔒 Identifier blocked: {identifier} (duration: {duration_seconds}s)")
        return True
    
    def unblock_identifier(self, identifier: str) -> bool:
        """Manually unblock identifier"""
        blocked_key = self._get_blocked_key(identifier)
        self.redis.delete(blocked_key)
        logger.info(f"🔓 Identifier unblocked: {identifier}")
        return True
    
    def is_blocked(self, identifier: str) -> bool:
        """Check if identifier is blocked"""
        blocked_key = self._get_blocked_key(identifier)
        return self.redis.exists(blocked_key) > 0
    
    def reset_bucket(self, identifier: str) -> bool:
        """Reset bucket to full capacity"""
        bucket_key = self._get_bucket_key(identifier)
        refill_key = self._get_last_refill_key(identifier)
        
        pipe = self.redis.pipeline()
        pipe.delete(bucket_key)
        pipe.delete(refill_key)
        pipe.execute()
        
        logger.info(f"🔄 Bucket reset: {identifier}")
        return True
    
    def get_status(self, identifier: str) -> dict:
        """Get current bucket status"""
        bucket_key = self._get_bucket_key(identifier)
        blocked_key = self._get_blocked_key(identifier)
        
        current_tokens_str = self.redis.get(bucket_key)
        is_blocked = self.redis.exists(blocked_key) > 0
        
        if current_tokens_str is None:
            current_tokens = float(self.capacity)
        else:
            current_tokens = float(current_tokens_str)
        
        return {
            "identifier": identifier,
            "current_tokens": current_tokens,
            "capacity": self.capacity,
            "refill_rate": self.refill_rate,
            "is_blocked": is_blocked,
            "bucket_fill_percent": (current_tokens / self.capacity) * 100
        }


class LoginRateLimiter:
    """Login-specific rate limiter with auto-blocking"""
    
    def __init__(
        self,
        redis_url: str = "redis://localhost:6379/2",
        max_failed_attempts: int = 5,
        block_duration_seconds: int = 900
    ):
        """
        Initialize login rate limiter
        
        Args:
            redis_url: Redis connection URL
            max_failed_attempts: Failed attempts before blocking
            block_duration_seconds: Auto-block duration
        """
        self.limiter = TokenBucketLimiter(
            redis_url=redis_url,
            capacity=max_failed_attempts,
            refill_rate=0.1  # 1 token per 10 seconds
        )
        self.max_attempts = max_failed_attempts
        self.block_duration = block_duration_seconds
    
    def attempt_login(
        self,
        identifier: str,
        success: bool = False
    ) -> Tuple[bool, dict]:
        """
        Record login attempt
        
        Args:
            identifier: IP or user ID
            success: Whether login succeeded
            
        Returns:
            (allowed, info)
        """
        if success:
            # Reset on success
            self.limiter.reset_bucket(identifier)
            logger.info(f"✅ Login successful: {identifier}")
            return True, {"allowed": True, "message": "Login successful"}
        
        # Failed attempt - consume token
        allowed, info = self.limiter.allow_request(identifier)
        
        if not allowed and info.get("reason") == "rate_limit_exceeded":
            # Auto-block after max attempts
            logger.critical(
                f"🔒 Auto-blocking: {identifier} after {self.max_attempts} failed attempts"
            )
            self.limiter.block_identifier(identifier, self.block_duration)
            
            info["auto_blocked"] = True
            info["block_duration_seconds"] = self.block_duration
        
        return allowed, info


# ============================================================================
# Singleton instances
# ============================================================================

def get_token_bucket_limiter(redis_url: str = None) -> TokenBucketLimiter:
    """Factory for token bucket limiter"""
    import os
    
    if redis_url is None:
        redis_url = os.getenv("REDIS_RATE_LIMIT_URL", "redis://localhost:6379/2")
    
    return TokenBucketLimiter(redis_url)


def get_login_rate_limiter(redis_url: str = None) -> LoginRateLimiter:
    """Factory for login rate limiter"""
    import os
    
    if redis_url is None:
        redis_url = os.getenv("REDIS_RATE_LIMIT_URL", "redis://localhost:6379/2")
    
    return LoginRateLimiter(redis_url)


# ============================================================================
# Examples
# ============================================================================

if __name__ == "__main__":
    print("📊 Token Bucket Rate Limiter Example")
    
    limiter = TokenBucketLimiter(capacity=5, refill_rate=0.1)
    
    # Simulate requests
    ip = "192.168.1.100"
    print(f"\n🎯 Testing {ip}")
    
    for i in range(1, 8):
        allowed, info = limiter.allow_request(ip)
        print(f"  Request {i}: allowed={allowed}, tokens={info.get('tokens_remaining', 0):.1f}")
    
    # Login rate limiter
    print(f"\n🔐 Login Rate Limiter Example")
    login_limiter = LoginRateLimiter(max_failed_attempts=3)
    
    for i in range(1, 5):
        allowed, info = login_limiter.attempt_login(ip, success=False)
        print(f"  Failed attempt {i}: allowed={allowed}, blocked={info.get('auto_blocked', False)}")
    
    # Check status
    status = limiter.get_status(ip)
    print(f"\n📈 Status: {status['bucket_fill_percent']:.1f}% full")
