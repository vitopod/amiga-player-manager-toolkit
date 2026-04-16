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

**42-byte player record** — fully documented in `player.py`. Key fields: bytes 0–3 RNG seed, byte 4 age, byte 5 position (1=GK 2=DEF 3=MID 4=FWD), byte 7 team_index (0xFF = free agent), bytes 10–19 ten skills.

**Real player filter** — `SaveSlot._is_real_player()` guards analytical views (Young Talents, Championship Highlights) against garbage sentinel records near the end of the DB. Criteria: `position in (1,2,3,4)` and `team_index <= 43 or team_index == 0xFF`.

**Market availability** — `PlayerRecord.is_market_available` is True when `is_free_agent` (team_index == 0xFF) or `transfer_weeks > 0`. Shown as ★ in GUI and CLI.

**Player names** — procedurally generated from the 4-byte RNG seed using a rolling-buffer hash (reversed from the original Windows binary). The 245-name surname table is inside the DEFAJAM-compressed `2507` executable on the game disk. Loading a game ADF is optional; all save editing works without it.

**GUI** — single-window tkinter app (`pm_gui.py`). Team dropdown includes regular teams plus special entries "— Young Talents (≤21)" and "— Top Scorers" handled in `_refresh_player_list()`. The "Mkt" column (★) is always visible.

**Byte compatibility** — `serialize_player()` must produce byte-identical output to `parse_player()`. The round-trip test (`test_roundtrip_all_players`) enforces this. Never change the serialization order.

## Constraints

- Zero external dependencies. `pm_core/` is pure Python; GUI uses only `tkinter` (stdlib).
- Minimum Python 3.8.
- All writes go through `ADF.write_at()` — never write to a `FileEntry`'s offset directly from outside `SaveSlot`.
- `start.dat` is excluded from `list_saves()` by design; it is a template, not an editable save slot.
