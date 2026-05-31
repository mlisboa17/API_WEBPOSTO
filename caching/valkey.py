"""Compatibility wrapper for executive Adelaide Valkey strategies."""

from __future__ import annotations

import json
from hashlib import sha256
from typing import Any, Awaitable, Callable

from src.infrastructure.cache.valkey_config import ValkeyCache as BaseValkeyCache


class ValkeyTaxCache(BaseValkeyCache):
	def build_tax_key(self, *, uf: str, cnae: str, ncm: str, regime: str) -> str:
		raw_key = f"{uf.upper()}|{cnae}|{ncm}|{regime.upper()}"
		return f"tax:matrix:{sha256(raw_key.encode('utf-8')).hexdigest()}"

	async def get_json(self, key: str) -> Any | None:
		raw = await self.get(key)
		if raw is None:
			return None
		return json.loads(raw)

	async def set_json(self, key: str, value: Any, ttl: int | None = None) -> bool:
		return await self.set(key, json.dumps(value, ensure_ascii=False, default=str), ttl=ttl)

	async def get_or_set_json(
		self,
		key: str,
		loader: Callable[[], Awaitable[Any]],
		ttl: int | None = None,
	) -> Any:
		cached = await self.get_json(key)
		if cached is not None:
			return cached
		value = await loader()
		if value is not None:
			await self.set_json(key, value, ttl=ttl)
		return value

	def stats(self) -> dict[str, float | int | bool]:
		ratio = self.hit_ratio()
		return {
			"hits": self.hits,
			"misses": self.misses,
			"hit_ratio": ratio,
			"target_met": ratio >= 0.95,
		}


ValkeyCache = ValkeyTaxCache

__all__ = ["ValkeyCache", "ValkeyTaxCache"]
