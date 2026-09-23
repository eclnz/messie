# messie

Notices when a folder has become a mess.

It does not tidy anything. It never moves, renames or deletes a file, and it
does not propose a filing scheme — what belongs where is your call. All it does
is read what is actually in a folder and tell you, with evidence, when unrelated
things have ended up living together.

Everything runs on your machine. No API keys, no accounts, no network calls
during analysis.

```
$ messie ~/Downloads

~/Downloads                                    CHAOTIC  89.7/100   30 files · wordllama
  4 unrelated things are living in this folder.
      · no shared wording              9 files  2023   IMG_4400.jpg, IMG_4401.jpg +7
      · agreement · lease · meeting    6 files  2026   lease agreement.txt +5
      · invoice · billed · hours       4 files  2026   invoice_1040.docx +3
      · batter · into · loaf           4 files  2025   banana_bread_recipe_0.md +3
  6 files here are copies of something else here.
  4 different sorts of file are mixed together here.
      11 text, 9 image, 4 document, 3 installer
  4 files here are debris.
      empty, leftover  ·  .DS_Store, Untitled 3.txt, statement.pdf.crdownload
  1 pile of revisions of the same thing (4 files).
      The deepest is 'lease agreement' at 4 versions.
```

## The point

Most "folder cleaner" tools sort by extension, which means a folder holding
forty Word documents looks perfectly uniform to them. If half of those documents
are tax paperwork and half are chapters of a novel, that folder is a mess, and
only the *contents* say so.

So messie reads the files. It pulls text out of each one, embeds it locally,
groups the folder by subject, and reports when the groups have nothing to do
with each other.

## Install

```bash
pip install messie
```

