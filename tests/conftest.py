"""Fixtures that build real folders on disk.

messie reads files, so its tests use real ones — including genuine .docx
archives, since stdlib OOXML extraction is a load-bearing part of the tool.
"""

from __future__ import annotations

import zipfile
from pathlib import Path

import pytest

from messie.config import DEFAULT_SETTINGS

_OOXML_NS = "http://schemas.openxmlformats.org"

_CONTENT_TYPES = (
    '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
    f'<Types xmlns="{_OOXML_NS}/package/2006/content-types">'
    '<Default Extension="xml" ContentType="application/xml"/>'
    '<Override PartName="/word/document.xml" ContentType="application/vnd'
    '.openxmlformats-officedocument.wordprocessingml.document.main+xml"/>'
    "</Types>"
)

_RELS = (
    '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
    f'<Relationships xmlns="{_OOXML_NS}/package/2006/relationships">'
    '<Relationship Id="rId1" '
    f'Type="{_OOXML_NS}/officeDocument/2006/relationships/officeDocument" '
    'Target="word/document.xml"/>'
    "</Relationships>"
)


def write_docx(path: Path, paragraphs: list[str]) -> Path:
    """A real, minimal .docx — a zip of XML, exactly as Word writes it."""
    body = "".join(
        f"<w:p><w:r><w:t>{p}</w:t></w:r></w:p>" for p in paragraphs
    )
    document = (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">'
        f"<w:body>{body}</w:body></w:document>"
    )
    path.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(path, "w", zipfile.ZIP_DEFLATED) as zf:
        zf.writestr("[Content_Types].xml", _CONTENT_TYPES)
        zf.writestr("_rels/.rels", _RELS)
        zf.writestr("word/document.xml", document)
    return path


def write_text(path: Path, text: str) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    return path


