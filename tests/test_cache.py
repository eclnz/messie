"""Persistent evidence cache behavior."""

from __future__ import annotations

import os

import messie.analyze as analyze_module
from messie.analyze import analyze_dir


def test_second_analysis_reuses_extracted_text(tmp_path, fake_embedder, monkeypatch):
    monkeypatch.setenv("MESSIE_CACHE_DIR", str(tmp_path / "cache"))
    folder = tmp_path / "files"
    folder.mkdir()
    for index in range(6):
        (folder / f"note-{index}.txt").write_text(f"shared subject material {index} " * 20)

    calls = 0
    original = analyze_module.extract_text

    def counted(entry, settings):
        nonlocal calls
        calls += 1
        return original(entry, settings)

    monkeypatch.setattr(analyze_module, "extract_text", counted)
    analyze_dir(folder, embedder=fake_embedder)
    assert calls == 6

    analyze_dir(folder, embedder=fake_embedder)
    assert calls == 6

    changed = folder / "note-0.txt"
    before = changed.stat()
    changed.write_text("changed subject material 0 " * 20)
    os.utime(changed, ns=(before.st_atime_ns, before.st_mtime_ns + 1_000_000_000))

    analyze_dir(folder, embedder=fake_embedder)
    assert calls == 7
