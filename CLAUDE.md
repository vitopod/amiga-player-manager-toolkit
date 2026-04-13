# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project

Binary analysis and tooling for **Player Manager** (Anco, 1990) — an Amiga 68000 football management game. Primary focus is the Italian version. The user plays on **MiSTer FPGA** (Minimig core), not WinUAE — there is no runtime debugger. All work happens offline on ADF files.

Two ADF disks are involved:
- **Game disk** (`PlayerManagerITA.adf`) — OFS filesystem, contains the DEFAJAM-compressed game executable
- **Save disk** (separate ADF) — FFS filesystem with custom non-AmigaDOS directory, contains save slots, tactics, team names

## Running the Save Disk Tool

```bash
/usr/local/bin/python3.11 PMSaveDiskTool_Mac/PMSaveDiskTool.py
```

The pyenv Python (`python3`) lacks tkinter. Use the python.org-installed `/usr/local/bin/python3.11` which has it. No dependencies beyond the standard library.

To test core parsing without tkinter (headless):

```bash
python3 -c "
exec(open('PMSaveDiskTool_Mac/PMSaveDiskTool.py').read().split('# ─── GUI')[0])
adf = ADF('/path/to/save.adf'); entries = parse_file_table(adf)
sf = SaveFile(adf, [e for e in entries if e.name == 'START.sav'][0])
for t in sf.teams[:5]: print(t.index, t.name, t.division, t.num_players)
"
```

The split on `'# ─── GUI'` isolates all data-layer code (ADF, SaveFile, PatchEntry, game-disk functions) from tkinter. Use the same pattern to test game-disk parsing:

```bash
python3 -c "
exec(open('PMSaveDiskTool_Mac/PMSaveDiskTool.py').read().split('# ─── GUI')[0])
with open('PlayerManagerITA.adf','rb') as f: raw = f.read()
sector = raw[1137*512:(1137+1)*512]
patches = _parse_block1137(sector)
for p in patches: print(f'\${p.offset:06X} {p.size} \${p.value:X}  {p.description}')
"
```

## Repository Layout

```
PlayerManagerITA.adf              Game disk (OFS, 901120 bytes)
PMSaveDiskTool_Mac/
  PMSaveDiskTool.py               Main application (~1600 lines, Python 3 + tkinter)
  MANUAL.md                       User-facing documentation
  ROADMAP.md                      Planned features (patch composer ✓, league dashboard ✓, DEFAJAM decompressor)
PMSaveDiskTool_v1.2/              Original Windows tool (MSI installer, reference only)
```

## PMSaveDiskTool Architecture

Single-file Python application. The file is split into four layers by comment headers; everything before `# ─── GUI` is pure data logic with no tkinter dependency.

### Data layer (before `# ─── GUI`)

| Class / function | Role |
|-----------------|------|
| `ADF` | Raw disk image I/O — read/write sectors and byte ranges |
| `DirEntry` | One entry in the custom file allocation table at sector 2 |
| `TeamRecord` | Parse/pack one 100-byte team record; `_name_is_binary` flag handles team #43 |
| `SaveFile` | Loads a save slot, parses 44 TeamRecords, writes changes back to ADF buffer |
| `PatchEntry` | Dataclass: `offset`, `size` ('B'/'W'/'L'), `value`, `description`. `encode()` returns 68000 bytes; `byte_size()` returns 12 (B/W) or 14 (L) |
| `parse_file_table(adf)` | Reads sector 2 → list of DirEntry |
| `parse_liga_names(adf, entries)` | Reads LigaName.nam → 44 canonical team names |
| `_parse_block1137(sector_512)` | Parses 68000 patch instructions from block 1137 → list of PatchEntry |
| `_write_block1137(sector_512, patches)` | Regenerates callback code, recalculates OFS checksum, returns new 512-byte block |
| `_parse_hex_str(s)` | Accepts `$xxxx`, `0x...`, or plain hex digits |
| `_ofs_read_file(adf_data, filename)` | Reads a file from an OFS ADF via root block hash table + data block chain |
| `_find_game_disk()` | Auto-discovers `PlayerManagerITA.adf` in script dir or parent dir |

### Game disk layer

| Class | Role |
|-------|------|
| `_DEFAJAMDecompressor` | Two-phase decompressor: backward LZ77 with Huffman LUT + $9B marker RLE |
| `GameDisk` | Loads game disk ADF, decompresses `2507`, extracts 245 Italian surnames from $15B02–$162E6 |
| `TacticsFile` | Parse/edit .tac files: 10 zones × 10 players × 2 states × (X,Y) + 128-byte description |
| `Disasm68k` | 68000 disassembler with EA decoding, cross-reference search, and word-pattern search |

`GameDisk.player_name(id)` maps player IDs to surnames via `id % 245` (heuristic — exact algorithm unknown).

The app auto-loads the game disk at startup via `_find_game_disk()` and stores it as `self.game_disk`. This is passed to `PatchComposerWindow` and `CompareSavesDialog` for auto-population.

### GUI layer (after `# ─── GUI`)

