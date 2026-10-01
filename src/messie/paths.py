"""Paths rendered consistently in command-line output."""

from __future__ import annotations

from pathlib import Path


def display_path(path: Path) -> str:
    """Use a relative path within the working directory, otherwise an absolute path."""
    try:
        relative = path.relative_to(Path.cwd())
    except (OSError, ValueError):
        return str(path)
    return "." if relative == Path(".") else f"./{relative}"
