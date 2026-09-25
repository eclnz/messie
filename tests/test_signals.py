"""Signal behaviour tests."""

from __future__ import annotations

import os
import time
from pathlib import Path
from types import SimpleNamespace
from typing import cast

import numpy as np
import pytest
from conftest import codes, finding, write_blob, write_text

from messie.analyze import SignalContext, analyze_dir
from messie.result import Verdict
from messie.scan import read_dir
from messie.signals.temporal import time_strata

DAY = 86400.0



#: Bodies long enough for topic signals to judge.
_BODY = (
    "This document is about {marker}, number {i} in the series. It concerns "
    "{marker} throughout, discussing {marker} at some length so that there is "
    "enough of it to form a considered view of the subject matter."
)


def body_for(marker: str, i: int) -> str:
    return _BODY.format(marker=marker, i=i)


def topic_files(folder: Path, marker: str, count: int, ext: str = "txt", start: int = 0):
    for i in range(start, start + count):
        write_text(folder / f"{marker}_{i}.{ext}", body_for(marker, i))


def age(path: Path, days: float):
    stamp = time.time() - days * DAY
    os.utime(path, (stamp, stamp))


def test_unrelated_topics_fires_on_three_subjects(tmp_path, fake_embedder):
    folder = tmp_path / "drawer"
    for marker in ("alpha", "beta", "gamma"):
        topic_files(folder, marker, 3)
    analysis = analyze_dir(folder, embedder=fake_embedder)

    assert "unrelated_topics" in codes(analysis)
    assert len(finding(analysis, "unrelated_topics").data["groups"]) == 3
    assert analysis.verdict in {Verdict.MESSY, Verdict.CHAOTIC}


def test_unrelated_topics_silent_on_one_subject(tmp_path, fake_embedder):
    folder = tmp_path / "coherent"
    topic_files(folder, "alpha", 9)
    analysis = analyze_dir(folder, embedder=fake_embedder)

    assert "unrelated_topics" not in codes(analysis)
    assert analysis.verdict is Verdict.TIDY


def test_same_file_type_is_no_defence(tmp_path, fake_embedder):
    """The motivating case, in miniature: uniform extension, unrelated content."""
    folder = tmp_path / "Documents"
    for marker in ("alpha", "beta", "gamma"):
        topic_files(folder, marker, 4, ext="docx")
    analysis = analyze_dir(folder, embedder=fake_embedder)

    assert {f.ext for f in read_dir(folder).files} == {"docx"}
    assert "unrelated_topics" in codes(analysis)


def test_a_tiny_side_group_does_not_count_as_a_topic(tmp_path, fake_embedder):
    folder = tmp_path / "mostly_one_thing"
    topic_files(folder, "alpha", 20)
    topic_files(folder, "beta", 1)
    analysis = analyze_dir(folder, embedder=fake_embedder)
    assert "unrelated_topics" not in codes(analysis)


def test_strays_are_reported(tmp_path, fake_embedder):
    folder = tmp_path / "with_strays"
    topic_files(folder, "alpha", 6)
    for i in range(4):
        write_text(
            folder / f"loner_{i}.txt",
            f"An entirely unshared subject, number {i}, sharing no vocabulary with "
            f"anything else in this folder and belonging to no group within it.",
        )
    analysis = analyze_dir(folder, embedder=fake_embedder)
    assert "strays" in codes(analysis)


def test_unreadable_files_are_not_strays(tmp_path, fake_embedder):
    """A photo album must not read as a pile of unrelated things."""
    folder = tmp_path / "album"
    for i in range(14):
        write_blob(folder / f"DSC_{100 + i}.jpg", 4000 + i)
    analysis = analyze_dir(folder, embedder=fake_embedder)
    assert "strays" not in codes(analysis)
    assert analysis.verdict is Verdict.TIDY


def test_overcrowded_is_silent_unless_asked_for(tmp_path, fake_embedder):
    """Crowding is opt-in."""
    folder = tmp_path / "heap"
    topic_files(folder, "alpha", 120)
    assert "overcrowded" not in codes(analyze_dir(folder, embedder=fake_embedder))


