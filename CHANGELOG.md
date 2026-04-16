# Changelog

All notable changes to PMSaveDiskTool v2 are recorded here.
The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and the project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.0.0] — 2026-04-16

### Added
- **Reorganised menu bar** — File / Edit / View / Tools / Help with
  proper accelerators. File: Open Save Disk…, Open Game Disk…, Open
  Recent ▸, Save, Save As…, Export Players…, Quit. Edit: Apply
  Changes, Revert Player, Find Player…. View: All Players, Free
  Agents, Young Talents, Top Scorers, Squad Analyst, Best XI ▸. Tools:
  Career Tracker…. All actions are keyboard-reachable on macOS (Cmd)
  and Windows/Linux (Ctrl).
- **macOS native menu conventions** — About appears in the apple menu,
  Cmd+Q routes through the same dirty-state guard as WM_DELETE_WINDOW.
- **Detail panel refactored into tabs** — Core · Skills · Status ·
  Season · Career, with an always-visible identity header (Player #,
  Name, Seed) above and a sticky footer below (Apply Changes / Revert).
  No more long scrolling form; Apply is always in view.
- **Dirty-state tracking** — window title shows the open file name,
  with a "•" marker while unsaved edits are pending. Quitting,
  closing the window, or opening a different ADF prompts to save.
- **File → Open Recent** — last five save disks, persisted to
  `~/.pmsavedisktool/recent.json`.
- **Polished About dialog** — versioned header, attribution, clickable
  GitHub and MIT License links.
- **Status bar split** — left: transient status messages; right:
  persistent game-disk indicator.
- Search-entry focus via Ctrl/Cmd+F; Esc clears the filter when the
  filter entry has focus, otherwise reverts the current player.

### Changed
- **Toolbar slimmed** — Open / Load Game / Save Changes buttons
  removed (all in File menu with accelerators). Team dropdown
  relabeled **View** since it holds both teams and analytical views.
- **Renamed labels** — "Open Game ADF (for names)" →
  "Open Game Disk"; "Save ADF" → "Save"; "Save ADF As…" → "Save As…".

## [0.99] — 2026-04-16

### Added
- **Squad Analyst in the GUI** — "— Squad Analyst (all teams)" entry in the
  team dropdown, reusing the tree with repurposed column headings (Team, Age,
  Size, GK·DEF·MID·FWD, AvgSkill, Mkt). Squad rows are non-selectable for
  editing.
- **Per-team Squad Summary label** above the roster whenever a specific team
  is selected — `"17 players · avg 25.2y · skill 1238 · 2 on market"` — so
  the roster view and the composition snapshot coexist.
- **Career Tracker window** under a new Tools menu — diff any two save slots
  on the current ADF or bring in a second ADF via "Load side-B ADF". Output
  columns mirror the CLI (id, name, age A/B, skill A/B, Δ, team A/B), with a
  "Team changes only" filter.
- **File → Export Players...** — export the current view (all / free agents /
  team) as CSV or JSON from the GUI. Uses the same schema as the CLI
  `export-players` subcommand via the new `pm_core.save.player_to_row` helper.
- **Live player filter** Entry above the tree (filter by id/name/team/position).
- CLI smoke tests for `squad-analyst` and `career-tracker`
  (`tests/test_cli.py`, now 19 tests).
- Unit tests for `SaveSlot.squad_summary`, `SaveSlot.all_squad_summaries`,
  and `SaveSlot.diff_players` (`tests/test_read_save.py::TestSquadSummary`,
  `TestDiffPlayers`).
- `MANUAL.md` sections for `squad-analyst`, `career-tracker`,
  `export-players`, GUI Squad Analyst / filter / Tools menu / Export,
  automatic `.bak` on first write, the `--version` flag, and `python -m`
  entry points.

### Changed
- `pm_core.save.player_to_row` is the single source of truth for the export
  row shape; `pm_cli` and the GUI both call it. (Previously duplicated as a
  private helper in `pm_cli`.)

### Fixed
- 0.98 shipped the Squad Analyst CLI but neither a GUI entry nor updated
  READMEs listing the feature. 0.99 closes that gap and adds Career Tracker
  and Export parity between CLI and GUI.

