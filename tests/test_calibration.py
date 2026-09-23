"""The constants in the source must keep matching what measurement says.

messie's thresholds were twice set by guesswork and twice found to be wrong —
the first time from a four-document probe that showed beautiful separation and
proved nothing. They are now derived from the example corpus by
``scripts/calibrate.py``, and these tests fail if the shipped numbers drift
away from what that derivation produces, or if the corpus stops being
separable in the first place.

Without this, the numbers in ``wordllama_backend.py`` would slowly go back to
being magic.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))

from calibrate import measure_separation, sweep_threshold  # noqa: E402

from messie.config import DEFAULT_SETTINGS, Thresholds  # noqa: E402
from messie.embed import BACKEND_ORDER, get_embedder  # noqa: E402

BACKEND = "wordllama"

#: How far the shipped scale may sit from the measured optimum. Wide enough
#: that a corpus tweak does not fail the build, narrow enough that a real
#: mistake does.
SCALE_TOLERANCE = 0.06


def backend_or_skip(name: str):
    try:
        return get_embedder(name)
    except Exception as exc:  # noqa: BLE001
        pytest.skip(f"{name} unavailable: {exc}")


@pytest.fixture(scope="module")
def separation():
    backend_or_skip(BACKEND)
    return measure_separation(BACKEND)


@pytest.fixture(scope="module")
def sweep():
    backend_or_skip(BACKEND)
    return sweep_threshold(BACKEND, pairs=60)


# --- the corpus has to be separable at all ---------------------------------


def test_every_subject_holds_together_above_the_threshold(separation):
    """The weakest subject must still be tighter than the clustering cut-off."""
    embedder = backend_or_skip(BACKEND)
    thresholds = Thresholds.derive(embedder.scale, DEFAULT_SETTINGS)
    assert separation.intra_min > thresholds.cluster


def test_subjects_are_further_apart_than_they_are_wide(separation):
    """Nearly all subject pairs sit below the loosest subject's own cohesion.

    If this inverts, no threshold exists that both holds subjects together and
    keeps them apart, and every verdict built on clustering becomes a coin toss.
    """
    assert separation.inter_p95 < separation.intra_min
    assert separation.inter_median < separation.intra_median / 2


def test_the_closest_pair_is_a_known_neighbour(separation):
    """The hardest pairs should be genuinely adjacent subjects, not nonsense."""
    hardest = {frozenset((a, b)) for a, b, _ in separation.closest_pairs[:4]}
    plausible = [
        {"conference_talk", "meeting_minutes"},
        {"docker_k8s_config", "ci_pipeline_config"},
        {"python_web_api", "go_microservice"},
        {"tax_return", "client_invoices"},
        {"board_slides", "meeting_minutes"},
        {"mortgage_application", "rental_lease"},
        {"board_slides", "conference_talk"},
    ]
    assert any(frozenset(p) in hardest for p in plausible)


# --- the shipped constants have to match the measurement -------------------


def test_shipped_scale_matches_the_measured_optimum(sweep):
    drift = abs(sweep.shipped_scale - sweep.best.scale)
    assert drift <= SCALE_TOLERANCE, (
        f"{BACKEND} ships scale {sweep.shipped_scale} but the corpus says "
        f"{sweep.best.scale}. Re-run scripts/calibrate.py and update the backend."
    )


def test_the_shipped_threshold_performs(sweep):
    """At the threshold we actually ship, both rates must stay high."""
    embedder = backend_or_skip(BACKEND)
    shipped = Thresholds.derive(embedder.scale, DEFAULT_SETTINGS).cluster
    nearest = min(sweep.points, key=lambda p: abs(p.threshold - shipped))
    assert nearest.subjects_held >= 0.90
    assert nearest.pairs_separated >= 0.80


def test_the_sweep_has_a_real_peak(sweep):
    """A flat sweep would mean the threshold does not matter, which would mean
    the measurement is not measuring anything."""
    best = sweep.best.total
    worst = min(p.total for p in sweep.points)
    assert best - worst > 0.25


@pytest.mark.parametrize("backend", BACKEND_ORDER)
def test_every_backend_declares_a_scale(backend):
    """Thresholds are fractions of this, so a missing scale is silently wrong."""
    embedder = backend_or_skip(backend)
    assert 0.05 < embedder.scale < 1.0
