"""Example datasets: realistic folders of many file kinds, on many subjects.

Three corpora supply the prose — office documents, developer files and personal
files — and :mod:`corpus.synth` turns any of it into a real file of whatever
type is asked for. :mod:`corpus.build` composes those into whole folders:
coherent ones, mixed ones, photo albums, and the hardest case of all, a folder
where every single file is about something different.
"""

from __future__ import annotations

from corpus import accented, dev, office, personal

#: topic key -> [(filename_stem, body_text), ...]
TOPICS: dict[str, list[tuple[str, str]]] = {
    **office.TOPICS,
    **dev.TOPICS,
    **personal.TOPICS,
    **accented.TOPICS,
}

#: topic key -> plausible extensions for that subject
EXTENSIONS: dict[str, tuple[str, ...]] = {
    **office.EXTENSIONS,
    **dev.EXTENSIONS,
    **personal.EXTENSIONS,
    **accented.EXTENSIONS,
}

OFFICE_TOPICS = tuple(office.TOPICS)
DEV_TOPICS = tuple(dev.TOPICS)
PERSONAL_TOPICS = tuple(personal.TOPICS)
#: Subjects written in English but thick with diacritics.
ACCENTED_TOPICS = tuple(accented.TOPICS)
ALL_TOPICS = tuple(TOPICS)


def entries(topic: str) -> list[tuple[str, str]]:
    return TOPICS[topic]


def extensions(topic: str) -> tuple[str, ...]:
    return EXTENSIONS.get(topic, ("txt",))


__all__ = [
    "ACCENTED_TOPICS", "ALL_TOPICS", "DEV_TOPICS", "EXTENSIONS", "OFFICE_TOPICS",
    "PERSONAL_TOPICS", "TOPICS", "entries", "extensions",
]
