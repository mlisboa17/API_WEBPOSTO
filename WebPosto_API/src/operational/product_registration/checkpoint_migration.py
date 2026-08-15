"""Leitura de checkpoints antigos sem reescreve-los."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .versions import CHECKPOINT_LEGACY_SCHEMA_VERSION, CHECKPOINT_SCHEMA_VERSION


def detect_checkpoint_schema(payload: Any) -> str:
    """Identifica o formato sem alterar o arquivo."""
    if isinstance(payload, dict) and payload.get("execution_id") and "checkpoint_index" in payload:
        return CHECKPOINT_LEGACY_SCHEMA_VERSION
    if isinstance(payload, dict):
        return CHECKPOINT_SCHEMA_VERSION
    raise ValueError("checkpoint em formato desconhecido")


def read_checkpoint(path: Path) -> dict[str, Any]:
    """Carrega checkpoint v2 (EAN -> registro) ou v1 (ExecutionState) como dict."""
    if not path.is_file():
        return {}
    payload = json.loads(path.read_text(encoding="utf-8"))
    schema = detect_checkpoint_schema(payload)
    if schema == CHECKPOINT_LEGACY_SCHEMA_VERSION:
        return {
            "_legacy": True,
            "_schema": schema,
            "execution_id": payload.get("execution_id"),
            "checkpoint_index": payload.get("checkpoint_index"),
            "last_result": payload.get("last_result"),
        }
    return payload
