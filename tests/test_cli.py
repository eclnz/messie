"""The command line: output shape, exit codes, and the read-only promise."""

from __future__ import annotations

import json

import pytest
from conftest import snapshot, write_blob

from messie.cli import main


@pytest.fixture
def messy_tree(mixed_docx_dir):
    return mixed_docx_dir


def run(argv, capsys):
    code = main(argv)
    return code, capsys.readouterr().out


def test_reports_a_mess_and_exits_one(messy_tree, capsys):
    code, out = run([str(messy_tree), "--no-color", "--backend", "wordllama"], capsys)
    assert code == 1
    assert "unrelated" in out.lower()


def test_tidy_folder_exits_zero(tmp_path, capsys):
    folder = tmp_path / "album"
    for i in range(12):
        write_blob(folder / f"DSC_{i:03d}.jpg", 4000 + i)
    code, out = run([str(folder), "--no-color", "--backend", "wordllama"], capsys)
    assert code == 0
    assert "No mess found" in out


def test_json_output_is_valid_and_complete(messy_tree, capsys):
    code, out = run([str(messy_tree), "--json", "--backend", "wordllama"], capsys)
    payload = json.loads(out)

    assert payload["root"] == str(messy_tree.resolve())
    folder = payload["folders"][0]
    assert folder["verdict"] in {"tidy", "lived-in", "messy", "chaotic"}
    assert 0 <= folder["score"] <= 100
    assert any(f["code"] == "unrelated_topics" for f in folder["findings"])
    assert code == 1


def test_fail_over_threshold_is_respected(messy_tree, capsys):
    code, _ = run(
        [str(messy_tree), "--no-color", "--backend", "wordllama", "--fail-over", "chaotic"],
        capsys,
    )
    assert code in (0, 1)
    quiet, _ = run(
        [str(messy_tree), "--no-color", "--backend", "wordllama", "--fail-over", "tidy"],
        capsys,
    )
    assert quiet == 1


def test_missing_folder_is_an_error(tmp_path, capsys):
    assert main([str(tmp_path / "nope"), "--backend", "wordllama"]) == 2


def test_bad_verdict_name_is_an_error(tmp_path, capsys):
    assert main([str(tmp_path), "--min-verdict", "spotless"]) == 2


def test_doctor_lists_backends(capsys):
    code, out = run(["--doctor"], capsys)
    assert code == 0
    assert "wordllama" in out
    assert "backends" in out.lower()


def test_cli_changes_nothing_on_disk(messy_tree, capsys):
    before = snapshot(messy_tree)
    run([str(messy_tree), "--no-color", "--backend", "wordllama"], capsys)
    assert snapshot(messy_tree) == before


def test_all_flag_shows_tidy_folders(tmp_path, capsys):
    folder = tmp_path / "album"
    for i in range(12):
        write_blob(folder / f"DSC_{i:03d}.jpg", 4000 + i)
    _, out = run([str(folder), "--all", "--no-color", "--backend", "wordllama"], capsys)
    assert "TIDY" in out


def test_explicit_backend_that_is_missing_fails_loudly(tmp_path, capsys, monkeypatch):
    """Asking for a backend and silently getting a weaker one would be a lie."""
    import messie.embed as embed

    monkeypatch.setattr(embed, "_load", lambda name: (_ for _ in ()).throw(RuntimeError("nope")))
    assert main([str(tmp_path), "--backend", "wordllama"]) == 2
