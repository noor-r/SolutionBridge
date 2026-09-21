"""Unit tests for security, API key hashing, and credential masking."""

from app.core.security import generate_api_key, hash_api_key, mask_api_key, verify_api_key


def test_api_key_generation():
    raw_key, key_hash, masked_key = generate_api_key("production")
    assert raw_key.startswith("sb_live_")
    assert len(key_hash) == 64  # SHA-256 hex length
    assert "***" in masked_key
    assert masked_key.endswith(raw_key[-4:])


def test_api_key_verification():
    raw_key, key_hash, _ = generate_api_key("production")
    assert verify_api_key(raw_key, key_hash) is True
    assert verify_api_key("sb_live_invalid_fake_key", key_hash) is False
    assert verify_api_key("", key_hash) is False
    assert verify_api_key(raw_key, "") is False


def test_api_key_masking():
    masked = mask_api_key("sb_live_abcdef1234567890")
    assert "***" in masked
    assert not masked.startswith("sb_live_abcdef1234567890")
    assert masked.endswith("7890")
