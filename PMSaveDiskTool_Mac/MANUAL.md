# PMSaveDiskTool v2.0 — Mac Edition
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

The app uses a dark Amiga-inspired theme (navy background, orange and cyan accents, Menlo monospace font throughout).

```
┌─────────────────────────────────────────────────────────────┐
│ [PM] Save Disk Tool                    ⬡ GameDisk loaded    │  Title bar
├─────────────────────────────────────────────────────────────┤
│ [Open ADF] [Save] [Save As…]              DataDisk.adf      │  Toolbar
├──────────────┬──────────────────────────────────────────────┤
│ SAVE SLOTS   │ ┌─ BAYERN MUNCHEN ── [DIV 1] +4357  46 ──┐  │
│ ► START.sav  │ │                   [Become Mgr] [Apply]  │  │  Team header
│   pm1.sav    │ ├─────────────────────────────────────────┤  │
│              │ │ [Roster]  Team Info  League Stats  Hex   │  │  Tabs
│ TEAMS (44)   │ ├─────────────────────────────────────────┤  │
│ Filter…      │ │  #  ID    Player Name                   │  │
│ ▼ Division 1 │ │  0  473   Zinetti                       │  │
│  BAYERN MUN. │ │  1  637   Nava                          │  │  Tab content
│  1. FC KOLN  │ │  2   —    empty slot                    │  │
│ ▼ Division 2 │ │                                         │  │
│  BOR. DORT.  │ │ [Set Player ID] [Remove Player]  18/25  │  │
│ ► Division 3 │ │                                         │  │
│ ► Division 4 │ │                                         │  │
├──────────────┴─┴─────────────────────────────────────────┴──┤
│ Game disk: PlayerManagerITA.adf   START.sav → BAYERN MUNCHEN│  Status bar
└─────────────────────────────────────────────────────────────┘
```

**Before a file is loaded**, the right panel shows a centred empty state with "PM / Save Disk Tool" and an Open ADF button. Once a team is selected, the team header bar and tabs appear.

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

Teams are grouped by division in the sidebar — Division 1 and 2 are expanded by default, Division 3 and 4 are collapsed. Click any team name to load its data into the right panel.

Use the **Filter** box above the team list to search by name across all divisions. Typing a filter expands all groups and hides non-matching teams.

When a team is selected, the **team header bar** appears showing the team name, a coloured division badge (orange for Div 1, cyan for Div 2), team value, and budget tier. The four editing tabs appear below it.

### 4. Edit Team Data

The right panel has four tabs:

| Tab | Content |
|-----|---------|
| **Roster** | Player table with slot number, ID, and name. Double-click a row to inline-edit the player ID. Use "Set Player ID" and "Remove Player" buttons below the table. The count (e.g. "18/25") shows how many slots are filled. |
| **Team Info** | Team Name, Division, Team Value, and Budget Tier fields. |
| **League Stats** | Points, Goals, Rank A, Rank B, Flag 1, Flag 2. |
| **Hex Dump** | Read-only hex view of the raw 100-byte team record. |

Switch tabs with **Cmd+1** through **Cmd+4** (Ctrl+1–4 on Windows/Linux).

Edit fields in any tab, then click **Apply Changes** in the team header bar.

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

**Inline editing:** Double-click any roster row to edit the player ID directly in the table. Type a numeric ID and press Enter to confirm, or Escape to cancel. The player name updates immediately. You can also select a row and click "Set Player ID" or "Remove Player" below the table.

**Important:** The individual player attributes (Stamina, Pace, Agility, etc.) are stored in a per-player database on the save disk. Editing player IDs changes which player occupies a roster slot. With the game disk loaded, player names are shown alongside IDs.

