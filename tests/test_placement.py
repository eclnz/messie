"""Optional placement analysis compares subtrees without relying on names."""

from __future__ import annotations

import json

from conftest import write_text

from messie.analyze import analyze_tree
from messie.cli import main
from messie.config import DEFAULT_SETTINGS
from messie.placement import PlacementEvidence


def _files(folder, topic, count=6):
    for index in range(count):
        write_text(folder / f"item_{index}.py", f"{topic} " * 30)


def _placement(results, path):
    analysis = next(item for item in results if item.path == path)
    finding = next(
        (finding for finding in analysis.findings if finding.code == "folder_placement"),
        None,
    )
    if finding is None:
        return None
    assert isinstance(finding.data, PlacementEvidence)
    return finding.data


def test_folder_mode_finds_a_coherent_misplaced_subtree(tmp_path, fake_embedder):
    root = tmp_path / "project"
    misplaced = root / "one" / "feature" / "nested"
    destination = root / "other"
    _files(root / "one" / "feature", "alpha")
    _files(root / "one" / "another", "gamma")
    _files(misplaced, "beta")
    _files(destination, "beta")

    normal = analyze_tree(root, embedder=fake_embedder)
    assert _placement(normal, misplaced) is None

    enabled = analyze_tree(
        root, DEFAULT_SETTINGS.with_(report_folder_placement=True), embedder=fake_embedder
    )
    evidence = _placement(enabled, misplaced)
    assert evidence is not None
    assert evidence.suggested_parent == destination
    assert evidence.supported_fraction >= 0.6


def test_folder_mode_preserves_multiple_topics(tmp_path, fake_embedder):
    root = tmp_path / "project"
    misplaced = root / "a" / "b"
    destination = root / "c"
    _files(root / "a", "alpha")
    _files(misplaced / "part1", "beta", 3)
    _files(misplaced / "part2", "gamma", 3)
    _files(destination / "part1", "beta", 3)
    _files(destination / "part2", "gamma", 3)

    results = analyze_tree(
        root, DEFAULT_SETTINGS.with_(report_folder_placement=True), embedder=fake_embedder
    )
    evidence = _placement(results, misplaced)
    assert evidence is not None
    assert evidence.suggested_parent == destination
    assert evidence.subtree_files == 6


def test_one_matching_topic_is_insufficient(tmp_path, fake_embedder):
    root = tmp_path / "project"
    candidate = root / "a" / "b"
    _files(root / "a", "alpha")
    _files(candidate, "beta", 3)
    _files(candidate / "different", "delta", 3)
    _files(root / "c", "beta")

    results = analyze_tree(
        root, DEFAULT_SETTINGS.with_(report_folder_placement=True), embedder=fake_embedder
    )
    assert _placement(results, candidate) is None


def test_no_alternative_means_no_placement_claim(tmp_path, fake_embedder):
    root = tmp_path / "project"
    candidate = root / "a" / "b"
    _files(root / "a", "alpha")
    _files(candidate, "beta")
    _files(root / "c", "gamma")

    results = analyze_tree(
        root, DEFAULT_SETTINGS.with_(report_folder_placement=True), embedder=fake_embedder
    )
    assert _placement(results, candidate) is None


def test_tiny_surroundings_cannot_establish_a_misplacement(tmp_path, fake_embedder):
    root = tmp_path / "project"
    candidate = root / "a" / "b"
    _files(root / "a", "alpha", 3)
    _files(candidate, "beta", 12)
    _files(root / "c", "beta", 12)

    results = analyze_tree(
        root, DEFAULT_SETTINGS.with_(report_folder_placement=True), embedder=fake_embedder
    )
    assert _placement(results, candidate) is None


def test_sibling_destination_is_excluded_from_current_context(tmp_path, fake_embedder):
    root = tmp_path / "project"
    candidate = root / "a" / "b"
    destination = root / "a" / "c"
    _files(root / "a", "alpha")
    _files(candidate, "beta")
    _files(destination, "beta")

    results = analyze_tree(
        root, DEFAULT_SETTINGS.with_(report_folder_placement=True), embedder=fake_embedder
    )
    evidence = _placement(results, candidate)
    assert evidence is not None
    assert evidence.suggested_parent == destination


def test_folder_flag_reports_placement_in_json(tmp_path, fake_embedder, monkeypatch, capsys):
    root = tmp_path / "project"
    candidate = root / "a" / "b"
    destination = root / "c"
    _files(root / "a", "alpha")
    _files(candidate, "beta")
    _files(destination, "beta")
    monkeypatch.setattr("messie.cli.get_embedder", lambda: fake_embedder)

    main([str(root), "--json"])
    baseline = json.loads(capsys.readouterr().out)
    assert all(
        finding["code"] != "folder_placement"
        for folder in baseline["folders"]
        for finding in folder["findings"]
    )

    assert main([str(root), "--folder", "--json"]) == 1
    payload = json.loads(capsys.readouterr().out)
    folder = next(item for item in payload["folders"] if item["path"] == str(candidate))
    finding = next(item for item in folder["findings"] if item["code"] == "folder_placement")
    assert finding["data"]["suggested_parent"] == str(destination)


def test_folder_mode_reports_its_own_progress(tmp_path, fake_embedder, monkeypatch, capsys):
    root = tmp_path / "project"
    _files(root / "a", "alpha")
    _files(root / "a" / "b", "beta")
    _files(root / "c", "beta")
    settings = DEFAULT_SETTINGS.with_(report_folder_placement=True)
    seen = []
    analyze_tree(root, settings, embedder=fake_embedder, progress=seen.append)

    stages = [event.stage for event in seen]
    assert stages.index("judge") < stages.index("place")
    placing = [event for event in seen if event.stage == "place"]
    assert placing[0].done == 0
    assert placing[-1].done == placing[-1].total
    assert any(event.path == root / "a" / "b" for event in placing)

    monkeypatch.setattr("messie.cli.get_embedder", lambda: fake_embedder)
    main([str(root), "--folder", "--verbose", "--json"])
    output = capsys.readouterr()
    assert "placing" in output.err
    assert json.loads(output.out)["root"] == str(root)

    main([str(root), "--verbose", "--json"])
    assert "placing" not in capsys.readouterr().err
