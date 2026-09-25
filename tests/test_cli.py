"""The command line: output shape, exit codes, and the read-only promise."""

from __future__ import annotations

import io
import json
from pathlib import Path

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
    code, out = run([str(messy_tree), "--no-color"], capsys)
    assert code == 1
    fields = out.rstrip("\n").split("\t")
    assert fields[1] in {"lived-in", "messy", "chaotic"}
    assert "unrelated_topics" in fields[4]


def test_tidy_folder_exits_zero(tmp_path, capsys):
    folder = tmp_path / "album"
    for i in range(12):
        write_blob(folder / f"DSC_{i:03d}.jpg", 4000 + i)
    code, out = run([str(folder), "--no-color"], capsys)
    assert code == 0
    assert out == ""


def test_json_output_is_valid_and_complete(messy_tree, capsys):
    code, out = run([str(messy_tree), "--json"], capsys)
    payload = json.loads(out)

    assert payload["root"] == str(messy_tree.resolve())
    folder = payload["folders"][0]
    assert "embedder" not in folder
    assert folder["verdict"] in {"tidy", "lived-in", "messy", "chaotic"}
    assert 0 <= folder["score"] <= 100
    assert any(f["code"] == "unrelated_topics" for f in folder["findings"])
    assert code == 1


def test_fail_over_threshold_is_respected(messy_tree, capsys):
    code, _ = run(
        [str(messy_tree), "--no-color", "--fail-over", "chaotic"],
        capsys,
    )
    assert code in (0, 1)
    quiet, _ = run(
        [str(messy_tree), "--no-color", "--fail-over", "tidy"],
        capsys,
    )
    assert quiet == 1


def test_missing_folder_is_an_error(tmp_path, capsys):
    assert main([str(tmp_path / "nope")]) == 2


def test_bad_verdict_name_is_an_error(tmp_path, capsys):
    assert main([str(tmp_path), "--min-verdict", "spotless"]) == 2


def test_cli_changes_nothing_on_disk(messy_tree, capsys):
    before = snapshot(messy_tree)
    run([str(messy_tree), "--no-color"], capsys)
    assert snapshot(messy_tree) == before


def test_all_flag_shows_tidy_folders(tmp_path, capsys):
    folder = tmp_path / "album"
    for i in range(12):
        write_blob(folder / f"DSC_{i:03d}.jpg", 4000 + i)
    _, out = run([str(folder), "--all", "--no-color"], capsys)
    assert "\ttidy\t" in out


def test_short_depth_and_all_flags(tmp_path, capsys):
    folder = tmp_path / "album"
    for i in range(12):
        write_blob(folder / f"DSC_{i:03d}.jpg", 4000 + i)
    _, out = run(["-a", "-d", "0", str(folder), "--no-color"], capsys)
    assert "\ttidy\t" in out


def test_quoted_glob_expands_to_multiple_roots(tmp_path, capsys):
    for name in ("left", "right"):
        folder = tmp_path / name
        for i in range(6):
            write_blob(folder / f"DSC_{i:03d}.jpg", 4000 + i)

    code, out = run([str(tmp_path / "*"), "-a", "--json"], capsys)
    payload = json.loads(out)

    assert code == 0
    assert [Path(item["root"]).name for item in payload["roots"]] == ["left", "right"]


def test_file_glob_analyzes_its_containing_folder(tmp_path, capsys):
    for i in range(6):
        (tmp_path / f"note-{i}.txt").write_text("one coherent subject " * 20)

    _, out = run([str(tmp_path / "*.txt"), "-a", "--json"], capsys)
    payload = json.loads(out)

    assert payload["root"] == str(tmp_path.resolve())


def test_dash_reads_newline_delimited_paths(tmp_path, capsys, monkeypatch):
    folder = tmp_path / "folder with spaces"
    for i in range(6):
        write_blob(folder / f"DSC_{i:03d}.jpg", 4000 + i)
    monkeypatch.setattr("sys.stdin", io.StringIO(f"{folder}\n"))

    _, out = run(["-", "-a", "--json"], capsys)

    assert json.loads(out)["root"] == str(folder.resolve())


