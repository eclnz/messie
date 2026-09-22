"""Signals about files that say nothing at all.

A folder does not only get messy by collecting unrelated things. It also
collects files whose contents have stopped meaning anything — downloads that
finished corrupt, text mangled by an encoding round-trip, payloads saved with
a .txt extension, scans OCR'd into nonsense.

Incoherence has to be caught head on. A garbled file has no subject, so it
joins no group and no amount of clustering will ever remark on it; it is
invisible to every signal that works by finding structure.
"""

from __future__ import annotations

from collections import Counter
from typing import TYPE_CHECKING

from messie.signals import Finding, ramp, signal

if TYPE_CHECKING:  # pragma: no cover
    from messie.analyze import DirAnalysis


@signal
def garbled(analysis: DirAnalysis) -> list[Finding]:
    """Files whose text has stopped being language."""
    if not analysis.legibility:
        return []

    bad = [i for i, verdict in enumerate(analysis.legibility) if verdict.garbled]
    if len(bad) < 2:
        # One odd file is bad luck. Several is a folder nobody has looked at.
        return []

    fraction = len(bad) / max(1, analysis.n_files)
    severity = max(ramp(len(bad), 1, 8), ramp(fraction, 0.03, 0.30))
    if severity <= 0:
        return []

    reasons = Counter(analysis.legibility[i].reason for i in bad)
    bad.sort(key=lambda i: analysis.legibility[i].score)

    return [
        Finding(
            code="garbled",
            severity=severity,
            headline=f"{len(bad)} files here are unreadable.",
            detail="; ".join(f"{reason} ({count})" for reason, count in reasons.most_common(3)),
            examples=analysis.names(bad, limit=4),
            data={
                "count": len(bad),
                "fraction": round(fraction, 3),
                "reasons": dict(reasons),
                "files": [
                    {
                        "name": analysis.files[i].name,
                        "score": analysis.legibility[i].score,
                        "reason": analysis.legibility[i].reason,
                    }
                    for i in bad[:20]
                ],
            },
        )
    ]