| Class | Role |
|-------|------|
| `PMSaveDiskToolApp` | Main window: save slot browser, team editor, hex viewer |
| `PatchComposerWindow` | Toplevel: game-disk block 1137 editor (add/remove/preview/write patches) |
| `LeagueDashboardWindow` | Toplevel: tabbed division league tables sorted by Points/Goals |
| `CompareSavesDialog` | Toplevel: player transfers, division changes, budget deltas between two saves |
| `TacticsViewerWindow` | Toplevel: visual pitch editor for .tac files with draggable player dots |
| `DisassemblerWindow` | Toplevel: interactive 68000 disassembler with navigation, xref, word/MUL search |

All multi-byte values are big-endian (Motorola 68000). Use `struct.unpack_from('>H', ...)` for words, `'>I'` for longs.

## ADF Format Basics

Both disk types are standard Amiga Disk Files: 901,120 bytes = 1,760 sectors × 512 bytes.

**OFS (Old File System)** — used by the game disk. Each 512-byte block has a 24-byte header:

| Offset | Size | Field |
|--------|------|-------|
| 0 | 4 | Block type (8 = data block) |
| 4 | 4 | Parent file header block |
| 8 | 4 | Sequence number (1-based) |
| 12 | 4 | Data size (valid bytes) |
| 16 | 4 | Next data block (0 = last) / Checksum (context-dependent) |
| 20 | 4 | Checksum / Next data block (context-dependent) |

**Note on OFS header layout**: The position of `next` vs `checksum` at offsets 16/20 varies. In `_ofs_read_file`, `next` is at 16 and checksum at 20 (verified by following data block chains). In `_write_block1137`, the checksum is zeroed/recalculated at sector byte 16 (sum of all 128 longwords = 0).

**Checksum rule**: sum of all 128 longwords in the 512-byte sector = `0x00000000`. After modifying data, recompute the checksum longword as the negation of the sum of the other 127 longwords.

**FFS (Fast File System)** — used by the save disk. No per-block headers; sectors are pure data. The save disk uses a **custom directory** (not standard AmigaDOS) at sector 2.

## Game Disk — Patch Mechanism

Block 1137 is a 68000 HUNK executable by arab^Scoopex that:

1. Calls `LoadSeg("2507")` to load the DEFAJAM-packed game
2. Hooks a callback into the decompressor's final `JMP $50000`
3. The callback applies byte/word/long patches to chip RAM at `$50000 + offset`
4. `JMP (A0)` hands control to the game

**Block 1137 data layout** (offsets relative to first data byte = sector byte 24):

| Data offset | Content |
|-------------|---------|
| `+$000–$04F` | HUNK loader stub (opens dos.library, LoadSeg, hooks callback) |
| `+$050` | `LEA $50000,A0` — 6 bytes |
| `+$056–+$0CB` | Patch instructions (currently 10 copy-protection bypasses, 118 bytes) |
| `+$0CC` | `JMP (A0)` — 2 bytes |
| `+$0CE–+$0FF` | Credit string — **safe to overwrite** (50 bytes reclaimable) |
| `+$100` | `dos.library\0` — **PC-relative ref from loader, do not touch** |
| `+$10C` | `2507\0` — **PC-relative ref from loader, do not touch** |

**Patch instruction encoding** (canonical form used by `PatchEntry.encode()`):
```
20 3C XX XX XX XX   MOVE.L #offset, D0
11 BC 00 YY 08 00   MOVE.B #val, (A0,D0.L)        ; byte patch, 12 bytes total
31 BC YY YY 08 00   MOVE.W #val, (A0,D0.L)        ; word patch, 12 bytes total
21 BC VV VV VV VV 08 00   MOVE.L #val, (A0,D0.L)  ; long patch, 14 bytes total
```

Note: for MOVE.B the immediate is a 16-bit word with the value in the **low byte** (`00 vv`), not the high byte.

**Patch space budget**: 170 bytes writable (`+$056` to `+$0FF`), minus 2 for JMP = **168 bytes** for patches. The 10 existing patches use 124 bytes (first patch was originally a 6-byte short form, re-encoded to canonical 12 bytes on write). Leaves 44 bytes free ≈ 3 more byte/word patches.

**Known game offsets** (decompressed image, relative to `$50000`):

| Offset | Size | What |
|--------|------|------|
| `$011740` | WORD | Manager age (`displayed = stored + 1`) |
| `$01608A` | BYTE | Single character in manager name |

## Save Disk Format

Sector 2 contains a flat file allocation table. Each 16-byte entry:

```
Bytes 0-11:  Filename (ASCII, null-padded)
Bytes 12-13: Start address (big-endian, in 32-byte units)
Bytes 14-15: File size in bytes (big-endian)
```

Disk offset = `start_field × 32`.

### Save file structure (4408 bytes = 44 teams × 100 bytes + 8-byte trailer)

**Team record (100 bytes):**

