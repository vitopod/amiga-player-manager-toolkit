# PMSaveDiskToolkit

Cross-platform save disk editor and analytics workbench for **Player Manager**
(Anco, 1990) on Amiga.

Started as a cross-platform port of **PMSaveDiskTool v1.2** by
**UltimateBinary** (http://www.ultimatebinary.com) — full credit to them
for the original save disk format research and field naming.

From there it grew into something broader: Mac / Linux / Windows support,
a full command-line interface, player name generation from the game disk,
and a stack of analytical views — Young Talents, Championship Highlights,
Top 11 of the championship, Squad Analyst, Career Tracker, Byte Workbench,
Line-up Coach (BETA), and a graphical **Compare Players** window. The editor
stays byte-for-byte compatible with v1.2.

---

## Requirements

- Python 3.10+
- No external dependencies (tkinter is included with Python)

## Important: Always Work on Copies

**Always make a backup of your save disk ADF before editing.**
The tool writes changes directly to the file. If something goes wrong, there is no undo.
Keep the original ADF safe and work on a copy.

## Upgrading from a previous version

The toolkit is distributed as a plain folder of Python files — there is no
installer or pip package. You upgrade by replacing the folder.

**If you cloned the repository with git:**

```
git pull
```

Or to pin to a specific tag:

```
git checkout v2.2.10
```

**If you downloaded a release zip:**

1. Download the latest zip from
   https://github.com/vitopod/amiga-player-manager-toolkit/releases
2. Unpack it and replace the previous folder with the new one.

Your settings and history survive the upgrade. Recent files and the
update-check preferences live in `~/.pmsavedisktool/`, which sits outside
the source tree and is never touched by the upgrade. Save disks themselves
are byte-compatible across all releases, so no migration is needed — but
the "always work on copies" rule still holds.

**Which version are you on?** Check `Help → About…` in the GUI, or run
`python3 PMSaveDiskTool_v2/pm_cli.py --version`. The in-app
`Help → Check for Updates…` compares against the latest GitHub release.

**Users on 2.2.0 or earlier should upgrade.** Release 2.2.1 fixed a
byte-alignment bug in the player record (matches-last-year and
career-division years were reading one byte low) and corrected the
aggression field, which is stored inverted on disk. Later releases
layered the update-check UI on top but depend on the 2.2.1 fix.

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
- **Player names from the game disk** — load your game disk ADF to resolve player names from their RNG seeds. Italian build is stable (245 surnames). English build is **BETA** (183 surnames; surnames and initials verified against an in-game roster screenshot). Other PM-shaped disks load with names blank rather than failing.
- **Team names for English / BETA save disks** — when a game disk is loaded, the toolkit fills in real team names (CHELSEA, LIVERPOOL, TOTTENHAM, …) in place of generic placeholders. Italian saves are unaffected.
- Browse players by team, view all players, or view free agents
- **Young Talents** — players aged ≤ 21 sorted by skill; ★ marks market availability
- **Championship Highlights** — top scorers grouped by division; ★ marks market availability
- **Top 11** — best XI in a chosen formation (4-4-2, 4-3-3, 3-5-2); includes Young XI (≤21) and Free-Agent XI variants
- **Squad Analyst** — per-team breakdown: roster size, position counts, average age and skill, youngest/oldest/best, on-market count. Available in the GUI and via `pm_cli.py squad-analyst`.
- **Career Tracker** — diff two save slots to track skill, age, and team changes per player. GUI: **Tools → Career Tracker...**. CLI: `pm_cli.py career-tracker`.
- **Byte Workbench** — reverse-engineering tool for the player record: raw byte dump with field labels, value histogram, and bit-level diff between two player sets. GUI: **Tools → Byte Workbench...**. CLI: `pm_cli.py byte-stats`, `pm_cli.py byte-diff`.
- **Line-up Coach (BETA)** — suggests a starting XI using a 12-role taxonomy layered on PM's skill fields; ranks formations by a composite of skill, role fit, morale, and form. Also picks two bench reserves (backup goalkeeper plus best remaining outfielder). BETA: scoring is a heuristic, not a reconstruction of PM's match engine. GUI: **Tools → Line-up Coach (BETA)...**. CLI: `pm_cli.py suggest-xi` (bench size via `--reserves N`).
- **Compare Players** — graphical side-by-side comparison: radar chart (10-axis spider chart) + skill bars for any two players. Right-click any player in the list → **Send to Compare…**, or **Tools → Compare Players…** (Cmd/Ctrl+P).
- **Export** players as CSV or JSON for use in spreadsheets or external tools. GUI: **File → Export Players...**. CLI: `pm_cli.py export-players --format csv|json`.
- View and edit all player attributes: age, position, skills, career stats
- **Live skill bars** — the Skills tab shows a colour-coded mini-bar next to each attribute that updates in real time as you edit values.
- **Game-inspired visual theme** — deep navy / amber / cyan palette throughout the GUI, with a splash screen on launch.
- **Automatic `.bak`** on first write — your original state is always recoverable
- Byte-for-byte compatible with PMSaveDiskTool v1.2
- Works on Mac, Linux, and Windows

The ★ marker indicates a player is on the market (free agent or transfer-listed).

## Temporarily Removed Features

Several features from the previous Mac version are planned for a future release (if feasible):

- **Transfer Market** — move players between teams
- **League Stats** — view and edit standings and season records
- **Patch Composer** — write patches into the game disk

Contributions welcome — see the License section.

## Project Structure

```
PMSaveDiskTool_v2/
  pm_core/    Core library (zero dependencies)
  pm_gui.py   tkinter GUI
  pm_cli.py   Command-line interface
  tests/      Test suite
```

## Tests

```
python3 -m pytest PMSaveDiskTool_v2/tests/ -v
```

## Credits

- **PMSaveDiskTool v1.2** by UltimateBinary (http://www.ultimatebinary.com) — original tool and format research.
- **Player Manager** by Anco Software (1990).
- **Dino Dini** (https://github.com/dndn1011) — original programmer of Player Manager.
- **Topaz** font — the GUI bundles `Topaz_a1200_v1.0.ttf` for its retro Amiga look. TrueType rendition © 2009 dMG of Trueschool and Divine Stylers (<http://www.trueschool.org>), licensed under [CC BY-NC-SA 3.0](http://creativecommons.org/licenses/by-nc-sa/3.0/). Full attribution and terms in `PMSaveDiskTool_v2/assets/NOTICE.md`. Sourced from <https://github.com/rewtnull/amigafonts>.

## License

Released under the [MIT License](LICENSE). Contributions and improvements are welcome.

Note: bundled third-party assets in `PMSaveDiskTool_v2/assets/` are under their own licenses — see `PMSaveDiskTool_v2/assets/NOTICE.md`. In particular, the bundled Topaz font is **non-commercial only** (CC BY-NC-SA 3.0); remove the `.ttf` file if you redistribute the toolkit as part of a commercial product. The GUI falls back to Courier New automatically.

This project is not affiliated with or endorsed by Anco Software or UltimateBinary.
Reverse-engineering was performed for interoperability purposes only.
