"""Command line entry point."""

from __future__ import annotations

import argparse
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
    render_text,
    supports_colour,
)
from messie.result import Verdict


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
    )
    parser.add_argument("path", nargs="?", default=".", help="folder to look at")
    parser.add_argument("--json", action="store_true", help="machine-readable output")
    parser.add_argument("--depth", type=int, default=DEFAULT_SETTINGS.max_depth,
                        help="how many levels of subfolder to check (default: %(default)s)")
    parser.add_argument("--all", dest="show_all", action="store_true",
                        help="show every folder, including the tidy ones")
    parser.add_argument("--hidden", action="store_true", help="include hidden files")
    parser.add_argument("--threshold", type=float, default=None,
                        help="similarity below which two files count as unrelated")
    parser.add_argument("--min-verdict", default="lived-in",
                        help="quietest verdict worth printing (default: %(default)s)")
    parser.add_argument("--fail-over", default="messy",
                        help="exit 1 when any folder reaches this verdict (default: %(default)s)")
    parser.add_argument("-c", "--crowding", action="store_true",
                        help="also report folders holding a lot of files, "
                             "even when everything in them belongs together")
    parser.add_argument("-v", "--verbose", action="store_true",
                        help="show the walk as it happens, on stderr")
    parser.add_argument("--no-color", dest="colour", action="store_false", default=None,
                        help="disable coloured output")
    parser.add_argument("--version", action="version", version=f"messie {__version__}")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)

    try:
        min_verdict = _parse_verdict(args.min_verdict)
        fail_over = _parse_verdict(args.fail_over)
    except ValueError as exc:
        print(f"messie: {exc}", file=sys.stderr)
        return 2

    root = Path(args.path).expanduser()
    if not root.is_dir():
        print(f"messie: {root} is not a folder", file=sys.stderr)
        return 2
    root = root.resolve()

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

    # Verbose output goes to stderr throughout, so that --json -v still pipes.
    printer = ProgressPrinter() if args.verbose else None
    if printer is not None:
        print(f"messie {__version__} · {embedder.name} · {root}", file=sys.stderr)

    try:
        analyses = analyze_tree(root, settings, embedder=embedder, progress=printer)
    except (NotADirectoryError, PermissionError) as exc:
        print(f"messie: {exc}", file=sys.stderr)
        return 2

    if printer is not None:
        printer.done(analyses)

    colour = args.colour if args.colour is not None else supports_colour()
    opts = RenderOptions(
        root=root,
        colour=colour,
        show_all=args.show_all,
        min_verdict=min_verdict,
    )

    print(render_json(analyses, opts) if args.json else render_text(analyses, opts))

    worst = max((a.verdict for a in analyses if a.judged), default=Verdict.TIDY)
    return 1 if worst >= fail_over else 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
