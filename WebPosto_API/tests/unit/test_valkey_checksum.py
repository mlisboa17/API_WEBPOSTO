"""Checksum SHA-256 no cache Valkey."""

from src.infrastructure.cache.valkey_manager import ValkeyManager


def test_cache_roundtrip_with_checksum():
    cache = ValkeyManager(url="redis://127.0.0.1:59999/0", default_ttl=5)
    cache._redis = None
    payload = {"galonagem": 123.45, "ok": True}
    cache.set_json("test:checksum", payload, ttl=10)
    got = cache.get_json("test:checksum")
    assert got == payload


def test_checksum_detects_tamper():
    cache = ValkeyManager(url="redis://127.0.0.1:59999/0")
    cache._memory["bad"] = (
        9999999999.0,
        '{"sha256":"deadbeef","data":{"x":1}}',
    )
    assert cache.get_json("bad") is None
