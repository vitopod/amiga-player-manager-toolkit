# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Commands

All commands are run from the repo root.

```bash
# Run full test suite
python3 -m pytest PMSaveDiskTool_v2/tests/ -v

# Run a single test class or test
python3 -m pytest PMSaveDiskTool_v2/tests/test_read_save.py::TestSaveSlot -v
python3 -m pytest PMSaveDiskTool_v2/tests/test_read_save.py::TestSaveSlot::test_player_0 -v

# Launch the GUI
python3 PMSaveDiskTool_v2/pm_gui.py

# CLI examples
python3 PMSaveDiskTool_v2/pm_cli.py list-saves PMSaveDiskTool_v1.2/Save1_PM.adf
python3 PMSaveDiskTool_v2/pm_cli.py young-talents PMSaveDiskTool_v1.2/Save1_PM.adf --save pm1.sav
python3 PMSaveDiskTool_v2/pm_cli.py highlights PMSaveDiskTool_v1.2/Save1_PM.adf --save pm1.sav
python3 PMSaveDiskTool_v2/pm_cli.py best-xi PMSaveDiskTool_v1.2/Save1_PM.adf --save pm1.sav --formation 4-3-3
python3 PMSaveDiskTool_v2/pm_cli.py squad-analyst PMSaveDiskTool_v1.2/Save1_PM.adf --save pm1.sav
python3 PMSaveDiskTool_v2/pm_cli.py career-tracker PMSaveDiskTool_v1.2/Save1_PM.adf --save-a pm1.sav --save-b pm2.sav

# Module entry points also work
python3 -m PMSaveDiskTool_v2.pm_cli --version

# Byte Workbench (reverse-engineering) CLI
python3 PMSaveDiskTool_v2/pm_cli.py byte-stats PMSaveDiskTool_v1.2/Save1_PM.adf --save pm1.sav --offset 0x1A --mask 0x80 --filter real
python3 PMSaveDiskTool_v2/pm_cli.py byte-diff  PMSaveDiskTool_v1.2/Save1_PM.adf --save pm1.sav --set-a transfer-listed --set-b not-transfer-listed

# Line-up Coach (BETA) — whole championship or a specific team
python3 PMSaveDiskTool_v2/pm_cli.py suggest-xi PMSaveDiskTool_v1.2/Save1_PM.adf --save pm1.sav
python3 PMSaveDiskTool_v2/pm_cli.py suggest-xi PMSaveDiskTool_v1.2/Save1_PM.adf --save pm1.sav --team 0 --include-injured --formation 4-3-3
```

The test ADF is at `PMSaveDiskTool_v1.2/Save1_PM.adf` (gitignored personal file). Tests skip automatically if it is absent.

## Architecture

All code lives under `PMSaveDiskTool_v2/`.

### Data flow

```
ADF file on disk
  └── ADF (adf.py)              raw bytearray, file table parser, read_at/write_at
        └── SaveSlot (save.py)  loads team names (PM1.nam) + player DB
              └── PlayerRecord  (player.py) — one 42-byte record per player
                    └── GameDisk (names.py) — optional; decompresses game executable
                                              to resolve RNG seeds → player names
```

### Key concepts

**Save disk layout** — the save disk uses a *custom* file table (not AmigaDOS). File table is at block 2 (0x400), 16-byte entries: 12-byte name + 2-byte offset (×32 multiplier) + 2-byte size. `ADF` parses this.

**Player database** — each `.sav` file (4408 bytes = 44 teams × 100 bytes) is immediately followed in the ADF image by the player database: 2-byte BE header + 1536 × 42-byte records. `SaveSlot._db_offset = entry.byte_offset + entry.size`.

**42-byte player record** — fully documented in `player.py`. Key fields: bytes 0–3 RNG seed, byte 4 age, byte 5 position (1=GK 2=DEF 3=MID 4=FWD), byte 7 team_index (0xFF = free agent), bytes 10–19 ten skills. **team_index is 1-based relative to the save slot's team records**: team_index=0 means the user's own team (whose label lives in `PM1.nam[0]`), while team_index=N (1..43) points at the (N−1)-th 100-byte team record inside the `.sav`. The record order reshuffles each season as teams move in league standings, so resolving names requires reading each save's own records — not `PM1.nam`, which only reflects the initial standings.

**Real player filter** — `SaveSlot._is_real_player()` guards analytical views (Young Talents, Championship Highlights, Best XI) against garbage sentinel records near the end of the DB. Criteria: `position in (1,2,3,4)` and `team_index <= 43 or team_index == 0xFF`.

