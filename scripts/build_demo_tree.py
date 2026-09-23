#!/usr/bin/env python3
"""Build a realistic home directory to try messie against.

    python scripts/build_demo_tree.py /tmp/demo && messie /tmp/demo --all

Everything written is synthetic and deterministic for a given seed: real files
of thirty-odd types, on forty-odd subjects, arranged into folders that range
from genuinely tidy to hopeless. Nothing here is anybody's real data.
"""

from __future__ import annotations

import argparse
import random
import shutil
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "tests"))

from corpus import DEV_TOPICS, OFFICE_TOPICS, PERSONAL_TOPICS  # noqa: E402
from corpus.build import (  # noqa: E402
    add_debris,
    add_duplicates,
    add_installers,
    add_topic,
    add_version_pileup,
    age,
    build_album,
    build_assorted,
    build_coherent,
    build_media_library,
)


def build(root: Path, seed: int = 0) -> Path:
    rng = random.Random(seed)
    office = list(OFFICE_TOPICS)
    dev = list(DEV_TOPICS)
    personal = list(PERSONAL_TOPICS)

    # A drawer: unrelated subjects, several file kinds, and a lot of leftovers.
    downloads = root / "Downloads"
    for topic, years in ((office[0], 0.2), (personal[0], 1.4), (dev[0], 2.6)):
        for path in add_topic(downloads, topic, 4, seed=seed):
            age(path, years * 365)
    add_installers(downloads)
    add_debris(downloads)
    add_duplicates(downloads)
    add_version_pileup(downloads)
    build_album(downloads, 8, seed=seed, prefix="IMG")

    # Loose paperwork sitting next to the folder it resembles.
    documents = root / "Documents"
    add_topic(documents, personal[1], 5, seed=seed)
    build_coherent(documents / "Taxes", office[0], 6, seed=seed + 1)
    for path in add_topic(documents, office[0], 3, seed=seed + 9):
        age(path, 1500)

    # Folders that are genuinely fine, and must be left alone.
    build_album(root / "Pictures" / "Wedding", 24, seed=seed)
    build_media_library(root / "Music" / "Albums", 16, seed=seed)
    build_coherent(root / "Projects" / "ledger-api", dev[0], 8, seed=seed)
    build_coherent(root / "Work" / "Invoices", office[1], 9, seed=seed)

    # Every file about something different: the hardest case there is.
    build_assorted(root / "Desktop", 18, seed=seed)

    # A big flat pile, of one subject but far too many of it.
    heap = root / "Archive" / "Scans"
    pool = rng.sample(office + personal, 1)
    add_topic(heap, pool[0], 60, seed=seed)

    return root


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("path", nargs="?", default="/tmp/messie-demo")
    parser.add_argument("--seed", type=int, default=0)
    parser.add_argument("--force", action="store_true", help="replace an existing tree")
    args = parser.parse_args(argv)

    root = Path(args.path).expanduser()
    if root.exists():
        if not args.force:
            print(f"{root} already exists; pass --force to replace it", file=sys.stderr)
            return 2
        shutil.rmtree(root)

    build(root, args.seed)
    files = sum(1 for p in root.rglob("*") if p.is_file())
    kinds = len({p.suffix.lower() for p in root.rglob("*") if p.is_file()})
    print(f"{root}: {files} files, {kinds} extensions")
    print(f"\nnow try:  messie {root} --all")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
