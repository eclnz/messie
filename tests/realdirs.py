"""Discover suitable real directories for tests."""

from __future__ import annotations

import os
import sysconfig
from pathlib import Path

#: Minimum sample size for a useful rate.
MINIMUM_FOLDERS = 25
DEFAULT_LIMIT = 90

_REPO_ROOT = Path(__file__).resolve().parent.parent


def real_roots() -> list[Path]:
    """Return available Python and repository trees."""
    roots = []
    for key in ("stdlib", "purelib", "platlib"):
        path = sysconfig.get_paths().get(key)
        if path and Path(path).is_dir():
            roots.append(Path(path))
    if _REPO_ROOT.is_dir():
        roots.append(_REPO_ROOT)
    return roots


def coherent_folders(limit: int = DEFAULT_LIMIT) -> list[Path]:
    """Return deterministic real folders with enough files to judge."""
    found: list[Path] = []
    for root in real_roots():
        for dirpath, dirnames, filenames in os.walk(root):
            dirnames[:] = sorted(
                d for d in dirnames if not d.startswith((".", "__pycache__", "test"))
            )
            if len(filenames) >= 8:
                found.append(Path(dirpath))
            if len(found) >= limit:
                break
        if len(found) >= limit:
            break
    return sorted(set(found))[:limit]