def write_blob(path: Path, size: int = 2048, seed: bytes = b"\x89PNG") -> Path:
    """A binary file with no readable text, standing in for a photo."""
    path.parent.mkdir(parents=True, exist_ok=True)
    filler = (seed + bytes(range(256))) * (size // 260 + 1)
    path.write_bytes(filler[:size])
    return path


# --- corpora ---------------------------------------------------------------

# Each corpus repeats its own domain vocabulary, the way real documents of a
# kind do. Without that the lexical backend has nothing to go on — it matches
# words, not meanings.
TAX = [
    "IRS form W-2: wage and tax statement for the tax filing year. Federal "
    "income tax withheld is reported to the revenue service.",
    "Total taxable income and federal income tax withheld for the tax year, "
    "with social security wages reported on the tax return.",
    "Tax deductions claimed on this return: mortgage interest, charitable "
    "contributions and state income tax paid during the tax year.",
    "This tax return was prepared and submitted to the revenue service, with "
    "taxable income and deductions assessed for the filing year.",
]
# Chapters of one novel: recurring people and places, as real chapters have.
NOVEL = [
    "Chapter one. The rain had not stopped for three days and the house above the "
    "dunes was cold. Marta listened to the sea and did not open the door.",
    "Chapter two. Marta walked down to the sea in the rain. The house behind her "
    "stayed dark, and the dunes gave back nothing but wind.",
    "Chapter three. The house was colder still. Marta read the same page of the "
    "manuscript eleven times, listening for the sea beyond the dunes.",
    "Chapter four. The manuscript lay unfinished on the desk in the cold house, "
    "and Marta watched the rain come in off the sea.",
]
INVOICE = [
    "Invoice number 1043. Consulting hours billed to the client account, "
    "payment due within thirty days of this invoice date.",
    "Invoice for professional services rendered to the client. Hours billed at "
    "the agreed hourly rate, payment due on receipt.",
    "Invoice summary: hourly rate, total hours billed, subtotal, VAT and the "
    "amount payable by the client.",
    "Remittance advice for this invoice: please quote the invoice number when "
    "making payment for the hours billed.",
]
RECIPE = [
    "Preheat the oven to 180 degrees and grease a loaf tin with butter before "
    "you fold the flour and sugar into the batter.",
    "Whisk the eggs and sugar until pale, then fold in the flour and baking "
    "powder and pour the batter into the greased tin.",
    "Bake the batter in the oven for forty minutes until a skewer pushed into "
    "the centre of the loaf comes out clean.",
    "Serve the loaf warm with cream. Bake it fresh; it keeps in an airtight "
    "tin for three days.",
]


@pytest.fixture
def embedder():
    """The default backend, shared across tests: loading it is cached."""
    from messie.embed import get_embedder

    return get_embedder("wordllama")


@pytest.fixture
def settings():
    return DEFAULT_SETTINGS


@pytest.fixture
def mixed_docx_dir(tmp_path: Path) -> Path:
    """The motivating case: one file type, three unrelated subjects."""
    folder = tmp_path / "Documents"
    for i, line in enumerate(TAX):
        write_docx(folder / f"tax_return_{2019 + i}.docx", [line] * 3)
    for i, line in enumerate(NOVEL):
        write_docx(folder / f"chapter_{i + 1:02d}.docx", [line] * 3)
    for i, line in enumerate(INVOICE):
        write_docx(folder / f"invoice_{1040 + i}.docx", [line] * 3)
    return folder


#: Further tax sentences, so the coherent fixture has twelve *distinct*
#: documents rather than one document repeated (which would be a real finding).
MORE_TAX = [
    "Schedule A itemised deductions worksheet attached for review.",
    "Employer identification number and payer details for the filing year.",
    "Estimated quarterly payment voucher submitted in April.",
    "Capital gains from the sale of shares reported separately.",
    "Interest income statement from the savings account provider.",
    "Health insurance coverage statement for the household.",
    "Property tax assessment notice from the county assessor.",
    "Retirement contribution summary for the workplace pension plan.",
]


@pytest.fixture
def coherent_docx_dir(tmp_path: Path) -> Path:
    """Same file type, same subject, all distinct: not a mess."""
    folder = tmp_path / "Tax"
    for i, line in enumerate(TAX + MORE_TAX):
        write_docx(
            folder / f"tax_document_{i:02d}.docx",
            [line, "Filed with the revenue service.", f"Reference number {i}."],
        )
    return folder


class FakeEmbedder:
    """A deterministic stand-in with exactly controllable topics.

    Any text containing a marker word becomes that marker's basis vector, so
    same-topic pairs score 1.0 and different-topic pairs score 0.0. This lets
    the signal tests assert on logic rather than on a model's judgement.
    """

    name = "fake"
    scale = 0.5
    MARKERS = ("alpha", "beta", "gamma", "delta")

    def encode(self, texts):
        import numpy as np

        out = np.zeros((len(texts), len(self.MARKERS)), dtype=np.float32)
        for row, text in enumerate(texts):
            lowered = text.lower()
            for col, marker in enumerate(self.MARKERS):
                if marker in lowered:
                    out[row, col] = 1.0
        norms = np.linalg.norm(out, axis=1, keepdims=True)
        return out / np.where(norms == 0, 1.0, norms)


@pytest.fixture
def fake_embedder():
    return FakeEmbedder()


def snapshot(root: Path) -> dict[str, tuple[int, float]]:
    """Every file under root with its size and mtime."""
    return {
        str(p.relative_to(root)): (p.stat().st_size, p.stat().st_mtime)
        for p in sorted(root.rglob("*"))
        if p.is_file()
    }


# --- shared helpers ---------------------------------------------------------
#
# These lived in three test modules apiece. conftest is already on the import
# path for every test file, so this is where one copy belongs.

#: Backends that compare meaning, best first. One, since model2vec and
#: sentence-transformers were measured and dropped — see messie/embed. The list
#: and the parametrisation around it are kept so that adding a candidate
#: backend means adding a name here, not rebuilding the test suite.
SEMANTIC_BACKENDS = ["wordllama"]


def backend_or_skip(name: str):
    """The named backend, or skip the test if it is not installed."""
    from messie.embed import get_embedder

    try:
        return get_embedder(name)
    except Exception as exc:  # noqa: BLE001
        pytest.skip(f"{name} unavailable: {exc}")


def installed(names: list[str]) -> list[str]:
    """Which of ``names`` can actually be loaded.

    Resolved once at collection so absent backends do not litter a run with
    hundreds of skipped parametrisations.
    """
    from messie.embed import get_embedder

    out = []
    for name in names:
        try:
            get_embedder(name)
        except Exception:  # noqa: BLE001
            continue
        out.append(name)
    return out


def codes(analysis) -> set[str]:
    """The finding codes an analysis produced."""
    return {f.code for f in analysis.findings}


def finding(analysis, code: str):
    """The one finding with this code. Raises if the signal stayed quiet."""
    return next(f for f in analysis.findings if f.code == code)
