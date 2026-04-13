# PMSaveDiskTool — Mac Edition
### Player Manager (1990, Anco) Save Disk Editor

---

## Overview

PMSaveDiskTool for macOS lets you open, inspect, and edit Player Manager save disk ADF images. It is the Mac equivalent of UltimateBinary's Windows tool (2010).

Player Manager (Anco, 1990) stores all game progress on a separate save/data disk. Up to 11 named save slots can coexist on that disk. This tool gives you direct access to all of them.

**Supports:** English, German, Italian, and any other language version of the game.

---

## System Requirements

| Requirement | Details |
|-------------|---------|
| macOS | 10.13 or later |
| Python | 3.8+ with tkinter — use `/usr/local/bin/python3.11` (bundled with python.org installer) |
| ADF file | A Player Manager **save disk** image (901,120 bytes) |

> The save disk is a separate floppy from the game disk. It uses FFS (DOS\x01) with a custom non-AmigaDOS directory structure. Do NOT use the game disk ADF with this tool.

---

## Running the Tool

```bash
/usr/local/bin/python3.11 PMSaveDiskTool.py
```

Or, if your default Python 3 has tkinter:

```bash
python3 PMSaveDiskTool.py
```

---

## Interface Overview

```
┌─────────────────────────────────────────────────────────────┐
│  [Open ADF]  [Save]   filename.adf                          │
├──────────────────┬──────────────────────────────────────────┤
│ Save Slots       │  Team Info                               │
│ ─────────────    │  ─────────────────────────────────────── │
│ save1.sav        │  Team Name  [____________]  Division [▼] │
│ save2.sav        │  Team Value [      ]  Budget Tier [    ] │
│ save3.sav        │  [Apply Changes]  [Become Manager]       │
│ ...              │                                          │
│                  │  League Stats                            │
│ Teams            │  Points [  ]  Goals [  ]  Rank A [  ]   │
│ ─────────────    │  Rank B [  ]  Flag1 [  ]  Flag2 [  ]    │
│ #  Name    Div   │                                          │
│  0 INTER     1   │  Player IDs (up to 25 roster slots)      │
│  1 JUVENTUS  1   │  P00 [  ] P01 [  ] P02 [  ] P03 [  ]   │
│  2 ROMA      1   │  ...                                     │
│                  │                                          │
│                  │  Raw Record Hex (100 bytes)              │
│                  │  +000  00 15 00 21 ...                   │
│                  │  ...                                     │
└──────────────────┴──────────────────────────────────────────┘
│ Status bar                                                   │
└─────────────────────────────────────────────────────────────┘
```

---

## Step-by-Step Workflow

### 1. Open a Save Disk

**File → Open ADF…** (or **Cmd+O**, or the **Open ADF** button)

Select your `.adf` file. The tool reads the entire disk into memory — nothing is written to disk until you explicitly save.

The status bar shows the number of files found and whether team names were loaded from `LigaName.nam`.

> If the tool reports "no save table found", you have opened a game disk, not a save disk.

### 2. Select a Save Slot

The **Save Slots** panel lists all `.sav` files and the `start.dat` template:

| File | Description |
|------|-------------|
| `save1.sav`, `save2.sav`, … | Named save slots (game progress) |
| `start.dat [template]` | Factory defaults — the starting point for a new game |

Click a slot to load it. The **Teams** list on the left populates with all 44 teams.

### 3. Select a Team

Click any row in the **Teams** list to load that team's data into the right panel.

The **Div** column shows the team's current division (0 = Division 1, 1 = Division 2, etc.). A `?` means the division field is not a simple 0–3 value (normal in the `start.dat` template).

### 4. Edit Team Data

Change any field in the **Team Info**, **League Stats**, or **Player IDs** sections, then click **Apply Changes**.

> Changes are applied to the in-memory buffer only. Use **File → Save ADF** to write to disk.

### 5. Save

