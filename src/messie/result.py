"""Internal signal inputs and the compact result returned to callers."""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass, field
from enum import Enum
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


class SkipReason(str, Enum):
    """Why a folder was not eligible for a verdict."""

    TOO_FEW_FILES = "too_few_files"

    @property
    def message(self) -> str:
        return {
            SkipReason.TOO_FEW_FILES: "too few files to judge",
        }[self]


@dataclass
class SignalContext:
    """Evidence and settings a signal needs while judging one folder."""

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


@dataclass
class DirAnalysis:
    """The reportable verdict for one folder."""

    path: Path
    backend: str
    n_files: int
    truncated: int = 0
    clusters: int = 0
    meaningful_clusters: int = 0
    judged: bool = True
    skip_reason: SkipReason | None = None
    findings: list[Finding] = field(default_factory=list)
    #: Signals that raised while judging this folder. A crashed signal and a
    #: quiet one look identical from the outside, so this is carried out to the
    #: report rather than left in a module-level global.
    failed_signals: list[str] = field(default_factory=list)
    score: float = 0.0
    verdict: Verdict = Verdict.TIDY
