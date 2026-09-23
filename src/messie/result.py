"""What an analysis produced: the verdict on one folder, and the workings.

This is a data carrier, not a place for logic. The conveniences on
``DirAnalysis`` exist because nine signals would otherwise each re-derive the
same things — which cluster is meaningful, what a group is called, when its
files arrived — from the same raw arrays.
"""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass, field
from pathlib import Path
from typing import NamedTuple

import numpy as np

from messie.cluster import Clustering
from messie.config import Settings, Thresholds
from messie.label import format_label
from messie.scan import FileEntry
from messie.score import Verdict
from messie.signals import Finding


class VectorRecord(NamedTuple):
    """What vectorising one folder produced."""

    texts: list[str]
    vectors: np.ndarray
    topical: np.ndarray
    terms: list[Counter]


@dataclass
class DirAnalysis:
    """Everything known about one folder, plus the verdict."""

    path: Path
    settings: Settings
    thresholds: Thresholds
    backend: str
    files: list[FileEntry] = field(default_factory=list)
    texts: list[str] = field(default_factory=list)
    terms: list[Counter] = field(default_factory=list)
    vectors: np.ndarray = field(default_factory=lambda: np.zeros((0, 0), np.float32))
    topical: np.ndarray = field(default_factory=lambda: np.zeros(0, bool))
    clustering: Clustering | None = None
    cluster_labels: dict[int, list[str]] = field(default_factory=dict)
    child_profiles: dict[Path, np.ndarray] = field(default_factory=dict)
    subdirs: list[Path] = field(default_factory=list)
    truncated: int = 0
    judged: bool = True
    skip_reason: str = ""
    findings: list[Finding] = field(default_factory=list)
    #: Signals that raised while judging this folder. A crashed signal and a
    #: quiet one look identical from the outside, so this is carried out to the
    #: report rather than left in a module-level global.
    failed_signals: list[str] = field(default_factory=list)
    score: float = 0.0
    verdict: Verdict = Verdict.TIDY

    # --- conveniences used by the signals ----------------------------------

    @property
    def n_files(self) -> int:
        return len(self.files)

    def meaningful_clusters(self) -> list[int]:
        """Clusters big enough for their presence to mean something."""
        if not self.clustering or self.n_files == 0:
            return []
        floor = max(
            self.settings.meaningful_cluster_min,
            int(self.settings.meaningful_cluster_frac * self.n_files),
        )
        sizes = self.clustering.sizes()
        return [cid for cid, size in sizes.items() if size >= floor]

    def members(self, cid: int) -> list[int]:
        if not self.clustering:
            return []
        return self.clustering.members(cid).tolist()

    def label_of(self, cid: int) -> str:
        return format_label(self.cluster_labels.get(cid, []))

    def names(self, indices: list[int], limit: int = 3) -> list[str]:
        return [self.files[i].name for i in indices[:limit]]

    def mtime_span(self, indices: list[int]) -> tuple[float, float]:
        if not indices:
            return (0.0, 0.0)
        times = [self.files[i].mtime for i in indices]
        return (min(times), max(times))
