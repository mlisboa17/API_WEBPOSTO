"""Seed station transactional data (sales/items) into Redis for demo and optionally Postgres.

Usage:
    python scripts/seed_station_data.py --items 5000 --station "Posto Casa Caiada"
"""
import os
import asyncio
import random
import json
import time
from datetime import datetime, timedelta

import redis.asyncio as aioredis

REDIS_URL = os.environ.get('REDIS_URL', 'redis://localhost:6379/0')


async def seed(items: int, station: str):
    r = aioredis.from_url(REDIS_URL)
    try:
        now = datetime.utcnow()
        sales = []
        categories = ['Bebidas', 'Alimentos', 'Tabacaria', 'Conveniencia']
        for i in range(items):
            sku = f'P{random.randint(1000,9999)}'
            units = random.randint(1,5)
            price = round(random.uniform(1.0, 20.0), 4)
            cost = round(price * random.uniform(0.5, 0.9), 4)
            ts = int((now - timedelta(seconds=random.randint(0, 60*60*24*30))).timestamp() * 1000)
            record = {'sku': sku, 'units': units, 'price': price, 'cost': cost, 'category': random.choice(categories), 'timestamp': ts, 'station': station}
            sales.append(record)
            if len(sales) >= 500:
                await r.rpush(f'sales:{station}', *[json.dumps(s) for s in sales])
                sales = []
        if sales:
            await r.rpush(f'sales:{station}', *[json.dumps(s) for s in sales])
        print(f'Seeded {items} sales into Redis list sales:{station}')
    finally:
        await r.close()


def main():
    import argparse
    p = argparse.ArgumentParser()
    p.add_argument('--items', type=int, default=5000)
    p.add_argument('--station', default='DemoStation')
    args = p.parse_args()
    asyncio.run(seed(args.items, args.station))


if __name__ == '__main__':
    main()
