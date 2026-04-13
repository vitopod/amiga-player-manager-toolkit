# Amiga Player Manager Toolkit

A Mac toolkit for editing **Player Manager** (Anco, 1990) save disks on ADF images. Reverse-engineer saves, compose game-disk patches, visualise tactics, and browse the 68000 game code — all without a running emulator.

Originally based on **Player Manager Save Disk Tool v1.2 (Experimental)** by [UltimateBinary](https://ultimatebinary.blogspot.com) (Windows, 2010). This project re-implements and significantly extends that tool for macOS.

---

## What it does

| Feature | Description |
|---------|-------------|
| **Save Disk Editor** | Open any Player Manager save disk ADF. Browse all 11 save slots. Edit team names, divisions, budget tiers, team values, league stats, and the 25-player roster for all 44 teams. Write changes back to the ADF. |
| **Game Disk Integration** | Auto-loads `PlayerManagerITA.adf` (Italian version) and extracts 245 player surnames from the DEFAJAM-decompressed game image. Player IDs in the roster show real names. |
| **Patch Composer** | GUI editor for the 68000 runtime patch block (block 1137) on the game disk. Add, remove, and preview byte/word/long patches — with space budget tracking and OFS checksum auto-calculation. Includes one-click manager age patch. |
| **League Tables** | Four-division league tables sorted by points and goals, with promotion and relegation zone highlighting. |
| **Compare Saves** | Diff two save slots: player transfers, division changes, and team value deltas. |
| **Tactics Viewer** | Visual pitch editor for `.tac` files. Ten zones × two ball states (with/without ball) × ten outfield players. Drag player dots on a football pitch and save back to disk. |
| **68000 Disassembler** | Interactive disassembler for the decompressed game image. All opcodes and addressing modes, cross-reference search, word/MUL/DIVU searches, and double-click address navigation. |

---

## Requirements

| | |
|-|-|
| **macOS** | 10.13 or later |
| **Python** | 3.8+ with tkinter. Use `/usr/local/bin/python3.11` from [python.org](https://www.python.org/downloads/) — the system Python and pyenv Pythons typically lack tkinter. |
| **Save disk ADF** | A Player Manager **save/data disk** image (901,120 bytes, FFS). |
| **Game disk ADF** *(optional)* | `PlayerManagerITA.adf` placed next to the script enables player name lookup, the disassembler, and auto-populates the Patch Composer. |

> **Note:** ADF images are not included. You must dump your own floppies. `.adf` files are excluded from this repository by `.gitignore`.

---

## Running

```bash
/usr/local/bin/python3.11 PMSaveDiskTool_Mac/PMSaveDiskTool.py
```

No dependencies beyond the Python standard library.

---

## Usage

1. **Open ADF** — select a Player Manager save disk ADF.
2. Select a **save slot** from the left panel.
3. Select a **team** from the division-grouped list.
4. Edit fields across the four tabs: **Roster**, **Team Info**, **League Stats**, **Hex Dump**.
5. Click **Apply Changes** to write to the in-memory ADF buffer.
6. **Save** (Cmd+S) or **Save As…** (Cmd+Shift+S) to write back to disk.

Tool windows are under the **Tools** menu: Patch Composer, League Tables, Compare Saves, Tactics Viewer, Disassembler.

---

## Headless / scripting use

All parsing logic is cleanly separated from the GUI. To use the data layer in a script:

```python
exec(open('PMSaveDiskTool_Mac/PMSaveDiskTool.py').read().split('# ─── GUI')[0])

adf = ADF('DataDisk_Simone.adf')
entries = parse_file_table(adf)
sf = SaveFile(adf, next(e for e in entries if e.name == 'START.sav'))
for team in sf.teams[:5]:
    print(team.index, team.name, team.division, team.num_players)
```

---

## Game compatibility

Tested with the **Italian version** (`PlayerManagerITA.adf`). The save disk format is identical across all language versions — the editor works with English, German, and other versions too. The Patch Composer, Disassembler, and player name lookup are Italian-version-specific.

---

## Platform notes

Developed for **MiSTer FPGA** (Minimig core) workflow, where there is no runtime debugger and all work happens offline on ADF files. The Patch Composer's OFS checksum recalculation means patches can be written and loaded directly without manual hex work.

---

## Credits

- **Player Manager Save Disk Tool v1.2 (Experimental)** — [UltimateBinary](https://ultimatebinary.blogspot.com) (Windows reference implementation, 2010)
- **Player Manager** — Anco Software, 1990
- **DEFAJAM decompressor** — reverse-engineered from the ITA game disk; original packer by DEFAJAM
- **Block 1137 crack code** — arab^Scoopex (copy-protection bypass in the game disk)

---

## License

This tool and its source code are released under the MIT License.

The game itself (Player Manager, Anco 1990) is copyrighted software. ADF images are not distributed here.
