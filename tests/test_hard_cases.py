"""Regression cases beyond the fixture corpus."""

from __future__ import annotations

import pytest
from conftest import codes, embedder_or_skip, finding
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
from messie.result import Verdict
from messie.tokens import base_stem, name_tokens


@pytest.fixture(scope="module")
def embedder():
    return embedder_or_skip()


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
    assert name_tokens(stem) == expected


def test_accents_do_not_break_version_grouping():
    assert base_stem("résumé_final_v2") == base_stem("résumé") == "résumé"


@pytest.mark.parametrize("topic", ACCENTED_TOPICS)
def test_an_accented_subject_reads_as_one_thing(topic, tmp_path, embedder):
    folder = build_coherent(tmp_path / topic, topic, 6)
    analysis = analyze_dir(folder, embedder=embedder)
    assert analysis.meaningful_clusters == 1
    assert analysis.verdict < Verdict.MESSY


def test_accented_and_plain_subjects_are_told_apart(tmp_path, embedder):
    folder = build_mixed(
        tmp_path / "drawer",
        {ACCENTED_TOPICS[0]: 5, ACCENTED_TOPICS[1]: 5, DEV_TOPICS[0]: 5},
    )
    analysis = analyze_dir(folder, embedder=embedder)
    assert "unrelated_topics" in codes(analysis)
    assert analysis.verdict >= Verdict.MESSY


def test_the_same_document_in_several_formats_is_noticed(tmp_path, embedder):
    folder = tmp_path / "formats"
    add_topic(folder, OFFICE_TOPICS[0], 6)
    add_same_document_in_many_formats(folder, PERSONAL_TOPICS[0])

    analysis = analyze_dir(folder, embedder=embedder)
    assert "duplicates" in codes(analysis)


def test_rtf_text_carries_no_font_table(tmp_path):
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


def test_loose_files_matching_a_deep_folder_are_found(tmp_path, embedder):
    root = build_nested_misfile(tmp_path / "home", OFFICE_TOPICS[0], PERSONAL_TOPICS[1])
    analysis = analyze_dir(root, embedder=embedder)

    assert "misfiled_neighbours" in codes(analysis)
    named = finding(analysis, "misfiled_neighbours").data["by_subdir"]
    assert any("/" in where for where in named), f"expected a deep path, got {list(named)}"


def test_a_folder_of_one_line_notes_is_left_alone(tmp_path, embedder):
    folder = tmp_path / "notes"
    add_short_notes(folder, ACCENTED_TOPICS[1], 8)
    analysis = analyze_dir(folder, embedder=embedder)

    assert "no_common_thread" not in codes(analysis)
    assert "strays" not in codes(analysis)
    assert analysis.verdict < Verdict.MESSY


def test_unrelated_one_line_notes_are_a_known_blind_spot(tmp_path, embedder):
    """Sparse unrelated notes are intentionally inconclusive."""
    folder = tmp_path / "notes"
    add_short_notes(folder, ACCENTED_TOPICS[1], 6, seed=1)
    add_short_notes(folder, DEV_TOPICS[2], 6, seed=2)
    assert analyze_dir(folder, embedder=embedder).verdict < Verdict.MESSY


def test_named_photographs_are_a_known_blind_spot(tmp_path, embedder):
    """Named photographs alone are intentionally inconclusive."""
    folder = tmp_path / "Pictures"
    build_named_album(folder, PERSONAL_TOPICS[2], 8, seed=1)
    build_named_album(folder, DEV_TOPICS[0], 8, seed=2)
    assert analyze_dir(folder, embedder=embedder).verdict < Verdict.MESSY


def test_named_photographs_of_one_subject_are_tidy(tmp_path, embedder):
    folder = build_named_album(tmp_path / "Crete", PERSONAL_TOPICS[2], 12)
    assert analyze_dir(folder, embedder=embedder).verdict == Verdict.TIDY
