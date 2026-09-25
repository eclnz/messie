"""Render analysis results."""

from __future__ import annotations

import json
import os
import sys
import time
from dataclasses import dataclass
from pathlib import Path

from messie.analyze import Progress
from messie.result import DirAnalysis, Verdict

_COLOURS = {
    Verdict.TIDY: "\033[32m",
    Verdict.LIVED_IN: "\033[36m",
    Verdict.MESSY: "\033[33m",
    Verdict.CHAOTIC: "\033[31m",
}
_VERDICT_LABELS = {
    Verdict.TIDY: "tidy",
    Verdict.LIVED_IN: "lived-in",
    Verdict.MESSY: "messy",
    Verdict.CHAOTIC: "chaotic",
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
    """Pad or truncate uncoloured text to ``width``."""
    if len(text) > width:
        return text[: width - 1] + "…"
    return text.ljust(width)


def _display_path(path: Path, root: Path) -> str:
    """Return a path that another command can use from the current directory."""
    del root  # Paths are records now, so they must not depend on a scan root.
    try:
        relative = os.path.relpath(path, Path.cwd())
    except (OSError, ValueError):
        return str(path)
    if relative == "." or relative.startswith("../"):
        return relative
    return "./" + relative


def render_dir(analysis: DirAnalysis, opts: RenderOptions) -> list[str]:
    """Render one tab-separated folder record.

    The columns are score, verdict, file count, path, and finding codes.  Keeping
    the numeric score first makes the default stream directly useful with
    ``sort -n`` while the path remains an executable operand for tools such as
    ``xargs``.
    """
    if not analysis.judged:
        return []

    verdict = _paint(
        _VERDICT_LABELS[analysis.verdict],
        _COLOURS[analysis.verdict] + _BOLD,
        opts.colour,
    )
    codes = ",".join(finding.code for finding in analysis.findings) or "-"
    return [
        "\t".join(
            (
                f"{analysis.score:g}",
                verdict,
                str(analysis.n_files),
                _display_path(analysis.path, opts.root),
                codes,
            )
        )
    ]


def render_text(analyses: list[DirAnalysis], opts: RenderOptions) -> str:
    """Render selected folders as newline-delimited TSV records."""
    shown = visible_analyses(analyses, opts)
    return "\n".join(
        render_dir(analysis, opts)[0]
        for analysis in sorted(shown, key=lambda a: (-a.score, str(a.path)))
    )


def visible_analyses(
    analyses: list[DirAnalysis], opts: RenderOptions
) -> list[DirAnalysis]:
    """Select findings by default and all judged folders only on request."""
    judged = [analysis for analysis in analyses if analysis.judged]
    if opts.show_all:
        return judged
    return [
        analysis
        for analysis in judged
        if analysis.findings and analysis.verdict >= opts.min_verdict
    ]


def to_dict(analysis: DirAnalysis) -> dict:
    return {
        "path": str(analysis.path),
        "judged": analysis.judged,
        "skip_reason": analysis.skip_reason.value if analysis.skip_reason else None,
        "files": analysis.n_files,
        "truncated": analysis.truncated,
        "score": analysis.score,
        "verdict": _VERDICT_LABELS[analysis.verdict],
        "clusters": analysis.clusters,
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
        "folders": [to_dict(a) for a in visible_analyses(analyses, opts)],
    }
    return json.dumps(payload, indent=2, default=str)


def render_json_lines(analyses: list[DirAnalysis], opts: RenderOptions) -> str:
    """One compact JSON object per selected folder."""
    return "\n".join(
        json.dumps({"root": str(opts.root), **to_dict(analysis)}, default=str)
        for analysis in visible_analyses(analyses, opts)
    )


class ProgressPrinter:
    """Write tree-walk progress to stderr."""

    #: Minimum interval between live-terminal updates.
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
        parts = path.parts[-3:]
        return "/".join(parts)

    def done(self, analyses: list) -> None:
        """Write a closing summary."""
        elapsed = time.monotonic() - self._started
        judged = sum(1 for a in analyses if getattr(a, "judged", False))
        summary = (
            f"  read {self._files} files in {self._folders} folders, "
            f"judged {judged}, in {elapsed:.1f}s"
        )
        self._stream.write(_paint(summary, _DIM, self._colour) + "\n")
        self._stream.flush()
