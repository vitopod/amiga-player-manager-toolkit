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

### Menu map

| Menu | Action | Shortcut |
|------|--------|----------|
| File | Open Save Disk… | Ctrl/Cmd+O |
| File | Open Game Disk… | Ctrl/Cmd+G |
| File | Open Recent ▸ | — |
| File | Save | Ctrl/Cmd+S |
| File | Save As… | Ctrl/Cmd+Shift+S |
| File | Export Players… | Ctrl/Cmd+E |
| Edit | Apply Changes | Ctrl/Cmd+Return |
| Edit | Revert Player | Esc |
| Edit | Find Player… | Ctrl/Cmd+F |
| View | Young Talents (≤21) | Ctrl/Cmd+Y |
| View | Top Scorers, Squad Analyst, Best XI ▸ | — |
| Tools | Career Tracker… | Ctrl/Cmd+T |
| Tools | Byte Workbench… | Ctrl/Cmd+B |
| Tools | Line-up Coach (BETA)… | Ctrl/Cmd+L |

On macOS, **About** lives in the apple menu and **Quit** is Cmd+Q.

### Opening a save disk

Use **File > Open Save Disk…** (Ctrl/Cmd+O) and pick a Player Manager save
disk ADF — **open a copy, not the original**. The five most recently opened
save disks are kept under **File > Open Recent**.

### Loading player names (you need the game disk for this)

Player names are **not stored on the save disk** — they are generated from
a 4-byte RNG seed by a name table that lives inside the **game disk**. To
see any player names anywhere in the tool (roster list, Best XI, Career
Tracker, Line-up Coach, CSV/JSON export, …), you must open the game disk
in addition to the save disk:

1. **File > Open Save Disk…** (Ctrl/Cmd+O) — the ADF that contains your
   save slots (typically shipped as a separate floppy from the game).
2. **File > Open Game Disk…** (Ctrl/Cmd+G) — the Player Manager game disk
   ADF (e.g. `PlayerManagerITA.adf`).

Both disks are plain ADF images; the save disk by itself is enough to
edit every byte of every player — names just stay blank without the
game disk. The status bar's right-hand label always shows the current
game-disk state. The CLI equivalent is `--game-adf PlayerManagerITA.adf`
on every subcommand that prints player details.

### Selecting a save slot

The game supports up to 7 save slots (pm1.sav through pm7.sav). Use the **Save** dropdown
in the toolbar to switch between them.

### Browsing players

Use the **View** dropdown (toolbar) or the **View** menu to switch between
lists. The dropdown and the menu stay in sync; the menu gives keyboard
shortcuts for the views you hit most. Available entries:

- **All Players** — every player with age > 0
- **Free Agents** — unassigned players (team index 0xFF)
- **0: MILAN**, **1: SAMPDORIA**, etc. — players on a specific team
- **— Young Talents (≤21)** — players aged 21 or under, sorted by total skill descending
- **— Top Scorers** — all active players sorted by division, then goals this season descending
- **— Top 11 (4-4-2)** / **— Top 11 (4-3-3)** — best XI of the championship in that formation
- **— Young XI (≤21)** — best XI built from under-21s only
- **— Free-Agent XI** — best XI you could assemble from free agents
- **— Squad Analyst (all teams)** — per-team composition breakdown:
  roster size, GK/DEF/MID/FWD counts, average age and skill, and on-market count

Click any player in the list to see their full details in the right panel.
Squad Analyst rows are informational — selecting one does not populate the
editor. The **Filter** box above the list narrows the visible rows by id, name,
team, or position as you type.

### Market availability (★)

A **★** in the Mkt column means the player is currently purchasable — either a free agent
or listed for transfer. The column is visible in all views. Use Young Talents or Top Scorers
to quickly spot high-value targets you can actually sign.

### Editing a player

