import time
from src.services.analytics_cache import build_cache_key, get_cache, set_cache, clear_cache


def test_build_cache_key_various_inputs():
    # As dictionary
    dct = {"data_inicial": "2026-06-01", "data_final": "2026-06-30", "empresa_codigo": 5256, "filial": "POSTO BR SHOPPING"}
    key1 = build_cache_key("dre", dct)
    assert key1 == "dre:2026-06-01:2026-06-30:5256:POSTO BR SHOPPING"

    # Some fields omitted
    dct2 = {"dataInicial": "2026-06-01", "dataFinal": "2026-06-30"}
    key2 = build_cache_key("kpis", dct2)
    assert key2 == "kpis:2026-06-01:2026-06-30::"

    # As object / dataclass dummy
    class FiltersDummy:
        data_inicial = "2026-06-05"
        data_final = "2026-06-05"
        empresa_codigo = 11495
        filial = "POSTO VIP"

    key3 = build_cache_key("data-quality", FiltersDummy())
    assert key3 == "data-quality:2026-06-05:2026-06-05:11495:POSTO VIP"


def test_cache_get_set_expiry():
    clear_cache()
    key = "test:key:123"
    assert get_cache(key) is None

    # Set value
    set_cache(key, {"score": 98.7}, ttl=0.1)
    assert get_cache(key) == {"score": 98.7}

    # Wait for expiration
    time.sleep(0.15)
    assert get_cache(key) is None


def test_clear_cache():
    clear_cache()
    set_cache("kpis:2026-06-01", "val1", ttl=60)
    set_cache("dre:2026-06-01", "val2", ttl=60)

    # Clear matching pattern
    clear_cache("dre")
    assert get_cache("dre:2026-06-01") is None
    assert get_cache("kpis:2026-06-01") == "val1"

    # Clear all
    clear_cache()
    assert get_cache("kpis:2026-06-01") is None
