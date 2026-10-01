# messie

A linter for folder structure. Fails your CI when a folder turns into a mess.

messie reads the files, groups them by subject, and scores each folder 0–100 for mixed topics, misfiled files, duplicates, and debris. Scores are deterministic, so a failure means the files changed, not that the run was unlucky. Local only, read only.

```yaml
- uses: actions/checkout@v5
- uses: astral-sh/setup-uv@v6
- run: uvx --from git+https://github.com/eclnz/messie.git messie docs --fail-over messy
```

Or run it locally to find the worst folders:

```text
$ messie ~/demo
88.7    chaotic 39      ./Downloads     unrelated_topics,time_strata,duplicates,debris,version_pileups
82      chaotic 8       ./Documents     misfiled_neighbours,unrelated_topics,time_strata
71.8    messy   18      ./Desktop       no_common_thread
```

## Install

```bash
uv tool install git+https://github.com/eclnz/messie.git
```

The embedding model ([wordllama](https://pypi.org/project/wordllama/)) ships with the package. PDF text needs the `pdf` extra.

## Use

```bash
messie                        # current folder and its descendants
messie ~/Drive --depth 5      # report 5 levels; read deeper folders as evidence
messie ~/Downloads --all      # also judge folders with < 6 files
messie ~/Downloads --sa       # include tidy and skipped folders
messie ~/Downloads --json     # or --jsonl
messie ~/Drive --folder       # find folders unusual for their surroundings
messie ~/Drive -v             # progress on stderr
messie ~/Downloads/2026*      # globs; each match runs separately
```

Output is TSV, worst first: `SCORE VERDICT FILES PATH FINDINGS`.

```bash
messie ~ | head
messie ~ | awk '$1 >= 75'
messie ~ | cut -f4 | xargs -n1 ls
```

`--json` adds a headline, examples, and data per finding:

```json
{
  "code": "misfiled_neighbours",
  "severity": 1.0,
  "headline": "3 loose files read like the contents of a folder further down.",
  "detail": "3 of them resemble ./Taxes.",
  "examples": ["2023_tax_return_federal.pdf", "tax_return_2022_amended.xlsx"]
}
```

## CI

| Exit | |
|---|---|
| 0 | all folders below `--fail-over` |
| 1 | a folder reached `--fail-over` (default `messy`) |
| 2 | usage or read error |

```yaml
- uses: actions/checkout@v5
- uses: astral-sh/setup-uv@v6
- run: uvx --from git+https://github.com/eclnz/messie.git messie docs --fail-over messy
```

## Scoring

| Signal | Meaning |
|---|---|
| unrelated_topics | distinct subjects sharing a folder |
| no_common_thread | no subject connects the files |
| strays | files that fit no meaningful group |
| misfiled_neighbours | loose files resembling a subfolder's contents |
| folder_placement | a subtree that looks out of place locally (opt in with `-f`) |
| overcrowded | many loose files (opt in with `-c`) |
| debris | temporary, empty, or unnamed files |
| version_pileups | multiple revisions of one file |
| duplicates | identical bytes or text |
| time_strata | unrelated material from separate periods |

tidy 0–24, lived-in 25–49, messy 50–74, chaotic 75–100. Folders with fewer than six files are skipped unless `--all`.

With `--folder`, a folder with few direct files can still get a placement finding
when its subtree has enough readable files. Messie compares it with its local
surroundings, allowing for variety among sibling folders. A related folder
elsewhere may explain the finding; it is not a proposed destination. The checks
use contents and names without rules for particular folder layouts.

Reads text, office formats, HTML, CSV, source, and subtitles; PDF optional. Other files are judged by name, kind, and metadata. No OCR. Embeddings are strongest on English; tune with `--threshold`. Hidden files and `.git`, `node_modules`, `.venv`, `dist`, etc. are skipped.

`tests/corpus/` includes placement ground truth with local outliers, parallel
branches, and decoys with partly matching contents or shared names.

## Development

```bash
uv sync --all-groups --extra dev --extra all
uv run pytest
uv run pyright
uv run ruff check src tests
uv run python scripts/build_demo_tree.py /tmp/messie-demo   # sample tree
```

`MESSIE_DEBUG=1` makes signal errors raise.
