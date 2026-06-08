import hashlib
import hmac
import secrets


def hash_password(password: str, *, salt: str | None = None) -> str:
    """Gera hash PBKDF2-SHA256 no formato pbkdf2_sha256$salt$hash."""
    if salt is None:
        salt = secrets.token_hex(16)

    digest = hashlib.pbkdf2_hmac(
        "sha256", password.encode("utf-8"), salt.encode("utf-8"), 100_000
    )
    return f"pbkdf2_sha256${salt}${digest.hex()}"


def verify_password(password: str, encoded_hash: str) -> bool:
    """Valida senha em comparação de tempo constante."""
    try:
        algorithm, salt, hashed_value = encoded_hash.split("$", 2)
    except ValueError:
        return False

    if algorithm != "pbkdf2_sha256":
        return False

    recomputed = hash_password(password, salt=salt)
    return hmac.compare_digest(recomputed, encoded_hash)