import asyncio
import json
from decimal import Decimal

from src.infrastructure.cache.redis_adapter import RedisCacheFactory


async def seed_executive_data():
    cache = await RedisCacheFactory.criar_cache(host="valkey", port=6379)
    payload = {
        "total_sales": "35000.0000",
        "net_margin": "4375.0000",
        "tax_collected": "2400.0000",
        "by_station": [
            {"source": "Casa Caiada", "total_sales": "12000.0000", "net_margin": "1500.0000", "tax_collected": "800.0000"},
            {"source": "VIP", "total_sales": "13000.0000", "net_margin": "1625.0000", "tax_collected": "800.0000"},
            {"source": "Real", "total_sales": "10000.0000", "net_margin": "1250.0000", "tax_collected": "800.0000"},
        ],
    }
    await cache.set("executive:metrics:aggregate:v1", payload)
    await cache.disconnect()
    print("Seeded executive metrics into cache")


if __name__ == "__main__":
    asyncio.run(seed_executive_data())
