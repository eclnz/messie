"""The individual things that make a folder messy.

Each signal inspects a finished :class:`~messie.analyze.DirAnalysis` and returns
zero or more findings. A finding states what was observed and how strongly,
never what to do about it — messie reports mess, it does not tidy.
"""

from __future__ import annotations

import os
from collections.abc import Callable
from dataclasses import dataclass, field
from typing import TYPE_CHECKING

if TYPE_CHECKING:  # pragma: no cover
    from messie.analyze import DirAnalysis


@dataclass
class Finding:
    code: str
    #: 0..1, how strongly this signal fired.
    severity: float
    #: One line, written to be read by a person.
    headline: str
    detail: str = ""
    examples: list[str] = field(default_factory=list)
    #: Structured payload for --json consumers.
    data: dict = field(default_factory=dict)

    def __post_init__(self) -> None:
        self.severity = max(0.0, min(1.0, float(self.severity)))


SignalFn = Callable[["DirAnalysis"], list[Finding]]

_REGISTRY: list[SignalFn] = []

#: Names of signals that raised during the last run_all, for --doctor and tests.
failed_signals: list[str] = []


def signal(fn: SignalFn) -> SignalFn:
    """Register a signal function."""
    _REGISTRY.append(fn)
    return fn


def run_all(analysis: DirAnalysis) -> list[Finding]:
    """Every registered signal, strongest first."""
    from messie.signals import debris, temporal, topics, types  # noqa: F401

    failed_signals.clear()

    debug = bool(os.environ.get("MESSIE_DEBUG"))
    out: list[Finding] = []
    for fn in _REGISTRY:
        try:
            out.extend(fn(analysis))
        except Exception:
            # One broken signal should not cost the user the other eight. But a
            # silently swallowed signal is indistinguishable from a quiet one,
            # so MESSIE_DEBUG=1 turns this back into a crash.
            if debug:
                raise
            failed_signals.append(fn.__name__)
            continue
    out.sort(key=lambda f: -f.severity)
    return out


def ramp(value: float, low: float, high: float) -> float:
    """0 below ``low``, 1 at or above ``high``, linear in between."""
    if high <= low:
        return 1.0 if value >= high else 0.0
    return max(0.0, min(1.0, (value - low) / (high - low)))