- **File → Save ADF** (Cmd+S) — overwrites the original file.
- **File → Save ADF As…** — saves to a new file (recommended for safety).
- **File → Export Save as Binary…** — dumps the raw 4408-byte save slot to a `.bin` file for external analysis.

---

## Field Reference

### Team Info

| Field | Bytes | Description |
|-------|-------|-------------|
| **Team Name** | 68–99 | ASCII name, null-terminated. Max ~30 characters. Changing this renames the team on the save disk; it does not affect the game disk's internal name table. |
| **Division** | 66–67 | 0 = Div 1 (top), 1 = Div 2, 2 = Div 3, 3 = Div 4. Controls which league the team plays in. |
| **Team Value** | 62–63 | Signed 16-bit integer. Represents the team's financial balance (positive = surplus, negative = debt). In fresh saves this correlates with division tier; during gameplay it evolves. |
| **Budget Tier** | 64–65 | Fixed baseline value proportional to division: 46 (Div 1) / 32 (Div 2) / 23 (Div 3) / 14 (Div 4). Influences spending power. |

### League Stats (bytes 0–11, six 16-bit words)

These counters reset at the start of each season.

| Field | Meaning |
|-------|---------|
| **Points** | Current season league points accumulated |
| **Goals** | Goals scored this season |
| **Rank A** | Secondary ranking value (used for table tie-breaking) |
| **Rank B** | Tertiary ranking value |
| **Flag 1** | Game status flag (0 or 1) |
| **Flag 2** | Game status flag (0–4) |

> In a saved game at season start, Points and Goals are 0.

### Player IDs (bytes 12–61, up to 25 slots)

Each slot holds a **16-bit player ID** (0–1036). These are indices into a master player database stored on the **game disk**, not the save disk.

| Value | Meaning |
|-------|---------|
| 0–1036 | Player ID — references a specific named player with fixed attributes |
| `FFFF` | Empty slot — no player assigned |

**Important:** The individual player attributes (Stamina, Pace, Agility, Heading, Ball Skills, Passing, Shooting) are stored on the game disk, keyed by player ID. Editing player IDs effectively swaps which players are on the team roster. To see what a player ID means (name, stats), you need the original game disk loaded in an Amiga emulator.

In the factory template (`start.dat`), each of the 1037 player IDs appears exactly once across all teams — every player has a unique home. The IDs form a nearly-sequential list from 0 to 1036.

---

## Tools Menu

| Menu item | What it opens |
|-----------|---------------|
| **Hex Viewer…** | Raw sector viewer for the currently loaded ADF |
| **Disk Info** | File table, filesystem type, canonical team names |
| **Patch Composer…** | Game-disk block 1137 editor — add/remove/preview 68000 patches |
| **League Tables…** | Division standings for the selected save slot |
| **Compare Saves…** | Side-by-side diff of two save slots (transfers, promotions, budgets) |
| **Championship Highlights…** | Player attribute browser — best by position, top scorers, young talents, market values, squad analyst |
| **Tactics Viewer…** | Visual formation editor for .tac files |
| **Disassembler…** | Interactive 68000 disassembler for the game image |

---

### Hex Viewer

Opens a full ADF hex viewer. You can navigate by sector number or raw byte offset, and view multiple sectors at once.

Useful for:
- Inspecting the file allocation table (sector 2)
- Viewing raw team records at known offsets
- Comparing sectors between different ADF files

### Disk Info

Opens a scrollable window showing:
- File system type (FFS = Fast File System)
- All 29 files in the save disk's custom directory (sector 2)
- The 44 canonical team names from `LigaName.nam`

---

### Patch Composer…

Edits the 68000 runtime patch block on the **game disk** ADF (block 1137). This is the block that applies byte/word/long patches to the decompressed game image in chip RAM before the game starts — used for copy-protection bypasses and game modifications.

> This tool opens a **separate game disk ADF**, not the save disk. Use it with `PlayerManagerITA.adf` or equivalent.

**Workflow:**

