"""Score combination and verdict bands."""

from __future__ import annotations

import pytest

from messie.analyze import _score_findings, _verdict_for
from messie.cli import _parse_verdict
from messie.config import DEFAULT_SETTINGS
from messie.result import Verdict
from messie.signals import Finding, ramp


def make(code: str, severity: float) -> Finding:
    return Finding(code=code, severity=severity, headline="x")


def test_no_findings_is_tidy():
    assert _score_findings([]) == (0.0, Verdict.TIDY)


def test_severity_is_clamped():
    assert make("x", 5.0).severity == 1.0
    assert make("x", -2.0).severity == 0.0


def test_signals_compound():
    one = _score_findings([make("debris", 0.5)])[0]
    two = _score_findings([make("debris", 0.5), make("type_soup", 0.5)])[0]
    assert two > one


def test_correlated_topic_signals_do_not_double_count():
    primary = make("unrelated_topics", 0.7)
    supporting = make("time_strata", 1.0)
    assert _score_findings([primary, supporting]) == _score_findings([primary])


def test_independent_signals_still_compound_with_topic_disorder():
    topical = make("unrelated_topics", 0.5)
    with_debris = _score_findings([topical, make("debris", 0.8)])[0]
    assert with_debris > _score_findings([topical])[0]


def test_score_never_exceeds_one_hundred():
    findings = [make(code, 1.0) for code in DEFAULT_SETTINGS.signal_weights]
    score, verdict = _score_findings(findings)
    assert score <= 100.0
    assert verdict == Verdict.CHAOTIC


def test_the_flagship_signal_alone_can_reach_messy():
    score, verdict = _score_findings([make("unrelated_topics", 0.55)])
    assert verdict >= Verdict.MESSY


def test_two_unrelated_subjects_is_a_mess_not_a_quirk():
    """Severity the unrelated_topics curve gives two well-separated subjects."""
    score, verdict = _score_findings([make("unrelated_topics", 0.55)])
    assert 50 <= score < 75


def test_weak_signals_alone_do_not_reach_messy():
    findings = [make("debris", 0.3), make("overcrowded", 0.25)]
    assert _score_findings(findings)[1] < Verdict.MESSY


def test_unknown_code_still_contributes():
    assert _score_findings([make("made_up", 1.0)])[0] > 0


@pytest.mark.parametrize(
    ("score", "expected"),
    [(0, Verdict.TIDY), (24.9, Verdict.TIDY), (25, Verdict.LIVED_IN),
     (49.9, Verdict.LIVED_IN), (50, Verdict.MESSY), (74.9, Verdict.MESSY),
     (75, Verdict.CHAOTIC), (100, Verdict.CHAOTIC)],
)
def test_bands(score, expected):
    assert _verdict_for(score) == expected


def test_verdicts_are_ordered():
    assert Verdict.TIDY < Verdict.LIVED_IN < Verdict.MESSY < Verdict.CHAOTIC


@pytest.mark.parametrize("text", ["tidy", "MESSY", "lived-in", "lived_in", "Chaotic"])
def test_verdict_parsing(text):
    assert isinstance(_parse_verdict(text), Verdict)


def test_verdict_parsing_rejects_nonsense():
    with pytest.raises(ValueError):
        _parse_verdict("spotless")


@pytest.mark.parametrize(
    ("value", "low", "high", "expected"),
    [(0, 1, 4, 0.0), (1, 1, 4, 0.0), (4, 1, 4, 1.0), (9, 1, 4, 1.0), (2.5, 1, 4, 0.5)],
)
def test_ramp(value, low, high, expected):
    assert ramp(value, low, high) == pytest.approx(expected)
