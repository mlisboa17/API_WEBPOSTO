"""DIR-01D — persistência JSON de ExecutiveReviewRequest."""

from __future__ import annotations

import json
import threading
from pathlib import Path
from typing import Any

from src.services.executive_review.models import (
    ACTIVE_STATUSES,
    ExecutiveReviewRequest,
    ReviewRequestType,
)

ROOT = Path(__file__).resolve().parents[3]
DEFAULT_STORE_PATH = ROOT / "snapshots" / "executive_review_requests" / "store.json"


class ExecutiveReviewStore:
    """Armazena solicitações em JSON — sobrevive a restart HTTP."""

    def __init__(self, store_path: str | Path | None = None) -> None:
        self._path = Path(store_path or DEFAULT_STORE_PATH)
        self._path.parent.mkdir(parents=True, exist_ok=True)
        self._lock = threading.Lock()
        if not self._path.exists():
            self._write({"requests": {}, "by_decision": {}})

    def _read(self) -> dict[str, Any]:
        if not self._path.exists():
            return {"requests": {}, "by_decision": {}}
        data = json.loads(self._path.read_text(encoding="utf-8"))
        return data if isinstance(data, dict) else {"requests": {}, "by_decision": {}}

    def _write(self, data: dict[str, Any]) -> None:
        self._path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")

    def save(self, request: ExecutiveReviewRequest) -> ExecutiveReviewRequest:
        with self._lock:
            data = self._read()
            requests = data.setdefault("requests", {})
            by_decision = data.setdefault("by_decision", {})
            requests[request.id] = request.model_dump(mode="json")
            ids = by_decision.setdefault(request.decision_id, [])
            if request.id not in ids:
                ids.append(request.id)
            self._write(data)
        return request

    def update(self, request_id: str, mutator) -> ExecutiveReviewRequest:
        """Read-modify-write atômico dentro do lock do store."""
        with self._lock:
            data = self._read()
            raw = (data.get("requests") or {}).get(request_id)
            if not raw:
                raise KeyError(request_id)
            request = ExecutiveReviewRequest.model_validate(raw)
            request = mutator(request)
            data.setdefault("requests", {})[request_id] = request.model_dump(mode="json")
            self._write(data)
            return request

    def get(self, request_id: str) -> ExecutiveReviewRequest | None:
        data = self._read()
        raw = (data.get("requests") or {}).get(request_id)
        if not raw:
            return None
        return ExecutiveReviewRequest.model_validate(raw)

    def list_by_decision(self, decision_id: str) -> list[ExecutiveReviewRequest]:
        data = self._read()
        ids = (data.get("by_decision") or {}).get(decision_id) or []
        requests_map = data.get("requests") or {}
        out: list[ExecutiveReviewRequest] = []
        for rid in ids:
            raw = requests_map.get(rid)
            if raw:
                out.append(ExecutiveReviewRequest.model_validate(raw))
        out.sort(key=lambda r: r.requested_at, reverse=True)
        return out

    def list_all(self) -> list[ExecutiveReviewRequest]:
        data = self._read()
        requests_map = data.get("requests") or {}
        out = [
            ExecutiveReviewRequest.model_validate(raw)
            for raw in requests_map.values()
            if isinstance(raw, dict)
        ]
        out.sort(key=lambda r: r.requested_at, reverse=True)
        return out

    def find_active(
        self,
        decision_id: str,
        request_type: ReviewRequestType,
    ) -> ExecutiveReviewRequest | None:
        for req in self.list_by_decision(decision_id):
            if req.request_type != request_type:
                continue
            if req.status in ACTIVE_STATUSES:
                return req
        return None

    def clear_all(self) -> None:
        """Apenas para testes."""
        with self._lock:
            self._write({"requests": {}, "by_decision": {}})
