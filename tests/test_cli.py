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


# --- --verbose --------------------------------------------------------------
#
# The whole point of the flag is watching a long run, so what these guard is
# that it stays out of the way of everything else: stdout unchanged, JSON still
# parseable, and the folder named before it is read rather than after, which is
# what makes the last line printed the one that names a crashing folder.


def test_verbose_writes_nothing_to_stdout(messy_tree, capsys):
    """Progress belongs on stderr. If it leaks into stdout, every pipeline
    built on messie breaks the day someone adds -v to it."""
    main([str(messy_tree), "--no-color", "--backend", "wordllama"])
    plain = capsys.readouterr().out

    main([str(messy_tree), "--no-color", "--backend", "wordllama", "-v"])
    captured = capsys.readouterr()

    assert captured.out == plain
    assert captured.err.strip(), "asked for verbose and got nothing"


def test_verbose_json_still_parses(messy_tree, capsys):
    code = main([str(messy_tree), "--json", "--backend", "wordllama", "--verbose"])
    captured = capsys.readouterr()
    assert code in (0, 1)
    payload = json.loads(captured.out)
    assert payload["folders"]


def test_verbose_names_every_stage_and_the_cost(messy_tree, capsys):
    main([str(messy_tree), "--no-color", "--backend", "wordllama", "-v"])
    err = capsys.readouterr().err

    for stage in ("scanning", "reading", "judging"):
        assert stage in err, f"no sign of the {stage} stage in verbose output"
    assert "files in" in err and "folders" in err, "no closing summary"


def test_progress_reports_a_folder_before_reading_it(tmp_path):
    """Named before, not after. A folder whose contents make an extractor throw
    is only identifiable from the log if its name was printed on the way in."""
    from messie.analyze import Progress, analyze_tree

    (tmp_path / "sub").mkdir()
    for i in range(8):
        (tmp_path / "sub" / f"note_{i}.txt").write_text(f"a note about gardening {i}")

    seen: list[Progress] = []
    analyze_tree(tmp_path, progress=seen.append)

    stages = [p.stage for p in seen]
    assert stages.index("scan") < stages.index("read") < stages.index("judge")
    reads = [p for p in seen if p.stage == "read"]
    assert reads[0].done == 1 and reads[-1].done == reads[-1].total
    assert any(p.path is not None and p.path.name == "sub" for p in reads)


def test_analyze_tree_without_a_progress_callback_is_unchanged(tmp_path):
    """The callback is optional and must stay that way — every other caller,
    tests included, passes nothing."""
    from messie.analyze import analyze_tree

    for i in range(8):
        (tmp_path / f"note_{i}.txt").write_text(f"a note about gardening {i}")

    quiet = analyze_tree(tmp_path)
    noisy = analyze_tree(tmp_path, progress=lambda _: None)
    assert [a.score for a in quiet] == [a.score for a in noisy]