1. Click **Open Game Disk ADF…** and select the game disk image.
2. The tool reads block 1137 and displays all current patches in the list.
3. Modify as needed (see sections below), then click **Write to Game Disk ADF**.

**Current Patches list**

Shows every patch in the callback area as a numbered row:

| Column | Meaning |
|--------|---------|
| Offset | Byte offset in the decompressed game image (e.g. `$002B5E`) |
| Size | `B` = byte, `W` = word (2 bytes), `L` = longword (4 bytes) |
| Value | Value written at that offset |
| Description | Human label (auto-filled for known offsets) |

Select a row and click **Delete Selected Patch** to remove it. Deleting a copy-protection patch triggers a warning — removing those will cause the game to crash.

**Quick Patches**

| Control | Effect |
|---------|--------|
| Manager Age spinbox | Sets a WORD patch at `$11740`. The game displays `stored_value + 1`, so entering 18 stores 17. Click **Apply Age Patch** to add or update the patch. |

**Custom Patch**

Enter a decompressed-image offset (hex), select size, enter a value (hex), optionally add a description, then click **Add Patch**.

Accepted offset formats: `11740`, `$11740`, `0x11740`.

**Space indicator**

Shows how many of the 168 available bytes are used and how many more patches will fit. Each byte/word patch uses 12 bytes; each longword patch uses 14 bytes.

**Preview ASM**

Opens a window showing the 68000 assembly listing for the full callback — useful for verification before writing.

**Write to Game Disk ADF**

Regenerates the callback code in canonical form, recalculates the OFS block checksum, and prompts for a save path. Always saves to a new file — the original is not modified until you explicitly choose to overwrite it.

> The protected strings at the end of the block (`dos.library`, `2507`) are never touched. The credit string region is reclaimed for additional patch space.

**Known game offsets**

| Offset | Size | What |
|--------|------|------|
| `$002B5E` – `$00F29C` | BYTE | Copy-protection bypasses (10 patches by arab^Scoopex) |
| `$011740` | WORD | Manager age (stored = displayed − 1) |
| `$01608A` | BYTE | Single character in manager name |

---

### League Tables…

Opens a tabbed window showing all four division league tables for the **currently selected save slot**. Select a save slot first, then open this window.

Each tab shows one division's teams ranked by Points (descending), with Goals as a tiebreaker:

| Column | Meaning |
|--------|---------|
| # | Current rank within the division |
| Team | Team name |
| Pts | Points accumulated this season |
| GF | Goals scored this season |
| Value | Team financial balance (signed; negative = debt) |
| Zone | `▲ Promotion` (top 2) or `▼ Relegation` (bottom 2) |

Promotion rows are highlighted green; relegation rows are highlighted red.

> Points and Goals are zero at the start of a new season. The tables are most meaningful mid-season or at season end.

---

### Compare Saves…

Compares two save slots side-by-side. Opens a dialog with two drop-down menus — pick any two slots from the currently loaded disk (including `start.dat`), then click **Compare →**.

The results show three sections:

**Player Transfers**

Lists every player ID whose team assignment changed between Save A and Save B. Player IDs are globally unique across all 44 teams, so any ID that appears in a different team's roster has transferred.

```
ID  473:  INTER                     → JUVENTUS
ID  637:  JUVENTUS                  → (unassigned)
```

**Division Changes**

Lists teams whose division number changed, with a promoted/relegated label.

```
INTER               Div 2 → Div 1  (promoted)
ROMA                Div 1 → Div 2  (relegated)
```

**Team Value Changes**

Lists all teams whose financial balance changed, sorted by largest absolute change.

```
JUVENTUS            +4357 → +5100  (Δ +743)
ROMA                  -48 →   -12  (Δ  +36)
```

---

### Championship Highlights…

Opens a player attribute browser for the currently selected save slot. The game stores a full player database (42 bytes per player, ~1037 players) on the save disk immediately after each `.sav` file. This window reads that database and presents five analysis tabs.