def test_null_delimited_stdin_and_json_lines(tmp_path, capsys, monkeypatch):
    roots = []
    for name in ("one", "two"):
        folder = tmp_path / name
        roots.append(folder)
        for i in range(6):
            write_blob(folder / f"DSC_{i:03d}.jpg", 4000 + i)
    monkeypatch.setattr("sys.stdin", io.StringIO("\0".join(map(str, roots)) + "\0"))

    code, out = run(["-0", "-", "-a", "--jsonl"], capsys)
    records = [json.loads(line) for line in out.splitlines()]

    assert code == 0
    assert {Path(record["root"]).name for record in records} == {"one", "two"}
    assert all("path" in record and "verdict" in record for record in records)
    assert all("embedder" not in record for record in records)


def test_quiet_mode_uses_only_exit_status(messy_tree, capsys):
    code, out = run([str(messy_tree), "-q"], capsys)
    assert code == 1
    assert out == ""


def test_json_omits_unjudged_folders_without_all(tmp_path, capsys):
    (tmp_path / "only.txt").write_text("too small")
    _, out = run([str(tmp_path), "--json"], capsys)
    assert json.loads(out)["folders"] == []


def test_all_handles_multiple_tidy_folders(tmp_path, capsys):
    for parent in (tmp_path, tmp_path / "child"):
        for i in range(6):
            write_blob(parent / f"DSC_{i:03d}.jpg", 4000 + i)

    code, out = run([str(tmp_path), "-a", "--no-color"], capsys)

    assert code == 0
    lines = out.splitlines()
    assert len(lines) == 2
    assert all(line.split("\t")[1] == "tidy" for line in lines)


def test_text_output_is_unix_friendly_tsv(tmp_path, capsys, monkeypatch):
    monkeypatch.chdir(tmp_path)
    folder = tmp_path / "album with spaces"
    for i in range(12):
        write_blob(folder / f"DSC_{i:03d}.jpg", 4000 + i)

    _, out = run([str(folder), "-a"], capsys)

    assert "\033[" not in out
    assert "nothing out of place" not in out
    assert "folders are a mess" not in out
    score, verdict, files, path, findings = out.rstrip("\n").split("\t")
    assert float(score) == 0
    assert verdict == "tidy"
    assert files == "12"
    assert path == "./album with spaces"
    assert findings == "-"


def test_default_colour_mode_preserves_plain_records():
    from messie.cli import build_parser

    assert build_parser().parse_args([]).color == "never"


def test_help_documents_plain_output_columns(capsys):
    from messie.cli import build_parser

    with pytest.raises(SystemExit) as stopped:
        build_parser().parse_args(["--help"])

    assert stopped.value.code == 0
    assert "SCORE<TAB>VERDICT<TAB>FILES<TAB>PATH<TAB>FINDINGS" in capsys.readouterr().out


def test_unavailable_embedder_is_an_error(tmp_path, capsys, monkeypatch):
    from messie.embed import EmbedderUnavailable

    def unavailable():
        raise EmbedderUnavailable("broken install")

    monkeypatch.setattr("messie.cli.get_embedder", unavailable)
    assert main([str(tmp_path)]) == 2


# --- --verbose --------------------------------------------------------------
#
# The whole point of the flag is watching a long run, so what these guard is
# that it stays out of the way of everything else: stdout unchanged, JSON still
# parseable, and the folder named before it is read rather than after, which is
# what makes the last line printed the one that names a crashing folder.


def test_verbose_writes_nothing_to_stdout(messy_tree, capsys):
    """Progress belongs on stderr. If it leaks into stdout, every pipeline
    built on messie breaks the day someone adds -v to it."""
    main([str(messy_tree), "--no-color"])
    plain = capsys.readouterr().out

    main([str(messy_tree), "--no-color", "-v"])
    captured = capsys.readouterr()

    assert captured.out == plain
    assert captured.err.strip(), "asked for verbose and got nothing"


def test_verbose_json_still_parses(messy_tree, capsys):
    code = main([str(messy_tree), "--json", "--verbose"])
    captured = capsys.readouterr()
    assert code in (0, 1)
    payload = json.loads(captured.out)
    assert payload["folders"]


def test_verbose_names_every_stage_and_the_cost(messy_tree, capsys):
    main([str(messy_tree), "--no-color", "-v"])
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
