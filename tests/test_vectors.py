"""Tests for combining content, names and file kinds into evidence vectors."""

from __future__ import annotations

from collections import Counter
from pathlib import Path

import numpy as np
import pytest

from messie.analyze import PreparedRecord, _compose_record, _mix_for
from messie.config import DEFAULT_SETTINGS
from messie.kinds import Domain, Kind
from messie.scan import FileEntry


def entry(name: str = "notes.txt") -> FileEntry:
    return FileEntry(
        path=Path(name), kind=Kind.TEXT, domain=Domain.OFFICE,
        size=100, mtime=0.0,
    )


def test_configured_text_weights_are_used():
    file = entry()
    settings = DEFAULT_SETTINGS.with_(text_weight_thin=0.2, text_weight_rich=0.9)
    assert _mix_for(file, "x", "notes", settings).text == pytest.approx(0.2, abs=0.001)
    assert _mix_for(file, "x" * 120, "notes", settings).text == pytest.approx(0.9)


def test_reliability_changes_smoothly_around_minimum_text_length():
    file = entry()
    before = _mix_for(file, "x" * 119, "notes", DEFAULT_SETTINGS).text
    after = _mix_for(file, "x" * 120, "notes", DEFAULT_SETTINGS).text
    assert 0 < after - before < 0.001


def test_evidence_channels_do_not_cross_match():
    files = [entry("alpha.txt"), entry("beta.txt")]
    prepared = PreparedRecord(
        files=files,
        texts=["alpha " * 30, "beta " * 30],
        names=["beta", "alpha"],
        kinds=["text", "text"],
        terms=[Counter(), Counter()],
    )
    # Content and filenames are swapped.  Adding modalities in one vector would
    # spuriously make these files similar through cross-channel dot products.
    text = np.array([[1.0, 0.0], [0.0, 1.0]], dtype=np.float32)
    names = np.array([[0.0, 1.0], [1.0, 0.0]], dtype=np.float32)
    kinds = np.array([[1.0, 1.0], [1.0, 1.0]], dtype=np.float32)
    kinds /= np.linalg.norm(kinds, axis=1, keepdims=True)

    record = _compose_record(prepared, text, names, kinds, DEFAULT_SETTINGS)
    similarity = float(record.vectors[0] @ record.vectors[1])
    assert similarity == pytest.approx(0.05, abs=1e-6)
