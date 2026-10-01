"""User exclusions should affect evidence, within their declared scope only."""

from __future__ import annotations

from pathlib import Path

import pytest
from conftest import codes, write_text

from messie.analyze import analyze_dir, analyze_tree
from messie.scan import read_dir, walk


def test_required_root_files_are_excluded_but_other_evidence_remains(
    tmp_path, fake_embedder
):
    root = tmp_path / "package"
    for i in range(6):
        write_text(root / f"alpha_{i}.txt", f"alpha topic {i} " * 30)
    write_text(root / "package.json", '{"name": "required metadata"}')
    write_text(root / "stray.txt", "unrelated content " * 30)
    (root / "ignore.messie").write_text("# Required by the package manager\npackage.json\n")

    assert {entry.name for entry in read_dir(root).files} == {
        *(f"alpha_{i}.txt" for i in range(6)), "stray.txt",
    }
    analysis = analyze_dir(root, embedder=fake_embedder)
    assert analysis.judged
    assert analysis.n_files == 7


def test_required_files_can_be_exempted_without_hiding_real_disorder(tmp_path, fake_embedder):
    root = tmp_path / "package"
    for i in range(6):
        write_text(root / f"alpha_{i}.txt", f"alpha topic {i} " * 30)
    required = (
        ("package.json", "beta"),
        ("package-lock.json", "beta"),
        ("tsconfig.json", "beta"),
        ("pyproject.toml", "gamma"),
        ("setup.cfg", "gamma"),
        ("MANIFEST.in", "gamma"),
    )
    for name, marker in required:
        write_text(root / name, f"{marker} manager metadata " * 30)

    assert "unrelated_topics" in codes(analyze_dir(root, embedder=fake_embedder))
    (root / "ignore.messie").write_text("\n".join(name for name, _ in required))
    exempted = analyze_dir(root, embedder=fake_embedder)
    assert exempted.n_files == 6
    assert "unrelated_topics" not in codes(exempted)

    for marker in ("beta", "gamma"):
        for i in range(3):
            write_text(root / f"{marker}_{i}.txt", f"{marker} unrelated content {i} " * 30)
    assert "unrelated_topics" in codes(analyze_dir(root, embedder=fake_embedder))


def test_rules_inherit_below_their_file_and_nested_rules_add_to_them(tmp_path):
    root = tmp_path / "project"
    (root / "ignore.messie").parent.mkdir()
    (root / "ignore.messie").write_text("*.lock\n")
    write_text(root / "root.lock", "lock")
    child = root / "module"
    (child / "ignore.messie").parent.mkdir()
    (child / "ignore.messie").write_text("generated/\n")
    write_text(child / "local.lock", "lock")
    write_text(child / "keep.py", "code")
    write_text(child / "generated" / "old.py", "generated")
    sibling = root / "sibling"
    write_text(sibling / "generated" / "keep.py", "code")

    folders = {folder.path.relative_to(root): folder for folder in walk(root)}
    assert {entry.name for entry in folders[child.relative_to(root)].files} == {"keep.py"}
    assert child / "generated" not in {folder.path for folder in folders.values()}
    assert sibling / "generated" in {folder.path for folder in folders.values()}
    assert not folders[Path(".")].files


def test_slash_patterns_are_relative_and_double_star_crosses_directories(tmp_path):
    root = tmp_path / "project"
    root.mkdir()
    (root / "ignore.messie").write_text("src/*/generated/\n**/cache.lock\n")
    write_text(root / "src" / "one" / "generated" / "old.py", "generated")
    write_text(root / "src" / "two" / "keep.py", "code")
    write_text(root / "src" / "two" / "cache.lock", "lock")
    write_text(root / "other" / "src" / "three" / "generated" / "keep.py", "code")

    folders = {folder.path: folder for folder in walk(root)}
    assert root / "src" / "one" / "generated" not in folders
    assert root / "other" / "src" / "three" / "generated" in folders
    assert {file.name for file in folders[root / "src" / "two"].files} == {"keep.py"}


def test_scanning_a_subtree_does_not_read_rules_above_it(tmp_path):
    root = tmp_path / "project"
    root.mkdir()
    (root / "ignore.messie").write_text("package.json\n")
    child = root / "module"
    write_text(child / "package.json", "required")

    assert not read_dir(child).ignore_rules
    assert [file.name for file in walk(child)[0].files] == ["package.json"]


def test_leading_slash_limits_a_rule_to_the_ignore_file_folder(tmp_path):
    root = tmp_path / "project"
    root.mkdir()
    (root / "ignore.messie").write_text("/package.json\n")
    write_text(root / "package.json", "required at root")
    write_text(root / "module" / "package.json", "still considered")

    folders = {folder.path: folder for folder in walk(root)}
    assert not folders[root].files
    assert [file.name for file in folders[root / "module"].files] == ["package.json"]


def test_invalid_ignore_file_is_reported_instead_of_silently_dropped(tmp_path):
    (tmp_path / "ignore.messie").write_bytes(b"\xff")
    with pytest.raises(OSError, match="must be UTF-8 text"):
        walk(tmp_path)


def test_tree_analysis_uses_ignored_evidence_consistently(tmp_path, fake_embedder):
    root = tmp_path / "project"
    for i in range(6):
        write_text(root / "module" / f"alpha_{i}.txt", f"alpha topic {i} " * 30)
    write_text(root / "module" / "package.json", '{"name": "required"}')
    (root / "ignore.messie").write_text("package.json\n")

    results = {item.path: item for item in analyze_tree(root, embedder=fake_embedder)}
    assert results[root / "module"].n_files == 6
    assert results[root / "module"].judged
