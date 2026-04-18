"""In-app help text for the GUI.

Each entry is a topic keyed by window / surface. Rendered by ``HelpDialog``
in ``pm_gui.py`` — a plain ``tk.Text`` widget with a couple of tag styles
(section headers, list bullets). Keep entries terse: bullets, short lines,
facts users can act on. Deeper material belongs in ``MANUAL.md``.

Markup: lines beginning with ``# `` become section headers; lines beginning
with ``- `` become bullets; blank lines are paragraph breaks.
"""

HELP: dict[str, dict[str, str]] = {

    "main_window": {
        "title": "Player Manager Toolkit — Help",
        "body": """\
# What this window does

- Open a Player Manager save disk (ADF) and browse / edit every player in it.
- Pick a save slot, pick a view, optionally filter, and the left-hand list updates.
- Clicking a player loads the right-hand detail panel (Core / Skills / Status / Season / Career tabs) where every field is editable.
- First Save creates a sibling `.adf.bak` so the original state is always recoverable.

# SAVE

- Player Manager stores up to 7 independent save slots on one disk: `pm1.sav` … `pm7.sav`.
- Each slot is a full championship snapshot — 44 teams, 1536 player records.
- Switch slots from the dropdown; the View dropdown and player list rebuild automatically.
- `start.dat` is the game's initial-state template and is intentionally hidden from this list — it is not an editable save.
- Unsaved edits prompt to save before switching slots, opening a different ADF, or quitting.

# VIEW

The View dropdown combines regular teams with several analytical "super-views". Each changes what the list shows and, in some cases, the column headings.

## Regular team rows (0 … 43)

- Format: `NN: TEAM NAME` — pick a team to see its squad.
- ID 0 is your own team (the one you play as). IDs 1..43 are CPU teams.
- Team identity changes as teams move up and down the league — the toolkit reads names from the save itself, not a static file, so labels stay correct mid-career.
- A summary line above the list shows roster size, average age, average skill, and how many players are on the market.

## All Players

- Every real player in the database, sorted by team index.
- Useful for bulk browsing or when combined with the Filter field.

## Free Agents

- Only players whose `team_index` is 0xFF (not contracted to any team).
- All free agents are by definition "on the market" → ★ shown in the Mkt column.

## — Young Talents (≤21)

- Every player aged 21 or younger, sorted by total skill.
- Good for scouting — a highly-skilled 18-year-old is the kind of signing worth chasing.
- Market availability (★) is prominent: a young talent on the transfer list is usually the best deal on the disk.

## — Top Scorers

- Every player with 1+ goals this year, ranked by goals_this_year.
- Grouped by division in the CLI version; in the GUI it is a flat list so you can sort.
- The "Skill" column is swapped for "Goals".

## — Squad Analyst (all teams)

- One row per team instead of per player. Columns change:
  - Tm / Team / AvgAge / Size / GK·DEF·MID·FWD / AvgSkl / Mkt (players on market).
- Quickest way to spot anomalies — e.g. a team with only 2 defenders, or one whose average skill vastly outstrips its division.
- Rows here are not players; the detail panel stays on the last real player you had selected.

## — Top 11 (4-4-2) / — Top 11 (4-3-3)

- The best starting XI in the whole championship for that formation.
- Uses `SaveSlot.best_xi` — greedy pick by total skill, respecting `max_per_team` so you don't get 11 players from one club.
- Ordered GK → DEF → MID → FWD within the list.

## — Young XI (≤21)

- Same idea, filtered to players aged 21 or younger. A "future of the league" XI.

## — Free-Agent XI

- The best XI drawn entirely from the free-agent pool. If half the slots are weak, the market is thin for that position.

# Filter

- Substring match across **ID, Name, Team, Position** (case-insensitive).
- Name matches only work when a game disk is loaded (File → Open Game Disk…). Without it, Name is blank.
- Examples:
  - `mil` → every player on MILAN (or anyone whose name contains "mil").
  - `gk` → every goalkeeper.
  - `19` → every player aged 19, plus IDs containing 19.
- The `×` button clears the filter.
- Filter applies on top of the current View — so "Young Talents" + filter "gk" gives you young goalkeepers only.

# Player list columns

- **ID** — 0..1535, the record's slot in the player database. Stable across the save; used by the CLI.
- **Name** — procedurally generated from the player's RNG seed. Blank until you load the game disk ADF. Italian build is stable (245 surnames); English is BETA (183 surnames).
- **Age** — years old. 0 means a sentinel / unused slot (filtered out of most views).
- **Pos** — GK / DEF / MID / FWD. Stored as 1/2/3/4 in the record's position byte.
- **Team** — owner club. "Free Agent" when team_index is 0xFF.
- **Skill** (or **Goals** in Top Scorers) — sum of the 10 skill fields (pace, stamina, heading, etc.), 0..990.
- **Mkt** — ★ means market-available: either a free agent, or currently on the transfer list. The transfer flag lives in the high bit of `mystery3` (byte 0x1A) and matches the in-game LISTA TRASFERIMENTI screen.

# Detail panel (right side)

Header: PLAYER# / NAME / SEED — the player's identity, fixed while you edit other fields. All field labels below match the in-game English "Player Information" screen where they appear there.

## Core tab

- **Age** — years (byte 0x04).
- **Position** — 1=GK, 2=DEF (Defense), 3=MID (Midfield), 4=FWD (Forward).
- **Division** — 1..4; which league tier the player's team plays in (0 for free agents).
- **Team Index** — which team record in the save slot this player belongs to. 0 = the user's team, 1..43 = the other league teams, 0xFF = free agent. Internal field; no in-game equivalent.
- **Height (cm)** — cm, as shown on the in-game card.
- **Weight (kg)** — kg.

## Skills tab (all 0..200, higher = better)

- **Pace** — top speed.
- **Agility** — turning / acceleration / balance.
- **Stamina** — endurance over a match.
- **Resilience** — injury resistance (higher = fewer/shorter injuries).
- **Aggression** — tackling intensity. Low = calm, high = reckless. Stored **inverted** on disk (raw byte = 200 − displayed); the GUI always shows the in-game value.
- **Flair** — creative / technical flair. Not separately labelled on the in-game card but part of the record.
- **Passing** — passing accuracy (in-game Skills panel).
- **Shooting** — finishing (in-game Skills panel).
- **Tackling** — tackle success (in-game Skills panel).
- **Keeping** — goalkeeping (in-game Skills panel; only meaningful for GKs).
- Live colour bars next to each value update as you type.

## Status tab (what's true *right now*)

- **Injury Weeks** — weeks the player is unavailable **this moment**. 0 = fit; >0 = injured and ticks down as weeks pass.
- **Disciplinary** — current suspension points / cards state.
- **Morale** — numeric morale (~0..255; ~80 is neutral). The in-game card summarises this as "OK / Low / High".
- **Value** — transfer market value scalar.
- **Wks Since Transfer** — post-transfer cooldown counter (NOT a "listed for sale" flag). Internal field; no in-game label.

## Season tab (This Yr / Last Yr pairs)

- **Injuries** — how many distinct injury spells this / last season. Matches the in-game "Injuries" row in History. **Different from Status → Injury Weeks**: that is current downtime, this is the cumulative tally.
- **Dsp.Pts.** — disciplinary points accumulated. Matches the "Dsp.Pts." row.
- **Goals** — goals scored.
- **Matches** — matches played.

## Career tab

- **Div1 / Div2 / Div3 / Div4 Years** — years played in each division (in-game columns 1st / 2nd / 3rd / 4th).
- **Int Years** — years as an international (in-game column Int).
- **Contract Yrs** — remaining seasons on contract (observed 1..5).

## Apply / Revert / Save

- **Apply** commits edits to memory; **Revert** discards them. The window title shows `•` when there are unsaved edits.
- Saving the ADF (Cmd/Ctrl+S) writes to disk and creates a one-shot `.adf.bak` the first time.

# Right-click / keyboard

- Right-click a player row → **Send to Compare…** (opens the Compare Players window, pre-loaded).
- Cmd/Ctrl+P → Compare Players.
- Cmd/Ctrl+Y → jump straight to Young Talents view.
- Cmd/Ctrl+S → Save ADF.
- Cmd/Ctrl+Shift+S → Save As…
- Cmd/Ctrl+G → Open Game Disk… (for player names).

# Tips

- **Work on copies.** Always back the ADF up before editing; first save creates a `.adf.bak`, but subsequent saves do not.
- **Load the game disk.** Names are optional for editing, but mandatory for exports and Compare to be meaningful.
- **Team labels go stale on `PM1.nam` alone.** The toolkit now reads names from each save's team records — if a team's label still looks wrong, it means that save-slot record has a garbage name (English/BETA edge case); fallback is `Team N`.
- **Filter + View is the power combo.** Use the View dropdown to narrow the universe, then Filter to drill in.
- **Sentinel records.** Some slots near ID 1500+ have position/team outside the normal range; analytical views (Young Talents, Top 11, etc.) filter them out via `_is_real_player`.
- **Cmd/Ctrl+Q on macOS** routes through the same save-prompt path as the close button — you will not lose work.

# See also

- **Tools → Line-up Coach (BETA)** — picks an XI + bench under a chosen formation.
- **Tools → Byte Workbench** — reverse-engineering view of the raw 42-byte player record.
- **Tools → Career Tracker** — diff two save slots to track how players evolved.
- MANUAL.md — deep guidance for every feature (GUI and CLI).
""",
    },

    "lineup_coach": {
        "title": "Line-up Coach (BETA) — Help",
        "body": """\
# What it does

- Suggests the best starting XI for your squad under a chosen formation.
- Layers a 12-role taxonomy (GK, CB, FB, SW, DM, CM, AM, WM, POA, TGT, WNG, DLF) on top of PM's raw position byte (1=GK / 2=DEF / 3=MID / 4=FWD).
- Scores each XI with a composite: total skill + mean role fit + morale - fatigue - card-risk + FWD form.
- Picks two bench reserves: backup GK (when available) + best remaining outfielder by total skill.
- Flags reassignment candidates — players whose best-fit role is outside their nominal position.

# How to use

- Team: pick one club, or leave on "— Whole championship" for a league-wide XI.
- Formation: pick one to lock it in, or leave on "— Rank all" to see 4-4-2 / 4-3-3 / 3-5-2 scored side-by-side.
- Allow cross-position: tick to let players fill slots outside their position byte. Off by default — PM's out-of-position behaviour is unknown.
- Include injured: tick to ignore the injury filter and see the "ideal" XI even when half the squad is injured.
- Click Compute.

# Reading the results

- Formation ranking (left): composite, total skill, mean role fit. Click a row to swap the shown XI.
- Reassignment suggestions (left): players whose top role sits in a different position group. Gap = best-fit − nominal-fit.
- Recommended XI (right): ordered GK → DEF → MID → FWD with role tag, age, team, skill, fit %.
- Reserves (right, below the XI): labelled R1 / R2 — same columns as the XI.

# Tips

- BETA because PM's actual match-engine weights are not reverse-engineered. Treat output as a starting point, not the "right" answer.
- Cross-position is most useful when a team has an obvious positional shortage — e.g. only 3 defenders but a 4-4-2 tactic.
- If every formation fails to fill, tick "Include injured" first, then "Allow cross-position".
- Morale is scored 0..255 (~80 is neutral); fatigue looks at matches_this_year vs the squad mean plus stamina and injuries.

# See also

- MANUAL.md → "Line-up Coach (BETA)" (GUI section) and "suggest-xi" (CLI section).
""",
    },

    "byte_workbench": {
        "title": "Byte Workbench — Help",
        "body": """\
# What it does

- Lets you see exactly which bytes in the 42-byte player record carry which field, and mine for the unknown ones.
- Three tabs: Raw View (single-player hex / dec / bin dump with field labels), Histogram (value distribution at a byte, optionally masked to a single bit), Diff (bits that differ most between two player sets).
- The Diff tab is how the transfer-list bit (mystery3 = 0x80) was originally cracked — it ranks all 336 bits of the record by |P(bit=1|A) − P(bit=1|B)|.

# How to use

## Raw View

- Pick a player by ID. The table shows every byte with its field name from FIELD_LAYOUT and any known invariants.
- Use this to sanity-check what a field actually holds on disk (e.g. aggression is stored inverted — displayed = 200 − raw).

## Histogram

- Offset: 0..41 — the byte index in the player record.
- Mask (optional): apply a single-bit mask (e.g. 0x80 for "high bit only"). Values are masked before counting.
- Filter: restrict the player set (all / real / free-agents / transfer-listed / …). Presets match the CLI byte-stats ones.
- Read the bars: which values appear for this byte, how often. Tight distributions often mean the field is bounded or enum-like.

## Diff

- Set A vs Set B: pick two disjoint filters (e.g. "transfer-listed" vs "not-transfer-listed", or "forwards" vs "defenders").
- Run. The table ranks the top N bits by how much their probability differs between the two sets.
- Rows near 0 % = noise. Rows at ~100 % = a field that perfectly separates the two sets — those are the interesting ones.
- Click a bit to inspect it against FIELD_LAYOUT: does it line up with a known field, or is it in an unlabelled region?

# Tips

- Label updates: once a bit is cracked, add it to FIELD_LAYOUT in pm_core/player.py so both GUI and CLI pick up the name.
- Use the CLI equivalents (byte-stats, byte-diff) to script analyses over multiple saves; see MANUAL.md.
- Sentinel garbage near the end of the database fails SaveSlot._is_real_player — filtering helps keep distributions clean.
- Confirm any hypothesis by round-tripping: edit the byte, save, reload in the game (emulator), and check the visible effect.

# See also

- MANUAL.md → "Byte Workbench" (GUI section) and the byte-stats / byte-diff CLI sections.
- CLAUDE.md → the section on FIELD_LAYOUT as the single source of truth for byte labels.
""",
    },

    "tactic_editor": {
        "title": "Tactic Editor — Help",
        "body": """\
# What it does

- Edits the `.tac` tactic files stored on a Player Manager save disk.
- Each `.tac` holds 20 pitch-zone snapshots — for every zone (area1..area12, kickoff, goalkick, corners), where each shirt #2..#11 is supposed to stand. The goalkeeper (#1) is fixed by the engine and never stored.
- Drag a shirt on the pitch to change its target position for the current zone. Switching zones shows that zone's arrangement.

# How to use

- File: pick a `.tac` entry on the loaded disk. PM ships 4-2-4, 4-3-3, 4-4-2, 5-3-2 plus per-save variants (e.g. `4-2-4a.tac`).
- Zone: pick one of the 20 zones. The shirts reposition to that zone's coordinates and the area this zone covers is highlighted on the pitch.
- Drag a circle to move a shirt. The new (x, y) is committed in world coordinates on mouse release.
- Revert zone / Revert file: discard edits to the current zone or the whole file since the last save.
- Save to ADF: writes the tactic back through the normal `.bak` path (a sibling `.adf.bak` is created on first edit).

# Format notes

- 928-byte tactics include a short ASCII description (shown below the pitch). 980-byte tactics are the stock Anco/KO2 templates — no description. The trailer is preserved byte-exact on save.
- The `.tac` file does NOT encode which 11 players start a match — that lives inside the `.sav` team record and is still un-reversed.

# See also

- MANUAL.md → "show-tactics" and "edit-tactics" (CLI) for scripting.
- reference: github.com/ssenegas/tacticaleditor (the KO2 editor the format decoding cross-checked against).
""",
    },
}