> **Warning — direct ID editing does not perform a full transfer.** Each player has a `team index` byte in the player database that records which team they belong to. "Edit ID" / "Set Player ID" only rewrites the slot in the *destination* team's roster list; it does **not** remove the player from their original team's roster, and it does not update the player's own `team index` byte. This leaves the save in an inconsistent state — the same player ID can appear on two teams simultaneously.
>
> Use the **Transfer Market** window when you want to move a player between teams. It handles all three bookkeeping steps atomically: removes the ID from the source roster, writes it to the destination roster, and updates the player's `team index` byte.
>
> Direct ID editing is intended for assigning a player to an **empty slot** (overwriting an `FFFF` entry) or recovering a specific known ID that has no current team — for example, free agents or IDs you know are not rostered anywhere.

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
| **Transfer Market…** | Search, filter, and transfer players between teams |
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

Compares two save slots side-by-side. Pick Save A and Save B from the dropdowns, then click **Compare →**. Results appear in three tabs.

---

**Tab 1 — Player Transfers**

Lists every player whose team changed between Save A and Save B, sorted by name. Columns: ID, Name, Position, From team, To team, and current role-skill average (from Save B). Double-click any row to open the full Player Detail popup for that player.

---

**Tab 2 — Division & Budget**

Lists teams where the division or team value changed. Division changes show "Promoted" or "Relegated" in green or red. Only rows with at least one change are shown, sorted by division change first then by largest value delta.

---

**Tab 3 — Career Tracker**

Full player database diff — all ~1037 players compared between Save A and Save B.

**Filters (top bar):**
- **Team** — "All", "Free Agents", or a specific team (from Save B roster)
- **Position** — All / GK / DEF / MID / FWD
- **Age** — Min/Max spinboxes (16–40); leave at defaults to show all ages
- **Show only changed** — default ON; hides players with no skill, team, or position changes

**What counts as "changed":** any skill delta ≠ 0, team changed, or position changed. Age progression alone (which happens to every player each season) does not count.

**Summary bar** (above the table) shows: `Showing N of M players — X improved, Y declined, Z transferred`. Updates whenever filters change.

**Table columns:**

| Column | Content |
|--------|---------|
| Name | Player surname |
| Pos | Position in Save B; shows `DEF->MID` if changed |
| Age | Age in Save B |
| Team | Team in Save B; shows `INTER->JUVENTUS` if transferred |
| Role Δ | Role-skill average change (Save B minus Save A) |
| Avg Δ | Overall skill average change |
| Goals | Goals this year in Save B |
| Mat | Matches this year in Save B |
| Inj | Injuries this year in Save B |
| Ctr | Contract years in Save B |
| Age Grp | Age bracket: 16-20, 21-25, 26-30, 31-35, 36+ |

Click any column header to sort. Click again to reverse. Default sort: Role Δ descending (most improved first).

**Row colours:**
- Green: role skill improved by 5+
- Red: role skill declined by 5+
- Yellow: transferred between teams
- Gray: player only in Save A (removed or retired)
- Blue: player only in Save B (newly generated)

**Age–Skill Trend bar** (below the table): when "Show only changed" is on and at least 20 changed players are visible, a one-line summary shows average role delta by age bracket:

```
Age–Skill Trends (avg role Δ):  16-20: +8.2  |  21-25: +3.1  |  26-30: +0.4  |  31-35: -2.7  |  36+: -6.1
```

Values update when filters change — filtering by position shows position-specific aging curves.

Double-click any row to open the **Player Detail** popup.

---

**Player Detail popup**

Opened by double-clicking any player row in the Transfers or Career Tracker tab. Shows a scrollable table of all attributes with Save A, Save B, and delta columns. Deltas are green for improvements, red for declines. At the bottom, **Edit in Save B…** opens the Player Editor for that player.

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

#### Editing Players

Double-click any player row in Championship Highlights (or the Transfer Market) to open the **Player Editor**. This lets you modify:

- **Skills** (0–200): Stamina, Resilience, Pace, Agility, Aggression, Flair, Passing, Shooting, Tackling, Keeping — each with a slider and spinbox
- **Info**: Age, Position (1=GK, 2=DEF, 3=MID, 4=FWD), Height, Weight, Contract years, Market value
- **Career stats**: Injury weeks, injuries this/last year, goals this/last year, matches this/last year

Click **Apply to ADF** to write changes to the in-memory buffer. The "Max All Skills" button sets all 10 skills to 200.

