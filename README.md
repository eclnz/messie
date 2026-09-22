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
pip install 'messie[semantic]'     # recommended
```

The `semantic` extra pulls in [wordllama](https://pypi.org/project/wordllama/),
whose model weights ship inside its wheel. Nothing is downloaded at analysis
time, or ever — `pip install` is the whole story, and messie works on a machine
that has never been online.

Plain `pip install messie` also works and falls back to lexical matching (see
*Backends*). `pip install 'messie[pdf]'` adds PDF text extraction.

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
| **strays** | files that match nothing else present |
| **misfiled neighbours** | loose files that read like the contents of a subfolder sitting right there |
| **type soup** | many different *sorts* of file evenly mixed — part photo album, part installer cache |
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
| `wordllama` | good | **none — weights are in the wheel** | `pip install 'messie[semantic]'` |
| `model2vec` | better | once, from Hugging Face | `pip install 'messie[model2vec]'` |
| `sentence` | best, slowest | once, from Hugging Face | `pip install 'messie[st]'` |
| `lexical` | limited | none | always available |

Pick one explicitly with `--backend`. Naming a backend that isn't installed is
an error rather than a silent downgrade: a verdict should never quietly come
from a weaker model than the one you asked for.

Thresholds are expressed as fractions of each backend's own similarity scale, so
the same settings behave sensibly across all of them.

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

## Limitations

- **The lexical backend matches words, not meanings.** It will separate subjects
  that use different vocabulary, but it cannot tell that "payment due" and
  "invoice" are the same topic. That is what the semantic backends are for.
- **Images, audio and video are judged by name and kind only.** There is no
  vision model here; a folder of photos is taken on trust.
- **Where the line falls is a judgement call.** Are tax returns and client
  invoices one subject or two? A semantic backend will usually say one. Tune
  with `--threshold` if your sense of it differs.
- **Scanned PDFs have no text to read.** There is no OCR.

## Development

```bash
pip install -e '.[semantic,dev]'
pytest
ruff check src tests
```

`MESSIE_DEBUG=1` makes a signal that raises crash instead of being skipped.

The test suite builds real folders on disk — including genuine `.docx` archives
— and runs the whole pipeline against every installed backend. It also asserts
that analysing a folder leaves every file in it byte-for-byte untouched.
