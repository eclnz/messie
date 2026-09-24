"""Signals about the shape of a folder rather than its meaning.

There was once a ``type_soup`` signal here, firing when a folder held many
different *sorts* of file evenly mixed. Measured across the demo tree it fired
on more folders than any other signal and never once changed a verdict band,
and on real coherent directories it was noise. A signal that never decides
anything is weight without a vote, so it was removed.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from messie.signals import Finding, ramp, signal

if TYPE_CHECKING:  # pragma: no cover
    from messie.result import DirAnalysis


@signal
def overcrowded(analysis: DirAnalysis) -> list[Finding]:
    """Far too many things loose in one place.

    Opt-in: see ``Settings.report_crowding`` for the measurement that made it
    so. A count is not evidence about contents, and this is the only signal
    that offers one.
    """
    if not analysis.settings.report_crowding:
        return []

    soft = analysis.settings.overcrowded_soft_limit
    n = analysis.n_files + analysis.truncated
    if n <= soft:
        return []

    severity = ramp(n, soft, soft * 6)
    if severity <= 0:
        return []

    return [
        Finding(
            code="overcrowded",
            severity=severity,
            headline=f"{n} files sit loose in this one folder.",
            detail=f"Past about {soft}, a flat folder stops being browsable.",
            data={"count": n, "soft_limit": soft},
        )
    ]
