"""Scan folder entries, reading only explicit ``ignore.messie`` rules."""

from __future__ import annotations

import os
from collections import deque
from dataclasses import dataclass, field
from pathlib import Path

from messie.config import DEFAULT_SETTINGS, Settings
from messie.ignore import IgnoreRules
from messie.kinds import Domain, Kind, domain_for, kind_for


@dataclass(frozen=True)
class FileEntry:
    path: Path
    size: int
    mtime: float
    kind: Kind
    domain: Domain

    @property
    def name(self) -> str:
        return self.path.name

    @property
    def stem(self) -> str:
        return self.path.stem

    @property
    def ext(self) -> str:
        return self.path.suffix.lower().lstrip(".")


@dataclass
class DirContents:
    path: Path
    files: list[FileEntry] = field(default_factory=list)
    subdirs: list[Path] = field(default_factory=list)
    #: Files omitted because the folder exceeded ``max_files_per_dir``.
    truncated: int = 0
    #: Levels below the walk's root.
    depth: int = 0
    #: Active rules are passed to child folders during a tree walk.
    ignore_rules: tuple[IgnoreRules, ...] = field(default_factory=tuple, repr=False)

    def __len__(self) -> int:
        return len(self.files)


def _entry_for(path: Path, st: os.stat_result) -> FileEntry:
    kind = kind_for(path.suffix, path.name)
    return FileEntry(
        path=path,
        size=st.st_size,
        mtime=st.st_mtime,
        kind=kind,
        domain=domain_for(kind),
    )


def read_dir(
    path: Path,
    settings: Settings = DEFAULT_SETTINGS,
    inherited_rules: tuple[IgnoreRules, ...] = (),
) -> DirContents:
    """Record the direct children of one folder."""
    contents = DirContents(path=path)
    try:
        raw = list(os.scandir(path))
    except (PermissionError, OSError):
        return contents

    local = next((item for item in raw if item.name == "ignore.messie"), None)
    if local is not None and local.is_file(follow_symlinks=False):
        inherited_rules += (IgnoreRules.read(Path(local.path)),)
    contents.ignore_rules = inherited_rules

    for item in raw:
        name = item.name
        if name == "ignore.messie":
            continue
        if (
            name.startswith(".")
            and not settings.include_hidden
            and not _is_notable_hidden(name)
        ):
            continue
        try:
            if item.is_dir(follow_symlinks=settings.follow_symlinks):
                if not settings.is_ignored_dir(name) and not any(
                    rules.matches(Path(item.path), is_dir=True) for rules in inherited_rules
                ):
                    contents.subdirs.append(Path(item.path))
                continue
            if item.is_symlink() and not settings.follow_symlinks:
                continue
            if any(
                rules.matches(Path(item.path), is_dir=False) for rules in inherited_rules
            ):
                continue
            st = item.stat(follow_symlinks=False)
        except (PermissionError, OSError):
            continue
        contents.files.append(_entry_for(Path(item.path), st))

    if len(contents.files) > settings.max_files_per_dir:
        # Keep a deterministic sample of oversized folders.
        contents.files.sort(key=lambda f: f.path.name)
        step = len(contents.files) / settings.max_files_per_dir
        kept = [contents.files[int(i * step)] for i in range(settings.max_files_per_dir)]
        contents.truncated = len(contents.files) - len(kept)
        contents.files = kept

    contents.files.sort(key=lambda f: f.path.name)
    contents.subdirs.sort()
    return contents


def _is_notable_hidden(name: str) -> bool:
    """Hidden files that are debris worth counting even in default mode."""
    return name in {".DS_Store", ".localized"} or name.startswith("._")


def walk(root: Path, settings: Settings = DEFAULT_SETTINGS) -> list[DirContents]:
    """Every folder at or under ``root``, breadth-first, within ``max_depth``."""
    root = root.expanduser().resolve()
    if not root.is_dir():
        raise NotADirectoryError(root)

    out: list[DirContents] = []
    queue: deque[tuple[Path, int, tuple[IgnoreRules, ...]]] = deque([(root, 0, ())])
    seen: set[Path] = set()

    while queue:
        path, depth, inherited_rules = queue.popleft()
        real = path.resolve()
        if real in seen:
            continue
        seen.add(real)

        contents = read_dir(path, settings, inherited_rules)
        contents.depth = depth
        out.append(contents)
        if settings.max_depth is None or depth < settings.max_depth:
            queue.extend((sub, depth + 1, contents.ignore_rules) for sub in contents.subdirs)
    return out
