"""Trava simples entre processos para stores JSON com troca atômica."""

from __future__ import annotations

import os
import time
from pathlib import Path
from uuid import uuid4


class InterProcessFileLock:
    def __init__(
        self,
        target: str | Path,
        *,
        timeout_seconds: float = 10.0,
        stale_seconds: float = 60.0,
    ) -> None:
        target_path = Path(target)
        self._path = target_path.with_suffix(f"{target_path.suffix}.lock")
        self._timeout = timeout_seconds
        self._stale = stale_seconds
        self._token = f"{os.getpid()}:{uuid4()}"

    def __enter__(self) -> "InterProcessFileLock":
        self._path.parent.mkdir(parents=True, exist_ok=True)
        deadline = time.monotonic() + self._timeout
        while True:
            try:
                descriptor = os.open(
                    self._path,
                    os.O_CREAT | os.O_EXCL | os.O_WRONLY,
                )
                with os.fdopen(descriptor, "w", encoding="ascii") as handle:
                    handle.write(self._token)
                    handle.flush()
                    os.fsync(handle.fileno())
                return self
            except (FileExistsError, PermissionError):
                try:
                    age = time.time() - self._path.stat().st_mtime
                    if age > self._stale:
                        self._path.unlink(missing_ok=True)
                        continue
                except OSError:
                    # On Windows another process/thread may still be closing the
                    # lock file. Treat transient access denial as contention.
                    pass
                if time.monotonic() >= deadline:
                    raise TimeoutError(f"LOCK_TIMEOUT:{self._path.name}")
                time.sleep(0.02)

    def __exit__(self, exc_type, exc, traceback) -> None:
        try:
            if self._path.read_text(encoding="ascii") == self._token:
                self._path.unlink(missing_ok=True)
        except OSError:
            pass
