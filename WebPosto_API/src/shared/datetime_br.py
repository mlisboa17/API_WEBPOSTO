"""Datas no fuso do posto — Recife/PE (America/Recife, UTC-3)."""

from __future__ import annotations

from datetime import date, datetime
from zoneinfo import ZoneInfo

RECIFE_TZ = ZoneInfo("America/Recife")


def hoje_recife() -> date:
    return datetime.now(RECIFE_TZ).date()


def agora_recife_iso() -> str:
    return datetime.now(RECIFE_TZ).isoformat(timespec="seconds")
