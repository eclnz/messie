"""Telling garbled files from merely unusual ones.

The hard part is not spotting nonsense; it is not crying nonsense at the many
legitimate files that do not look like prose. Most of what follows guards
against false positives, because that is where the risk lies.
"""

from __future__ import annotations

import pytest
from corpus import ALL_TOPICS, TOPICS
from corpus.build import add_garbled, add_topic, build_coherent
from corpus.synth import GARBLE_FLAVOURS, garbled_text, write_file

from messie.analyze import analyze_dir
from messie.extract import extract_text
from messie.legibility import FLOOR, assess, is_prose, legibility, looks_structured
from messie.scan import read_dir

# Legitimate content that does not read like English prose.
LEGITIMATE = {
    "chinese prose": (
        "这是一个关于季度收入报告的文件。北方地区的收入增长了百分之十一，"
        "主要得益于企业续约。利润率保持稳定，而人力成本仅略有上升。" * 3,
        "document", "docx",
    ),
    "arabic prose": (
        "هذا تقرير عن الإيرادات الفصلية للمنطقة الشمالية. ارتفعت الإيرادات "
        "بنسبة أحد عشر بالمئة بفضل تجديد عقود الشركات." * 3,
        "document", "docx",
    ),
    "french accented": (
        "Rapport trimestriel sur les recettes de la région nord. Les recettes "
        "ont augmenté de onze pour cent grâce aux renouvellements d'entreprise. "
        "Les marges sont restées stables malgré la hausse des coûts." * 3,
        "document", "docx",
    ),
    "source code": (
        "def compute_totals(rows, rate):\n    subtotal = sum(r.amount for r in rows)\n"
        "    return subtotal * (1 + rate)\n" * 8,
        "code", "py",
    ),
    "minified javascript": (
        '!function(e,t){"object"==typeof exports?module.exports=t():e.z=t()}'
        "(this,function(){var n=[],r={};return function e(t){return r[t]||n[t]}});" * 4,
        "code", "js",
    ),
    "server log with hashes": (
        "2026-03-04T11:22:31Z INFO req=9f2c1ab4d3e5 user=4412 path=/api/orders 200 14ms\n" * 12,
        "text", "log",
    ),
    "csv of numbers": ("sku,units,revenue\nA-1044,312,18422.50\nA-1045,87,5120.00\n" * 10,
                       "data", "csv"),
    "csv saved as txt": ("sku,units,revenue\nA-1044,312,18422.50\nA-1045,87,5120.00\n" * 10,
                         "text", "txt"),
    "settings dump as txt": ("timeout = 30\nretries = 5\nhost = cache.internal\n" * 8,
                             "text", "txt"),
    "list of urls": (
        "\n".join(
            f"https://example.invalid/articles/2026/03/{i:04d}/a-fairly-long-slug-here"
            for i in range(30)
        ),
        "text", "txt",
    ),
}


# --- it must not cry wolf ---------------------------------------------------


@pytest.mark.parametrize("name", sorted(LEGITIMATE))
def test_legitimate_but_unusual_files_are_not_called_garbled(name):
    text, kind, ext = LEGITIMATE[name]
    verdict = assess(text, kind, ext)
    assert not verdict.garbled, f"{name} was called garbled: {verdict.reason}"


@pytest.mark.parametrize("topic", ALL_TOPICS)
def test_every_real_document_is_legible(topic, tmp_path):
    """Across the whole example corpus, nothing may read as nonsense."""
    folder = build_coherent(tmp_path / topic, topic, 6)
    for entry in read_dir(folder).files:
        verdict = assess(extract_text(entry), entry.kind, entry.ext)
        assert not verdict.garbled, f"{entry.name} flagged: {verdict.reason}"


def test_short_files_are_not_judged():
    assert not assess("Notes.", "text", "txt").garbled
    assert assess("", "text", "txt").score == 1.0


def test_structured_data_is_recognised():
    assert looks_structured("a,b,c\n1,2,3\n4,5,6\n7,8,9\n")
    assert looks_structured("host = one\nport = two\nuser = three\nmode = four\n")
    assert not looks_structured("This is an ordinary paragraph of prose, with commas, "
                                "and it should not be mistaken for a table.")