> Changes are applied to the in-memory buffer only. Use **File → Save ADF** to write to disk. Always save to a new file first ("Save As") to keep a backup.

---

### Transfer Market…

Opens a full player database browser with search, filtering, and team transfer controls. Requires a save slot selected.

**Left panel — Player Database:**

A searchable table of all ~1037 players. Columns: Name, Position, Age, Team, Role Skill Avg, Overall Avg, Market Value, Goals, Matches. Click column headers to sort.

**Filters:**

| Filter | What it does |
|--------|-------------|
| Search | Filter by player name (substring match) |
| Position | All / GK / DEF / MID / FWD |
| Age | Min–max range (default 16–50) |
| Min skill | Only show players with role skill average above this threshold |
| Team | All / Free Agents / specific team name |

**Right panel — Team Roster:**

Select a team from the dropdown to see its current roster (up to 25 players).

**Transfer operations:**

| Button | What it does |
|--------|-------------|
| **Transfer to Team →** | Moves the selected player from the database list into the chosen team's roster. Automatically removes the player from their previous team. |
| **← Remove from Team** | Removes the selected player from the roster (becomes a free agent). |
| **Edit Player…** | Opens the Player Editor for the selected player. |

Double-clicking a player in the database list also opens the Player Editor.

**Safeguards:**
- Cannot exceed 25 players per team
- Cannot transfer a player who is already on the destination team
- All changes are written to the in-memory ADF buffer immediately. Use **File → Save ADF** to persist to disk.

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

- **Player attribute changes are save-disk only.** Edited skills and stats are written to the player database on the save disk. The game loads this database when resuming a saved game, so changes take effect on next load. However, the game may regenerate some values during gameplay.
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

The Roster tab shows player surnames in a dedicated Name column (e.g., `Zinetti`). Names are extracted from the Italian surname table embedded in the game executable (245 unique surnames). The ID-to-name mapping uses a heuristic (`player_id % 245`) — names are indicative, not guaranteed to match the in-game display.

When inline-editing a player ID, enter just the numeric ID. The name updates automatically on confirm.

### Player Names in Compare Saves

The **Compare Saves** Transfers tab shows player surnames in the Name column. The Career Tracker tab also shows surnames throughout. Names are extracted from the Italian surname table embedded in the game executable (245 unique surnames). The ID-to-name mapping uses a heuristic (`player_id % 245`) — names are indicative, not guaranteed to match the in-game display.

### Patch Composer Auto-Load

The **Patch Composer** opens with the game disk already loaded — no need to click "Open Game Disk ADF…" each time.

### DEFAJAM Decompression

The tool decompresses the game disk's DEFAJAM-packed executable entirely in Python (two-phase: backward LZ77 + RLE expansion), producing a 131,072-byte game image. This runs once at startup and takes ~1 second. The decompressed image is used for player name extraction, the disassembler, and cross-referencing the player attribute generation code.

### Title Bar and Status Bar

The **title bar** shows game disk status on the right:
- `⬡ PlayerManagerITA.adf — 245 names` (if loaded)
- `(no game disk)` (if not found)

The **status bar** at the bottom has two sections:
- Left: general status messages (file loaded, changes applied, errors)
- Right: navigation breadcrumb showing the current save slot and team (e.g., `START.sav → BAYERN MUNCHEN`)

If no game disk is found, the tool works normally without player names.

---

## Tips

**Make a backup first.** Always use File → Save ADF As… to a new file before editing. The original `.adf` is unchanged until you explicitly save.

**To give yourself unlimited money:** Set **Team Value** to `32767` (maximum positive 16-bit signed value).

**To move to Division 1:** Set **Division** to `0` for your team and re-assign other teams to fill the tier.

**To start a fresh season:** Load `start.dat`, adjust teams as desired, then save it back and rename it as one of your `.sav` slots.

**To transfer a player:** Use **Tools → Transfer Market…** — it removes the player from the source team, adds them to the destination, and updates the player's own team record in one step. Direct ID editing in the Roster tab does not do this atomically and can leave the save in an inconsistent state (same player on two teams).

---

## FAQ

