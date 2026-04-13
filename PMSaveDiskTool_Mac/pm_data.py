#!/usr/bin/env python3
"""
pm_data — data layer for PMSaveDiskTool.
Parses ADF disk images, save files, player databases, game disk structures.
No tkinter dependency — safe for headless/scripting use.
"""

import struct
import os
import sys
import dataclasses

# Export all public AND underscore-prefixed names needed by pm_gui
__all__ = [
    # Platform / UI constants
    '_IS_MAC', '_IS_WIN', '_MOD', '_MOD_DISP', '_MONO',
    # Data constants
    'ADF_SIZE', 'SECTOR_SIZE', 'NUM_SECTORS', 'DIR_SECTOR', 'DIR_ENTRY_SIZE',
    'ADDR_UNIT', 'TEAM_RECORD_SIZE', 'TEAM_NAME_OFFSET', 'MAX_TEAMS',
    'MAX_PLAYER_SLOTS', 'LIGA_NAME_ENTRY_SIZE', 'LIGA_NAME_TEAMS',
    'PLAYER_RECORD_SIZE', 'PLAYER_DB_HEADER_SIZE',
    'POSITION_NAMES', 'SKILL_NAMES',
    # Classes
    'ADF', 'DirEntry', 'TeamRecord', 'SaveFile', 'PlayerRecord',
    'PatchEntry', 'TacticsFile', 'Disasm68k', 'GameDisk',
    # Functions
    'parse_file_table', 'parse_liga_names', 'parse_player_db', 'write_player_db',
    'player_name_str', 'team_name_str', 'build_roster_map',
    '_find_game_disk', '_parse_block1137', '_write_block1137', '_parse_hex_str',
    '_ofs_read_file', '_read16',
    # Game disk constants
    '_PATCH_BLOCK_SECTOR', '_CB_LEA_AT', '_COPYPROT_OFFSETS',
    '_GAME_DISK_FILENAME', '_JMP_A0', '_LEA_50000_A0', '_MAX_PATCH_BYTES',
    '_ZONE_NAMES', 'TAC_NUM_ZONES', 'TAC_NUM_PLAYERS',
]

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
    header_word = struct.unpack_from('>H', header_raw, 0)[0]
    # Genuine player DBs have a header word in range 1–4.
    # If not, this is not a real player database (e.g. start.dat has none).
    if not (1 <= header_word <= 4):
        return {}
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




# ─── Shared Helpers ─────────────────────────────────────────────────

def player_name_str(game_disk, pid):
    """Return player surname from GameDisk, or '#<pid>' as fallback."""
    if game_disk:
        n = game_disk.player_name(pid)
        if n:
            return n
    return f"#{pid}"


def team_name_str(liga, team_idx):
    """Return team name from liga_names list, or fallback string."""
    if team_idx == 0xFF:
        return "Free Agent"
    if liga and 0 <= team_idx < len(liga):
        return liga[team_idx]
    return f"Team {team_idx}"


def build_roster_map(save):
    """Return dict pid → team_name from a SaveFile's team rosters."""
    m = {}
    for team in save.teams:
        tname = team.name or f"(team {team.index})"
        for pid in team.player_values:
            if pid != 0xFFFF:
                m[pid] = tname
    return m
