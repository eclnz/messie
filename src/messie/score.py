"""Turning findings into a number and a word.

Signals are combined with a soft OR rather than a sum: several independent
kinds of mess compound, but no amount of piling on can push the score past 100,
and one strong signal alone is already enough to call a folder messy.
"""

from __future__ import annotations

import math
from enum import IntEnum
from typing import TYPE_CHECKING

from messie.config import DEFAULT_SETTINGS, Settings

if TYPE_CHECKING:  # pragma: no cover
    from messie.result import Finding


class Verdict(IntEnum):
    TIDY = 0
    LIVED_IN = 1
    MESSY = 2
    CHAOTIC = 3

    @property
    def label(self) -> str:
        return {
            Verdict.TIDY: "tidy",
            Verdict.LIVED_IN: "lived-in",
            Verdict.MESSY: "messy",
            Verdict.CHAOTIC: "chaotic",
        }[self]

    @classmethod
    def parse(cls, text: str) -> Verdict:
        key = text.strip().lower().replace("-", "_")
        for member in cls:
            if member.name.lower() == key:
                return member
        raise ValueError(f"unknown verdict {text!r}")


#: Lower bound of each band.
BANDS: tuple[tuple[int, Verdict], ...] = (
    (75, Verdict.CHAOTIC),
    (50, Verdict.MESSY),
    (25, Verdict.LIVED_IN),
    (0, Verdict.TIDY),
)


def verdict_for(score: float) -> Verdict:
    for floor, verdict in BANDS:
        if score >= floor:
            return verdict
    return Verdict.TIDY


def score_findings(
    findings: list[Finding], settings: Settings = DEFAULT_SETTINGS
) -> tuple[float, Verdict]:
    """Combined 0-100 score and the band it falls in."""
    if not findings:
        return 0.0, Verdict.TIDY

    # Work in log space so many small signals cannot silently saturate.
    residual = 0.0
    for finding in findings:
        weight = settings.signal_weights.get(finding.code, 0.3)
        contribution = max(0.0, min(0.999, weight * finding.severity))
        residual += math.log1p(-contribution)

    score = round(100.0 * (1.0 - math.exp(residual)), 1)
    return score, verdict_for(score)
