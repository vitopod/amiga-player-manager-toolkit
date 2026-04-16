# PMSaveDiskTool v2 — User Manual

## Overview

PMSaveDiskTool v2 edits save disks for the Amiga game **Player Manager** (Anco, 1990).
It reads standard ADF disk images, lets you view and modify player attributes, and writes
the changes back. The modified ADF can then be loaded in an emulator (WinUAE, FS-UAE) or
on real hardware (MiSTer FPGA, Gotek, real Amiga).

> **Always work on a copy of your save disk ADF, never on the original.**
> The tool writes changes directly to the file — there is no undo. Keep the original ADF
> in a safe location and open only the copy for editing.

**Based on PMSaveDiskTool v1.2 by UltimateBinary** (http://www.ultimatebinary.com).
The original Windows-only tool by UltimateBinary laid the groundwork for understanding the
save disk format, the 42-byte player record layout, and the field naming conventions used
throughout this project. All credit for that foundational research goes to UltimateBinary.
This version extends it with cross-platform support, player name generation, and a CLI.

---

## GUI Usage

### Opening a save disk

1. Run `python3 pm_gui.py`
2. Click **Open Save Disk** or use **File > Open Save Disk ADF** (Ctrl+O)
3. Select your Player Manager save disk `.adf` file — **open a copy, not the original**

### Loading player names (optional)

Player names are generated from the game disk, not the save disk. To see names:

1. Click **Load Game ADF (names)** or use **File > Open Game ADF (for names)** (Ctrl+G)
2. Select your `PlayerManagerITA.adf` (or any Player Manager game disk)
3. The tool decompresses the game executable, extracts the surname table, and
   immediately populates the Name column and player detail panel

If no game ADF is loaded, the Name field is left blank — all other editing functions
work normally without it.

### Selecting a save slot

The game supports up to 7 save slots (pm1.sav through pm7.sav). Use the **Save** dropdown
in the toolbar to switch between them.

### Browsing players

Use the **Team** dropdown to filter players:

- **All Players** — every player with age > 0
- **Free Agents** — unassigned players (team index 0xFF)
- **0: MILAN**, **1: SAMPDORIA**, etc. — players on a specific team
- **— Young Talents (≤21)** — players aged 21 or under, sorted by total skill descending
- **— Top Scorers** — all active players sorted by division, then goals this season descending
- **— Top 11 (4-4-2)** / **— Top 11 (4-3-3)** — best XI of the championship in that formation
- **— Young XI (≤21)** — best XI built from under-21s only
- **— Free-Agent XI** — best XI you could assemble from free agents

Click any player in the list to see their full details in the right panel.

### Market availability (★)

A **★** in the Mkt column means the player is currently purchasable — either a free agent
or listed for transfer. The column is visible in all views. Use Young Talents or Top Scorers
to quickly spot high-value targets you can actually sign.

### Editing a player

1. Select a player from the list
2. Modify any field in the detail panel (age, skills, stats, etc.)
3. Click **Apply Changes** to write the changes to the in-memory ADF image
4. Use **File > Save ADF** (Ctrl+S) to write back to disk

**Important:** "Apply Changes" updates the in-memory image only. You must also **Save ADF**
to persist changes to the file on disk.

### Save As

Use **File > Save ADF As** to write to a new file, keeping the original unmodified.
This is the safest workflow: always keep an unedited backup of your save disk and use
**Save ADF As** to produce modified copies.

---

## CLI Usage

All CLI commands take the save disk ADF path as the first argument.

### List save slots

```
python3 pm_cli.py list-saves Save1_PM.adf
```

Output:
```
Save File         Offset   Size
--------------------------------
pm1.sav         0x013e20   4408
pm2.sav         0x025820   4408
...
pm7.sav         0x07ba20   4408
```

### List players

Show all players in a save:
```
python3 pm_cli.py list-players Save1_PM.adf --save pm1.sav
```

Filter by team index (0–43):
```
python3 pm_cli.py list-players Save1_PM.adf --save pm1.sav --team 0
```

Show free agents only:
```
python3 pm_cli.py list-players Save1_PM.adf --save pm1.sav --free-agents
```

Show player names (requires game disk ADF):
```
python3 pm_cli.py list-players Save1_PM.adf --save pm1.sav --team 0 \
    --game-adf PlayerManagerITA.adf
```

### Show player details

```
python3 pm_cli.py show-player Save1_PM.adf --save pm1.sav --id 42
```

Displays all 42-byte fields with a visual skill bar.

### Edit a player

```
python3 pm_cli.py edit-player Save1_PM.adf --save pm1.sav --id 42 \
    --age 20 --pace 200 --shooting 180
```

This modifies the ADF file in place. To write to a different file:
```
python3 pm_cli.py edit-player Save1_PM.adf --save pm1.sav --id 42 \
    --age 20 -o modified.adf
```

#### Editable fields

| Flag | Field | Range |
|------|-------|-------|
| `--age` | Age | 0-255 |
| `--position` | Position | 1=GK, 2=DEF, 3=MID, 4=FWD |
| `--division` | Division | 0-3 |
| `--team-index` | Team | 0-43, or 255 for free agent |
| `--height` | Height (cm) | 0-255 |
| `--weight` | Weight (kg) | 0-255 |
| `--stamina` | Stamina | 0-200 |
| `--resilience` | Resilience | 0-200 |
| `--pace` | Pace | 0-200 |
| `--agility` | Agility | 0-200 |
| `--aggression` | Aggression | 0-200 |
| `--flair` | Flair | 0-200 |
| `--passing` | Passing | 0-200 |
| `--shooting` | Shooting | 0-200 |
| `--tackling` | Tackling | 0-200 |
| `--keeping` | Keeping | 0-200 |
| `--injury-weeks` | Current injury duration | 0-255 |
| `--disciplinary` | Disciplinary points | 0-255 |
| `--morale` | Morale | 0-255 |
| `--value` | Market value | 0-255 |
| `--weeks-since-transfer` | Weeks since last transfer (post-transfer cooldown) | 0-255 |
| `--goals-this-year` | Goals scored this season | 0-255 |
| `--goals-last-year` | Goals scored last season | 0-255 |
| `--matches-this-year` | Matches played this season | 0-255 |
| `--matches-last-year` | Matches played last season | 0-255 |
| `--contract-years` | Contract length in years | 0-255 |
| `--div1-years` .. `--div4-years` | Seasons spent in each division | 0-255 |
| `--int-years` | International career seasons | 0-255 |

### Young Talents

List players aged ≤ 21, sorted by total skill descending. ★ marks players available on the market.

```
python3 pm_cli.py young-talents Save1_PM.adf --save pm1.sav
```

Show only players you can actually sign right now:
```
python3 pm_cli.py young-talents Save1_PM.adf --save pm1.sav --market-only
```

Raise the age cutoff:
```
python3 pm_cli.py young-talents Save1_PM.adf --save pm1.sav --max-age 23
```

With player names (requires game disk ADF):
```
python3 pm_cli.py young-talents Save1_PM.adf --save pm1.sav \
    --game-adf PlayerManagerITA.adf
```

### Top 11

Select the best XI of the championship in a chosen formation. Output is grouped by position
(Goalkeeper → Defenders → Midfielders → Forwards) and players are sorted by total skill
within each group. ★ marks players available on the market.

```
python3 pm_cli.py best-xi Save1_PM.adf --save pm1.sav
```

Pick a different formation:
```
python3 pm_cli.py best-xi Save1_PM.adf --save pm1.sav --formation 4-3-3
python3 pm_cli.py best-xi Save1_PM.adf --save pm1.sav --formation 3-5-2
```

Cap the number of players per team (free agents are exempt from the cap):
```
python3 pm_cli.py best-xi Save1_PM.adf --save pm1.sav --max-per-team 2
```

Build companion XIs from a filtered pool:
```
python3 pm_cli.py best-xi Save1_PM.adf --save pm1.sav --filter young        # ≤21
python3 pm_cli.py best-xi Save1_PM.adf --save pm1.sav --filter veteran      # ≥30
python3 pm_cli.py best-xi Save1_PM.adf --save pm1.sav --filter free-agent   # only 0xFF
python3 pm_cli.py best-xi Save1_PM.adf --save pm1.sav --filter market       # purchasable
```

With player names:
```
python3 pm_cli.py best-xi Save1_PM.adf --save pm1.sav \
    --game-adf PlayerManagerITA.adf
```

### Championship Highlights

Top scorers for the current season, grouped by division. ★ marks players available on the market.

```
python3 pm_cli.py highlights Save1_PM.adf --save pm1.sav
```

Show only purchasable players:
```
python3 pm_cli.py highlights Save1_PM.adf --save pm1.sav --market-only
```

With player names:
```
python3 pm_cli.py highlights Save1_PM.adf --save pm1.sav \
    --game-adf PlayerManagerITA.adf
```

---

## MiSTer FPGA Workflow

1. Copy the save disk ADF from the MiSTer SD card to your Mac/PC
2. **Make a backup copy before editing** — keep the original untouched
3. Optionally copy the game disk ADF too (for player names)
4. Edit players with PMSaveDiskTool v2 (GUI or CLI) on the copy
5. Copy the modified save disk ADF back to the SD card
6. Load it in the Minimig core as a second floppy (DF1)

---

## Technical Notes

### Compatibility with PMSaveDiskTool v1.2

This tool is byte-for-byte compatible with the original **PMSaveDiskTool v1.2** by
UltimateBinary. The save disk format, player record layout, and all field names match the
original exactly. The test suite verifies round-trip integrity: reading and writing an ADF
without changes produces an identical file.

### Save disk layout

The save disk is a standard 880 KB Amiga DD floppy (901120 bytes) using a custom file
table — not a standard AmigaDOS filesystem. The file table sits at byte offset 0x400
(block 2) with 16-byte entries:

```
[0:12]  filename (null-padded ASCII)
[12:14] offset (big-endian uint16 × 32 = byte offset in image)
[14:16] size (big-endian uint16, bytes)
```

Files on disk: `data.disk` (marker), `PM1.nam` (44 team names × 20 bytes), `start.dat`
(initial save state), `pm1.sav`–`pm7.sav` (save slots), and several `.tac` tactical files.

### Player database

Each save slot (pm1.sav, 4408 bytes = 44 teams × 100 bytes) is followed immediately in the
ADF image by the player database: a 2-byte big-endian header, then 1536 player records of
42 bytes each. Fields documented by UltimateBinary:

| Offset | Field |
|--------|-------|
| +00-03 | RNG Seed (4-byte BE longword) |
| +04 | Age |
| +05 | Position (1=GK, 2=DEF, 3=MID, 4=FWD) |
| +06 | Division (0-3) |
| +07 | Team index (0xFF = free agent) |
| +08 | Height (cm) |
| +09 | Weight (kg) |
| +0A-13 | 10 skill attributes (0-200) |
| +14 | Reserved |
| +15-1A | Status fields (injury, disciplinary, morale, value, weeks-since-transfer, mystery3 where bit 0x80 = on transfer list) |
| +1B-22 | Season statistics (injuries, display points, goals, matches) |
| +23-29 | Career fields (div years, international, contract) |

### Player name generation

Player names are procedurally generated by the game from the 4-byte RNG seed. The surname
table (245 names) is stored in the DEFAJAM-packed `2507` executable on the game
disk, at offset `$15B02` in the decompressed image. Verified compatible with the Italian
version; other language versions may use a different surname set at the same location. The hash algorithm was reverse-engineered
from the Windows PMSaveDiskTool v1.2 PE32 binary and uses a 6-byte rolling buffer with 20+
warm-up rounds to derive initials and a surname index.

### Positions

| Value | Position |
|-------|----------|
| 0 | Unset |
| 1 | Goalkeeper (GK) |
| 2 | Defender (DEF) |
| 3 | Midfielder (MID) |
| 4 | Forward (FWD) |

### Teams

The 44 teams span four divisions and are stored in `PM1.nam` (44 × 20-byte records,
null-terminated ASCII). The Italian version includes Milan, Sampdoria, Fiorentina,
Napoli, Roma, Torino, and 38 further clubs. Other language versions use different team
names but the same structure.

---

## Credits

- **PMSaveDiskTool v1.2** by **UltimateBinary** (http://www.ultimatebinary.com) —
  original Windows tool (2010). The save disk format documentation, 42-byte player record
  layout, and all field names in this project derive directly from that work.
  UltimateBinary's tool remains the definitive reference for the Player Manager save format.
- **Player Manager** by Anco Software (1990).
- **Dino Dini** (https://github.com/dndn1011) — original programmer of Player Manager.
  Without his work none of this would exist.
