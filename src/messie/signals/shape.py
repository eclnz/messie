"""Signals based on folder shape rather than content."""

from __future__ import annotations

from typing import TYPE_CHECKING

from messie.result import Finding
from messie.signals import ramp, signal

if TYPE_CHECKING:  # pragma: no cover
    from messie.analyze import SignalContext


@signal
def overcrowded(analysis: SignalContext) -> list[Finding]:
    """Report opt-in crowding in a flat folder."""
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