| Bytes | Field | Details |
|-------|-------|---------|
| 0–11 | League stats | 6 BE words: Points, Goals, Rank A, Rank B, Flag 1, Flag 2 |
| 12–61 | Player IDs | Up to 25 BE words; `0xFFFF` = empty. Globally unique indices (0–1036) into the game disk's player database |
| 62–63 | Team value | Signed BE word (negative = debt) |
| 64–65 | Budget tier | Fixed per division in templates (46/32/23/14), evolves in saves |
| 66–67 | Division | 0–3 in .sav files; different meaning in start.dat |
| 68–99 | Team name | Null-terminated ASCII + trailing data |

**Key facts verified by roundtrip testing:**
- All 1,037 player IDs (0–1036) are globally unique in start.dat — database indices, not attribute values
- Team #43 sometimes contains binary data; `pack()` preserves `self.raw[68:]` unchanged when `_name_is_binary` is set
- Team ordering differs between LigaName.nam, start.dat, and .sav files (reshuffled by division/performance)

### Other save disk files

| File | Size | Description |
|------|------|-------------|
| `LigaName.nam` | 880 | 44 × 20-byte canonical team name entries |
| `start.dat` | 4408 | Factory template (zeroed stats, all 1037 player IDs distributed) |
| `*.sav` | 4408 | Save slots (up to 11) |
| `*.tac` | 928–980 | Tactics files (see Tactics format below) |
| `data.disk` | 10 | ASCII string `"data.disk\0"` |

### Player database (42 bytes × ~1037 players)

The game stores a full player attribute database on the save disk immediately after each `.sav` file. Attributes are procedurally generated at runtime by the RNG function at $050E8, then persisted so they survive load/save cycles.

**Location**: For a file table entry `e`, the player DB starts at `e.byte_offset + e.size_bytes`. First 2 bytes are a BE word header (values 1–4 observed), then 42-byte records indexed by player ID.

**42-byte record layout** (all single bytes unless noted):

| Offset | Field | Notes |
|--------|-------|-------|
| +00–03 | RNG Seed | 4-byte BE longword |
| +04 | Age | Starts at 16, increments each season |
| +05 | Position | 0=unset, 1=GK, 2=DEF, 3=MID, 4=FWD |
| +06 | Division | 0–3 |
| +07 | Team index | 0xFF = free agent |
| +08 | Height (cm) | Range ~150–250 |
| +09 | Weight (kg) | Range ~40–100 |
| +0A–13 | Skills | Stamina, Resilience, Pace, Agility, Aggression, Flair, Passing, Shooting, Tackling, Keeping (0–200 each) |
| +14 | Reserved | Always 0 |
| +15 | Injury weeks | |
| +16 | Disciplinary | Bit-packed: high 6 + low 2 |
| +17 | Morale | Bit-packed: high 6 + low 2 |
| +18 | Value | 0–255, likely market value |
| +19 | Transfer weeks | |
| +1A | Mystery | Bit-packed: bits 0–5 and 6–7 |
| +1B–1C | Injuries this/last year | |
| +1D–1E | Display points this/last year | |
| +1F–20 | Goals this/last year | |
| +21–22 | Matches this/last year | |
| +23–26 | Division years | Div1, Div2, Div3, Div4 |
| +27 | International years | |
| +28 | Contract years | |
| +29 | Last byte | Partially correlates with position |

**Windows tool confirmation**: Reverse-engineered from UltimateBinary's PE32 executable — `IMUL reg, reg, 0x2A` (42) matches the 68000 `MULU #42` at $050E8.

### Tactics file format (.tac)

928 bytes base (some templates 980 bytes with 52-byte icon appended):

```
Bytes 0-799:   Coordinate data
Bytes 800-927: Description (2-byte header 0x0000 + null-terminated ASCII + padding)
Bytes 928-979: Optional formation icon bitmap (980-byte files only)
```

**Coordinate data**: 10 zones × 10 outfield players × 2 states × (X, Y) = 400 word pairs = 800 bytes.

For zone Z, player P, state S (0=with ball, 1=without ball):
- Byte offset = `(Z * 40 + P * 4 + S * 2) * 2`
- Two big-endian 16-bit words: X (range 12–900), Y (range 1–1392)

Goalkeeper is not stored — fixed by game engine. X values typically divisible by 6, Y by 3.

### Decompressed game image layout

| Region | Size | Content |
|--------|------|---------|
| `$00000–$00076` | 118 B | System init (disable DMA/IRQ, clear chip RAM) |
| `$00078–$134D6` | ~79 KB | Main game code |
| `$134D8–$1369A` | 450 B | JMP vector table (75 Amiga library redirects) |
| `$14000–$15B02` | ~7 KB | Italian text strings |
| `$15B02–$162E6` | ~2 KB | Player surname table (245 null-terminated names) |
| `$162E6–$1DD57` | ~31 KB | Data (city names, graphics) |
| `$1DD58–$1FFFF` | ~9 KB | Zero padding |

**Key architectural notes**: A4 is the library dispatch base register (set to `$19382 + $7FFE = $21380`). Library calls use `JSR d16(A4)` with negative displacements. A4-relative and A5-relative addressing dominates the code. `MULU #100` = team record operations; `MULU #42` = player sub-structure operations.