**Requires:** A save slot selected (not `start.dat` — it has no player database).

#### Tab: Best By Position

Four sub-tabs (Goalkeepers, Defenders, Midfielders, Forwards) each showing the top 15 players ranked by **role-relevant skill average**:

| Position | Key skills used for ranking |
|----------|----------------------------|
| GK | Keeping, Agility, Resilience |
| DEF | Tackling, Stamina, Aggression, Pace |
| MID | Passing, Flair, Stamina, Agility |
| FWD | Shooting, Pace, Flair, Agility |

Each row shows the player's name, age, team, role average, overall skill average, position-specific skill values, goals, and matches.

#### Tab: Top Scorers

Four sub-tabs ranking players by:

| Sub-tab | Stat |
|---------|------|
| Goals This Year | Season goal tally |
| Goals Last Year | Previous season goals |
| Matches This Year | Games played this season |
| Display Pts This Year | The game's internal performance metric |

Only players with a non-zero stat are shown, ranked highest first.

#### Tab: Young Talents

Shows the top 30 players aged 16–22, ranked by role-relevant skill average. Useful for scouting young players with high potential. Includes contract years remaining.

#### Tab: Market Values

Shows the top 30 players by market value (a 0–255 field in the player record). Cross-references with role skill average and career stats to identify over/undervalued players.

#### Tab: Squad Analyst

Pick any team from the dropdown to see its full roster with colour-coded recommendations:

| Colour | Hint | Meaning |
|--------|------|---------|
| Green | "Young talent" | Age 22 or under with role avg 100+ |
| Green | "Star player" | Role avg 130+ |
| Green | "Renew contract!" | Star player (130+) with 1 or fewer contract years |
| Red | "Past peak" | Age 30+ with role avg under 100 |
| Red | "Below average" | Role avg under 70 |
| Yellow | "Injury prone" | 4+ injuries across this and last year |

The summary line shows squad size, average age, average skill, and total team goals.

#### Player attributes (10 skills, all 0–200 range)

| Skill | Description |
|-------|-------------|
| Stamina | Endurance over 90 minutes |
| Resilience | Recovery from tackles and fatigue |
| Pace | Sprint speed |
| Agility | Turning and close control |
| Aggression | Tackling intensity (displayed inverted by the Windows tool) |
| Flair | Creative ability |
| Passing | Pass accuracy and vision |
| Shooting | Shot power and accuracy |
| Tackling | Defensive interception ability |
| Keeping | Goalkeeping ability |

Additional fields: Height (cm), Weight (kg), Age, Injury weeks, Disciplinary, Morale, Market value, Transfer weeks, Contract years, Goals/Matches (this year and last year), Division years, International years.

---

### Tactics Viewer…

Opens a visual formation editor for `.tac` tactics files on the save disk. Requires a save disk with at least one `.tac` file loaded.

