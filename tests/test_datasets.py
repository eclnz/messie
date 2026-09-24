"""The example datasets, and what messie makes of them.

These run the whole pipeline over realistic folders built from the corpora —
many file kinds, many subjects — and check both halves of the job: that a mess
is called a mess, and that a folder which is merely full is left alone.
"""

from __future__ import annotations

from pathlib import Path

import pytest
from conftest import SEMANTIC_BACKENDS, backend_or_skip, codes, installed
from corpus import ALL_TOPICS, DEV_TOPICS, EXTENSIONS, OFFICE_TOPICS, PERSONAL_TOPICS, TOPICS
from corpus.build import (
    add_debris,
    add_duplicates,
    add_installers,
    add_topic,
    add_version_pileup,
    build_album,
    build_assorted,
    build_coherent,
    build_media_library,
    build_mixed,
)
from corpus.synth import write_file

from messie.analyze import analyze_dir
from messie.score import Verdict

#: Subjects that do not hold together even for a semantic backend, and why.
#: Measured against the example corpus: 34 of 35 topics form a single group.
KNOWN_WEAK = {
    "car_maintenance": "six unrelated garage jobs share little beyond the car itself",
}


INSTALLED_SEMANTIC = installed(SEMANTIC_BACKENDS)
_NO_SEMANTIC = [pytest.param(None, marks=pytest.mark.skip(reason="no semantic backend"))]


@pytest.fixture(params=INSTALLED_SEMANTIC or _NO_SEMANTIC)
def real_embedder(request):
    """Every backend that is installed."""
    return backend_or_skip(request.param)


@pytest.fixture(params=INSTALLED_SEMANTIC or _NO_SEMANTIC)
def semantic_embedder(request):
    """Only the backends that compare meaning rather than vocabulary."""
    return backend_or_skip(request.param)


# --- the corpora themselves -------------------------------------------------


def test_corpus_contract():
    """Keeps future edits to the corpora honest."""
    seen: dict[str, str] = {}
    for topic, entries in TOPICS.items():
        assert topic in EXTENSIONS, f"{topic} has no extensions"
        assert EXTENSIONS[topic], f"{topic} has an empty extension list"
        assert len(entries) >= 5, f"{topic} has only {len(entries)} entries"
        for stem, text in entries:
            assert stem not in seen, f"{stem!r} appears in {seen[stem]} and {topic}"
            seen[stem] = topic
            assert "/" not in stem and "\\" not in stem, f"{stem!r} contains a path separator"
            assert text.strip(), f"{stem!r} is empty"


def test_the_datasets_are_varied():
    """The point of the exercise: many subjects, across many file types."""
    assert len(TOPICS) >= 25
    kinds = {ext for exts in EXTENSIONS.values() for ext in exts}
    assert len(kinds) >= 12
    assert OFFICE_TOPICS and DEV_TOPICS and PERSONAL_TOPICS

# @pytest.mark.parametrize("topic", [t for t in ALL_TOPICS if t not in KNOWN_WEAK])
# def test_each_topic_reads_as_one_subject(topic, tmp_path, semantic_embedder):
#     """Six files on one subject must form exactly one group.

#     A corpus topic whose own entries do not cluster would make every test built
#     on it meaningless, so this guards the ground truth as much as the tool.
#     """
#     folder = build_coherent(tmp_path / topic, topic, 6)
#     analysis = analyze_dir(folder, embedder=semantic_embedder)
#     assert analysis.clustering.n_clusters == 1, (
#         f"{topic} split into {analysis.clustering.n_clusters} groups: "
#         f"{[analysis.label_of(c) for c in range(analysis.clustering.n_clusters)]}"
#     )


@pytest.mark.parametrize("topic", [t for t in ALL_TOPICS if t not in KNOWN_WEAK])
def test_a_single_subject_folder_is_not_a_mess(topic, tmp_path, semantic_embedder):
    folder = build_coherent(tmp_path / topic, topic, 6)
    analysis = analyze_dir(folder, embedder=semantic_embedder)
    assert "unrelated_topics" not in codes(analysis)
    assert "no_common_thread" not in codes(analysis)
    assert analysis.verdict < Verdict.MESSY


# --- mess -------------------------------------------------------------------


def test_three_unrelated_domains_in_one_folder(tmp_path, real_embedder):
    """Office paperwork, source code and a personal hobby, all in one place."""
    spec = {OFFICE_TOPICS[0]: 5, DEV_TOPICS[0]: 5, PERSONAL_TOPICS[0]: 5}
    folder = build_mixed(tmp_path / "drawer", spec)
    analysis = analyze_dir(folder, embedder=real_embedder)

    assert "unrelated_topics" in codes(analysis)
    groups = next(f for f in analysis.findings if f.code == "unrelated_topics")
    assert len(groups.data["groups"]) >= 3
    assert analysis.verdict >= Verdict.MESSY


def test_a_folder_where_every_file_is_its_own_topic(tmp_path, real_embedder):
    """The hardest case: nothing groups, because nothing belongs together.

    The clustering signal cannot fire here — there are no groups to compare —
    so this is exactly where a tool that only looks for structure goes quiet.
    """
    folder = build_assorted(tmp_path / "Desktop", 18)
    analysis = analyze_dir(folder, embedder=real_embedder)

    assert "no_common_thread" in codes(analysis)
    assert analysis.verdict >= Verdict.MESSY
    # It is not described as a few files standing out: it is all of them.
    assert "strays" not in codes(analysis)


