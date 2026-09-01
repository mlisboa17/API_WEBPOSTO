"""EXEC-02/03 — persistência JSON de ExecutionRecord (sobrevive a restart HTTP).

Segue o mesmo padrão de src/services/executive_review/store.py: 1 arquivo JSON,
lock em memória, read-modify-write atômico. Chave primária: decision_id (1
ExecutionRecord por decisão, criado na primeira chamada de /execute).
"""

from __future__ import annotations

import json
import threading
from pathlib import Path
from typing import Any, Callable

from src.services.decision_execution.models import ExecutionRecord

ROOT = Path(__file__).resolve().parents[3]
DEFAULT_STORE_PATH = ROOT / "snapshots" / "decision_execution" / "store.json"


class ExecutionRecordStore:
    """Repository JSON para ExecutionRecord, compatível com ExecutionService(repository=...)."""

    def __init__(self, store_path: str | Path | None = None) -> None:
        self._path = Path(store_path or DEFAULT_STORE_PATH)
        self._path.parent.mkdir(parents=True, exist_ok=True)
        self._lock = threading.Lock()
        if not self._path.exists():
            self._write({"records": {}})

    def _read(self) -> dict[str, Any]:
        if not self._path.exists():
            return {"records": {}}
        data = json.loads(self._path.read_text(encoding="utf-8"))
        return data if isinstance(data, dict) else {"records": {}}

    def _write(self, data: dict[str, Any]) -> None:
        self._path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")

    def save(self, record: ExecutionRecord) -> ExecutionRecord:
        """Assinatura compatível com o `self.repository.save(record)` chamado internamente
        pelo ExecutionService — sempre indexado por decision_id (1:1)."""
        with self._lock:
            data = self._read()
            data.setdefault("records", {})[record.decision_id] = record.model_dump(mode="json")
            self._write(data)
        return record

    def get(self, decision_id: str) -> ExecutionRecord | None:
        data = self._read()
        raw = (data.get("records") or {}).get(decision_id)
        if not raw:
            return None
        return ExecutionRecord.model_validate(raw)

    def update(self, decision_id: str, mutator: Callable[[ExecutionRecord], ExecutionRecord]) -> ExecutionRecord:
        """Read-modify-write atômico dentro do lock do store."""
        with self._lock:
            data = self._read()
            raw = (data.get("records") or {}).get(decision_id)
            if not raw:
                raise KeyError(decision_id)
            record = ExecutionRecord.model_validate(raw)
            record = mutator(record)
            data.setdefault("records", {})[decision_id] = record.model_dump(mode="json")
            self._write(data)
            return record

    def list_all(self) -> list[ExecutionRecord]:
        data = self._read()
        return [ExecutionRecord.model_validate(raw) for raw in (data.get("records") or {}).values()]
