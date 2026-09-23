"""Walking a tree and judging every folder in it.

The judging itself lives in :mod:`messie.engine`; what is here is the
traversal, and the bookkeeping that lets a folder be compared against the
folders below it without reading anything twice.
"""

from __future__ import annotations

from pathlib import Path

import numpy as np

from messie.cache import Cache
from messie.config import DEFAULT_SETTINGS, Settings
from messie.embed import Embedder
from messie.engine import Engine
from messie.result import DirAnalysis, VectorRecord
from messie.scan import read_dir, walk

__all__ = ["DirAnalysis", "Engine", "VectorRecord", "analyze_dir", "analyze_tree"]


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
) -> list[DirAnalysis]:
    """Judge every folder at or under ``root``, worst first."""
    engine = Engine(settings, embedder, cache)
    all_contents = walk(Path(root), settings)
    by_path = {c.path.resolve(): c for c in all_contents}

    # Vectorise each folder once. The result serves both that folder's own
    # analysis and its parent's view of it as a subfolder.
    records: dict[Path, VectorRecord] = {}
    profiles: dict[Path, np.ndarray] = {}
    for contents in all_contents:
        if len(contents.files) < settings.meaningful_cluster_min:
            continue
        key = contents.path.resolve()
        records[key] = engine.vectorize(contents.files)
        profiles[key] = engine.profile_of(records[key].vectors)

    results: list[DirAnalysis] = []
    for contents in all_contents:
        key = contents.path.resolve()
        # Every folder underneath, not just the immediate children. People file
        # things away several levels down — ./Archive/2023/Taxes — and loose
        # paperwork upstairs resembles that folder just as much for being deep.
        child_profiles = {
            other: profile
            for other, profile in profiles.items()
            if other != key and other.is_relative_to(key) and other in by_path
        }
        results.append(engine.analyze(contents, child_profiles, records.get(key)))

    engine.cache.commit()
    results.sort(key=lambda a: (-a.score, str(a.path)))
    return results
