# PMSaveDiskToolkit

Cross-platform save disk editor and analytics workbench for
**Player Manager** (Anco, 1990) on Amiga.

Started out as a cross-platform port of **PMSaveDiskTool v1.2** by
**UltimateBinary** (http://www.ultimatebinary.com) — that's where the
save disk format, the 42-byte record layout, and the field naming
conventions come from. Full credit to UltimateBinary for that
ground-work; without it this project wouldn't exist.

From there it's grown into something different. On top of the original
byte-for-byte save editing I've added Mac / Linux / Windows support, a
full command-line interface, **player name generation** from the game
disk (reverse-engineered from the DEFAJAM-compressed executable), and a
stack of analytical / reverse-engineering views that weren't part of
v1.2 — Young Talents, Championship Highlights, Top 11, Squad Analyst,
Career Tracker, Byte Workbench, and Line-up Coach (BETA). The editor
part stays byte-for-byte compatible with v1.2; everything else is new
territory.

---

## Requirements

- Python 3.8+
- No external dependencies (tkinter is included with Python)

## Important: Always Work on Copies

**Always make a backup of your save disk ADF before editing.**
The tool writes changes directly to the file. If something goes wrong, there is no undo.
Keep the original ADF safe and work on a copy.

## Quick Start

**GUI:**

```
python3 pm_gui.py
```

Then **File → Open Save Disk…** and pick your save disk ADF.

**CLI:**

> The examples below use `your_save.adf` and `your_game.adf` as
> placeholders. Substitute the actual filenames of your own disks.

```
python3 pm_cli.py list-saves your_save.adf
python3 pm_cli.py list-players your_save.adf --save pm1.sav --team 0
python3 pm_cli.py show-player your_save.adf --save pm1.sav --id 42
python3 pm_cli.py edit-player your_save.adf --save pm1.sav --id 42 --age 20 --pace 200
```

With player names (requires game disk ADF):

```
python3 pm_cli.py list-players your_save.adf --save pm1.sav --team 0 \
    --game-adf your_game.adf
```

## Features

- Open any Player Manager save disk ADF image
- **Load game ADF to show player names**. Italian build is stable (245 surnames decompressed from the DEFAJAM-packed `2507` executable). English build is **BETA** (183 surnames extracted by anchor-scan from a PM-custom-file-table disk; initials charsets reused from the Italian build). Other PM-shaped disks load successfully but keep names blank rather than failing.
- **Team names for English / BETA save disks** — English save disks don't ship `PM1.nam`, so team names default to `"Team 0".."Team 43"`. When a game disk is loaded, the toolkit fills them in from `start.dat` on the game disk (e.g. CHELSEA, LIVERPOOL, TOTTENHAM). Italian saves are unaffected — `PM1.nam` still wins.
- Browse players by team, view all players, or view free agents
- **Young Talents** — list players aged ≤ 21 sorted by skill; ★ marks who is available on the market
- **Championship Highlights** — top scorers grouped by division; ★ marks who is available on the market
- **Top 11** — the best XI of the championship in a chosen formation (4-4-2, 4-3-3, 3-5-2); includes Young XI (≤21) and Free-Agent XI variants, and an optional per-team cap
- **Squad Analyst** — per-team breakdown: roster size, GK/DEF/MID/FWD counts, average age and skill, youngest/oldest/best, on-market count. GUI: "— Squad Analyst (all teams)" plus a summary label above the roster when a team is selected. CLI: `pm_cli.py squad-analyst [--team N]`.
- **Career Tracker** — diff two save slots (same ADF or two ADFs) to track per-player skill, age, and team changes. GUI: **Tools → Career Tracker...**. CLI: `pm_cli.py career-tracker --save-a pm1.sav --save-b pm2.sav`.
- **Byte Workbench** — reverse-engineering UI for the 42-byte player record: raw dump with field labels, value histogram at any offset/mask, and bit-level diff between two player sets (the same method that identified `mystery3` bit 0x80 as the LISTA TRASFERIMENTI flag). GUI: **Tools → Byte Workbench...**. CLI: `pm_cli.py byte-stats --offset 0x1A --mask 0x80`, `pm_cli.py byte-diff --set-a transfer-listed --set-b not-transfer-listed`.
- **Line-up Coach (BETA)** — suggests a formation + starting XI using a 12-role taxonomy (GK / CB·FB·SW / DM·CM·AM·WM / POA·TGT·WNG·DLF) layered on PM's skill fields; ranks 4-4-2 / 4-3-3 / 3-5-2 by a composite of skill, role fit, morale, fatigue, card risk and form; flags players whose best-fit role lies outside their nominal position. BETA: scoring is a heuristic, **not** a reconstruction of PM's match engine — treat output as *suggested*, not *optimal*. GUI: **Tools → Line-up Coach (BETA)...**. CLI: `pm_cli.py suggest-xi --team 0 --include-injured`.
- **Export** players as CSV or JSON. GUI: **File → Export Players...**. CLI: `pm_cli.py export-players --format csv|json [-o file]`.
- View and edit all player attributes: age, position, skills, career stats
- **Automatic `.bak`** sibling on first write — idempotent; never overwrites an existing backup
- Save changes back to ADF — byte-for-byte compatible with PMSaveDiskTool v1.2
- Works on Mac, Linux, and Windows

The ★ market availability marker appears throughout: a player is marked if they are a free agent
(team_index == 0xFF) **or** on the in-game LISTA TRASFERIMENTI. The transfer-list flag is the high
bit (0x80) of the `mystery3` byte (offset 0x1A), identified empirically by matching the 9 players
visible in the in-game transfer screen against the DB. The lower 7 bits of `mystery3` remain
unidentified.

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

Released under the [MIT License](../LICENSE). You are free to use, modify, and distribute
this software. Contributions and improvements are welcome — open a pull request or issue
on GitHub.

This project is not affiliated with or endorsed by Anco Software or UltimateBinary.
Reverse-engineering was performed for interoperability purposes only.
