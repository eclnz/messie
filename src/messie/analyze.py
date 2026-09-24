"""Walking a tree and judging every folder in it.

The judging itself lives in :mod:`messie.engine`; what is here is the
traversal, and the bookkeeping that lets a folder be compared against the
folders below it without reading anything twice.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

import numpy as np

from messie.cache import Cache
from messie.config import DEFAULT_SETTINGS, Settings
from messie.embed import Embedder
from messie.engine import Engine
from messie.result import DirAnalysis, VectorRecord
from messie.scan import read_dir, walk

__all__ = [
    "DirAnalysis",
    "Engine",
    "Progress",
    "ProgressFn",
    "VectorRecord",
    "analyze_dir",
    "analyze_tree",
]


@dataclass(frozen=True)
class Progress:
    """Where a tree walk has got to.

    Reported rather than printed: a library that writes to a terminal is a
    library you cannot call from anything else. ``--verbose`` supplies a
    callback that draws it; everything else passes nothing and pays nothing.
    """

    #: ``scan`` while finding folders, ``read`` while extracting and embedding
    #: them, ``judge`` while running the signals.
    stage: str
    done: int
    total: int
    #: The folder being worked on, which is the thing worth naming: when a file
    #: makes an extractor or a model throw, this is what says which one.
    path: Path | None = None
    #: Files in that folder, where the stage knows.
    files: int = 0


ProgressFn = Callable[[Progress], None]


def analyze_dir(
    path: Path | str,
    settings: Settings = DEFAULT_SETTINGS,
    embedder: Embedder | None = None,
    cache: Cache | None = None,
) -> DirAnalysis:
    """Judge a single folder, ignoring what is in its subfolders.

    Folders below it are still read, but only to build a profile of each, so
    that loose files here can be recognised as resembling one of them.
    """
    engine = Engine(settings, embedder, cache)
    root = Path(path).expanduser().resolve()
    contents = read_dir(root, settings)

    profiles = {}
    for sub_contents in walk(root, settings):
        if sub_contents.path.resolve() == root:
            continue
        if len(sub_contents.files) >= settings.meaningful_cluster_min:
            profiles[sub_contents.path.resolve()] = engine.profile(sub_contents.files)
    return engine.analyze(contents, profiles)


def analyze_tree(
    root: Path | str,
    settings: Settings = DEFAULT_SETTINGS,
    embedder: Embedder | None = None,
    cache: Cache | None = None,
    progress: ProgressFn | None = None,
) -> list[DirAnalysis]:
    """Judge every folder at or under ``root``, worst first."""
    engine = Engine(settings, embedder, cache)
    report: ProgressFn = progress or (lambda _: None)

    all_contents = walk(Path(root), settings)
    total = len(all_contents)
    report(Progress("scan", total, total, Path(root)))
    by_path = {c.path.resolve(): c for c in all_contents}

    # Vectorise each folder once. The result serves both that folder's own
    # analysis and its parent's view of it as a subfolder.
    records: dict[Path, VectorRecord] = {}
    profiles: dict[Path, np.ndarray] = {}
    for done, contents in enumerate(all_contents, start=1):
        report(Progress("read", done, total, contents.path, len(contents.files)))
        if len(contents.files) < settings.meaningful_cluster_min:
            continue
        key = contents.path.resolve()
        records[key] = engine.vectorize(contents.files)
        profiles[key] = engine.profile_of(records[key].vectors)

    # Every folder underneath, not just the immediate children. People file
    # things away several levels down — ./Archive/2023/Taxes — and loose
    # paperwork upstairs resembles that folder just as much for being deep.
    #
    # Built by walking each folder *up* to its ancestors, rather than by asking
    # every folder whether every other folder sits beneath it. The second reads
    # more naturally and is quadratic: 1600 folders spent 13s comparing paths
    # and found nothing, because the answer for almost every pair is no. A path
    # has a handful of ancestors and a dict lookup settles each one, so this is
    # linear in the tree and the cost disappears.
    descendants: dict[Path, dict[Path, np.ndarray]] = {}
    for other, profile in profiles.items():
        for ancestor in other.parents:
            if ancestor in by_path:
                descendants.setdefault(ancestor, {})[other] = profile

    results: list[DirAnalysis] = []
    for done, contents in enumerate(all_contents, start=1):
        report(Progress("judge", done, total, contents.path, len(contents.files)))
        key = contents.path.resolve()
        results.append(
            engine.analyze(contents, descendants.get(key, {}), records.get(key))
        )

    engine.cache.commit()
    results.sort(key=lambda a: (-a.score, str(a.path)))
    return results