**Q: I edited a player ID in the Roster tab and now the same player appears on two teams. How do I fix it?**

This happens when you assign an ID that is already rostered on another team. Direct ID editing only writes to the destination slot — it does not remove the player from their original team. To fix it: open **Transfer Market**, find the player, and use **Transfer to Team** to move them properly. Alternatively, manually set the ID back to `FFFF` in the team where the player should not be, then re-add them via Transfer Market to the intended team.

---

**Q: What is the difference between "Edit ID" / "Set Player ID" and the Transfer Market?**

"Edit ID" is a low-level slot assignment — it writes a single 16-bit value into one roster slot and nothing else. It is intended for placing a player into an empty (`FFFF`) slot when you already know their ID.

The Transfer Market performs a complete, consistent transfer: it removes the player from their current team's roster, adds them to the new team's roster, and updates the `team index` byte inside the player's own database record. Always use Transfer Market when moving a player between teams.

---

**Q: I edited a player's skills but after loading the save in the game nothing changed (or the skills reset). Why?**

The game sometimes regenerates player attributes from a stored RNG seed during gameplay. If the game re-rolls skills mid-game, your edits may be overwritten. Changes are most reliable when applied to a save that is then loaded fresh — not resumed mid-season from a point where the game has already seeded those values.

---

**Q: Player names in the Roster tab don't match what the game shows.**

Player names are looked up using a heuristic (`player_id % 245`) against the 245 surnames embedded in the Italian game executable. This mapping is approximate. The in-game display follows a different assignment (exact algorithm unknown). Use the name column for orientation only; the ID is the authoritative identifier.

---

**Q: I opened an ADF and got "no save table found". What went wrong?**

You opened the **game disk** instead of the **save disk**. The tool expects the save/data disk (FFS filesystem with a custom directory at sector 2). The game disk uses OFS and does not have this structure. Make sure you select the correct `.adf` — the save disk is the floppy you insert when the game asks you to "Insert Data Disk".

---

**Q: Points and Goals are all zero. Is the file corrupt?**

No. Points and Goals reset to zero at the start of each new season. If you loaded a save that was created at a season boundary, or if you loaded `start.dat`, all league stats will be zero — this is normal.

---

**Q: Team #43 shows "(record 43)" instead of a name and has garbled stats. Is it safe to edit?**

Team record #43 sometimes contains binary data rather than a normal team entry (observed in some save files). The tool detects this (`_name_is_binary` flag) and preserves the raw bytes unchanged when saving, so it is safe to leave it alone. Do not attempt to edit its name or stats — the tool will not let the name field be changed for this record.

---

**Q: I changed a team's Division to 0 (Div 1) but it still plays in a lower division in-game.**

Division changes only affect which league table the team appears in when the save is read by this tool. The game engine may also use internal promotion/relegation flags (Flag 1, Flag 2 in the League Stats tab) to track division placement. For best results, change the Division field **and** re-balance the other teams in the affected divisions so each division has the correct number of teams (11 per division). Setting Flag 1 and Flag 2 to 0 for the affected teams is also advisable.

---

**Q: Can I use this tool with the English or German version of the game?**

Save disk editing works with all language versions. The game disk integration (player name lookup, Patch Composer, Disassembler) targets the Italian version specifically. If you use a different language game disk, names may not resolve correctly, but save editing is unaffected.

---

**Q: I wrote a patch in the Patch Composer and now the game crashes on startup.**

The most common cause is deleting or corrupting one of the 10 copy-protection bypass patches (offsets `$002B5E`–`$00F29C`). The tool warns before deleting these. Re-open the original unmodified game disk ADF and write a fresh patch set. Always keep a backup of the game disk before writing.

---

**Q: How many extra patches can I add in the Patch Composer?**

The patch area in block 1137 has **168 bytes** available. Each byte or word patch uses 12 bytes; each longword patch uses 14 bytes. The 10 existing copy-protection patches use 124 bytes, leaving 44 bytes free — enough for approximately 3 additional byte/word patches or 2 longword patches. The space indicator in the Patch Composer shows exact remaining capacity.

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
