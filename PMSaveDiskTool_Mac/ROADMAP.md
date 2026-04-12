# PMSaveDiskTool — Roadmap

Three features to build, in priority order. Each section covers what it does, why it matters for MiSTer workflow, what's technically verified, and what's still unknown.

---

## Feature 1: Game Disk Patch Composer

**Priority:** Highest — directly serves the MiSTer workflow.

### What it does

A new **Patches** tab in the tool that reads, displays, and composes 68000 runtime patches in the game disk's Patch block (block 1137, OFS data). Instead of hex-editing the block by hand, you use a GUI to add/remove/modify patches, preview the generated machine code, and write the result back to the game disk ADF — ready to copy to the MiSTer SD card.

### Why it matters

On MiSTer there is no debugger. Every patch attempt is: edit ADF → copy to SD → boot → check result → repeat. A wrong byte means a wasted cycle. The Patch Composer eliminates manual hex work and OFS checksum errors, cutting iteration time to seconds.

### Verified technical foundation

Everything below has been confirmed by disassembling block 1137 of `PlayerManagerITA.adf`:

**Block 1137 layout (OFS data block):**
- 24-byte OFS header (type=8, parent=1133, seq=1, data_size=280)
- Data bytes 0x000–0x04F: HUNK loader stub (opens dos.library, LoadSeg("2507"), hooks callback, jumps)
- Data bytes 0x050–0x0CB: Callback code (124 bytes) — LEA $50000,A0 then 9 patch instructions
- Data byte 0x0CC–0x0CD: `JMP (A0)` — transfers control to decompressed game
- Data bytes 0x0CE–0x117: Credit string "Cracked by StingRay/[S]carab^Scoop" + padding

**Current 9 patches (all copy-protection bypasses by arab^Scoopex):**

| # | Offset | Instruction | Effect |
|---|--------|-------------|--------|
| 1 | $2B5E | MOVE.B #$60 | BRA over protection check |
| 2 | $7330 | MOVE.B #$60 | BRA over protection check |
| 3 | $1113E | MOVE.B #$60 | BRA over protection check |
| 4 | $4A38 | MOVE.L #$4E714E71 | NOP×2 over protection call |
| 5 | $7F08 | MOVE.L #$4E714E71 | NOP×2 over protection call |
| 6 | $48B0 | MOVE.B #$60 | BRA over protection check |
| 7 | $C2D6 | MOVE.B #$60 | BRA over protection check |
| 8 | $3608 | MOVE.B #$60 | BRA over protection check |
| 9 | $70D8 | MOVE.B #$60 | BRA over protection check |
| — | $F29C | MOVE.B #$60 | BRA over protection check |

*(10 total — I miscounted earlier as 9; there are 7 BRA patches + 2 NOP patches + 1 more BRA)*

**Available patch space:**
- Credit string (74 bytes) can be reclaimed → ~6 more patch slots
- Block data can be extended from 280 → 488 bytes (OFS max) → ~17 more slots total
- Each byte patch = 12 bytes (`MOVE.L #offset,D0` + `MOVE.B #val,(A0,D0.L)`)
- Each word patch = 12 bytes (`MOVE.L` + `MOVE.W`)
- Each long patch = 14 bytes (`MOVE.L` + `MOVE.L`)

**OFS checksum rule:** Sum of all 128 longwords (512-byte block including header) must equal $00000000. After modifying data, recompute the checksum longword at block offset 16.

### GUI design

