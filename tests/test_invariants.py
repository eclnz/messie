"""What must hold for any folder at all.

The tests elsewhere check that messie is right about folders somebody designed.
These check that it is well-behaved about folders nobody designed: that it
never crashes, never contradicts itself, never disagrees with itself between
two runs, and never touches a byte.

Folders here are composed at random from every builder available, so the shapes
are ones no one thought to write a test for.
"""

from __future__ import annotations

import os
import random
import stat
from pathlib import Path

import pytest
from conftest import snapshot
from corpus import ALL_TOPICS
from corpus.build import (
    add_debris,
    add_duplicates,
    add_installers,
    add_topic,
    add_version_pileup,
    build_album,
    build_assorted,
    build_media_library,
)
from corpus.synth import write_empty, write_file, write_plain

from messie.analyze import analyze_dir, analyze_tree
from messie.cache import Cache
from messie.embed import get_embedder
from messie.score import Verdict, verdict_for

FUZZ_FOLDERS = 12


@pytest.fixture(scope="module")
def embedder():
    try:
        return get_embedder("wordllama")
    except Exception as exc:  # noqa: BLE001
        pytest.skip(f"wordllama unavailable: {exc}")


def _compose(folder: Path, seed: int) -> Path:
    """A folder of whatever this seed happens to produce."""
    rng = random.Random(seed)
    folder.mkdir(parents=True, exist_ok=True)
    for _ in range(rng.randrange(1, 4)):
        move = rng.choice(("topic", "topic", "album", "media", "assorted", "debris",
                           "duplicates", "installers", "pileup"))
        if move == "topic":
            add_topic(folder, rng.choice(ALL_TOPICS), rng.randrange(1, 9), seed=seed)
        elif move == "album":
            build_album(folder, rng.randrange(1, 12), seed=seed)
        elif move == "media":
            build_media_library(folder, rng.randrange(1, 10), seed=seed)
        elif move == "assorted":
            build_assorted(folder, rng.randrange(2, 14), seed=seed)
        elif move == "debris":
            add_debris(folder, seed=seed)
        elif move == "duplicates":
            add_duplicates(folder, rng.randrange(2, 4))
        elif move == "installers":
            add_installers(folder, seed=seed)
        else:
            add_version_pileup(folder)
    return folder


@pytest.mark.parametrize("seed", range(FUZZ_FOLDERS))
def test_any_folder_yields_a_coherent_verdict(seed, tmp_path, embedder):
    analysis = analyze_dir(_compose(tmp_path / f"fuzz_{seed}", seed), embedder=embedder)

    assert 0.0 <= analysis.score <= 100.0
    assert analysis.verdict == verdict_for(analysis.score)
    assert analysis.failed_signals == []
    for finding in analysis.findings:
        assert 0.0 <= finding.severity <= 1.0
        assert finding.headline


@pytest.mark.parametrize("seed", range(FUZZ_FOLDERS))
def test_any_folder_is_judged_identically_twice(seed, tmp_path, embedder):
    folder = _compose(tmp_path / f"fuzz_{seed}", seed)
    first = analyze_dir(folder, embedder=embedder)
    second = analyze_dir(folder, embedder=embedder)
    assert first.score == second.score
    assert [f.code for f in first.findings] == [f.code for f in second.findings]


@pytest.mark.parametrize("seed", range(4))
def test_the_cache_changes_nothing_but_speed(seed, tmp_path, embedder):
    folder = _compose(tmp_path / f"fuzz_{seed}", seed)
    cold = analyze_dir(folder, embedder=embedder, cache=Cache(enabled=False))
    cache = Cache(tmp_path / "cache.sqlite", enabled=True)
    try:
        warm = analyze_dir(folder, embedder=embedder, cache=cache)
        again = analyze_dir(folder, embedder=embedder, cache=cache)
    finally:
        cache.close()
    assert cold.score == warm.score == again.score


@pytest.mark.parametrize("seed", range(FUZZ_FOLDERS))
def test_analysis_never_writes(seed, tmp_path, embedder):
    folder = _compose(tmp_path / f"fuzz_{seed}", seed)
    before = snapshot(folder)
    analyze_dir(folder, embedder=embedder)
    assert snapshot(folder) == before


# --- shapes nobody would think to write a test for --------------------------


def test_empty_folder(tmp_path, embedder):
    (tmp_path / "empty").mkdir()
    analysis = analyze_dir(tmp_path / "empty", embedder=embedder)
    assert not analysis.judged
    assert analysis.score == 0.0


def test_single_file(tmp_path, embedder):
    write_plain(tmp_path / "one" / "note.txt", "a single solitary note about nothing")
    assert not analyze_dir(tmp_path / "one", embedder=embedder).judged


def test_every_file_identical(tmp_path, embedder):
    folder = tmp_path / "same"
    for i in range(10):
        write_plain(folder / f"copy_{i}.txt", "the very same words in every single file here")
    analysis = analyze_dir(folder, embedder=embedder)
    assert 0.0 <= analysis.score <= 100.0
    assert analysis.failed_signals == []


