"""What a binary file says about itself.

``metadata.py`` is the one module that reads bytes it did not put there, and
the one carrying an optional dependency, so it is tested directly rather than
only through a verdict. Two properties matter more than any particular phrase:

* a describer that cannot make sense of a file returns ``""`` — a damaged zip,
  a font truncated mid-table and a zero-byte file must all come back empty
  rather than raise, because a scan of a real folder will meet all three;
* the phrase is *words*, not numbers alone. "4032x3024" and "1920x1080" are two
  terse strings to an embedding and nothing more, which is why the EXIF
  category words exist and why they are asserted on here.
"""

from __future__ import annotations

import struct
import tarfile
import zipfile
from pathlib import Path

import pytest

from messie.metadata import (
    _category_words,
    _clip,
    _describe_archive,
    _describe_font,
    _describe_image,
    _gif_size,
    _jpeg_size,
    _png_size,
    describe,
)
from messie.scan import read_dir

FONT_ROOTS = ("/usr/share/fonts", "/Library/Fonts", "/System/Library/Fonts")


def entry_for(path: Path):
    """The FileEntry a scan would produce for one real file."""
    return next(f for f in read_dir(path.parent).files if f.path.name == path.name)


# --- archives ---------------------------------------------------------------


def test_a_zip_is_described_by_its_members(tmp_path):
    path = tmp_path / "holiday.zip"
    with zipfile.ZipFile(path, "w") as archive:
        for name in ("beach_sunset.jpg", "hotel-booking.pdf", "flight_itinerary.pdf"):
            archive.writestr(name, b"x")

    words = _describe_archive(path).split()
    assert {"beach", "sunset", "hotel", "booking", "flight", "itinerary"} <= set(words)


def test_two_archives_of_different_things_share_no_words(tmp_path):
    """The whole point: a zip of holiday photos and a zip of tax papers are
    plainly different things, and the manifest is what says so."""
    holiday, taxes = tmp_path / "trip.zip", tmp_path / "taxes.zip"
    with zipfile.ZipFile(holiday, "w") as archive:
        archive.writestr("crete/beach_sunset.jpg", b"x")
        archive.writestr("crete/harbour_boats.jpg", b"x")
    with zipfile.ZipFile(taxes, "w") as archive:
        archive.writestr("2023/income_statement.pdf", b"x")
        archive.writestr("2023/mortgage_interest.pdf", b"x")

    assert not set(_describe_archive(holiday).split()) & set(_describe_archive(taxes).split())


def test_a_tar_is_read_the_same_way(tmp_path):
    member = tmp_path / "quarterly_revenue.csv"
    member.write_text("a,b\n1,2\n", encoding="utf-8")
    path = tmp_path / "reports.tar.gz"
    with tarfile.open(path, "w:gz") as archive:
        archive.add(member, arcname="reports/quarterly_revenue.csv")

    assert {"quarterly", "revenue"} <= set(_describe_archive(path).split())


def test_a_wheel_is_an_archive_despite_its_extension(tmp_path):
    """``.whl`` is not a kind messie knows, so the extension is what routes it."""
    path = tmp_path / "widgets-1.0-py3-none-any.whl"
    with zipfile.ZipFile(path, "w") as archive:
        archive.writestr("widgets/rendering.py", b"x")
        archive.writestr("widgets/layout.py", b"x")

    assert entry_for(path).kind == "unknown"
    assert {"rendering", "layout"} <= set(describe(entry_for(path)).split())


def test_a_bare_gzip_says_nothing(tmp_path):
    """No member list to read, and the original name is already in the
    filename. Attempting it would make ``is_tarfile`` decompress the lot."""
    import gzip

    path = tmp_path / "database_dump.sql.gz"
    path.write_bytes(gzip.compress(b"select * from customers;" * 200))
    assert _describe_archive(path) == ""


def test_a_damaged_archive_returns_empty(tmp_path):
    """``is_zipfile`` says yes and opening it then raises.

    A zip's member list lives in the central directory at the *end* of the
    file, so a half-written download keeps a valid-looking signature and fails
    only when something tries to read it.
    """
    path = tmp_path / "broken.zip"
    with zipfile.ZipFile(path, "w") as archive:
        archive.writestr("notes.txt", b"hello")
    data = bytearray(path.read_bytes())
    end = data.rfind(b"PK\x05\x06")
    data[end - 40 : end] = b"\x00" * 40  # shred the central directory
    path.write_bytes(bytes(data))

    assert zipfile.is_zipfile(path)
    assert _describe_archive(path) == ""


def test_a_truncated_tar_returns_empty(tmp_path):
    path = tmp_path / "half.tar"
    with tarfile.open(path, "w") as archive:
        info = tarfile.TarInfo("notes.txt")
        info.size = 5
        archive.addfile(info, __import__("io").BytesIO(b"hello"))
    path.write_bytes(path.read_bytes()[:100])

    assert _describe_archive(path) == ""


# --- fonts ------------------------------------------------------------------


