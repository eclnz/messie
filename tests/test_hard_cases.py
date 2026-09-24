"""Cases the corpus could not express until now.

Each of these was untested territory, and between them they turned up an
ASCII tokeniser that shredded accented words, a cliff between two signals that
were meant to hand off to each other, an RTF extractor leaking font names into
every document's text, and a misfiled-file signal that could not see past the
immediate children of a folder.

Some of them record a blind spot rather than a capability. A limit written
down as a passing test is a limit somebody can find; a limit left in a
docstring is one they discover the hard way.
"""

from __future__ import annotations

import pytest
from conftest import backend_or_skip, codes, finding
from corpus import ACCENTED_TOPICS, DEV_TOPICS, OFFICE_TOPICS, PERSONAL_TOPICS
from corpus.build import (
    add_same_document_in_many_formats,
    add_short_notes,
    add_topic,
    build_coherent,
    build_mixed,
    build_named_album,
    build_nested_misfile,
)

from messie.analyze import analyze_dir
from messie.score import Verdict
from messie.tokens import base_stem, name_tokens

BACKEND = "wordllama"


@pytest.fixture(scope="module")
def embedder():
    return backend_or_skip(BACKEND)



# --- accented English -------------------------------------------------------


@pytest.mark.parametrize(
    ("stem", "expected"),
    [
        ("café receipts", ["café", "receipts"]),
        ("Zürich trip notes", ["zürich", "trip", "notes"]),
        ("résumé_final_v2", ["résumé"]),
        ("naïve bayes notes", ["naïve", "bayes", "notes"]),
        ("Déclaration_revenus_2023", ["déclaration", "revenus"]),
        ("Łódź photos", ["łódź", "photos"]),
    ],
)
def test_accented_words_survive_tokenising(stem, expected):
    """An ASCII split treated every diacritic as a separator, and quietly
    destroyed the word around it: ``café`` became ``caf``."""
    assert name_tokens(stem) == expected


def test_accents_do_not_break_version_grouping():
    assert base_stem("résumé_final_v2") == base_stem("résumé") == "résumé"


@pytest.mark.parametrize("topic", ACCENTED_TOPICS)
def test_an_accented_subject_reads_as_one_thing(topic, tmp_path, embedder):
    folder = build_coherent(tmp_path / topic, topic, 6)
    analysis = analyze_dir(folder, embedder=embedder)
    assert analysis.clustering is not None
    assert analysis.clustering.n_clusters == 1
    assert analysis.verdict < Verdict.MESSY


def test_accented_and_plain_subjects_are_told_apart(tmp_path, embedder):
    folder = build_mixed(
        tmp_path / "drawer",
        {ACCENTED_TOPICS[0]: 5, ACCENTED_TOPICS[1]: 5, DEV_TOPICS[0]: 5},
    )
    analysis = analyze_dir(folder, embedder=embedder)
    assert "unrelated_topics" in codes(analysis)
    assert analysis.verdict >= Verdict.MESSY


# --- one document, many formats ---------------------------------------------


def test_the_same_document_in_several_formats_is_noticed(tmp_path, embedder):
    """The .docx somebody wrote, the .pdf they sent, the .txt somebody pasted."""
    folder = tmp_path / "formats"
    add_topic(folder, OFFICE_TOPICS[0], 6)
    add_same_document_in_many_formats(folder, PERSONAL_TOPICS[0])

    analysis = analyze_dir(folder, embedder=embedder)
    assert "duplicates" in codes(analysis)


def test_rtf_text_carries_no_font_table(tmp_path):
    """Stripping RTF control words alone leaves the font *names* behind, so
    every document's text began with "Helvetica;" or "Times New Roman;"."""
    from messie.extract import extract_text
    from messie.scan import read_dir

    body = (
        r"{\rtf1\ansi\deff0{\fonttbl{\f0\fnil Calibri;}{\f1\fnil Times New Roman;}}"
        r"{\colortbl ;\red255\green0\blue0;}{\*\generator Riched20 10.0;}"
        r"\pard\f0\fs22 Quarterly revenue for the northern region grew.\par}"
    )
    (tmp_path / "memo.rtf").write_text(body, encoding="ascii")
    entry = next(f for f in read_dir(tmp_path).files if f.ext == "rtf")
    text = extract_text(entry)

    assert "Quarterly revenue" in text
    for machinery in ("Calibri", "Times New Roman", "Riched20", "fonttbl"):
        assert machinery not in text


# --- filed away several levels down -----------------------------------------


def test_loose_files_matching_a_deep_folder_are_found(tmp_path, embedder):
    """misfiled_neighbours compared a folder only against its direct children,
    so a subject filed three levels down was invisible."""
    root = build_nested_misfile(tmp_path / "home", OFFICE_TOPICS[0], PERSONAL_TOPICS[1])
    analysis = analyze_dir(root, embedder=embedder)

    assert "misfiled_neighbours" in codes(analysis)
    named = finding(analysis, "misfiled_neighbours").data["by_subdir"]
    assert any("/" in where for where in named), f"expected a deep path, got {list(named)}"


# --- what we cannot see, recorded as such -----------------------------------


def test_a_folder_of_one_line_notes_is_left_alone(tmp_path, embedder):
    """Short notes do not cluster, and that absence is not evidence of mess.

    Before files this thin were excluded from the reckoning, a folder of eight
    jotted notes on a single subject scored 39 and was called lived-in.
    """
    folder = tmp_path / "notes"
    add_short_notes(folder, ACCENTED_TOPICS[1], 8)
    analysis = analyze_dir(folder, embedder=embedder)

    assert "no_common_thread" not in codes(analysis)
    assert "strays" not in codes(analysis)
    assert analysis.verdict < Verdict.MESSY


def test_unrelated_one_line_notes_are_a_known_blind_spot(tmp_path, embedder):
    """The other side of that coin, and the price of not crying wolf.

    Two unrelated subjects written as one-liners cannot be told apart from one
    subject written as one-liners, because there is too little to read either
    way. messie says nothing rather than guessing.
    """
    folder = tmp_path / "notes"
    add_short_notes(folder, ACCENTED_TOPICS[1], 6, seed=1)
    add_short_notes(folder, DEV_TOPICS[2], 6, seed=2)
    assert analyze_dir(folder, embedder=embedder).verdict < Verdict.MESSY


def test_named_photographs_are_a_known_blind_spot(tmp_path, embedder):
    """Photographs are judged by their names, and names are thin evidence.

    A folder of pictures from two unrelated occasions does not read as mess,
    because there is no way to read a photograph. Flagging it would mean
    flagging every album, which is the worse error.
    """
    folder = tmp_path / "Pictures"
    build_named_album(folder, PERSONAL_TOPICS[2], 8, seed=1)
    build_named_album(folder, DEV_TOPICS[0], 8, seed=2)
    assert analyze_dir(folder, embedder=embedder).verdict < Verdict.MESSY


def test_named_photographs_of_one_subject_are_tidy(tmp_path, embedder):
    folder = build_named_album(tmp_path / "Crete", PERSONAL_TOPICS[2], 12)
    assert analyze_dir(folder, embedder=embedder).verdict == Verdict.TIDY