def test_overcrowded_when_asked_for(tmp_path, fake_embedder):
    from messie.config import DEFAULT_SETTINGS

    folder = tmp_path / "heap"
    topic_files(folder, "alpha", 120)
    analysis = analyze_dir(
        folder, DEFAULT_SETTINGS.with_(report_crowding=True), embedder=fake_embedder
    )
    assert "overcrowded" in codes(analysis)


def test_small_folder_is_not_overcrowded_even_when_asked(tmp_path, fake_embedder):
    from messie.config import DEFAULT_SETTINGS

    folder = tmp_path / "small"
    topic_files(folder, "alpha", 10)
    analysis = analyze_dir(
        folder, DEFAULT_SETTINGS.with_(report_crowding=True), embedder=fake_embedder
    )
    assert "overcrowded" not in codes(analysis)


def test_debris(tmp_path, fake_embedder):
    folder = tmp_path / "downloads"
    topic_files(folder, "alpha", 6)
    write_text(folder / "~$report.docx", "")
    write_text(folder / "statement.pdf.crdownload", "partial")
    write_text(folder / "notes.txt.tmp", "x")
    write_text(folder / "empty.txt", "")
    analysis = analyze_dir(folder, embedder=fake_embedder)
    assert "debris" in codes(analysis)
    assert finding(analysis, "debris").data["count"] >= 4


def test_version_pileup(tmp_path, fake_embedder):
    folder = tmp_path / "docs"
    topic_files(folder, "alpha", 6)
    for tag in ("", "_final", "_final_v2", " (copy)"):
        write_text(folder / f"lease agreement{tag}.txt", f"beta tenancy terms {tag}")
    analysis = analyze_dir(folder, embedder=fake_embedder)
    assert "version_pileups" in codes(analysis)


def test_numbered_series_is_not_a_pileup(tmp_path, fake_embedder):
    folder = tmp_path / "scans"
    for i in range(10):
        write_text(folder / f"tax_document_{i:02d}.txt", f"alpha page {i}")
    assert "version_pileups" not in codes(analyze_dir(folder, embedder=fake_embedder))


def test_exact_duplicates(tmp_path, fake_embedder):
    folder = tmp_path / "dupes"
    topic_files(folder, "alpha", 6)
    body = "beta meeting notes agreed to ship on friday"
    for name in ("notes.txt", "notes (1).txt", "notes copy.txt"):
        write_text(folder / name, body)
    analysis = analyze_dir(folder, embedder=fake_embedder)
    assert "duplicates" in codes(analysis)


def test_distinct_files_are_not_duplicates(tmp_path, fake_embedder):
    folder = tmp_path / "distinct"
    for i in range(8):
        write_text(
            folder / f"alpha_{i}.txt",
            f"alpha subject with quite different wording {i} " * i,
        )
    assert "duplicates" not in codes(analyze_dir(folder, embedder=fake_embedder))


def test_time_strata(tmp_path, fake_embedder):
    folder = tmp_path / "attic"
    topic_files(folder, "alpha", 4)
    topic_files(folder, "beta", 4)
    for path in folder.glob("alpha_*"):
        age(path, 1500)
    for path in folder.glob("beta_*"):
        age(path, 10)
    assert "time_strata" in codes(analyze_dir(folder, embedder=fake_embedder))


def test_a_long_running_single_subject_is_an_archive_not_a_mess(tmp_path, fake_embedder):
    folder = tmp_path / "archive"
    topic_files(folder, "alpha", 9)
    for i, path in enumerate(sorted(folder.glob("alpha_*"))):
        age(path, i * 400)
    assert "time_strata" not in codes(analyze_dir(folder, embedder=fake_embedder))


def test_loose_files_resembling_a_subfolder(tmp_path, fake_embedder):
    folder = tmp_path / "Documents"
    topic_files(folder, "beta", 6)
    topic_files(folder, "alpha", 3, start=90)
    topic_files(folder / "Alphas", "alpha", 5)

    analysis = analyze_dir(folder, embedder=fake_embedder)
    assert "misfiled_neighbours" in codes(analysis)
    assert "Alphas" in finding(analysis, "misfiled_neighbours").data["by_subdir"]