```
┌─ Patches (PlayerManagerITA.adf, Block 1137) ──────────────────────┐
│                                                                    │
│  Current Patches                                                   │
│  ┌────┬──────────┬───────────────┬────────────────────────────┐   │
│  │ #  │ Offset   │ Value         │ Description                │   │
│  ├────┼──────────┼───────────────┼────────────────────────────┤   │
│  │  1 │ $002B5E  │ BYTE $60     │ Copy-prot BRA              │   │
│  │  2 │ $007330  │ BYTE $60     │ Copy-prot BRA              │   │
│  │ ...│          │               │                            │   │
│  │ 10 │ $00F29C  │ BYTE $60     │ Copy-prot BRA              │   │
│  │ 11 │ $011740  │ WORD $0011   │ Manager age = 18           │   │
│  │ 12 │ $01608A  │ BYTE $69     │ Name: 'i' (Pozza→Pozzi)   │   │
│  └────┴──────────┴───────────────┴────────────────────────────┘   │
│                                                                    │
│  ┌─ Quick Patches ──────────────────────────────────────────────┐ │
│  │  Manager Age: [18 ▾]  (stored as WORD at $11740)            │ │
│  │  [ ] Remove copy protection  (all 10 patches above)         │ │
│  └──────────────────────────────────────────────────────────────┘ │
│                                                                    │
│  ┌─ Custom Patch ───────────────────────────────────────────────┐ │
│  │  Decompressed offset: [0x______]                             │ │
│  │  Size: (•) Byte  ( ) Word  ( ) Long                         │ │
│  │  Value: [0x____]    Description: [________________]          │ │
│  │  [Add Patch]                                                 │ │
│  └──────────────────────────────────────────────────────────────┘ │
│                                                                    │
│  Space: ████████░░░░░░░░░░ 12/17 slots used                      │
│                                                                    │
│  [Preview ASM]  [Write to Game Disk ADF]                          │
└────────────────────────────────────────────────────────────────────┘
```

**"Preview ASM"** shows the raw 68000 hex that will be written — so you can verify before committing.

**"Write to Game Disk ADF"** rewrites block 1137, recalculates the OFS checksum, and saves. The file is then ready to copy to MiSTer.

### Known offsets for quick-patch controls

| What | Decompressed offset | Size | Notes |
|------|---------------------|------|-------|
| Manager age | $11740 | WORD | displayed_age = stored + 1 |
| Manager name char | $1608A | BYTE | single character patch (e.g. 'a'→'i') |

More offsets to be discovered from the decompressed game image (see Feature 3).

### What's still unknown

- Full map of patchable game offsets (difficulty, starting money, etc.) — requires Feature 3
- Whether extending the block from 280→488 bytes requires updating the file header's size field at block 1133 (likely yes — need to verify OFS header chain)

---

## Feature 2: League Dashboard + Transfer Tracker

**Priority:** Medium — uses only save disk data, no dependencies on game disk work.

### What it does

Two additions to the existing save disk tool:

**A) Division Tables view** — a read-only panel showing all four divisions as proper ranked league tables, with promotion/relegation zones marked.

**B) Save Comparison** — pick two save slots, see what changed: player transfers, division changes, budget deltas.

### Division Tables

A toggle ("Team Editor" / "League Tables") switches the right panel to show four ranked tables:

```
 DIVISION 1 (8 teams)                    DIVISION 2 (11 teams)
 ───────────────────────────────────      ─────────────────────────────────
   # Team                 Pts  GF  Val     # Team                 Pts  GF  Val
 ▲ 1 1. FC KOLN           67  10  +4357  ▲ 1 EINTR. BRAUNSCHWEIG  23  12  +746
 ▲ 2 VfL BOCHUM           19  11  +4704    2 BORUSSIA DORTMUND    11  16   +1461
   3 SV MEPPEN             15  17  +5608    3 ...
   ...                                      ...
 ▼10 FC GUTERLOH           11  42  +4736  ▼11 ...
 ▼11 SPVGG GREUTHER FURTH   9  22  +4330

 ▲ = promotion zone (top 2)    ▼ = relegation zone (bottom 2)
```

Sorted by Points descending, then Goals for tie-breaking. Team Value shown as signed integer. Clicking a team row switches back to Team Editor with that team selected.

**Implementation:** Trivial — group `save.teams` by `team.division`, sort each group by `team.league_stats[0]` descending, render in a Treeview.

### Save Comparison