def get(topic: str) -> tuple[str, str]:
    """Return (title, body) for ``topic``; raises KeyError if unknown."""
    entry = HELP[topic]
    return entry["title"], entry["body"]


class SearchHit(tuple):
    """One match of a query inside the help corpus.

    Fields: ``topic`` (key into ``HELP``), ``title`` (of that topic),
    ``line`` (full matching body line, stripped of markup prefixes so it
    reads cleanly in a results list), ``line_no`` (1-based line number
    inside the topic body — useful for ordering).
    """

    __slots__ = ()

    def __new__(cls, topic: str, title: str, line: str, line_no: int):
        return super().__new__(cls, (topic, title, line, line_no))

    @property
    def topic(self) -> str:
        return self[0]

    @property
    def title(self) -> str:
        return self[1]

    @property
    def line(self) -> str:
        return self[2]

    @property
    def line_no(self) -> int:
        return self[3]


def _strip_markup(line: str) -> str:
    """Remove the leading ``# ``, ``## ``, or ``- `` marker for display."""
    for prefix in ("## ", "# ", "- "):
        if line.startswith(prefix):
            return line[len(prefix):]
    return line


def search(query: str, *, max_hits_per_topic: int = 8) -> list[SearchHit]:
    """Case-insensitive substring search across every topic body.

    Returns one ``SearchHit`` per matching line, ordered by topic
    (insertion order of ``HELP``) then line number. Blank and empty
    queries return ``[]`` — callers should not treat that as an error.
    ``max_hits_per_topic`` caps the per-topic result count so one huge
    topic can't dominate the list.
    """
    q = query.strip().lower()
    if not q:
        return []
    hits: list[SearchHit] = []
    for topic, entry in HELP.items():
        per_topic = 0
        for i, raw in enumerate(entry["body"].splitlines(), start=1):
            if q in raw.lower():
                hits.append(SearchHit(topic, entry["title"], _strip_markup(raw), i))
                per_topic += 1
                if per_topic >= max_hits_per_topic:
                    break
    return hits