1. Select a player from the list.
2. Flip through the **Core · Skills · Status · Season · Career** tabs in
   the detail panel; fields are grouped by topic. The identity row
   (Player #, Name, Seed) stays visible above the tabs no matter which
   tab you are on.
3. Click **Apply Changes** (Ctrl/Cmd+Return) in the footer to write to the
   in-memory ADF image. **Revert** (or Esc when the filter is not focused)
   reloads the detail panel from the last applied record.
4. Use **File > Save** (Ctrl/Cmd+S) to write back to disk.

**Important:** "Apply Changes" updates the in-memory image only. You must also **Save**
to persist changes to the file on disk. The window title ends with a "•" marker
while you have unsaved edits; quitting, closing the window, or opening a
different ADF will prompt you to save first.

### Save As

Use **File > Save ADF As** to write to a new file, keeping the original unmodified.
This is the safest workflow: always keep an unedited backup of your save disk and use
**Save ADF As** to produce modified copies.

### Exporting the player database

Use **File > Export Players...** to write the current view to CSV (default) or
JSON. The file extension you pick drives the format (`.csv` or `.json`). The
output uses the same column schema as the CLI `export-players` subcommand.

### Per-team Squad Summary label

When you pick a specific team from the Team dropdown, a one-line summary is
shown above the roster — for example:

```
17 players  ·  avg 25.2y  ·  skill 1238  ·  2 on market
```

Switch to a different view (Young Talents, Free Agents, All Players, any XI,
or the all-teams Squad Analyst) and the label clears.

### Career Tracker window

Open **Tools > Career Tracker...** to diff two save slots and see which
players changed. Pick slot A and slot B from the drop-downs; by default both
slots come from the same ADF. Click **Load side-B ADF...** to pull slot B from
a different disk image (e.g. an older backup). Tick **Team changes only** to
restrict the output to transfers. The table lists player id, name (if a game
ADF is loaded), ages, total skills, skill delta, and team names for each
side, sorted by skill delta descending.

### Byte Workbench window

Open **Tools > Byte Workbench...** to inspect and experiment with the raw
42-byte player record. The tool was built to continue the reverse-engineering
work that identified `mystery3 bit 0x80` as the LISTA TRASFERIMENTI flag —
the same method, now automated across the whole database.

- **Raw View** — pick a player by ID and see all 42 bytes side-by-side with
  their field name, hex/dec/bin values, and any known invariants (e.g.
  `reserved` always 0, `mystery3` bit 7 = transfer-listed).
- **Histogram** — choose a preset set of players (real / free agents /
  transfer-listed / GK / young / …), an offset, and an optional mask.
  The tab shows the distribution of values for that byte, which makes it
  obvious when a byte is constant (unidentified field always 0), skewed
  (e.g. `last_byte` heavily favours 2 and 3), or discrete (known enums).
- **Diff** — pick two preset sets for A and B. The tool computes
  `P(bit=1|A)` and `P(bit=1|B)` for every bit in the record and lists
  the top N by absolute difference. Splitting the DB on
  "On transfer list" vs "Not on transfer list" puts `mystery3 bit 7` at
  100% delta — a sanity anchor for the already-known bit — and reveals
  which other bits co-vary with transfer-listing.

Both the Histogram and Diff tabs also have CLI equivalents (`byte-stats`
and `byte-diff`) if you prefer pipeline-friendly output.

### Line-up Coach (BETA) window

Open **Tools > Line-up Coach (BETA)…** (Ctrl/Cmd+L). The coach suggests
a starting XI — for a single team or for the whole championship — by
scoring every (player, role) pair against a 12-role taxonomy, then
assembling the best XI in each of the three supported formations
(4-4-2 / 4-3-3 / 3-5-2) and ranking them by a composite of **skill**,
**role fit**, **morale**, **fatigue**, **card-risk**, and **form**.
The same run also flags players whose best-fit role lies **outside**
their nominal position — useful for spotting a defender who would be
a better attacking midfielder, or similar.

- **Team** — pick a single team or leave on "— Whole championship" to
  build the best XI of the entire DB.
- **Formation** — force a specific formation, or leave on "— Rank all"
  to see the three options scored side-by-side.
- **Allow cross-position** — let players fill slots outside their
  nominal position. Useful when the chosen pool is thin in one area.
- **Include injured** — include players with active injury weeks in
  the candidate pool. Without this flag, a heavily-injured team may
  return "No formation could be filled".

Left pane lists the formation ranking (click a row to load its XI into
the right pane) and the reassignment suggestions. Right pane shows the
XI with the role tag, player, age, team, skill and fit percentage.
Under it, a one-liner breakdown summarises the six composite components.

**BETA caveat.** The scoring is a modern football-management heuristic
on top of the 10 skill fields Player Manager stores. PM's actual match
engine weights are **not** reverse-engineered. Treat the output as
"suggested," not "optimal" — the weights are starting points, not
ground truth. The CLI equivalent is `pm_cli.py suggest-xi`.

### Automatic `.bak` on first write

The first time the GUI writes back to a loaded ADF it creates a sibling
`<file>.adf.bak` containing the pre-edit bytes. Subsequent writes reuse the
existing backup — the original first-known-good state is always recoverable
without being silently overwritten later. The CLI `edit-player` subcommand
follows the same rule.

---

## CLI Usage

All CLI commands take the save disk ADF path as the first argument.
Run `python3 pm_cli.py --version` to print the tool version, or
`python3 pm_cli.py --help` for the list of subcommands. The CLI can also be
invoked as a module: `python3 -m PMSaveDiskTool_v2.pm_cli …` (from the repo
root) or `python3 -m pm_core` to launch the GUI.

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

`best-xi` also takes `--market-only` for the same effect on the starting XI.

### Squad Analyst

Per-team composition breakdown. Without `--team`, prints a one-row-per-team
table covering all 44 clubs: roster size, position counts (GK/DEF/MID/FWD),
average age and skill, youngest age, and number of players available on the
market. With `--team N`, drills into a single team and prints the youngest,
oldest, and highest-skill players with their ids.

```
python3 pm_cli.py squad-analyst Save1_PM.adf --save pm1.sav
python3 pm_cli.py squad-analyst Save1_PM.adf --save pm1.sav --team 0
```

### Career Tracker

Compare two save slots and surface per-player skill, age, and team changes. The
two slots can be on the same ADF (e.g. pm1 vs pm2) or on different ADFs via
`--adf-b`.

```
python3 pm_cli.py career-tracker Save1_PM.adf \
    --save-a pm1.sav --save-b pm2.sav
```

Sort and limit:
```
python3 pm_cli.py career-tracker Save1_PM.adf \
    --save-a pm1.sav --save-b pm2.sav \
    --sort skill --limit 20
```

Compare across ADFs (e.g. an older backup vs. the current disk):
```
python3 pm_cli.py career-tracker Save1_PM.adf \
    --adf-b Save1_PM_backup.adf \
    --save-a pm1.sav --save-b pm1.sav
```

Show only players whose team changed:
```
python3 pm_cli.py career-tracker Save1_PM.adf \
    --save-a pm1.sav --save-b pm2.sav --team-changes-only
```

### Export Players

Dump the player database as CSV (default) or JSON, with the same filters as
`list-players`. Use `--output` to write to a file; otherwise the data is
written to stdout.

```
python3 pm_cli.py export-players Save1_PM.adf --save pm1.sav --format csv
python3 pm_cli.py export-players Save1_PM.adf --save pm1.sav \
    --format json --output players.json
python3 pm_cli.py export-players Save1_PM.adf --save pm1.sav \
    --team 0 --game-adf PlayerManagerITA.adf --output milan.csv
```

Each row includes the raw 42-byte fields plus synthetic conveniences:
`position_name`, `team_name`, `total_skill`, `is_free_agent`,
`is_transfer_listed`, `is_market_available`, and `name` (when a game ADF is
supplied).

### Byte Stats

Histogram a single byte (or bit) at a chosen offset across a preset player
set. Useful for confirming invariants (e.g. `reserved == 0`) and spotting
skewed / enum-looking distributions.

```
# Verify the reserved byte is always zero across real players
python3 pm_cli.py byte-stats Save1_PM.adf --save pm1.sav \
    --offset 0x14 --filter real

# Isolate a single bit: how many real players have the transfer-list flag set?
python3 pm_cli.py byte-stats Save1_PM.adf --save pm1.sav \
    --offset 0x1A --mask 0x80 --filter real
```

Preset filters: `all`, `real`, `free-agents`, `contracted`, `transfer-listed`,
`not-transfer-listed`, `gk`, `def`, `mid`, `fwd`, `young`, `veteran`.

### Byte Diff

Rank the bits whose probability of being set differs most between two
preset player sets. Automates the method used to identify `mystery3`
bit 0x80 — split the DB on a known property and see which bits light up.

```
# Anchor: splitting on transfer-listed puts mystery3 bit 7 at 100% delta
python3 pm_cli.py byte-diff Save1_PM.adf --save pm1.sav \
    --set-a transfer-listed --set-b not-transfer-listed --top 5

# Exploratory: what bytes/bits distinguish goalkeepers from forwards?
python3 pm_cli.py byte-diff Save1_PM.adf --save pm1.sav \
    --set-a gk --set-b fwd --top 10
```

### Suggest XI (BETA)

Line-up Coach on the command line. Suggests a formation + XI from a
team or the whole championship, and flags players whose best-fit role
is outside their nominal position. Scoring is the same heuristic as the
GUI — modern football-management weights layered on PM's 10 skill
fields, **not** a reconstruction of PM's match engine. Treat output as
"suggested," not "optimal."

```
# Best XI of the whole championship, ranked over 4-4-2 / 4-3-3 / 3-5-2
python3 pm_cli.py suggest-xi Save1_PM.adf --save pm1.sav

# A specific team — add --include-injured if the squad has too many
# injuries to field the coach's default (uninjured) pool
python3 pm_cli.py suggest-xi Save1_PM.adf --save pm1.sav \
    --team 0 --include-injured --formation 4-3-3

# Weight overrides (see CHANGELOG/pm_core.lineup for default values)
python3 pm_cli.py suggest-xi Save1_PM.adf --save pm1.sav \
    --weights morale=40 fatigue=10

# Show more reassignment suggestions, or tighten the threshold
python3 pm_cli.py suggest-xi Save1_PM.adf --save pm1.sav \
    --reassign-threshold 0.10 --reassign-limit 30
```

Flags: `--team N`, `--formation {4-4-2,4-3-3,3-5-2}`,
`--allow-cross-position`, `--include-injured`,
`--weights KEY=VAL…` (keys: `skill`, `fit`, `morale`, `fatigue`,
`card_risk`, `form`), `--reassign-threshold FLOAT` (default 0.15),
`--reassign-limit N` (default 10), `--game-adf PATH`.

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
