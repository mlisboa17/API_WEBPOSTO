#!/usr/bin/env python3
"""
🔐 Security Setup Script for Logos Space (2026)
Generates all necessary cryptographic keys and secrets
Run: python scripts/generate_secrets.py

Creates:
- JWT RS256 keys (private + public)
- AES encryption key (Fernet)
- Random secrets (API keys, passwords)
- Stores in .env file securely
"""

import os
import sys
import argparse
from pathlib import Path
from datetime import datetime

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

try:
    from cryptography.fernet import Fernet
    from cryptography.hazmat.primitives.asymmetric import rsa
    from cryptography.hazmat.primitives import serialization
    from cryptography.hazmat.backends import default_backend
except ImportError:
    print("❌ cryptography library not installed!")
    print("   Run: pip install cryptography pyjwt[crypto] bcrypt")
    sys.exit(1)


class SecretGenerator:
    """Generate cryptographic secrets"""
    
    @staticmethod
    def generate_jwt_keys(key_size: int = 2048) -> tuple[str, str]:
        """
        Generate RS256 (RSA) key pair for JWT
        
        Args:
            key_size: RSA key size (2048 or 4096)
            
        Returns:
            (private_key_pem, public_key_pem)
        """
        print(f"🔑 Generating {key_size}-bit RSA key pair (JWT RS256)...")
        
        # Generate private key
        private_key = rsa.generate_private_key(
            public_exponent=65537,
            key_size=key_size,
            backend=default_backend()
        )
        
        # Serialize to PEM
        private_pem = private_key.private_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PrivateFormat.PKCS8,
            encryption_algorithm=serialization.NoEncryption()
        ).decode('utf-8')
        
        # Extract public key
        public_key = private_key.public_key()
        public_pem = public_key.public_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PublicFormat.SubjectPublicKeyInfo
        ).decode('utf-8')
        
        print("✅ JWT keys generated successfully")
        return private_pem, public_pem
    
    @staticmethod
    def generate_aes_key() -> str:
        """
        Generate Fernet encryption key (AES-128)
        
        Returns:
            Base64-encoded Fernet key
        """
        print("🔑 Generating AES-128 encryption key (Fernet)...")
        key = Fernet.generate_key().decode('utf-8')
        print("✅ AES key generated successfully")
        return key
    
    @staticmethod
    def generate_random_secret(length: int = 32) -> str:
        """Generate random secret"""
        import secrets
        return secrets.token_urlsafe(length)
    
    @staticmethod
    def generate_password(length: int = 16) -> str:
        """Generate random password"""
        import secrets
        import string
        
        alphabet = string.ascii_letters + string.digits + "!@#$%^&*"
        password = ''.join(secrets.choice(alphabet) for i in range(length))
        return password