def build_font(path: Path, names: dict[int, str], *, truncate: int | None = None) -> Path:
    """A minimal sfnt carrying a real name table.

    Only the offset table, one table record and the ``name`` table itself —
    which is all ``_describe_font`` reads. Strings are UTF-16BE under platform
    3, as Windows-platform records are.
    """
    records, storage = b"", b""
    for name_id in sorted(names):
        blob = names[name_id].encode("utf-16-be")
        records += struct.pack(">HHHHHH", 3, 1, 0x409, name_id, len(blob), len(storage))
        storage += blob
    name_table = struct.pack(">HHH", 0, len(names), 6 + len(records)) + records + storage

    offset = 12 + 16
    header = struct.pack(">IHHHH", 0x00010000, 1, 16, 0, 0)
    header += b"name" + struct.pack(">III", 0, offset, len(name_table))

    data = header + name_table
    path.write_bytes(data[:truncate] if truncate is not None else data)
    return path


def test_a_font_is_described_by_its_name_table(tmp_path):
    path = build_font(
        tmp_path / "serif.ttf",
        {1: "Cormorant Garamond", 2: "SemiBold Italic", 8: "Catharsis Fonts"},
    )
    words = _describe_font(path).split()
    assert words[:2] == ["Cormorant", "Garamond"]
    assert {"SemiBold", "Italic", "Catharsis", "Fonts"} <= set(words)


def test_fonts_from_different_families_do_not_look_alike(tmp_path):
    a = build_font(tmp_path / "a.ttf", {1: "Cormorant Garamond", 8: "Catharsis Fonts"})
    b = build_font(tmp_path / "b.ttf", {1: "Fira Code", 8: "Mozilla"})
    assert not set(_describe_font(a).split()) & set(_describe_font(b).split())


@pytest.mark.parametrize("cut", [0, 8, 20, 30, 40])
def test_a_truncated_font_returns_empty_rather_than_raising(tmp_path, cut):
    """A font cut off mid-table is the shape of a half-finished download, and
    a scan meets those. Every prefix must come back empty, not explode."""
    path = build_font(tmp_path / "cut.ttf", {1: "Cormorant Garamond"}, truncate=cut)
    assert _describe_font(path) == ""


def test_a_font_without_a_name_table_returns_empty(tmp_path):
    """A well-formed offset table pointing at no ``name`` at all."""
    path = tmp_path / "nameless.ttf"
    path.write_bytes(
        struct.pack(">IHHHH", 0x00010000, 1, 16, 0, 0)
        + b"glyf"
        + struct.pack(">III", 0, 28, 4)
        + b"\x00\x00\x00\x00"
    )
    assert _describe_font(path) == ""


def test_a_real_system_font_reads():
    """The synthetic font is one reading of the spec; a shipped font is the
    other. Skipped where the machine has no fonts installed."""
    fonts = [
        p
        for root in FONT_ROOTS
        if Path(root).is_dir()
        for p in sorted(Path(root).rglob("*.ttf"))[:5]
    ]
    if not fonts:
        pytest.skip("no system fonts installed")

    described = {p.name: _describe_font(p) for p in fonts}
    assert any(described.values()), f"nothing read from {list(described)}"
    for name, text in described.items():
        assert len(text) < 300, f"{name} described at length: {text[:80]}"


# --- images -----------------------------------------------------------------


def test_png_dimensions():
    header = b"\x89PNG\r\n\x1a\n" + b"\x00\x00\x00\x0dIHDR" + struct.pack(">II", 1920, 1080)
    assert _png_size(header) == "1920x1080"


def test_gif_dimensions():
    assert _gif_size(b"GIF89a" + struct.pack("<HH", 320, 240)) == "320x240"


def test_jpeg_dimensions_are_found_past_the_leading_segments():
    """The SOF marker is not at a fixed offset: JFIF and EXIF segments come
    first, and each has to be stepped over by its own length."""
    jfif = b"\xff\xe0" + struct.pack(">H", 16) + b"JFIF\x00" + b"\x00" * 11
    sof = b"\xff\xc0" + struct.pack(">H", 17) + b"\x08" + struct.pack(">HH", 3024, 4032)
    assert _jpeg_size(b"\xff\xd8" + jfif + sof + b"\x00" * 8) == "4032x3024"


@pytest.mark.parametrize(
    "data",
    [b"", b"\x89PNG", b"GIF8", b"\xff\xd8", b"not an image at all"],
    ids=["empty", "png-stub", "gif-stub", "jpeg-stub", "junk"],
)
def test_truncated_image_headers_yield_nothing(data):
    assert _png_size(data) == _jpeg_size(data) == _gif_size(data) == ""


def test_an_unreadable_image_returns_empty(tmp_path):
    path = tmp_path / "corrupt.png"
    path.write_bytes(b"\x89PNG\r\n\x1a\n" + b"\x00" * 40)
    assert _describe_image(path) == ""


# --- EXIF categories --------------------------------------------------------
#
# ``_category_words`` is a pure function of the tag dictionary, so the words it
# chooses are tested without needing Pillow. The end-to-end tests below need a
# real image with real EXIF, so those ask for it.


