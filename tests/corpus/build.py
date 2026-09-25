"""Build deterministic example folders."""

from __future__ import annotations

import os
import random
import time
from pathlib import Path

from corpus import EXTENSIONS, TOPICS
from corpus.synth import write_empty, write_file, write_image, write_plain

DAY = 86400.0


def age(path: Path, days: float) -> Path:
    """Backdate a file, for the signals that care about when things arrived."""
    stamp = time.time() - days * DAY
    os.utime(path, (stamp, stamp))
    return path


def _pick_ext(topic: str, rng: random.Random, kinds: tuple[str, ...] | None) -> str:
    choices = kinds or EXTENSIONS.get(topic, ("txt",))
    return rng.choice(list(choices))


#: Suffixes for distinct documents on the same subject.
_SUFFIXES = ("part two", "continued", "appendix", "later notes", "addendum",
             "follow up", "second pass", "extra")


def _vary(stem: str, text: str, round_number: int) -> tuple[str, str]:
    """Vary a source document without changing its topic."""
    if round_number == 0:
        return stem, text

    sentences = [part.strip() for part in text.split(". ") if part.strip()]
    pivot = round_number % max(1, len(sentences))
    rotated = sentences[pivot:] + sentences[:pivot]
    suffix = _SUFFIXES[(round_number - 1) % len(_SUFFIXES)]
    body = ". ".join(rotated).rstrip(".") + "."
    body += f" Filed under reference {1000 + round_number * 37} ({suffix})."
    return f"{stem} {suffix}", body


def _unique(folder: Path, stem: str, ext: str) -> Path:
    candidate = folder / f"{stem}.{ext}"
    n = 2
    while candidate.exists():
        candidate = folder / f"{stem} ({n}).{ext}"
        n += 1
    return candidate


