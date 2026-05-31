"""Buffer circular de logs recentes (dev/diagnóstico)."""

from __future__ import annotations

import logging
from collections import deque
from typing import Deque, List

_MAX = 200
_buffer: Deque[str] = deque(maxlen=_MAX)


class RingBufferHandler(logging.Handler):
    def emit(self, record: logging.LogRecord) -> None:
        try:
            _buffer.append(self.format(record))
        except Exception:
            pass


_handler_installed = False


def install_log_buffer() -> None:
    global _handler_installed
    if _handler_installed:
        return
    h = RingBufferHandler()
    h.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(name)s — %(message)s"))
    logging.getLogger().addHandler(h)
    _handler_installed = True


def recent_logs(limit: int = 50) -> List[str]:
    n = max(1, min(limit, _MAX))
    return list(_buffer)[-n:]