def test_dominant_parent_files_are_not_misfiled(tmp_path, fake_embedder):
    """A descendant of the dominant subject must not make its parent files loose."""
    folder = tmp_path / "Documents"
    topic_files(folder, "alpha", 8)
    topic_files(folder / "Alphas", "alpha", 6)

    analysis = analyze_dir(folder, embedder=fake_embedder)

    assert "misfiled_neighbours" not in codes(analysis)


def test_weakly_attached_files_still_match_a_descendant(tmp_path, fake_embedder):
    """A small same-subject group beside a dominant group remains detectable."""
    folder = tmp_path / "Documents"
    topic_files(folder, "beta", 6)
    topic_files(folder, "alpha", 3)
    topic_files(folder / "Alphas", "alpha", 5)

    analysis = analyze_dir(folder, embedder=fake_embedder)

    assert "misfiled_neighbours" in codes(analysis)


def _strata_context(vectors: np.ndarray, labels: list[int]):
    """Build the smallest context needed to exercise ``time_strata``."""
    now = time.time()
    files = [
        SimpleNamespace(mtime=now - (730 if i < 3 else 1) * DAY)
        for i in range(6)
    ]
    groups = tuple(np.flatnonzero(np.asarray(labels) == cid) for cid in sorted(set(labels)))
    clustering = SimpleNamespace(labels=np.asarray(labels), groups=groups)
    return SimpleNamespace(
        clustering=clustering,
        n_files=6,
        settings=SimpleNamespace(min_files_to_judge=6, time_strata_gap_days=365.0),
        files=files,
        vectors=vectors,
        topical=np.ones(6, dtype=bool),
        thresholds=SimpleNamespace(unrelated=0.55),
        mtime_span=lambda indices: (
            min(files[i].mtime for i in indices), max(files[i].mtime for i in indices)
        ),
        label_of=lambda cid: f"subject {cid}",
    )


def test_related_fragmented_eras_stay_quiet():
    """Different cluster ids alone do not make one subject separate eras."""
    vectors = np.tile(np.array([1.0, 0.0], dtype=np.float32), (6, 1))
    analysis = _strata_context(vectors, [0, 0, 0, 1, 1, 1])

    assert time_strata(cast(SignalContext, analysis)) == []


def test_unrelated_eras_are_reported():
    vectors = np.vstack(
        [
            np.tile(np.array([1.0, 0.0], dtype=np.float32), (3, 1)),
            np.tile(np.array([0.0, 1.0], dtype=np.float32), (3, 1)),
        ]
    )
    analysis = _strata_context(vectors, [0, 0, 0, 1, 1, 1])

    assert time_strata(cast(SignalContext, analysis))[0].code == "time_strata"


def test_no_neighbour_finding_when_nothing_matches(tmp_path, fake_embedder):
    folder = tmp_path / "Documents"
    topic_files(folder, "beta", 8)
    topic_files(folder / "Alphas", "alpha", 5)
    assert "misfiled_neighbours" not in codes(analyze_dir(folder, embedder=fake_embedder))


def test_too_few_files_is_not_judged(tmp_path, fake_embedder):
    folder = tmp_path / "sparse"
    topic_files(folder, "alpha", 2)
    topic_files(folder, "beta", 2)
    analysis = analyze_dir(folder, embedder=fake_embedder)
    assert not analysis.judged
    assert analysis.findings == []


@pytest.mark.parametrize("marker", ["alpha", "beta"])
def test_no_signal_raises(tmp_path, fake_embedder, marker, monkeypatch):
    """MESSIE_DEBUG turns a swallowed signal error into a failure."""
    monkeypatch.setenv("MESSIE_DEBUG", "1")
    folder = tmp_path / "x"
    topic_files(folder, marker, 8)
    write_blob(folder / "thing.jpg")

    analysis = analyze_dir(folder, embedder=fake_embedder)
    assert analysis.failed_signals == []
