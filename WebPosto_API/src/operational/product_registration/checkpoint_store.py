"""Persistência: checkpoint, lock, pause/resume — FASE 4."""

from __future__ import annotations

import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Any

from .schemas import ExecutionState

logger = logging.getLogger(__name__)


class CheckpointStore:
    """Gerencia checkpoint JSON e lock para execução."""

    def __init__(self, checkpoint_dir: Path | str = "data/product_registration/executions"):
        self.checkpoint_dir = Path(checkpoint_dir)
        self.checkpoint_dir.mkdir(parents=True, exist_ok=True)

    def create_execution_id(self) -> str:
        """Gera execution ID único."""
        return datetime.now().strftime("%Y%m%d_%H%M%S_%f")

    def get_checkpoint_path(self, execution_id: str) -> Path:
        """Retorna caminho do checkpoint JSON."""
        return self.checkpoint_dir / execution_id / "checkpoint.json"

    def get_lock_path(self, execution_id: str) -> Path:
        """Retorna caminho do lock file."""
        return self.checkpoint_dir / execution_id / ".lock"

    def create_lock(self, execution_id: str) -> bool:
        """Cria lock file. Retorna True se criou, False se já existe."""
        lock_path = self.get_lock_path(execution_id)
        if lock_path.exists():
            logger.warning(f"[LOCK_EXISTS] execution_id={execution_id}")
            return False
        
        lock_path.parent.mkdir(parents=True, exist_ok=True)
        lock_path.write_text(str(datetime.now().isoformat()))
        logger.info(f"[LOCK_CREATED] execution_id={execution_id}")
        return True

    def release_lock(self, execution_id: str) -> None:
        """Remove lock file."""
        lock_path = self.get_lock_path(execution_id)
        if lock_path.exists():
            lock_path.unlink()
            logger.info(f"[LOCK_RELEASED] execution_id={execution_id}")

    def save_checkpoint(self, state: ExecutionState) -> None:
        """Salva checkpoint JSON."""
        checkpoint_path = self.get_checkpoint_path(state.execution_id)
        checkpoint_path.parent.mkdir(parents=True, exist_ok=True)

        checkpoint_data = {
            "execution_id": state.execution_id,
            "started_at": state.started_at.isoformat(),
            "checkpoint_index": state.checkpoint_index,
            "products_processed": state.products_processed,
            "success_count": state.success_count,
            "blocked_count": state.blocked_count,
            "review_required_count": state.review_required_count,
            "failed_count": state.failed_count,
            "paused_at": state.paused_at.isoformat() if state.paused_at else None,
            "paused_reason": state.paused_reason,
            "last_result": state.last_result,
            "api_rejection_reason": state.api_rejection_reason,
        }

        checkpoint_path.write_text(json.dumps(checkpoint_data, indent=2, ensure_ascii=False))
        logger.info(f"[CHECKPOINT_SAVED] execution_id={state.execution_id}, index={state.checkpoint_index}")

    def load_checkpoint(self, execution_id: str) -> ExecutionState | None:
        """Carrega checkpoint JSON."""
        checkpoint_path = self.get_checkpoint_path(execution_id)
        if not checkpoint_path.exists():
            logger.warning(f"[CHECKPOINT_NOT_FOUND] execution_id={execution_id}")
            return None

        try:
            data = json.loads(checkpoint_path.read_text())
            return ExecutionState(
                execution_id=data["execution_id"],
                started_at=datetime.fromisoformat(data["started_at"]),
                checkpoint_index=data.get("checkpoint_index", 0),
                products_processed=data.get("products_processed", 0),
                success_count=data.get("success_count", 0),
                blocked_count=data.get("blocked_count", 0),
                review_required_count=data.get("review_required_count", 0),
                failed_count=data.get("failed_count", 0),
                paused_at=datetime.fromisoformat(data["paused_at"]) if data.get("paused_at") else None,
                paused_reason=data.get("paused_reason"),
                last_result=data.get("last_result"),
                api_rejection_reason=data.get("api_rejection_reason"),
            )
        except Exception as e:
            logger.error(f"[CHECKPOINT_LOAD_ERROR] execution_id={execution_id}: {e}")
            return None