def test_camera_tags_say_photograph():
    words = _category_words(
        {"Make": "NIKON CORPORATION", "Model": "D7000", "DateTimeOriginal": "2019:07:14 11:02:03"}
    )
    assert words[0] == "photograph"
    assert "2019" in words


def test_scanner_software_says_scanned():
    assert _category_words({"Software": "EPSON Scan 2"})[0] == "scanned"


def test_screenshot_software_says_screenshot():
    assert _category_words({"Software": "Screenshot"})[0] == "screenshot"


def test_a_camera_wins_over_software():
    """Phones write both. What produced the pixels is the camera."""
    tags = {"Make": "Apple", "Model": "iPhone 13", "Software": "16.1 Screenshot-ish"}
    assert _category_words(tags)[0] == "photograph"


def test_no_tags_say_nothing():
    assert _category_words({}) == []


def test_unknown_software_is_named_without_a_category():
    words = _category_words({"Software": "GIMP 2.10"})
    assert words[0] == "image"
    assert "GIMP 2.10" in words


def write_image(path: Path, size: tuple[int, int], tags: dict[str, str]) -> Path:
    from PIL import ExifTags, Image

    ids = {name: tag for tag, name in ExifTags.TAGS.items()}
    exif = Image.Exif()
    for name, value in tags.items():
        exif[ids[name]] = value
    Image.new("RGB", size, (10, 20, 30)).save(path, exif=exif)
    return path


def test_a_photograph_and_a_scan_describe_themselves_differently(tmp_path):
    """The case that brought EXIF back: not one camera roll against another,
    but a folder mixing *kinds* of image."""
    pytest.importorskip("PIL")
    photo = write_image(
        tmp_path / "DSC_0142.jpg", (4032, 3024), {"Make": "NIKON", "Model": "D7000"}
    )
    scan = write_image(tmp_path / "page_03.png", (2480, 3508), {"Software": "EPSON Scan 2"})

    assert _describe_image(photo).startswith("photograph")
    assert "4032x3024" in _describe_image(photo)
    assert _describe_image(scan).startswith("scanned")


def test_dimensions_alone_when_there_is_no_exif(tmp_path):
    pytest.importorskip("PIL")
    from PIL import Image

    path = tmp_path / "plain.png"
    Image.new("RGB", (800, 600)).save(path)
    assert _describe_image(path) == "800x600"


# --- clipping ---------------------------------------------------------------


def test_repeated_words_are_said_once():
    assert _clip(["invoice", "Invoice", "invoice", "2023"]) == "invoice 2023"


def test_a_description_is_capped():
    assert len(_clip([f"word{i}" for i in range(500)]).split()) == 40


def test_an_image_description_stays_under_the_judging_floor(tmp_path):
    """This is what keeps photo albums out of the coherence reckoning.

    ``unattached_files`` only judges files with at least ``min_text_chars`` of
    text, so as long as an image's description stays below that line, a folder
    of pictures can never read as a pile of unrelated things.
    """
    pytest.importorskip("PIL")
    from messie.config import DEFAULT_SETTINGS

    photo = write_image(
        tmp_path / "DSC_0142.jpg",
        (4032, 3024),
        {"Make": "NIKON CORPORATION", "Model": "NIKON D7000", "Software": "Ver.1.01"},
    )
    assert len(_describe_image(photo)) < DEFAULT_SETTINGS.min_text_chars


def test_an_archive_of_thousands_of_members_is_still_short(tmp_path):
    path = tmp_path / "huge.zip"
    with zipfile.ZipFile(path, "w") as archive:
        for i in range(2000):
            archive.writestr(f"module_{i}/widget_{i}.py", b"x")
    assert len(_describe_archive(path).split()) <= 40


# --- dispatch ---------------------------------------------------------------


def test_a_zero_byte_file_says_nothing(tmp_path):
    for name in ("empty.zip", "empty.ttf", "empty.png"):
        (tmp_path / name).write_bytes(b"")
    for entry in read_dir(tmp_path).files:
        assert describe(entry) == ""


def test_text_files_are_not_metadata_s_business(tmp_path):
    """Prose is ``extract_text``'s job. ``describe`` speaks for the files it
    cannot read, and stays silent about the rest."""
    (tmp_path / "notes.txt").write_text("a real document with real words", encoding="utf-8")
    (tmp_path / "report.pdf").write_bytes(b"%PDF-1.4\n")
    for entry in read_dir(tmp_path).files:
        assert describe(entry) == ""


def test_describe_never_raises_on_a_file_lying_about_its_type(tmp_path):
    """Extensions are claims, not facts. Every one of these is mislabelled."""
    (tmp_path / "actually_text.zip").write_text("hello, not a zip at all", encoding="utf-8")
    (tmp_path / "actually_zip.ttf").write_bytes(b"PK\x03\x04" + b"\x00" * 60)
    (tmp_path / "actually_font.png").write_bytes(b"\x00\x01\x00\x00" + b"\x00" * 60)

    for entry in read_dir(tmp_path).files:
        assert isinstance(describe(entry), str)
