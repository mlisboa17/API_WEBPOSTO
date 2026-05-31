"""
Tarefas de background (Celery) — inventário e fechamento de caixa.
"""

from __future__ import annotations

import logging

logger = logging.getLogger(__name__)

try:
    from src.infrastructure.background.celery_app import celery_app
except ImportError:
    celery_app = None


def _task_decorator(name: str):
    if celery_app is not None:
        return celery_app.task(name=name)
    return lambda fn: fn


@_task_decorator("webposto.sync_inventory")
def sync_inventory(filial_codigo: int | None = None) -> dict:
    """Sincroniza estoque/produtos (stub — integra com SyncInventory use case)."""
    logger.info("sync_inventory filial=%s", filial_codigo)
    return {"ok": True, "task": "sync_inventory", "filial": filial_codigo}


@_task_decorator("webposto.process_box_closure")
def process_box_closure(data_inicial: str, data_final: str) -> dict:
    """Processa fechamento de caixa (stub — integra com ProcessBoxClosure)."""
    logger.info("process_box_closure %s → %s", data_inicial, data_final)
    return {"ok": True, "task": "process_box_closure", "periodo": [data_inicial, data_final]}
