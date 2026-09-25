"""Calibration regression tests."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))

from calibrate import (  # noqa: E402
    MIN_NEGATIVES,
    measure_separation,
    sweep_misfiled,
    sweep_threshold,
    sweep_unrelated,
)
from conftest import embedder_or_skip  # noqa: E402

from messie.config import DEFAULT_SETTINGS, Thresholds  # noqa: E402

#: Permitted drift from the measured optimum.
SCALE_TOLERANCE = 0.06

@pytest.fixture(scope="module")
def separation():
    embedder_or_skip()
    return measure_separation()


@pytest.fixture(scope="module")
def sweep():
    embedder_or_skip()
    return sweep_threshold(pairs=60)


def test_every_subject_holds_together_above_the_threshold(separation):
    """The weakest subject must still be tighter than the clustering cut-off."""
    embedder = embedder_or_skip()
    thresholds = Thresholds.derive(embedder.scale, DEFAULT_SETTINGS)
    assert separation.intra_min > thresholds.cluster


def test_subjects_are_further_apart_than_they_are_wide(separation):
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


def test_shipped_scale_matches_the_measured_optimum(sweep):
    drift = abs(sweep.shipped_scale - sweep.best.scale)
    assert drift <= SCALE_TOLERANCE, (
        f"the default embedder ships scale {sweep.shipped_scale} but the corpus says "
        f"{sweep.best.scale}. Re-run scripts/calibrate.py and update the calibration."
    )


def test_the_shipped_threshold_performs(sweep):
    """The shipped threshold must retain useful performance."""
    embedder = embedder_or_skip()
    shipped = Thresholds.derive(embedder.scale, DEFAULT_SETTINGS).cluster
    nearest = min(sweep.points, key=lambda p: abs(p.threshold - shipped))
    assert nearest.subjects_held >= 0.70
    assert nearest.pairs_separated >= 0.85


def test_the_sweep_has_a_real_peak(sweep):
    """The sweep must have enough range to distinguish useful thresholds."""
    best = sweep.best.total
    worst = min(p.total for p in sweep.points)
    assert best - worst >= 0.20


def test_chosen_threshold_generalises_to_unseen_topics(sweep):
    """Selection and evaluation must not reuse the same authored subjects."""
    assert sweep.training_topics > sweep.validation_topics >= 2
    assert sweep.validation.subjects_held >= 0.60
    assert sweep.validation.pairs_separated >= 0.70


def test_default_embedder_declares_a_scale():
    """Thresholds are fractions of this, so a missing scale is silently wrong."""
    embedder = embedder_or_skip()
    assert 0.05 < embedder.scale < 1.0


@pytest.fixture(scope="module")
def unrelated_sweep():
    embedder_or_skip()
    return sweep_unrelated(pairs=40, limit=250)


def test_unrelated_rel_sits_above_its_measured_plateau_on_purpose(unrelated_sweep):
    """The unrelated-topic setting intentionally exceeds this sweep's plateau."""
    lo, hi = unrelated_sweep.plateau
    shipped = DEFAULT_SETTINGS.unrelated_rel
    assert shipped > hi, (
        f"unrelated_rel={shipped} is no longer above the measured plateau "
        f"{lo}-{hi}. If the sweep now agrees with the shipped value, delete "
        "this test and the long comment in config.py along with it."
    )


def test_the_unrelated_sweep_knows_when_it_cannot_conclude(unrelated_sweep):
    """Sweeps with too few negatives must be marked inconclusive."""
    assert unrelated_sweep.inconclusive == (unrelated_sweep.negatives < MIN_NEGATIVES)
    if unrelated_sweep.inconclusive:
        pytest.skip(
            f"only {unrelated_sweep.negatives} at-risk directories on this machine; "
            "the sweep correctly declines to conclude"
        )


def test_the_unrelated_sweep_still_trades_off(unrelated_sweep):
    """Recall must rise and precision must fall across the range. If both move
    the same way the sweep is measuring an artefact, not a trade-off."""
    points = unrelated_sweep.points
    assert points[0].caught < points[-1].caught
    assert points[0].false_alarms < points[-1].false_alarms


def test_misfiled_margin_is_still_known_to_be_unmeasurable():
    """The misfiled margin needs more real negatives before fitting."""
    embedder_or_skip()
    report = sweep_misfiled(limit=250)
    assert report.inconclusive, (
        "the misfiled sweep now has enough negatives to be conclusive "
        f"({report.negatives}); fit misfiled_margin_rel and update config.py"
    )
