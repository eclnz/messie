"""Saying it out loud.

The report states what is in the folder and how strongly that reads as mess.
It deliberately never suggests a filing scheme, a move, or a deletion: what
belongs where is the user's call, and messie has no opinion worth having about
it.
"""

from __future__ import annotations

import json
import os
import sys
import time
from dataclasses import dataclass
from pathlib import Path

from messie.analyze import DirAnalysis, Progress
from messie.score import Verdict

_COLOURS = {
    Verdict.TIDY: "\033[32m",
    Verdict.LIVED_IN: "\033[36m",
    Verdict.MESSY: "\033[33m",
    Verdict.CHAOTIC: "\033[31m",
}
_DIM = "\033[2m"
_BOLD = "\033[1m"
_RESET = "\033[0m"


@dataclass
class RenderOptions:
    root: Path
    colour: bool = True
    verbose: bool = False
    show_all: bool = False
    min_verdict: Verdict = Verdict.LIVED_IN


def supports_colour(stream=sys.stdout) -> bool:
    if os.environ.get("NO_COLOR"):
        return False
    return bool(getattr(stream, "isatty", lambda: False)())


def _paint(text: str, code: str, enabled: bool) -> str:
    return f"{code}{text}{_RESET}" if enabled else text


def _fit(text: str, width: int) -> str:
    """Pad or truncate to exactly ``width`` visible characters.

    Padding has to happen before colouring: escape codes count towards a format
    spec's width but not towards anything the reader can see.
    """
    if len(text) > width:
        return text[: width - 1] + "…"
    return text.ljust(width)


def _display_path(path: Path, root: Path) -> str:
    if path == root:
        return _tilde(path)
    try:
        return "./" + str(path.relative_to(root))
    except ValueError:
        return _tilde(path)


def _tilde(path: Path) -> str:
    home = str(Path.home())
    text = str(path)
    return "~" + text[len(home) :] if text.startswith(home) else text


def _year(ts: float) -> str:
    return time.strftime("%Y", time.localtime(ts)) if ts else "?"


def _span(first: float, last: float) -> str:
    a, b = _year(first), _year(last)
    return a if a == b else f"{a}–{b}"


def render_dir(analysis: DirAnalysis, opts: RenderOptions) -> list[str]:
    """One folder's verdict and the evidence for it."""
    colour = opts.colour
    lines: list[str] = []
    title = _display_path(analysis.path, opts.root)

    if not analysis.judged:
        if opts.show_all:
            lines.append(
                    f"{title:<44} {_paint(chr(8212), _DIM, colour)}  "
                f"{_paint(analysis.skip_reason, _DIM, colour)}"
            )
        return lines

    badge = _paint(analysis.verdict.label.upper(), _COLOURS[analysis.verdict] + _BOLD, colour)
    score = f"{analysis.score:g}/100"
    meta = _paint(f"{analysis.n_files} files · {analysis.backend}", _DIM, colour)
    lines.append(f"{_paint(_fit(title, 52), _BOLD, colour)} {badge}  {score}   {meta}")

    if not analysis.findings:
        lines.append(_paint("  nothing out of place.", _DIM, colour))
        return lines

    for finding in analysis.findings:
        lines.append(f"  {finding.headline}")

        if finding.code == "unrelated_topics":
            for group in finding.data.get("groups", []):
                label = group["label"]
                count = f"{group['count']} files"
                when = _span(group.get("first_seen", 0), group.get("last_seen", 0))
                examples = ", ".join(group["examples"])
                extra = group["count"] - len(group["examples"])
                if extra > 0:
                    examples += f" +{extra}"
                lines.append(
                    f"      · {_fit(label, 28)} {count:>9}  {when:<11} "
                    f"{_paint(examples, _DIM, colour)}"
                )
            continue

        detail_bits = []
        if finding.detail:
            detail_bits.append(finding.detail)
        if finding.examples:
            detail_bits.append(", ".join(finding.examples[:4]))
        if detail_bits:
            lines.append(_paint("      " + "  ·  ".join(detail_bits), _DIM, colour))

    if analysis.truncated:
        lines.append(
            _paint(f"      ({analysis.truncated} further files not read)", _DIM, colour)
        )
    if analysis.failed_signals:
        # A signal that crashed and a signal that had nothing to say look
        # identical from out here. Say which happened.
        lines.append(
            _paint(
                "  ! these checks could not run: "
                + ", ".join(sorted(set(analysis.failed_signals))),
                _COLOURS[Verdict.MESSY],
                colour,
            )
        )
    return lines


