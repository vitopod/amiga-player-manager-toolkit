#!/usr/bin/env python3
"""
PMSaveDiskTool for macOS
Player Manager Save Disk Editor — Mac version of UltimateBinary's Windows tool.
Works with Player Manager (1990, Anco) ADF disk images.

Supports: English, German, Italian and other language versions.
Save disk uses FFS (DOS\x01) with a custom (non-AmigaDOS) directory structure.

Usage:
    python3 PMSaveDiskTool.py

Requires: Python 3.8+ with tkinter (included with macOS Python).
"""

import struct
import os
import sys
import dataclasses
import tkinter as tk
from tkinter import ttk, filedialog, messagebox, simpledialog

# ─── Platform ────────────────────────────────────────────────────────

_IS_MAC   = sys.platform == 'darwin'
_IS_WIN   = sys.platform == 'win32'
_MOD      = 'Command' if _IS_MAC else 'Control'   # keyboard modifier key
_MOD_DISP = '⌘' if _IS_MAC else 'Ctrl+'          # display label
# Monospace font: Menlo on macOS, Consolas on Windows, fallback elsewhere
_MONO = 'Menlo' if _IS_MAC else ('Consolas' if _IS_WIN else 'Monospace')

# ─── Constants ───────────────────────────────────────────────────────

ADF_SIZE = 901120          # 1760 sectors × 512 bytes
SECTOR_SIZE = 512
NUM_SECTORS = 1760
DIR_SECTOR = 2             # File table is at sector 2
DIR_ENTRY_SIZE = 16        # 12-byte name + 2-byte start + 2-byte size
ADDR_UNIT = 32             # Start field is in 32-byte units
TEAM_RECORD_SIZE = 100     # Each team record is 100 bytes
TEAM_NAME_OFFSET = 68      # Team name starts at byte 68 in each record
MAX_TEAMS = 44             # Max teams in a save file
MAX_PLAYER_SLOTS = 25      # Words at bytes 12-61 (50 bytes / 2)
LIGA_NAME_ENTRY_SIZE = 20  # LigaName.nam: 44 × 20-byte entries
LIGA_NAME_TEAMS = 44
PLAYER_RECORD_SIZE = 42    # Each player attribute record is 42 bytes
PLAYER_DB_HEADER_SIZE = 2  # 2-byte BE header before player records

POSITION_NAMES = {0: "?", 1: "GK", 2: "DEF", 3: "MID", 4: "FWD"}
SKILL_NAMES = [
    "Stamina", "Resilience", "Pace", "Agility", "Aggression",
    "Flair", "Passing", "Shooting", "Tackling", "Keeping",
]


# ─── ADF Layer ───────────────────────────────────────────────────────

class ADF:
    """Raw ADF disk image access."""

    def __init__(self, path):
        self.path = path
        with open(path, 'rb') as f:
            self.data = bytearray(f.read())
        if len(self.data) != ADF_SIZE:
            raise ValueError(f"Not an ADF: expected {ADF_SIZE} bytes, got {len(self.data)}")

    @property
    def filesystem_type(self):
        sig = self.data[0:4]
        if sig[:3] == b'DOS':
            return 'FFS' if sig[3] & 1 else 'OFS'
        return 'Unknown'

    def read_sector(self, sector):
        off = sector * SECTOR_SIZE
        return bytes(self.data[off:off + SECTOR_SIZE])

    def read_bytes(self, offset, length):
        return bytes(self.data[offset:offset + length])

    def write_bytes(self, offset, data):
        self.data[offset:offset + len(data)] = data

    def save(self, path=None):
        path = path or self.path
        with open(path, 'wb') as f:
            f.write(self.data)


# ─── Save Disk File Table ────────────────────────────────────────────

class DirEntry:
    """One entry in the save disk's custom file table (sector 2)."""

    def __init__(self, name, start_unit, size_bytes):
        self.name = name
        self.start_unit = start_unit      # In 32-byte units
        self.size_bytes = size_bytes

    @property
    def byte_offset(self):
        return self.start_unit * ADDR_UNIT

    def __repr__(self):
        return f"DirEntry({self.name!r}, off={self.byte_offset}, size={self.size_bytes})"


