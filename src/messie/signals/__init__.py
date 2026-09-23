"""The individual things that make a folder messy.

Each signal inspects a finished :class:`~messie.result.DirAnalysis` and returns
zero or more findings. A finding states what was observed and how strongly,
never what to do about it — messie reports mess, it does not tidy.

Signals register themselves with the ``@signal`` decorator, and the modules
holding them are imported at the bottom of this file. That import is what makes
the decorator mean anything: it used to live inside ``run_all``, which left the
registry empty until the first folder was judged and made "add a signal" quietly
depend on editing a line buried in a function.
"""

from __future__ import annotations

import os
from collections.abc import Callable
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, NamedTuple

if TYPE_CHECKING:  # pragma: no cover
    from messie.result import DirAnalysis


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


class SignalRun(NamedTuple):
    """What one pass over the signals produced.

    The failures travel back with the findings rather than in a module-level
    list. A crashed signal and a quiet one look identical from the outside, so
    the caller has to be told which happened — and telling it through shared
    state would mean two folders judged at once could overwrite each other.
    """

    findings: list[Finding]
    failed: list[str]


SignalFn = Callable[["DirAnalysis"], list[Finding]]

_REGISTRY: list[SignalFn] = []


def signal(fn: SignalFn) -> SignalFn:
    """Register a signal function."""
    _REGISTRY.append(fn)
    return fn


def run_all(analysis: DirAnalysis) -> SignalRun:
    """Every registered signal, strongest first."""
    debug = bool(os.environ.get("MESSIE_DEBUG"))
    findings: list[Finding] = []
    failed: list[str] = []

    for fn in _REGISTRY:
        try:
            findings.extend(fn(analysis))
        except Exception:
            # One broken signal should not cost the user the other eight. But a
            # silently swallowed signal is indistinguishable from a quiet one,
            # so MESSIE_DEBUG=1 turns this back into a crash.
            if debug:
                raise
            failed.append(fn.__name__)
            continue

    findings.sort(key=lambda f: -f.severity)
    return SignalRun(findings, failed)


def ramp(value: float, low: float, high: float) -> float:
    """0 below ``low``, 1 at or above ``high``, linear in between."""
    if high <= low:
        return 1.0 if value >= high else 0.0
    return max(0.0, min(1.0, (value - low) / (high - low)))


# Importing these is what populates the registry, and it has to happen after
# ``signal`` exists. Each module imports Finding/ramp/signal back from here,
# which is safe: by this line they are defined.
from messie.signals import debris, shape, temporal, topics  # noqa: E402,F401
