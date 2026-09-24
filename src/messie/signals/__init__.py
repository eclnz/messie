"""Signal registration and execution."""

from __future__ import annotations

import os
from collections.abc import Callable
from typing import TYPE_CHECKING, NamedTuple

from messie.result import Finding

if TYPE_CHECKING:  # pragma: no cover
    from messie.analyze import SignalContext


class SignalRun(NamedTuple):
    """Findings and failed signal names from one run."""

    findings: list[Finding]
    failed: list[str]


SignalFn = Callable[["SignalContext"], list[Finding]]

_REGISTRY: list[SignalFn] = []


def signal(fn: SignalFn) -> SignalFn:
    """Register a signal function."""
    _REGISTRY.append(fn)
    return fn


def run_all(analysis: SignalContext) -> SignalRun:
    """Every registered signal, strongest first."""
    debug = bool(os.environ.get("MESSIE_DEBUG"))
    findings: list[Finding] = []
    failed: list[str] = []

    for fn in _REGISTRY:
        try:
            findings.extend(fn(analysis))
        except Exception:
            # Keep independent signals running; debug mode re-raises.
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


# Import signal modules after defining the decorator.
from messie.signals import debris, shape, temporal, topics  # noqa: E402,F401
