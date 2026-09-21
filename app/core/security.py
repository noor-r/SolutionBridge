"""Security utilities: API key generation, hashing, masking, and verification."""

import hashlib
import hmac
import secrets
from typing import Tuple
from app.core.config import settings


def hash_api_key(raw_key: str) -> str:
    """Hash an API key using HMAC-SHA256 with the application secret key."""
    return hmac.new(
        settings.SECRET_KEY.encode("utf-8"),
        raw_key.strip().encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()


def mask_api_key(raw_or_masked_key: str) -> str:
    """Return a masked representation of an API key (e.g., sb_live_***a8f2)."""
    if not raw_or_masked_key:
        return "sb_live_***invalid"
    if "***" in raw_or_masked_key:
        return raw_or_masked_key
    if len(raw_or_masked_key) <= 8:
        return "***" + raw_or_masked_key[-4:]
    prefix = raw_or_masked_key[:8]
    suffix = raw_or_masked_key[-4:]
    return f"{prefix}***{suffix}"


def generate_api_key(environment: str = "production") -> Tuple[str, str, str]:
    """
    Generate a new API key pair.
    Returns:
        (raw_api_key, api_key_hash, masked_api_key)
    """
    env_tag = "live" if environment.lower() in ("production", "live") else "test"
    random_token = secrets.token_hex(16)
    raw_key = f"sb_{env_tag}_{random_token}"
    key_hash = hash_api_key(raw_key)
    masked_key = mask_api_key(raw_key)
    return raw_key, key_hash, masked_key


def verify_api_key(raw_key: str, expected_hash: str) -> bool:
    """Safely verify an incoming API key against stored hash using constant-time comparison."""
    if not raw_key or not expected_hash:
        return False
    computed_hash = hash_api_key(raw_key)
    return hmac.compare_digest(computed_hash, expected_hash)