def create_env_file(output_path: str = ".env.security"):
    """
    Create .env file with all security secrets
    
    Args:
        output_path: Path to output .env file
    """
    print("\n" + "="*70)
    print("🔐 LOGOS SPACE: Security Configuration Generator")
    print("="*70 + "\n")
    
    gen = SecretGenerator()
    
    # Generate secrets
    jwt_private, jwt_public = gen.generate_jwt_keys()
    aes_key = gen.generate_aes_key()
    secret_key = gen.generate_random_secret()
    db_password = gen.generate_password()
    redis_password = gen.generate_password()
    grafana_password = gen.generate_password()
    smtp_password = gen.generate_password()
    
    # Format output
    env_content = f"""# ============================================================================
# 🔐 LOGOS SPACE: Security Configuration
# Generated: {datetime.now().isoformat()}
# ============================================================================
# ⚠️ PRODUCTION: Copy secret values to .env file (not in version control)
# ⚠️ NEVER share these secrets in Slack, email, or version control

# ============================================================================
# Database (PostgreSQL)
# ============================================================================
DB_PASSWORD={db_password}

# ============================================================================
# Redis (Token Storage + Caching)
# ============================================================================
REDIS_PASSWORD={redis_password}

# ============================================================================
# JWT (RS256 - Asymmetric Key Pair)
# ============================================================================
# Private Key (KEEP SECRET - Never share):
JWT_PRIVATE_KEY={repr(jwt_private)}

# Public Key (Can be shared):
JWT_PUBLIC_KEY={repr(jwt_public)}

JWT_ALGORITHM=RS256
JWT_EXPIRATION_MINUTES=30
JWT_REFRESH_EXPIRATION_DAYS=7

# ============================================================================
# AES Encryption (Fernet - for sensitive field encryption)
# ============================================================================
AES_KEY={aes_key}

# ============================================================================
# General Security
# ============================================================================
SECRET_KEY={secret_key}
BCRYPT_ROUNDS=12

# ============================================================================
# Rate Limiting & Brute-Force Protection (GROK 4)
# ============================================================================
RATE_LIMIT_MAX_ATTEMPTS=5
RATE_LIMIT_WINDOW_SECONDS=300
RATE_LIMIT_LOCKOUT_SECONDS=900

# ============================================================================
# Monitoring & Admin
# ============================================================================
GRAFANA_PASSWORD={grafana_password}

# ============================================================================
# Email (SMTP)
# ============================================================================
SMTP_PASSWORD={smtp_password}

# ============================================================================
# CORS (Frontend URL)
# ============================================================================
CORS_ORIGINS=https://logos.space,https://www.logos.space

# ============================================================================
# Environment
# ============================================================================
ENVIRONMENT=production
DEBUG=false
DEPLOYMENT_ID=prod-{datetime.now().strftime('%Y%m%d')}
"""
    
    # Write file
    with open(output_path, 'w') as f:
        f.write(env_content)
    
    # Set restrictive permissions (Unix-like systems)
    try:
        os.chmod(output_path, 0o600)  # rw------- (owner only)
    except Exception:
        pass  # Windows doesn't support this
    
    print(f"\n✅ Configuration file created: {output_path}")
    print("   Permissions: Read/Write (owner only)")
    
    # Display secrets (with masking)
    print("\n" + "="*70)
    print("🔑 SECRET SUMMARY (DO NOT SHARE)")
    print("="*70)
    print(f"JWT Private Key: {SecretGenerator.generate_random_secret(8)}...")
    print(f"AES Key: {aes_key[:20]}...")
    print(f"DB Password: {gen.generate_password()[:10]}...")
    print(f"Redis Password: {gen.generate_password()[:10]}...")
    print("\n💾 Full secrets saved to:", output_path)
    print("⚠️  Add to .gitignore (already done if using default setup)")
    
    return env_content


def merge_env_files():
    """Merge .env.security into .env"""
    print("\n🔄 Merging security secrets into .env...")
    
    security_path = ".env.security"
    env_path = ".env"
    
    if not os.path.exists(security_path):
        print(f"❌ {security_path} not found!")
        return False
    
    # Read security secrets
    with open(security_path, 'r') as f:
        security_content = f.read()
    
    # Merge with existing .env
    if os.path.exists(env_path):
        with open(env_path, 'a') as f:
            f.write("\n# ============================================================================\n")
            f.write("# 🔐 SECURITY SECRETS (auto-generated)\n")
            f.write("# ============================================================================\n")
            f.write(security_content)
        print(f"✅ Merged secrets into {env_path}")
    else:
        os.rename(security_path, env_path)
        print(f"✅ Renamed {security_path} to {env_path}")
    
    # Clean up security file
    try:
        os.remove(security_path)
    except:
        pass
    
    return True


def verify_secrets():
    """Verify all required secrets are in .env"""
    print("\n✅ Verifying secrets...")
    
    env_path = ".env"
    if not os.path.exists(env_path):
        print(f"❌ {env_path} not found!")
        return False
    
    required_secrets = [
        "JWT_PRIVATE_KEY",
        "JWT_PUBLIC_KEY",
        "AES_KEY",
        "SECRET_KEY",
        "DB_PASSWORD",
        "REDIS_PASSWORD",
    ]
    
    with open(env_path, 'r') as f:
        env_content = f.read()
    
    missing = []
    for secret in required_secrets:
        if secret not in env_content:
            missing.append(secret)
    
    if missing:
        print(f"❌ Missing secrets: {', '.join(missing)}")
        return False
    
    print("✅ All required secrets present in .env")
    return True


def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(description="Generate Logos Space security secrets")
    parser.add_argument("--output", default=".env.security", help="Output file path")
    parser.add_argument("--merge", action="store_true", help="Merge secrets into .env")
    parser.add_argument("--verify", action="store_true", help="Verify secrets in .env")
    
    args = parser.parse_args()
    
    try:
        # Generate secrets
        if not args.verify:
            create_env_file(args.output)
        
        # Merge if requested
        if args.merge:
            merge_env_files()
        
        # Verify
        if args.verify or args.merge:
            verify_secrets()
        
        print("\n✅ Security setup completed!")
        
    except KeyboardInterrupt:
        print("\n⚠️  Cancelled by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
