"""Seed demo data for Logos Executive Vision.

This script seeds Redis (Valkey-compatible) with realistic metrics and rateio
distributions used by the executive dashboard demo.
"""
import os
import asyncio
import json
import random
import time
from datetime import datetime

import redis.asyncio as aioredis

from src.infrastructure.finance.rateio_engine import compute_rateio

REDIS_URL = os.environ.get('REDIS_URL', 'redis://localhost:6379/0')


async def seed(group_name: str = 'Grupo Lisboa'):
    r = aioredis.from_url(REDIS_URL)
    try:
        # seed metrics stream (push per-station metrics)
        metrics = {
            'rps': round(random.uniform(20_000, 60_000) / 1000.0, 4),
            'growth': f"{round(random.uniform(2.3, 18.5),4)}%",
            'users': random.randint(800, 2500),
        }
        await r.set('executive:metrics:latest', json.dumps(metrics))

        # seed rateio distribution for three centers
        shares = {'Center A': 45250.04532, 'Center B': 35750.12345, 'Center C': 19000.28483}
        rateio = await compute_rateio(shares)
        await r.set(f'rateio:{group_name}', json.dumps(rateio))

        # seed audit lines
        audits = []
        now = int(time.time() * 1000)
        for i in range(200):
            entry = {
                'timestamp': now - i * 1000,
                'actor': f'user{random.randint(1,20)}@company.com',
                'action': random.choice(['login_success', 'login_failed', 'data_accessed', 'rateio_view']),
                'ip': f'192.168.{random.randint(0,255)}.{random.randint(1,254)}',
                'checksum': f"{random.getrandbits(128):032x}",
            }
            audits.append(entry)

        await r.set(f'audit:{group_name}:recent', json.dumps(audits))

        print('Seeded Redis keys: executive:metrics:latest, rateio:%s, audit:%s:recent' % (group_name, group_name))
    finally:
        await r.close()


def main():
    import argparse
    p = argparse.ArgumentParser()
    p.add_argument('--group', default='Grupo Lisboa')
    args = p.parse_args()
    asyncio.run(seed(args.group))


if __name__ == '__main__':
    main()
