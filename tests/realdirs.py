"""Finding real directories on this machine to judge.

Every fixture in this repo was authored alongside the code it exercises, and
that is how a bad feature once passed: eight flavours of synthetic nonsense
written in the same hour as the eight checks that caught them. The filesystem
is the antidote — large, free, and arranged by nobody with messie in mind.

A package directory is coherent by construction: one project, one purpose. So
the share of them that reads as messy is a false-positive rate measured against
a sample the tool cannot have been fitted to.

Both ``tests/test_real_world.py`` and ``scripts/calibrate.py`` select their
folders from here, so the guard and the report are looking at the same thing.
"""

from __future__ import annotations

import os
import sysconfig
from pathlib import Path

#: Enough folders for a rate to mean anything.
MINIMUM_FOLDERS = 25
DEFAULT_LIMIT = 90

_REPO_ROOT = Path(__file__).resolve().parent.parent


def real_roots() -> list[Path]:
    """Trees that exist on any machine with Python installed, plus this repo."""
    roots = []
    for key in ("stdlib", "purelib", "platlib"):
        path = sysconfig.get_paths().get(key)
        if path and Path(path).is_dir():
            roots.append(Path(path))
    if _REPO_ROOT.is_dir():
        roots.append(_REPO_ROOT)
    return roots


def coherent_folders(limit: int = DEFAULT_LIMIT) -> list[Path]:
    """Real directories with enough files in them to be worth judging.

    Directories named like tests are skipped: a test-data folder is a grab bag
    on purpose and proves nothing either way. The walk is sorted so the same
    machine yields the same folders, and a rate is comparable between runs.
    """
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
