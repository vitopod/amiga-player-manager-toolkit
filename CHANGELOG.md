# Changelog

All notable changes to PMSaveDiskToolkit are recorded here.
The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and the project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [2.2.2] — 2026-04-17

### Added
- **Help → Check for Updates…** — on-demand check against the GitHub
  Releases API. Compares the latest `tag_name` to the running version and
  either confirms you're up to date or offers to open the release page in
  your browser. Uses `urllib.request` only (zero new dependencies) with a
  5-second timeout; does nothing automatically on launch.

## [2.2.1] — 2026-04-17

### Fixed
- **Season & career fields were misaligned by one byte.** Everything from
  offset `0x1B` onwards in the 42-byte player record was read one byte too
  early, so (for example) *Matches Last Year* surfaced as *Div1 Years*,
  *Contract Years* surfaced as an unidentified "last_byte", and every
  other season/career stat was off by one slot. Verified against an
  in-game career screen (Galassi, HURGADA: matches_last=5, div3=4, div4=1,
  contract=3 all now match). The real layout is: reserved2 at `0x1B`
  (zero for 1033/1035 real players), season stats at `0x1C..0x23`, career
  years div1..4 + international at `0x24..0x28`, and `contract_years`
  (1..5) at `0x29`.
- **Aggression displayed the raw on-disk byte instead of the in-game
  value.** The stat is stored *inverted* — raw disk byte = 200 − displayed.
  A "calm" player (in-game aggression 28) was showing as 172 throughout
  the GUI, CLI, Compare Players, Line-up Coach card-risk heuristic, and
  CSV/JSON exports. `parse_player` / `serialize_player` now invert, so
  `PlayerRecord.aggression` holds the in-game value; round-trip
  serialization remains byte-identical.
- Applies equally to Italian and English/BETA save disks — both builds
  share the same 42-byte record format.

### Changed
- `PlayerRecord.last_byte` is gone; its byte (`0x29`) is now
  `contract_years`. `PlayerRecord.reserved2` (new) holds `0x1B`.
- CSV/JSON exports gain a `reserved2` column and drop `last_byte`; all
  season/career columns now carry correct values.

### Tests
- Round-trip (`test_roundtrip_all_players`, `test_roundtrip_full_adf`)
  still passes — byte-identical across parse → serialize.
- Renamed `test_last_byte_in_expected_range` → `test_contract_years_in_expected_range`.
- Added `test_reserved2_mostly_zero` documenting the 0x1B invariant.

### Known remaining mystery
- `injuries_last_year` (byte `0x1D`) for Galassi is `9` on disk but the
  game displays `3`. Possibly a weeks-vs-events or scaling difference on
  that single byte; unrelated to the alignment bug and worth a separate
  investigation.

## [2.1.2] — 2026-04-17

