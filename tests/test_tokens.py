"""Filename tokenisation and revision-marker detection."""

from __future__ import annotations

import pytest

from messie.tokens import base_stem, name_phrase, name_tokens, version_markers


@pytest.mark.parametrize(
    ("stem", "expected"),
    [
        ("2023_Tax-Return_FINALv2", ["tax", "return"]),
        ("quarterlyRevenueReport", ["quarterly", "revenue", "report"]),
        ("IMG_4412", []),
        ("Screenshot 2024-01-03 at 11.42.55", []),
        ("holiday-photos-crete", ["holiday", "photos", "crete"]),
    ],
)
def test_name_tokens(stem, expected):
    assert name_tokens(stem) == expected


def test_name_phrase_reads_like_a_phrase():
    assert name_phrase("2023_tax_return_final") == "tax return"


@pytest.mark.parametrize(
    "stem", ["report", "report_final", "report_v2", "report final v2 (copy)", "REPORT-Final"]
)
def test_revisions_of_one_thing_share_a_base_stem(stem):
    assert base_stem(stem) == "report"


def test_numbered_series_is_not_a_revision_pile():
    # The thing that separates "tax_document_04" from "report_final_v2".
    assert version_markers("tax_document_04") == []
    assert version_markers("chapter_01") == []


@pytest.mark.parametrize(
    "stem", ["report_final", "notes - Copy", "budget (2)", "deck_v3", "plan_draft"]
)
def test_revision_markers_are_found(stem):
    assert version_markers(stem)


def test_generic_words_are_not_revision_markers():
    for stem in ("scanned_document", "downloaded_image", "export_file"):
        assert version_markers(stem) == []
