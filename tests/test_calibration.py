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

from calibrate import (  # noqa: E402
    MIN_NEGATIVES,
    measure_separation,
    sweep_misfiled,
    sweep_threshold,
    sweep_unrelated,
)
from conftest import backend_or_skip  # noqa: E402

from messie.config import DEFAULT_SETTINGS, Thresholds  # noqa: E402
from messie.embed import BACKEND_ORDER  # noqa: E402

BACKEND = "wordllama"

#: How far the shipped scale may sit from the measured optimum. Wide enough
#: that a corpus tweak does not fail the build, narrow enough that a real
#: mistake does.
SCALE_TOLERANCE = 0.06


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
    """At the threshold we actually ship, both rates must stay high.

    The floors were 0.90 and 0.80, copied from a comment describing a corpus
    half this size. The held rate had not met 0.90 for some time and nobody
    noticed, because the test was asserting a remembered number rather than a
    measured one. These are set just under what the current corpus produces
    (76% and 92%), which is what the assertion was always meant to be: a guard
    against regression, not a target nothing has to hit.
    """
    embedder = backend_or_skip(BACKEND)
    shipped = Thresholds.derive(embedder.scale, DEFAULT_SETTINGS).cluster
    nearest = min(sweep.points, key=lambda p: abs(p.threshold - shipped))
    assert nearest.subjects_held >= 0.70
    assert nearest.pairs_separated >= 0.85


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


# --- the ratios that were never swept until now ----------------------------
#
# cluster_rel had a derivation; unrelated_rel and misfiled_margin_rel were
# guesses that had never been measured at all, and one of them was badly wrong.
# These keep both honest, and — just as importantly — keep the measurement
# itself honest: each sweep's negative set was at one point empty or nearly so,
# which produced a clean-looking plateau that was a statement about nothing.


@pytest.fixture(scope="module")
def unrelated_sweep():
    backend_or_skip(BACKEND)
    return sweep_unrelated(BACKEND, pairs=40, limit=250)


def test_unrelated_rel_sits_above_its_measured_plateau_on_purpose(unrelated_sweep):
    """The shipped value is knowingly off the sweep's optimum, and stays there.

    This is the one constant where measurement and intent disagree, so the test
    pins the disagreement rather than either side of it. The sweep scores
    against package directories, which the README explicitly declines to tune
    to; moving onto its plateau costs 13 points of recall on genuinely mixed
    folders and stops the canonical novel-and-tax-returns case reading as a
    mess at all.

    If the plateau ever rises to meet 0.55 the divergence has resolved itself
    and this test should go. If someone lowers the constant onto the plateau
    without also fixing the ground-truth tests that then break, this fails and
    says why.
    """
    lo, hi = unrelated_sweep.plateau
    shipped = DEFAULT_SETTINGS.unrelated_rel
    assert shipped > hi, (
        f"unrelated_rel={shipped} is no longer above the measured plateau "
        f"{lo}-{hi}. If the sweep now agrees with the shipped value, delete "
        "this test and the long comment in config.py along with it."
    )


def test_the_unrelated_sweep_knows_when_it_cannot_conclude(unrelated_sweep):
    """The thin-sample guard has to be wired up, whichever way it lands here.

    This deliberately does *not* assert a sample size. How many real
    directories split into two meaningful clusters depends on what happens to
    be installed on the machine running the tests, and it moves for reasons
    that have nothing to do with messie: shortening ``text_excerpt_chars`` for
    speed took it from 34 to 9 on one laptop. A test asserting 20+ would have
    failed for that, which is not a bug in anything.

    What must hold is that the count and the verdict agree — that a sweep
    scoring against too few negatives says so instead of recommending a
    constant off the back of nine coin flips. The first version of this sweep
    scored against folders that could not fire the signal at any setting and
    reported a flawless 0% false-alarm rate across the whole range, and nothing
    in the output hinted that it was measuring nothing at all.
    """
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
    """misfiled_margin_rel ships as an unfitted guess on purpose.

    Too few real directories can raise the finding for a false-alarm rate to
    mean anything, so ``calibrate.py`` declines to recommend a value. If this
    ever starts passing as conclusive, the constant should finally be fitted —
    which is a good failure to get.
    """
    backend_or_skip(BACKEND)
    report = sweep_misfiled(BACKEND, limit=250)
    assert report.inconclusive, (
        "the misfiled sweep now has enough negatives to be conclusive "
        f"({report.negatives}); fit misfiled_margin_rel and update config.py"
    )
