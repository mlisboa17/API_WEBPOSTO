"""F07.3 — cache/index corporativo de produtos."""
from __future__ import annotations

import json
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
DEFAULT_CACHE_PATH = ROOT / "snapshots" / "product_master_cache" / "index.json"


class ProductMasterCache:
    """Cache local por produtoCodigo + empresaCodigo."""

    def __init__(self, path: Path | None = None) -> None:
        self._path = path or DEFAULT_CACHE_PATH
        self._entries: dict[str, dict[str, Any]] = {}
        self.hits = 0
        self.misses = 0
        self.writes = 0
        self._load()

    @staticmethod
    def _key(produto_codigo: int, empresa_codigo: int) -> str:
        return f"{produto_codigo}:{empresa_codigo}"

    def _load(self) -> None:
        if not self._path.exists():
            return
        try:
            raw = json.loads(self._path.read_text(encoding="utf-8"))
            self._entries = raw.get("entries") or {}
        except (json.JSONDecodeError, OSError):
            self._entries = {}

    def save(self) -> None:
        self._path.parent.mkdir(parents=True, exist_ok=True)
        payload = {
            "version": "F07.3",
            "updatedAt": datetime.now(timezone.utc).isoformat(),
            "total": len(self._entries),
            "entries": self._entries,
        }
        self._path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")

    def get(self, produto_codigo: int, empresa_codigo: int) -> dict[str, Any] | None:
        entry = self._entries.get(self._key(produto_codigo, empresa_codigo))
        if entry:
            self.hits += 1
            entry["lastSeen"] = datetime.now(timezone.utc).isoformat()
            return entry
        self.misses += 1
        return None

    def put(
        self,
        produto_codigo: int,
        empresa_codigo: int,
        *,
        nome_produto: str,
        departamento: str,
        fonte: str,
        confidence: str = "MEDIA",
        extra: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        now = datetime.now(timezone.utc).isoformat()
        entry = {
            "produtoCodigo": produto_codigo,
            "empresaCodigo": empresa_codigo,
            "nomeProduto": nome_produto,
            "departamento": departamento,
            "fonte": fonte,
            "lastSeen": now,
            "confidence": confidence,
            **(extra or {}),
        }
        self._entries[self._key(produto_codigo, empresa_codigo)] = entry
        self.writes += 1
        return entry

    def stats(self) -> dict[str, Any]:
        total = self.hits + self.misses or 1
        return {
            "cacheHits": self.hits,
            "cacheMisses": self.misses,
            "cacheWrites": self.writes,
            "cacheHitRatePct": round(self.hits / total * 100, 2),
            "indexSize": len(self._entries),
            "cachePath": str(self._path),
        }

    def reset_stats(self) -> None:
        self.hits = 0
        self.misses = 0
        self.writes = 0

    def clear(self) -> None:
        self._entries = {}
        self.reset_stats()
        if self._path.exists():
            self._path.unlink(missing_ok=True)
