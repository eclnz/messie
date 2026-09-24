"""Values returned from analysis and rendered for callers."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path

from messie.score import Verdict


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
