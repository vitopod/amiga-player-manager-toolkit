# PMSaveDiskToolkit

Cross-platform save disk editor and analytics workbench for **Player Manager**
(Anco, 1990) on Amiga.

Started out as a cross-platform port of **PMSaveDiskTool v1.2** by
**UltimateBinary** (http://www.ultimatebinary.com) — that's where I got the
save disk format, the 42-byte record layout, and the field naming
conventions. Full credit to UltimateBinary for that ground-work; without it
this project wouldn't exist.

From there it's grown into something different. On top of the original
byte-for-byte save editing I've added: Mac / Linux / Windows support, a
full command-line interface, **player name generation** from the game
disk (reverse-engineered from the DEFAJAM-compressed executable), and a
stack of analytical / reverse-engineering views that weren't part of v1.2 —
Young Talents, Championship Highlights, Top 11 of the championship,
Squad Analyst, Career Tracker, Byte Workbench (the reverse-engineering UI
that originally cracked the LISTA TRASFERIMENTI flag), and the Line-up
Coach (BETA) role-fit / formation suggester. The editor part stays
byte-for-byte compatible with v1.2; everything else is new territory.

---

## Requirements

- Python 3.10+
- No external dependencies (tkinter is included with Python)

## Important: Always Work on Copies

**Always make a backup of your save disk ADF before editing.**
The tool writes changes directly to the file. If something goes wrong, there is no undo.
Keep the original ADF safe and work on a copy.

## Quick Start

**GUI:**

```
python3 PMSaveDiskTool_v2/pm_gui.py
```

Then **File → Open Save Disk…** and pick your save disk ADF.

**CLI:**

> The examples below use `your_save.adf` and `your_game.adf` as
> placeholders. Substitute the actual filenames of your own disks.

```
python3 PMSaveDiskTool_v2/pm_cli.py list-saves your_save.adf
python3 PMSaveDiskTool_v2/pm_cli.py list-players your_save.adf --save pm1.sav --team 0
python3 PMSaveDiskTool_v2/pm_cli.py show-player your_save.adf --save pm1.sav --id 42
python3 PMSaveDiskTool_v2/pm_cli.py edit-player your_save.adf --save pm1.sav --id 42 --age 20 --pace 200
```

With player names (requires game disk ADF):

```
python3 PMSaveDiskTool_v2/pm_cli.py list-players your_save.adf --save pm1.sav --team 0 \
    --game-adf your_game.adf
```

## Features

- Open any Player Manager save disk ADF image
- **Load game ADF to show player names**. Italian build is stable (245 surnames). English build is **BETA** (183 surnames, anchor-scan extraction, initials charsets reused from the Italian build). Other PM-shaped disks load with names blank rather than failing.
- **Team names for English / BETA save disks** — English save disks don't ship `PM1.nam`, so team names default to `"Team 0".."Team 43"`. When a game disk is loaded, the toolkit fills them in from `start.dat` on the game disk (CHELSEA, LIVERPOOL, TOTTENHAM, …). Italian saves are unaffected.
- Browse players by team, view all players, or view free agents
- **Young Talents** — list players aged ≤ 21 sorted by skill; ★ marks who is available on the market
- **Championship Highlights** — top scorers grouped by division; ★ marks who is available on the market
- **Top 11** — the best XI of the championship in a chosen formation (4-4-2, 4-3-3, 3-5-2); includes Young XI (≤21) and Free-Agent XI variants, and an optional per-team cap
- **Squad Analyst** — per-team composition breakdown (roster size, GK/DEF/MID/FWD counts, average age and skill, youngest/oldest/best, on-market count). Available in the GUI as "— Squad Analyst (all teams)", as a per-team summary label above the roster view, and via `pm_cli.py squad-analyst`.
- **Career Tracker** — diff two save slots (same ADF or two ADFs) to surface skill, age, and team changes per player. Available in the GUI under **Tools → Career Tracker...** and via `pm_cli.py career-tracker`.
- **Byte Workbench** — reverse-engineering UI for the 42-byte player record with three tabs: raw dump (hex/dec/bin with field labels), value histogram at any offset/mask across a preset player set, and bit-level diff between two sets. The same method that identified `mystery3` bit 0x80 as the LISTA TRASFERIMENTI flag, now a push-button tool for cracking the remaining unknowns (`mystery3` lower 7 bits, `last_byte` skew). GUI: **Tools → Byte Workbench...**. CLI: `pm_cli.py byte-stats`, `pm_cli.py byte-diff`.
- **Line-up Coach (BETA)** — suggests a formation + starting XI for a team (or the whole championship) using a 12-role taxonomy layered on PM's skill fields, ranks 4-4-2 / 4-3-3 / 3-5-2 by a composite of skill, role fit, morale, fatigue, card risk and form, and flags players whose best-fit role lies outside their nominal position. BETA: scoring is a heuristic, not a reconstruction of PM's match engine — treat output as *suggested*, not *optimal*. GUI: **Tools → Line-up Coach (BETA)...**. CLI: `pm_cli.py suggest-xi`.
- **Export** players as CSV or JSON for use in spreadsheets or external tools: GUI **File → Export Players...** or `pm_cli.py export-players --format csv|json`.
- View and edit all player attributes: age, position, skills, career stats
- **Automatic `.bak`** on first write — your original byte-for-byte state is always recoverable
- Save changes back to ADF — byte-for-byte compatible with PMSaveDiskTool v1.2
- Works on Mac, Linux, and Windows

The ★ market availability marker appears throughout: a player is marked if they are a free agent
(team_index == 0xFF) or on the in-game LISTA TRASFERIMENTI (high bit of the `mystery3` byte).
See `PMSaveDiskTool_v2/README.md`.

## Temporarily Removed Features

This version is a ground-up rewrite focused on correctness and cross-platform support.
Several features from the previous Mac version have been temporarily removed while they
are reworked and re-validated. They are still planned for a future release (if feasible):

- **Transfer Market** — move players between teams with full consistency (roster + player DB)
- **League Stats** — view and edit team standings, division flags, and season records
- **Patch Composer** — write copy-protection bypass and custom patches into the game disk

Contributions to re-implement any of the above are welcome — see the License section below.

## Project Structure

```
pm_core/          Core library (zero dependencies)
  adf.py          ADF disk image I/O
  player.py       42-byte player record parsing/serialization
  save.py         Save file and player database handling
  names.py        DEFAJAM decompressor + name generation from RNG seeds
pm_gui.py         tkinter GUI
pm_cli.py         Command-line interface
tests/            Test suite (19 tests, all verified against Save1_PM.adf)
```

## Tests

```
python3 -m pytest tests/ -v
```

## Credits

- **PMSaveDiskTool v1.2** by UltimateBinary (http://www.ultimatebinary.com) — original
  Windows tool, save disk format research, and field naming. This project would not exist
  without that work.
- **Player Manager** by Anco Software (1990) — the game.
- **Dino Dini** (https://github.com/dndn1011) — original programmer of Player Manager.
  The game that started it all.

## License

Released under the [MIT License](LICENSE). You are free to use, modify, and distribute
this software. Contributions and improvements are welcome — open a pull request or issue
on GitHub.

This project is not affiliated with or endorsed by Anco Software or UltimateBinary.
Reverse-engineering was performed for interoperability purposes only.