def test_nothing_but_debris(tmp_path, embedder):
    folder = tmp_path / "junk"
    folder.mkdir()
    add_debris(folder)
    add_debris(folder, seed=2)
    analysis = analyze_dir(folder, embedder=embedder)
    assert analysis.failed_signals == []


@pytest.mark.parametrize(
    "name",
    [
        "🎉 party photos 2024.txt",
        "مستند مهم.txt",
        "файл заметки.txt",
        "no_extension_at_all",
        "spaces   and...dots.....txt",
        "x" * 200 + ".txt",
    ],
)
def test_awkward_filenames(name, tmp_path, embedder):
    folder = tmp_path / "awkward"
    folder.mkdir(exist_ok=True)
    for i in range(6):
        write_plain(folder / f"filler_{i}.txt", f"ordinary filler number {i} " * 8)
    try:
        write_plain(folder / name, "content behind an awkward name " * 6)
    except OSError:
        pytest.skip(f"filesystem refused {name[:24]!r}")
    analysis = analyze_dir(folder, embedder=embedder)
    assert analysis.failed_signals == []
    assert 0.0 <= analysis.score <= 100.0


def test_broken_symlink(tmp_path, embedder):
    folder = tmp_path / "links"
    folder.mkdir()
    for i in range(6):
        write_plain(folder / f"real_{i}.txt", f"a real file number {i} " * 9)
    (folder / "dangling.txt").symlink_to(folder / "does_not_exist.txt")
    analysis = analyze_dir(folder, embedder=embedder)
    assert analysis.failed_signals == []


def test_unreadable_file_among_readable_ones(tmp_path, embedder):
    folder = tmp_path / "locked"
    folder.mkdir()
    for i in range(6):
        write_plain(folder / f"open_{i}.txt", f"a readable file number {i} " * 9)
    secret = write_plain(folder / "secret.txt", "cannot be read " * 9)
    secret.chmod(0)
    try:
        analysis = analyze_dir(folder, embedder=embedder)
        assert analysis.failed_signals == []
        assert 0.0 <= analysis.score <= 100.0
    finally:
        secret.chmod(stat.S_IRUSR | stat.S_IWUSR)


def test_zero_byte_files_only(tmp_path, embedder):
    folder = tmp_path / "hollow"
    for i in range(8):
        write_empty(folder / f"blank_{i}.txt")
    analysis = analyze_dir(folder, embedder=embedder)
    assert analysis.failed_signals == []


def test_a_deep_tree_is_walked_without_incident(tmp_path, embedder):
    root = tmp_path / "deep"
    here = root
    for level in range(5):
        here = here / f"level_{level}"
        add_topic(here, ALL_TOPICS[level % len(ALL_TOPICS)], 6, seed=level)
    results = analyze_tree(root, embedder=embedder)
    assert results
    for analysis in results:
        assert analysis.failed_signals == []
        assert 0.0 <= analysis.score <= 100.0


def test_a_directory_that_looks_like_a_file(tmp_path, embedder):
    folder = tmp_path / "odd"
    folder.mkdir()
    (folder / "report.docx").mkdir()
    for i in range(6):
        write_file(folder / f"note_{i}.txt", f"ordinary note number {i} " * 9)
    analysis = analyze_dir(folder, embedder=embedder)
    assert analysis.failed_signals == []


def test_symlinked_loop_does_not_hang(tmp_path, embedder):
    root = tmp_path / "loop"
    add_topic(root, ALL_TOPICS[0], 6)
    try:
        (root / "self").symlink_to(root, target_is_directory=True)
    except OSError:
        pytest.skip("symlinks unavailable")
    results = analyze_tree(root, embedder=embedder)
    assert results
    assert all(a.failed_signals == [] for a in results)


def test_verdict_bands_are_total():
    """Every score lands in exactly one band."""
    for score in range(0, 101):
        assert isinstance(verdict_for(float(score)), Verdict)
    assert verdict_for(0.0) == Verdict.TIDY
    assert verdict_for(100.0) == Verdict.CHAOTIC


def test_permission_denied_directory_is_skipped(tmp_path, embedder):
    root = tmp_path / "guarded"
    add_topic(root, ALL_TOPICS[0], 6)
    blocked = root / "private"
    add_topic(blocked, ALL_TOPICS[1], 6, seed=3)
    blocked.chmod(0)
    try:
        results = analyze_tree(root, embedder=embedder)
        assert results
        assert all(a.failed_signals == [] for a in results)
    finally:
        blocked.chmod(stat.S_IRWXU)


def test_os_walk_is_not_confused_by_a_file_named_like_a_directory(tmp_path, embedder):
    folder = tmp_path / "names"
    add_topic(folder, ALL_TOPICS[2], 6)
    write_plain(folder / "subfolder", "a file with no extension named like a folder " * 4)
    assert analyze_dir(folder, embedder=embedder).failed_signals == []


def test_analysis_of_the_repo_itself(embedder):
    """messie on its own source: the most convenient real folder there is."""
    here = Path(__file__).resolve().parent.parent / "src" / "messie"
    if not here.is_dir():
        pytest.skip("source tree not present")
    analysis = analyze_dir(here, embedder=embedder)
    assert analysis.failed_signals == []
    assert os.path.isdir(here)
