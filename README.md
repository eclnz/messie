# messie

**A repeatable way to measure how messy a folder is.**

Folders fill up slowly: a stray invoice in the thesis folder, three copies of
`report_final_v2.docx`, a download dump nobody has sorted in two years. It's
hard to see from the inside, and "this folder is a mess" is hard to act on or
enforce.

Messie reads the files in a folder, groups them by subject, and gives the
folder a score from 0 to 100 and a verdict, along with the reasons behind it:
unrelated topics mixed together, loose files that belong in a subfolder,
duplicates, version pileups, leftover temp files. It runs locally, never calls
external services or models, and never moves, renames, or deletes anything.

```text
$ messie ~/demo
88.7    chaotic 39      ./Downloads     unrelated_topics,time_strata,duplicates,debris,version_pileups
82      chaotic 8       ./Documents     misfiled_neighbours,unrelated_topics,time_strata
71.8    messy   18      ./Desktop       no_common_thread
```

## Why use it

- **It's deterministic.** The embedding model ships with the package and
  there's no sampling, so the same files give the same score every time. A
  score is something you can compare over time, set a threshold on, and argue
  about.
- **It works as a test.** The exit status says whether any folder crossed a
  threshold you pick, so messie can gate a CI pipeline the same way a linter
  does. A `docs/` tree or a shared data folder can have a tidiness check that
  fails the build when it drifts.
- **It explains itself.** Every verdict comes with the signals that caused it,
  and `--json` adds headlines, example files, and the groups it found, so you
  know what to fix rather than just that something is wrong.
- **It's safe to point anywhere.** It only reads, and nothing leaves your
  machine, so it's fine to run on personal folders, shared drives, or
  repositories with sensitive content.

Typical uses:

- Finding which folders in `~/Documents` or a shared drive need attention first.
- Keeping documentation, research, or dataset folders in a repository organised,
  enforced in CI.
- Tracking whether a cleanup actually worked, by comparing scores before and
  after.
- Feeding folder health into other tools through TSV or JSON output.

## Install

```bash
uv tool install git+https://github.com/eclnz/messie.git
```

Or, to work on it:

```bash
git clone https://github.com/eclnz/messie.git
cd messie
uv sync
uv tool install --editable .
uv tool update-shell
```

The [wordllama](https://pypi.org/project/wordllama/) model ships with the
package, so no download happens at run time. PDF text extraction is optional:
install with the `pdf` extra (or `all`) to enable it.

## Use

```bash
messie                        # current folder and its subfolders
messie ~/Documents            # a specific folder
messie ~/Drive --depth 5      # recurse further; default is 3
messie ~/Downloads --all      # analyse all folders, including those normally skipped
messie ~/Downloads --json     # JSON output
messie ~/Drive -v             # progress on stderr
messie -a --sa --color        # my favourite
messie -h                     # see the help page for more options
```

It accepts wildcards:

```bash
messie ~/Downloads/2026* -a --sa --color
```

Each matched path runs separately, so this is often slower than running on the
parent and filtering:

```bash
messie ~/Downloads -a --sa --color | grep 2026
```

### Reading the output

Plain output is one tab-separated line per folder, most messy first:

```text
SCORE   VERDICT   FILES   PATH   FINDINGS
```

Tidy and skipped folders are hidden by default; `--st` shows tidy folders,
`--ss` shows skipped ones, and `--sa` shows both. `-m/--min-verdict` sets the
quietest verdict that's printed (default `lived-in`).

Because the score comes first and paths are usable as arguments, the output
works with ordinary Unix tools:

```bash
messie ~ | head                     # the ten worst folders under your home directory
messie ~ | awk '$1 >= 75'           # only chaotic folders
messie ~ | cut -f4 | xargs -n1 ls   # list what's in each flagged folder
```

For detail, `--json` writes one document and `--jsonl` writes one object per
folder. Each finding has a code, a severity, a plain-language headline, and
example files:

```json
{
  "path": "/home/me/demo/Documents",
  "files": 8,
  "score": 82.0,
  "verdict": "chaotic",
  "clusters": 2,
  "findings": [
    {
      "code": "misfiled_neighbours",
      "severity": 1.0,
      "headline": "3 loose files read like the contents of a folder further down.",
      "detail": "3 of them resemble ./Taxes.",
      "examples": [
        "2023_tax_return_federal.pdf",
        "Self Assessment Tax Computation.docx",
        "tax_return_2022_amended.xlsx"
      ],
      "data": { "...": "..." }
    }
  ]
}
```

## Running in CI

Messie's exit status is what makes it usable as a test:

| Exit | Meaning |
|---|---|
| `0` | every judged folder is below the `--fail-over` verdict |
| `1` | at least one folder reached the `--fail-over` verdict |
| `2` | usage error, or a path couldn't be read |

`--fail-over` defaults to `messy`, so a plain `messie docs` fails when any
folder under `docs/` scores 50 or more. Raise it to `chaotic` to only fail on
serious mess, or lower it to `lived-in` to be strict. `-q` suppresses the
report when only the exit status matters.

A GitHub Actions step:

```yaml
- uses: astral-sh/setup-uv@v6
- run: uv tool install git+https://github.com/eclnz/messie.git
- name: Check the docs folder is tidy
  run: messie docs --fail-over messy
```

When it fails, the log shows which folders crossed the line and why. For a
report you can keep or post elsewhere, write JSON and upload it as an artifact:

```yaml
- run: messie docs --json > messie-report.json
```

Because results are deterministic, a failure means the folder's contents
changed, not that the run was unlucky.

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
are too small to judge unless you pass `--all`.

## Notes

Messie reads plain text, common office formats, HTML, CSV, source code, and
subtitles directly. PDF support is optional. For files without readable text,
it uses filenames, file kinds, and limited metadata. It does not use OCR or
image recognition.

Embeddings compare broad subject matter rather than detailed argument. The
default model is strongest on English; use `--threshold` to tune clustering for
your folders.

Common build and tooling folders (`.git`, `node_modules`, `.venv`, `dist`,
and so on) are skipped, as are hidden files unless you pass `--hidden`.

## Example data

`tests/corpus/` contains synthetic documents and builders for test folders.
Build a demonstration tree and run messie on it:

```text
$ uv run python scripts/build_demo_tree.py /tmp/messie-demo
$ cd /tmp/messie-demo

$ messie
88.7    chaotic 39      ./Downloads     unrelated_topics,time_strata,duplicates,debris,version_pileups
82      chaotic 8       ./Documents     misfiled_neighbours,unrelated_topics,time_strata
71.8    messy   18      ./Desktop       no_common_thread

$ messie --sa            # include tidy and skipped folders
88.7    chaotic 39      ./Downloads     unrelated_topics,time_strata,duplicates,debris,version_pileups
82      chaotic 8       ./Documents     misfiled_neighbours,unrelated_topics,time_strata
71.8    messy   18      ./Desktop       no_common_thread
-       skipped 0       .               too_few_files
-       skipped 0       ./Archive       too_few_files
0       tidy    60      ./Archive/Scans -
0       tidy    6       ./Documents/Taxes       -
-       skipped 0       ./Music         too_few_files
0       tidy    16      ./Music/Albums  -
-       skipped 0       ./Pictures      too_few_files
0       tidy    24      ./Pictures/Wedding      -
-       skipped 0       ./Projects      too_few_files
0       tidy    8       ./Projects/ledger-api   -
-       skipped 0       ./Work          too_few_files
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
