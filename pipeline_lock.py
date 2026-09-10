"""Cross-platform, fail-closed lock for a full portfolio pipeline run."""

from __future__ import annotations

import json
import os
import socket
import time
from pathlib import Path


class PipelineAlreadyRunning(RuntimeError):
    """Raised when another process owns the pipeline lock."""


class PipelineLock:
    """Own a lock file for the lifetime of a scheduled pipeline execution.

    ``O_CREAT | O_EXCL`` is atomic on local disks and GitHub runners. A stale
    lock is never removed automatically: uncertain ownership must stop trading
    and be investigated rather than guessed away.
    """

    def __init__(self, directory: str | os.PathLike[str], name: str = ".pipeline.lock"):
        self.path = Path(directory).resolve() / name
        self._owned = False

    def acquire(self) -> None:
        payload = {
            "pid": os.getpid(),
            "host": socket.gethostname(),
            "started_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        }
        try:
            fd = os.open(self.path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
        except FileExistsError as exc:
            try:
                owner = self.path.read_text(encoding="utf-8").strip()
            except OSError:
                owner = "unreadable lock metadata"
            raise PipelineAlreadyRunning(
                f"Pipeline lock already exists at {self.path}; refusing overlapping run. Owner: {owner}"
            ) from exc
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            json.dump(payload, handle, sort_keys=True)
            handle.write("\n")
        self._owned = True

    def release(self) -> None:
        if self._owned:
            try:
                self.path.unlink()
            except FileNotFoundError:
                pass
            self._owned = False

    def __enter__(self) -> "PipelineLock":
        self.acquire()
        return self

    def __exit__(self, exc_type, exc_value, traceback) -> None:
        self.release()
