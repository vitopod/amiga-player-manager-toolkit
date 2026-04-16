# PMSaveDiskToolkit — User Manual

## What this tool does

PMSaveDiskToolkit lets you open, inspect, and edit the save disk for the Amiga
game **Player Manager** (Anco, 1990). The save disk is a standard ADF floppy
image that holds up to seven independent save slots (pm1.sav–pm7.sav). Each
slot stores 44 team rosters and a database of up to 1536 players, each
described by a 42-byte record containing age, position, ten skill values,
career stats, and more.

Beyond editing individual players, the tool includes several analytical views
that let you scan the whole championship at once — find the best young players,
see who's scoring, pick a formation, track how players evolve between saves.

> **Always work on a copy of your save disk ADF, never on the original.**
> The tool writes changes directly to the file — there is no undo.
> Keep the original in a safe place and open only the copy.

---

## Two disks, not one

Player Manager ships on two separate floppies:

- **Save disk** — the ADF you edit here. Contains your save slots and the
  player database. No player names are stored here.
- **Game disk** — the ADF that boots the game. Contains the game executable,
  which holds the surname table used to generate player names from their
  4-byte RNG seeds.

**You need both disks open to see player names.** With only the save disk
loaded, every name column is blank — everything else works normally (editing,
analysis, export). To load the game disk:

- **GUI:** File → Open Game Disk… (Cmd/Ctrl+G), then pick `PlayerManagerITA.adf`
  (or whichever game disk you have). Names appear immediately everywhere.
- **CLI:** add `--game-adf PlayerManagerITA.adf` to any command that prints
  player details.

