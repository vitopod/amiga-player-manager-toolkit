# PMSaveDiskTool v2

Cross-platform save disk editor for **Player Manager** (Anco, 1990) on Amiga.

This project is a cross-platform rewrite of **PMSaveDiskTool v1.2** by **UltimateBinary**
(http://www.ultimatebinary.com). All credit for the original Windows tool, the save disk format
research, and the field naming conventions goes to UltimateBinary. This version adds Mac and
Linux support, player name generation from the game disk, and a command-line interface.

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

**CLI:**

```
python3 pm_cli.py list-saves Save1_PM.adf
python3 pm_cli.py list-players Save1_PM.adf --save pm1.sav --team 0
python3 pm_cli.py show-player Save1_PM.adf --save pm1.sav --id 42
python3 pm_cli.py edit-player Save1_PM.adf --save pm1.sav --id 42 --age 20 --pace 200
```

With player names (requires game disk ADF):

```
python3 pm_cli.py list-players Save1_PM.adf --save pm1.sav --team 0 \
    --game-adf PlayerManagerITA.adf
```

## Features

- Open any Player Manager save disk ADF image
- **Load game ADF to show player names** (decompressed from game executable; compatible with Italian version and potentially others)
- Browse players by team, view all players, or view free agents
- **Young Talents** — list players aged ≤ 21 sorted by skill; ★ marks who is available on the market
- **Championship Highlights** — top scorers grouped by division; ★ marks who is available on the market
- **Top 11** — the best XI of the championship in a chosen formation (4-4-2, 4-3-3, 3-5-2); includes Young XI (≤21) and Free-Agent XI variants, and an optional per-team cap
- **Squad Analyst** — per-team breakdown: roster size, GK/DEF/MID/FWD counts, average age and skill, youngest/oldest/best, on-market count. GUI: "— Squad Analyst (all teams)" plus a summary label above the roster when a team is selected. CLI: `pm_cli.py squad-analyst [--team N]`.
- **Career Tracker** — diff two save slots (same ADF or two ADFs) to track per-player skill, age, and team changes. GUI: **Tools → Career Tracker...**. CLI: `pm_cli.py career-tracker --save-a pm1.sav --save-b pm2.sav`.
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
