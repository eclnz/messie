"""Whole-pipeline behaviour against the real embedding backends.

The first test here is the one that matters: the case the tool was built for.
"""

from __future__ import annotations

import pytest
from conftest import snapshot, write_blob, write_docx

from messie.analyze import analyze_dir, analyze_tree
from messie.embed import BackendUnavailable, get_embedder
from messie.score import Verdict

BACKENDS = ["lexical", "wordllama"]


def backend_or_skip(name):
    try:
        return get_embedder(name)
    except (BackendUnavailable, Exception) as exc:  # noqa: BLE001
        pytest.skip(f"{name} unavailable: {exc}")


@pytest.fixture(params=BACKENDS)
def real_embedder(request):
    return backend_or_skip(request.param)


def test_uniform_file_type_unrelated_contents_is_a_mess(mixed_docx_dir, real_embedder):
    """A folder of Word documents about three different things is messy.

    Nothing about the file listing gives this away — every file is a .docx.
    Only the contents do.
    """
    analysis = analyze_dir(mixed_docx_dir, embedder=real_embedder)

    assert {f.ext for f in analysis.files} == {"docx"}, "the premise: one file type"
    assert analysis.verdict >= Verdict.MESSY
    topics = next(f for f in analysis.findings if f.code == "unrelated_topics")
    assert len(topics.data["groups"]) >= 2

    # The novel and the tax paperwork must not be judged the same subject.
    # (How finely the rest divides is the model's call: a semantic backend may
    # reasonably file invoices and tax returns together as money paperwork.)
    def group_of(name: str) -> int:
        index = next(i for i, f in enumerate(analysis.files) if f.name == name)
        return int(analysis.clustering.labels[index])

    assert group_of("chapter_01.docx") != group_of("tax_return_2019.docx")


def test_uniform_file_type_coherent_contents_is_tidy(coherent_docx_dir, real_embedder):
    analysis = analyze_dir(coherent_docx_dir, embedder=real_embedder)

    assert analysis.verdict == Verdict.TIDY
    assert analysis.findings == []
    assert analysis.clustering.n_clusters == 1


def test_photo_album_is_tidy(tmp_path, real_embedder):
    """Opaque filenames and unreadable contents must not read as mess."""
    folder = tmp_path / "Wedding Photos"
    for i in range(16):
        write_blob(folder / f"DSC_{1000 + i}.jpg", 4000 + i)
    analysis = analyze_dir(folder, embedder=real_embedder)
    assert analysis.verdict == Verdict.TIDY


def test_analysis_never_touches_the_filesystem(mixed_docx_dir, real_embedder):
    """The core promise: messie reports, it does not tidy."""
    before = snapshot(mixed_docx_dir)
    analyze_dir(mixed_docx_dir, embedder=real_embedder)
    assert snapshot(mixed_docx_dir) == before


def test_tree_walk_judges_each_folder_separately(tmp_path, real_embedder):
    from conftest import INVOICE, NOVEL, TAX

    root = tmp_path / "home"
    for i, line in enumerate(TAX):
        write_docx(root / "Taxes" / f"return_{i}.docx", [line] * 4)
    for i, line in enumerate(NOVEL):
        write_docx(root / "Taxes" / f"extra_{i}.docx", [line] * 4)
    for i, line in enumerate(INVOICE):
        write_docx(root / "Drawer" / f"invoice_{1040 + i}.docx", [line] * 4)
    for i, line in enumerate(NOVEL):
        write_docx(root / "Drawer" / f"chapter_{i + 1:02d}.docx", [line] * 4)
    for i, line in enumerate(TAX):
        write_docx(root / "Drawer" / f"tax_return_{2019 + i}.docx", [line] * 4)

    results = {a.path.name: a for a in analyze_tree(root, embedder=real_embedder)}
    assert results["Drawer"].verdict >= Verdict.MESSY
    assert results["Drawer"].score >= results["Taxes"].score


def test_results_are_stable_across_runs(mixed_docx_dir, real_embedder):
    first = analyze_dir(mixed_docx_dir, embedder=real_embedder)
    second = analyze_dir(mixed_docx_dir, embedder=real_embedder)
    assert first.score == second.score
    assert [f.code for f in first.findings] == [f.code for f in second.findings]


def test_empty_folder_is_not_judged(tmp_path, real_embedder):
    folder = tmp_path / "empty"
    folder.mkdir()
    analysis = analyze_dir(folder, embedder=real_embedder)
    assert not analysis.judged
    assert analysis.score == 0.0


def test_unreadable_folder_does_not_crash(tmp_path, real_embedder):
    folder = tmp_path / "locked"
    folder.mkdir()
    (folder / "a.txt").write_text("alpha")
    folder.chmod(0o000)
    try:
        analysis = analyze_dir(folder, embedder=real_embedder)
        assert not analysis.judged
    finally:
        folder.chmod(0o755)


def test_a_shared_filename_prefix_does_not_hide_the_mess(tmp_path, real_embedder):
    """Everything named with the same project prefix, on unrelated subjects.

    A word in nearly every filename lifts every pairwise similarity at once. If
    it were left in, three separate subjects would read as one.
    """
    from conftest import INVOICE, NOVEL, TAX

    folder = tmp_path / "ProjectX"
    for group, lines in (("a", INVOICE), ("b", NOVEL), ("c", TAX)):
        for i, line in enumerate(lines):
            write_docx(folder / f"ProjectX_2024_{group}{i}.docx", [line] * 4)

    analysis = analyze_dir(folder, embedder=real_embedder)
    assert analysis.verdict >= Verdict.MESSY
