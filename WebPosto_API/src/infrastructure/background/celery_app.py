"""
App Celery — broker Redis/Valkey. Opcional: pip install celery
"""

from __future__ import annotations

import os

try:
    from celery import Celery

    broker = os.getenv("CELERY_BROKER_URL") or os.getenv("REDIS_URL", "redis://localhost:6379/1")
    result = os.getenv("CELERY_RESULT_BACKEND") or broker

    celery_app = Celery(
        "webposto_worker",
        broker=broker,
        backend=result,
        include=["src.infrastructure.background.tasks"],
    )
    celery_app.conf.update(
        task_serializer="json",
        accept_content=["json"],
        result_serializer="json",
        timezone="America/Sao_Paulo",
        enable_utc=True,
        task_track_started=True,
        worker_prefetch_multiplier=1,
    )
except ImportError:
    celery_app = None  # type: ignore
