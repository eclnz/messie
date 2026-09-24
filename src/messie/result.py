"""Values returned from analysis and rendered for callers."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum, IntEnum
from pathlib import Path


class Verdict(IntEnum):
    """How messy a folder appears from its score."""

    TIDY = 0
    LIVED_IN = 1
    MESSY = 2
    CHAOTIC = 3


@dataclass
class Finding:
    """One observed sign that a folder has become messy."""

    code: str
    severity: float
    headline: str
    detail: str = ""
    examples: list[str] = field(default_factory=list)
    data: dict = field(default_factory=dict)

    def __post_init__(self) -> None:
        self.severity = max(0.0, min(1.0, float(self.severity)))


class SkipReason(str, Enum):
    """Why a folder was not eligible for a verdict."""

    TOO_FEW_FILES = "too_few_files"

    @property
    def message(self) -> str:
        return {
            SkipReason.TOO_FEW_FILES: "too few files to judge",
        }[self]


@dataclass
class DirAnalysis:
    """The reportable verdict for one folder."""

    path: Path
    embedder: str
    n_files: int
    truncated: int = 0
    clusters: int = 0
    meaningful_clusters: int = 0
    judged: bool = True
    skip_reason: SkipReason | None = None
    findings: list[Finding] = field(default_factory=list)
    #: Signals that could not run.
    failed_signals: list[str] = field(default_factory=list)
    score: float = 0.0
    verdict: Verdict = Verdict.TIDY
