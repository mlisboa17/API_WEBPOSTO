from datetime import datetime, timedelta
from hashlib import md5
from typing import Any, Dict, Optional


class CacheManager:
    """In-memory TTL cache keyed by posto_id and data_consulta."""

    def __init__(self, ttl_minutes: int = 5):
        self.ttl = ttl_minutes
        self.store: Dict[str, Dict[str, Any]] = {}

    def _generate_key(self, posto_id: str, data_consulta: datetime) -> str:
        """Generate deterministic key for posto/date pair."""
        key_str = f"{posto_id}_{data_consulta.date().isoformat()}"
        return md5(key_str.encode()).hexdigest()

    @staticmethod
    def _generate_generic_key(namespace: str, identifier: str) -> str:
        key_str = f"{namespace}_{identifier}"
        return md5(key_str.encode()).hexdigest()

    def _is_expired(self, created_at: datetime) -> bool:
        return datetime.utcnow() > created_at + timedelta(minutes=self.ttl)

    def get(self, posto_id: str, data_consulta: datetime) -> Optional[Any]:
        self.cleanup_expired()
        key = self._generate_key(posto_id, data_consulta)
        entry = self.store.get(key)
        if not entry:
            return None
        if self._is_expired(entry["created_at"]):
            self.store.pop(key, None)
            return None
        return entry["value"]

    def set(self, posto_id: str, data_consulta: datetime, value: Any) -> None:
        key = self._generate_key(posto_id, data_consulta)
        self.store[key] = {
            "value": value,
            "created_at": datetime.utcnow(),
        }

    def get_by_key(self, namespace: str, identifier: str) -> Optional[Any]:
        self.cleanup_expired()
        key = self._generate_generic_key(namespace, identifier)
        entry = self.store.get(key)
        if not entry:
            return None
        if self._is_expired(entry["created_at"]):
            self.store.pop(key, None)
            return None
        return entry["value"]

    def set_by_key(self, namespace: str, identifier: str, value: Any) -> None:
        key = self._generate_generic_key(namespace, identifier)
        self.store[key] = {
            "value": value,
            "created_at": datetime.utcnow(),
        }

    def invalidate(self, namespace: str, identifier: Optional[str] = None) -> int:
        """Invalidate one key or all keys under a namespace."""
        if identifier is not None:
            key = self._generate_generic_key(namespace, identifier)
            return 1 if self.store.pop(key, None) is not None else 0

        # Keys are hashed, so namespace-wide invalidation cannot filter by prefix.
        deleted = len(self.store)
        self.store.clear()
        return deleted

    def clear(self) -> None:
        """Clear full cache."""
        self.store.clear()

    def cleanup_expired(self) -> int:
        now = datetime.utcnow()
        keys_to_delete = [
            key
            for key, entry in self.store.items()
            if now > entry["created_at"] + timedelta(minutes=self.ttl)
        ]
        for key in keys_to_delete:
            self.store.pop(key, None)
        return len(keys_to_delete)


cache_manager = CacheManager(ttl_minutes=5)
