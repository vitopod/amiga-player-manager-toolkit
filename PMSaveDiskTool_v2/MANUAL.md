# Player Manager Toolkit — User Manual

## What this tool does

Player Manager Toolkit lets you open, inspect, and edit the save disk for the Amiga
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

- **GUI:** File → Open Game Disk… (Cmd/Ctrl+G), then pick your game disk ADF
  (e.g. `PlayerManagerITA.adf`, `PlayerManager.adf`, or whatever yours is called).
  Names appear immediately everywhere.
- **CLI:** add `--game-adf <your_game_disk.adf>` to any command that prints
  player details.

The status bar in the GUI always shows which game disk is loaded (or "no game
disk" if none).

**Game disk builds.** The loader accepts any recognisable Player Manager
game disk and reports which build it detected:

- **Italian (stable)** — AmigaDOS OFS disk, `2507` executable, 245 surnames
  decompressed from the DEFAJAM-packed image. Names verified against the
  live game.
- **English (BETA)** — PM custom-file-table disk (the same 16-byte layout
  as a save disk), 183 surnames extracted by anchor-scan. Surnames and the
  reused Italian initials charsets were cross-checked against a real in-game
  roster screen — every observed name matched. What's still BETA is the
  exact seed → displayed-name mapping: individual players could in principle
  resolve to a slightly different name than the live game shows. The GUI
  shows an amber BETA pill and a one-time warning dialog; the CLI prints a
  stderr `Note:`.
- **Other PM-shaped disks** load with names blank rather than failing —
  save editing still works in full.

**Team names for English / BETA save disks.** Italian save disks carry team
names inside a file called `PM1.nam`. English (BETA) save disks don't have
that file — on its own the save shows generic `"Team 0".."Team 43"`
placeholders. When an English game disk is loaded, the toolkit extracts
real team names from `start.dat` on the game disk (CHELSEA, LIVERPOOL,
TOTTENHAM, …) and swaps them in everywhere — roster view, Squad Analyst,
Best XI, Career Tracker, CSV/JSON export, Line-up Coach. One slot is
reserved/unused on the English disk and stays a placeholder. Italian saves
are unaffected: `PM1.nam` still wins.

---

## Upgrading from a previous version

Player Manager Toolkit is distributed as a folder of Python files — no
installer, no pip package. Upgrading means replacing the folder.

**If you cloned with git:**

```
git pull                 # latest on main
git checkout v2.4.6      # or any tagged release
```

**If you downloaded a release zip:**

1. Grab the newest zip from
   <https://github.com/vitopod/amiga-player-manager-toolkit/releases>.
2. Unpack it and overwrite the previous folder.

**What survives an upgrade.** Your recent-files list and the update-check
preference live in `~/.pmsavedisktool/`, outside the source tree. They are
untouched by replacing the folder. Save disks themselves are
byte-compatible across every release of the toolkit — no migration is
ever needed — but keep working on copies regardless.

**Finding out which version you have.** `Help → About…` in the GUI, or
`python3 pm_cli.py --version` from the command line. In-app,
`Help → Check for Updates…` compares your version against the latest
GitHub release and opens the releases page if a newer tag is out.
`Help → Preferences…` toggles the once-a-day background check.

**If you're on 2.2.0 or earlier, please upgrade.** Release 2.2.1 fixed a
real byte-alignment bug — matches-last-year and the career year counters
(div 1–4, Int) were all reading one byte low, and the aggression value
was displayed as `200 − actual` because it's stored inverted on disk.
2.2.2 added the manual update-check menu item; 2.2.3 added the opt-in
daily background check and the "Update available" banner next to the
title. None of these later additions change save-disk bytes.

---

## GUI

### Starting the GUI

```
python3 pm_gui.py
```

A splash screen is shown briefly on launch (click or press any key to dismiss early). Then: **File → Open Save Disk…** (Cmd/Ctrl+O) and pick your save disk ADF.

The GUI uses a game-inspired dark theme — deep navy background, amber data values, cyan accents — consistent across all windows.

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
| Tools | Compare Players… | Cmd/Ctrl+P |
| Help | Find in Help… | Cmd/Ctrl+? |
| Help | Open Manual | — |

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

### Sorting the list

Every column heading in the player list is clickable. Click **Name** and the
list sorts by family name (ascending); click again to flip to descending — the
active column shows a ▲ or ▼ arrow next to its label. The same works for
**ID**, **Age**, **Pos**, **Team**, **Skill**, **⚠**, and **Mkt**.

- **Name** sorts on the family name — the last whitespace-separated token of
  the displayed name. "S.D. Giannini" sorts under **G**, alongside
  "R. Giannini".
- **Age**, **Skill**, **ID** sort numerically. **⚠** and **Mkt** group flagged
  rows first. **Pos** and **Team** are alphabetical.
- The active sort persists across View / Filter / save-slot changes — useful
  for scanning the same shape across multiple teams or seasons without having
  to click again.

### Skill-threshold warnings (⚠)

When a player's essential skills for its position fall below 100, a **⚠**
appears in the Warn column. Essentials per position (all taken from the 9
officially-labelled skills on the in-game Player Information card):

| Position | Essential skills |
|----------|-----------------|
| GK  | keeping, agility, resilience |
| DEF | tackling, stamina, pace |
| MID | passing, stamina, tackling |
| FWD | shooting, pace, agility |

Select a flagged player and the **Status** tab shows a "Weakness" row listing
which skills tripped the threshold, e.g. `⚠ pace 85, stamina 92`. This is a
tactic-agnostic sanity check — a shallow "can this player do the basics of
its position?" warning, not a judgement on whether they're a good player. A
future release may layer a tactic-aware version on top once shirt→player
mapping is reverse-engineered from the `.sav`.

The feature can be toggled in **Help → Preferences…** → "Flag players whose
essential skills are below 100". When off, the ⚠ column stays empty and the
Status tab reads "(warnings disabled in Preferences)".

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
   In the Skills tab, a colour-coded bar next to each attribute updates live
   as you type or spin the value.
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

### Preferences

Open via **Help → Preferences…**. Settings are persisted to
`~/.pmsavedisktool/preferences.json` (outside the source tree, so they
survive upgrades).

**On launch:**

- **Show splash screen** (default on) — toggle the Amiga-style splash
  image that appears for ~3 seconds at startup.
- **Auto-open last save disk** (default off) — when enabled, the toolkit
  automatically opens the most recently-used save ADF at launch. The
  remembered path is shown dim beneath the checkbox; if the file has
  since been moved or deleted, auto-open silently does nothing.
- **Auto-open last game disk** (default off) — same idea for the game
  disk ADF used for player names.

The **last-used paths are always recorded** after a successful open,
regardless of the auto-open toggles. This means the `File → Open Save
Disk…` and `File → Open Game Disk…` dialogs seed their starting folder
from the last file you opened — always handy on a workflow where the
ADFs live in the same directory each time (e.g. MiSTer / emulator
setups).

**Warnings:**

- **Flag players whose essential skills are below 100 (⚠)** (default on) —
  the ⚠ column on the player list and the Status tab's Weakness row will
  highlight players whose position-essential skills fall below 100. See
  *Skill-threshold warnings* above for the exact skill list per position.
  Takes effect immediately — the next list refresh reflects the new value.

**Updates:**

- **Check GitHub for updates once a day** (default off, asked once on
  first launch) — when enabled, a small *Update available* banner
  appears next to the title whenever a newer release is published.
  `Help → Check for Updates…` works regardless of this toggle.

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
age, team, total skill, and role-fit %. Below the XI a short `— Reserves —`
section lists two bench substitutes: the best backup goalkeeper (where one
exists) and the best remaining outfielder by total skill. The reserve rows
use `R1 / R2` prefixes and are highlighted to stand apart from the starting
eleven.

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

### Compare Players

**What it does:** Opens a graphical window that places two players side by side —
a radar chart (10-axis spider chart) on the left and a paired skill-bar chart on
the right — so you can see at a glance who leads where.

**How to open:**

- **Right-click** any player row in the list → **Send to Compare…** (sets that
  player as Player A and opens the window if it isn't already open).
- **Tools → Compare Players…** (Cmd/Ctrl+P) — opens the window with no Player A
  pre-selected.

If the window is already open, right-clicking another player updates Player A
without closing and reopening.

**How to use:**

1. Player A is set from the right-click. It is shown in the header row (read-only).
2. Pick a **team** from the Team combo, then pick a **player** from the Player B
   combo. The charts redraw immediately.
3. Use **⇄** to swap A and B — Player A becomes B and vice versa, then the
   charts redraw.
4. The status line at the bottom shows **"A leads on N/10 skills"** (or B, or
   "Tied") based on the raw skill counts.
5. Click **Done** to close the window.

**Reading the charts:**

| Chart | What it shows |
|-------|--------------|
| Radar | Ten-spoke spider chart. Each spoke = one skill, scaled 0–200. Player A = blue; Player B = red. Both polygons are outline-only so they don't obscure each other. |
| Bars | Side-by-side horizontal bars, one row per skill. Scale 0–200 — no skill can reach the end of a full bar at the game's maximum value. The winning value for each row is highlighted brighter. |

---

### Tactic Editor

**Tools → Tactic Editor…** (Cmd/Ctrl+K) opens a window that edits the
`.tac` tactic files stored on the save disk. Each `.tac` holds 20
pitch-zone snapshots — for every zone (area1..area12, kickoff, goalkick,
corners) it records where each shirt #2..#11 should stand. The goalkeeper
(#1) is fixed by the engine and never stored.

- **File** picker lists every `.tac` on the loaded disk (PM ships
  `4-4-2.tac`, `4-3-3.tac`, `5-3-2.tac`, `4-2-4.tac` plus per-save
  variants like `4-2-4a.tac`).
- **Zone** picker cycles through the 20 zones. The shirts reposition to
  that zone's coordinates and the on-pitch region the zone covers is
  highlighted with a translucent yellow overlay.
- **Shift-click** anywhere on the pitch to jump to whichever zone the
  click lands in. Overlapping zones (corner inside `areaN`, kickoff
  inside `areaN`, …) resolve to the smallest match so the tighter zone
  wins — handy for dropping straight into corners or the kickoff spot.
- **Compare to** dropdown draws a movement overlay: a ghost ring at each
  shirt's position in a reference zone plus a dashed arrow to its
  current position. The default `(previous zone)` auto-follows the last
  zone you left, so every switch shows the delta. Pin a specific zone
  to walk through all 20 while keeping the reference fixed, or pick
  `(none)` to hide the overlay. A `movement from: <zone>` legend sits
  bottom-right whenever arrows are visible.
- **Drag** a shirt circle to move it. The new (x, y) commits in world
  coordinates on mouse release. Shirts are clamped to the pitch.
- **Revert zone** undoes edits to the current zone; **Revert file**
  rolls the whole tactic back to the on-disk version.
- **Save to ADF** writes the tactic back through the normal `.bak` path
  (a sibling `.adf.bak` is created on first edit, just like File → Save).

The pitch is rendered landscape (660×440) with a halfway line, centre
circle and both penalty/goal boxes. World coordinates themselves stay
portrait (1024×1536) — that's how PM stores them; only the display
rotates 90° CCW. This keeps the edited bytes identical to what the
engine reads.

**Description line.** Below the pitch the window shows whatever
description PM saved into the `.tac` trailer. PM stores it as
`<midfielders>-<forwards> <blurb>` with defender count implicit — so a
4-2-4 file reads `"2-4 an attacking…"` (2 mids + 4 forwards). That's
PM's own label, not a parsing quirk. Descriptions live in a fixed
~126-char slot on disk; if PM's text overflowed it was chopped
mid-word, and a trailing `…` in the editor signals that truncation.
Stock 980-byte Anco/KO2 template tactics have no description — the
line reads `No in-game description stored`.

**What's *not* in the `.tac` file.** It doesn't encode which 11 players
actually start a match. That lives inside the `.sav` team record and is
still un-reversed. So the editor reshapes the *zone geometry* a
formation uses, not the roster that plays it.

### Find in Help

**Help → Find in Help…** (Cmd/Ctrl+?) opens a search window that scans
every in-app help topic — the main window, Line-up Coach, Byte Workbench,
and any future surfaces — from a single box. Live filtering as you type;
results show **Topic** and the matching line as context.

- **Enter** opens the top hit.
- **Double-click** any row opens its topic with every match highlighted
  and the view scrolled to the first one.
- With an empty query the window lists every help topic as an index, so
  you can browse even when you don't know what term to search for.

This is the fastest way to re-find a feature whose name you almost
remember — e.g. searching "transfer" lands on the Market availability (★)
explanation without you having to open the right `?` button first.

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

> **About the filenames in these examples**
> The examples below use `Save1_PM.adf` as the save disk and
> `PlayerManagerITA.adf` as the game disk — these are the filenames from
> the developer's own setup. **Replace them with whatever your files are
> actually called.** Your save disk might be named `PM_Save.adf`,
> `MySave.adf`, or anything else; your game disk might be
> `PlayerManager.adf`, `PM_Game.adf`, etc. The tool doesn't care about
> the name — it reads the file format, not the filename.

**Adding player names to any command:** append `--game-adf <your_game_disk.adf>`.
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

By default the command also prints a `— Reserves —` section after the XI
with two bench substitutes (a backup goalkeeper, when one is available,
plus the best spare outfielder by total skill). Pass `--reserves N` to ask
for a different bench size, or `--reserves 0` to skip reserves entirely:
```
python3 pm_cli.py suggest-xi Save1_PM.adf --save pm1.sav \
    --team 0 --reserves 3
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

### show-tactics — raw dump of the `.tac` tactic files

The save disk contains a `.tac` file per formation (`4-4-2.tac`, `4-3-3.tac`,
`5-3-2.tac`, `4-2-4.tac`) plus per-save variants used by the game to store
the player's tactical selections. The format is now decoded — see
`edit-tactics` below for the editing workflow. `show-tactics` remains as
the raw-dump diagnostic for disk inspection.

Dump every tactic file on a save disk:
```
python3 pm_cli.py show-tactics Save1_PM.adf
```

Dump just one:
```
python3 pm_cli.py show-tactics Save1_PM.adf --file 4-4-2.tac
```

Diff the same tactic in two disks — the usual workflow is: make a copy of
your save disk, change the XI for one formation in the game on emulator,
copy the modified disk off, then compare to find which bytes moved:
```
python3 pm_cli.py show-tactics Save1_PM.adf --file 4-4-2.tac \
    --diff Save1_PM_AFTER.adf
```

Add `--full` to print both hex dumps in addition to the diff summary, and
`--limit N` to cap how many differing bytes are listed per file.

---

### edit-tactics — round-trip a `.tac` file through JSON

Scriptable equivalent of the GUI **Tools → Tactic Editor…**. Dumps a
`.tac` file on the loaded ADF as human-editable JSON, and writes a
JSON file back through the ADF with a sibling `.bak` created on first
edit.

The on-disk layout is:

- **800 bytes** of positional data — 20 pitch zones × 10 players ×
  `(x, y)` as big-endian `u16`. Zones: `area1..area12`, `kickoff_own`,
  `kickoff_def`, `goalkick_def`, `goalkick_own`, `corner1..corner4`.
  Shirt numbers 2..11; the goalkeeper (#1) is fixed by the engine and
  never stored.
- **Variable trailer** preserved byte-exact: 128 bytes on PM-edited
  tactics (holds a NUL-padded ASCII description) or 180 bytes on the
  stock Anco/KO2 templates.

Dump the current tactic as JSON:
```
python3 pm_cli.py edit-tactics Save1_PM.adf --file 4-2-4.tac --dump \
    > 4-2-4.json
```

Edit the JSON by hand (or in a script), then write it back — this
creates `Save1_PM.adf.bak` on first write:
```
python3 pm_cli.py edit-tactics Save1_PM.adf --file 4-2-4.tac \
    --import 4-2-4.json
```

`--output PATH` writes the result to a new ADF instead of mutating the
input in place. The command refuses to write if the imported tactic's
total size doesn't match the on-disk entry, so you can't silently
corrupt the file table.

---

## MiSTer FPGA workflow

1. Copy `Save1_PM.adf` (and optionally `PlayerManagerITA.adf`) from the MiSTer
   SD card to your Mac/PC.
2. **Make a backup copy of the save disk before editing.**
3. Open the copy in Player Manager Toolkit and make your changes.
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
| +0A–13 | Ten skill attributes (0–200 each). Aggression (+0E) is stored **inverted**: raw byte = 200 − in-game value. |
| +14 | Reserved (always 0) |
| +15 | Injury weeks |
| +16 | Disciplinary points |
| +17 | Morale |
| +18 | Value |
| +19 | Weeks since last transfer (cooldown counter) |
| +1A | mystery3 — bit 0x80 = on transfer list; lower 7 bits unknown |
| +1B | Reserved2 (0 in 1033/1035 observed real players) |
| +1C–23 | Season stats: injuries, discipline pts, goals, matches (this/last year) |
| +24–28 | Career: seasons in div1/2/3/4, international |
| +29 | Contract years remaining (1–5) |

### Player names

Names are not stored on the save disk. They are generated at runtime from the
4-byte RNG seed using a rolling-buffer hash. The surname table (245 names)
lives in the DEFAJAM-compressed `2507` executable on the game disk. Verified
with the Italian version; other versions likely use the same structure at the
same offset but a different surname list.

### Compatibility

Player Manager Toolkit is byte-for-byte compatible with PMSaveDiskTool v1.2 by
UltimateBinary. A round-trip read+write with no edits produces an identical
file. The field layout and naming conventions used here follow UltimateBinary's
original documentation.

---

## From the original game manual

The rules and mechanics below are summarised from Anco's own Amiga
docs/manual for Player Manager. They are game behaviour, not toolkit
behaviour — useful context for understanding what the bytes you're editing
actually do in-game.

### Starting position

You begin as the newly-appointed player-manager of a **third-division club**.
The manager himself is an international-class player. He plays at
international class **only** in his designated position; in any other
position he takes on the attributes of whichever player would have worn
that shirt.

### Play mode (chosen when starting a new game)

- **Play in Position** — the manager plays only in his assigned role. The
  manual calls this "the right and best way to play".
- **Play as a Team** — the manager controls whichever player is nearest the
  ball. The engine **deliberately handicaps this mode** to offset the
  versatility of a human switching between outfielders.

### Rating scale

In-game ratings use **100 as the league average**, on an absolute scale —
a player rated 400 for pace is objectively four times as fast as an
average player. On save disk the raw skill bytes live in the 0–200 range;
how that maps onto the displayed in-game rating has not been
reverse-engineered. **Exception:** in the transfer-market browser, ability
figures are shown *relative to the division average*, not on the absolute
scale — useful when scouting but not directly comparable across divisions.

### Squad and transfers

- **Maximum squad size: 24 players.**
- **Two transfer bids per week.** Bidding is ask-price / your-offer: either
  the seller lowers, or you raise. The deal closes when the numbers match;
  otherwise the seller may quit the negotiation.
- Overseas players appear in the browser tagged **INT.** under the club
  column.
- **Contract ending = FREE transfer.** If you let a contract run out
  without renewing, the player leaves for nothing. Even before expiry the
  club "is likely to get only a fraction of their valuation" for a player
  allowed to run down his deal. The manager can offer a new contract
  **once per week per player**, choosing duration but not cost. Longer
  contracts are more expensive and the lump sum comes straight out of the
  transfer budget.
- **Revalue.** The manager can set a selling price higher than the board's
  valuation (to discourage offers for a player requesting transfer) or
  lower (to shift a player who won't sell). Independent of the board's own
  valuation.
- **Transfer requests.** A player may ask to leave. The manager's response
  — ignore / persuade to withdraw / deny — **affects the player's
  performance afterwards.**
- **The board** sets the available transfer budget and may also demand
  that the manager sell players to raise cash. Ignore the board at your
  peril — your job security rests with them.

### Discipline

- **Yellow card = 4 disciplinary points.**
- **Red card = 10 points *and* an automatic 2-match suspension.**
- **10+ points accumulated** also triggers a 2-match suspension.

This matters when editing `disciplinary_points` (byte 0x16): a value of
10 or more will cause a ban at the next check.

### Training and the coach

- **Squad training** assigns each player a training position. A player
  "acquires the skills associated with that category" over time by
  training (and playing) there — this is the in-engine basis for the
  "hidden talent" suggestion in the manual: *"his talents may lie
  elsewhere. The manager may experiment by training a player in a
  different position."* Line-up Coach's Reassignment suggestions are this
  same idea, applied statically to the current skill profile.
- **Tactical training** — only **4 tactics are active in any given week**,
  and only **1 can be swapped** per week.
- **Extra training** improves performance; the manual advises against
  overuse.
- **Have a break** — a team-morale booster, available only at the start of
  the week. Blocks all activity that week except the match itself.

### The match

- **Five minutes per half.**
- **Thirteen players selected per match day** (starting XI + two subs).
- **Pitch conditions** alter physics:
  - **Normal** — baseline.
  - **Wet** — faster, further-travelling ball; increased injury risk.
  - **Soggy** — low bounce, reduced ball travel, reduced player pace and
    stamina.
  - **Hard** — more bounce, more speed, more travel.
- **Wind direction and strength** are shown before the toss; the toss
  winner picks ends.
- Tactics change only at half time or during a substitution. Substitutions
  only while the ball is out of play (or at half time).
- **Cup ties** settle by penalty shoot-out — five kicks each, then sudden
  death.

### Injuries

- **Injury Report** gives the expected absence.
- A player on **light training** after a serious injury can be picked, but
  playing him **risks aggravating the injury**. Relevant when editing
  `injury_weeks` to 0 — the in-game state machine may still treat the
  player as fragile if he was recently injured.

### Morale

The manual states outright that **morale affects both individual-player
and team performance**, tracked per-player and aggregated in the **Coach
Report**. No threshold or formula is given. This is the engine backing for
the Line-up Coach's morale weighting.

---

## Hints, Cheats and Suggestions

### Tips from Ray Earle's Game Help

*(Credit: Ray Earle's Game Help)*

- **Young player investment.** Buy a few young, cheap players and keep them in
  the squad for a whole season. Next year, their price will have increased and
  you should have no trouble selling them for a huge profit.
- **Agility is king.** Only buy players with very high agility ratings, as this
  affects all their other attributes. If agility is high (about 200), expect
  the player to become an excellent footballer, given a season or two.
- **Sponsorship trick.** Remove 8 or 9 players from your team, then after 2 or
  3 big defeats, you will receive sponsorship.

---

> **A note on what's verified.** Player Manager's match engine and AI were
> never reverse-engineered — Player Manager Toolkit can tell you what bytes a
> player record contains, but it cannot tell you exactly how the game *uses*
> those bytes during play. The tips below that touch tool-verified mechanics
> (free agents, transfer-list flag, save-file editing) are solid. Tips that
> touch engine behaviour (how agility affects growth, how value is computed,
> what morale threshold degrades performance) are best-effort received wisdom.
> Where that's the case, it's flagged inline.

---

### General strategy

**Agility first when scouting.** *(Received wisdom — Ray Earle's claim; engine
behaviour unverified.)* Ray Earle claims agility amplifies every other
attribute and drives long-term development. The PM engine wasn't
reverse-engineered, so we can't confirm the mechanism from the bytes alone,
but the tip is consistent with how the community played the game and with the
existence of a dedicated agility attribute (byte 0x10). When scanning the
Young Talents view, sort or scan by agility before overall skill — a
17-year-old with 180 agility and mediocre other stats is the kind of prospect
Ray Earle's advice points at.

**Free agents cost nothing.** *(Verified — team_index 0xFF means no
club.)* Free agents have no club to negotiate with, so the only cost is
wages. The **Free-Agent XI** view (View → — Free-Agent XI) shows the best
XI you could assemble right now at zero transfer fee. Worth checking at the
start of every season; occasionally a top-quality player has been released.
Cross-reference with the ★ column to find signable prospects.

**Use the Mkt column to find active sellers.** *(Verified — ★ = transfer-
listed OR free agent.)* In Squad Analyst, teams with a **high Mkt count** are
the ones *themselves* offering players up. That is the signal that they're
willing to deal — not squad size. A 20-player squad with 5 listed is a better
target than a 13-player squad with 0 listed; the thin-squad team is
*protecting* its players, not offloading them. Click into the team to see
exactly who's available.

**Track who is improving.** *(Verified — Career Tracker does exactly this
diff.)* After each season, compare your current save against a backup from
the previous season (Tools → Career Tracker… / Cmd/Ctrl+T). Sort by skill
delta descending. Players who gained 20+ points in a season are keepers.
Players who flatlined after two seasons of growth are candidates to sell
while their market price still reflects the peak.

**Morale matters.** *(Verified by the original manual — exact threshold not
given.)* Anco's manual states outright that morale affects individual and
team performance; the Coach Report is where the game itself reports on it.
The toolkit can't tell you where the performance cliff is, but the field is
real and worth watching. If a signed player goes cold, check the Status tab
and see whether morale has dropped; benching them briefly to break a bad run
is the folklore remedy.

**Renew contracts early.** *(Verified by the original manual.)* A player
whose contract expires without renewal leaves as a **free agent** and the
club gets nothing. Even before expiry, the manual warns the club will "only
get a fraction of their valuation" for a player allowed to run his deal
down. Use the Career tab (contract_years field) to spot anyone entering
their final season and renew before rivals swoop. Renewal comes out of your
transfer budget, so plan ahead — and you can only offer a new contract
**once per week per player**.

**Don't let the squad exceed 24.** *(Verified — hard game limit.)* Buying
when you're already at 24 requires selling first. The Squad Analyst view
shows every team's size at a glance, including your own — check before
each transfer window.

---

### Editor tips (Player Manager Toolkit)

**Fix an injury instantly.** *(Verified byte; in-engine effect expected but
untested.)* Set *Injury weeks* to 0 in the Status tab and save. The byte is
the number of weeks remaining, so zeroing it should make the player available
next match day. Useful for rescuing a season wrecked by a long-term injury.
Caveat from the original manual: a player "on light training after a
serious injury" runs the risk of aggravating it — zeroing the byte may not
zero that residual fragility if the engine tracks it elsewhere.

**Retrain a player's position.** *(Verified — Position byte is directly
editable.)* The in-game UI rarely lets you convert a player's role. The
editor lets you change the Position byte (Core tab: 1=GK, 2=DEF, 3=MID,
4=FWD). A midfielder with high agility and shooting may be more dangerous as
a forward. Open the Line-up Coach (Cmd/Ctrl+L) afterwards — the Reassignment
suggestions panel scores the new role and tells you whether the skill profile
actually fits.

**Build a youngster at peak.** *(Byte-level verified; long-term in-engine
behaviour — growth, decline, price — not reverse-engineered.)* Set skills to
200 across the Skills tab and age to 17 in Core. On disk you now have a
17-year-old at the skill ceiling. Whether the game then leaves them alone,
re-rolls them, or applies age-based decline is not something the toolkit can
tell you — try it and see. Keep a backup save.

**Find hidden free agents mid-season.** *(Verified — views re-read the ADF
whenever you open it.)* Reopening the save disk in the toolkit after any
in-game transfer window surfaces newly-released players as free agents (★)
immediately, including players the in-game transfer screen hasn't yet shown
you.

**On editing Value.** *(Field exists, but whether the game respects it is
unverified.)* The Value byte (Status tab) is writable, but the match engine
and AI may recompute value from skills/age whenever they consult it, in which
case editing it is cosmetic. Untested — don't rely on inflated values for a
quick sale until you've confirmed it sticks in your own copy of the game.

---

## Credits

- **PMSaveDiskTool v1.2** by **UltimateBinary** (http://www.ultimatebinary.com)
  — original Windows tool. The save disk format documentation, 42-byte record
  layout, and field names used throughout this project derive from that work.
- **Player Manager** by Anco Software (1990).
- **Dino Dini** (https://github.com/dndn1011) — original programmer of Player
  Manager.
- **Topaz** font — `Topaz_a1200_v1.0.ttf` in `assets/`, used for the GUI's
  retro title band, tabs, and list headers. TrueType rendition © 2009 dMG
  of Trueschool and Divine Stylers (http://www.trueschool.org), licensed
  **CC BY-NC-SA 3.0** (non-commercial). Remove the `.ttf` for commercial
  redistribution — the GUI falls back to Courier New automatically. Full
  notice in `assets/NOTICE.md`.