**Best XI** — `SaveSlot.best_xi(formation, filter_fn=, max_per_team=)` selects the top XI of the championship. `FORMATIONS` dict maps formation strings (`"4-4-2"`, `"4-3-3"`, `"3-5-2"`) to `{position: slot_count}`. Returns players ordered GK → DEF → MID → FWD, sorted by `total_skill` within each position, picked greedily while respecting `max_per_team` (free agents 0xFF are exempt from the cap). The CLI `best-xi` subcommand and GUI entries (`— Top 11 (4-4-2)`, `— Young XI (≤21)`, `— Free-Agent XI`) wrap this.

**Market availability** — `PlayerRecord.is_market_available` = `is_free_agent OR is_transfer_listed`. Shown as ★ in GUI and CLI. The transfer-list flag is the **high bit (0x80) of `mystery3`** (byte 0x1A), identified by cross-referencing the 9 visible in-game LISTA TRASFERIMENTI entries against the DB (all 9 have the bit set; 255 players total flagged across all positions/divisions, consistent with the in-game price-bracket filters). The lower 7 bits of `mystery3` vary independently and are not yet identified. Note: `weeks_since_transfer` (byte 0x19, previously misnamed `transfer_weeks`) is a post-transfer cooldown counter and plays no role in market availability.

**Player names** — procedurally generated from the 4-byte RNG seed using a rolling-buffer hash (reversed from the original Windows binary). The surname table lives on the **game disk** — a separate ADF from the save disk. Loading the game ADF is optional, but names stay blank everywhere (roster, Best XI, exports, Line-up Coach, …) until it's loaded. All save *editing* works without it. GUI: File → Open Game Disk… (Cmd/Ctrl+G). CLI: `--game-adf PATH` flag on every subcommand that prints player details.

`GameDisk` detects the build during `load()` and exposes `build`, `names_available`, and `is_beta`:

- **`italian`** (stable): AmigaDOS OFS disk, `2507` executable, DEFAJAM-decompressed, surnames at 0x15B02–0x162E6 in the image. 245 names. Verified against the live game.
- **`english`** (BETA): PM custom-file-table disk (same 16-byte layout as save disks), `manager.prg` is plain m68k not hunk. Surname table is plaintext NUL-separated ASCII; located by anchor-scan on `Adams\0Adcock\0Addison\0Aldridge\0Alexander\0`. 183 names. Surnames and the reused Italian initials charsets cross-checked against a real in-game roster screen on 2026-04-17 — every observed surname and initial matched. BETA only because the seed→exact-name mapping hasn't been verified against a known seed; individual resolutions could in principle drift.
- **`unknown-pm`**: disk parses as PM-shaped but has no recognised executable. Loads with `surnames=[]` so save editing works; names stay blank.

The GameDisk loader is deliberately lenient: any disk that looks PM-shaped is accepted; unsupported builds load with `names_available=False` rather than erroring. GUI shows an amber toolbar label + BETA dialog for English disks; CLI prints a stderr `Note:` on BETA loads.