**Tools → Compare Saves…** opens a dialog to pick two slots (e.g. START.sav vs TURRICAN.sav).

The output shows three sections:

**Player Transfers:**
```
  ID  473: KOLN → BAYERN MUNCHEN
  ID  637: BAYERN MUNCHEN → (released)
  ID  816: BAYERN MUNCHEN → BORUSSIA DORTMUND
```

This works because every player ID is globally unique across all 44 teams (verified: 861 unique IDs in start.dat). For each ID present in Save A, find which team it belongs to in Save B. If different → transfer.

**Division Changes:**
```
  BAYERN MUNCHEN:  Div 3 → Div 2  (promoted)
  HAMBURGER SV:    Div 2 → Div 3  (relegated)
```

**Budget Changes:**
```
  1. FC KOLN:       +4357 → +5100  (Δ +743)
  BAYERN MUNCHEN:     +72 →  +101  (Δ  +29)
  DYNAMO DRESDEN:    -48  →   -12  (Δ  +36)
```

### What's still unknown

- The exact meaning of league stats 2–5 (labelled "Rank A", "Rank B", "Flag 1", "Flag 2"). The tie-breaking logic used by the game may depend on these. For now, sort by Points only.
- Whether the game preserves team ordering within a division across saves (it doesn't — teams get reshuffled). The comparison must match by team name, not by array index.

---

## Feature 3: DEFAJAM Decompressor + Player Database

**Priority:** Lowest (hardest) — but unlocks the most long-term capability.

### What it does

Decompresses the game disk's `2507` file (70,600 bytes, DEFAJAM-packed) entirely in Python. Scans the decompressed image for the player attribute table. Maps each of the 1,037 player IDs to their 7 attributes and (if possible) generated names. Feeds this data back into the save disk editor so player IDs display as real players.

### Why it can't be phased

On MiSTer there is no debugger. You cannot pause the CPU, dump chip RAM, or extract the decompressed image at runtime. The only way to get the decompressed data is to implement the decompressor ourselves.

There is no shortcut. WinUAE could provide a dump, but the user doesn't use WinUAE — they use MiSTer FPGA hardware.

### What's known

**DEFAJAM packer facts:**
- Created by Bandit/DEFAJAM (Amiga demo/cracking scene, late 1980s)
- Uses LZ77-style compression with bit-stream control
- The packed file is a standard AmigaDOS HUNK executable: HUNK_HEADER → HUNK_CODE (decompressor stub + packed data) → HUNK_END
- The decompressor stub is 68000 machine code (~200 instructions) that unpacks the payload into a new memory region, then builds HUNK segments from the result
- The algorithm has been reimplemented in C by various Amiga preservation projects (amigadepack, xfdmaster)

**What we know about the decompressed image:**
- Decompresses to chip RAM at $50000
- Bootstrap at $50000 copies $50056 → $5F00
- Game code runs from $5F00
- Known offsets: age display at $117E8, age value at $11740, name char at $1608A
- Total decompressed size: unknown but >$11800 bytes (>71,680 bytes) based on known offsets

**Player database estimates:**
- 1,037 players (IDs 0–1036, all unique in start.dat)
- 7 attributes per player: Stamina, Pace, Agility, Heading, Ball Skills, Passing, Shooting
- If attributes are single bytes (0–99 range): 1,037 × 7 = 7,259 bytes
- If names are inline (12–16 bytes each): add ~12–17 KB
- If names are procedural (syllable table + 2-byte mapping per player): add ~2–3 KB for syllable table + 2,074 bytes for mappings
- The Windows tool had 4 ComboBox controls for name editing → confirms syllable-based generation with 4 parts

### Transfer Market Insight

Once the player database is decoded, the tool can provide **transfer market intelligence**:

**"Available Players" panel:**
When viewing a save, the tool can compute which player IDs are NOT assigned to any team (ID exists in the master 0–1036 range but doesn't appear in any of the 44 rosters). These are the players available on the transfer market.

```
┌─ Transfer Market (156 unassigned players) ──────────────────────┐
│                                                                  │
│  Sort by: [Attribute ▾]  Filter: Pace > [70]  Shooting > [60]  │
│                                                                  │
│  ID    Name            Stm  Pac  Agi  Hea  Bal  Pas  Sho  Total│
│  ─────────────────────────────────────────────────────────────── │
│  0847  [MÜLLER K.]      82   91   75   68   80   72   88   556  │
│  0293  [SCHMIDT H.]     78   85   70   72   83   79   85   552  │
│  0614  [WEBER T.]       80   77   88   65   79   81   76   546  │
│  ...                                                             │
│                                                                  │
│  [Add to Current Team]  [Compare with Roster]                    │
└──────────────────────────────────────────────────────────────────┘
```

**"Scout Report" for your team:**
- Your weakest attribute across the roster (e.g. "Heading avg: 42 — worst in Div 1")
- Best available upgrades: "ID 847 has Heading 68, would raise your average to 51"
- "Overpriced" players: roster members whose attributes are worse than free agents at the same position

**Roster Gap Analysis:**
- Compare your 22 players' attribute averages against division opponents
- Highlight positions where you're below-average
- Suggest trade targets from the unassigned pool

### Implementation status

| Step | Status | Notes |
|------|--------|-------|
| 1. Extract HUNK structure from `2507` | **Done** | OFS file reader + HUNK parser implemented |
| 2. DEFAJAM decompressor | **Done** | Two-phase Python implementation (backward LZ77 + RLE) |
| 3. Validate decompressed image | **Done** | 131,072 bytes; age at $11740 = $001C, name char at $1608A = 'a' |
| 4. Scan for player attribute table | **Blocked** | Extensive search found no static attribute table; attributes may be procedurally generated |
| 5. Locate name table | **Done** | 245 Italian surnames at $15B02–$162E6 |
| 6. GUI integration | **Done** | Player names in roster view, Compare Saves, auto-loaded game disk, Patch Composer auto-load |

### What's been discovered

- **DEFAJAM variant**: sentinel-based 32-bit bit buffer; backward LZ77 with 256-byte Huffman LUT; $9B marker RLE
- **Decompressed image**: 131,072 bytes ($20000), loaded at $50000 in chip RAM
- **Name table**: 245 null-terminated Italian surnames at $15B02–$162E6 (not a syllable system — full surnames)
- **Name mapping**: No index table found linking player IDs (0–1036) to surname indices (0–244). Using `player_id % 245` as heuristic.

### What's still unknown

- **Player attribute database**: Despite exhaustive searching (byte/word records, multiple stride lengths, entropy analysis, A4-relative displacement mapping), no static attribute table was found. Attributes may be generated procedurally from the player ID.
- **Exact ID-to-name mapping algorithm**: The game may use a more complex function than simple modulo.
- **Transfer market mechanics**: Whether "unassigned" IDs are available on the market or controlled by a separate flag.
- **Player position data**: No position table found; positions may be implicit or runtime-computed.

### Remaining work

- **Transfer Market panel**: Can list unassigned player IDs with names, but without attributes there's no way to rank or filter by stats
- **Full offset map for Patch Composer**: Requires more reverse-engineering of the decompressed image
- **Player attribute reverse-engineering**: May require comparing German version's game disk, or running the game in WinUAE with a debugger to observe attribute loading at runtime

---

## Dependencies

```
Feature 1 (Patch Composer)  ──→  DONE
Feature 2 (League Dashboard) ──→  DONE
Feature 3 (DEFAJAM + Player DB):
    ├──→ Decompressor + name extraction:  DONE
    ├──→ Player names in roster view:     DONE
    ├──→ Player names in Compare Saves:   DONE
    ├──→ Auto-load game disk:             DONE
    ├──→ Player attribute database:       BLOCKED (no static table found)
    └──→ Transfer Market panel:           BLOCKED (needs attributes)
```
