"""Explicit, tree-local exclusions from ``ignore.messie`` files."""

from __future__ import annotations

from dataclasses import dataclass
from fnmatch import fnmatchcase
from pathlib import Path


@dataclass(frozen=True)
class IgnorePattern:
    parts: tuple[str, ...]
    directory_only: bool
    basename_only: bool

    @classmethod
    def parse(cls, line: str) -> IgnorePattern:
        directory_only = line.endswith("/")
        parts = tuple(part for part in line.strip("/").split("/") if part)
        return cls(parts, directory_only, len(parts) == 1 and not line.startswith("/"))

    def matches(self, relative: Path, *, is_dir: bool) -> bool:
        if self.directory_only and not is_dir:
            return False
        path_parts = relative.parts
        if self.basename_only:
            return fnmatchcase(path_parts[-1], self.parts[0])
        return _match_parts(path_parts, self.parts)


def _match_parts(path: tuple[str, ...], pattern: tuple[str, ...]) -> bool:
    """Match path segments; only ``**`` crosses directory boundaries."""
    if not pattern:
        return not path
    if pattern[0] == "**":
        return _match_parts(path, pattern[1:]) or (
            bool(path) and _match_parts(path[1:], pattern)
        )
    return bool(path) and fnmatchcase(path[0], pattern[0]) and _match_parts(
        path[1:], pattern[1:]
    )


@dataclass(frozen=True)
class IgnoreRules:
    base: Path
    patterns: tuple[IgnorePattern, ...]

    @classmethod
    def read(cls, path: Path) -> IgnoreRules:
        try:
            lines = path.read_text(encoding="utf-8").splitlines()
        except UnicodeError as exc:
            raise OSError(f"{path}: ignore.messie must be UTF-8 text") from exc
        patterns = tuple(
            IgnorePattern.parse(line.strip())
            for line in lines
            if line.strip() and not line.lstrip().startswith("#")
        )
        return cls(path.parent, patterns)

    def matches(self, path: Path, *, is_dir: bool) -> bool:
        relative = path.relative_to(self.base)
        return any(pattern.matches(relative, is_dir=is_dir) for pattern in self.patterns)
