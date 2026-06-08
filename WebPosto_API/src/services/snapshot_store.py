from __future__ import annotations

import json
import re
from datetime import datetime
from pathlib import Path
from typing import Any


def safe_filename(key: str) -> str:
    return re.sub(r"[^a-zA-Z0-9._-]+", "_", key)


class SnapshotStore:
    """Armazenamento memória + disco com TTL configurável."""

    def __init__(self, output_dir: str | Path, ttl_seconds: float) -> None:
        self._output_dir = Path(output_dir)
        self._ttl_seconds = ttl_seconds
        self._memory: dict[str, dict[str, Any]] = {}

    @property
    def ttl_seconds(self) -> float:
        return self._ttl_seconds

    def _disk_path(self, key: str) -> Path:
        self._output_dir.mkdir(parents=True, exist_ok=True)
        return self._output_dir / f"{safe_filename(key)}.json"

    def is_expired(self, payload: dict[str, Any] | None) -> bool:
        if not payload:
            return True
        last_updated = payload.get("lastUpdated")
        if not last_updated:
            return True
        try:
            ts = datetime.fromisoformat(str(last_updated))
        except ValueError:
            return True
        age = (datetime.now() - ts).total_seconds()
        return age > self._ttl_seconds

    def load(self, key: str) -> dict[str, Any] | None:
        stored = self._memory.get(key)
        if stored is None:
            path = self._disk_path(key)
            if path.exists():
                try:
                    payload = json.loads(path.read_text(encoding="utf-8"))
                    if isinstance(payload, dict):
                        stored = payload
                except (OSError, json.JSONDecodeError):
                    stored = None
        if stored and not self.is_expired(stored):
            self._memory[key] = stored
            return stored
        self._memory.pop(key, None)
        return None

    def save(self, key: str, payload: dict[str, Any]) -> None:
        self._memory[key] = payload
        path = self._disk_path(key)
        path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")

    def delete(self, key: str) -> None:
        self._memory.pop(key, None)
        path = self._disk_path(key)
        if path.exists():
            path.unlink(missing_ok=True)