def test_prose_routing():
    assert is_prose("document", "docx")
    assert is_prose("text", "txt")
    assert is_prose("pdf", "pdf")
    assert not is_prose("text", "log")
    assert not is_prose("code", "py")
    assert not is_prose("data", "csv")


# --- and it must catch the real thing ---------------------------------------


@pytest.mark.parametrize("flavour", sorted(GARBLE_FLAVOURS))
def test_each_flavour_of_nonsense_is_caught(flavour):
    verdict = assess(garbled_text(flavour, "seed"), "text", "txt")
    assert verdict.garbled, f"{flavour} scored {verdict.score}"
    assert verdict.reason


def test_a_reason_is_given_only_when_garbled():
    assert assess("A perfectly ordinary sentence about quarterly revenue. " * 4,
                  "document", "docx").reason == ""


def test_the_floor_is_configurable():
    text = garbled_text("ocr", "s")
    assert assess(text, "text", "txt", floor=0.0).garbled is False
    assert assess(text, "text", "txt", floor=1.0).garbled is True


def test_score_is_bounded():
    for name, (text, kind, ext) in LEGITIMATE.items():
        assert 0.0 <= assess(text, kind, ext).score <= 1.0, name


def test_non_prose_kinds_skip_word_shape():
    """The same nonsense is judged differently depending on what it claims to be."""
    letters = garbled_text("random letters", "s")
    assert legibility(letters, prose=True).garbled
    assert not legibility(letters, prose=False).garbled


# --- through the whole pipeline ---------------------------------------------


def test_garbled_files_are_reported(tmp_path, embedder):
    folder = tmp_path / "Scans"
    add_topic(folder, ALL_TOPICS[0], 6)
    add_garbled(folder, 6)

    analysis = analyze_dir(folder, embedder=embedder)
    finding = next(f for f in analysis.findings if f.code == "garbled")
    assert finding.data["count"] == 6
    assert len(finding.data["reasons"]) >= 2


def test_garbled_files_do_not_become_a_topic(tmp_path, embedder):
    """Nonsense left in the clustering would group together and pose as a subject."""
    folder = tmp_path / "Scans"
    add_topic(folder, ALL_TOPICS[0], 6)
    add_garbled(folder, 6)

    analysis = analyze_dir(folder, embedder=embedder)
    assert analysis.clustering.n_clusters == 1, "the six real documents, and nothing else"
    assert "unrelated_topics" not in {f.code for f in analysis.findings}


def test_one_odd_file_is_not_a_finding(tmp_path, embedder):
    folder = tmp_path / "Docs"
    add_topic(folder, ALL_TOPICS[0], 6)
    add_garbled(folder, 1)
    analysis = analyze_dir(folder, embedder=embedder)
    assert "garbled" not in {f.code for f in analysis.findings}


def test_a_folder_of_pure_nonsense(tmp_path, embedder):
    folder = tmp_path / "Recovered"
    add_garbled(folder, 8)
    analysis = analyze_dir(folder, embedder=embedder)

    from messie.score import Verdict

    assert "garbled" in {f.code for f in analysis.findings}
    assert analysis.verdict >= Verdict.MESSY


def test_a_folder_of_real_files_reports_nothing_garbled(tmp_path, embedder):
    folder = build_coherent(tmp_path / "Tax", ALL_TOPICS[0], 8)
    analysis = analyze_dir(folder, embedder=embedder)
    assert "garbled" not in {f.code for f in analysis.findings}


def test_mojibake_survives_a_docx_round_trip(tmp_path, embedder):
    """The damage has to be detectable after extraction, not just in a string."""
    write_file(tmp_path / "exported notes.docx", garbled_text("mojibake", "s"))
    for stem, text in TOPICS[ALL_TOPICS[0]]:
        write_file(tmp_path / f"{stem}.docx", text)

    entry = next(f for f in read_dir(tmp_path).files if f.name == "exported notes.docx")
    assert assess(extract_text(entry), entry.kind, entry.ext).garbled


def test_floor_constant_matches_settings():
    from messie.config import DEFAULT_SETTINGS

    assert DEFAULT_SETTINGS.legibility_floor == FLOOR
