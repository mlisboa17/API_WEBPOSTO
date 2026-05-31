from __future__ import annotations

import json
from typing import Any

from src.infrastructure.cache.valkey_config import ValkeyCache as BaseValkeyCache


class ValkeyMatrixCache(BaseValkeyCache):
    """Cache strategy for UF/CNAE tax matrices with hit-ratio visibility."""

    def build_key(self, uf: str, cnae: str, ncm: str | None) -> str:
        return f"matrix:{uf}:{cnae}:{ncm or 'SEM_NCM'}"

    async def get_matrix(self, uf: str, cnae: str, ncm: str | None) -> dict[str, Any] | None:
        raw = await self.get(self.build_key(uf, cnae, ncm))
        if raw is None:
            return None
        if isinstance(raw, str):
            return json.loads(raw)
        return raw

    async def set_matrix(self, uf: str, cnae: str, ncm: str | None, payload: dict[str, Any], ttl: int = 60 * 60 * 24) -> bool:
        return await self.set(self.build_key(uf, cnae, ncm), json.dumps(payload), ttl=ttl)


__all__ = ["ValkeyMatrixCache"]
