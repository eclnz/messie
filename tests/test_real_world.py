"""Real-directory regression tests."""

from __future__ import annotations

import pytest
from realdirs import MINIMUM_FOLDERS, coherent_folders

from messie.analyze import analyze_dir
from messie.result import Verdict

#: Maximum messy rate allowed for coherent directories.
FALSE_POSITIVE_BUDGET = 0.10

@pytest.fixture(scope="module")
def judged() -> list:
    folders = coherent_folders()
    if len(folders) < MINIMUM_FOLDERS:
        pytest.skip(f"only {len(folders)} real folders available")
    out = []
    for folder in folders:
        analysis = analyze_dir(folder)
        if analysis.judged:
            out.append(analysis)
    if len(out) < MINIMUM_FOLDERS:
        pytest.skip(f"only {len(out)} real folders had enough files")
    return out


def test_most_real_coherent_folders_are_left_alone(judged):
    """Most coherent real folders are not messy."""
    messy = [a for a in judged if a.verdict >= Verdict.MESSY]
    rate = len(messy) / len(judged)
    assert rate <= FALSE_POSITIVE_BUDGET, (
        f"{len(messy)} of {len(judged)} real coherent folders read as messy "
        f"({rate:.1%}, budget {FALSE_POSITIVE_BUDGET:.0%}). Worst: "
        + "; ".join(f"{a.path.name} {[f.code for f in a.findings]}" for a in messy[:5])
    )


def test_a_package_is_not_misfiled_into_its_own_subpackages(judged):
    """A package is not misfiled into its own subpackages."""
    flagged = [a for a in judged if any(f.code == "misfiled_neighbours" for f in a.findings)]
    assert len(flagged) / len(judged) <= 0.05, (
        "misfiled_neighbours fires on "
        f"{len(flagged)} of {len(judged)} real coherent folders: "
        + ", ".join(a.path.name for a in flagged[:6])
    )


def test_no_signal_crashes_on_real_files(judged):
    """Signals do not fail on real files."""
    broken = {name for a in judged for name in a.failed_signals}
    assert not broken, f"signals raised on real directories: {sorted(broken)}"


def test_real_files_are_never_modified(judged):
    """Analysis does not modify real files."""
    for analysis in judged[:12]:
        before = {
            p.name: (p.stat().st_size, p.stat().st_mtime)
            for p in analysis.path.iterdir()
            if p.is_file()
        }
        analyze_dir(analysis.path)
        after = {
            p.name: (p.stat().st_size, p.stat().st_mtime)
            for p in analysis.path.iterdir()
            if p.is_file()
        }
        assert before == after, f"{analysis.path} changed during analysis"
