"""Scan folder entries without opening files."""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path

from messie.config import DEFAULT_SETTINGS, Settings
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


def read_dir(path: Path, settings: Settings = DEFAULT_SETTINGS) -> DirContents:
    """Record the direct children of one folder."""
    contents = DirContents(path=path)
    try:
        raw = list(os.scandir(path))
    except (PermissionError, OSError):
        return contents

    for item in raw:
        name = item.name
        if (
            name.startswith(".")
            and not settings.include_hidden
            and not _is_notable_hidden(name)
        ):
            continue
        try:
            if item.is_dir(follow_symlinks=settings.follow_symlinks):
                if not settings.is_ignored_dir(name):
                    contents.subdirs.append(Path(item.path))
                continue
            if item.is_symlink() and not settings.follow_symlinks:
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
    queue: list[tuple[Path, int]] = [(root, 0)]
    seen: set[Path] = set()

    while queue:
        path, depth = queue.pop(0)
        real = path.resolve()
        if real in seen:
            continue
        seen.add(real)

        contents = read_dir(path, settings)
        out.append(contents)
        if depth < settings.max_depth:
            queue.extend((sub, depth + 1) for sub in contents.subdirs)
    return out