**Pitch view:** A green football pitch canvas shows 10 outfield player positions as colored, numbered dots. The goalkeeper is not included (the game engine fixes the keeper's position).

**Controls:**

| Control | What it does |
|---------|-------------|
| Tactics file dropdown | Select which `.tac` file to view/edit |
| Zone (0–9) | Select which pitch zone to display — zones represent different ball positions, from deep defense to deep attack |
| State | "With ball" (attacking positions) or "Without ball" (defensive positions) |
| Drag dots | Click and drag any player dot to reposition it on the pitch |
| Save to Disk | Writes changes back to the ADF buffer (use File → Save to persist) |

**Zone layout** (approximate, from own goal to opponent):

| Zones | Area |
|-------|------|
| 3, 4 | Deep defense, central |
| 0, 1 | Defense wings (right, left) |
| 2, 6 | Center midfield |
| 5, 9 | Attacking wings |
| 7, 8 | Attack / deep attack |

**Technical format:** Each `.tac` file is 928 bytes: 800 bytes of coordinates (10 zones × 10 outfield players × 2 states × X,Y word pairs) + 128-byte description. Some template files are 980 bytes (extra 52-byte formation icon bitmap).

---

### Disassembler…

Opens an interactive 68000 disassembler for the decompressed Player Manager game image. Requires the game disk to be auto-loaded (see Game Disk Integration).

**Navigation:**

| Control | What it does |
|---------|-------------|
| Address field | Enter a hex address (e.g., `$11740`) and press Go or Enter |
| ← Back | Return to the previous address in navigation history |
| Lines | Number of instructions to disassemble |
| Quick Navigation buttons | Jump to known regions (entry point, age offset, name table, etc.) |
| Double-click | Click any address in the disassembly to navigate there |

**Search tools:**

| Tool | What it does |
|------|-------------|
| **X-Ref** | Find all instructions in the code region that reference a given address |
| **Find (word search)** | Find all occurrences of a 16-bit word value in the code |
| **Find MUL/DIV** | Find all MULU/MULS/DIVU/DIVS instructions with a specific immediate value |

**Output format:**

```
$000000  33 FC 7F FF 00 DF F0 9A  MOVE.W #$7FFF,$00DFF09A  ; INTENA
```

Each line shows: address, raw hex bytes, disassembled mnemonic, and automatic annotations for known offsets (manager age, name table, DMA registers, team record size multipliers).

**Game image regions:**

| Address range | Content |
|---------------|---------|
| `$00000–$00076` | System init (disable DMA/IRQ, setup stack) |
| `$00078–$134D6` | Main game code (~79 KB) |
| `$134D8–$1369A` | JMP vector table (75 Amiga library redirects) |
| `$14000–$15B02` | Italian text strings |
| `$15B02–$162E6` | Player surname table (245 names) |

---

## Save Disk Format (Technical Reference)

### ADF Container

| Property | Value |
|----------|-------|
| Total size | 901,120 bytes (1,760 sectors × 512 bytes) |
| File system | FFS — `DOS\x01` signature at sector 0 |
| Directory | **Custom** non-AmigaDOS format at sector 2 |

### Custom Directory (Sector 2)

Sector 2 is a flat file allocation table. Each entry is 16 bytes:

```
Offset  Size  Field
  0      12   File name (ASCII, null-padded)
 12       2   Start address (big-endian, in 32-byte units)
 14       2   File size in bytes (big-endian)
```

Byte offset on disk = `start_field × 32`.

### Save File Layout

Each `.sav` file and `start.dat` is **4408 bytes** = 44 × 100 bytes + 8-byte trailer.

```
Offset   Size   Content
     0    100   Team record #0
   100    100   Team record #1
   ...
  4300    100   Team record #43
  4400      8   Trailer (all zeros in .sav; 0x00000001_00000007 in start.dat)
```

### Team Record (100 bytes)

```
Offset  Size  Field
  0-11   12   League stats (6 big-endian 16-bit words)
 12-61   50   Player IDs (25 big-endian 16-bit words; 0xFFFF = empty)
 62-63    2   Team value (signed big-endian 16-bit)
 64-65    2   Budget tier (unsigned big-endian 16-bit)
 66-67    2   Division 0–3 in saves; other data in start.dat
 68-99   32   Team name (null-terminated ASCII) + trailing bytes
```

### Other Files on the Save Disk

| File | Size | Description |
|------|------|-------------|
| `LigaName.nam` | 880 bytes | Canonical team names: 44 × 20-byte entries (name + null + logo data) |
| `start.dat` | 4408 bytes | Factory template — all stats zeroed, all 1037 player IDs distributed |
| `data.disk` | 10 bytes | Contains the ASCII string "data.disk\0" |
| `*.tac` | 928–980 bytes | Tactics file: 10 zones × 10 outfield players × 2 states (with/without ball) × (X,Y) word pairs = 800 bytes + 128-byte description. Some templates have a 52-byte formation icon bitmap appended. |

---

## Limitations

- **Player attributes are read-only.** The tool reads all 10 skill attributes and career stats from the player database on the save disk (see Championship Highlights). Editing player attributes is not yet supported. Player ID-to-name mapping uses a heuristic (`id % 245`) and may not match in-game names exactly.
- **Team name changes are save-disk only.** The game disk has its own name table. If you rename a team here, the game may show the old name on some screens.
- **Tactics zones are approximate.** The 10 zone names are inferred from positional analysis; the exact game-engine mapping has not been confirmed.
- **Record #43 is sometimes binary.** In some save files the last team slot contains non-ASCII data. The tool displays it as `(record 43)` and preserves the raw bytes on save.
- **Patch Composer space is fixed at 168 bytes.** Extending the block beyond 280 bytes (OFS max 488) to gain more patch slots is not yet implemented.

---

## Game Disk Integration

Place your game disk ADF in the same directory as the script (or its parent directory) and the tool **automatically loads it at startup** — no file dialog needed.

**Accepted filenames** (tried in order, first match wins):

| Filename | Version |
|----------|---------|
| `PlayerManagerITA.adf` | Italian *(tested and recommended)* |
| `PlayerManager.adf` | English / generic |
| `PlayerManagerDE.adf` | German |
| `PlayerManagerFR.adf` | French |
| `PlayerManagerSP.adf` | Spanish |

> The Patch Composer, Disassembler, and player name lookup target the Italian version specifically. Save disk editing works with all versions.

This enables:

### Player Names in Roster View

Player ID fields show the player's surname next to the numeric ID (e.g., `473 Zinetti`). Names are extracted from the Italian surname table embedded in the game executable (245 unique surnames). The ID-to-name mapping uses a heuristic (`player_id % 245`) — names are indicative, not guaranteed to match the in-game display.

When editing player IDs, enter just the numeric ID or the full `ID Name` string — the tool strips the name automatically.

### Player Names in Compare Saves

The **Compare Saves** transfer report shows player surnames alongside IDs:

```
ID  473 (Zinetti):  INTER                     → JUVENTUS
ID  637 (Nava):     JUVENTUS                  → (unassigned)
```

### Patch Composer Auto-Load

The **Patch Composer** opens with the game disk already loaded — no need to click "Open Game Disk ADF…" each time.

### DEFAJAM Decompression

The tool decompresses the game disk's DEFAJAM-packed executable entirely in Python (two-phase: backward LZ77 + RLE expansion), producing a 131,072-byte game image. This runs once at startup and takes ~1 second. The decompressed image is used for player name extraction, the disassembler, and cross-referencing the player attribute generation code.

### Status Bar

The status bar shows game disk loading status at startup:
- `Game disk loaded: PlayerManagerITA.adf — 245 player names extracted`
- `Game disk error: <reason>` (if loading fails)

If no game disk is found, the tool works normally without player names.

---

## Tips

**Make a backup first.** Always use File → Save ADF As… to a new file before editing. The original `.adf` is unchanged until you explicitly save.

**To give yourself unlimited money:** Set **Team Value** to `32767` (maximum positive 16-bit signed value).

**To move to Division 1:** Set **Division** to `0` for your team and re-assign other teams to fill the tier.

**To start a fresh season:** Load `start.dat`, adjust teams as desired, then save it back and rename it as one of your `.sav` slots.

**To transfer a player:** Find the player's ID in team A's Player IDs list, set it to `FFFF` there, then add that same ID to team B's list in an empty (`FFFF`) slot.

---

## File Locations

| Path | Description |
|------|-------------|
| `PMSaveDiskTool_Mac/PMSaveDiskTool.py` | Main application |
| `PMSaveDiskTool_Mac/MANUAL.md` | This file |
| `PMSaveDiskTool_Mac/ROADMAP.md` | Planned features |
| `PlayerManagerITA.adf` | Italian game disk (use with Patch Composer) |

---

*Reverse-engineered from ADF analysis and the Windows PMSaveDiskTool by UltimateBinary (2010).*
