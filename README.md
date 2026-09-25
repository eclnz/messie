# messie

Messie finds folders whose files cover unrelated subjects. It reads the files, groups them by subject, and reports where a folder looks mixed, with examples. Analysis runs locally and doesn't call external modes, and it never changes files.

```text
$ messie ~/Downloads

88.7    chaotic 39      /messie-demo/Downloads   unrelated_topics,time_strata,duplicates,debris,version_pileups
82      chaotic 8       /messie-demo/Documents   misfiled_neighbours,unrelated_topics,time_strata
71.8    messy   18      /messie-demo/Desktop     no_common_thread
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
messie ~/Downloads --all      # analyse all folders, including those normally skipped
messie ~/Downloads --json     # JSON output
messie ~/Drive -v             # progress on stderr
messie -a --sa --color        # my favorite
messie -h                     # see the help page for more args
```

It accepts wildcards, so the following is acceptable:
```bash
messie ~/Downloads/2026* -a --sa --color # note it runs for each path seperately so it is often slower than running for an entire parent.
messie ~/Downloads -a --sa --color | grep 2026 # the same could be achieved with
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
> uv run python scripts/build_demo_tree.py /tmp/messie-demo

> uv run messie /tmp/messie-demo
88.7    chaotic 39      ../../../../private/tmp/messie-demo/Downloads   unrelated_topics,time_strata,duplicates,debris,version_pileups
82      chaotic 8       ../../../../private/tmp/messie-demo/Documents   misfiled_neighbours,unrelated_topics,time_strata
71.8    messy   18      ../../../../private/tmp/messie-demo/Desktop     no_common_thread

# Comprehensive version showing it did indeed check all folders
> uv run messie /tmp/messie-demo --ss --sa
88.7    chaotic 39      ./Downloads     unrelated_topics,time_strata,duplicates,debris,version_pileups
82      chaotic 8       ./Documents     misfiled_neighbours,unrelated_topics,time_strata
71.8    messy   18      ./Desktop       no_common_thread
-       skipped 0       .       too_few_files
-       skipped 0       ./Archive       too_few_files
0       tidy    60      ./Archive/Scans -
0       tidy    6       ./Documents/Taxes       -
-       skipped 0       ./Music too_few_files
0       tidy    16      ./Music/Albums  -
-       skipped 0       ./Pictures      too_few_files
0       tidy    24      ./Pictures/Wedding      -
-       skipped 0       ./Projects      too_few_files
0       tidy    8       ./Projects/ledger-api   -
-       skipped 0       ./Work  too_few_files
0       tidy    9       ./Work/Invoices -
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
