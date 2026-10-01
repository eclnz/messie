"""Placement ground truth evaluated with the default embedding model."""

from __future__ import annotations

import pytest
from conftest import embedder_or_skip
from corpus.placement import PLACEMENT_CASES, PlacementCase

from messie.analyze import analyze_tree
from messie.config import DEFAULT_SETTINGS
from messie.placement import PlacementEvidence


@pytest.fixture(scope="module")
def real_embedder():
    return embedder_or_skip()


@pytest.mark.parametrize("case", PLACEMENT_CASES, ids=lambda case: case.name)
def test_folder_placement_ground_truth(case: PlacementCase, tmp_path, real_embedder):
    root = (tmp_path / case.name).resolve()
    expected = case.build(root)
    for candidate, destination in expected.items():
        assert (root / candidate).is_dir()
        if destination is not None:
            assert (root / destination).is_dir()
    results = analyze_tree(
        root, DEFAULT_SETTINGS.with_(report_folder_placement=True), embedder=real_embedder
    )
    observed = {}
    for analysis in results:
        for finding in analysis.findings:
            if finding.code != "folder_placement":
                continue
            assert isinstance(finding.data, PlacementEvidence)
            related = finding.data.related_folder
            observed[str(analysis.path.relative_to(root))] = (
                str(related.relative_to(root)) if related is not None else None
            )
    assert observed == expected