def test_assorted_beats_merely_mixed(tmp_path, real_embedder):
    """Total incoherence must score above a folder holding three subjects."""
    mixed = build_mixed(tmp_path / "mixed", {OFFICE_TOPICS[0]: 6, DEV_TOPICS[0]: 6})
    assorted = build_assorted(tmp_path / "assorted", 14)

    mixed_score = analyze_dir(mixed, embedder=real_embedder).score
    assorted_score = analyze_dir(assorted, embedder=real_embedder).score
    assert assorted_score > mixed_score


def test_a_realistic_downloads_drawer(tmp_path, real_embedder):
    folder = tmp_path / "Downloads"
    add_topic(folder, OFFICE_TOPICS[1], 4)
    add_topic(folder, PERSONAL_TOPICS[0], 4)
    add_installers(folder)
    add_debris(folder)
    add_duplicates(folder)
    add_version_pileup(folder)
    build_album(folder, 6, prefix="IMG")

    analysis = analyze_dir(folder, embedder=real_embedder)
    found = codes(analysis)
    assert analysis.verdict >= Verdict.MESSY
    for expected in ("debris", "version_pileups", "duplicates"):
        assert expected in found, f"{expected} missing from {found}"


# --- restraint --------------------------------------------------------------


def test_photo_album_is_left_alone(tmp_path, real_embedder):
    folder = build_album(tmp_path / "Wedding", 30)
    assert analyze_dir(folder, embedder=real_embedder).verdict == Verdict.TIDY


def test_music_library_is_left_alone(tmp_path, real_embedder):
    folder = build_media_library(tmp_path / "Albums", 20)
    assert analyze_dir(folder, embedder=real_embedder).verdict < Verdict.MESSY


def test_one_subject_in_many_formats_is_not_a_mess(tmp_path, real_embedder):
    """A project folder holds code, config, data and notes. That is not mess."""
    folder = tmp_path / "project"
    topic = DEV_TOPICS[0]
    for index, (stem, text) in enumerate(TOPICS[topic]):
        ext = ["py", "md", "json", "yaml", "txt", "csv"][index % 6]
        write_file(folder / f"{stem}.{ext}", text)

    analysis = analyze_dir(folder, embedder=real_embedder)
    assert "unrelated_topics" not in codes(analysis)
    assert analysis.verdict < Verdict.MESSY


def test_a_big_folder_of_one_subject_is_left_alone(tmp_path, real_embedder):
    """Ninety documents on one subject: large, and not a mess.

    This used to assert ``overcrowded`` fired, back when size alone counted as
    evidence. It is the shape of a camera roll or a dataset directory, and on a
    real workspace that reading was wrong far more often than it was right, so
    the signal now has to be asked for.
    """
    from messie.config import DEFAULT_SETTINGS

    folder = build_coherent(tmp_path / "Scans", OFFICE_TOPICS[0], 90)
    analysis = analyze_dir(folder, embedder=real_embedder)
    assert codes(analysis) == set() or "overcrowded" not in codes(analysis)
    assert "unrelated_topics" not in codes(analysis)
    assert "no_common_thread" not in codes(analysis)

    # Asked for, it is still there and still says the true thing.
    asked = analyze_dir(
        folder, DEFAULT_SETTINGS.with_(report_crowding=True), embedder=real_embedder
    )
    assert "overcrowded" in codes(asked)


# --- formats ----------------------------------------------------------------

_TEXT_FORMATS = ["docx", "pptx", "xlsx", "odt", "epub", "pdf", "rtf", "ipynb", "srt",
                 "txt", "md", "csv", "json", "yaml", "py", "sql", "log"]


@pytest.mark.parametrize("ext", _TEXT_FORMATS)
def test_text_survives_a_round_trip_through_every_readable_format(ext, tmp_path):
    from messie.extract import extract_text
    from messie.scan import read_dir

    if ext == "pdf":
        pytest.importorskip("pypdf", reason="PDF text needs the pdf extra")

    body = (
        "Quarterly revenue for the northern region grew by eleven percent, driven "
        "by enterprise renewals while headcount costs rose only modestly."
    )
    write_file(tmp_path / f"revenue_report.{ext}", body)
    entry = next(f for f in read_dir(tmp_path).files if f.ext == ext.lower())
    assert "revenue" in extract_text(entry).lower()


_BINARY_FORMATS = {
    "jpg": "image", "png": "image", "heic": "image", "gif": "image",
    "mp3": "audio", "wav": "audio", "mp4": "video", "mov": "video",
    "ttf": "font", "exe": "installer", "dmg": "installer", "pkg": "installer",
    "deb": "installer", "iso": "disk_image", "zip": "archive",
    "sqlite": "database", "url": "shortcut",
}


@pytest.mark.parametrize(("ext", "kind"), sorted(_BINARY_FORMATS.items()))
def test_binary_formats_are_recognised_by_kind(ext, kind, tmp_path):
    from messie.scan import read_dir

    write_file(tmp_path / f"thing.{ext}", "")
    entry = next(f for f in read_dir(tmp_path).files if f.ext == ext)
    assert entry.kind == kind
    assert entry.size > 0


# --- the whole demo tree ----------------------------------------------------


def test_demo_tree(tmp_path, real_embedder):
    """The generator in scripts/ must produce a tree with a sensible verdict spread."""
    import sys

    sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))
    from build_demo_tree import build

    from messie.analyze import analyze_tree

    root = build(tmp_path / "home")
    results = {str(a.path.relative_to(root)): a for a in analyze_tree(root, embedder=real_embedder)}

    assert results["Desktop"].verdict >= Verdict.MESSY
    assert results["Downloads"].verdict >= Verdict.MESSY
    assert results["Pictures/Wedding"].verdict == Verdict.TIDY
    assert results["Work/Invoices"].verdict < Verdict.MESSY
    assert results["Projects/ledger-api"].verdict < Verdict.MESSY
