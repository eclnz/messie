"""A local cache of extracted text and vectors.

Re-running messie on a large folder should not re-read and re-embed every file.
Entries are keyed by path, size and mtime, so an edited file is recomputed and
an untouched one is not.

The cache is an optimisation and nothing more: every failure here is swallowed
and the caller simply does the work again.
"""

from __future__ import annotations

import contextlib
import os
import sqlite3
import zlib
from pathlib import Path

import numpy as np

_SCHEMA = """
CREATE TABLE IF NOT EXISTS entries (
    key      TEXT PRIMARY KEY,
    dim      INTEGER NOT NULL,
    vector   BLOB    NOT NULL,
    excerpt  BLOB    NOT NULL
)
"""


def default_cache_path() -> Path:
    base = os.environ.get("XDG_CACHE_HOME")
    root = Path(base).expanduser() if base else Path.home() / ".cache"
    return root / "messie" / "content.sqlite"


class Cache:
    """Best-effort store. Construct with ``enabled=False`` to disable entirely."""

    def __init__(self, path: Path | None = None, *, enabled: bool = True) -> None:
        self.enabled = enabled
        self._conn: sqlite3.Connection | None = None
        if not enabled:
            return
        path = path or default_cache_path()
        try:
            path.parent.mkdir(parents=True, exist_ok=True)
            self._conn = sqlite3.connect(str(path))
            self._conn.execute(_SCHEMA)
            self._conn.commit()
        except (sqlite3.Error, OSError):
            self._conn = None
            self.enabled = False

    @staticmethod
    def key(backend: str, path: Path, size: int, mtime: float) -> str:
        return f"{backend}|{path}|{size}|{mtime:.3f}"

    def get(self, key: str) -> tuple[np.ndarray, str] | None:
        if not self._conn:
            return None
        try:
            row = self._conn.execute(
                "SELECT dim, vector, excerpt FROM entries WHERE key = ?", (key,)
            ).fetchone()
        except sqlite3.Error:
            return None
        if not row:
            return None
        dim, vector_blob, excerpt_blob = row
        try:
            vector = np.frombuffer(vector_blob, dtype=np.float32)
            if vector.size != dim:
                return None
            excerpt = zlib.decompress(excerpt_blob).decode("utf-8", errors="replace")
        except (ValueError, zlib.error):
            return None
        return vector.copy(), excerpt

    def put(self, key: str, vector: np.ndarray, excerpt: str) -> None:
        if not self._conn:
            return
        with contextlib.suppress(sqlite3.Error, ValueError):
            self._conn.execute(
                "INSERT OR REPLACE INTO entries (key, dim, vector, excerpt) VALUES (?, ?, ?, ?)",
                (
                    key,
                    int(vector.size),
                    np.ascontiguousarray(vector, dtype=np.float32).tobytes(),
                    zlib.compress(excerpt.encode("utf-8")),
                ),
            )

    def commit(self) -> None:
        if self._conn:
            with contextlib.suppress(sqlite3.Error):
                self._conn.commit()

    def close(self) -> None:
        self.commit()
        if self._conn:
            with contextlib.suppress(sqlite3.Error):
                self._conn.close()
            self._conn = None

    def __enter__(self) -> Cache:
        return self

    def __exit__(self, *exc) -> None:
        self.close()