The status bar in the GUI always shows which game disk is loaded (or "no game
disk" if none).

---

## GUI

### Starting the GUI

```
python3 pm_gui.py
```

Then: **File → Open Save Disk…** (Cmd/Ctrl+O) and pick your save disk ADF.

### Layout

```
┌─ Menu bar ──────────────────────────────────────────────────────────┐
│  File  Edit  View  Tools  Help                                       │
├─ Toolbar ───────────────────────────────────────────────────────────┤
│  Save slot: [pm1.sav ▾]   View: [0: MILAN ▾]                        │
├─ Player list ─────────────┬─ Detail panel ──────────────────────────┤
│  ID   Name   Pos  Skill   │  Player #0                               │
│  0    ...    DEF  1195    │  ┌ Core │ Skills │ Status │ Season │ Career ┐
│  1    ...    MID  1229    │  └──────────────────────────────────────┘ │
│  ...                      │  [ Apply Changes ]  [ Revert ]            │
└───────────────────────────┴────────────────────────────────────────┘
│ Status bar                                             Game disk: ─  │
└─────────────────────────────────────────────────────────────────────┘
```

### Menu map

| Menu | Action | Shortcut |
|------|--------|----------|
| File | Open Save Disk… | Cmd/Ctrl+O |
| File | Open Game Disk… | Cmd/Ctrl+G |
| File | Open Recent ▸ | — |
| File | Save | Cmd/Ctrl+S |
| File | Save As… | Cmd/Ctrl+Shift+S |
| File | Export Players… | Cmd/Ctrl+E |
| Edit | Apply Changes | Cmd/Ctrl+Return |
| Edit | Revert Player | Esc |
| Edit | Find Player… | Cmd/Ctrl+F |
| View | Young Talents (≤21) | Cmd/Ctrl+Y |
| View | Top Scorers, Squad Analyst, Best XI ▸ | — |
| Tools | Career Tracker… | Cmd/Ctrl+T |
| Tools | Byte Workbench… | Cmd/Ctrl+B |
| Tools | Line-up Coach (BETA)… | Cmd/Ctrl+L |

On macOS **About** lives in the apple menu and **Quit** is Cmd+Q.

---

### Browsing players

Use the **View** dropdown in the toolbar to switch between:

- A specific team (e.g. **0: MILAN**) — shows that team's roster
- **All Players** — every player with age > 0
- **Free Agents** — players with no team (team index 0xFF)
- **— Young Talents (≤21)** — players aged 21 or under, sorted by skill
- **— Top Scorers** — all players sorted by goals this season, grouped by division
- **— Top 11 (4-4-2)** or **— Top 11 (4-3-3)** — best championship XI in that formation
- **— Young XI (≤21)** — best XI drawn only from under-21s
- **— Free-Agent XI** — best XI you could sign right now (free agents only)
- **— Squad Analyst (all teams)** — one row per team, composition at a glance

The **Filter** box above the list narrows the visible rows in real time as you
type — by player id, name, team, or position abbreviation (GK / DEF / MID / FWD).

Click any player row to load their full record into the detail panel on the right.

### Market availability (★)

A **★** in the Mkt column means the player is currently available to sign —
either because they are a free agent or because they appear on the in-game
LISTA TRASFERIMENTI (transfer list). The ★ appears in every view, including
Young Talents and Top Scorers, so you can quickly spot who you can actually
approach.

### Editing a player

1. Click a player in the list.
2. Use the tabs in the detail panel — **Core** (age, position, team, height,
   weight), **Skills** (the ten skill attributes), **Status** (injury, morale,
   discipline, value), **Season** (goals, matches, discipline points this/last
   year), **Career** (years in each division, international, contract).
3. Change any value.
4. Click **Apply Changes** (Cmd/Ctrl+Return) — this updates the in-memory
   image. The window title gains a **•** marker.
5. **File → Save** (Cmd/Ctrl+S) writes the changes to the ADF file on disk.

Apply and Save are two separate steps by design. You can apply changes to
several players in sequence and save once at the end.

**Revert** (Esc when the filter is not focused) discards any changes you've
made to the currently-open player since the last Apply.

### Saving and backups

- **Save** (Cmd/Ctrl+S) — overwrites the current file.
- **Save As…** (Cmd/Ctrl+Shift+S) — writes to a new file, leaving the original
  untouched.
- **Automatic `.bak`** — the very first time you save to a file, the tool
  creates `<filename>.adf.bak` next to it containing the original bytes.
  Subsequent saves never overwrite `.bak`, so you always have the first-known-
  good state even if you save multiple times.

---

### Squad Analyst

**What it shows:** A one-row-per-team breakdown of every squad in the
championship. Useful for spotting thin squads, lopsided position counts, or
unusually young/old rosters before a transfer window.

**How to use:**
Select **— Squad Analyst (all teams)** from the View dropdown. Each row shows:

| Column | Meaning |
|--------|---------|
| # | Team index |
| Team | Team name |
| Sz | Roster size |
| GK / DEF / MID / FWD | Player count per position |
| Age | Average age |
| Skill | Average total skill |
| Young | Age of the youngest player |
| Old | Age of the oldest player |
| Mkt | Players currently available on the market |

When you select a specific team from the dropdown instead, a summary line
appears above the roster:
```
17 players  ·  avg 25.2y  ·  skill 1238  ·  2 on market
```

---

### Career Tracker

**What it does:** Compares two save slots and shows you what changed — skill
gains/losses, age progression, and transfers. Useful for tracking a player's
development across a season, or for comparing two backed-up saves.

**How to open:** Tools → Career Tracker… (Cmd/Ctrl+T). A new window opens.

**How to use:**
1. Pick **Slot A** and **Slot B** from the dropdowns. By default, both come
   from the currently-open ADF (e.g. compare pm1.sav with pm2.sav on the same disk).
2. To compare against a different ADF (e.g. a backup from last month), click
   **Load side-B ADF…** and pick that file. Slot B will then pull from that
   second disk instead.
3. Tick **Team changes only** if you only care about transfers.
4. Click **Compare**.

The table shows for each changed player: id, name (if game disk is loaded),
age in A and B, skill total in A and B, the skill delta (Δ), and team in A
and B. Sorted by skill delta descending — biggest improvers at the top.

---

### Byte Workbench

**What it does:** A reverse-engineering tool for the raw 42-byte player record.
It lets you inspect the distribution of every byte and bit across the whole
player database, and find which bits discriminate between groups of players.

You don't need this for normal editing. It's for understanding what the bytes
mean — for example, this is how the LISTA TRASFERIMENTI flag was identified
(byte 0x1A bit 7 is always set for players on the transfer list, and never
set for players not on it).

**How to open:** Tools → Byte Workbench… (Cmd/Ctrl+B).

The window has three tabs:

**Raw View**
Pick a player by ID. See all 42 bytes laid out with their offset, hex/decimal/
binary value, and the field name for that byte. Useful for confirming what a
known player's bytes look like.

**Histogram**
Pick a player set (e.g. "Real players", "On transfer list", "GK"), an offset
(0x00–0x29), and optionally a bit mask. Click Compute. The table shows how
often each value appears at that offset in the chosen set.

Example: pick offset 0x1A, mask 0x80, filter "Real players" — you'll see that
roughly 25% of real players have the high bit set (they're on the transfer
list).

**Diff**
Pick two player sets — A and B — and click Compute. The tool checks every bit
in the 42-byte record and ranks them by how differently they behave between
the two sets. A delta of 100% means the bit is always set in A and never set
in B (or vice versa).

Example: set A = "On transfer list", B = "Not on transfer list". The top
result will be byte 0x1A bit 7 (mystery3 bit 0x80) at 100% delta — the
confirmed transfer-list flag. The bits below it are candidates for further
investigation.

---

### Line-up Coach (BETA)

**What it does:** Suggests which formation to play and who should start,
taking into account not just overall skill but each player's fit for a
specific role, their morale, how many games they've played (fatigue), their
disciplinary record, and for forwards their scoring form.

It also flags players who might perform better in a different role than the
one their position code suggests — for example, a midfielder whose skill
profile matches a defensive midfielder role much better than an attacking one.

**BETA label:** Player Manager's match engine was not reverse-engineered. The
scoring weights are a reasonable football-management heuristic, but they are
not calibrated against actual in-game results. Use the output as a starting
point for your own thinking, not as a definitive answer.

**How to open:** Tools → Line-up Coach (BETA)… (Cmd/Ctrl+L).

**How to use:**
1. **Team** — pick a specific team, or leave on "— Whole championship" to
   find the best XI across the entire player database.
2. **Formation** — pick one to lock it in, or leave on "— Rank all" to see
   all three formations (4-4-2, 4-3-3, 3-5-2) scored side-by-side.
3. **Allow cross-position** — tick this if you want the tool to consider
   playing a player outside their nominal position (e.g. a midfielder as a
   forward). Off by default.
4. **Include injured** — tick this to include players who currently have
   injury weeks > 0. Useful to see the "ideal" lineup even if half the squad
   is in the medical room. Off by default — teams with heavy injury lists
   will otherwise return "no formation could be filled."
5. Click **Compute**.

**Reading the results:**

Left pane — **Formation ranking**: each row shows the formation, composite
score, total skill, mean role-fit %, mean morale %, mean fatigue %. Click a
row to load that formation's XI into the right pane.

Left pane — **Reassignment suggestions**: players whose skills fit a role in
a *different* position better than any role in their current position. The
"Gap" column shows how much better the suggested role scores.

Right pane — **Recommended XI**: the starting eleven for the selected
formation. Each row shows the role tag (CB, DM, POA, etc.), player id, name,
age, team, total skill, and role-fit %.

Bottom — **Breakdown line**: mean role fit, morale, fatigue, card risk, and
forward form for the selected XI.

**The 12 roles:**

| Role | Position | Best for |
|------|----------|---------|
| GK | Goalkeeper | High keeping + agility |
| CB | Defender | Tackling, resilience, tall |
| FB | Defender | Pace, stamina — young |
| SW | Defender | Passing, flair — sweeper |
| DM | Midfielder | Tackling, stamina, aggression |
| CM | Midfielder | Stamina, passing, all-round |
| AM | Midfielder | Flair, passing, shooting |
| WM | Midfielder | Pace, agility — wide |
| POA | Forward | Shooting, agility — poacher |
| TGT | Forward | Shooting, resilience — tall target |
| WNG | Forward | Pace, flair — wide forward |
| DLF | Forward | Passing, flair — deep-lying |

---

### Exporting players

**File → Export Players…** (Cmd/Ctrl+E) exports the current view (whichever
team or analytical view is selected) to CSV or JSON. Pick a filename ending
in `.csv` or `.json` — the format follows the extension.

Each row includes all 42-byte fields plus: `position_name`, `team_name`,
`total_skill`, `is_free_agent`, `is_transfer_listed`, `is_market_available`,
and `name` (only when a game disk is loaded).

---

## CLI

All commands follow the same pattern:

```
python3 pm_cli.py <subcommand> <save_disk.adf> --save <slot> [options]
```

Run without arguments for the subcommand list:
```
python3 pm_cli.py --help
python3 pm_cli.py --version
```

**Adding player names to any command:** append `--game-adf PlayerManagerITA.adf`.
Without it, name columns are blank. Nothing else changes.

---

### list-saves — what slots are on disk

```
python3 pm_cli.py list-saves Save1_PM.adf
```

```
Save File         Offset   Size
--------------------------------
pm1.sav         0x013e20   4408
pm2.sav         0x025820   4408
pm3.sav         0x03d220   4408
pm4.sav         0x054c20   4408
pm5.sav         0x06c620   4408
pm6.sav         0x074020   4408
pm7.sav         0x07ba20   4408
```

---

### list-players — browse a roster

Show all players in a slot:
```
python3 pm_cli.py list-players Save1_PM.adf --save pm1.sav
```

Filter by team (index 0–43):
```
python3 pm_cli.py list-players Save1_PM.adf --save pm1.sav --team 0
```

Free agents only:
```
python3 pm_cli.py list-players Save1_PM.adf --save pm1.sav --free-agents
```

With player names:
```
python3 pm_cli.py list-players Save1_PM.adf --save pm1.sav --team 0 \
    --game-adf PlayerManagerITA.adf
```

---

### show-player — full record for one player

```
python3 pm_cli.py show-player Save1_PM.adf --save pm1.sav --id 42
```

Prints all fields including a text skill bar, career stats, and status bytes.

---

### edit-player — change a player's attributes

```
python3 pm_cli.py edit-player Save1_PM.adf --save pm1.sav --id 42 \
    --age 20 --pace 200 --shooting 180
```

Writes changes to the ADF in place. To write to a different file instead:
```
python3 pm_cli.py edit-player Save1_PM.adf --save pm1.sav --id 42 \
    --age 20 -o edited.adf
```

A `.bak` sibling is created the first time any file is written.

**Editable fields:**

| Flag | Field | Notes |
|------|-------|-------|
| `--age` | Age | |
| `--position` | Position | 1=GK 2=DEF 3=MID 4=FWD |
| `--division` | Division | 0–3 |
| `--team-index` | Team | 0–43, or 255 for free agent |
| `--height` | Height (cm) | |
| `--weight` | Weight (kg) | |
| `--stamina` … `--keeping` | Ten skill attributes | 0–200 each |
| `--injury-weeks` | Weeks injured | 0 = fit |
| `--morale` | Morale | 0–255 |
| `--disciplinary` | Disciplinary points | |
| `--value` | Market value | |
| `--goals-this-year` | Goals this season | |
| `--goals-last-year` | Goals last season | |
| `--matches-this-year` | Matches this season | |
| `--matches-last-year` | Matches last season | |
| `--contract-years` | Seasons remaining on contract | |
| `--div1-years` … `--div4-years` | Seasons in each division | |
| `--int-years` | International seasons | |

---

### young-talents — find the best prospects

Lists all players aged ≤21, sorted by total skill descending.
★ marks players you can actually approach (free agents or on transfer list).

```
python3 pm_cli.py young-talents Save1_PM.adf --save pm1.sav
```

Only show players you can sign right now:
```
python3 pm_cli.py young-talents Save1_PM.adf --save pm1.sav --market-only
```

Raise the age cutoff to 23:
```
python3 pm_cli.py young-talents Save1_PM.adf --save pm1.sav --max-age 23
```

With player names:
```
python3 pm_cli.py young-talents Save1_PM.adf --save pm1.sav \
    --game-adf PlayerManagerITA.adf
```

---

### highlights — top scorers by division

Shows the leading scorers for the current season, grouped by division.
★ marks available players.

```
python3 pm_cli.py highlights Save1_PM.adf --save pm1.sav
```

Available players only:
```
python3 pm_cli.py highlights Save1_PM.adf --save pm1.sav --market-only
```

---

### best-xi — best starting XI of the championship

Picks the strongest possible XI from the whole player database using a
position-only selection (best skill per position slot). Grouped by position,
sorted by skill within each group.

```
python3 pm_cli.py best-xi Save1_PM.adf --save pm1.sav
```

Pick a formation:
```
python3 pm_cli.py best-xi Save1_PM.adf --save pm1.sav --formation 4-3-3
python3 pm_cli.py best-xi Save1_PM.adf --save pm1.sav --formation 3-5-2
```

Limit selections from any single team (free agents are exempt):
```
python3 pm_cli.py best-xi Save1_PM.adf --save pm1.sav --max-per-team 2
```

Draw from a filtered pool:
```
python3 pm_cli.py best-xi Save1_PM.adf --save pm1.sav --filter young      # ≤21 only
python3 pm_cli.py best-xi Save1_PM.adf --save pm1.sav --filter free-agent # signable
python3 pm_cli.py best-xi Save1_PM.adf --save pm1.sav --filter market     # on market
```

> **Note:** `best-xi` scores purely by total skill. For a role-aware selection
> that also weighs morale, fatigue, and fit, use `suggest-xi` instead.

---

### squad-analyst — team composition at a glance

All 44 teams in one table:
```
python3 pm_cli.py squad-analyst Save1_PM.adf --save pm1.sav
```

```
  #  Team              Sz   GK  DEF  MID  FWD    Age   Skill  Young  Old   Mkt
--------------------------------------------------------------------------------
  0  MILAN             17    1    5    7    4   25.2    1238     19   31     2
  1  SAMPDORIA         16    1    5    6    4   24.8    1221     18   33     3
...
```

Drill into a single team (also shows youngest, oldest, best player):
```
python3 pm_cli.py squad-analyst Save1_PM.adf --save pm1.sav --team 0
```

---

### career-tracker — track player progress between saves

Compares two save slots and lists every player who changed, sorted by skill
delta descending. Works within the same ADF or across two different files.

Compare pm1 with pm2 on the same disk:
```
python3 pm_cli.py career-tracker Save1_PM.adf \
    --save-a pm1.sav --save-b pm2.sav
```

Compare against an older backup:
```
python3 pm_cli.py career-tracker Save1_PM.adf \
    --adf-b Save1_PM_old.adf \
    --save-a pm1.sav --save-b pm1.sav
```

Show only transfers (team changed):
```
python3 pm_cli.py career-tracker Save1_PM.adf \
    --save-a pm1.sav --save-b pm2.sav --team-changes-only
```

Sort by number of changed fields, limit output:
```
python3 pm_cli.py career-tracker Save1_PM.adf \
    --save-a pm1.sav --save-b pm2.sav \
    --sort changes --limit 20
```

With player names:
```
python3 pm_cli.py career-tracker Save1_PM.adf \
    --save-a pm1.sav --save-b pm2.sav \
    --game-adf PlayerManagerITA.adf
```

---

### export-players — dump to CSV or JSON

Export the full player database:
```
python3 pm_cli.py export-players Save1_PM.adf --save pm1.sav --format csv
```

Export to a file:
```
python3 pm_cli.py export-players Save1_PM.adf --save pm1.sav \
    --format json --output players.json
```

Export a single team with names:
```
python3 pm_cli.py export-players Save1_PM.adf --save pm1.sav \
    --team 0 --game-adf PlayerManagerITA.adf --output milan.csv
```

Each row contains all raw fields plus `position_name`, `team_name`,
`total_skill`, `is_free_agent`, `is_transfer_listed`, `is_market_available`,
and `name` (when game disk is loaded).

---

### byte-stats — inspect a single byte across the database

Shows the distribution of values at a given byte offset across a chosen
player set. Useful for confirming a byte is constant, spotting an enum,
or isolating a single bit flag.

How many real players have the transfer-list flag set?
```
python3 pm_cli.py byte-stats Save1_PM.adf --save pm1.sav \
    --offset 0x1A --mask 0x80 --filter real
```

```
Byte @ 0x1A = mystery3  filter=real (1031 players)  mask=0x80
     value    count     pct
    0 (0x00)    776   75.3%
  128 (0x80)    255   24.7%
```

Confirm the reserved byte is always zero:
```
python3 pm_cli.py byte-stats Save1_PM.adf --save pm1.sav \
    --offset 0x14 --filter real
```

Available filters: `all`, `real`, `free-agents`, `contracted`,
`transfer-listed`, `not-transfer-listed`, `gk`, `def`, `mid`, `fwd`,
`young`, `veteran`.

---

### byte-diff — find discriminating bits between two groups

Checks every bit in the 42-byte record and ranks them by how differently they
behave between two player sets. A delta of 100% means the bit perfectly
separates the two groups.

Confirm the transfer-list flag:
```
python3 pm_cli.py byte-diff Save1_PM.adf --save pm1.sav \
    --set-a transfer-listed --set-b not-transfer-listed --top 5
```

```
Bit-level diff: A=transfer-listed (255) vs B=not-transfer-listed (776)
  offset  field                    bit    P(A)    P(B)   delta
    0x1A  mystery3              7 (0x80) 100.0%   0.0%  100.0%
    0x1A  mystery3              0 (0x01)  78.0%  62.1%   15.9%
    ...
```

Explore what distinguishes goalkeepers from forwards:
```
python3 pm_cli.py byte-diff Save1_PM.adf --save pm1.sav \
    --set-a gk --set-b fwd --top 10
```

---

### suggest-xi — role-aware formation and XI (BETA)

Selects the best XI for a team or the whole championship using the **12-role
taxonomy** (see the GUI section above), and ranks all three formations
(4-4-2, 4-3-3, 3-5-2) by composite score. Also flags players whose skill
profile fits a role in a *different* position better than anything in their
current one.

**BETA:** scoring is a heuristic, not a reconstruction of PM's engine.

Best XI of the whole championship — ranks all three formations:
```
python3 pm_cli.py suggest-xi Save1_PM.adf --save pm1.sav
```

```
[BETA] Line-up Coach — whole championship  (pool size 1031)
Scoring is heuristic; not calibrated to PM's match engine.

Formation ranking (by composite score):
  4-3-3  composite  14803.5   skill 14776   fit  78.5% ...
  3-5-2  composite  14621.4   skill 14594   fit  78.6% ...
  4-4-2  composite  14588.9   skill 14561   fit  80.5% ...

Recommended XI — 4-3-3  (composite 14803.5, skill 14776)
— Goalkeeper —
  GK   #1007  27y  BOLOGNA          skill 1327  fit  80.7%
— Defenders —
  CB   # 911  28y  Free Agent       skill 1296  fit  85.0%
...
```

A specific team in a specific formation:
```
python3 pm_cli.py suggest-xi Save1_PM.adf --save pm1.sav \
    --team 0 --formation 4-3-3
```

If a team has too many injured players to field a full XI, add
`--include-injured` to see the ideal lineup regardless:
```
python3 pm_cli.py suggest-xi Save1_PM.adf --save pm1.sav \
    --team 0 --include-injured
```

Allow players to fill slots outside their nominal position (e.g. put a
midfielder at forward if needed):
```
python3 pm_cli.py suggest-xi Save1_PM.adf --save pm1.sav \
    --team 0 --allow-cross-position
```

Increase how many reassignment suggestions are shown, and lower the threshold
so smaller gaps are included:
```
python3 pm_cli.py suggest-xi Save1_PM.adf --save pm1.sav \
    --reassign-threshold 0.10 --reassign-limit 30
```

Adjust how the composite score is calculated (default weights shown):
```
python3 pm_cli.py suggest-xi Save1_PM.adf --save pm1.sav \
    --weights skill=1.0 fit=40 morale=20 fatigue=20 card_risk=15 form=15
```

With player names:
```
python3 pm_cli.py suggest-xi Save1_PM.adf --save pm1.sav \
    --game-adf PlayerManagerITA.adf
```

---

## MiSTer FPGA workflow

1. Copy `Save1_PM.adf` (and optionally `PlayerManagerITA.adf`) from the MiSTer
   SD card to your Mac/PC.
2. **Make a backup copy of the save disk before editing.**
3. Open the copy in PMSaveDiskToolkit and make your changes.
4. Save. The `.bak` sibling protects the pre-edit version.
5. Copy the modified ADF back to the SD card.
6. In the Minimig core, load the save disk as DF1 (second drive).

---

## Technical reference

### Save disk layout

The save disk is a standard 880 KB Amiga DD floppy (901120 bytes) using a
custom file table — not a standard AmigaDOS filesystem. The file table sits
at byte offset 0x400 (block 2) with 16-byte entries:

```
[0:12]  filename (null-padded ASCII)
[12:14] offset (big-endian uint16 × 32 = byte offset in image)
[14:16] size (big-endian uint16, bytes)
```

Files: `data.disk` (marker), `PM1.nam` (44 team names × 20 bytes),
`start.dat` (template — not editable), `pm1.sav`–`pm7.sav` (save slots),
several `.tac` tactical files.

### 42-byte player record

Each save slot (4408 bytes = 44 teams × 100 bytes) is immediately followed
in the ADF by the player database: a 2-byte big-endian header, then
1536 × 42-byte records.

| Offset | Field |
|--------|-------|
| +00–03 | RNG seed (4-byte BE longword) — used for name generation |
| +04 | Age |
| +05 | Position (1=GK 2=DEF 3=MID 4=FWD) |
| +06 | Division (0–3) |
| +07 | Team index (0xFF = free agent) |
| +08 | Height (cm) |
| +09 | Weight (kg) |
| +0A–13 | Ten skill attributes (0–200 each) |
| +14 | Reserved (always 0) |
| +15 | Injury weeks |
| +16 | Disciplinary points |
| +17 | Morale |
| +18 | Value |
| +19 | Weeks since last transfer (cooldown counter) |
| +1A | mystery3 — bit 0x80 = on transfer list; lower 7 bits unknown |
| +1B–22 | Season stats: injuries, discipline pts, goals, matches (this/last year) |
| +23–29 | Career: seasons in div1/2/3/4, international, contract years |
| +2A | last_byte — values 1–5 observed, meaning unknown |

### Player names

Names are not stored on the save disk. They are generated at runtime from the
4-byte RNG seed using a rolling-buffer hash. The surname table (245 names)
lives in the DEFAJAM-compressed `2507` executable on the game disk. Verified
with the Italian version; other versions likely use the same structure at the
same offset but a different surname list.

### Compatibility

PMSaveDiskToolkit is byte-for-byte compatible with PMSaveDiskTool v1.2 by
UltimateBinary. A round-trip read+write with no edits produces an identical
file. The field layout and naming conventions used here follow UltimateBinary's
original documentation.

---

## Credits

- **PMSaveDiskTool v1.2** by **UltimateBinary** (http://www.ultimatebinary.com)
  — original Windows tool. The save disk format documentation, 42-byte record
  layout, and field names used throughout this project derive from that work.
- **Player Manager** by Anco Software (1990).
- **Dino Dini** (https://github.com/dndn1011) — original programmer of Player
  Manager.
