"Walking a tree and judging every folder in it."

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

import numpy as np

from messie.config import DEFAULT_SETTINGS, Settings
from messie.embed import Embedder, get_embedder
from messie.engine import analyze, profile, profile_of, vectorize
from messie.result import DirAnalysis, VectorRecord
from messie.scan import read_dir, walk

__all__ = [
    "DirAnalysis",
    "Progress",
    "ProgressFn",
    "VectorRecord",
    "analyze_dir",
    "analyze_tree",
]


@dataclass(frozen=True)
class Progress:
    "Where a tree walk has got to."
    stage: str
    done: int
    total: int
    path: Path | None = None
    files: int = 0


ProgressFn = Callable[[Progress], None]


def analyze_dir(
    path: Path,
    settings: Settings = DEFAULT_SETTINGS,
    embedder: Embedder | None = None,
) -> DirAnalysis:
    "Judge a single folder, ignoring what is in its subfolders."
    embedder = embedder or get_embedder()
    root = Path(path).expanduser().resolve()
    contents = read_dir(root, settings)

    profiles = {}
    for sub_contents in walk(root, settings):
        if sub_contents.path.resolve() == root:
            continue
        if len(sub_contents.files) >= settings.meaningful_cluster_min:
            profiles[sub_contents.path.resolve()] = profile(
                sub_contents.files, embedder=embedder, settings=settings
            )
    return analyze(contents, embedder=embedder, settings=settings, child_profiles=profiles)


def analyze_tree(
    root: Path | str,
    settings: Settings = DEFAULT_SETTINGS,
    embedder: Embedder | None = None,
    progress: ProgressFn | None = None,
) -> list[DirAnalysis]:
    """Judge every folder at or under ``root``, worst first."""
    embedder = embedder or get_embedder()
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
        records[key] = vectorize(contents.files, embedder=embedder, settings=settings)
        profiles[key] = profile_of(records[key].vectors)

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
            analyze(
                contents,
                embedder=embedder,
                settings=settings,
                child_profiles=descendants.get(key, {}),
                precomputed=records.get(key),
            )
        )

    results.sort(key=lambda a: (-a.score, str(a.path)))
    return results
