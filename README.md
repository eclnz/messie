# messie

Messie finds folders whose files cover unrelated subjects. It reads the files,
groups them by subject, and reports where a folder looks mixed, with examples.
Analysis runs locally and never changes files.

```text
$ messie ~/Downloads

~/Downloads                                    CHAOTIC  89.7/100   30 files · wordllama
  4 unrelated things are living in this folder.
      · agreement · lease · meeting    6 files  2026   lease agreement.txt +5
      · invoice · billed · hours       4 files  2026   invoice_1040.docx +3
  6 files here are copies of something else here.
  4 files here are debris.
```

## Install

```bash
pip install messie
pip install 'messie[pdf]'     # PDF text extraction
pip install 'messie[photos]'  # image metadata, when available
```

The [wordllama](https://pypi.org/project/wordllama/) model ships with the
package.

## Use

```bash
messie                        # current folder and its subfolders
messie ~/Documents            # a specific folder
messie ~/Drive --depth 5      # recurse further; default is 3
messie ~/Downloads --all      # include tidy folders
messie ~/Downloads --json     # JSON output
messie ~/Drive -v             # progress on stderr
messie ~/Pictures -c          # include crowding observations
```

The command exits with 1 when a folder reaches `--fail-over` (default:
`messy`), so it can be used in scheduled checks:

```bash
messie ~/Downloads --fail-over chaotic || notify-send 'Downloads needs sorting'
```

## What it looks for

| Signal | Meaning |
|---|---|
| unrelated topics | distinct subjects sharing a folder |
| nothing in common | no subject connects the files |
| strays | files that do not fit a meaningful group |
| misfiled neighbours | loose files resembling a subfolder's contents |
| overcrowded | many loose files; opt in with `-c` |
| debris | temporary, empty, or never-named files |
| version pileups | multiple revisions of one file |
| duplicates | identical bytes or duplicate text |
| time strata | unrelated material accumulated in separate periods |

Signals combine into a score: **tidy** (0–24), **lived-in** (25–49),
**messy** (50–74), or **chaotic** (75–100). Folders with fewer than six files
are too small to judge.

## Notes

Messie reads plain text, common office formats, HTML, CSV, source code, and
subtitles directly. PDF support is optional. For files without readable text,
it uses filenames, file kinds, and limited metadata. It does not use OCR or
image recognition.

Embeddings compare broad subject matter rather than detailed argument. The
default model is strongest on English; use `--threshold` to tune clustering for
your folders.

## Example data

`tests/corpus/` contains synthetic documents and builders for test folders.
Build a demonstration tree with:

```bash
uv run python scripts/build_demo_tree.py /tmp/messie-demo
uv run messie /tmp/messie-demo --all
```

## Development

```bash
uv sync --all-groups --extra dev --extra all
uv run pytest
uv run pyright
uv run ruff check src tests
```

`-v` writes progress to stderr, so JSON stays safe to pipe. Set
`MESSIE_DEBUG=1` to let signal errors raise during development.
