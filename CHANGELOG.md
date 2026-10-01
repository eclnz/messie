# Changelog

## 0.2.0 — potentially breaking

### Compatibility changes

- `--json` now always returns an object with a `roots` array. Each root has its
  own `root` path and `folders` array. JSON consumers written for the previous
  shape need updating.
- Standard-input paths now require an explicit `-` operand. `-z` replaces `-0`
  for NUL-delimited input.
- `--depth` limits which folders are judged and reported. Deeper folders are
  still read as evidence, and the default depth is now unlimited rather than 3.
- Reported paths are formatted consistently across text, JSON, and JSON Lines;
  scripts comparing path strings may need updating.

### Additions

- `-f` / `--folder` checks whether a folder's contents are out of place in its
  local surroundings. This remains opt in.
- `--show tidy,skipped` and `--show all` control which folder rows are printed.
  The older `--st`, `--ss`, and `--sa` flags remain accepted but are hidden from
  help.
- `ignore.messie` excludes explicitly named files or folders from analysis.
  Rules can be placed in nested folders and inherited by their descendants.
