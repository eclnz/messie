"""Command line entry point."""

from __future__ import annotations

import argparse
import glob
import json
import os
import sys
from pathlib import Path

from messie import __version__
from messie.analyze import analyze_tree
from messie.config import DEFAULT_SETTINGS
from messie.embed import EmbedderUnavailable, get_embedder
from messie.report import (
    ProgressPrinter,
    RenderOptions,
    render_json,
    render_json_lines,
    render_text,
    supports_colour,
)
from messie.result import DirAnalysis, Verdict


def _parse_verdict(text: str) -> Verdict:
    key = text.strip().upper().replace("-", "_")
    try:
        return Verdict[key]
    except KeyError as exc:
        raise ValueError(f"unknown verdict {text!r}") from exc


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="messie",
        description=(
            "Notices when a folder has become a mess. Reports only — never moves, "
            "renames or deletes anything. Runs entirely on this machine."
        ),
        epilog=(
            "plain output: SCORE<TAB>VERDICT<TAB>FILES<TAB>PATH<TAB>FINDINGS; "
            "use --json or --jsonl for structured output"
        ),
    )
    parser.add_argument(
        "paths",
        nargs="*",
        metavar="PATH",
        help="folders, files, or glob patterns; '-' reads paths from standard input",
    )
    output = parser.add_mutually_exclusive_group()
    output.add_argument(
        "-j", "--json", action="store_true", help="write one JSON document"
    )
    output.add_argument(
        "--jsonl", "--json-lines", action="store_true",
        help="write one compact JSON object per folder",
    )
    parser.add_argument(
        "-d", "--depth", "--max-depth", type=int,
        default=DEFAULT_SETTINGS.max_depth,
        help="maximum recursion depth (default: %(default)s)",
    )
    parser.add_argument(
        "-a", "--all", dest="show_all", action="store_true",
        help="write one record for every judged folder",
    )
    parser.add_argument("--hidden", action="store_true", help="include hidden files")
    parser.add_argument(
        "-t", "--threshold", type=float, default=None,
        help="similarity below which two files count as unrelated",
    )
    parser.add_argument(
        "-m", "--min-verdict", default="lived-in",
        help="quietest verdict to print (default: %(default)s)",
    )
    parser.add_argument(
        "--fail-over", default="messy",
        help="exit 1 when any folder reaches this verdict (default: %(default)s)",
    )
    parser.add_argument(
        "-c", "--crowding", action="store_true",
        help="report folders holding many files even when they belong together",
    )
    chatter = parser.add_mutually_exclusive_group()
    chatter.add_argument(
        "-q", "--quiet", action="store_true",
        help="write no report; communicate through the exit status",
    )
    chatter.add_argument(
        "-v", "--verbose", action="store_true",
        help="show progress on standard error",
    )
    parser.add_argument(
        "-0", "--null", action="store_true",
        help="split standard-input paths on NUL bytes instead of newlines",
    )
    parser.add_argument(
        "--color", choices=("auto", "always", "never"), nargs="?", const="always",
        default="never", help="when to colour the verdict (default: %(default)s)",
    )
    parser.add_argument(
        "--no-color", dest="color", action="store_const", const="never",
        help=argparse.SUPPRESS,
    )
    parser.add_argument("--version", action="version", version=f"messie {__version__}")
    return parser


def _read_stdin(null: bool) -> list[str]:
    """Read path operands without losing spaces or undecodable filesystem bytes."""
    stream = getattr(sys.stdin, "buffer", sys.stdin)
    data: bytes | str = stream.read()
    if isinstance(data, bytes):
        chunks = data.split(b"\0") if null else data.splitlines()
        return [os.fsdecode(chunk.rstrip(b"\r")) for chunk in chunks if chunk]
    chunks = data.split("\0") if null else data.splitlines()
    return [chunk.rstrip("\r") for chunk in chunks if chunk]


def _path_operands(paths: list[str], *, null: bool, implicit_stdin: bool) -> list[str]:
    if not paths:
        if implicit_stdin and not getattr(sys.stdin, "isatty", lambda: True)():
            try:
                piped = _read_stdin(null)
                if piped:
                    return piped
            except OSError:
                pass
        return ["."]

    operands: list[str] = []
    read_stdin = False
    for path in paths:
        if path == "-":
            if not read_stdin:
                operands.extend(_read_stdin(null))
                read_stdin = True
        else:
            operands.append(path)
    return operands