That is the whole story. messie depends on
[wordllama](https://pypi.org/project/wordllama/), whose model weights ship
inside its wheel, so nothing is downloaded at analysis time — or ever — and it
works on a machine that has never been online.

`pip install 'messie[pdf]'` adds PDF text extraction.

## Use

```bash
messie                        # the current folder and its subfolders
messie ~/Documents            # somewhere specific
messie ~/Drive --depth 5      # look deeper (default 3)
messie ~/Downloads --all      # show tidy folders too
messie ~/Downloads --json     # machine-readable
messie --doctor               # which backends are available
```

Exit status is 0 while everything is below the `--fail-over` verdict (default
`messy`) and 1 once something reaches it, so it drops into a cron job or a
pre-commit hook:

```bash
messie ~/Downloads --fail-over chaotic || notify-send "your Downloads folder"
```

## What it looks for

| | |
|---|---|
| **unrelated topics** | two or more unrelated subjects sharing one folder — the main event |
| **nothing in common** | no organising subject at all: every file about something different |
| **strays** | files that match nothing else present |
| **misfiled neighbours** | loose files that read like the contents of a folder further down |
| **overcrowded** | far too many files loose in one flat folder |
| **debris** | `~$report.docx`, `.crdownload`, `.DS_Store`, zero-byte and never-named files |
| **version pileups** | `report.docx`, `report_final.docx`, `report_final_v2 (copy).docx` |
| **duplicates** | byte-identical files, and text that really is the same document twice |
| **time strata** | separate eras of stuff on separate subjects — a folder that accreted rather than got filled |

Each fires with a severity, and they combine into a 0–100 score:
**tidy** (0–24) · **lived-in** (25–49) · **messy** (50–74) · **chaotic** (75–100).

A folder with fewer than six files is reported as too small to judge rather than
being given a score.

## Backends

Text is embedded by the best backend available, and the report names the one it
used.

| backend | quality | model download | install |
|---|---|---|---|
| `wordllama` | good | **none — weights are in the wheel** | included |
| `model2vec` | better | once, from Hugging Face | `pip install 'messie[model2vec]'` |
| `sentence` | best, slowest | once, from Hugging Face | `pip install 'messie[st]'` |

There was once a hashed TF-IDF fallback for machines that could not fetch a
model. Measured across the example corpus it held only about 71% of subjects
together against wordllama's 97%, and since wordllama downloads nothing, the
fallback bought nothing but worse verdicts. It has been removed.

Pick one explicitly with `--backend`. Naming a backend that isn't installed is
an error rather than a silent downgrade: a verdict should never quietly come
from a weaker model than the one you asked for.

Thresholds are expressed as fractions of each backend's own similarity scale, so
one set of settings behaves sensibly across all of them. The `wordllama` scale
was calibrated by sweeping the threshold through the real pipeline over the
example corpus; the other two are estimates, since no model was reachable to
measure them against. Override with `--threshold`.

## Reading the contents

`.docx`, `.pptx`, `.xlsx`, `.odt` and `.epub` are read with the standard library
alone — they are zips of XML, so no third-party parser is needed. Plain text,
Markdown, HTML, CSV, source code and subtitles are read directly, with an
encoding sniff. PDFs need the `pdf` extra. Only the first 4 KB of text is used,
and never more than 1 MiB is read off disk per file.

Photos, video and audio are not opened. A file with no readable text and no
meaningful filename — `IMG_4412.HEIC` — is represented by its kind, so it groups
with the other photos instead of looking like a stray. This is why a folder of
holiday photos reads as tidy rather than as hundreds of unrelated things.

Extracted text is cached in `~/.cache/messie/`, keyed by path, size and
modification time, so re-running on a large folder is cheap. `--no-cache` turns
that off.

## Reading binaries

Photographs, music and installers cannot be read, so every one of them used to
be represented by the same stand-in phrase — `photograph picture image` for
every photograph anybody has ever taken. Three kinds of file now say something
about themselves, using the standard library alone:

- **archives** — the member list. A zip of holiday photos and a zip of tax
  papers are plainly different things, and the manifest says so.
- **fonts** — family and foundry from the sfnt name table, worth 0.60 of
  separation between real font directories where there was none.
- **images** — dimensions, which is thin, but is what stopped a real folder of
  bullet graphics fragmenting into fifteen meaningless groups.

Byte-level similarity was tried first and measured. Normalized compression
distance separates same-folder from cross-folder files by 0.72 for SVG (which
is really text) and 0.13 for shared libraries, but by only 0.016 for PNG, 0.005
for TrueType and 0.002 for gzip: compressed formats are entropy-coded, so their
bytes look random whatever the content. It cannot see photographs, so it is not
used.

EXIF and audio tags were built and then removed. Telling one camera's
photographs from another's is discrimination between things that are alike, and
a Pictures folder holding two cameras is normal rather than messy — the
capability cost two dependencies and changed no verdict. messie is for noticing
obviously mixed content, not for splitting hairs.

## What was removed, and why

Two signals were deleted after being measured against real files rather than
against fixtures:

- **garbled** flagged files whose contents had stopped being language. Across
  5,080 real files it flagged 143 — **2.81%, every one of them wrong** — while
  finding no genuinely garbled file at all. `# --- section ---` comments tripped
  it, so it flagged messie's own source, and flagged files were silently
  dropped from clustering. It handled a rare case with hand-tuned thresholds
  and had been validated on eight flavours of synthetic nonsense written in the
  same hour as the eight checks that caught them.
- **type soup** fired on more folders than any other signal and never once
  changed a verdict band. A signal that decides nothing is weight without a
  vote.

Real directories are now a permanent part of the test suite
(`tests/test_real_world.py`). They are large, free, and nobody arranged them to
suit messie. On 75 coherent package directories, **1.3% read as messy**, down
from 16.0% before those deletions and before `misfiled_neighbours` stopped
reporting packages for resembling their own subpackages.

## Limitations

- **Static embeddings are coarse.** They compare subject matter, not argument.
  Measured across the 35-subject example corpus, the default backend keeps 97%
  of single-subject folders together and 84% of unrelated pairs apart — the
  remaining 16% are adjacent subjects it files as one. Install
  `messie[model2vec]` or `messie[st]` for a stronger model if that matters to
  you; both fetch a model once, so they need the network that first time.
- **Photographs are taken on trust.** There is no vision model here. Images
  contribute their dimensions and their filenames, nothing more, so two camera
  rolls in one folder read as one thing — which is the intended answer.
- **Audio and video say nothing beyond their filenames.**
- **`overcrowded` fires on 13% of real package directories** and
  `unrelated_topics` on 8%. Those are libraries rather than personal folders,
  and the thresholds are deliberately not tuned to them, but the numbers are
  worth knowing.
- **Where the line falls is a judgement call.** Are tax returns and client
  invoices one subject or two? A semantic backend will usually say one. Tune
  with `--threshold` if your sense of it differs.
- **Scanned PDFs have no text to read.** There is no OCR.
- **messie is built for English.** Other Latin-script languages mostly work,
  but the default backend tends to group non-English documents by language
  rather than by subject, so verdicts on them are unreliable.

## Example datasets

`tests/corpus/` holds 35 subjects and 210 documents across three domains —
office paperwork, developer files and personal clutter — together with builders
that turn any of it into real files of thirty-odd types. `.docx`, `.pptx`,
`.xlsx`, `.odt`, `.epub`, `.pdf`, `.rtf`, `.ipynb` and the plain-text family
carry their text for real; photos, audio, video, installers, disk images,
archives, fonts and SQLite files get genuine headers and containers, because
messie never decodes those and generating a real JPEG would only test the
generator.

To see it work on something substantial:

```bash
python scripts/build_demo_tree.py /tmp/demo
messie /tmp/demo --all
```

That writes ~190 files across 29 extensions into folders ranging from genuinely
tidy to hopeless: a Downloads drawer of unrelated subjects and debris, loose
paperwork sitting beside the subfolder it belongs with, a wedding album, a music
library, a coherent code project, and a Desktop where every single file is about
something different. Everything is synthetic and deterministic for a given seed.

The builders are also what the tests are made of, so a folder that catches a
false positive can be turned into a regression test directly.

## Development

```bash
pip install -e '.[semantic,dev]'
pytest
ruff check src tests
```

`MESSIE_DEBUG=1` makes a signal that raises crash instead of being skipped.

The test suite builds real folders on disk and runs the whole pipeline against
every installed backend. As well as the signals themselves it checks that every
corpus subject is internally coherent — ground truth the other tests depend on —
that text survives a round trip through each readable format, that every file
type is recognised by kind, and that analysing a folder leaves every file in it
byte-for-byte untouched.

Most of the legibility tests guard against false positives rather than
detection, because that is where the risk lies: calling somebody's minified
JavaScript or Chinese-language report "gibberish" would be far worse than
missing a corrupt download.