### Fixed
- **Wrong team rosters on saves after standings reshuffle.** From pm2.sav
  onward the team ordering inside each save slot shifts as teams move in
  the league standings, but the toolkit was resolving team names through
  `PM1.nam` — a static snapshot of the *initial* standings. This made
  players in later saves (e.g. pm6.sav, pm7.sav) display under the wrong
  team label and caused the entire roster for teams like HURGADA to look
  nothing like the in-game squad. `SaveSlot` now reads team names
  directly from each `.sav`'s 44 × 100-byte team records (NUL-terminated
  ASCII at sub-offset 68, same layout `start.dat` uses), matching the
  1-based `team_index` → record[N−1] mapping the game engine uses. Slot
  0 (the user's own team) still falls back to `PM1.nam[0]` when present.
- Documented that `player.team_index` is **1-based** against the save's
  team records (team_index=0 = user's own team, team_index=N → record N−1).

### Changed
- `SaveSlot.apply_team_name_fallback` is now a no-op whenever the save's
  own records populated that slot — which is the common case for both
  Italian and English save disks.

### Tests
- New regression tests: HURGADA moves between saves as standings shift;
  slot 0 falls back to `PM1.nam[0]` on Italian saves and to the
  placeholder on English saves without `PM1.nam`.

## [2.1.1] — 2026-04-17

### Added
- **Team-name fallback for English / BETA save disks.** English save
  disks don't ship `PM1.nam`, so team names previously showed as
  `"Team 0".."Team 43"` placeholders. When a game disk is loaded the
  toolkit now extracts real team names from `start.dat` on the game
  disk (44 × 100-byte team records; NUL-terminated name at sub-offset
  0x3C) and fills them in everywhere — roster, Squad Analyst, Best XI,
  Career Tracker, CSV/JSON export, Line-up Coach. Italian saves are
  unaffected: `PM1.nam` still wins.
- `GameDisk.team_names` (list of 44 strings, empty for unused slots) and
  `GameDisk.team_names_available` on any PM custom-file-table game disk
  where `start.dat` parses cleanly.
- `SaveSlot.apply_team_name_fallback(team_names)` — no-op when the save
  already had real names; returns `True` if anything changed.
- `SaveSlot.team_names_from_save` flag indicating whether names came
  from `PM1.nam` (True) or the placeholder path (False).
- Tests: 5 new (English start.dat extraction, malformed-disk fallback,
  save-slot fallback applied + no-op when PM1.nam present).

### Changed
- CLI `_load_game_disk` now takes an optional `slot` argument and
  applies the team-name fallback automatically when it runs. The GUI
  applies it in both directions (save-then-game or game-then-save).

## [2.1.0] — 2026-04-17

### Added
- **English game disk support (BETA).** The game-disk loader now accepts
  English (Anco 1990) disks in addition to the Italian build. 183 English
  surnames are extracted by anchor-scan on `Adams\0Adcock\0Addison\0
  Aldridge\0Alexander\0` out of a PM-custom-file-table disk; the Italian
  initials charsets (ADJR / CEGMS / BFHILNTW / O) are reused. Surnames
  and initials verified against a real in-game roster screen on
  2026-04-17. BETA because the full seed → displayed-name mapping is not
  yet locked against a known seed; individual resolutions could in
  principle drift.
- `GameDisk.build`, `GameDisk.names_available`, `GameDisk.is_beta`
  exposed so callers can adapt their UI. GUI shows an amber BETA pill
  and a one-time warning dialog for BETA builds; CLI prints a stderr
  `Note:` on BETA loads.
- The loader is deliberately lenient: any disk that looks PM-shaped is
  accepted. Unknown builds load with `surnames=[]` so save editing still
  works; names stay blank rather than erroring.
- Tests: 8 new tests in `TestEnglishGameDiskBeta`
  (`tests/test_names.py`), gated on `PM_EN_GAME_ADF`.

## [2.0.0] — 2026-04-16

### Added
- **Line-up Coach (BETA)** — Tools → Line-up Coach (BETA)… (accelerator
  Cmd/Ctrl+L). Suggests a starting XI for a team or the whole championship.
  Scores every (player, role) pair over a 12-role taxonomy (GK / CB·FB·SW
  / DM·CM·AM·WM / POA·TGT·WNG·DLF), assembles the best XI via global-greedy
  assignment, and ranks the three supported formations (4-4-2 / 4-3-3 /
  3-5-2) by a composite of skill, role fit, morale, fatigue, card-risk and
  form. Also flags players whose best-fit role lies **outside** their
  nominal position — useful for squad rotation experiments.
  BETA: scoring is a modern football-management heuristic, **not** a
  reconstruction of PM's match-engine weights. Treat output as "suggested,"
  not "optimal."
- **CLI** `suggest-xi` — same engine on the command line. Ranks formations,
  prints the recommended XI with role tags and fit percentages, and lists
  reassignment suggestions with a configurable gap threshold. `--team`,
  `--formation`, `--allow-cross-position`, `--include-injured`, `--weights
  KEY=VAL…`, `--reassign-threshold`, `--reassign-limit`.
- **`pm_core.lineup`** — pure library module (zero external deps). Exposes
  `ROLES`, `FORMATION_ROLES`, `role_fit`, `best_role`, `assemble_xi`,
  `score_xi`, `suggest_reassignments`, `rank_formations`, plus the
  composite-weight defaults and result dataclasses. 33 unit tests pin
  down the role maths, taxonomy consistency (FORMATION_ROLES must match
  `pm_core.save.FORMATIONS` at the position-count level), XI-assembly
  invariants, and reassignment flagging.

## [1.1.0] — 2026-04-16

### Added
- **Byte Workbench** — Tools → Byte Workbench… (accelerator Cmd/Ctrl+B). A
  reverse-engineering UI for the 42-byte player record with three tabs:
  - **Raw View** — hex / decimal / binary dump of the selected player, each
    byte annotated with the field it belongs to and any known invariants.
  - **Histogram** — value distribution at any offset, optionally masked to
    a single bit. Preset filters (real / free agents / transfer-listed /
    by position / young / veteran / contracted) narrow the input set.
  - **Diff** — picks two player sets by preset filter and ranks the bits
    whose probability of being set differs most between them. Reproduces
    the manual process that originally cracked `mystery3 bit 0x80`, now as
    a push-button tool for cracking the remaining unknowns (`mystery3`
    lower 7 bits, `last_byte` skew).
- **CLI** `byte-stats` — histogram a byte/bit across a preset set, e.g.
  `byte-stats … --offset 0x1A --mask 0x80 --filter real`.
- **CLI** `byte-diff` — rank the top-N discriminative bits between two
  preset sets, e.g. `byte-diff … --set-a transfer-listed --set-b not-transfer-listed`.
- **`pm_core.workbench`** — pure analysis module: `byte_histogram`,
  `bit_probability`, `diff_sets`, `query`. Operates on iterables of
  `PlayerRecord`; no `SaveSlot` dependency. 26 unit tests.
- **`pm_core.player.FIELD_LAYOUT`** and **`field_at_offset(offset)`** — the
  single source of truth mapping each of the 42 bytes to its field, size,
  and note. Used by the workbench UI and CLI to label every offset.

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