def parse_file_table(adf):
    """Parse the custom file table at sector 2."""
    sector = adf.read_sector(DIR_SECTOR)
    entries = []
    for i in range(SECTOR_SIZE // DIR_ENTRY_SIZE):
        raw = sector[i * DIR_ENTRY_SIZE:(i + 1) * DIR_ENTRY_SIZE]
        if all(b == 0 for b in raw):
            break
        # Name is 12 bytes, null-padded
        name_raw = raw[:12]
        null_idx = name_raw.find(b'\x00')
        if null_idx == -1:
            null_idx = 12
        name = name_raw[:null_idx].decode('ascii', errors='replace')
        if not name:
            break
        start = struct.unpack_from('>H', raw, 12)[0]
        size = struct.unpack_from('>H', raw, 14)[0]
        entries.append(DirEntry(name, start, size))
    return entries


# ─── Team Record ─────────────────────────────────────────────────────

class TeamRecord:
    """One team's data within a save file (100 bytes).

    Layout:
      Bytes  0-11: League stats — 6 big-endian words
      Bytes 12-61: Player slots — up to 25 words (0xFFFF = empty slot)
      Bytes 62-63: Team value / budget (signed BE word)
      Bytes 64-65: Budget tier (start.dat) or evolving value (saves)
      Bytes 66-67: Division (0-3 in .sav) or other data (start.dat)
      Bytes 68-99: Team name (null-terminated ASCII) + trailing data
    """

    STAT_LABELS = ["Points", "Goals", "Rank A", "Rank B", "Flag 1", "Flag 2"]

    def __init__(self, raw, index):
        self.index = index
        self.raw = bytearray(raw)

        # Parse league stats (bytes 0-11 → 6 big-endian words)
        self.league_stats = [struct.unpack_from('>H', self.raw, i)[0]
                            for i in range(0, 12, 2)]

        # Player value words (bytes 12-61 → up to 25 words)
        self.player_values = [struct.unpack_from('>H', self.raw, i)[0]
                              for i in range(12, 62, 2)]

        # Count how many player slots are filled (non-0xFFFF)
        self.num_players = sum(1 for v in self.player_values if v != 0xFFFF)

        # Pre-name header (bytes 62-67 → 3 words)
        self.word_62 = struct.unpack_from('>H', self.raw, 62)[0]
        self.word_64 = struct.unpack_from('>H', self.raw, 64)[0]
        self.word_66 = struct.unpack_from('>H', self.raw, 66)[0]

        # Team name (bytes 68+, null-terminated)
        name_data = self.raw[TEAM_NAME_OFFSET:]
        null = name_data.find(b'\x00')
        if null == -1:
            null = len(name_data)
        # Check if name is valid ASCII
        raw_name = name_data[:null]
        if all(32 <= b < 127 for b in raw_name) and len(raw_name) > 0:
            self.name = raw_name.decode('ascii')
            self._name_is_binary = False
        else:
            self.name = ""  # Garbled data (e.g. team #43 in some saves)
            self._name_is_binary = True

        # After-name data (variable position)
        after_name_start = TEAM_NAME_OFFSET + null + 1
        self.after_name = bytes(self.raw[after_name_start:])

    @property
    def division(self):
        """Division number (0-3), only meaningful in .sav files."""
        return self.word_66 if self.word_66 <= 3 else None

    @property
    def team_value_signed(self):
        """word_62 as signed 16-bit (can be negative = debt)."""
        v = self.word_62
        return v if v < 0x8000 else v - 0x10000

    def pack(self):
        """Re-pack the record to 100 bytes."""
        buf = bytearray(100)

        # League stats
        for i, v in enumerate(self.league_stats):
            struct.pack_into('>H', buf, i * 2, v)

        # Player values (up to 25 slots)
        for i, v in enumerate(self.player_values):
            struct.pack_into('>H', buf, 12 + i * 2, v)

        # Pre-name header
        struct.pack_into('>H', buf, 62, self.word_62)
        struct.pack_into('>H', buf, 64, self.word_64)
        struct.pack_into('>H', buf, 66, self.word_66)

        # Team name + trailing data
        if self._name_is_binary:
            # Preserve original raw bytes for garbled name records
            buf[TEAM_NAME_OFFSET:] = self.raw[TEAM_NAME_OFFSET:]
        else:
            name_bytes = self.name.encode('ascii', errors='replace')
            name_field_len = 100 - TEAM_NAME_OFFSET
            for i in range(name_field_len):
                buf[TEAM_NAME_OFFSET + i] = 0
            buf[TEAM_NAME_OFFSET:TEAM_NAME_OFFSET + len(name_bytes)] = name_bytes

            # After-name data
            after_start = TEAM_NAME_OFFSET + len(name_bytes) + 1
            remaining = min(len(self.after_name), 100 - after_start)
            if remaining > 0:
                buf[after_start:after_start + remaining] = self.after_name[:remaining]

        self.raw = buf
        return bytes(buf)

    def __repr__(self):
        return f"TeamRecord({self.index}, {self.name!r})"


# ─── Liga Name Table ────────────────────────────────────────────────

def parse_liga_names(adf, dir_entries):
    """Parse LigaName.nam → list of 44 canonical team names."""
    for e in dir_entries:
        if e.name.lower() == 'liganame.nam':
            raw = adf.read_bytes(e.byte_offset, e.size_bytes)
            names = []
            for i in range(LIGA_NAME_TEAMS):
                rec = raw[i * LIGA_NAME_ENTRY_SIZE:(i + 1) * LIGA_NAME_ENTRY_SIZE]
                null = rec.find(b'\x00')
                if null == -1:
                    null = LIGA_NAME_ENTRY_SIZE
                name = rec[:null].decode('ascii', errors='replace')
                names.append(name)
            return names
    return []


# ─── Save File ───────────────────────────────────────────────────────

class SaveFile:
    """A single save slot (e.g. START.sav, WIN.sav) or template (start.dat)."""

    def __init__(self, adf, dir_entry):
        self.adf = adf
        self.entry = dir_entry
        self.data = bytearray(adf.read_bytes(dir_entry.byte_offset, dir_entry.size_bytes))
        self.is_template = dir_entry.name.endswith('.dat')
        self.teams = []
        self._parse_teams()

    def _parse_teams(self):
        self.teams = []
        num = min(MAX_TEAMS, len(self.data) // TEAM_RECORD_SIZE)
        for i in range(num):
            off = i * TEAM_RECORD_SIZE
            raw = self.data[off:off + TEAM_RECORD_SIZE]
            team = TeamRecord(raw, i)
            self.teams.append(team)

    @property
    def trailer(self):
        """Last 8 bytes after all 44 team records (bytes 4400-4407)."""
        if len(self.data) >= 4408:
            return bytes(self.data[4400:4408])
        return b''

    def write_back(self):
        """Write modified team records back to the ADF buffer."""
        for team in self.teams:
            packed = team.pack()
            off = team.index * TEAM_RECORD_SIZE
            self.data[off:off + TEAM_RECORD_SIZE] = packed
        self.adf.write_bytes(self.entry.byte_offset, bytes(self.data))


# ─── Player Record ──────────────────────────────────────────────────

class PlayerRecord:
    """One player's 42-byte attribute record from the save disk database.

    The game stores the full player database (42 bytes × ~1037 players)
    on the save disk immediately after each .sav file.  Attributes are
    procedurally generated at runtime, then persisted so they survive
    load/save cycles.
    """

    __slots__ = (
        'player_id', 'raw',
        'rng_seed', 'age', 'position', 'division', 'team_index',
        'height', 'weight',
        'stamina', 'resilience', 'pace', 'agility', 'aggression',
        'flair', 'passing', 'shooting', 'tackling', 'keeping',
        'injury_weeks', 'disciplinary', 'morale', 'value',
        'transfer_weeks', 'mystery',
        'injuries_this_year', 'injuries_last_year',
        'dsp_pts_this_year', 'dsp_pts_last_year',
        'goals_this_year', 'goals_last_year',
        'matches_this_year', 'matches_last_year',
        'div1_years', 'div2_years', 'div3_years', 'div4_years',
        'int_years', 'contract_years', 'last_byte',
    )

    def __init__(self, raw_42, player_id):
        self.player_id = player_id
        self.raw = bytes(raw_42)
        r = raw_42
        self.rng_seed       = struct.unpack_from('>I', r, 0)[0]
        self.age            = r[4]
        self.position       = r[5]
        self.division       = r[6]
        self.team_index     = r[7]
        self.height         = r[8]
        self.weight         = r[9]
        # 10 skills at offsets 0x0A–0x13
        self.stamina        = r[0x0A]
        self.resilience     = r[0x0B]
        self.pace           = r[0x0C]
        self.agility        = r[0x0D]
        self.aggression     = r[0x0E]
        self.flair          = r[0x0F]
        self.passing        = r[0x10]
        self.shooting       = r[0x11]
        self.tackling       = r[0x12]
        self.keeping        = r[0x13]
        # Status
        self.injury_weeks   = r[0x15]
        self.disciplinary   = r[0x16]
        self.morale         = r[0x17]
        self.value          = r[0x18]
        self.transfer_weeks = r[0x19]
        self.mystery        = r[0x1A]
        # Career stats
        self.injuries_this_year = r[0x1B]
        self.injuries_last_year = r[0x1C]
        self.dsp_pts_this_year  = r[0x1D]
        self.dsp_pts_last_year  = r[0x1E]
        self.goals_this_year    = r[0x1F]
        self.goals_last_year    = r[0x20]
        self.matches_this_year  = r[0x21]
        self.matches_last_year  = r[0x22]
        self.div1_years     = r[0x23]
        self.div2_years     = r[0x24]
        self.div3_years     = r[0x25]
        self.div4_years     = r[0x26]
        self.int_years      = r[0x27]
        self.contract_years = r[0x28]
        self.last_byte      = r[0x29]

    @property
    def position_name(self):
        return POSITION_NAMES.get(self.position, "?")

    @property
    def skills(self):
        """Return list of 10 skill values in canonical order."""
        return [
            self.stamina, self.resilience, self.pace, self.agility,
            self.aggression, self.flair, self.passing, self.shooting,
            self.tackling, self.keeping,
        ]

    @property
    def skill_avg(self):
        """Average of all 10 skills."""
        s = self.skills
        return sum(s) / len(s)

    def role_skill_avg(self):
        """Average of position-relevant skills.
        GK: Keeping, Agility, Resilience
        DEF: Tackling, Stamina, Aggression, Pace
        MID: Passing, Flair, Stamina, Agility
        FWD: Shooting, Pace, Flair, Agility
        """
        if self.position == 1:  # GK
            vals = [self.keeping, self.agility, self.resilience]
        elif self.position == 2:  # DEF
            vals = [self.tackling, self.stamina, self.aggression, self.pace]
        elif self.position == 3:  # MID
            vals = [self.passing, self.flair, self.stamina, self.agility]
        elif self.position == 4:  # FWD
            vals = [self.shooting, self.pace, self.flair, self.agility]
        else:
            vals = self.skills
        return sum(vals) / len(vals) if vals else 0

    @property
    def total_career_years(self):
        return self.div1_years + self.div2_years + self.div3_years + self.div4_years

    def __repr__(self):
        return (f"PlayerRecord(id={self.player_id}, age={self.age}, "
                f"pos={self.position_name}, skills_avg={self.skill_avg:.0f})")

    def pack(self):
        """Serialize this record back to 42 bytes."""
        buf = bytearray(42)
        struct.pack_into('>I', buf, 0, self.rng_seed)
        buf[4]    = self.age
        buf[5]    = self.position
        buf[6]    = self.division
        buf[7]    = self.team_index
        buf[8]    = self.height
        buf[9]    = self.weight
        buf[0x0A] = self.stamina
        buf[0x0B] = self.resilience
        buf[0x0C] = self.pace
        buf[0x0D] = self.agility
        buf[0x0E] = self.aggression
        buf[0x0F] = self.flair
        buf[0x10] = self.passing
        buf[0x11] = self.shooting
        buf[0x12] = self.tackling
        buf[0x13] = self.keeping
        buf[0x14] = 0  # Reserved
        buf[0x15] = self.injury_weeks
        buf[0x16] = self.disciplinary
        buf[0x17] = self.morale
        buf[0x18] = self.value
        buf[0x19] = self.transfer_weeks
        buf[0x1A] = self.mystery
        buf[0x1B] = self.injuries_this_year
        buf[0x1C] = self.injuries_last_year
        buf[0x1D] = self.dsp_pts_this_year
        buf[0x1E] = self.dsp_pts_last_year
        buf[0x1F] = self.goals_this_year
        buf[0x20] = self.goals_last_year
        buf[0x21] = self.matches_this_year
        buf[0x22] = self.matches_last_year
        buf[0x23] = self.div1_years
        buf[0x24] = self.div2_years
        buf[0x25] = self.div3_years
        buf[0x26] = self.div4_years
        buf[0x27] = self.int_years
        buf[0x28] = self.contract_years
        buf[0x29] = self.last_byte
        return bytes(buf)


def parse_player_db(adf, dir_entry):
    """Parse the player attribute database that follows a .sav file on disk.

    Returns a dict mapping player_id → PlayerRecord, or empty dict if
    the database is not found or unreadable.
    """
    db_offset = dir_entry.byte_offset + dir_entry.size_bytes
    # Check there's enough room for at least the 2-byte header + one record
    if db_offset + PLAYER_DB_HEADER_SIZE + PLAYER_RECORD_SIZE > ADF_SIZE:
        return {}
    header_raw = adf.read_bytes(db_offset, PLAYER_DB_HEADER_SIZE)
    _header_word = struct.unpack_from('>H', header_raw, 0)[0]
    records_start = db_offset + PLAYER_DB_HEADER_SIZE
    # Read as many 42-byte records as fit before hitting the ADF boundary
    available = ADF_SIZE - records_start
    max_players = available // PLAYER_RECORD_SIZE
    # Sanity cap — the game has ~1037 players
    max_players = min(max_players, 1100)
    players = {}
    for pid in range(max_players):
        off = records_start + pid * PLAYER_RECORD_SIZE
        raw = adf.read_bytes(off, PLAYER_RECORD_SIZE)
        # Skip completely zeroed records (unused slots)
        if all(b == 0 for b in raw):
            continue
        players[pid] = PlayerRecord(raw, pid)
    return players


def write_player_db(adf, dir_entry, players):
    """Write modified player records back to the ADF buffer.

    `players` is a dict {player_id: PlayerRecord} — the same format
    returned by parse_player_db().  Only records present in the dict
    are written; the 2-byte header is preserved.
    """
    db_offset = dir_entry.byte_offset + dir_entry.size_bytes
    records_start = db_offset + PLAYER_DB_HEADER_SIZE
    for pid, rec in players.items():
        off = records_start + pid * PLAYER_RECORD_SIZE
        if off + PLAYER_RECORD_SIZE <= ADF_SIZE:
            adf.write_bytes(off, rec.pack())


# ─── Game Disk / Patch Composer ──────────────────────────────────────

_PATCH_BLOCK_SECTOR = 1137    # Block 1137 on the game disk ADF
_OFS_HDR = 24                 # OFS data block header size in bytes

# Offsets within the data area (after 24-byte OFS header):
_CB_LEA_AT      = 0x050       # LEA $50000,A0 lives here (6 bytes)
_CB_PATCHES_AT  = 0x056       # First patch instruction starts here
_CB_SAFE_END    = 0x100       # Protected strings start here — do NOT write here or beyond
#   data[+$100] = "dos.library\0"  ← referenced by PC-relative loader code
#   data[+$10C] = "2507\0"         ← referenced by PC-relative loader code

_PATCH_AREA_SIZE  = _CB_SAFE_END - _CB_PATCHES_AT   # 0xAA = 170 bytes writable
_JMP_SIZE         = 2                                # JMP (A0) = 4E D0
_MAX_PATCH_BYTES  = _PATCH_AREA_SIZE - _JMP_SIZE     # 168 bytes for actual patches

_LEA_50000_A0 = bytes([0x41, 0xF9, 0x00, 0x05, 0x00, 0x00])  # LEA $50000, A0
_JMP_A0       = bytes([0x4E, 0xD0])                            # JMP  (A0)

# Known copy-protection patch offsets (original arab^Scoopex cracks)
_COPYPROT_OFFSETS = {
    0x002B5E, 0x007330, 0x01113E, 0x004A38, 0x007F08,
    0x0048B0, 0x00C2D6, 0x003608, 0x0070D8, 0x00F29C,
}

# Human labels for known offsets
_OFFSET_LABELS = {
    0x002B5E: "Copy-prot bypass #1 (BRA)",
    0x007330: "Copy-prot bypass #2 (BRA)",
    0x01113E: "Copy-prot bypass #3 (BRA)",
    0x004A38: "Copy-prot bypass #4 (NOP×2)",
    0x007F08: "Copy-prot bypass #5 (NOP×2)",
    0x0048B0: "Copy-prot bypass #6 (BRA)",
    0x00C2D6: "Copy-prot bypass #7 (BRA)",
    0x003608: "Copy-prot bypass #8 (BRA)",
    0x0070D8: "Copy-prot bypass #9 (BRA)",
    0x00F29C: "Copy-prot bypass #10 (BRA)",
    0x011740: "Manager age (= displayed − 1)",
    0x01608A: "Manager name char",
}

# Game disk ADF filename (auto-discovered relative to script directory)
# Game disk filenames tried in order (first match wins)
_GAME_DISK_CANDIDATES = [
    "PlayerManagerITA.adf",   # Italian (primary dev target)
    "PlayerManager.adf",      # English / generic
    "PlayerManagerDE.adf",    # German
    "PlayerManagerFR.adf",    # French
    "PlayerManagerSP.adf",    # Spanish
]
_GAME_DISK_FILENAME = _GAME_DISK_CANDIDATES[0]  # used in error messages


# ─── OFS File Reader ────────────────────────────────────────────────

def _ofs_read_file(adf_data, filename):
    """Read a file from an OFS (Old File System) ADF by following the
    root block hash table and OFS data block chain.
    Returns the file contents as bytes, or None if not found."""
    root_sector = 880
    root_off = root_sector * SECTOR_SIZE
    # Root block hash table: 72 longwords at offset 24
    ht_offset = root_off + 24
    ht_size = 72

    # Hash the filename (AmigaDOS hash)
    h = len(filename)
    for ch in filename.upper():
        h = ((h * 13) + ord(ch)) & 0x7FF
    h %= ht_size

    block = struct.unpack_from('>I', adf_data, ht_offset + h * 4)[0]
    if block == 0:
        return None

    # Walk the hash chain to find the file header
    while block:
        blk_off = block * SECTOR_SIZE
        blk_type = struct.unpack_from('>I', adf_data, blk_off)[0]
        if blk_type != 2:  # not a header block
            break
        # Name at offset 432: 1 length byte + up to 30 chars
        name_len = adf_data[blk_off + 432]
        name = adf_data[blk_off + 433:blk_off + 433 + name_len].decode('ascii', errors='replace')
        if name.upper() == filename.upper():
            # Found it — read file size from offset 324
            file_size = struct.unpack_from('>I', adf_data, blk_off + 324)[0]
            first_data = struct.unpack_from('>I', adf_data, blk_off + 16)[0]
            # Follow OFS data block chain
            result = bytearray()
            data_block = first_data
            while data_block and len(result) < file_size:
                db_off = data_block * SECTOR_SIZE
                # OFS data block: type(4) parent(4) seq(4) data_size(4) next(4) checksum(4) + data
                db_data_size = struct.unpack_from('>I', adf_data, db_off + 12)[0]
                db_next = struct.unpack_from('>I', adf_data, db_off + 16)[0]
                result.extend(adf_data[db_off + 24:db_off + 24 + db_data_size])
                data_block = db_next
            return bytes(result[:file_size])
        # Follow hash chain
        block = struct.unpack_from('>I', adf_data, blk_off + SECTOR_SIZE - 4)[0]

    return None


# ─── DEFAJAM Decompressor ───────────────────────────────────────────

class _DEFAJAMDecompressor:
    """Two-phase decompressor for DEFAJAM-packed Amiga executables.
    Phase 1: backward LZ77 with Huffman-coded literals through a 256-byte LUT.
    Phase 2: RLE expansion using $9B as a marker byte."""

    def __init__(self, hunk_code):
        self._lut = hunk_code[0x0190:0x0190 + 256]
        packed_full = hunk_code[0x0290:]
        self._packed = packed_full[:-8]
        self._write_offset = struct.unpack_from('>I', packed_full, len(packed_full) - 4)[0]
        self._d0_init = struct.unpack_from('>I', packed_full, len(packed_full) - 8)[0]

    def decompress(self):
        """Run both phases and return the final game image."""
        intermediate = self._phase1_lz()
        return self._phase2_rle(intermediate)

    # Phase 1: backward LZ77
    def _phase1_lz(self):
        packed = self._packed
        d0 = self._d0_init
        rp = len(packed)
        out_size = self._write_offset
        output = bytearray(out_size)
        wp = out_size

        def refill():
            nonlocal d0, rp
            rp -= 4
            val = struct.unpack_from('>I', packed, rp)[0]
            carry = val & 1
            d0 = (val >> 1) | 0x80000000
            return carry

        def get_bit():
            nonlocal d0
            carry = d0 & 1
            d0 >>= 1
            if d0 == 0:
                return refill()
            return carry

        def read_bits(n):
            r = 0
            for _ in range(n):
                r = (r << 1) | get_bit()
            return r

        def decode_literal():
            if get_bit() == 0:
                return self._lut[read_bits(6) + 8]
            if get_bit() == 0:
                return self._lut[read_bits(3)]
            if get_bit() == 0:
                return self._lut[read_bits(6) + 72]
            return self._lut[read_bits(7) + 136]

        while wp > 0:
            lc = read_bits(3)
            if lc == 7:
                if get_bit() == 0:
                    lc = read_bits(2) + 7
                else:
                    v = read_bits(8)
                    if v:
                        lc = v + 10
                    else:
                        v = read_bits(12)
                        lc = (v + 265) if v else (read_bits(15) + 4363)
            for _ in range(lc):
                wp -= 1
                output[wp] = decode_literal()
            if wp <= 0:
                break
            if get_bit() == 0:
                ml = 3 if get_bit() == 0 else 2
                off = read_bits(8)
            else:
                tag = read_bits(2)
                if tag == 0:
                    ml, off = 4, read_bits(8)
                elif tag == 1:
                    ml = 5 + read_bits(1); off = read_bits(8)
                elif tag == 2:
                    ml = 7 + read_bits(3); off = read_bits(8)
                else:
                    ml = 15 + read_bits(8); off = read_bits(8)
            for _ in range(ml):
                wp -= 1
                output[wp] = output[wp + off]
        return bytes(output)

    # Phase 2: RLE expansion (marker byte $9B)
    @staticmethod
    def _phase2_rle(data):
        MARKER = 0x9B
        out = bytearray()
        pos = 0
        while pos < len(data):
            b = data[pos]; pos += 1
            if b == MARKER and pos < len(data):
                count = data[pos]; pos += 1
                if count == 0:
                    out.append(MARKER)
                else:
                    val = data[pos]; pos += 1
                    out.extend(bytes([val]) * (count + 3))
            else:
                out.append(b)
        return bytes(out)


# ─── Game Disk ──────────────────────────────────────────────────────

class GameDisk:
    """Represents a loaded and decompressed Player Manager game disk.
    Provides access to the decompressed game image, player names,
    and the raw ADF data for the Patch Composer."""

    def __init__(self, adf_path):
        self.path = adf_path
        with open(adf_path, 'rb') as f:
            self.adf_data = bytearray(f.read())
        if len(self.adf_data) != ADF_SIZE:
            raise ValueError(f"Not an ADF: expected {ADF_SIZE} bytes")

        self.game_image = None     # Decompressed game image (bytes)
        self.player_names = []     # List of player surname strings
        self._decompress()
        self._extract_names()

    def _decompress(self):
        """Extract file '2507', parse its HUNK_CODE, and decompress."""
        raw = _ofs_read_file(self.adf_data, "2507")
        if raw is None:
            raise ValueError("File '2507' not found on game disk")

        # Parse AmigaDOS HUNK: HUNK_HEADER($3F3) ... HUNK_CODE($3E9) size data HUNK_END($3F2)
        pos = 0
        hunk_code = None
        while pos + 4 <= len(raw):
            marker = struct.unpack_from('>I', raw, pos)[0]
            pos += 4
            if marker == 0x3F3:  # HUNK_HEADER
                # Skip header: num_names(0) + table_size + first + last + sizes[]
                pos += 4  # 0 (no resident library names)
                table_size = struct.unpack_from('>I', raw, pos)[0]; pos += 4
                pos += 4  # first hunk
                pos += 4  # last hunk
                pos += table_size * 4  # hunk sizes
            elif marker == 0x3E9:  # HUNK_CODE
                size_longs = struct.unpack_from('>I', raw, pos)[0]; pos += 4
                hunk_code = raw[pos:pos + size_longs * 4]
                break
            elif marker == 0x3F2:  # HUNK_END
                break
            else:
                break

        if hunk_code is None:
            raise ValueError("HUNK_CODE not found in file '2507'")

        dec = _DEFAJAMDecompressor(hunk_code)
        self.game_image = dec.decompress()

    def _extract_names(self):
        """Extract player surname table from the decompressed game image.
        Names are null-terminated ASCII strings in the $15B00-$162E6 region."""
        if self.game_image is None:
            return
        # The name table region — detected by scanning for Italian surnames
        NAME_START = 0x15B02
        NAME_END = 0x162E6
        if len(self.game_image) < NAME_END:
            return
        pos = NAME_START
        names = []
        while pos < NAME_END:
            if self.game_image[pos] == 0:
                pos += 1
                continue
            end = pos
            while end < NAME_END and self.game_image[end] != 0:
                end += 1
            s = self.game_image[pos:end]
            try:
                text = s.decode('ascii')
                if len(text) >= 2 and text[0].isupper():
                    names.append(text)
            except (UnicodeDecodeError, ValueError):
                pass
            pos = end + 1
        self.player_names = names

    def player_name(self, player_id):
        """Return the surname for a player ID. Uses modulo mapping as a
        heuristic until the exact game algorithm is reverse-engineered."""
        if not self.player_names or player_id == 0xFFFF:
            return ""
        return self.player_names[player_id % len(self.player_names)]


def _find_game_disk():
    """Auto-discover the game disk ADF relative to the script directory.
    Tries each name in _GAME_DISK_CANDIDATES in both the script dir and its
    parent. Returns the path of the first match, or None."""
    script_dir = os.path.dirname(os.path.abspath(__file__))
    for base in [script_dir, os.path.dirname(script_dir)]:
        for name in _GAME_DISK_CANDIDATES:
            path = os.path.join(base, name)
            if os.path.isfile(path):
                return path
    return None


@dataclasses.dataclass
class PatchEntry:
    """A single 68000 runtime patch written into the game's decompressed image."""
    offset: int       # Target decompressed-image byte offset
    size: str         # 'B' = byte, 'W' = word, 'L' = longword
    value: int        # Value to write at that offset
    description: str  # Human-readable label

    def byte_size(self):
        """Machine-code bytes required to encode this patch."""
        return 14 if self.size == 'L' else 12

    def encode(self):
        """Return 68000 bytes: MOVE.L #offset,D0 + MOVE.x #val,(A0,D0.L)."""
        out = b'\x20\x3C' + struct.pack('>I', self.offset & 0xFFFFFFFF)
        if self.size == 'B':
            # MOVE.B #val, (A0,D0.L) — immediate byte is low byte of word
            out += b'\x11\xBC' + bytes([0x00, self.value & 0xFF]) + b'\x08\x00'
        elif self.size == 'W':
            out += b'\x31\xBC' + struct.pack('>H', self.value & 0xFFFF) + b'\x08\x00'
        else:  # 'L'
            out += b'\x21\xBC' + struct.pack('>I', self.value & 0xFFFFFFFF) + b'\x08\x00'
        return out


def _parse_hex_str(s):
    """Parse a hex string accepting $xxxx or 0x/0X prefix or plain hex digits."""
    s = s.strip()
    if s.startswith('$'):
        return int(s[1:], 16)
    if s.lower().startswith('0x'):
        return int(s[2:], 16)
    return int(s, 16)


def _parse_block1137(sector_512):
    """
    Parse PatchEntry list from a 512-byte copy of block 1137.
    Recognises:
      • Short MOVE.B #val, d16(A0)  — 11 7C 00 vv disp_hi disp_lo
      • MOVE.L #off, D0  + MOVE.B/W/L #val, (A0,D0.L)  — canonical form
    Stops at JMP (A0) or any unrecognised opcode.
    """
    data = sector_512[_OFS_HDR:]
    patches = []
    pos = _CB_PATCHES_AT

    while pos < _CB_SAFE_END - 1:
        b0, b1 = data[pos], data[pos + 1]

        if b0 == 0x4E and b1 == 0xD0:          # JMP (A0) — end of stream
            break

        # Short form: MOVE.B #val, d16(A0) — 11 7C 00 vv disp_hi disp_lo
        if b0 == 0x11 and b1 == 0x7C and pos + 6 <= _CB_SAFE_END:
            val = data[pos + 3]                 # low byte of immediate word
            off = struct.unpack_from('>H', data, pos + 4)[0]
            desc = _OFFSET_LABELS.get(off, "Copy-prot bypass (BRA)" if val == 0x60 else "")
            patches.append(PatchEntry(off, 'B', val, desc))
            pos += 6
            continue

        # Canonical form: MOVE.L #offset, D0 — 20 3C oo oo oo oo
        if b0 == 0x20 and b1 == 0x3C and pos + 6 <= _CB_SAFE_END:
            off = struct.unpack_from('>I', data, pos + 2)[0]
            pos += 6
            if pos + 2 > _CB_SAFE_END:
                break
            n0, n1 = data[pos], data[pos + 1]

            if n0 == 0x11 and n1 == 0xBC and pos + 6 <= _CB_SAFE_END:   # MOVE.B
                val = data[pos + 3]
                desc = _OFFSET_LABELS.get(off, "Copy-prot bypass (BRA)" if val == 0x60 else "")
                patches.append(PatchEntry(off, 'B', val, desc))
                pos += 6
                continue

            if n0 == 0x31 and n1 == 0xBC and pos + 6 <= _CB_SAFE_END:   # MOVE.W
                val = struct.unpack_from('>H', data, pos + 2)[0]
                desc = _OFFSET_LABELS.get(off, "")
                patches.append(PatchEntry(off, 'W', val, desc))
                pos += 6
                continue

            if n0 == 0x21 and n1 == 0xBC and pos + 8 <= _CB_SAFE_END:   # MOVE.L
                val = struct.unpack_from('>I', data, pos + 2)[0]
                desc = _OFFSET_LABELS.get(off,
                    "Copy-prot bypass (NOP×2)" if val == 0x4E714E71 else "")
                patches.append(PatchEntry(off, 'L', val, desc))
                pos += 8
                continue

            break   # unknown sub-instruction after MOVE.L

        break       # unknown opcode

    return patches


def _write_block1137(sector_512, patches):
    """
    Return a new 512-byte block with the patch list regenerated and the OFS
    checksum recalculated.  Bytes from data +$100 onward are never touched.
    Raises ValueError when patches exceed the available 168-byte budget.
    """
    total = sum(p.byte_size() for p in patches)
    if total > _MAX_PATCH_BYTES:
        raise ValueError(
            f"Patches need {total} bytes but only {_MAX_PATCH_BYTES} available "
            f"({len(patches)} patches)")

    block = bytearray(sector_512)
    base = _OFS_HDR

    # LEA $50000, A0 at data +$050
    block[base + _CB_LEA_AT: base + _CB_LEA_AT + 6] = _LEA_50000_A0

    # Write patches starting at data +$056
    pos = base + _CB_PATCHES_AT
    for p in patches:
        enc = p.encode()
        block[pos: pos + len(enc)] = enc
        pos += len(enc)

    # JMP (A0) immediately after last patch
    block[pos: pos + 2] = _JMP_A0
    pos += 2

    # Zero out rest of safe area (reclaims the credit string space)
    safe_end = base + _CB_SAFE_END
    for i in range(pos, safe_end):
        block[i] = 0

    # Recalculate OFS checksum at block byte 16
    struct.pack_into('>I', block, 16, 0)
    lw_sum = sum(struct.unpack_from('>I', block, i)[0] for i in range(0, 512, 4))
    struct.pack_into('>I', block, 16, (-lw_sum) & 0xFFFFFFFF)

    return bytes(block)


# ─── Tactics File Parser ────────────────────────────────────────────

TAC_NUM_ZONES = 10
TAC_NUM_PLAYERS = 10    # Outfield only; goalkeeper is fixed by the engine
TAC_COORD_BYTES = 800   # 10 zones × 10 players × 2 states × 2 coords × 2 bytes
TAC_DESC_BYTES = 128
TAC_BASE_SIZE = TAC_COORD_BYTES + TAC_DESC_BYTES  # 928
TAC_ICON_SIZE = 52      # Optional formation icon bitmap (980-byte files only)

# Zone names, ordered from own-goal to opponent-goal (approximate)
_ZONE_NAMES = [
    "Def right wing",   # 0
    "Def left wing",    # 1
    "Center midfield R",# 2
    "Deep defense C",   # 3
    "Defense central",  # 4
    "Attack right wing",# 5
    "Center midfield L",# 6
    "Attack central",   # 7
    "Deep attack",      # 8
    "Attack left wing", # 9
]


class TacticsFile:
    """Parse and edit a .tac tactics file from the save disk.

    Structure: 10 zones × 10 outfield players × 2 states (with/without ball)
    Each position is an (X, Y) pair of big-endian 16-bit words.
    Followed by a 128-byte description field.
    """

    def __init__(self, raw_bytes):
        if len(raw_bytes) < TAC_BASE_SIZE:
            raise ValueError(f"Tactics file too small: {len(raw_bytes)} < {TAC_BASE_SIZE}")
        self.raw = bytearray(raw_bytes)
        self.has_icon = len(raw_bytes) >= TAC_BASE_SIZE + TAC_ICON_SIZE
        # positions[zone][player][state] = (x, y)
        # state 0 = "with ball", state 1 = "without ball"
        self.positions = []
        self._parse()

    def _parse(self):
        self.positions = []
        for z in range(TAC_NUM_ZONES):
            zone = []
            for p in range(TAC_NUM_PLAYERS):
                states = []
                for s in range(2):
                    off = (z * TAC_NUM_PLAYERS * 4 + p * 4 + s * 2) * 2
                    x = struct.unpack_from('>H', self.raw, off)[0]
                    y = struct.unpack_from('>H', self.raw, off + 2)[0]
                    states.append((x, y))
                zone.append(states)
            self.positions.append(zone)

    def set_pos(self, zone, player, state, x, y):
        off = (zone * TAC_NUM_PLAYERS * 4 + player * 4 + state * 2) * 2
        struct.pack_into('>H', self.raw, off, x)
        struct.pack_into('>H', self.raw, off + 2, y)
        self.positions[zone][player][state] = (x, y)

    @property
    def description(self):
        desc = self.raw[TAC_COORD_BYTES + 2:TAC_BASE_SIZE]
        end = desc.find(0)
        if end >= 0:
            desc = desc[:end]
        return desc.decode('ascii', errors='replace').strip()

    def pack(self):
        return bytes(self.raw)


# ─── 68000 Disassembler ────────────────────────────────────────────

# Condition code mnemonics for Bcc/DBcc/Scc
_CC_NAMES = [
    'T', 'F', 'HI', 'LS', 'CC', 'CS', 'NE', 'EQ',
    'VC', 'VS', 'PL', 'MI', 'GE', 'LT', 'GT', 'LE',
]

# Register names
_DN = [f'D{i}' for i in range(8)]
_AN = [f'A{i}' for i in range(8)]
_AN[7] = 'SP'  # A7 alias


def _read16(data, pos):
    if pos + 2 > len(data):
        return 0
    return struct.unpack_from('>H', data, pos)[0]


def _read32(data, pos):
    if pos + 4 > len(data):
        return 0
    return struct.unpack_from('>I', data, pos)[0]


def _sign8(v):
    return v - 256 if v >= 128 else v


def _sign16(v):
    return v - 65536 if v >= 32768 else v


def _sign32(v):
    return v - (1 << 32) if v >= (1 << 31) else v


_SIZE_NAMES = {0: '.B', 1: '.W', 2: '.L'}
_SIZE_BYTES = {0: 1, 1: 2, 2: 4}


class Disasm68k:
    """Minimal 68000 disassembler covering the instruction subset used
    by Player Manager.  Returns (mnemonic, length_in_bytes) tuples."""

    def __init__(self, data, base_addr=0):
        self.data = data
        self.base = base_addr

    def _ea_str(self, mode, reg, size, pos, is_dst=False):
        """Decode effective address. Returns (string, extra_bytes_consumed)."""
        if mode == 0:
            return _DN[reg], 0
        elif mode == 1:
            return _AN[reg], 0
        elif mode == 2:
            return f'({_AN[reg]})', 0
        elif mode == 3:
            return f'({_AN[reg]})+', 0
        elif mode == 4:
            return f'-({_AN[reg]})', 0
        elif mode == 5:
            d16 = _sign16(_read16(self.data, pos))
            return f'{d16}({_AN[reg]})', 2
        elif mode == 6:
            ext = _read16(self.data, pos)
            idx_reg = _DN[(ext >> 12) & 7] if not (ext & 0x8000) else _AN[(ext >> 12) & 7]
            idx_sz = '.L' if ext & 0x800 else '.W'
            d8 = _sign8(ext & 0xFF)
            return f'{d8}({_AN[reg]},{idx_reg}{idx_sz})', 2
        elif mode == 7:
            if reg == 0:  # abs.W
                addr = _sign16(_read16(self.data, pos))
                return f'${addr & 0xFFFFFFFF:08X}.W', 2
            elif reg == 1:  # abs.L
                addr = _read32(self.data, pos)
                return f'${addr:08X}', 4
            elif reg == 2:  # d16(PC)
                d16 = _sign16(_read16(self.data, pos))
                target = (pos + self.base - 2) + d16 + 2
                return f'${target & 0xFFFFFFFF:08X}(PC)', 2
            elif reg == 3:  # d8(PC,Xn)
                ext = _read16(self.data, pos)
                idx_reg = _DN[(ext >> 12) & 7] if not (ext & 0x8000) else _AN[(ext >> 12) & 7]
                idx_sz = '.L' if ext & 0x800 else '.W'
                d8 = _sign8(ext & 0xFF)
                target = (pos + self.base - 2) + d8 + 2
                return f'${target & 0xFFFFFFFF:08X}(PC,{idx_reg}{idx_sz})', 2
            elif reg == 4:  # #imm
                if size == 0:  # byte
                    return f'#${_read16(self.data, pos) & 0xFF:02X}', 2
                elif size == 1:  # word
                    return f'#${_read16(self.data, pos):04X}', 2
                elif size == 2:  # long
                    return f'#${_read32(self.data, pos):08X}', 4
        return '???', 0

    def disasm_one(self, offset):
        """Disassemble one instruction at offset. Returns (address, mnemonic, num_bytes)."""
        addr = offset + self.base
        w = _read16(self.data, offset)
        pos = offset + 2  # next word position

        top4 = (w >> 12) & 0xF

        # ── Line 0: ORI, ANDI, SUBI, ADDI, EORI, CMPI, BTST/BCHG/BCLR/BSET ──
        if top4 == 0:
            if (w & 0x0100) and (w & 0x0038) != 0x0008:
                # Dynamic bit operations: BTST/BCHG/BCLR/BSET Dn,<ea>
                dn = (w >> 9) & 7
                op_type = (w >> 6) & 3
                names = ['BTST', 'BCHG', 'BCLR', 'BSET']
                mode = (w >> 3) & 7
                reg = w & 7
                ea_s, ea_n = self._ea_str(mode, reg, 0, pos)
                return addr, f'{names[op_type]} {_DN[dn]},{ea_s}', 2 + ea_n
            op_hi = (w >> 8) & 0xF
            if op_hi in (0x00, 0x02, 0x04, 0x06, 0x0A, 0x0C):
                # Immediate ops: ORI, ANDI, SUBI, ADDI, EORI, CMPI
                names = {0x00: 'ORI', 0x02: 'ANDI', 0x04: 'SUBI',
                         0x06: 'ADDI', 0x0A: 'EORI', 0x0C: 'CMPI'}
                sz = (w >> 6) & 3
                if sz > 2:
                    return addr, f'DC.W ${w:04X}', 2
                sz_name = _SIZE_NAMES[sz]
                if sz == 0:
                    imm = _read16(self.data, pos) & 0xFF
                    imm_s = f'#${imm:02X}'
                    pos += 2
                elif sz == 1:
                    imm = _read16(self.data, pos)
                    imm_s = f'#${imm:04X}'
                    pos += 2
                else:
                    imm = _read32(self.data, pos)
                    imm_s = f'#${imm:08X}'
                    pos += 4
                mode = (w >> 3) & 7
                reg = w & 7
                # Check for SR/CCR destination
                if mode == 7 and reg == 4:
                    return addr, f'{names[op_hi]}{sz_name} {imm_s},SR', pos - offset
                ea_s, ea_n = self._ea_str(mode, reg, sz, pos)
                return addr, f'{names[op_hi]}{sz_name} {imm_s},{ea_s}', pos - offset + ea_n
            if op_hi == 0x08:
                # Static bit operations: BTST/BCHG/BCLR/BSET #imm,<ea>
                op_type = (w >> 6) & 3
                names = ['BTST', 'BCHG', 'BCLR', 'BSET']
                bit_num = _read16(self.data, pos) & 0xFF
                pos += 2
                mode = (w >> 3) & 7
                reg = w & 7
                ea_s, ea_n = self._ea_str(mode, reg, 0, pos)
                return addr, f'{names[op_type]} #${bit_num:02X},{ea_s}', pos - offset + ea_n

        # ── Line 1/2/3: MOVE ──
        if top4 in (1, 2, 3):
            sz_map = {1: 0, 3: 1, 2: 2}  # 1=byte, 3=word, 2=long
            sz = sz_map[top4]
            sz_name = _SIZE_NAMES[sz]
            dst_reg = (w >> 9) & 7
            dst_mode = (w >> 6) & 7
            src_mode = (w >> 3) & 7
            src_reg = w & 7
            src_s, src_n = self._ea_str(src_mode, src_reg, sz, pos)
            pos += src_n
            # MOVEA has dst_mode == 1
            if dst_mode == 1:
                dst_s = _AN[dst_reg]
                mne = f'MOVEA{sz_name}'
            else:
                dst_s, dst_n = self._ea_str(dst_mode, dst_reg, sz, pos)
                pos += dst_n
                mne = f'MOVE{sz_name}'
            return addr, f'{mne} {src_s},{dst_s}', pos - offset

        # ── Line 4: Misc (CLR, NEG, NOT, TST, LEA, PEA, JMP, JSR, MOVEM, SWAP, EXT, TRAP, LINK, UNLK, RTS, RTE, NOP) ──
        if top4 == 4:
            # LEA
            if (w & 0x01C0) == 0x01C0:
                an = (w >> 9) & 7
                mode = (w >> 3) & 7
                reg = w & 7
                ea_s, ea_n = self._ea_str(mode, reg, 2, pos)
                return addr, f'LEA {ea_s},{_AN[an]}', 2 + ea_n
            # CHK
            if (w & 0x01C0) == 0x0180:
                dn = (w >> 9) & 7
                mode = (w >> 3) & 7
                reg = w & 7
                ea_s, ea_n = self._ea_str(mode, reg, 1, pos)
                return addr, f'CHK {ea_s},{_DN[dn]}', 2 + ea_n
            # SWAP
            if (w & 0xFFF8) == 0x4840:
                return addr, f'SWAP {_DN[w & 7]}', 2
            # PEA
            if (w & 0xFFC0) == 0x4840:
                mode = (w >> 3) & 7
                reg = w & 7
                ea_s, ea_n = self._ea_str(mode, reg, 2, pos)
                return addr, f'PEA {ea_s}', 2 + ea_n
            # EXT
            if (w & 0xFFF8) == 0x4880:
                return addr, f'EXT.W {_DN[w & 7]}', 2
            if (w & 0xFFF8) == 0x48C0:
                return addr, f'EXT.L {_DN[w & 7]}', 2
            # MOVEM
            if (w & 0xFB80) == 0x4880:
                direction = (w >> 10) & 1  # 0=reg-to-mem, 1=mem-to-reg
                sz = 2 if (w & 0x0040) else 1
                sz_name = '.L' if sz == 2 else '.W'
                mask = _read16(self.data, pos)
                pos += 2
                mode = (w >> 3) & 7
                reg = w & 7
                ea_s, ea_n = self._ea_str(mode, reg, sz, pos)
                pos += ea_n
                regs = self._movem_regs(mask, mode == 4)
                if direction == 0:
                    return addr, f'MOVEM{sz_name} {regs},{ea_s}', pos - offset
                else:
                    return addr, f'MOVEM{sz_name} {ea_s},{regs}', pos - offset
            # TST
            if (w & 0xFF00) == 0x4A00:
                sz = (w >> 6) & 3
                if sz <= 2:
                    mode = (w >> 3) & 7
                    reg = w & 7
                    ea_s, ea_n = self._ea_str(mode, reg, sz, pos)
                    return addr, f'TST{_SIZE_NAMES[sz]} {ea_s}', 2 + ea_n
            # TAS
            if (w & 0xFFC0) == 0x4AC0:
                mode = (w >> 3) & 7
                reg = w & 7
                ea_s, ea_n = self._ea_str(mode, reg, 0, pos)
                return addr, f'TAS {ea_s}', 2 + ea_n
            # CLR
            if (w & 0xFF00) == 0x4200:
                sz = (w >> 6) & 3
                if sz <= 2:
                    mode = (w >> 3) & 7
                    reg = w & 7
                    ea_s, ea_n = self._ea_str(mode, reg, sz, pos)
                    return addr, f'CLR{_SIZE_NAMES[sz]} {ea_s}', 2 + ea_n
            # NEG
            if (w & 0xFF00) == 0x4400:
                sz = (w >> 6) & 3
                if sz <= 2:
                    mode = (w >> 3) & 7
                    reg = w & 7
                    ea_s, ea_n = self._ea_str(mode, reg, sz, pos)
                    return addr, f'NEG{_SIZE_NAMES[sz]} {ea_s}', 2 + ea_n
            # NEGX
            if (w & 0xFF00) == 0x4000:
                sz = (w >> 6) & 3
                if sz <= 2:
                    mode = (w >> 3) & 7
                    reg = w & 7
                    ea_s, ea_n = self._ea_str(mode, reg, sz, pos)
                    return addr, f'NEGX{_SIZE_NAMES[sz]} {ea_s}', 2 + ea_n
            # NOT
            if (w & 0xFF00) == 0x4600:
                sz = (w >> 6) & 3
                if sz <= 2:
                    mode = (w >> 3) & 7
                    reg = w & 7
                    ea_s, ea_n = self._ea_str(mode, reg, sz, pos)
                    return addr, f'NOT{_SIZE_NAMES[sz]} {ea_s}', 2 + ea_n
            # TRAP
            if (w & 0xFFF0) == 0x4E40:
                return addr, f'TRAP #{w & 0xF}', 2
            # LINK
            if (w & 0xFFF8) == 0x4E50:
                d16 = _sign16(_read16(self.data, pos))
                return addr, f'LINK {_AN[w & 7]},#{d16}', 4
            # UNLK
            if (w & 0xFFF8) == 0x4E58:
                return addr, f'UNLK {_AN[w & 7]}', 2
            # MOVE USP
            if (w & 0xFFF0) == 0x4E60:
                an = _AN[w & 7]
                if w & 8:
                    return addr, f'MOVE USP,{an}', 2
                return addr, f'MOVE {an},USP', 2
            # RESET, NOP, STOP, RTE, RTS, TRAPV
            specials = {0x4E70: 'RESET', 0x4E71: 'NOP', 0x4E73: 'RTE',
                        0x4E75: 'RTS', 0x4E76: 'TRAPV'}
            if w in specials:
                return addr, specials[w], 2
            if w == 0x4E72:  # STOP
                imm = _read16(self.data, pos)
                return addr, f'STOP #${imm:04X}', 4
            # JSR
            if (w & 0xFFC0) == 0x4E80:
                mode = (w >> 3) & 7
                reg = w & 7
                ea_s, ea_n = self._ea_str(mode, reg, 2, pos)
                return addr, f'JSR {ea_s}', 2 + ea_n
            # JMP
            if (w & 0xFFC0) == 0x4EC0:
                mode = (w >> 3) & 7
                reg = w & 7
                ea_s, ea_n = self._ea_str(mode, reg, 2, pos)
                return addr, f'JMP {ea_s}', 2 + ea_n

        # ── Line 5: ADDQ, SUBQ, Scc, DBcc ──
        if top4 == 5:
            if (w & 0x00C0) == 0x00C0:
                cc = (w >> 8) & 0xF
                mode = (w >> 3) & 7
                reg = w & 7
                if mode == 1:  # DBcc
                    d16 = _sign16(_read16(self.data, pos))
                    target = addr + 2 + d16
                    return addr, f'DB{_CC_NAMES[cc]} {_DN[reg]},${target & 0xFFFFFFFF:08X}', 4
                else:  # Scc
                    ea_s, ea_n = self._ea_str(mode, reg, 0, pos)
                    return addr, f'S{_CC_NAMES[cc]} {ea_s}', 2 + ea_n
            else:
                # ADDQ/SUBQ
                data_val = (w >> 9) & 7
                if data_val == 0:
                    data_val = 8
                sz = (w >> 6) & 3
                mode = (w >> 3) & 7
                reg = w & 7
                ea_s, ea_n = self._ea_str(mode, reg, sz, pos)
                op = 'SUBQ' if w & 0x0100 else 'ADDQ'
                return addr, f'{op}{_SIZE_NAMES[sz]} #{data_val},{ea_s}', 2 + ea_n

        # ── Line 6: Bcc, BSR, BRA ──
        if top4 == 6:
            cc = (w >> 8) & 0xF
            disp = w & 0xFF
            if disp == 0:
                disp = _sign16(_read16(self.data, pos))
                target = addr + 2 + disp
                inst_len = 4
            else:
                disp = _sign8(disp)
                target = addr + 2 + disp
                inst_len = 2
            if cc == 0:
                mne = 'BRA'
            elif cc == 1:
                mne = 'BSR'
            else:
                mne = f'B{_CC_NAMES[cc]}'
            return addr, f'{mne} ${target & 0xFFFFFFFF:08X}', inst_len

        # ── Line 7: MOVEQ ──
        if top4 == 7:
            dn = (w >> 9) & 7
            val = _sign8(w & 0xFF)
            if val < 0:
                return addr, f'MOVEQ #-${(-val) & 0xFF:02X},{_DN[dn]}', 2
            return addr, f'MOVEQ #${val:02X},{_DN[dn]}', 2

        # ── Line 8: OR, DIVU, DIVS, SBCD ──
        if top4 == 8:
            if (w & 0x01C0) == 0x00C0:
                # DIVU
                dn = (w >> 9) & 7
                mode = (w >> 3) & 7
                reg = w & 7
                ea_s, ea_n = self._ea_str(mode, reg, 1, pos)
                return addr, f'DIVU {ea_s},{_DN[dn]}', 2 + ea_n
            if (w & 0x01C0) == 0x01C0:
                # DIVS
                dn = (w >> 9) & 7
                mode = (w >> 3) & 7
                reg = w & 7
                ea_s, ea_n = self._ea_str(mode, reg, 1, pos)
                return addr, f'DIVS {ea_s},{_DN[dn]}', 2 + ea_n
            if (w & 0x01F0) == 0x0100:
                # SBCD
                ry = w & 7
                rx = (w >> 9) & 7
                if w & 8:
                    return addr, f'SBCD -({_AN[ry]}),-({_AN[rx]})', 2
                return addr, f'SBCD {_DN[ry]},{_DN[rx]}', 2
            # OR
            dn = (w >> 9) & 7
            sz = (w >> 6) & 3
            if sz > 2:
                return addr, f'DC.W ${w:04X}', 2
            mode = (w >> 3) & 7
            reg = w & 7
            ea_s, ea_n = self._ea_str(mode, reg, sz, pos)
            if w & 0x0100:
                return addr, f'OR{_SIZE_NAMES[sz]} {_DN[dn]},{ea_s}', 2 + ea_n
            return addr, f'OR{_SIZE_NAMES[sz]} {ea_s},{_DN[dn]}', 2 + ea_n

        # ── Line 9: SUB, SUBA, SUBX ──
        if top4 == 9:
            if (w & 0x00C0) == 0x00C0 and ((w >> 6) & 7) in (3, 7):
                # SUBA
                an = (w >> 9) & 7
                sz = 2 if (w & 0x0100) else 1
                mode = (w >> 3) & 7
                reg = w & 7
                ea_s, ea_n = self._ea_str(mode, reg, sz, pos)
                return addr, f'SUBA{".L" if sz == 2 else ".W"} {ea_s},{_AN[an]}', 2 + ea_n
            if (w & 0x0130) == 0x0100 and (w & 0x00C0) != 0x00C0:
                # SUBX
                ry = w & 7
                rx = (w >> 9) & 7
                sz = (w >> 6) & 3
                if w & 8:
                    return addr, f'SUBX{_SIZE_NAMES[sz]} -({_AN[ry]}),-({_AN[rx]})', 2
                return addr, f'SUBX{_SIZE_NAMES[sz]} {_DN[ry]},{_DN[rx]}', 2
            # SUB
            dn = (w >> 9) & 7
            sz = (w >> 6) & 3
            if sz > 2:
                return addr, f'DC.W ${w:04X}', 2
            mode = (w >> 3) & 7
            reg = w & 7
            ea_s, ea_n = self._ea_str(mode, reg, sz, pos)
            if w & 0x0100:
                return addr, f'SUB{_SIZE_NAMES[sz]} {_DN[dn]},{ea_s}', 2 + ea_n
            return addr, f'SUB{_SIZE_NAMES[sz]} {ea_s},{_DN[dn]}', 2 + ea_n

        # ── Line A: Line-A trap ──
        if top4 == 0xA:
            return addr, f'LINE-A ${w:04X}', 2

        # ── Line B: CMP, CMPA, CMPM, EOR ──
        if top4 == 0xB:
            if (w & 0x00C0) == 0x00C0 and ((w >> 6) & 7) in (3, 7):
                # CMPA
                an = (w >> 9) & 7
                sz = 2 if (w & 0x0100) else 1
                mode = (w >> 3) & 7
                reg = w & 7
                ea_s, ea_n = self._ea_str(mode, reg, sz, pos)
                return addr, f'CMPA{".L" if sz == 2 else ".W"} {ea_s},{_AN[an]}', 2 + ea_n
            if (w & 0x0100) and ((w >> 3) & 7) == 1:
                # CMPM
                ax = w & 7
                ay = (w >> 9) & 7
                sz = (w >> 6) & 3
                return addr, f'CMPM{_SIZE_NAMES[sz]} ({_AN[ax]})+,({_AN[ay]})+', 2
            if (w & 0x0100):
                # EOR
                dn = (w >> 9) & 7
                sz = (w >> 6) & 3
                if sz > 2:
                    return addr, f'DC.W ${w:04X}', 2
                mode = (w >> 3) & 7
                reg = w & 7
                ea_s, ea_n = self._ea_str(mode, reg, sz, pos)
                return addr, f'EOR{_SIZE_NAMES[sz]} {_DN[dn]},{ea_s}', 2 + ea_n
            # CMP
            dn = (w >> 9) & 7
            sz = (w >> 6) & 3
            if sz > 2:
                return addr, f'DC.W ${w:04X}', 2
            mode = (w >> 3) & 7
            reg = w & 7
            ea_s, ea_n = self._ea_str(mode, reg, sz, pos)
            return addr, f'CMP{_SIZE_NAMES[sz]} {ea_s},{_DN[dn]}', 2 + ea_n

        # ── Line C: AND, MULU, MULS, ABCD, EXG ──
        if top4 == 0xC:
            if (w & 0x01C0) == 0x00C0:
                # MULU
                dn = (w >> 9) & 7
                mode = (w >> 3) & 7
                reg = w & 7
                ea_s, ea_n = self._ea_str(mode, reg, 1, pos)
                return addr, f'MULU {ea_s},{_DN[dn]}', 2 + ea_n
            if (w & 0x01C0) == 0x01C0:
                # MULS
                dn = (w >> 9) & 7
                mode = (w >> 3) & 7
                reg = w & 7
                ea_s, ea_n = self._ea_str(mode, reg, 1, pos)
                return addr, f'MULS {ea_s},{_DN[dn]}', 2 + ea_n
            if (w & 0x01F0) == 0x0100:
                # ABCD
                ry = w & 7
                rx = (w >> 9) & 7
                if w & 8:
                    return addr, f'ABCD -({_AN[ry]}),-({_AN[rx]})', 2
                return addr, f'ABCD {_DN[ry]},{_DN[rx]}', 2
            if (w & 0x01F8) in (0x0140, 0x0148, 0x0188):
                # EXG
                rx = (w >> 9) & 7
                ry = w & 7
                opmode = (w >> 3) & 0x1F
                if opmode == 0x08:
                    return addr, f'EXG {_DN[rx]},{_DN[ry]}', 2
                elif opmode == 0x09:
                    return addr, f'EXG {_AN[rx]},{_AN[ry]}', 2
                else:
                    return addr, f'EXG {_DN[rx]},{_AN[ry]}', 2
            # AND
            dn = (w >> 9) & 7
            sz = (w >> 6) & 3
            if sz > 2:
                return addr, f'DC.W ${w:04X}', 2
            mode = (w >> 3) & 7
            reg = w & 7
            ea_s, ea_n = self._ea_str(mode, reg, sz, pos)
            if w & 0x0100:
                return addr, f'AND{_SIZE_NAMES[sz]} {_DN[dn]},{ea_s}', 2 + ea_n
            return addr, f'AND{_SIZE_NAMES[sz]} {ea_s},{_DN[dn]}', 2 + ea_n

        # ── Line D: ADD, ADDA, ADDX ──
        if top4 == 0xD:
            if (w & 0x00C0) == 0x00C0 and ((w >> 6) & 7) in (3, 7):
                # ADDA
                an = (w >> 9) & 7
                sz = 2 if (w & 0x0100) else 1
                mode = (w >> 3) & 7
                reg = w & 7
                ea_s, ea_n = self._ea_str(mode, reg, sz, pos)
                return addr, f'ADDA{".L" if sz == 2 else ".W"} {ea_s},{_AN[an]}', 2 + ea_n
            if (w & 0x0130) == 0x0100 and (w & 0x00C0) != 0x00C0:
                # ADDX
                ry = w & 7
                rx = (w >> 9) & 7
                sz = (w >> 6) & 3
                if w & 8:
                    return addr, f'ADDX{_SIZE_NAMES[sz]} -({_AN[ry]}),-({_AN[rx]})', 2
                return addr, f'ADDX{_SIZE_NAMES[sz]} {_DN[ry]},{_DN[rx]}', 2
            # ADD
            dn = (w >> 9) & 7
            sz = (w >> 6) & 3
            if sz > 2:
                return addr, f'DC.W ${w:04X}', 2
            mode = (w >> 3) & 7
            reg = w & 7
            ea_s, ea_n = self._ea_str(mode, reg, sz, pos)
            if w & 0x0100:
                return addr, f'ADD{_SIZE_NAMES[sz]} {_DN[dn]},{ea_s}', 2 + ea_n
            return addr, f'ADD{_SIZE_NAMES[sz]} {ea_s},{_DN[dn]}', 2 + ea_n

        # ── Line E: Shifts / Rotates ──
        if top4 == 0xE:
            if (w & 0x00C0) == 0x00C0:
                # Memory shift/rotate (word only)
                op_type = (w >> 9) & 3
                direction = 'L' if (w & 0x0100) else 'R'
                names = ['AS', 'LS', 'ROX', 'RO']
                mode = (w >> 3) & 7
                reg = w & 7
                ea_s, ea_n = self._ea_str(mode, reg, 1, pos)
                return addr, f'{names[op_type]}{direction}.W {ea_s}', 2 + ea_n
            # Register shift/rotate
            sz = (w >> 6) & 3
            if sz > 2:
                return addr, f'DC.W ${w:04X}', 2
            op_type = (w >> 3) & 3
            direction = 'L' if (w & 0x0100) else 'R'
            names = ['AS', 'LS', 'ROX', 'RO']
            dn = w & 7
            if w & 0x20:
                cnt = _DN[(w >> 9) & 7]
            else:
                cnt = (w >> 9) & 7
                if cnt == 0:
                    cnt = 8
                cnt = f'#{cnt}'
            return addr, f'{names[op_type]}{direction}{_SIZE_NAMES[sz]} {cnt},{_DN[dn]}', 2

        # ── Line F: Line-F trap ──
        if top4 == 0xF:
            return addr, f'LINE-F ${w:04X}', 2

        return addr, f'DC.W ${w:04X}', 2

    def _movem_regs(self, mask, predec):
        """Format MOVEM register list."""
        if predec:
            # Reversed bit order for -(An)
            bits = [(mask >> (15 - i)) & 1 for i in range(16)]
        else:
            bits = [(mask >> i) & 1 for i in range(16)]
        names = _DN + [_AN[i] for i in range(8)]
        parts = []
        i = 0
        while i < 16:
            if bits[i]:
                start = i
                while i + 1 < 16 and bits[i + 1]:
                    i += 1
                if i == start:
                    parts.append(names[start])
                else:
                    parts.append(f'{names[start]}-{names[i]}')
            i += 1
        return '/'.join(parts) if parts else '???'

    def disasm_range(self, start, end):
        """Disassemble a range of bytes. Yields (addr, mnemonic, num_bytes)."""
        off = start
        while off < end and off < len(self.data):
            a, m, n = self.disasm_one(off)
            yield a, m, n
            off += n

    def xref_search(self, target_addr, code_start=0, code_end=None):
        """Find instructions that reference a target address.
        Searches for: immediate operands, branch targets, d16(PC) refs,
        and absolute address references."""
        if code_end is None:
            code_end = len(self.data)
        results = []
        off = code_start
        while off < code_end:
            a, m, n = self.disasm_one(off)
            # Check if the mnemonic references target_addr
            target_hex = f'${target_addr:08X}'
            target_hex_short = f'${target_addr:04X}'
            if target_hex in m or target_hex_short in m:
                results.append((a, m, n))
            off += n
        return results

    def find_pattern(self, pattern_words, code_start=0, code_end=None):
        """Find occurrences of a word pattern (list of 16-bit ints, None = wildcard)."""
        if code_end is None:
            code_end = len(self.data) - len(pattern_words) * 2
        results = []
        for off in range(code_start, code_end, 2):
            match = True
            for i, pw in enumerate(pattern_words):
                if pw is not None:
                    w = _read16(self.data, off + i * 2)
                    if w != pw:
                        match = False
                        break
            if match:
                results.append(off + self.base)
        return results


# ─── GUI ─────────────────────────────────────────────────────────────

class PMSaveDiskToolApp:
    def __init__(self, root):
        self.root = root
        self.root.title("PM Save Disk Tool")
        self.root.geometry("1060x800")

        self.adf = None
        self.dir_entries = []
        self.liga_names = []      # Canonical team names from LigaName.nam
        self.current_save = None
        self.current_team = None
        self.game_disk = None     # GameDisk instance (auto-loaded from script dir)

        self._build_menu()
        self._build_ui()

        # Auto-load game disk if found next to the script
        game_path = _find_game_disk()
        if game_path:
            try:
                self.game_disk = GameDisk(game_path)
                n = len(self.game_disk.player_names)
                self.status_var.set(
                    f"Game disk loaded: {os.path.basename(game_path)} — "
                    f"{n} player names extracted")
            except Exception as e:
                self.status_var.set(f"Game disk error: {e}")

    # ── Menu ──

    def _build_menu(self):
        menubar = tk.Menu(self.root)

        file_menu = tk.Menu(menubar, tearoff=0)
        file_menu.add_command(label="Open ADF…", command=self.open_adf, accelerator=f"{_MOD_DISP}O")
        file_menu.add_command(label="Save ADF", command=self.save_adf, accelerator=f"{_MOD_DISP}S")
        file_menu.add_command(label="Save ADF As…", command=self.save_adf_as, accelerator=f"{_MOD_DISP}Shift+S")
        file_menu.add_separator()
        file_menu.add_command(label="Export Save as Binary…", command=self.export_save)
        file_menu.add_separator()
        file_menu.add_command(label="Quit", command=self.root.quit, accelerator=f"{_MOD_DISP}Q")
        menubar.add_cascade(label="File", menu=file_menu)

        tools_menu = tk.Menu(menubar, tearoff=0)
        tools_menu.add_command(label="Hex Viewer…", command=self.hex_viewer)
        tools_menu.add_command(label="Disk Info", command=self.show_disk_info)
        tools_menu.add_separator()
        tools_menu.add_command(label="Patch Composer…", command=self.open_patch_composer)
        tools_menu.add_separator()
        tools_menu.add_command(label="League Tables…", command=self.show_league_tables)
        tools_menu.add_command(label="Compare Saves…", command=self.show_compare_saves)
        tools_menu.add_command(label="Championship Highlights…", command=self.show_highlights)
        tools_menu.add_separator()
        tools_menu.add_command(label="Tactics Viewer…", command=self.show_tactics_viewer)
        tools_menu.add_command(label="Disassembler…", command=self.show_disassembler)
        menubar.add_cascade(label="Tools", menu=tools_menu)

        self.root.config(menu=menubar)

        # Key bindings
        self.root.bind_all(f'<{_MOD}-o>', lambda e: self.open_adf())
        self.root.bind_all(f'<{_MOD}-s>', lambda e: self.save_adf())

    # ── Layout ──

    def _build_ui(self):
        # Top: filename
        top = ttk.Frame(self.root)
        top.pack(fill=tk.X, padx=8, pady=(8, 0))

        ttk.Button(top, text="Open ADF", command=self.open_adf).pack(side=tk.LEFT)
        ttk.Button(top, text="Save", command=self.save_adf).pack(side=tk.LEFT, padx=(4, 0))
        self.filename_var = tk.StringVar(value="No file loaded")
        ttk.Label(top, textvariable=self.filename_var, foreground="gray").pack(
            side=tk.LEFT, padx=(12, 0))

        # Main PanedWindow: left = saves/teams, right = details
        pw = ttk.PanedWindow(self.root, orient=tk.HORIZONTAL)
        pw.pack(fill=tk.BOTH, expand=True, padx=8, pady=8)

        # Left panel: saves + teams
        left = ttk.Frame(pw, width=280)
        pw.add(left, weight=1)

        # Save slots
        saves_frame = ttk.LabelFrame(left, text="Save Slots")
        saves_frame.pack(fill=tk.X, padx=4, pady=4)
        self.saves_listbox = tk.Listbox(saves_frame, height=5, exportselection=False)
        self.saves_listbox.pack(fill=tk.X, padx=4, pady=4)
        self.saves_listbox.bind('<<ListboxSelect>>', self.on_save_select)

        # Teams
        teams_frame = ttk.LabelFrame(left, text="Teams")
        teams_frame.pack(fill=tk.BOTH, expand=True, padx=4, pady=4)

        cols = ("idx", "name", "div")
        self.teams_tree = ttk.Treeview(teams_frame, columns=cols, show='headings', height=15)
        self.teams_tree.heading("idx", text="#")
        self.teams_tree.heading("name", text="Team Name")
        self.teams_tree.heading("div", text="Div")
        self.teams_tree.column("idx", width=30, anchor='center')
        self.teams_tree.column("name", width=180)
        self.teams_tree.column("div", width=40, anchor='center')
        self.teams_tree.pack(fill=tk.BOTH, expand=True, padx=4, pady=4)
        self.teams_tree.bind('<<TreeviewSelect>>', self.on_team_select)

        scrollbar = ttk.Scrollbar(teams_frame, orient='vertical',
                                  command=self.teams_tree.yview)
        self.teams_tree.configure(yscrollcommand=scrollbar.set)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        # Right panel: team details
        right = ttk.Frame(pw, width=640)
        pw.add(right, weight=3)

        # Right panel is scrollable
        right_canvas = tk.Canvas(right)
        right_scroll = ttk.Scrollbar(right, orient='vertical', command=right_canvas.yview)
        right_inner = ttk.Frame(right_canvas)

        right_inner.bind('<Configure>',
                         lambda e: right_canvas.configure(scrollregion=right_canvas.bbox('all')))
        right_canvas.create_window((0, 0), window=right_inner, anchor='nw')
        right_canvas.configure(yscrollcommand=right_scroll.set)

        right_canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        right_scroll.pack(side=tk.RIGHT, fill=tk.Y)

        # Team info section
        info_frame = ttk.LabelFrame(right_inner, text="Team Info")
        info_frame.pack(fill=tk.X, padx=4, pady=4)

        info_grid = ttk.Frame(info_frame)
        info_grid.pack(fill=tk.X, padx=8, pady=8)

        self.team_name_var = tk.StringVar()
        self.division_var = tk.StringVar()
        self.word62_var = tk.StringVar()
        self.word64_var = tk.StringVar()

        row = 0
        ttk.Label(info_grid, text="Team Name:").grid(row=row, column=0, sticky='e', padx=4, pady=2)
        ttk.Entry(info_grid, textvariable=self.team_name_var, width=24).grid(
            row=row, column=1, sticky='w', padx=4)

        ttk.Label(info_grid, text="Division:").grid(row=row, column=2, sticky='e', padx=4)
        div_combo = ttk.Combobox(info_grid, textvariable=self.division_var, width=12,
                                 values=["0 (Div 1)", "1 (Div 2)", "2 (Div 3)", "3 (Div 4)"])
        div_combo.grid(row=row, column=3, sticky='w', padx=4)

        row += 1
        ttk.Label(info_grid, text="Team Value:").grid(row=row, column=0, sticky='e', padx=4, pady=2)
        ttk.Entry(info_grid, textvariable=self.word62_var, width=8).grid(
            row=row, column=1, sticky='w', padx=4)
        ttk.Label(info_grid, text="Budget Tier:").grid(row=row, column=2, sticky='e', padx=4)
        ttk.Entry(info_grid, textvariable=self.word64_var, width=8).grid(
            row=row, column=3, sticky='w', padx=4)

        row += 1
        ttk.Button(info_grid, text="Apply Changes", command=self.apply_team_changes).grid(
            row=row, column=0, columnspan=2, pady=8)
        ttk.Button(info_grid, text="Become Manager of This Team",
                   command=self.become_manager).grid(row=row, column=2, columnspan=2, pady=8)

        # League stats section
        stats_frame = ttk.LabelFrame(right_inner, text="League Stats")
        stats_frame.pack(fill=tk.X, padx=4, pady=4)

        stats_grid = ttk.Frame(stats_frame)
        stats_grid.pack(fill=tk.X, padx=8, pady=8)

        self.stat_vars = []
        stat_labels = TeamRecord.STAT_LABELS
        for i, label in enumerate(stat_labels):
            ttk.Label(stats_grid, text=f"{label}:").grid(
                row=i // 3, column=(i % 3) * 2, sticky='e', padx=4, pady=2)
            var = tk.StringVar()
            self.stat_vars.append(var)
            ttk.Entry(stats_grid, textvariable=var, width=8).grid(
                row=i // 3, column=(i % 3) * 2 + 1, sticky='w', padx=4)

        # Player IDs section (25 slots)
        pv_frame = ttk.LabelFrame(right_inner, text="Player IDs (up to 25 roster slots, FFFF = empty)")
        pv_frame.pack(fill=tk.X, padx=4, pady=4)

        pv_grid = ttk.Frame(pv_frame)
        pv_grid.pack(fill=tk.X, padx=8, pady=8)

        self.pv_vars = []
        for i in range(MAX_PLAYER_SLOTS):
            r, c = divmod(i, 5)
            ttk.Label(pv_grid, text=f"P{i:02d}:").grid(row=r, column=c * 2, sticky='e', padx=2, pady=1)
            var = tk.StringVar()
            self.pv_vars.append(var)
            ttk.Entry(pv_grid, textvariable=var, width=14).grid(
                row=r, column=c * 2 + 1, sticky='w', padx=2)

        # Hex dump section
        hex_frame = ttk.LabelFrame(right_inner, text="Raw Record Hex (100 bytes)")
        hex_frame.pack(fill=tk.BOTH, expand=True, padx=4, pady=4)

        self.hex_text = tk.Text(hex_frame, height=8, font=(_MONO, 11), state='disabled',
                                wrap='none', bg='#1e1e1e', fg='#d4d4d4',
                                insertbackground='white')
        self.hex_text.pack(fill=tk.BOTH, expand=True, padx=4, pady=4)

        # Status bar
        self.status_var = tk.StringVar(value="Ready — Open an ADF to begin")
        ttk.Label(self.root, textvariable=self.status_var, relief='sunken',
                  anchor='w').pack(fill=tk.X, side=tk.BOTTOM, padx=2, pady=2)

    # ── File operations ──

    def open_adf(self):
        path = filedialog.askopenfilename(
            title="Open Player Manager ADF",
            filetypes=[("ADF files", "*.adf"), ("All files", "*.*")]
        )
        if not path:
            return

        try:
            self.adf = ADF(path)
        except Exception as e:
            messagebox.showerror("Error", f"Could not open file:\n{e}")
            return

        self.filename_var.set(os.path.basename(path))

        # Check if it's a save disk by looking at sector 2 for the file table
        try:
            self.dir_entries = parse_file_table(self.adf)
        except Exception:
            self.dir_entries = []

        if not self.dir_entries:
            messagebox.showinfo("Info",
                "No save file table found in sector 2.\n"
                "This may be a game disk, not a save/data disk.\n\n"
                "Use Tools → Hex Viewer to inspect the disk.")
            self.status_var.set(f"Loaded: {os.path.basename(path)} ({self.adf.filesystem_type}) — no save table found")
            return

        # Load canonical team names
        self.liga_names = parse_liga_names(self.adf, self.dir_entries)

        # Populate save slots (include .sav and .dat files)
        self.saves_listbox.delete(0, tk.END)
        save_entries = [e for e in self.dir_entries
                        if e.name.endswith('.sav') or e.name.endswith('.dat')]
        for e in save_entries:
            tag = " [template]" if e.name.endswith('.dat') else ""
            self.saves_listbox.insert(tk.END, f"{e.name}  ({e.size_bytes} bytes){tag}")

        self.status_var.set(
            f"Loaded: {os.path.basename(path)} ({self.adf.filesystem_type}) — "
            f"{len(self.dir_entries)} files, {len(save_entries)} saves"
            f"{', ' + str(len(self.liga_names)) + ' team names' if self.liga_names else ''}")

    def save_adf(self):
        if not self.adf:
            return
        try:
            self.adf.save()
            self.status_var.set(f"Saved: {os.path.basename(self.adf.path)}")
        except Exception as e:
            messagebox.showerror("Error", f"Could not save:\n{e}")

    def save_adf_as(self):
        if not self.adf:
            return
        path = filedialog.asksaveasfilename(
            title="Save ADF As",
            defaultextension=".adf",
            filetypes=[("ADF files", "*.adf"), ("All files", "*.*")]
        )
        if path:
            try:
                self.adf.save(path)
                self.adf.path = path
                self.filename_var.set(os.path.basename(path))
                self.status_var.set(f"Saved as: {os.path.basename(path)}")
            except Exception as e:
                messagebox.showerror("Error", f"Could not save:\n{e}")

    def export_save(self):
        if not self.current_save:
            messagebox.showinfo("Info", "Select a save slot first.")
            return
        path = filedialog.asksaveasfilename(
            title="Export Save Data",
            defaultextension=".bin",
            initialfile=self.current_save.entry.name.replace('.sav', '.bin')
        )
        if path:
            with open(path, 'wb') as f:
                f.write(bytes(self.current_save.data))
            self.status_var.set(f"Exported {len(self.current_save.data)} bytes to {os.path.basename(path)}")

    # ── Selection handlers ──

    def on_save_select(self, event):
        sel = self.saves_listbox.curselection()
        if not sel:
            return
        idx = sel[0]
        save_entries = [e for e in self.dir_entries
                        if e.name.endswith('.sav') or e.name.endswith('.dat')]
        entry = save_entries[idx]

        try:
            self.current_save = SaveFile(self.adf, entry)
        except Exception as e:
            messagebox.showerror("Error", f"Could not parse save:\n{e}")
            return

        # Populate teams tree
        self.teams_tree.delete(*self.teams_tree.get_children())
        for team in self.current_save.teams:
            div = team.division
            div_str = str(div) if div is not None else "?"
            name = team.name if team.name else f"(record {team.index})"
            self.teams_tree.insert('', 'end', values=(team.index, name, div_str))

        self.status_var.set(
            f"Save: {entry.name} — {len(self.current_save.teams)} teams, "
            f"{entry.size_bytes} bytes")

    def on_team_select(self, event):
        sel = self.teams_tree.selection()
        if not sel or not self.current_save:
            return
        values = self.teams_tree.item(sel[0], 'values')
        idx = int(values[0])

        team = None
        for t in self.current_save.teams:
            if t.index == idx:
                team = t
                break
        if not team:
            return

        self.current_team = team
        self._display_team(team)

    def _display_team(self, team):
        self.team_name_var.set(team.name)
        div = team.division
        if div is not None:
            self.division_var.set(f"{div} (Div {div + 1})")
        else:
            self.division_var.set(f"{team.word_66:#06x}")
        self.word62_var.set(f"{team.team_value_signed}")
        self.word64_var.set(str(team.word_64))

        for i, var in enumerate(self.stat_vars):
            var.set(str(team.league_stats[i]))

        for i, var in enumerate(self.pv_vars):
            v = team.player_values[i]
            if v == 0xFFFF:
                var.set("FFFF")
            elif self.game_disk:
                name = self.game_disk.player_name(v)
                var.set(f"{v} {name}" if name else str(v))
            else:
                var.set(str(v))

        # Hex dump
        self.hex_text.config(state='normal')
        self.hex_text.delete('1.0', tk.END)

        hex_lines = []
        for i in range(0, len(team.raw), 16):
            chunk = team.raw[i:i + 16]
            hex_str = ' '.join(f'{b:02X}' for b in chunk)
            asc_str = ''.join(chr(b) if 32 <= b < 127 else '·' for b in chunk)
            hex_lines.append(f"+{i:03d}  {hex_str:<48s}  {asc_str}")

        self.hex_text.insert('1.0', '\n'.join(hex_lines))
        self.hex_text.config(state='disabled')

    # ── Editing ──

    def apply_team_changes(self):
        if not self.current_team or not self.current_save:
            return

        team = self.current_team

        # Team name
        new_name = self.team_name_var.get().strip()
        max_name_len = 100 - TEAM_NAME_OFFSET - 1
        if len(new_name) > max_name_len:
            messagebox.showwarning("Warning", f"Name too long (max {max_name_len} chars)")
            return
        team.name = new_name

        # Division
        try:
            div_str = self.division_var.get().strip()
            team.word_66 = int(div_str.split()[0])
        except (ValueError, IndexError):
            pass

        # Team value (signed → unsigned)
        try:
            v = int(self.word62_var.get().strip())
            team.word_62 = v & 0xFFFF
        except ValueError:
            pass

        # Budget tier
        try:
            team.word_64 = int(self.word64_var.get().strip())
        except ValueError:
            pass

        # League stats
        for i, var in enumerate(self.stat_vars):
            try:
                team.league_stats[i] = int(var.get().strip())
            except ValueError:
                pass

        # Player values (field may contain "123 Surname" — take first token)
        for i, var in enumerate(self.pv_vars):
            try:
                val = var.get().strip().split()[0].upper()
                if val == 'FFFF':
                    team.player_values[i] = 0xFFFF
                else:
                    team.player_values[i] = int(val, 16) if val.startswith('0X') else int(val)
            except (ValueError, IndexError):
                pass

        # Write back
        self.current_save.write_back()
        self._display_team(team)

        # Refresh tree
        for item in self.teams_tree.get_children():
            vals = self.teams_tree.item(item, 'values')
            if int(vals[0]) == team.index:
                self.teams_tree.item(item, values=(team.index, team.name, str(team.word_66)))
                break

        self.status_var.set(f"Applied changes to {team.name}")

    def become_manager(self):
        if not self.current_team:
            return
        messagebox.showinfo("Become Manager",
            f"To become manager of {self.current_team.name}:\n\n"
            f"This team is record #{self.current_team.index}.\n"
            f"The manager team assignment is stored in the game's runtime data.\n\n"
            f"For the Italian version, the manager team index can be patched\n"
            f"in the game disk's Patch block (block 1137).\n\n"
            f"Word 64 = {self.current_team.word_64:#06x} may be related to\n"
            f"team assignment in the save data.")

    # ── Tools ──

    def hex_viewer(self):
        if not self.adf:
            messagebox.showinfo("Info", "Open an ADF first.")
            return

        win = tk.Toplevel(self.root)
        win.title("Hex Viewer")
        win.geometry("820x600")

        ctrl = ttk.Frame(win)
        ctrl.pack(fill=tk.X, padx=8, pady=4)

        ttk.Label(ctrl, text="Sector:").pack(side=tk.LEFT)
        sector_var = tk.StringVar(value="0")
        sector_entry = ttk.Entry(ctrl, textvariable=sector_var, width=6)
        sector_entry.pack(side=tk.LEFT, padx=4)

        ttk.Label(ctrl, text="or Byte offset:").pack(side=tk.LEFT, padx=(8, 0))
        offset_var = tk.StringVar(value="")
        offset_entry = ttk.Entry(ctrl, textvariable=offset_var, width=10)
        offset_entry.pack(side=tk.LEFT, padx=4)

        ttk.Label(ctrl, text="Sectors:").pack(side=tk.LEFT, padx=(8, 0))
        count_var = tk.StringVar(value="2")
        ttk.Entry(ctrl, textvariable=count_var, width=4).pack(side=tk.LEFT, padx=4)

        text = tk.Text(win, font=(_MONO, 11), wrap='none',
                       bg='#1e1e1e', fg='#d4d4d4')
        text.pack(fill=tk.BOTH, expand=True, padx=8, pady=4)

        def do_dump():
            text.delete('1.0', tk.END)
            try:
                count = int(count_var.get())
                off_str = offset_var.get().strip()
                if off_str:
                    start = int(off_str, 0)
                    length = count * SECTOR_SIZE
                else:
                    sec = int(sector_var.get())
                    start = sec * SECTOR_SIZE
                    length = count * SECTOR_SIZE
            except ValueError:
                text.insert('1.0', 'Invalid input')
                return

            data = self.adf.read_bytes(start, min(length, ADF_SIZE - start))
            lines = []
            for i in range(0, len(data), 16):
                addr = start + i
                chunk = data[i:i + 16]
                hex_str = ' '.join(f'{b:02X}' for b in chunk)
                asc_str = ''.join(chr(b) if 32 <= b < 127 else '·' for b in chunk)
                lines.append(f"{addr:06X}  {hex_str:<48s}  {asc_str}")
            text.insert('1.0', '\n'.join(lines))

        ttk.Button(ctrl, text="Dump", command=do_dump).pack(side=tk.LEFT, padx=8)
        do_dump()

    def open_patch_composer(self):
        PatchComposerWindow(self.root, game_disk=self.game_disk)

    def show_league_tables(self):
        if not self.current_save:
            messagebox.showinfo("Info", "Select a save slot first.")
            return
        LeagueDashboardWindow(self.root, self.current_save, self.liga_names)

    def show_compare_saves(self):
        if not self.adf or not self.dir_entries:
            messagebox.showinfo("Info", "Open a save disk ADF first.")
            return
        CompareSavesDialog(self.root, self.adf, self.dir_entries,
                           game_disk=self.game_disk)

    def show_highlights(self):
        if not self.current_save:
            messagebox.showinfo("Info", "Select a save slot first.")
            return
        ChampionshipHighlightsWindow(
            self.root, self.current_save, self.adf,
            game_disk=self.game_disk, liga_names=self.liga_names)

    def show_disk_info(self):
        if not self.adf:
            messagebox.showinfo("Info", "Open an ADF first.")
            return

        info = [
            f"File: {os.path.basename(self.adf.path)}",
            f"Size: {len(self.adf.data)} bytes ({len(self.adf.data) // SECTOR_SIZE} sectors)",
            f"Filesystem: {self.adf.filesystem_type}",
            "",
            "File Table (sector 2):",
        ]

        if self.dir_entries:
            for e in self.dir_entries:
                info.append(f"  {e.name:<14s}  start={e.start_unit:#06x} "
                           f"(byte {e.byte_offset:6d})  size={e.size_bytes:5d}")
        else:
            info.append("  (none found)")

        if self.liga_names:
            info.append("")
            info.append(f"Canonical team names ({len(self.liga_names)}):")
            for i, name in enumerate(self.liga_names):
                info.append(f"  {i:2d}. {name}")

        # Show in a scrollable window instead of messagebox
        win = tk.Toplevel(self.root)
        win.title("Disk Info")
        win.geometry("500x600")
        text = tk.Text(win, font=(_MONO, 11), wrap='word')
        text.pack(fill=tk.BOTH, expand=True, padx=8, pady=8)
        text.insert('1.0', '\n'.join(info))
        text.config(state='disabled')

    def show_tactics_viewer(self):
        if not self.adf or not self.dir_entries:
            messagebox.showinfo("Info", "Open a save disk ADF first.")
            return
        tac_entries = [e for e in self.dir_entries if e.name.endswith('.tac')]
        if not tac_entries:
            messagebox.showinfo("Info", "No .tac files found on this disk.")
            return
        TacticsViewerWindow(self.root, self.adf, tac_entries)

    def show_disassembler(self):
        if not self.game_disk:
            messagebox.showinfo("Info",
                "No game disk loaded.\n\n"
                f"Place {_GAME_DISK_FILENAME} next to the script and restart.")
            return
        DisassemblerWindow(self.root, self.game_disk)


# ─── Patch Composer Window (Feature 1) ───────────────────────────────

class PatchComposerWindow(tk.Toplevel):
    """
    Standalone tool for editing block 1137 (the runtime Patch block) on the
    game disk ADF.  Opens a separate game-disk ADF, parses the callback's
    68000 patch instructions, lets you add / remove / preview patches, and
    writes back with a correct OFS checksum.
    """

    def __init__(self, parent, game_disk=None):
        super().__init__(parent)
        self.title("Patch Composer — Game Disk Block 1137")
        self.geometry("820x720")
        self.resizable(True, True)

        self._adf_path = None
        self._adf_data = None     # bytearray of the full ADF
        self._patches = []        # list[PatchEntry]

        self._build_ui()

        # Auto-load from pre-loaded game disk if available
        if game_disk is not None:
            self._adf_path = game_disk.path
            self._adf_data = bytearray(game_disk.adf_data)
            self._fname_var.set(os.path.basename(game_disk.path))
            sec_off = _PATCH_BLOCK_SECTOR * SECTOR_SIZE
            sector = bytes(self._adf_data[sec_off: sec_off + SECTOR_SIZE])
            self._patches = _parse_block1137(sector)
            self._refresh_list()

    # ── Build UI ──

    def _build_ui(self):
        # Top bar
        top = ttk.Frame(self)
        top.pack(fill=tk.X, padx=8, pady=6)
        ttk.Button(top, text="Open Game Disk ADF…",
                   command=self._open_adf).pack(side=tk.LEFT)
        self._fname_var = tk.StringVar(value="No game disk loaded")
        ttk.Label(top, textvariable=self._fname_var, foreground="gray").pack(
            side=tk.LEFT, padx=(10, 0))

        # Patch list
        lf = ttk.LabelFrame(self, text="Current Patches  (Block 1137, callback area)")
        lf.pack(fill=tk.BOTH, expand=True, padx=8, pady=4)

        cols = ("#", "Offset", "Size", "Value", "Description")
        self._tree = ttk.Treeview(lf, columns=cols, show='headings', height=10)
        self._tree.heading("#", text="#")
        self._tree.heading("Offset", text="Offset")
        self._tree.heading("Size", text="Size")
        self._tree.heading("Value", text="Value")
        self._tree.heading("Description", text="Description")
        self._tree.column("#", width=32, anchor='center')
        self._tree.column("Offset", width=90, anchor='center')
        self._tree.column("Size", width=44, anchor='center')
        self._tree.column("Value", width=120, anchor='center')
        self._tree.column("Description", width=400)

        vsb = ttk.Scrollbar(lf, orient='vertical', command=self._tree.yview)
        self._tree.configure(yscrollcommand=vsb.set)
        self._tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=4, pady=4)
        vsb.pack(side=tk.RIGHT, fill=tk.Y, pady=4)

        del_frame = ttk.Frame(self)
        del_frame.pack(fill=tk.X, padx=8)
        ttk.Button(del_frame, text="Delete Selected Patch",
                   command=self._delete_patch).pack(side=tk.LEFT, padx=4, pady=2)

        # Quick Patches
        qf = ttk.LabelFrame(self, text="Quick Patches")
        qf.pack(fill=tk.X, padx=8, pady=4)
        qg = ttk.Frame(qf)
        qg.pack(fill=tk.X, padx=8, pady=6)

        ttk.Label(qg, text="Manager Age:").grid(row=0, column=0, sticky='e', padx=4)
        self._age_var = tk.StringVar(value="18")
        ttk.Spinbox(qg, from_=16, to=99, textvariable=self._age_var,
                    width=5).grid(row=0, column=1, sticky='w', padx=4)
        ttk.Label(qg, text="displayed age; stored value = age − 1  "
                  "(WORD at $11740)").grid(row=0, column=2, sticky='w', padx=4)
        ttk.Button(qg, text="Apply Age Patch",
                   command=self._apply_age).grid(row=0, column=3, padx=12)

        # Custom Patch form
        cf = ttk.LabelFrame(self, text="Custom Patch")
        cf.pack(fill=tk.X, padx=8, pady=4)
        cg = ttk.Frame(cf)
        cg.pack(fill=tk.X, padx=8, pady=6)

        ttk.Label(cg, text="Offset (hex):").grid(row=0, column=0, sticky='e', padx=4)
        self._coff_var = tk.StringVar()
        ttk.Entry(cg, textvariable=self._coff_var, width=10).grid(
            row=0, column=1, sticky='w', padx=4)

        ttk.Label(cg, text="Size:").grid(row=0, column=2, sticky='e', padx=8)
        self._csize_var = tk.StringVar(value="B")
        for i, sz in enumerate(('B (byte)', 'W (word)', 'L (long)')):
            ttk.Radiobutton(cg, text=sz, value=sz[0],
                            variable=self._csize_var).grid(row=0, column=3 + i, padx=2)

        ttk.Label(cg, text="Value (hex):").grid(row=1, column=0, sticky='e', padx=4, pady=4)
        self._cval_var = tk.StringVar()
        ttk.Entry(cg, textvariable=self._cval_var, width=10).grid(
            row=1, column=1, sticky='w', padx=4)

        ttk.Label(cg, text="Description:").grid(row=1, column=2, sticky='e', padx=8)
        self._cdesc_var = tk.StringVar()
        ttk.Entry(cg, textvariable=self._cdesc_var, width=32).grid(
            row=1, column=3, sticky='w', padx=4, columnspan=3)

        ttk.Button(cg, text="Add Patch", command=self._add_patch).grid(
            row=2, column=0, columnspan=2, pady=6)

        # Space + action buttons
        bot = ttk.Frame(self)
        bot.pack(fill=tk.X, padx=8, pady=6)
        self._space_var = tk.StringVar(value="Space: open a game disk to begin")
        ttk.Label(bot, textvariable=self._space_var).pack(side=tk.LEFT)
        ttk.Button(bot, text="Write to Game Disk ADF",
                   command=self._write_adf).pack(side=tk.RIGHT, padx=4)
        ttk.Button(bot, text="Preview ASM",
                   command=self._preview_asm).pack(side=tk.RIGHT, padx=4)

    # ── File operations ──

    def _open_adf(self):
        path = filedialog.askopenfilename(
            parent=self, title="Open Game Disk ADF",
            filetypes=[("ADF files", "*.adf"), ("All files", "*.*")])
        if not path:
            return
        try:
            with open(path, 'rb') as f:
                data = bytearray(f.read())
            if len(data) != ADF_SIZE:
                raise ValueError(f"Expected {ADF_SIZE} bytes, got {len(data)}")
        except Exception as e:
            messagebox.showerror("Error", str(e), parent=self)
            return

        self._adf_path = path
        self._adf_data = data
        self._fname_var.set(os.path.basename(path))

        sec_off = _PATCH_BLOCK_SECTOR * SECTOR_SIZE
        sector = bytes(data[sec_off: sec_off + SECTOR_SIZE])
        self._patches = _parse_block1137(sector)
        self._refresh_list()

    # ── List management ──

    def _refresh_list(self):
        self._tree.delete(*self._tree.get_children())
        for i, p in enumerate(self._patches, 1):
            if p.size == 'L':
                val_str = f"LONG  ${p.value:08X}"
            elif p.size == 'W':
                val_str = f"WORD  ${p.value:04X}"
            else:
                val_str = f"BYTE  ${p.value:02X}"
            self._tree.insert('', 'end', iid=str(i - 1),
                              values=(i, f"${p.offset:06X}", p.size, val_str, p.description))
        self._update_space()

    def _update_space(self):
        used = sum(p.byte_size() for p in self._patches)
        avail = _MAX_PATCH_BYTES
        filled = int(used / avail * 20) if avail else 0
        bar = '█' * filled + '░' * (20 - filled)
        free_patches = (avail - used) // 12
        self._space_var.set(
            f"Space: {bar}  {used}/{avail} bytes  "
            f"({avail - used} free ≈ {free_patches} more byte/word patches)")

    def _delete_patch(self):
        sel = self._tree.selection()
        if not sel:
            return
        idx = int(sel[0])
        p = self._patches[idx]
        if p.offset in _COPYPROT_OFFSETS:
            if not messagebox.askyesno(
                    "Copy-Protection Patch",
                    f"Patch at ${p.offset:06X} is a copy-protection bypass.\n"
                    "Removing it will likely cause the game to crash.\n\n"
                    "Delete anyway?", parent=self):
                return
        del self._patches[idx]
        self._refresh_list()

    def _upsert_patch(self, offset, size, value, desc):
        """Update an existing patch at the same offset+size, or append a new one."""
        for p in self._patches:
            if p.offset == offset and p.size == size:
                p.value = value
                p.description = desc
                self._refresh_list()
                return
        new_p = PatchEntry(offset, size, value, desc)
        total = sum(q.byte_size() for q in self._patches) + new_p.byte_size()
        if total > _MAX_PATCH_BYTES:
            messagebox.showerror("No Space",
                f"Adding this patch would use {total}/{_MAX_PATCH_BYTES} bytes.",
                parent=self)
            return
        self._patches.append(new_p)
        self._refresh_list()

    # ── Quick Patches ──

    def _apply_age(self):
        try:
            age = int(self._age_var.get().strip())
            if not 16 <= age <= 99:
                raise ValueError
        except ValueError:
            messagebox.showwarning("Invalid", "Age must be 16–99.", parent=self)
            return
        stored = age - 1    # Game displays stored_value + 1
        self._upsert_patch(0x011740, 'W', stored,
                           f"Manager age = {age} (stored {stored})")

    # ── Custom Patch ──

    def _add_patch(self):
        try:
            offset = _parse_hex_str(self._coff_var.get())
        except ValueError:
            messagebox.showwarning("Invalid Offset",
                "Enter a hex offset, e.g.  11740  or  $11740", parent=self)
            return
        try:
            value = _parse_hex_str(self._cval_var.get())
        except ValueError:
            messagebox.showwarning("Invalid Value",
                "Enter a hex value, e.g.  0011  or  $0011", parent=self)
            return

        size = self._csize_var.get()
        max_val = {'B': 0xFF, 'W': 0xFFFF, 'L': 0xFFFFFFFF}[size]
        if value > max_val:
            messagebox.showwarning("Value Too Large",
                f"${value:X} exceeds {size} maximum (${max_val:X})", parent=self)
            return

        desc = self._cdesc_var.get().strip()
        new_p = PatchEntry(offset, size, value, desc)
        total = sum(q.byte_size() for q in self._patches) + new_p.byte_size()
        if total > _MAX_PATCH_BYTES:
            messagebox.showerror("No Space",
                f"This patch would need {total} bytes; only {_MAX_PATCH_BYTES} available.",
                parent=self)
            return

        self._patches.append(new_p)
        self._refresh_list()
        self._coff_var.set("")
        self._cval_var.set("")
        self._cdesc_var.set("")

    # ── Preview ──

    def _preview_asm(self):
        if not self._patches:
            messagebox.showinfo("Preview", "No patches to preview.", parent=self)
            return

        used = sum(p.byte_size() for p in self._patches)
        lines = [
            f"; Block 1137 callback — {len(self._patches)} patches, "
            f"{used}/{_MAX_PATCH_BYTES} bytes",
            "",
            f"        LEA     $50000,A0          ; base of decompressed game",
            "",
        ]
        for i, p in enumerate(self._patches, 1):
            label = p.description or "(no description)"
            lines.append(f"        ; [{i}] {label}")
            lines.append(f"        MOVE.L  #${p.offset:06X},D0")
            if p.size == 'B':
                lines.append(f"        MOVE.B  #${p.value:02X},(A0,D0.L)")
            elif p.size == 'W':
                lines.append(f"        MOVE.W  #${p.value:04X},(A0,D0.L)")
            else:
                lines.append(f"        MOVE.L  #${p.value:08X},(A0,D0.L)")
            lines.append("")

        lines.append("        JMP     (A0)               ; jump to $50000 bootstrap")
        lines.append("")
        lines.append("; ── Hex bytes for callback region ──")

        hex_data = _LEA_50000_A0
        for p in self._patches:
            hex_data += p.encode()
        hex_data += _JMP_A0

        for i in range(0, len(hex_data), 16):
            chunk = hex_data[i:i + 16]
            addr = _CB_LEA_AT + i
            hex_str = ' '.join(f'{b:02X}' for b in chunk)
            lines.append(f"  +{addr:03X}  {hex_str}")

        win = tk.Toplevel(self)
        win.title("ASM Preview — Block 1137 Callback")
        win.geometry("720x560")
        txt = tk.Text(win, font=(_MONO, 11), wrap='none',
                      bg='#1e1e1e', fg='#d4d4d4')
        vsb = ttk.Scrollbar(win, orient='vertical', command=txt.yview)
        txt.configure(yscrollcommand=vsb.set)
        vsb.pack(side=tk.RIGHT, fill=tk.Y)
        txt.pack(fill=tk.BOTH, expand=True, padx=8, pady=8)
        txt.insert('1.0', '\n'.join(lines))
        txt.config(state='disabled')

    # ── Write ──

    def _write_adf(self):
        if not self._adf_path or self._adf_data is None:
            messagebox.showinfo("No File", "Open a game disk ADF first.", parent=self)
            return
        if not self._patches:
            if not messagebox.askyesno("Confirm",
                    "No patches defined. Write an empty callback (JMP only)?\n\n"
                    "Without copy-protection patches the game will crash.",
                    parent=self):
                return

        # Check all copy-prot patches still present
        present = {p.offset for p in self._patches}
        missing = _COPYPROT_OFFSETS - present
        if missing:
            missing_str = ', '.join(f'${o:06X}' for o in sorted(missing))
            if not messagebox.askyesno("Missing Copy-Protection Patches",
                    f"The following copy-protection bypass offsets are not in the patch list:\n"
                    f"{missing_str}\n\n"
                    "The game will likely crash without them. Write anyway?",
                    parent=self):
                return

        try:
            sec_off = _PATCH_BLOCK_SECTOR * SECTOR_SIZE
            old_sector = bytes(self._adf_data[sec_off: sec_off + SECTOR_SIZE])
            new_sector = _write_block1137(old_sector, self._patches)
        except ValueError as e:
            messagebox.showerror("Error", str(e), parent=self)
            return

        used = sum(p.byte_size() for p in self._patches)
        if not messagebox.askyesno("Confirm Write",
                f"Write {len(self._patches)} patches ({used} bytes) to block 1137 of:\n"
                f"{os.path.basename(self._adf_path)}\n\n"
                "The OFS checksum will be recalculated automatically.\n"
                "Make sure you have a backup of the original ADF!", parent=self):
            return

        self._adf_data[sec_off: sec_off + SECTOR_SIZE] = new_sector

        save_path = filedialog.asksaveasfilename(
            parent=self,
            title="Save Patched Game Disk ADF As",
            defaultextension=".adf",
            initialfile=os.path.basename(self._adf_path),
            filetypes=[("ADF files", "*.adf"), ("All files", "*.*")])
        if save_path:
            try:
                with open(save_path, 'wb') as f:
                    f.write(self._adf_data)
                self._adf_path = save_path
                self._fname_var.set(os.path.basename(save_path))
                messagebox.showinfo("Done",
                    f"Saved: {os.path.basename(save_path)}\n"
                    f"{len(self._patches)} patches, {used} bytes.", parent=self)
            except Exception as e:
                messagebox.showerror("Write Error", str(e), parent=self)


# ─── League Dashboard (Feature 2a) ───────────────────────────────────

class LeagueDashboardWindow(tk.Toplevel):
    """
    Shows all four division league tables ranked by Points (then Goals) for
    the currently loaded save slot.
    """

    _DIV_NAMES = {0: "Division 1", 1: "Division 2", 2: "Division 3", 3: "Division 4"}
    _PROMOTE  = 2   # Top N teams marked as promotion zone
    _RELEGATE = 2   # Bottom N teams marked as relegation zone

    def __init__(self, parent, save, liga_names):
        super().__init__(parent)
        self.title(f"League Tables — {save.entry.name}")
        self.geometry("920x640")
        self.resizable(True, True)
        self._save = save
        self._liga = liga_names
        self._build_ui()

    def _build_ui(self):
        ttk.Label(self,
                  text=f"Save slot: {self._save.entry.name}  "
                       f"({len(self._save.teams)} teams)",
                  font=("", 12, "bold")).pack(pady=6)

        # Bucket teams by division, sort each bucket
        divs = {0: [], 1: [], 2: [], 3: []}
        for team in self._save.teams:
            d = team.division
            if d in divs:
                divs[d].append(team)

        for d in divs:
            divs[d].sort(key=lambda t: (-t.league_stats[0], -t.league_stats[1]))

        # Note on promotion/relegation counts
        info = ttk.Frame(self)
        info.pack(fill=tk.X, padx=8)
        ttk.Label(info, text="▲ = promotion zone (top 2)    "
                             "▼ = relegation zone (bottom 2)    "
                             "Sorted by Points, then Goals",
                  foreground="gray").pack(side=tk.LEFT)

        nb = ttk.Notebook(self)
        nb.pack(fill=tk.BOTH, expand=True, padx=8, pady=4)

        for d in range(4):
            teams = divs[d]
            tab = ttk.Frame(nb)
            label = self._DIV_NAMES.get(d, f"Div {d}") + f"  ({len(teams)})"
            nb.add(tab, text=label)
            self._build_table(tab, teams)

    def _build_table(self, parent, teams):
        cols = ("rank", "name", "pts", "goals", "value", "zone")
        tree = ttk.Treeview(parent, columns=cols, show='headings')
        tree.heading("rank",  text="#")
        tree.heading("name",  text="Team")
        tree.heading("pts",   text="Pts")
        tree.heading("goals", text="GF")
        tree.heading("value", text="Value")
        tree.heading("zone",  text="")
        tree.column("rank",  width=40,  anchor='center')
        tree.column("name",  width=260)
        tree.column("pts",   width=60,  anchor='center')
        tree.column("goals", width=60,  anchor='center')
        tree.column("value", width=80,  anchor='center')
        tree.column("zone",  width=100, anchor='center')

        n = len(teams)
        for rank, team in enumerate(teams, 1):
            if rank <= self._PROMOTE:
                zone, tag = "▲ Promotion", "promote"
            elif rank > n - self._RELEGATE:
                zone, tag = "▼ Relegation", "relegate"
            else:
                zone, tag = "", ""

            name = team.name or f"(team {team.index})"
            val = team.team_value_signed
            tree.insert('', 'end', tags=(tag,), values=(
                rank, name,
                team.league_stats[0],   # Points
                team.league_stats[1],   # Goals
                f"{val:+d}",
                zone))

        tree.tag_configure('promote',  background='#d8f5d8')
        tree.tag_configure('relegate', background='#f5d8d8')

        vsb = ttk.Scrollbar(parent, orient='vertical', command=tree.yview)
        tree.configure(yscrollcommand=vsb.set)
        vsb.pack(side=tk.RIGHT, fill=tk.Y)
        tree.pack(fill=tk.BOTH, expand=True, padx=4, pady=4)


# ─── Compare Saves (Feature 2b) ──────────────────────────────────────

class CompareSavesDialog(tk.Toplevel):
    """
    Pick two save slots from the same disk and see:
      • Player transfers (player IDs that changed team)
      • Division changes (promotions / relegations)
      • Team value (budget) changes
    """

    def __init__(self, parent, adf, dir_entries, game_disk=None):
        super().__init__(parent)
        self.title("Compare Saves")
        self.geometry("780x580")
        self.resizable(True, True)
        self._adf = adf
        self._game_disk = game_disk
        self._saves = [e for e in dir_entries
                       if e.name.endswith('.sav') or e.name.endswith('.dat')]
        self._build_ui()

    def _build_ui(self):
        pick = ttk.LabelFrame(self, text="Select Two Save Slots to Compare")
        pick.pack(fill=tk.X, padx=8, pady=6)
        pg = ttk.Frame(pick)
        pg.pack(fill=tk.X, padx=8, pady=8)

        names = [e.name for e in self._saves]

        ttk.Label(pg, text="Save A:").grid(row=0, column=0, sticky='e', padx=4)
        self._var_a = tk.StringVar()
        ttk.Combobox(pg, textvariable=self._var_a, values=names,
                     width=22, state='readonly').grid(row=0, column=1, padx=4)

        ttk.Label(pg, text="Save B:").grid(row=0, column=2, sticky='e', padx=12)
        self._var_b = tk.StringVar()
        ttk.Combobox(pg, textvariable=self._var_b, values=names,
                     width=22, state='readonly').grid(row=0, column=3, padx=4)

        ttk.Button(pg, text="Compare →", command=self._compare).grid(
            row=0, column=4, padx=12)

        res = ttk.LabelFrame(self, text="Comparison Results")
        res.pack(fill=tk.BOTH, expand=True, padx=8, pady=4)

        self._txt = tk.Text(res, font=(_MONO, 11), wrap='none',
                            bg='#1e1e1e', fg='#d4d4d4', state='disabled')
        vsb = ttk.Scrollbar(res, orient='vertical', command=self._txt.yview)
        hsb = ttk.Scrollbar(res, orient='horizontal', command=self._txt.xview)
        self._txt.configure(yscrollcommand=vsb.set, xscrollcommand=hsb.set)
        vsb.pack(side=tk.RIGHT, fill=tk.Y)
        hsb.pack(side=tk.BOTTOM, fill=tk.X)
        self._txt.pack(fill=tk.BOTH, expand=True, padx=4, pady=4)

    def _load(self, name):
        for e in self._saves:
            if e.name == name:
                return SaveFile(self._adf, e)
        return None

    def _compare(self):
        name_a = self._var_a.get()
        name_b = self._var_b.get()
        if not name_a or not name_b:
            messagebox.showwarning("Select", "Choose two save slots.", parent=self)
            return
        if name_a == name_b:
            messagebox.showwarning("Same File",
                "Choose two different save slots.", parent=self)
            return

        try:
            sa = self._load(name_a)
            sb = self._load(name_b)
        except Exception as e:
            messagebox.showerror("Error", str(e), parent=self)
            return

        lines = [f"A = {name_a}    B = {name_b}", "=" * 64, ""]

        # Build player-ID → team-name maps
        def roster_map(save):
            m = {}
            for team in save.teams:
                for pid in team.player_values:
                    if pid != 0xFFFF:
                        m[pid] = team.name or f"(team {team.index})"
            return m

        ra = roster_map(sa)
        rb = roster_map(sb)

        # ── Player Transfers ──
        xfers = []
        for pid in sorted(set(ra) | set(rb)):
            ta = ra.get(pid, "(unassigned)")
            tb = rb.get(pid, "(unassigned)")
            if ta != tb:
                xfers.append((pid, ta, tb))

        lines.append(f"Player Transfers  ({len(xfers)}):")
        if xfers:
            for pid, ta, tb in xfers:
                pname = ""
                if self._game_disk:
                    pname = self._game_disk.player_name(pid)
                    if pname:
                        pname = f" ({pname})"
                lines.append(f"  ID {pid:4d}{pname}:  {ta:<28s} →  {tb}")
        else:
            lines.append("  (none)")

        # ── Division Changes ──
        teams_a = {t.name: t for t in sa.teams if t.name}
        teams_b = {t.name: t for t in sb.teams if t.name}

        div_changes = []
        for name in sorted(set(teams_a) & set(teams_b)):
            da = teams_a[name].division
            db = teams_b[name].division
            if da is not None and db is not None and da != db:
                note = "promoted" if db < da else "relegated"
                div_changes.append(
                    f"  {name:<30s}  Div {da + 1} → Div {db + 1}  ({note})")

        lines.append("")
        lines.append(f"Division Changes  ({len(div_changes)}):")
        if div_changes:
            lines.extend(div_changes)
        else:
            lines.append("  (none)")

        # ── Budget / Team Value Changes ──
        budget = []
        for name in sorted(set(teams_a) & set(teams_b)):
            va = teams_a[name].team_value_signed
            vb = teams_b[name].team_value_signed
            d = vb - va
            if d != 0:
                budget.append((abs(d), name, va, vb, d))
        budget.sort(reverse=True)

        lines.append("")
        lines.append(f"Team Value Changes  ({len(budget)}):")
        if budget:
            for _, name, va, vb, delta in budget:
                lines.append(f"  {name:<30s}  {va:+7d} → {vb:+7d}  (Δ {delta:+d})")
        else:
            lines.append("  (none)")

        self._txt.config(state='normal')
        self._txt.delete('1.0', tk.END)
        self._txt.insert('1.0', '\n'.join(lines))
        self._txt.config(state='disabled')


# ─── Tactics Viewer Window ──────────────────────────────────────────

class TacticsViewerWindow(tk.Toplevel):
    """Visual editor for .tac tactics files.  Shows a football pitch with
    draggable player dots for each zone and state (with/without ball)."""

    # Pitch drawing constants — coordinates scaled from game coords
    PITCH_W = 460     # Canvas width
    PITCH_H = 600     # Canvas height
    MARGIN = 30
    # Game coord ranges (discovered from data analysis)
    GAME_X_MIN = 0
    GAME_X_MAX = 912
    GAME_Y_MIN = 0
    GAME_Y_MAX = 1400
    DOT_R = 8

    # Player colors (10 outfield players)
    _PLAYER_COLORS = [
        '#E53935', '#1E88E5', '#43A047', '#FB8C00', '#8E24AA',
        '#00ACC1', '#FFB300', '#6D4C41', '#D81B60', '#546E7A',
    ]

    def __init__(self, parent, adf, tac_entries):
        super().__init__(parent)
        self.title("Tactics Viewer")
        self.geometry("560x780")
        self.resizable(True, True)

        self._adf = adf
        self._tac_entries = tac_entries
        self._tac = None           # Current TacticsFile
        self._tac_entry = None     # Current DirEntry
        self._zone = 0
        self._state = 0            # 0 = with ball, 1 = without ball
        self._drag_player = None   # Index of player being dragged

        self._build_ui()

    def _build_ui(self):
        # Top: file selector
        top = ttk.Frame(self)
        top.pack(fill=tk.X, padx=8, pady=6)

        ttk.Label(top, text="Tactics file:").pack(side=tk.LEFT, padx=4)
        self._file_var = tk.StringVar()
        names = [e.name for e in self._tac_entries]
        cb = ttk.Combobox(top, textvariable=self._file_var, values=names,
                          width=18, state='readonly')
        cb.pack(side=tk.LEFT, padx=4)
        cb.bind('<<ComboboxSelected>>', lambda e: self._load_tac())
        if names:
            cb.current(0)

        ttk.Button(top, text="Load", command=self._load_tac).pack(side=tk.LEFT, padx=4)
        ttk.Button(top, text="Save to Disk", command=self._save_tac).pack(side=tk.LEFT, padx=8)

        # Controls: zone and state
        ctrl = ttk.Frame(self)
        ctrl.pack(fill=tk.X, padx=8, pady=2)

        ttk.Label(ctrl, text="Zone:").pack(side=tk.LEFT, padx=4)
        self._zone_var = tk.StringVar(value="0")
        zone_cb = ttk.Combobox(ctrl, textvariable=self._zone_var,
                               values=[f"{i}: {_ZONE_NAMES[i]}" for i in range(TAC_NUM_ZONES)],
                               width=22, state='readonly')
        zone_cb.pack(side=tk.LEFT, padx=4)
        zone_cb.current(0)
        zone_cb.bind('<<ComboboxSelected>>', lambda e: self._on_zone_change())

        ttk.Label(ctrl, text="State:").pack(side=tk.LEFT, padx=(12, 4))
        self._state_var = tk.StringVar(value="With ball")
        state_cb = ttk.Combobox(ctrl, textvariable=self._state_var,
                                values=["With ball", "Without ball"],
                                width=14, state='readonly')
        state_cb.pack(side=tk.LEFT, padx=4)
        state_cb.current(0)
        state_cb.bind('<<ComboboxSelected>>', lambda e: self._on_state_change())

        # Description
        self._desc_var = tk.StringVar()
        ttk.Label(self, textvariable=self._desc_var, foreground='gray',
                  wraplength=520).pack(fill=tk.X, padx=12, pady=2)

        # Canvas — football pitch
        self._canvas = tk.Canvas(self, bg='#2E7D32', highlightthickness=0)
        self._canvas.pack(fill=tk.BOTH, expand=True, padx=8, pady=4)

        self._canvas.bind('<Configure>', lambda e: self._draw_pitch())
        self._canvas.bind('<Button-1>', self._on_click)
        self._canvas.bind('<B1-Motion>', self._on_drag)
        self._canvas.bind('<ButtonRelease-1>', self._on_release)

        # Legend
        leg = ttk.Frame(self)
        leg.pack(fill=tk.X, padx=8, pady=4)
        for i in range(TAC_NUM_PLAYERS):
            tk.Canvas(leg, width=12, height=12, bg=self._PLAYER_COLORS[i],
                      highlightthickness=1, highlightbackground='white'
                      ).pack(side=tk.LEFT, padx=1)
            ttk.Label(leg, text=f"P{i}", font=(_MONO, 9)).pack(side=tk.LEFT, padx=(0, 4))

        # Status
        self._status = tk.StringVar(value="Select a .tac file and click Load")
        ttk.Label(self, textvariable=self._status, relief='sunken',
                  anchor='w').pack(fill=tk.X, side=tk.BOTTOM, padx=2, pady=2)

        self._load_tac()

    def _load_tac(self):
        name = self._file_var.get()
        if not name:
            return
        for e in self._tac_entries:
            if e.name == name:
                raw = bytes(self._adf.data[e.byte_offset: e.byte_offset + e.size_bytes])
                try:
                    self._tac = TacticsFile(raw)
                    self._tac_entry = e
                    self._desc_var.set(self._tac.description or "(no description)")
                    self._status.set(f"Loaded {name} ({e.size_bytes} bytes)")
                    self._draw_pitch()
                except Exception as ex:
                    messagebox.showerror("Error", str(ex), parent=self)
                return

    def _save_tac(self):
        if not self._tac or not self._tac_entry:
            return
        packed = self._tac.pack()
        e = self._tac_entry
        self._adf.data[e.byte_offset: e.byte_offset + len(packed)] = packed
        self._status.set(f"Written {e.name} back to ADF buffer (use File → Save to write to disk)")

    def _on_zone_change(self):
        val = self._zone_var.get()
        self._zone = int(val.split(':')[0])
        self._draw_pitch()

    def _on_state_change(self):
        self._state = 0 if 'With' in self._state_var.get() else 1
        self._draw_pitch()

    def _game_to_canvas(self, gx, gy):
        cw = self._canvas.winfo_width()
        ch = self._canvas.winfo_height()
        m = self.MARGIN
        # Scale game coords to canvas, Y inverted (low Y = bottom = own goal)
        cx = m + (gx - self.GAME_X_MIN) / (self.GAME_X_MAX - self.GAME_X_MIN) * (cw - 2 * m)
        cy = ch - m - (gy - self.GAME_Y_MIN) / (self.GAME_Y_MAX - self.GAME_Y_MIN) * (ch - 2 * m)
        return cx, cy

    def _canvas_to_game(self, cx, cy):
        cw = self._canvas.winfo_width()
        ch = self._canvas.winfo_height()
        m = self.MARGIN
        gx = self.GAME_X_MIN + (cx - m) / (cw - 2 * m) * (self.GAME_X_MAX - self.GAME_X_MIN)
        gy = self.GAME_Y_MIN + (ch - m - cy) / (ch - 2 * m) * (self.GAME_Y_MAX - self.GAME_Y_MIN)
        return max(0, int(gx)), max(0, int(gy))

    def _draw_pitch(self):
        c = self._canvas
        c.delete('all')
        cw = c.winfo_width()
        ch = c.winfo_height()
        if cw < 50 or ch < 50:
            return
        m = self.MARGIN

        # Pitch outline
        c.create_rectangle(m, m, cw - m, ch - m, outline='white', width=2)
        # Center line
        cy_mid = ch / 2
        c.create_line(m, cy_mid, cw - m, cy_mid, fill='white', width=1)
        # Center circle
        cr = min(cw, ch) * 0.08
        c.create_oval(cw / 2 - cr, cy_mid - cr, cw / 2 + cr, cy_mid + cr,
                      outline='white', width=1)
        # Penalty areas
        pa_w = (cw - 2 * m) * 0.4
        pa_h = (ch - 2 * m) * 0.1
        # Bottom (own goal)
        c.create_rectangle(cw / 2 - pa_w / 2, ch - m - pa_h,
                           cw / 2 + pa_w / 2, ch - m, outline='white', width=1)
        # Top (opponent goal)
        c.create_rectangle(cw / 2 - pa_w / 2, m,
                           cw / 2 + pa_w / 2, m + pa_h, outline='white', width=1)

        # Goal labels
        c.create_text(cw / 2, ch - m + 12, text="OWN GOAL", fill='white',
                      font=(_MONO, 9))
        c.create_text(cw / 2, m - 12, text="OPPONENT", fill='white',
                      font=(_MONO, 9))

        if not self._tac:
            return

        # Draw players
        r = self.DOT_R
        z = self._zone
        s = self._state
        for p in range(TAC_NUM_PLAYERS):
            gx, gy = self._tac.positions[z][p][s]
            cx, cy = self._game_to_canvas(gx, gy)
            color = self._PLAYER_COLORS[p]
            c.create_oval(cx - r, cy - r, cx + r, cy + r,
                          fill=color, outline='white', width=2, tags=f'p{p}')
            c.create_text(cx, cy, text=str(p), fill='white',
                          font=(_MONO, 9, 'bold'), tags=f'p{p}')

    def _on_click(self, event):
        if not self._tac:
            return
        r = self.DOT_R + 4
        for p in range(TAC_NUM_PLAYERS):
            gx, gy = self._tac.positions[self._zone][p][self._state]
            cx, cy = self._game_to_canvas(gx, gy)
            if abs(event.x - cx) < r and abs(event.y - cy) < r:
                self._drag_player = p
                return
        self._drag_player = None

    def _on_drag(self, event):
        if self._drag_player is None or not self._tac:
            return
        gx, gy = self._canvas_to_game(event.x, event.y)
        gx = max(0, min(self.GAME_X_MAX, gx))
        gy = max(0, min(self.GAME_Y_MAX, gy))
        self._tac.set_pos(self._zone, self._drag_player, self._state, gx, gy)
        self._draw_pitch()
        self._status.set(f"Player {self._drag_player}: ({gx}, {gy})")

    def _on_release(self, event):
        self._drag_player = None


# ─── Championship Highlights ────────────────────────────────────────

class ChampionshipHighlightsWindow(tk.Toplevel):
    """Player attribute browser and championship highlights for a save slot.

    Tabs:
    - Best By Position: top 10 players for each role (GK/DEF/MID/FWD)
    - Top Scorers / Most Matches
    - Young Talents (age 16-22)
    - Market Values (highest value players)
    - Squad Analyst (per-team view with renew/sack hints)
    """

    _TOP_N = 15

    def __init__(self, parent, save, adf, game_disk=None, liga_names=None):
        super().__init__(parent)
        self.title(f"Championship Highlights — {save.entry.name}")
        self.geometry("1020x700")
        self.resizable(True, True)
        self._save = save
        self._adf = adf
        self._game_disk = game_disk
        self._liga = liga_names or []
        self._players = parse_player_db(adf, save.entry)
        self._build_ui()

    def _player_name(self, pid):
        if self._game_disk:
            return self._game_disk.player_name(pid)
        return f"#{pid}"

    def _team_name(self, team_idx):
        if team_idx == 0xFF:
            return "Free Agent"
        if 0 <= team_idx < len(self._liga):
            return self._liga[team_idx]
        return f"Team {team_idx}"

    def _build_ui(self):
        if not self._players:
            ttk.Label(self, text="No player database found for this save slot.",
                      font=("", 13)).pack(pady=40)
            return

        ttk.Label(self,
                  text=f"{self._save.entry.name} — {len(self._players)} players",
                  font=("", 12, "bold")).pack(pady=6)

        nb = ttk.Notebook(self)
        nb.pack(fill=tk.BOTH, expand=True, padx=8, pady=4)

        # Tab 1: Best by Position
        tab_pos = ttk.Frame(nb)
        nb.add(tab_pos, text="Best By Position")
        self._build_position_tab(tab_pos)

        # Tab 2: Top Scorers / Matches
        tab_stats = ttk.Frame(nb)
        nb.add(tab_stats, text="Top Scorers")
        self._build_scorers_tab(tab_stats)

        # Tab 3: Young Talents
        tab_young = ttk.Frame(nb)
        nb.add(tab_young, text="Young Talents")
        self._build_young_tab(tab_young)

        # Tab 4: Market Values
        tab_value = ttk.Frame(nb)
        nb.add(tab_value, text="Market Values")
        self._build_value_tab(tab_value)

        # Tab 5: Squad Analyst
        tab_squad = ttk.Frame(nb)
        nb.add(tab_squad, text="Squad Analyst")
        self._build_squad_tab(tab_squad)

    # ── Common Treeview builder ──

    def _make_tree(self, parent, columns, headings, widths, anchors=None,
                   on_double_click=None):
        frame = ttk.Frame(parent)
        frame.pack(fill=tk.BOTH, expand=True, padx=4, pady=4)
        tree = ttk.Treeview(frame, columns=columns, show='headings')
        for col, hd, w in zip(columns, headings, widths):
            tree.heading(col, text=hd)
            anc = 'center'
            if anchors and col in anchors:
                anc = anchors[col]
            tree.column(col, width=w, anchor=anc)
        vsb = ttk.Scrollbar(frame, orient='vertical', command=tree.yview)
        tree.configure(yscrollcommand=vsb.set)
        vsb.pack(side=tk.RIGHT, fill=tk.Y)
        tree.pack(fill=tk.BOTH, expand=True)
        tree._pid_map = {}
        if on_double_click:
            tree.bind('<Double-1>', on_double_click)
        return tree

    # ── Tab: Best by Position ──

    def _build_position_tab(self, parent):
        pos_nb = ttk.Notebook(parent)
        pos_nb.pack(fill=tk.BOTH, expand=True)
        for pos_code, pos_label in [(1, "Goalkeepers"), (2, "Defenders"),
                                     (3, "Midfielders"), (4, "Forwards")]:
            tab = ttk.Frame(pos_nb)
            pos_nb.add(tab, text=pos_label)
            self._build_pos_subtab(tab, pos_code)

    def _build_pos_subtab(self, parent, pos_code):
        players = [p for p in self._players.values() if p.position == pos_code]
        players.sort(key=lambda p: -p.role_skill_avg())
        players = players[:self._TOP_N]

        cols = ("rank", "name", "age", "team", "role_avg", "overall",
                "sk1", "sk2", "sk3", "sk4", "goals", "matches")
        # Pick position-relevant skill headers
        if pos_code == 1:
            sk_heads = ["Keep", "Agi", "Res"]
            sk_attrs = ["keeping", "agility", "resilience"]
        elif pos_code == 2:
            sk_heads = ["Tck", "Sta", "Agg", "Pac"]
            sk_attrs = ["tackling", "stamina", "aggression", "pace"]
        elif pos_code == 3:
            sk_heads = ["Pas", "Fla", "Sta", "Agi"]
            sk_attrs = ["passing", "flair", "stamina", "agility"]
        else:
            sk_heads = ["Sht", "Pac", "Fla", "Agi"]
            sk_attrs = ["shooting", "pace", "flair", "agility"]

        headings = ["#", "Name", "Age", "Team", "Role", "Avg"] + sk_heads + ["Gls", "Mat"]
        widths = [30, 140, 40, 140, 50, 50] + [45] * len(sk_heads) + [40, 40]
        tree = self._make_tree(parent, cols[:6 + len(sk_heads) + 2],
                               headings, widths,
                               anchors={"name": "w", "team": "w"},
                               on_double_click=self._open_editor)

        for rank, p in enumerate(players, 1):
            sk_vals = [str(getattr(p, a)) for a in sk_attrs]
            # Pad to 4 if fewer skills
            while len(sk_vals) < 4:
                sk_vals.append("")
            iid = tree.insert('', 'end', values=(
                rank,
                self._player_name(p.player_id),
                p.age,
                self._team_name(p.team_index),
                f"{p.role_skill_avg():.0f}",
                f"{p.skill_avg:.0f}",
                *sk_vals[:len(sk_attrs)],
                p.goals_this_year,
                p.matches_this_year,
            ))
            tree._pid_map[iid] = p.player_id

    # ── Tab: Top Scorers ──

    def _build_scorers_tab(self, parent):
        scorer_nb = ttk.Notebook(parent)
        scorer_nb.pack(fill=tk.BOTH, expand=True)

        # Sub-tab: Goals this year
        tab_g = ttk.Frame(scorer_nb)
        scorer_nb.add(tab_g, text="Goals This Year")
        self._build_stat_list(tab_g, "goals_this_year", "Goals")

        # Sub-tab: Goals last year
        tab_gl = ttk.Frame(scorer_nb)
        scorer_nb.add(tab_gl, text="Goals Last Year")
        self._build_stat_list(tab_gl, "goals_last_year", "Goals")

        # Sub-tab: Matches this year
        tab_m = ttk.Frame(scorer_nb)
        scorer_nb.add(tab_m, text="Matches This Year")
        self._build_stat_list(tab_m, "matches_this_year", "Matches")

        # Sub-tab: Display points
        tab_d = ttk.Frame(scorer_nb)
        scorer_nb.add(tab_d, text="Display Pts This Year")
        self._build_stat_list(tab_d, "dsp_pts_this_year", "DspPts")

    def _build_stat_list(self, parent, attr, label):
        players = sorted(self._players.values(),
                         key=lambda p: -getattr(p, attr))
        players = [p for p in players if getattr(p, attr) > 0][:self._TOP_N]
        cols = ("rank", "name", "pos", "age", "team", "stat", "avg")
        headings = ["#", "Name", "Pos", "Age", "Team", label, "Skill Avg"]
        widths = [30, 140, 50, 40, 140, 60, 60]
        tree = self._make_tree(parent, cols, headings, widths,
                               anchors={"name": "w", "team": "w"},
                               on_double_click=self._open_editor)
        for rank, p in enumerate(players, 1):
            iid = tree.insert('', 'end', values=(
                rank,
                self._player_name(p.player_id),
                p.position_name,
                p.age,
                self._team_name(p.team_index),
                getattr(p, attr),
                f"{p.skill_avg:.0f}",
            ))
            tree._pid_map[iid] = p.player_id

    # ── Tab: Young Talents ──

    def _build_young_tab(self, parent):
        young = [p for p in self._players.values() if 16 <= p.age <= 22]
        young.sort(key=lambda p: -p.role_skill_avg())
        young = young[:30]

        cols = ("rank", "name", "pos", "age", "team", "role_avg", "overall",
                "goals", "matches", "contract")
        headings = ["#", "Name", "Pos", "Age", "Team", "Role", "Avg",
                    "Gls", "Mat", "Contract"]
        widths = [30, 140, 50, 40, 140, 50, 50, 40, 40, 60]
        tree = self._make_tree(parent, cols, headings, widths,
                               anchors={"name": "w", "team": "w"},
                               on_double_click=self._open_editor)
        for rank, p in enumerate(young, 1):
            iid = tree.insert('', 'end', values=(
                rank,
                self._player_name(p.player_id),
                p.position_name,
                p.age,
                self._team_name(p.team_index),
                f"{p.role_skill_avg():.0f}",
                f"{p.skill_avg:.0f}",
                p.goals_this_year,
                p.matches_this_year,
                p.contract_years,
            ))
            tree._pid_map[iid] = p.player_id

    # ── Tab: Market Values ──

    def _build_value_tab(self, parent):
        valued = sorted(self._players.values(), key=lambda p: -p.value)
        valued = [p for p in valued if p.value > 0][:30]

        cols = ("rank", "name", "pos", "age", "team", "value", "role_avg",
                "overall", "goals", "matches")
        headings = ["#", "Name", "Pos", "Age", "Team", "Value", "Role",
                    "Avg", "Gls", "Mat"]
        widths = [30, 140, 50, 40, 140, 50, 50, 50, 40, 40]
        tree = self._make_tree(parent, cols, headings, widths,
                               anchors={"name": "w", "team": "w"},
                               on_double_click=self._open_editor)
        for rank, p in enumerate(valued, 1):
            iid = tree.insert('', 'end', values=(
                rank,
                self._player_name(p.player_id),
                p.position_name,
                p.age,
                self._team_name(p.team_index),
                p.value,
                f"{p.role_skill_avg():.0f}",
                f"{p.skill_avg:.0f}",
                p.goals_this_year,
                p.matches_this_year,
            ))
            tree._pid_map[iid] = p.player_id

    # ── Tab: Squad Analyst ──

    def _build_squad_tab(self, parent):
        top = ttk.Frame(parent)
        top.pack(fill=tk.X, padx=4, pady=4)
        ttk.Label(top, text="Team:").pack(side=tk.LEFT)
        self._squad_var = tk.StringVar()
        team_names = []
        self._squad_team_map = {}  # display_name → team_index
        for team in self._save.teams:
            if team.num_players > 0:
                disp = team.name or f"(team {team.index})"
                team_names.append(disp)
                self._squad_team_map[disp] = team.index
        combo = ttk.Combobox(top, textvariable=self._squad_var,
                             values=team_names, state='readonly', width=30)
        combo.pack(side=tk.LEFT, padx=8)
        combo.bind('<<ComboboxSelected>>', self._on_squad_selected)

        # Summary label
        self._squad_summary = ttk.Label(parent, text="", font=("", 11))
        self._squad_summary.pack(fill=tk.X, padx=8)

        # Player list
        cols = ("name", "pos", "age", "role_avg", "overall",
                "goals", "matches", "inj", "contract", "hint")
        headings = ["Name", "Pos", "Age", "Role", "Avg",
                    "Gls", "Mat", "Inj", "Contract", "Hint"]
        widths = [140, 50, 40, 50, 50, 40, 40, 35, 60, 120]
        self._squad_tree = self._make_tree(parent, cols, headings, widths,
                                           anchors={"name": "w", "hint": "w"},
                                           on_double_click=self._open_editor)
        self._squad_tree._pid_map = {}
        self._squad_tree.tag_configure('renew', background='#d8f5d8')
        self._squad_tree.tag_configure('sack', background='#f5d8d8')
        self._squad_tree.tag_configure('watch', background='#f5f0d8')

        if team_names:
            combo.current(0)
            self._on_squad_selected()

    def _on_squad_selected(self, event=None):
        disp = self._squad_var.get()
        team_idx = self._squad_team_map.get(disp)
        if team_idx is None:
            return
        team = self._save.teams[team_idx]

        # Collect roster player records
        roster = []
        for i in range(MAX_PLAYER_SLOTS):
            pid = struct.unpack_from('>H', team.raw, 12 + i * 2)[0]
            if pid != 0xFFFF and pid in self._players:
                roster.append(self._players[pid])

        # Summary
        if roster:
            avg_age = sum(p.age for p in roster) / len(roster)
            avg_skill = sum(p.skill_avg for p in roster) / len(roster)
            total_goals = sum(p.goals_this_year for p in roster)
            self._squad_summary.config(
                text=f"{len(roster)} players | Avg age: {avg_age:.1f} | "
                     f"Avg skill: {avg_skill:.0f} | Team goals: {total_goals}")
        else:
            self._squad_summary.config(text="No player data available")

        # Sort by position then role skill
        roster.sort(key=lambda p: (p.position, -p.role_skill_avg()))

        tree = self._squad_tree
        tree.delete(*tree.get_children())
        tree._pid_map = {}
        for p in roster:
            hint, tag = self._squad_hint(p)
            iid = tree.insert('', 'end', tags=(tag,), values=(
                self._player_name(p.player_id),
                p.position_name,
                p.age,
                f"{p.role_skill_avg():.0f}",
                f"{p.skill_avg:.0f}",
                p.goals_this_year,
                p.matches_this_year,
                p.injury_weeks if p.injury_weeks else "",
                p.contract_years,
                hint,
            ))
            tree._pid_map[iid] = p.player_id

    def _squad_hint(self, p):
        """Return (hint_text, tag) for renew/sack/watch recommendations."""
        role_avg = p.role_skill_avg()
        # Young + high potential → renew
        if p.age <= 22 and role_avg >= 100:
            return "Young talent", "renew"
        # Star player with expiring contract → renew urgently
        if role_avg >= 130 and p.contract_years <= 1:
            return "Renew contract!", "renew"
        # Old + declining → consider selling
        if p.age >= 30 and role_avg < 100:
            return "Past peak", "sack"
        # Injury-prone
        if p.injuries_this_year + p.injuries_last_year >= 4:
            return "Injury prone", "watch"
        # Low skill for position
        if role_avg < 70:
            return "Below average", "sack"
        # Good performer
        if role_avg >= 130:
            return "Star player", "renew"
        return "", ""

    def _open_editor(self, event):
        """Open the Player Editor for the double-clicked row."""
        tree = event.widget
        sel = tree.selection()
        if not sel:
            return
        iid = sel[0]
        pid = tree._pid_map.get(iid)
        if pid is None or pid not in self._players:
            return
        PlayerEditorWindow(
            self, self._players[pid], self._adf, self._save.entry,
            game_disk=self._game_disk,
            on_save=lambda: self._refresh_tree(tree))

    def _refresh_tree(self, tree):
        """Placeholder for refreshing a tree after edits."""
        pass


# ─── Transfer Market Window ─────────────────────────────────────────

class TransferMarketWindow(tk.Toplevel):
    """Search, filter, and transfer players between teams."""

    def __init__(self, parent, save, adf, game_disk=None, liga_names=None):
        super().__init__(parent)
        self.title(f"Transfer Market — {save.entry.name}")
        self.geometry("1200x720")
        self.resizable(True, True)
        self._save = save
        self._adf = adf
        self._game_disk = game_disk
        self._liga = liga_names or []
        self._players = parse_player_db(adf, save.entry)
        self._build_ui()
        self._apply_filters()

    def _player_name(self, pid):
        if self._game_disk:
            return self._game_disk.player_name(pid)
        return f"#{pid}"

    def _team_name(self, team_idx):
        if team_idx == 0xFF:
            return "Free Agent"
        if 0 <= team_idx < len(self._liga):
            return self._liga[team_idx]
        return f"Team {team_idx}"

    def _build_ui(self):
        if not self._players:
            ttk.Label(self, text="No player database found for this save slot.",
                      font=("", 13)).pack(pady=40)
            return

        # Filters
        filt = ttk.LabelFrame(self, text="Filters")
        filt.pack(fill=tk.X, padx=8, pady=(8, 4))

        r1 = ttk.Frame(filt)
        r1.pack(fill=tk.X, padx=4, pady=2)

        ttk.Label(r1, text="Search:").pack(side=tk.LEFT)
        self._search_var = tk.StringVar()
        search_entry = ttk.Entry(r1, textvariable=self._search_var, width=20)
        search_entry.pack(side=tk.LEFT, padx=4)
        search_entry.bind('<Return>', lambda e: self._apply_filters())

        ttk.Label(r1, text="Position:").pack(side=tk.LEFT, padx=(12, 0))
        self._pos_var = tk.StringVar(value="All")
        pos_combo = ttk.Combobox(r1, textvariable=self._pos_var,
                                 values=["All", "GK", "DEF", "MID", "FWD"],
                                 state='readonly', width=6)
        pos_combo.pack(side=tk.LEFT, padx=4)
        pos_combo.bind('<<ComboboxSelected>>', lambda e: self._apply_filters())

        ttk.Label(r1, text="Age:").pack(side=tk.LEFT, padx=(12, 0))
        self._age_min_var = tk.IntVar(value=16)
        self._age_max_var = tk.IntVar(value=50)
        ttk.Spinbox(r1, from_=16, to=50, textvariable=self._age_min_var,
                    width=4).pack(side=tk.LEFT, padx=2)
        ttk.Label(r1, text="–").pack(side=tk.LEFT)
        ttk.Spinbox(r1, from_=16, to=50, textvariable=self._age_max_var,
                    width=4).pack(side=tk.LEFT, padx=2)

        ttk.Label(r1, text="Min skill:").pack(side=tk.LEFT, padx=(12, 0))
        self._skill_min_var = tk.IntVar(value=0)
        ttk.Spinbox(r1, from_=0, to=200, textvariable=self._skill_min_var,
                    width=5).pack(side=tk.LEFT, padx=2)

        ttk.Button(r1, text="Apply",
                   command=self._apply_filters).pack(side=tk.LEFT, padx=8)

        r2 = ttk.Frame(filt)
        r2.pack(fill=tk.X, padx=4, pady=2)

        ttk.Label(r2, text="Team:").pack(side=tk.LEFT)
        team_values = ["All", "Free Agents"]
        for team in self._save.teams:
            if team.num_players > 0:
                team_values.append(team.name or f"(team {team.index})")
        self._team_filter_var = tk.StringVar(value="All")
        ttk.Combobox(r2, textvariable=self._team_filter_var,
                     values=team_values, state='readonly',
                     width=25).pack(side=tk.LEFT, padx=4)

        self._count_label = ttk.Label(r2, text="")
        self._count_label.pack(side=tk.RIGHT, padx=8)

        # Main PanedWindow
        pw = ttk.PanedWindow(self, orient=tk.HORIZONTAL)
        pw.pack(fill=tk.BOTH, expand=True, padx=8, pady=4)

        # Left: database list
        left = ttk.Frame(pw)
        pw.add(left, weight=3)

        cols = ("name", "pos", "age", "team", "role", "avg",
                "val", "goals", "mat")
        headings = ["Name", "Pos", "Age", "Team", "Role", "Avg",
                    "Val", "Gls", "Mat"]
        widths = [140, 45, 35, 130, 45, 45, 40, 35, 35]

        db_frame = ttk.Frame(left)
        db_frame.pack(fill=tk.BOTH, expand=True)
        self._db_tree = ttk.Treeview(db_frame, columns=cols, show='headings')
        for col, hd, w in zip(cols, headings, widths):
            self._db_tree.heading(col, text=hd,
                                  command=lambda c=col: self._sort_column(c))
            anc = 'w' if col in ('name', 'team') else 'center'
            self._db_tree.column(col, width=w, anchor=anc)
        vsb = ttk.Scrollbar(db_frame, orient='vertical',
                            command=self._db_tree.yview)
        self._db_tree.configure(yscrollcommand=vsb.set)
        vsb.pack(side=tk.RIGHT, fill=tk.Y)
        self._db_tree.pack(fill=tk.BOTH, expand=True)
        self._db_tree._pid_map = {}
        self._db_tree.bind('<Double-1>', self._on_db_double_click)

        btn_mid = ttk.Frame(left)
        btn_mid.pack(fill=tk.X, pady=4)
        ttk.Button(btn_mid, text="Transfer to Team →",
                   command=self._transfer_to_team).pack(side=tk.LEFT, padx=4)
        ttk.Button(btn_mid, text="Edit Player…",
                   command=self._edit_selected).pack(side=tk.LEFT, padx=4)

        # Right: team roster
        right = ttk.LabelFrame(pw, text="Team Roster")
        pw.add(right, weight=2)

        top_r = ttk.Frame(right)
        top_r.pack(fill=tk.X, padx=4, pady=4)
        ttk.Label(top_r, text="Team:").pack(side=tk.LEFT)
        self._roster_team_var = tk.StringVar()
        roster_teams = []
        self._roster_team_map = {}
        for team in self._save.teams:
            disp = team.name or f"(team {team.index})"
            roster_teams.append(disp)
            self._roster_team_map[disp] = team.index
        self._roster_combo = ttk.Combobox(
            top_r, textvariable=self._roster_team_var,
            values=roster_teams, state='readonly', width=25)
        self._roster_combo.pack(side=tk.LEFT, padx=4)
        self._roster_combo.bind('<<ComboboxSelected>>', self._load_roster)

        self._roster_summary = ttk.Label(right, text="")
        self._roster_summary.pack(fill=tk.X, padx=8)

        rcols = ("name", "pos", "age", "role", "avg")
        rheadings = ["Name", "Pos", "Age", "Role", "Avg"]
        rwidths = [140, 45, 35, 45, 45]
        roster_frame = ttk.Frame(right)
        roster_frame.pack(fill=tk.BOTH, expand=True, padx=4, pady=4)
        self._roster_tree = ttk.Treeview(roster_frame, columns=rcols,
                                         show='headings')
        for col, hd, w in zip(rcols, rheadings, rwidths):
            self._roster_tree.heading(col, text=hd)
            anc = 'w' if col == 'name' else 'center'
            self._roster_tree.column(col, width=w, anchor=anc)
        rvsb = ttk.Scrollbar(roster_frame, orient='vertical',
                             command=self._roster_tree.yview)
        self._roster_tree.configure(yscrollcommand=rvsb.set)
        rvsb.pack(side=tk.RIGHT, fill=tk.Y)
        self._roster_tree.pack(fill=tk.BOTH, expand=True)
        self._roster_tree._pid_map = {}

        rbtn = ttk.Frame(right)
        rbtn.pack(fill=tk.X, padx=4, pady=4)
        ttk.Button(rbtn, text="← Remove from Team",
                   command=self._remove_from_team).pack(side=tk.LEFT, padx=4)

        if roster_teams:
            self._roster_combo.current(0)
            self._load_roster()

    def _sort_column(self, col):
        reverse = getattr(self, '_sort_reverse', False)
        items = [(self._db_tree.set(iid, col), iid)
                 for iid in self._db_tree.get_children('')]
        try:
            items.sort(key=lambda t: float(t[0]), reverse=reverse)
        except ValueError:
            items.sort(key=lambda t: t[0].lower(), reverse=reverse)
        for idx, (_, iid) in enumerate(items):
            self._db_tree.move(iid, '', idx)
        self._sort_reverse = not reverse

    def _apply_filters(self):
        tree = self._db_tree
        tree.delete(*tree.get_children())
        tree._pid_map = {}

        search = self._search_var.get().lower().strip()
        pos_filter = self._pos_var.get()
        age_lo = self._age_min_var.get()
        age_hi = self._age_max_var.get()
        skill_min = self._skill_min_var.get()
        team_filter = self._team_filter_var.get()

        pos_code = {"GK": 1, "DEF": 2, "MID": 3, "FWD": 4}.get(pos_filter)
        team_idx_filter = None
        if team_filter == "Free Agents":
            team_idx_filter = 0xFF
        elif team_filter != "All":
            for team in self._save.teams:
                disp = team.name or f"(team {team.index})"
                if disp == team_filter:
                    team_idx_filter = team.index
                    break

        count = 0
        for pid, p in sorted(self._players.items()):
            if pos_code is not None and p.position != pos_code:
                continue
            if not (age_lo <= p.age <= age_hi):
                continue
            if p.role_skill_avg() < skill_min:
                continue
            if team_idx_filter is not None and p.team_index != team_idx_filter:
                continue
            if search:
                name = self._player_name(pid).lower()
                if search not in name:
                    continue

            iid = tree.insert('', 'end', values=(
                self._player_name(pid),
                p.position_name,
                p.age,
                self._team_name(p.team_index),
                f"{p.role_skill_avg():.0f}",
                f"{p.skill_avg:.0f}",
                p.value,
                p.goals_this_year,
                p.matches_this_year,
            ))
            tree._pid_map[iid] = pid
            count += 1

        self._count_label.config(text=f"{count} players")

    def _load_roster(self, event=None):
        disp = self._roster_team_var.get()
        team_idx = self._roster_team_map.get(disp)
        if team_idx is None:
            return
        team = self._save.teams[team_idx]

        tree = self._roster_tree
        tree.delete(*tree.get_children())
        tree._pid_map = {}

        roster = []
        for i in range(MAX_PLAYER_SLOTS):
            pid = struct.unpack_from('>H', team.raw, 12 + i * 2)[0]
            if pid != 0xFFFF and pid in self._players:
                roster.append(self._players[pid])

        roster.sort(key=lambda p: (p.position, -p.role_skill_avg()))
        for p in roster:
            iid = tree.insert('', 'end', values=(
                self._player_name(p.player_id),
                p.position_name,
                p.age,
                f"{p.role_skill_avg():.0f}",
                f"{p.skill_avg:.0f}",
            ))
            tree._pid_map[iid] = p.player_id

        self._roster_summary.config(
            text=f"{len(roster)} / {MAX_PLAYER_SLOTS} slots filled")

    def _transfer_to_team(self):
        sel = self._db_tree.selection()
        if not sel:
            messagebox.showinfo("Info", "Select a player from the left list.",
                                parent=self)
            return
        pid = self._db_tree._pid_map.get(sel[0])
        if pid is None:
            return

        disp = self._roster_team_var.get()
        dest_idx = self._roster_team_map.get(disp)
        if dest_idx is None:
            messagebox.showinfo("Info", "Select a destination team.",
                                parent=self)
            return

        dest_team = self._save.teams[dest_idx]
        player = self._players[pid]

        filled = sum(1 for i in range(MAX_PLAYER_SLOTS)
                     if struct.unpack_from('>H', dest_team.raw, 12 + i * 2)[0]
                     != 0xFFFF)
        if filled >= MAX_PLAYER_SLOTS:
            messagebox.showwarning("Full",
                                   f"{disp} has no empty roster slots (25/25).",
                                   parent=self)
            return

        for i in range(MAX_PLAYER_SLOTS):
            existing = struct.unpack_from('>H', dest_team.raw, 12 + i * 2)[0]
            if existing == pid:
                messagebox.showinfo("Info",
                                    f"Player is already on {disp}.",
                                    parent=self)
                return

        old_idx = player.team_index
        if old_idx != 0xFF and old_idx < len(self._save.teams):
            old_team = self._save.teams[old_idx]
            for i in range(MAX_PLAYER_SLOTS):
                if struct.unpack_from('>H', old_team.raw, 12 + i * 2)[0] == pid:
                    struct.pack_into('>H', old_team.raw, 12 + i * 2, 0xFFFF)
                    old_team.player_values[i] = 0xFFFF
                    old_team.num_players = sum(
                        1 for v in old_team.player_values if v != 0xFFFF)
                    break

        for i in range(MAX_PLAYER_SLOTS):
            if struct.unpack_from('>H', dest_team.raw, 12 + i * 2)[0] == 0xFFFF:
                struct.pack_into('>H', dest_team.raw, 12 + i * 2, pid)
                dest_team.player_values[i] = pid
                dest_team.num_players = sum(
                    1 for v in dest_team.player_values if v != 0xFFFF)
                break

        player.team_index = dest_idx
        self._save.write_back()
        write_player_db(self._adf, self._save.entry, {pid: player})
        self._load_roster()
        self._apply_filters()

    def _remove_from_team(self):
        sel = self._roster_tree.selection()
        if not sel:
            messagebox.showinfo("Info", "Select a player from the roster.",
                                parent=self)
            return
        pid = self._roster_tree._pid_map.get(sel[0])
        if pid is None:
            return

        disp = self._roster_team_var.get()
        team_idx = self._roster_team_map.get(disp)
        if team_idx is None:
            return

        team = self._save.teams[team_idx]
        player = self._players[pid]

        for i in range(MAX_PLAYER_SLOTS):
            if struct.unpack_from('>H', team.raw, 12 + i * 2)[0] == pid:
                struct.pack_into('>H', team.raw, 12 + i * 2, 0xFFFF)
                team.player_values[i] = 0xFFFF
                team.num_players = sum(
                    1 for v in team.player_values if v != 0xFFFF)
                break

        player.team_index = 0xFF
        self._save.write_back()
        write_player_db(self._adf, self._save.entry, {pid: player})
        self._load_roster()
        self._apply_filters()

    def _on_db_double_click(self, event):
        sel = self._db_tree.selection()
        if not sel:
            return
        pid = self._db_tree._pid_map.get(sel[0])
        if pid is not None and pid in self._players:
            PlayerEditorWindow(
                self, self._players[pid], self._adf, self._save.entry,
                game_disk=self._game_disk,
                on_save=self._apply_filters)

    def _edit_selected(self):
        sel = self._db_tree.selection()
        if not sel:
            messagebox.showinfo("Info", "Select a player first.", parent=self)
            return
        pid = self._db_tree._pid_map.get(sel[0])
        if pid is not None and pid in self._players:
            PlayerEditorWindow(
                self, self._players[pid], self._adf, self._save.entry,
                game_disk=self._game_disk,
                on_save=self._apply_filters)


# ─── Player Editor Window ───────────────────────────────────────────

class PlayerEditorWindow(tk.Toplevel):
    """Edit a single player's attributes and write changes to the ADF."""

    _SKILL_FIELDS = [
        ("Stamina",    "stamina"),
        ("Resilience", "resilience"),
        ("Pace",       "pace"),
        ("Agility",    "agility"),
        ("Aggression", "aggression"),
        ("Flair",      "flair"),
        ("Passing",    "passing"),
        ("Shooting",   "shooting"),
        ("Tackling",   "tackling"),
        ("Keeping",    "keeping"),
    ]
    _INFO_FIELDS = [
        ("Age",             "age",             0, 50),
        ("Position (1-4)",  "position",        0, 4),
        ("Height (cm)",     "height",          140, 255),
        ("Weight (kg)",     "weight",          30, 150),
        ("Contract years",  "contract_years",  0, 20),
        ("Market value",    "value",           0, 255),
    ]
    _STAT_FIELDS = [
        ("Injury weeks",       "injury_weeks"),
        ("Injuries this year", "injuries_this_year"),
        ("Injuries last year", "injuries_last_year"),
        ("Goals this year",    "goals_this_year"),
        ("Goals last year",    "goals_last_year"),
        ("Matches this year",  "matches_this_year"),
        ("Matches last year",  "matches_last_year"),
    ]

    def __init__(self, parent, player, adf, dir_entry, game_disk=None,
                 on_save=None):
        """
        player:    PlayerRecord to edit (modified in place)
        adf:       ADF instance (for write-back)
        dir_entry: DirEntry of the .sav file this player DB belongs to
        game_disk: optional GameDisk for name lookup
        on_save:   optional callback() invoked after successful write
        """
        super().__init__(parent)
        self._player = player
        self._adf = adf
        self._dir_entry = dir_entry
        self._game_disk = game_disk
        self._on_save = on_save

        name = ""
        if game_disk:
            name = game_disk.player_name(player.player_id)
        self.title(f"Edit Player — {name or f'#{player.player_id}'}")
        self.geometry("480x620")
        self.resizable(False, True)

        self._vars = {}   # attr_name → tk.IntVar
        self._build_ui()

    def _build_ui(self):
        canvas = tk.Canvas(self, borderwidth=0)
        scrollbar = ttk.Scrollbar(self, orient="vertical", command=canvas.yview)
        inner = ttk.Frame(canvas)
        inner.bind("<Configure>",
                   lambda e: canvas.configure(scrollregion=canvas.bbox("all")))
        canvas.create_window((0, 0), window=inner, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        row = 0

        # Player info header
        p = self._player
        pos_name = POSITION_NAMES.get(p.position, "?")
        ttk.Label(inner, text=f"ID {p.player_id}  |  {pos_name}  |  "
                              f"Age {p.age}  |  Avg {p.skill_avg:.0f}",
                  font=("", 12, "bold")).grid(
            row=row, column=0, columnspan=3, pady=(8, 12), padx=8, sticky="w")
        row += 1

        # Info fields
        ttk.Label(inner, text="Player Info",
                  font=("", 11, "bold")).grid(
            row=row, column=0, columnspan=3, pady=(8, 4), padx=8, sticky="w")
        row += 1

        for label, attr, lo, hi in self._INFO_FIELDS:
            ttk.Label(inner, text=label).grid(row=row, column=0, padx=(12, 4),
                                              sticky="e")
            var = tk.IntVar(value=getattr(p, attr))
            self._vars[attr] = var
            spin = ttk.Spinbox(inner, from_=lo, to=hi, textvariable=var,
                               width=6)
            spin.grid(row=row, column=1, padx=4, sticky="w")
            row += 1

        # Skills (0-200 sliders + spinboxes)
        ttk.Label(inner, text="Skills (0–200)",
                  font=("", 11, "bold")).grid(
            row=row, column=0, columnspan=3, pady=(12, 4), padx=8, sticky="w")
        row += 1

        for label, attr in self._SKILL_FIELDS:
            ttk.Label(inner, text=label).grid(row=row, column=0, padx=(12, 4),
                                              sticky="e")
            var = tk.IntVar(value=getattr(p, attr))
            self._vars[attr] = var
            scale = ttk.Scale(inner, from_=0, to=200, variable=var,
                              orient=tk.HORIZONTAL, length=180)
            scale.grid(row=row, column=1, padx=4, sticky="w")
            spin = ttk.Spinbox(inner, from_=0, to=200, textvariable=var,
                               width=5)
            spin.grid(row=row, column=2, padx=4, sticky="w")
            row += 1

        # Career stats
        ttk.Label(inner, text="Career Stats",
                  font=("", 11, "bold")).grid(
            row=row, column=0, columnspan=3, pady=(12, 4), padx=8, sticky="w")
        row += 1

        for label, attr in self._STAT_FIELDS:
            ttk.Label(inner, text=label).grid(row=row, column=0, padx=(12, 4),
                                              sticky="e")
            var = tk.IntVar(value=getattr(p, attr))
            self._vars[attr] = var
            spin = ttk.Spinbox(inner, from_=0, to=255, textvariable=var,
                               width=6)
            spin.grid(row=row, column=1, padx=4, sticky="w")
            row += 1

        # Buttons
        btn_frame = ttk.Frame(inner)
        btn_frame.grid(row=row, column=0, columnspan=3, pady=12)
        ttk.Button(btn_frame, text="Apply to ADF",
                   command=self._apply).pack(side=tk.LEFT, padx=8)
        ttk.Button(btn_frame, text="Reset",
                   command=self._reset).pack(side=tk.LEFT, padx=8)
        ttk.Button(btn_frame, text="Max All Skills",
                   command=self._max_skills).pack(side=tk.LEFT, padx=8)

    def _apply(self):
        """Copy UI values into the PlayerRecord and write to ADF."""
        p = self._player
        for attr, var in self._vars.items():
            val = var.get()
            val = max(0, min(255, val))
            setattr(p, attr, val)
        db_offset = self._dir_entry.byte_offset + self._dir_entry.size_bytes
        records_start = db_offset + PLAYER_DB_HEADER_SIZE
        off = records_start + p.player_id * PLAYER_RECORD_SIZE
        if off + PLAYER_RECORD_SIZE <= ADF_SIZE:
            self._adf.write_bytes(off, p.pack())
        if self._on_save:
            self._on_save()
        messagebox.showinfo("Applied",
                            f"Player #{p.player_id} updated in ADF buffer.\n"
                            "Use File → Save to write to disk.",
                            parent=self)

    def _reset(self):
        """Reset UI vars to current PlayerRecord values."""
        p = self._player
        for attr, var in self._vars.items():
            var.set(getattr(p, attr))

    def _max_skills(self):
        """Set all 10 skills to 200."""
        for _, attr in self._SKILL_FIELDS:
            self._vars[attr].set(200)


# ─── Disassembler Window ────────────────────────────────────────────

class DisassemblerWindow(tk.Toplevel):
    """Interactive 68000 disassembler and cross-reference browser for
    the decompressed Player Manager game image."""

    def __init__(self, parent, game_disk):
        super().__init__(parent)
        self.title("68000 Disassembler — Game Image")
        self.geometry("900x750")
        self.resizable(True, True)

        self._gd = game_disk
        self._disasm = Disasm68k(game_disk.game_image, base_addr=0)
        self._history = []        # Navigation history (list of offsets)

        self._build_ui()
        # Start at the entry point
        self._goto(0)

    def _build_ui(self):
        # Top bar: navigation
        nav = ttk.Frame(self)
        nav.pack(fill=tk.X, padx=8, pady=6)

        ttk.Label(nav, text="Address:").pack(side=tk.LEFT, padx=4)
        self._addr_var = tk.StringVar(value="$000000")
        addr_entry = ttk.Entry(nav, textvariable=self._addr_var, width=10,
                               font=(_MONO, 12))
        addr_entry.pack(side=tk.LEFT, padx=4)
        addr_entry.bind('<Return>', lambda e: self._go_to_addr())

        ttk.Button(nav, text="Go", command=self._go_to_addr).pack(side=tk.LEFT, padx=2)
        ttk.Button(nav, text="← Back", command=self._go_back).pack(side=tk.LEFT, padx=8)

        ttk.Label(nav, text="Lines:").pack(side=tk.LEFT, padx=(12, 4))
        self._lines_var = tk.StringVar(value="80")
        ttk.Spinbox(nav, from_=20, to=500, textvariable=self._lines_var,
                    width=5).pack(side=tk.LEFT, padx=2)

        # Quick jumps
        qf = ttk.LabelFrame(self, text="Quick Navigation")
        qf.pack(fill=tk.X, padx=8, pady=2)
        qg = ttk.Frame(qf)
        qg.pack(fill=tk.X, padx=8, pady=4)

        quick_targets = [
            ("Entry ($0000)", 0x0000),
            ("Age ($11740)", 0x11740),
            ("Name char ($1608A)", 0x1608A),
            ("Names table ($15B02)", 0x15B02),
            ("JMP vectors ($134D8)", 0x134D8),
            ("Strings ($14000)", 0x14000),
        ]
        for i, (label, addr) in enumerate(quick_targets):
            ttk.Button(qg, text=label,
                       command=lambda a=addr: self._goto(a)).grid(
                row=0, column=i, padx=3, pady=2)

        # Search tools
        sf = ttk.LabelFrame(self, text="Search / Cross-Reference")
        sf.pack(fill=tk.X, padx=8, pady=2)
        sg = ttk.Frame(sf)
        sg.pack(fill=tk.X, padx=8, pady=4)

        ttk.Label(sg, text="Find references to:").grid(row=0, column=0, sticky='e', padx=4)
        self._xref_var = tk.StringVar()
        ttk.Entry(sg, textvariable=self._xref_var, width=10,
                  font=(_MONO, 11)).grid(row=0, column=1, padx=4)
        ttk.Button(sg, text="X-Ref", command=self._do_xref).grid(
            row=0, column=2, padx=4)

        ttk.Label(sg, text="Search word:").grid(row=0, column=3, sticky='e', padx=(12, 4))
        self._sword_var = tk.StringVar()
        ttk.Entry(sg, textvariable=self._sword_var, width=10,
                  font=(_MONO, 11)).grid(row=0, column=4, padx=4)
        ttk.Button(sg, text="Find", command=self._do_word_search).grid(
            row=0, column=5, padx=4)

        ttk.Label(sg, text="MULU/DIVU #imm:").grid(row=1, column=0, sticky='e', padx=4, pady=4)
        self._mulimm_var = tk.StringVar()
        ttk.Entry(sg, textvariable=self._mulimm_var, width=10,
                  font=(_MONO, 11)).grid(row=1, column=1, padx=4, pady=4)
        ttk.Button(sg, text="Find MUL/DIV", command=self._find_muldiv).grid(
            row=1, column=2, padx=4, pady=4)

        # Main disassembly output
        main = ttk.Frame(self)
        main.pack(fill=tk.BOTH, expand=True, padx=8, pady=4)

        self._text = tk.Text(main, font=(_MONO, 11), wrap='none',
                             bg='#1e1e1e', fg='#d4d4d4', insertbackground='white',
                             state='disabled')
        vsb = ttk.Scrollbar(main, orient='vertical', command=self._text.yview)
        hsb = ttk.Scrollbar(main, orient='horizontal', command=self._text.xview)
        self._text.configure(yscrollcommand=vsb.set, xscrollcommand=hsb.set)
        vsb.pack(side=tk.RIGHT, fill=tk.Y)
        hsb.pack(side=tk.BOTTOM, fill=tk.X)
        self._text.pack(fill=tk.BOTH, expand=True)

        # Tag colors
        self._text.tag_configure('addr', foreground='#569CD6')
        self._text.tag_configure('mnemonic', foreground='#DCDCAA')
        self._text.tag_configure('hex', foreground='#6A9955')
        self._text.tag_configure('comment', foreground='#6A9955')
        self._text.tag_configure('header', foreground='#CE9178')
        self._text.tag_configure('xref_result', foreground='#4EC9B0')

        # Double-click to follow address
        self._text.bind('<Double-Button-1>', self._on_double_click)

        # Status
        self._status = tk.StringVar(value="Ready")
        ttk.Label(self, textvariable=self._status, relief='sunken',
                  anchor='w').pack(fill=tk.X, side=tk.BOTTOM, padx=2, pady=2)

    def _goto(self, addr):
        self._history.append(addr)
        self._addr_var.set(f'${addr:06X}')
        self._disasm_at(addr)

    def _go_to_addr(self):
        try:
            addr = _parse_hex_str(self._addr_var.get())
        except ValueError:
            return
        self._goto(addr)

    def _go_back(self):
        if len(self._history) > 1:
            self._history.pop()
            addr = self._history[-1]
            self._addr_var.set(f'${addr:06X}')
            self._disasm_at(addr)

    def _disasm_at(self, addr):
        try:
            num_lines = int(self._lines_var.get())
        except ValueError:
            num_lines = 80

        t = self._text
        t.config(state='normal')
        t.delete('1.0', tk.END)

        # Header
        t.insert(tk.END, f"; Disassembly at ${addr:06X}\n", 'header')
        t.insert(tk.END, f"; Game image: {len(self._gd.game_image)} bytes "
                         f"({len(self._gd.game_image) // 1024}K)\n\n", 'header')

        off = addr
        count = 0
        while count < num_lines and off < len(self._gd.game_image):
            a, mne, n = self._disasm.disasm_one(off)
            raw = self._gd.game_image[off:off + n]
            hex_str = ' '.join(f'{b:02X}' for b in raw)

            t.insert(tk.END, f'${a:06X}', 'addr')
            t.insert(tk.END, f'  {hex_str:<20s}', 'hex')
            t.insert(tk.END, f'  {mne}', 'mnemonic')

            # Auto-annotate known offsets
            comment = self._auto_comment(a, mne)
            if comment:
                t.insert(tk.END, f'  ; {comment}', 'comment')
            t.insert(tk.END, '\n')

            off += n
            count += 1

        t.config(state='disabled')
        self._status.set(f"Showing {count} instructions from ${addr:06X}")

    def _auto_comment(self, addr, mne):
        """Generate automatic comments for known addresses and patterns."""
        comments = []
        if '$011740' in mne:
            comments.append('Manager age (displayed = stored + 1)')
        if '$01608A' in mne:
            comments.append('Manager name character')
        if '$015B02' in mne:
            comments.append('Player name table start')
        if '$0162E6' in mne:
            comments.append('Player name table end')
        if '$050000' in mne or '$50000' in mne.replace(' ', ''):
            comments.append('Game image base address')
        if 'MULU' in mne and '#$0064' in mne:
            comments.append('× 100 (team record size)')
        if 'DIVU' in mne and '#$0064' in mne:
            comments.append('÷ 100 (team record size)')
        if 'MULU' in mne and '#$002A' in mne:
            comments.append('× 42')
        if '$DFF09A' in mne:
            comments.append('INTENA')
        if '$DFF096' in mne:
            comments.append('DMACON')
        return ', '.join(comments)

    def _on_double_click(self, event):
        """Double-click an address in the disassembly to navigate there."""
        idx = self._text.index(f'@{event.x},{event.y}')
        line = self._text.get(f'{idx} linestart', f'{idx} lineend')
        # Look for $XXXXXX patterns in the line
        import re
        matches = re.findall(r'\$([0-9A-Fa-f]{4,8})', line)
        if matches:
            # Navigate to the last address-like match (skip the line's own address)
            for m in reversed(matches):
                val = int(m, 16)
                if val < len(self._gd.game_image) and val != self._history[-1]:
                    self._goto(val)
                    return

    def _do_xref(self):
        """Find all instructions referencing a given address."""
        try:
            target = _parse_hex_str(self._xref_var.get())
        except ValueError:
            return

        self._status.set(f"Searching cross-references to ${target:06X}...")
        self.update()

        code_end = min(len(self._gd.game_image), 0x134D8)
        results = self._disasm.xref_search(target, 0, code_end)

        t = self._text
        t.config(state='normal')
        t.delete('1.0', tk.END)
        t.insert(tk.END, f"; Cross-references to ${target:06X}\n", 'header')
        t.insert(tk.END, f"; Searched ${0:06X}–${code_end:06X} "
                         f"({len(results)} results)\n\n", 'header')

        for a, mne, n in results:
            raw = self._gd.game_image[a:a + n]
            hex_str = ' '.join(f'{b:02X}' for b in raw)
            t.insert(tk.END, f'${a:06X}', 'addr')
            t.insert(tk.END, f'  {hex_str:<20s}', 'hex')
            t.insert(tk.END, f'  {mne}\n', 'xref_result')

        if not results:
            t.insert(tk.END, '  (no references found)\n')

        t.config(state='disabled')
        self._status.set(f"Found {len(results)} references to ${target:06X}")

    def _do_word_search(self):
        """Find occurrences of a 16-bit word in the code region."""
        try:
            word = _parse_hex_str(self._sword_var.get()) & 0xFFFF
        except ValueError:
            return

        self._status.set(f"Searching for word ${word:04X}...")
        self.update()

        code_end = min(len(self._gd.game_image), 0x134D8)
        results = []
        for off in range(0, code_end, 2):
            if _read16(self._gd.game_image, off) == word:
                a, mne, n = self._disasm.disasm_one(off)
                results.append((a, mne, n))

        t = self._text
        t.config(state='normal')
        t.delete('1.0', tk.END)
        t.insert(tk.END, f"; Search for word ${word:04X}\n", 'header')
        t.insert(tk.END, f"; {len(results)} occurrences in code region\n\n", 'header')

        for a, mne, n in results[:200]:
            raw = self._gd.game_image[a:a + n]
            hex_str = ' '.join(f'{b:02X}' for b in raw)
            t.insert(tk.END, f'${a:06X}', 'addr')
            t.insert(tk.END, f'  {hex_str:<20s}', 'hex')
            t.insert(tk.END, f'  {mne}\n', 'xref_result')

        if len(results) > 200:
            t.insert(tk.END, f'\n  ... and {len(results) - 200} more\n')

        t.config(state='disabled')
        self._status.set(f"Found {len(results)} occurrences of ${word:04X}")

    def _find_muldiv(self):
        """Find all MULU/MULS/DIVU/DIVS with a specific immediate value."""
        try:
            val = int(self._mulimm_var.get().strip().replace('$', '').replace('0x', ''), 0)
        except ValueError:
            try:
                val = int(self._mulimm_var.get().strip())
            except ValueError:
                return

        self._status.set(f"Searching MULU/DIVU #{val}...")
        self.update()

        code_end = min(len(self._gd.game_image), 0x134D8)
        results = []
        off = 0
        while off < code_end:
            a, mne, n = self._disasm.disasm_one(off)
            if ('MULU' in mne or 'MULS' in mne or 'DIVU' in mne or 'DIVS' in mne):
                # Check if the immediate matches
                imm_hex4 = f'#${val:04X}'
                imm_hex2 = f'#${val:02X}'
                if imm_hex4 in mne or imm_hex2 in mne:
                    results.append((a, mne, n))
            off += n

        t = self._text
        t.config(state='normal')
        t.delete('1.0', tk.END)
        t.insert(tk.END, f"; MULU/MULS/DIVU/DIVS with immediate #{val} (${val:04X})\n", 'header')
        t.insert(tk.END, f"; {len(results)} results\n\n", 'header')

        for a, mne, n in results:
            raw = self._gd.game_image[a:a + n]
            hex_str = ' '.join(f'{b:02X}' for b in raw)
            t.insert(tk.END, f'${a:06X}', 'addr')
            t.insert(tk.END, f'  {hex_str:<20s}', 'hex')
            t.insert(tk.END, f'  {mne}', 'xref_result')
            comment = self._auto_comment(a, mne)
            if comment:
                t.insert(tk.END, f'  ; {comment}', 'comment')
            t.insert(tk.END, '\n')

        t.config(state='disabled')
        self._status.set(f"Found {len(results)} MULU/DIVU #{val}")


# ─── Main ────────────────────────────────────────────────────────────

def main():
    root = tk.Tk()

    # Retina / HiDPI scaling on macOS
    if _IS_MAC:
        try:
            root.tk.call('tk', 'scaling', 2.0)
        except tk.TclError:
            pass

    # Theme: prefer clam (works on all platforms); aqua is macOS-only
    style = ttk.Style()
    if 'clam' in style.theme_names():
        style.theme_use('clam')

    app = PMSaveDiskToolApp(root)
    root.mainloop()


if __name__ == '__main__':
    main()
