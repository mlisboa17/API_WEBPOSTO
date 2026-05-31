import asyncio
from typing import Iterable, Protocol, List
from fastapi import Depends


class ProductRepository(Protocol):
    async def list_products(self) -> Iterable[dict]:
        ...


async def _process_chunk(chunk: List[dict]):
    # placeholder for processing logic (call TaxEngine, persist audit)
    await asyncio.sleep(0)
    return len(chunk)


async def process_products(repo: ProductRepository = Depends()) -> dict:
    products = await repo.list_products()
    products = list(products)
    chunk_size = 500
    tasks = []
    for i in range(0, len(products), chunk_size):
        chunk = products[i : i + chunk_size]
        tasks.append(asyncio.create_task(_process_chunk(chunk)))

    results = await asyncio.gather(*tasks)
    return {"processed": sum(results), "chunks": len(results)}