def _roots_for(operands: list[str]) -> tuple[list[Path], list[str]]:
    roots: list[Path] = []
    errors: list[str] = []
    seen: set[Path] = set()
    for operand in operands:
        expanded = os.path.expanduser(operand)
        matches = (
            sorted(glob.glob(expanded, recursive=True))
            if glob.has_magic(expanded)
            else [expanded]
        )
        if not matches:
            errors.append(f"{operand}: no matches")
            continue
        for match in matches:
            path = Path(match)
            if path.is_file():
                path = path.parent
            elif not path.is_dir():
                errors.append(f"{match}: no such file or directory")
                continue
            root = path.resolve()
            if root not in seen:
                seen.add(root)
                roots.append(root)
    return roots, errors


def _write_stdout(output: str) -> None:
    if not output:
        return
    try:
        sys.stdout.write(output)
        if not output.endswith("\n"):
            sys.stdout.write("\n")
        sys.stdout.flush()
    except BrokenPipeError:
        # Prevent Python's final stdout flush from reporting another EPIPE.
        sys.stdout = None


def main(argv: list[str] | None = None) -> int:
    implicit_stdin = argv is None
    args = build_parser().parse_args(argv)

    try:
        min_verdict = _parse_verdict(args.min_verdict)
        fail_over = _parse_verdict(args.fail_over)
    except ValueError as exc:
        print(f"messie: {exc}", file=sys.stderr)
        return 2

    try:
        operands = _path_operands(
            args.paths, null=args.null, implicit_stdin=implicit_stdin
        )
    except OSError as exc:
        print(f"messie: standard input: {exc}", file=sys.stderr)
        return 2
    roots, operand_errors = _roots_for(operands)
    for error in operand_errors:
        print(f"messie: {error}", file=sys.stderr)
    if not roots:
        return 0 if not operands and not operand_errors else 2

    settings = DEFAULT_SETTINGS.with_(
        max_depth=max(0, args.depth),
        include_hidden=args.hidden,
        report_crowding=args.crowding,
    )
    if args.threshold is not None:
        settings = settings.with_(cluster_threshold_override=args.threshold)

    try:
        embedder = get_embedder()
    except EmbedderUnavailable as exc:
        print(f"messie: embedding unavailable: {exc}", file=sys.stderr)
        return 2

    colour = args.color == "always" or (
        args.color == "auto" and supports_colour(sys.stdout)
    )
    completed: list[tuple[Path, list[DirAnalysis], RenderOptions]] = []
    runtime_error = bool(operand_errors)
    for root in roots:
        # Verbose output stays on stderr, so JSON and text remain safe to pipe.
        printer = ProgressPrinter() if args.verbose else None
        if printer is not None:
            print(f"messie {__version__} · {embedder.name} · {root}", file=sys.stderr)
        try:
            analyses = analyze_tree(root, settings, embedder=embedder, progress=printer)
        except (NotADirectoryError, PermissionError, OSError) as exc:
            print(f"messie: {root}: {exc}", file=sys.stderr)
            runtime_error = True
            continue
        if printer is not None:
            printer.done(analyses)
        completed.append(
            (
                root,
                analyses,
                RenderOptions(
                    root=root,
                    colour=colour,
                    show_all=args.show_all,
                    min_verdict=min_verdict,
                ),
            )
        )

    if not args.quiet:
        if args.json:
            payloads = [json.loads(render_json(items, opts)) for _, items, opts in completed]
            output = (
                json.dumps(payloads[0], indent=2, default=str)
                if len(payloads) == 1
                else json.dumps({"roots": payloads}, indent=2, default=str)
            )
        elif args.jsonl:
            output = "\n".join(
                rendered
                for _, items, opts in completed
                if (rendered := render_json_lines(items, opts))
            )
        else:
            output = "\n".join(
                rendered
                for _, items, opts in completed
                if (rendered := render_text(items, opts))
            )
        _write_stdout(output)

    worst = max(
        (analysis.verdict for _, items, _ in completed for analysis in items if analysis.judged),
        default=Verdict.TIDY,
    )
    if runtime_error:
        return 2
    return 1 if worst >= fail_over else 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
