"""Persistencia local atomica de propostas. Nao sobrescreve historico."""

from __future__ import annotations

import json
import os
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .schemas import CostUpdateProposal


class CostProposalStore:
    def __init__(self, root: Path) -> None:
        self.root = Path(root)
        self.history = self.root / "history"
        self.index_path = self.root / "proposal_index.json"
        self._index = self.load_index()

    def load_index(self) -> dict[str, Any]:
        if not self.index_path.is_file():
            return {"by_hash": {}, "by_ean": {}}
        return json.loads(self.index_path.read_text(encoding="utf-8"))

    def flush(self) -> None:
        self._index["updated_at"] = datetime.now(timezone.utc).isoformat()
        self._atomic_write(self.index_path, self._index)

    def get_by_hash(self, proposal_hash: str) -> dict[str, Any] | None:
        path = self.history / f"{proposal_hash}.json"
        if not path.is_file():
            return None
        return json.loads(path.read_text(encoding="utf-8"))

    def latest_for_ean(self, ean: str) -> dict[str, Any] | None:
        hashes = self._index.get("by_ean", {}).get(ean) or []
        if not hashes:
            return None
        return self.get_by_hash(hashes[-1])

    def persist(self, proposal: CostUpdateProposal) -> dict[str, Any]:
        existing = self.get_by_hash(proposal.proposal_hash)
        if existing:
            return {"created": False, "proposal": existing}
        payload = json.loads(proposal.model_dump_json())
        self.history.mkdir(parents=True, exist_ok=True)
        path = self.history / f"{proposal.proposal_hash}.json"
        self._atomic_write(path, payload)
        self._index.setdefault("by_hash", {})[proposal.proposal_hash] = str(path)
        versions = self._index.setdefault("by_ean", {}).setdefault(proposal.ean, [])
        if proposal.proposal_hash not in versions:
            versions.append(proposal.proposal_hash)
        return {"created": True, "proposal": payload}

    def mark_superseded(self, proposal_hash: str) -> None:
        payload = self.get_by_hash(proposal_hash)
        if not payload or payload.get("lifecycle") == "SUPERSEDED":
            return
        payload["lifecycle"] = "SUPERSEDED"
        path = self.history / f"{proposal_hash}.json"
        self._atomic_write(path, payload)

    def _atomic_write(self, path: Path, payload: dict[str, Any]) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        fd, tmp = tempfile.mkstemp(prefix=path.name, dir=path.parent)
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as handle:
                json.dump(payload, handle, ensure_ascii=False, indent=2, default=str)
            try:
                os.replace(tmp, path)
            except PermissionError:
                path.write_text(Path(tmp).read_text(encoding="utf-8"), encoding="utf-8")
                os.remove(tmp)
        except Exception:
            if os.path.exists(tmp):
                os.remove(tmp)
            raise