def render_text(analyses: list[DirAnalysis], opts: RenderOptions) -> str:
    judged = [a for a in analyses if a.judged]
    flagged = [a for a in judged if a.verdict >= opts.min_verdict]
    shown = judged if opts.show_all else flagged

    blocks: list[str] = []
    for analysis in sorted(shown, key=lambda a: (-a.score, str(a.path))):
        block = render_dir(analysis, opts)
        if block:
            blocks.append("\n".join(block))

    if not blocks:
        if not judged:
            return _paint(
                "Nothing here has enough in it to judge.", _DIM, opts.colour
            )
        return _paint(
            f"No mess found. {len(judged)} folder{'s' if len(judged) != 1 else ''} looked at.",
            _COLOURS[Verdict.TIDY],
            opts.colour,
        )

    out = "\n\n".join(blocks)
    if len(judged) > 1:
        worst = max(flagged, key=lambda a: a.score)
        summary = (
            f"{len(flagged)} of {len(judged)} folders are a mess — "
            f"worst is {_display_path(worst.path, opts.root)} at {worst.score:g}."
        )
        out += "\n\n" + _paint(summary, _BOLD, opts.colour)
    return out


def to_dict(analysis: DirAnalysis) -> dict:
    return {
        "path": str(analysis.path),
        "judged": analysis.judged,
        "skip_reason": analysis.skip_reason,
        "files": analysis.n_files,
        "truncated": analysis.truncated,
        "backend": analysis.backend,
        "score": analysis.score,
        "verdict": analysis.verdict.label,
        "clusters": (analysis.clustering.n_clusters if analysis.clustering else 0),
        "failed_signals": analysis.failed_signals,
        "findings": [
            {
                "code": f.code,
                "severity": round(f.severity, 3),
                "headline": f.headline,
                "detail": f.detail,
                "examples": f.examples,
                "data": f.data,
            }
            for f in analysis.findings
        ],
    }


def render_json(analyses: list[DirAnalysis], opts: RenderOptions) -> str:
    payload = {
        "root": str(opts.root),
        "folders": [to_dict(a) for a in analyses],
    }
    return json.dumps(payload, indent=2, default=str)


class ProgressPrinter:
    """Draws a tree walk as it happens, on stderr.

    stderr because stdout carries the report: ``messie --json -v | jq`` has to
    keep working, and it only does if the chatter goes somewhere else.

    On a terminal this is one line, rewritten in place. Redirected to a file it
    becomes one line per folder at a sampled interval, because a log full of
    carriage returns is not a log. Either way the folder is named before it is
    read rather than after, so if something in it throws, the last line printed
    is the folder that did it.
    """

    #: Rewriting the line faster than this buys nothing a person can see, and
    #: on a big tree the terminal write costs more than the work it describes.
    _MIN_INTERVAL = 0.08

    _STAGES = {
        "scan": "scanning",
        "read": "reading",
        "judge": "judging",
    }

    def __init__(self, stream=None, colour: bool | None = None, width: int = 78) -> None:
        self._stream = stream if stream is not None else sys.stderr
        self._live = bool(getattr(self._stream, "isatty", lambda: False)())
        self._colour = supports_colour(self._stream) if colour is None else colour
        self._width = width
        self._last = 0.0
        self._stage = ""
        self._started = time.monotonic()
        self._folders = 0
        self._files = 0

    def __call__(self, progress: Progress) -> None:
        now = time.monotonic()
        changed = progress.stage != self._stage
        if changed:
            self._stage = progress.stage
        if progress.stage == "read":
            self._folders = max(self._folders, progress.done)
            self._files += progress.files

        last = progress.done >= progress.total
        if not (changed or last) and now - self._last < self._MIN_INTERVAL:
            return
        self._last = now

        name = self._where(progress.path)
        line = (
            f"  {self._STAGES.get(progress.stage, progress.stage):<9}"
            f"{progress.done:>5}/{progress.total:<6} {name}"
        )
        if self._live:
            self._stream.write("\r" + _fit(_paint(line, _DIM, self._colour), self._width))
            if last and progress.stage == "judge":
                self._stream.write("\r" + " " * self._width + "\r")
        elif changed or last:
            self._stream.write(line.rstrip() + "\n")
        self._stream.flush()

    @staticmethod
    def _where(path: Path | None) -> str:
        if path is None:
            return ""
        # The tail is the informative part; a full path scrolls the line away.
        parts = path.parts[-3:]
        return "/".join(parts)

    def done(self, analyses: list) -> None:
        """One closing line with what the run actually cost."""
        elapsed = time.monotonic() - self._started
        judged = sum(1 for a in analyses if getattr(a, "judged", False))
        summary = (
            f"  read {self._files} files in {self._folders} folders, "
            f"judged {judged}, in {elapsed:.1f}s"
        )
        self._stream.write(_paint(summary, _DIM, self._colour) + "\n")
        self._stream.flush()
