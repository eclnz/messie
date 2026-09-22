"""Command line entry point."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from messie import __version__
from messie.analyze import analyze_tree
from messie.cache import Cache, default_cache_path
from messie.config import DEFAULT_SETTINGS
from messie.embed import BACKEND_ORDER, backend_status, get_embedder
from messie.report import RenderOptions, render_json, render_text, supports_colour
from messie.score import Verdict


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
    parser.add_argument("--backend", default="auto", choices=("auto", *BACKEND_ORDER),
                        help="embedding backend (default: auto, best available)")
    parser.add_argument("--threshold", type=float, default=None,
                        help="similarity below which two files count as unrelated")
    parser.add_argument("--min-verdict", default="lived-in",
                        help="quietest verdict worth printing (default: %(default)s)")
    parser.add_argument("--fail-over", default="messy",
                        help="exit 1 when any folder reaches this verdict (default: %(default)s)")
    parser.add_argument("--no-cache", action="store_true", help="do not read or write the cache")
    parser.add_argument("--no-color", dest="colour", action="store_false", default=None,
                        help="disable coloured output")
    parser.add_argument("--doctor", action="store_true",
                        help="report which embedding backends are usable, then exit")
    parser.add_argument("--version", action="version", version=f"messie {__version__}")
    return parser


def _doctor() -> int:
    print(f"messie {__version__}")
    print(f"cache: {default_cache_path()}")
    print("\nembedding backends, best first:")
    any_semantic = False
    for name, ok, detail in backend_status():
        mark = "✓" if ok else "·"
        print(f"  {mark} {name:<12} {detail}")
        if ok and name != "lexical":
            any_semantic = True
    if not any_semantic:
        print(
            "\nNo semantic backend available — falling back to lexical matching.\n"
            "For content-meaning comparison: pip install 'messie[semantic]'\n"
            "(wordllama ships its weights in the wheel; nothing is downloaded at runtime.)"
        )
    return 0


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)

    if args.doctor:
        return _doctor()

    try:
        min_verdict = Verdict.parse(args.min_verdict)
        fail_over = Verdict.parse(args.fail_over)
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
    )
    if args.threshold is not None:
        settings = settings.with_(cluster_threshold_override=args.threshold)

    try:
        embedder = get_embedder(args.backend)
    except Exception as exc:  # noqa: BLE001 - surfaced to the user, not swallowed
        print(f"messie: no usable embedding backend: {exc}", file=sys.stderr)
        return 2

    cache = Cache(enabled=not args.no_cache)
    try:
        analyses = analyze_tree(root, settings, embedder=embedder, cache=cache)
    except (NotADirectoryError, PermissionError) as exc:
        print(f"messie: {exc}", file=sys.stderr)
        return 2
    finally:
        cache.close()

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