**Team names** — each `.sav` slot *is* a 4408-byte block of 44 × 100-byte team records, and each record carries its own team name as a NUL-terminated ASCII string at sub-offset 68 (same layout the game disk's `start.dat` uses). `SaveSlot._load_team_names` reads those in-record names as the source of truth for team_names[1..43] (matching the 1-based team_index mapping). Slot 0 — the user's own team — has no in-record name there, so it's filled from `PM1.nam[0]` when present (Italian saves) or falls back to the `"Team 0"` placeholder (English/BETA saves without `PM1.nam`). Any record that fails the ASCII-name sanity check also falls back to `"Team N"`. `team_names_from_save` stays `True` whenever any record yielded a real name. `SaveSlot.apply_team_name_fallback(gd.team_names)` still exists for the edge case of English saves with no usable in-record name for slot 0, and is a no-op when records already populated that slot. Historical note: earlier versions read team names from `PM1.nam` directly, but that file is a static snapshot of the *initial* standings and goes stale after any gameplay — which is why pm6/pm7 squad rosters used to display against the wrong team labels.

**GUI** — tkinter app (`pm_gui.py`) with one main window and a `CareerTrackerWindow` Toplevel under Tools. The main window is organised as menu bar (File/Edit/View/Tools/Help with platform-aware accelerators — `MOD`/`MOD_LABEL` resolve to Cmd/Ctrl), slim toolbar (Save slot + **View** combo), left tree of players, and a right-hand detail pane. Detail pane = pinned identity header + `ttk.Notebook` tabs (Core/Skills/Status/Season/Career) + sticky Apply/Revert footer. The **View** combo includes regular teams plus special entries "— Young Talents (≤21)", "— Top Scorers", "— Squad Analyst (all teams)", and the XI entries defined in `XI_ENTRIES`, all handled in `_refresh_player_list()`. The "Mkt" column (★) is always visible.

**Dirty state** — `_set_dirty(True/False)` updates the window title with a "•" marker; `_apply_changes` dirties, `_save_adf`/`_save_adf_as` clean. `WM_DELETE_WINDOW` and macOS Cmd+Q both route to `_on_quit` so unsaved edits prompt to save. Opening a different ADF also prompts.

**Recent files** — `~/.pmsavedisktool/recent.json` holds up to 5 paths. `_load_recent`/`_save_recent`/`_rebuild_recent_menu` manage the File → Open Recent submenu; missing paths are pruned when clicked.

**Export row schema** — `pm_core.save.player_to_row(player, slot, game_disk=None)` is the single source of truth for the export shape. Both `pm_cli export-players` and the GUI's File → Export Players… use it. Don't duplicate the schema.

**Byte layout source of truth** — `pm_core.player.FIELD_LAYOUT` (list of `(offset, size, name, note)`) describes which bytes in the 42-byte record belong to which field, with any known invariants in the note. `field_at_offset(offset)` returns `(field_name, sub_index, field_size)` for any byte. The Byte Workbench UI and `byte-stats` / `byte-diff` CLI commands both label offsets from this table — if you identify a new field, update it here once.

**Byte Workbench** — `pm_core.workbench` (pure analysis: `byte_histogram`, `bit_probability`, `diff_sets`, `query`) plus `ByteWorkbenchWindow` in `pm_gui.py`. Three tabs: Raw View, Histogram, Diff. Preset filters live in `BYTE_PRESETS` (GUI) and `BYTE_FILTERS` (CLI) — keep them aligned. The Diff tab computes `|P(bit=1|A) − P(bit=1|B)|` across all 42×8 = 336 bits; this is the method that originally cracked `mystery3 bit 0x80` and is the primary tool for cracking the remaining unknowns.

**Line-up Coach (BETA)** — `pm_core.lineup` (pure library) plus `LineupCoachWindow` in `pm_gui.py` and the `suggest-xi` CLI subcommand. The module defines a **12-role taxonomy** (`ROLES`: GK / CB·FB·SW / DM·CM·AM·WM / POA·TGT·WNG·DLF) with per-role skill weight vectors, optional height/age modifiers, and a `CROSS_POSITION_PENALTY`. `FORMATION_ROLES` maps each formation to an 11-slot role list; its per-position counts must stay in sync with `pm_core.save.FORMATIONS` (enforced by `tests/test_lineup.py::TestFormationTaxonomyConsistency`). XI assembly uses global-greedy assignment — score every (slot, player) pair and pick by descending fit — which beats slot-order greedy on mixed-role formations like 4-3-3. `score_xi` combines `total_skill`, `mean_fit`, `mean_morale`, `mean_fatigue`, `mean_card_risk`, `mean_form` via `DEFAULT_COMPOSITE_WEIGHTS`. Scoring is a **heuristic** layered on PM's 10 skill fields — PM's actual match-engine weights are **not** reverse-engineered; the module docstring and all user-facing surfaces label the feature BETA. Default eligibility filters out injured players; the CLI/GUI expose `--include-injured` for the "ideal" XI.

**Byte compatibility** — `serialize_player()` must produce byte-identical output to `parse_player()`. The round-trip test (`test_roundtrip_all_players`) enforces this. Never change the serialization order.

## Constraints

- Zero external dependencies. `pm_core/` is pure Python; GUI uses only `tkinter` (stdlib).
- Minimum Python 3.10 (codebase uses PEP 604 `X | None` and PEP 585 generics).
- All writes go through `ADF.write_at()` — never write to a `FileEntry`'s offset directly from outside `SaveSlot`.
- First write on a loaded ADF creates a sibling `<file>.adf.bak`; subsequent writes don't overwrite it. Both CLI `edit-player` and GUI Save go through the same path.
- `start.dat` is excluded from `list_saves()` by design; it is a template, not an editable save slot.
