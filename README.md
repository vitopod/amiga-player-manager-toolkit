# Amiga Player Manager Toolkit

A cross-platform toolkit for editing **Player Manager** (Anco, 1990) save disks on ADF images. Edit teams, rosters, and player attributes; compose game-disk patches; visualise tactics; and browse the 68000 game code — all without a running emulator.

The original **Player Manager Save Disk Tool v1.2** by [UltimateBinary](https://ultimatebinary.blogspot.com) (Windows, 2010) could edit team names, divisions, budgets, and player ID slots in save files. This project re-implements that foundation and adds: full player attribute access (the 42-byte per-player database stored on the save disk), player editing and transfer management, a 68000 runtime patch composer for the game disk, league tables, save comparison, a tactics viewer, and an interactive disassembler.

---

## What it does

| Feature | Description |
|---------|-------------|
| **Save Disk Editor** | Open any Player Manager save disk ADF. Browse all 11 save slots. Edit team names, divisions, budget tiers, team values, league stats, and the 25-player roster for all 44 teams. Write changes back to the ADF. |
| **Game Disk Integration** | Auto-loads a game disk ADF on startup and extracts 245 player surnames from the DEFAJAM-decompressed game image. Player IDs in the roster show real names. Tested with the Italian version; other versions likely work for save editing but name lookup is Italian-specific. |
| **Patch Composer** | GUI editor for the 68000 runtime patch block (block 1137) on the game disk. Add, remove, and preview byte/word/long patches — with space budget tracking and OFS checksum auto-calculation. Includes one-click manager age patch. |
| **League Tables** | Four-division league tables sorted by points and goals, with promotion and relegation zone highlighting. |
| **Compare Saves** | Tabbed diff of two save slots: player transfers, division/budget changes, and full Career Tracker (player DB diff with filters, age-skill trends, and Player Detail popup). |
| **Championship Highlights** | Player attribute browser. Reads the 42-byte per-player database stored on the save disk after each .sav file. Five tabs: Best By Position (GK/DEF/MID/FWD ranked by role skills), Top Scorers, Young Talents (age 16–22), Market Values, and Squad Analyst with renew/sack hints. |
| **Transfer Market** | Search and filter all ~1037 players by name, position, age, skill level. Transfer players between teams. Edit individual player attributes (10 skills, physical stats, career stats). |
| **Tactics Viewer** | Visual pitch editor for `.tac` files. Ten zones × two ball states (with/without ball) × ten outfield players. Drag player dots on a football pitch and save back to disk. |
| **68000 Disassembler** | Interactive disassembler for the decompressed game image. All opcodes and addressing modes, cross-reference search, word/MUL/DIVU searches, and double-click address navigation. |

---

## Requirements

| | |
|-|-|
| **OS** | macOS 10.13+, Windows 10+, or Linux |
| **Python** | 3.8+ with tkinter. On macOS use `/usr/local/bin/python3.11` from [python.org](https://www.python.org/downloads/) — the system Python and pyenv Pythons typically lack tkinter. On Windows, Python from python.org includes tkinter by default. |
| **Save disk ADF** | A Player Manager **save/data disk** image (901,120 bytes, FFS). |
| **Game disk ADF** *(optional)* | The game disk ADF placed next to the script (or its parent folder) enables player name lookup, the disassembler, and auto-populates the Patch Composer. |

> **Note:** ADF images are not included. You must dump your own floppies. `.adf` files are excluded from this repository by `.gitignore`.

**Accepted game disk filenames** (tried in this order, first match wins):

| Filename | Version |
|----------|---------|
| `PlayerManagerITA.adf` | Italian *(tested)* |
| `PlayerManager.adf` | English / generic |
| `PlayerManagerDE.adf` | German |
| `PlayerManagerFR.adf` | French |
| `PlayerManagerSP.adf` | Spanish |

---

## Running

**macOS:**
```bash
/usr/local/bin/python3.11 PMSaveDiskTool_Mac/PMSaveDiskTool.py
```

**Windows / Linux:**
```bash
python PMSaveDiskTool_Mac/PMSaveDiskTool.py
```

No dependencies beyond the Python standard library. Keyboard shortcuts use ⌘ on macOS and Ctrl on Windows/Linux.

---

## Usage

1. **Open ADF** — select a Player Manager save disk ADF.
2. Select a **save slot** from the sidebar.
3. Select a **team** from the division-grouped tree (filter by typing in the search box).
4. Edit fields across the four tabs: **Roster**, **Team Info**, **League Stats**, **Hex Dump** (switch with Cmd+1–4).
5. Click **Apply Changes** in the team header bar to write to the in-memory ADF buffer.
6. **Save** (Cmd+S) or **Save As…** (Cmd+Shift+S) to write back to disk.

Double-click a roster row to inline-edit the player ID. Tool windows are under the **Tools** menu: Patch Composer, League Tables, Compare Saves, Championship Highlights, Transfer Market, Tactics Viewer, Disassembler.

Full documentation: **[PMSaveDiskTool_Mac/MANUAL.md](PMSaveDiskTool_Mac/MANUAL.md)**

---

## Headless / scripting use

All parsing logic lives in `pm_data.py`, cleanly separated from the GUI. To use the data layer in a script:

```python
import sys
sys.path.insert(0, 'PMSaveDiskTool_Mac')
from pm_data import *

adf = ADF('DataDisk.adf')
entries = parse_file_table(adf)

# Browse teams in a save slot
sf = SaveFile(adf, next(e for e in entries if e.name == 'pm1.sav'))
for team in sf.teams[:5]:
    print(team.index, team.name, team.division, team.num_players)

# Read the player attribute database (42 bytes × ~1037 players)
players = parse_player_db(adf, sf.entry)
best_fwd = max((p for p in players.values() if p.position == 4),
               key=lambda p: p.role_skill_avg())
print(best_fwd)  # PlayerRecord(id=270, age=26, pos=FWD, skills_avg=144)

# Edit and write back
best_fwd.shooting = 200
write_player_db(adf, sf.entry, {best_fwd.player_id: best_fwd})
adf.save('DataDisk_modified.adf')
```

---

## Game compatibility

Developed and tested with the **Italian version** (`PlayerManagerITA.adf`). The save disk format is identical across all language versions, so save editing (team names, rosters, stats, tactics) works with English, German, French, and other versions too.

The **Patch Composer**, **Disassembler**, and **player name lookup** target the Italian game executable specifically. Using them with other versions should be harmless but the patch offsets, player names, and code addresses may differ.

---

## Platform notes

Developed for **MiSTer FPGA** (Minimig core) workflow, where there is no runtime debugger and all work happens offline on ADF files. The Patch Composer's OFS checksum recalculation means patches can be written and loaded directly without manual hex work.

---

## Credits

- **Player Manager Save Disk Tool v1.2 (Experimental)** — [UltimateBinary](https://ultimatebinary.blogspot.com) (Windows reference implementation, 2010)
- **Player Manager** — Anco Software, 1990. Designed by **[Dino Dini](https://github.com/dndn1011)**, whose work on Player Manager and Kick Off defined a golden era of football games on the Amiga. Thank you, Dino — these games are still being played and loved more than thirty years later.
- **DEFAJAM decompressor** — reverse-engineered from the ITA game disk; original packer by DEFAJAM

---

## License

This tool and its source code are released under the MIT License.

The game itself (Player Manager, Anco 1990) is copyrighted software. ADF images are not distributed here.