def add_topic(
    folder: Path,
    topic: str,
    count: int | None = None,
    *,
    seed: int = 0,
    kinds: tuple[str, ...] | None = None,
    age_days: float | None = None,
) -> list[Path]:
    """Drop ``count`` files on one subject into ``folder``."""
    rng = random.Random(f"{topic}:{seed}")
    source = list(TOPICS[topic])
    total = len(source) if count is None else count

    items = []
    for index in range(total):
        stem, text = source[index % len(source)]
        items.append(_vary(stem, text, index // len(source)))

    written = []
    for stem, text in items:
        path = write_file(_unique(folder, stem, _pick_ext(topic, rng, kinds)), text)
        if age_days is not None:
            age(path, age_days + rng.uniform(0, 30))
        written.append(path)
    return written


def build_coherent(folder: Path, topic: str, count: int = 8, *, seed: int = 0) -> Path:
    """Build a single-subject folder."""
    add_topic(folder, topic, count, seed=seed)
    return folder


def build_mixed(
    folder: Path, spec: dict[str, int], *, seed: int = 0, kinds: tuple[str, ...] | None = None
) -> Path:
    """Several subjects sharing one folder, ``{topic: how many}``."""
    for index, (topic, count) in enumerate(spec.items()):
        add_topic(folder, topic, count, seed=seed + index, kinds=kinds)
    return folder


def build_assorted(folder: Path, count: int = 20, *, seed: int = 0) -> Path:
    """Build a folder with one file from each subject."""
    rng = random.Random(f"assorted:{seed}")
    topics = rng.sample(list(TOPICS), min(count, len(TOPICS)))
    for index, topic in enumerate(topics):
        stem, text = TOPICS[topic][index % len(TOPICS[topic])]
        ext = rng.choice(list(EXTENSIONS.get(topic, ("txt",))))
        write_file(_unique(folder, stem, ext), text)
    return folder


def build_album(folder: Path, count: int = 20, *, seed: int = 0, prefix: str = "DSC") -> Path:
    """Build an album with opaque image names."""
    rng = random.Random(f"album:{seed}")
    for i in range(count):
        ext = rng.choice(["jpg", "jpg", "jpg", "heic", "png"])
        write_image(folder / f"{prefix}_{1000 + i:04d}.{ext}", size=18_000 + i * 97)
    return folder


def build_media_library(folder: Path, count: int = 15, *, seed: int = 0) -> Path:
    """Build a media library."""
    rng = random.Random(f"media:{seed}")
    for i in range(count):
        ext = rng.choice(["mp3", "mp3", "m4a", "flac"])
        write_file(folder / f"track_{i + 1:02d}_untitled_song.{ext}", "")
    return folder


def add_debris(folder: Path, *, seed: int = 0) -> list[Path]:
    """Lock files, partial downloads, OS droppings, never-named files."""
    paths = [
        write_plain(folder / "~$quarterly summary.docx", ""),
        write_plain(folder / ".DS_Store", "\x00\x00bud1"),
        write_plain(folder / "statement.pdf.crdownload", "partial download"),
        write_plain(folder / "notes.txt.tmp", "scratch"),
        write_empty(folder / "Untitled 3.txt"),
        write_empty(folder / "New Text Document (2).txt"),
    ]
    return paths


def add_version_pileup(
    folder: Path, stem: str = "lease agreement", ext: str = "docx"
) -> list[Path]:
    body = (
        "Tenancy agreement between the landlord and the tenant for the property, "
        "setting out the rent, the deposit and the notice period for the tenancy."
    )
    tags = ["", "_final", "_final_v2", " (copy)", " - Copy (2)"]
    return [write_file(folder / f"{stem}{tag}.{ext}", body) for tag in tags]


def add_duplicates(folder: Path, copies: int = 3) -> list[Path]:
    body = (
        "Minutes of the planning meeting. The team agreed to ship the release on "
        "Friday once the review is signed off, and to revisit staffing in the autumn."
    )
    names = ["meeting minutes.txt", "meeting minutes (1).txt", "meeting minutes copy.txt",
             "minutes FINAL.txt"]
    return [write_plain(folder / name, body) for name in names[:copies]]


def add_installers(folder: Path, *, seed: int = 0) -> list[Path]:
    names = ["ZoomInstaller.dmg", "AdobeReader_setup.exe", "node-v20.11.0.pkg",
             "obsidian_1.5.3_amd64.deb", "Blender-4.0.AppImage"]
    return [write_file(folder / name, name) for name in names]


def add_same_document_in_many_formats(
    folder: Path,
    topic: str,
    formats: tuple[str, ...] = ("docx", "pdf", "txt", "rtf", "odt"),
    *,
    index: int = 0,
) -> list[Path]:
    """Write one document in several formats."""
    stem, text = TOPICS[topic][index % len(TOPICS[topic])]
    return [write_file(folder / f"{stem}.{ext}", text) for ext in formats]


def build_named_album(folder: Path, topic: str, count: int = 12, *, seed: int = 0) -> Path:
    """Build an album with topical image names."""
    rng = random.Random(f"named-album:{seed}")
    source = TOPICS[topic]
    for i in range(count):
        stem, _ = source[i % len(source)]
        ext = rng.choice(["jpg", "jpg", "heic", "png"])
        write_image(_unique(folder, f"{stem} {i + 1:02d}", ext), size=16_000 + i * 131)
    return folder


def add_short_notes(folder: Path, topic: str, count: int = 8, *, seed: int = 0) -> list[Path]:
    """Write notes below the topic-evidence length threshold."""
    rng = random.Random(f"short:{seed}")
    source = TOPICS[topic]
    written = []
    for i in range(count):
        stem, text = source[i % len(source)]
        # Content may not contain sentence punctuation.
        line = " ".join(text.split())[:70].rstrip()
        stem, line = _vary(stem, line, i // len(source))
        ext = rng.choice(["txt", "md"])
        written.append(write_plain(_unique(folder, stem, ext), line))
    return written


def build_nested_misfile(root: Path, topic: str, other: str, *, depth: int = 3) -> Path:
    """Build a root with loose files matching a deep descendant."""
    deep = root
    for level in range(depth):
        deep = deep / f"level_{level + 1}"
    build_coherent(deep, topic, 6)
    add_topic(root, other, 6, seed=1)
    add_topic(root, topic, 3, seed=2)
    return root
