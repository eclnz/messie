"""Small persistent cache for evidence that is expensive to read from disk."""

from __future__ import annotations

import hashlib
import os
import sqlite3
import sys
import time
from pathlib import Path
from types import TracebackType

import numpy as np

from messie.config import Settings
from messie.scan import FileEntry

_SCHEMA_VERSION = 1
_EXTRACTION_VERSION = 3
_MAX_ROWS = 100_000
_MAX_EMBEDDINGS = 250_000


def _cache_dir() -> Path:
    override = os.environ.get("MESSIE_CACHE_DIR")
    if override:
        return Path(override).expanduser()
    if sys.platform == "darwin":
        return Path.home() / "Library" / "Caches" / "messie"
    if os.name == "nt":
        base = os.environ.get("LOCALAPPDATA")
        return Path(base) / "messie" if base else Path.home() / "AppData" / "Local" / "messie"
    base = os.environ.get("XDG_CACHE_HOME")
    return (Path(base).expanduser() if base else Path.home() / ".cache") / "messie"


def _settings_key(settings: Settings) -> str:
    return (
        f"{_EXTRACTION_VERSION}:{settings.text_excerpt_chars}:"
        f"{settings.max_read_bytes}:{settings.image_description_sample}"
    )


class EvidenceCache:
    """SQLite-backed extracted-text cache which degrades to a no-op on failure."""

    def __init__(self, settings: Settings) -> None:
        self._settings = _settings_key(settings)
        self._connection: sqlite3.Connection | None = None
        self._pending: dict[tuple[str, int, str, str], str] = {}
        self._pending_embeddings: dict[tuple[str, bytes], np.ndarray] = {}
        if os.environ.get("MESSIE_NO_CACHE"):
            return
        try:
            directory = _cache_dir()
            directory.mkdir(parents=True, exist_ok=True)
            connection = sqlite3.connect(directory / "evidence.sqlite3", timeout=0.25)
            connection.execute("PRAGMA journal_mode=WAL")
            connection.execute(f"PRAGMA user_version={_SCHEMA_VERSION}")
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS extracted (
                    path TEXT PRIMARY KEY,
                    size INTEGER NOT NULL,
                    mtime TEXT NOT NULL,
                    settings TEXT NOT NULL,
                    text TEXT NOT NULL,
                    accessed INTEGER NOT NULL
                )
                """
            )
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS embeddings (
                    model TEXT NOT NULL,
                    digest BLOB NOT NULL,
                    vector BLOB NOT NULL,
                    dimensions INTEGER NOT NULL,
                    accessed INTEGER NOT NULL,
                    PRIMARY KEY(model, digest)
                )
                """
            )
            self._connection = connection
        except (OSError, sqlite3.Error):
            self._connection = None

    def _key(self, entry: FileEntry) -> tuple[str, int, str, str]:
        return (str(entry.path.resolve()), entry.size, entry.mtime.hex(), self._settings)

    def get(self, entry: FileEntry) -> str | None:
        key = self._key(entry)
        if key in self._pending:
            return self._pending[key]
        if self._connection is None:
            return None
        try:
            row = self._connection.execute(
                "SELECT text FROM extracted WHERE path=? AND size=? AND mtime=? AND settings=?",
                key,
            ).fetchone()
            return row[0] if row is not None else None
        except sqlite3.Error:
            self._connection = None
            return None

    def put(self, entry: FileEntry, text: str) -> None:
        if self._connection is not None:
            self._pending[self._key(entry)] = text

    @staticmethod
    def _digest(text: str) -> bytes:
        return hashlib.sha256(text.encode("utf-8", "replace")).digest()

    def get_embeddings(self, model: str, texts: list[str]) -> dict[str, np.ndarray]:
        """Return cached vectors for the requested texts, keyed by exact input."""
        if self._connection is None or not texts:
            return {}
        by_digest = {self._digest(text): text for text in texts}
        found: dict[str, np.ndarray] = {}
        missing: list[bytes] = []
        for digest, text in by_digest.items():
            pending = self._pending_embeddings.get((model, digest))
            if pending is None:
                missing.append(digest)
            else:
                found[text] = pending
        try:
            for start in range(0, len(missing), 400):
                chunk = missing[start : start + 400]
                placeholders = ",".join("?" for _ in chunk)
                rows = self._connection.execute(
                    f"SELECT digest, vector, dimensions FROM embeddings "  # noqa: S608
                    f"WHERE model=? AND digest IN ({placeholders})",
                    (model, *chunk),
                )
                for digest, blob, dimensions in rows:
                    vector = np.frombuffer(blob, dtype=np.float32)
                    if vector.size == dimensions:
                        found[by_digest[digest]] = vector.copy()
        except sqlite3.Error:
            return {}
        return found

    def put_embeddings(
        self, model: str, texts: list[str], vectors: np.ndarray
    ) -> None:
        if self._connection is None:
            return
        for text, vector in zip(texts, vectors, strict=True):
            self._pending_embeddings[(model, self._digest(text))] = np.asarray(
                vector, dtype=np.float32
            ).copy()

    def close(self) -> None:
        connection = self._connection
        self._connection = None
        if connection is None:
            return
        try:
            now = int(time.time())
            connection.executemany(
                """
                INSERT INTO extracted(path, size, mtime, settings, text, accessed)
                VALUES (?, ?, ?, ?, ?, ?)
                ON CONFLICT(path) DO UPDATE SET
                    size=excluded.size,
                    mtime=excluded.mtime,
                    settings=excluded.settings,
                    text=excluded.text,
                    accessed=excluded.accessed
                """,
                ((*key, text, now) for key, text in self._pending.items()),
            )
            connection.executemany(
                """
                INSERT INTO embeddings(model, digest, vector, dimensions, accessed)
                VALUES (?, ?, ?, ?, ?)
                ON CONFLICT(model, digest) DO UPDATE SET
                    vector=excluded.vector,
                    dimensions=excluded.dimensions,
                    accessed=excluded.accessed
                """,
                (
                    (model, digest, vector.tobytes(), vector.size, now)
                    for (model, digest), vector in self._pending_embeddings.items()
                ),
            )
            excess = connection.execute(
                "SELECT max(count(*) - ?, 0) FROM extracted", (_MAX_ROWS,)
            ).fetchone()
            if excess and excess[0]:
                connection.execute(
                    "DELETE FROM extracted WHERE path IN "
                    "(SELECT path FROM extracted ORDER BY accessed LIMIT ?)",
                    (excess[0],),
                )
            excess = connection.execute(
                "SELECT max(count(*) - ?, 0) FROM embeddings", (_MAX_EMBEDDINGS,)
            ).fetchone()
            if excess and excess[0]:
                connection.execute(
                    "DELETE FROM embeddings WHERE (model, digest) IN "
                    "(SELECT model, digest FROM embeddings ORDER BY accessed LIMIT ?)",
                    (excess[0],),
                )
            connection.commit()
        except sqlite3.Error:
            pass
        finally:
            connection.close()
            self._pending.clear()
            self._pending_embeddings.clear()

    def __enter__(self) -> EvidenceCache:
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_value: BaseException | None,
        traceback: TracebackType | None,
    ) -> None:
        self.close()