## [0.98] — 2026-04-16

### Added
- `export-players` CLI subcommand — dump the player database as CSV or JSON,
  with optional team/free-agent filters and game-ADF name resolution.
- `squad-analyst` CLI subcommand — per-team composition breakdown
  (size, counts by position, average age and skill, youngest/oldest/best,
  players on the market). `--team N` drills into a single team.
- `career-tracker` CLI subcommand — diff two save slots (same ADF or
  different ADFs) to surface skill/age/team changes per player.
  `--sort {skill,id,changes}`, `--limit N`, `--team-changes-only` for
  zeroing in on the interesting records.
- `best-xi --market-only` — consistent with `young-talents` and `highlights`.
- `python -m PMSaveDiskTool_v2.pm_cli` and `python -m pm_core` entry points.
- Automatic `.bak` creation on first write. The CLI `edit-player` and the
  GUI "Save Changes" action both create a sibling `<file>.adf.bak` the
  first time they write to a loaded ADF; subsequent writes leave the
  original backup untouched so the first-known-good state is recoverable.
- Live player filter box in the GUI — narrow the list by id, name,
  team, or position as you type.
- GitHub Actions CI running the ADF-independent tests on Python 3.10,
  3.11, and 3.12 across Linux, macOS, and Windows.
- `tests/test_unit.py` (18 tests), `tests/test_names.py` (15 tests,
  4 require a game ADF), `tests/test_cli.py` (14 subprocess smoke
  tests), and a new `TestUnknownFieldObservations` in
  `tests/test_read_save.py` that locks in the observed invariants for
  `reserved`, `mystery3`, and `last_byte`. Total test count: 79.

### Changed
- `PlayerRecord.reserved`, `PlayerRecord.mystery3`, and
  `PlayerRecord.last_byte` are now documented with empirical findings
  from Save1_PM (1031 real players): `reserved` is always 0;
  `mystery3` bit 5 is never set; `last_byte` is always in 1..5.
  The bit-level analysis of `mystery3` (value 19 → free agents, value
  18 → veterans) and the skill/age skew of `last_byte` are recorded
  inline for future reverse engineering.
- Documented Python 3.10 as the minimum supported version (the codebase
  already used PEP 604 `X | None` annotations and PEP 585 generics).

## [0.97] — 2026-04-16

### Added
- **Top 11 of the Championship** — pick the best starting XI in a chosen
  formation (4-4-2, 4-3-3, 3-5-2). CLI subcommand `best-xi`; GUI team
  dropdown entries "— Top 11 (4-4-2)", "— Top 11 (4-3-3)", "— Young XI
  (≤21)", "— Free-Agent XI". Supports an optional per-team cap (free
  agents exempt) and filters (young, veteran, free-agent, market).
- `is_transfer_listed` player property (mystery3 bit 0x80) — identified
  empirically by byte-diffing records of players known to be on the
  in-game LISTA TRASFERIMENTI. 255 matches DB-wide with a realistic
  position/division/age distribution.
- `--version` flag on the CLI.
- Version string in the GUI window title.

### Changed
- `PlayerRecord.is_market_available` is now `is_free_agent or
  is_transfer_listed` (union of free agency and the transfer-list flag).
  Previously used a `transfer_weeks > 0` heuristic that produced false
  positives (e.g. A. Attrice was starred without being on LISTA
  TRASFERIMENTI in-game).
- Renamed `transfer_weeks` → `weeks_since_transfer`. The field is a
  post-transfer cooldown counter, not a "listed for sale" flag.

### Fixed
- "Young Talents" and "Championship Highlights" no longer include garbage
  sentinel records from the tail of the player database.

## [Pre-0.97]

- Ground-up cross-platform rewrite of
  [PMSaveDiskTool v1.2](http://www.ultimatebinary.com) by UltimateBinary
  for Mac, Linux, and Windows.
- ADF save-disk reader/writer with byte-for-byte round trip compatibility.
- tkinter GUI and argparse CLI.
- Player name generation from the 4-byte RNG seed, using surnames
  decompressed from the DEFAJAM-packed game executable.
- Young Talents view (≤21 by skill) and Championship Highlights
  (top scorers per division).
