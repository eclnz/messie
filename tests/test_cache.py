"""Persistent evidence cache behavior."""

from __future__ import annotations

import os

import messie.analyze as analyze_module
import numpy as np
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


class _CountingEmbedder:
    name = "counting"
    scale = 0.5
    cache_key = "tests:counting:v1"

    def __init__(self):
        self.calls: list[list[str]] = []

    def encode(self, texts):
        self.calls.append(list(texts))
        out = np.zeros((len(texts), 4), dtype=np.float32)
        for index, text in enumerate(texts):
            out[index, hash(text) % 4] = 1.0
        return out


def test_embedding_inputs_are_deduplicated_batched_and_persisted(tmp_path, monkeypatch):
    monkeypatch.setenv("MESSIE_CACHE_DIR", str(tmp_path / "cache"))
    folder = tmp_path / "files"
    folder.mkdir()
    for index in range(6):
        (folder / f"shared-{index}.txt").write_text("one shared body " * 20)

    first = _CountingEmbedder()
    analyze_dir(folder, embedder=first)
    assert [len(call) for call in first.calls] == [1, 1]

    second = _CountingEmbedder()
    analyze_dir(folder, embedder=second)
    assert second.calls == []
