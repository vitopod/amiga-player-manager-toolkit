"""Player record parsing and serialization.

Each player is stored as a 42-byte record in the player database that
follows each .sav file on the save disk. Fields are single bytes except
for the 4-byte RNG seed at offset 0.
"""

import struct
from dataclasses import dataclass, field, fields
from enum import IntEnum

RECORD_SIZE = 42
PLAYER_DB_HEADER_SIZE = 2
TOTAL_PLAYERS = 1536

POSITION_NAMES = {0: "???", 1: "GK", 2: "DEF", 3: "MID", 4: "FWD"}

SKILL_NAMES = [
    "stamina", "resilience", "pace", "agility", "aggression",
    "flair", "passing", "shooting", "tackling", "keeping",
]

SKILL_OFFSETS = {name: 0x0A + i for i, name in enumerate(SKILL_NAMES)}

# Byte layout of the 42-byte player record: (offset, size, field_name, note).
# Used by the Byte Workbench and annotation tooling — the single source of
# truth for "what lives at which offset".
FIELD_LAYOUT: list[tuple[int, int, str, str]] = [
    (0x00, 4, "rng_seed", "Drives procedural name generation"),
    (0x04, 1, "age", ""),
    (0x05, 1, "position", "1=GK 2=DEF 3=MID 4=FWD"),
    (0x06, 1, "division", ""),
    (0x07, 1, "team_index", "0xFF = free agent"),
    (0x08, 1, "height", ""),
    (0x09, 1, "weight", ""),
    (0x0A, 1, "stamina", ""),
    (0x0B, 1, "resilience", ""),
    (0x0C, 1, "pace", ""),
    (0x0D, 1, "agility", ""),
    (0x0E, 1, "aggression", "Stored inverted on disk: raw = 200 - displayed"),
    (0x0F, 1, "flair", ""),
    (0x10, 1, "passing", ""),
    (0x11, 1, "shooting", ""),
    (0x12, 1, "tackling", ""),
    (0x13, 1, "keeping", ""),
    (0x14, 1, "reserved", "Always 0 in observed data"),
    (0x15, 1, "injury_weeks", "Meaning unconfirmed; not used as injury indicator"),
    (0x16, 1, "disciplinary", ""),
    (0x17, 1, "morale", ""),
    (0x18, 1, "value", ""),
    (0x19, 1, "weeks_since_transfer", "Post-transfer cooldown, not a listed flag"),
    (0x1A, 1, "mystery3", "bit 0x80 = is_transfer_listed; lower 7 bits TBD"),
    (0x1B, 1, "reserved2", "Nearly always 0 (1033/1035 observed)"),
    (0x1C, 1, "injuries_this_year", ""),
    (0x1D, 1, "injuries_last_year", ""),
    (0x1E, 1, "dsp_pts_this_year", ""),
    (0x1F, 1, "dsp_pts_last_year", ""),
    (0x20, 1, "goals_this_year", ""),
    (0x21, 1, "goals_last_year", ""),
    (0x22, 1, "matches_this_year", ""),
    (0x23, 1, "matches_last_year", ""),
    (0x24, 1, "div1_years", ""),
    (0x25, 1, "div2_years", ""),
    (0x26, 1, "div3_years", ""),
    (0x27, 1, "div4_years", ""),
    (0x28, 1, "int_years", ""),
    (0x29, 1, "contract_years", "Observed 1..5"),
]


def field_at_offset(offset: int) -> tuple[str, int, int]:
    """Return (field_name, sub_index_in_field, field_size) for a byte offset.

    For a byte inside a multi-byte field (e.g. rng_seed), sub_index is the
    byte position within that field (0..field_size-1).
    """
    if not 0 <= offset < RECORD_SIZE:
        raise IndexError(f"offset {offset} out of range [0, {RECORD_SIZE})")
    for off, size, name, _ in FIELD_LAYOUT:
        if off <= offset < off + size:
            return name, offset - off, size
    raise IndexError(f"no field covers offset {offset}")


class Position(IntEnum):
    UNKNOWN = 0
    GK = 1
    DEF = 2
    MID = 3
    FWD = 4

    def __str__(self):
        return self.name


@dataclass
class PlayerRecord:
    """A single 42-byte player record from the save disk."""
    player_id: int = 0  # Not stored in record, set by caller

    # Bytes +00-03: RNG seed
    rng_seed: int = 0

    # Byte +04-07: Core attributes
    age: int = 0
    position: int = 0
    division: int = 0
    team_index: int = 0xFF  # 0xFF = free agent

    # Bytes +08-09: Physical
    height: int = 0
    weight: int = 0

    # Bytes +0A-13: Skills (0-200).
    # NOTE: aggression is stored INVERTED on disk — the raw byte at 0x0E is
    # 200 - displayed. The dataclass holds the displayed (in-game) value; the
    # parse/serialize functions perform the inversion. This matches what the
    # game shows in the stats screen (low = calm, high = aggressive).
    stamina: int = 0
    resilience: int = 0
    pace: int = 0
    agility: int = 0
    aggression: int = 0
    flair: int = 0
    passing: int = 0
    shooting: int = 0
    tackling: int = 0
    keeping: int = 0

    # Byte +14: Reserved — observed to be 0 for every real player in Save1_PM
    # (1031/1031). Preserved in round-trip serialization.
    reserved: int = 0

    # Bytes +15-1A: Status
    injury_weeks: int = 0
    disciplinary: int = 0
    morale: int = 0
    value: int = 0
    weeks_since_transfer: int = 0  # Originally "transfer_weeks" in UB's notes; empirical testing shows it is a post-transfer cooldown, NOT a "listed for sale" flag.
    # mystery3 bit layout (Save1_PM, 1031 real players):
    #   bit 7 (0x80) — is_transfer_listed (on in-game LISTA TRASFERIMENTI)
    #   bit 5 (0x20) — never set in observed data
    #   bits 0,1,4   — combined value 0x13 (=19) appears 131 times; 126 of those
    #                  are free agents. Likely a free-agent / offered-out marker.
    #   bits 0,1     — combined value 0x12 (=18) appears 31 times, all with team,
    #                  avg age ~31. Likely a veteran / end-of-career marker.
    #   bits 2,3,6   — rarely set; semantics unidentified.
    # Treat the whole byte as opaque except for the known 0x80 flag.
    mystery3: int = 0

    # Byte +1B: Second reserved byte. Observed to be 0 for 1033/1035 real
    # players in Save1_PM. Preserved in round-trip serialization.
    reserved2: int = 0

    # Bytes +1C-23: Season stats
    injuries_this_year: int = 0
    injuries_last_year: int = 0
    dsp_pts_this_year: int = 0
    dsp_pts_last_year: int = 0
    goals_this_year: int = 0
    goals_last_year: int = 0
    matches_this_year: int = 0
    matches_last_year: int = 0

    # Bytes +24-29: Career (years played per division, internationals, and
    # remaining contract length). Verified against in-game career screen.
    div1_years: int = 0
    div2_years: int = 0
    div3_years: int = 0
    div4_years: int = 0
    int_years: int = 0
    contract_years: int = 0

    @property
    def position_name(self) -> str:
        return POSITION_NAMES.get(self.position, "???")

    @property
    def is_free_agent(self) -> bool:
        return self.team_index == 0xFF

    @property
    def is_transfer_listed(self) -> bool:
        """True if the player is on the in-game LISTA TRASFERIMENTI.

        The high bit (0x80) of mystery3 (byte 0x1A) is set for all players
        that appear on the in-game transfer list. Verified by cross-
        referencing the 9 visible entries of LISTA TRASFERIMENTI against
        the DB: all 9 have this bit set. The lower 7 bits of mystery3 vary
        independently and are not yet identified.
        """
        return bool(self.mystery3 & 0x80)

    @property
    def is_market_available(self) -> bool:
        """True if the player can be acquired: free agent or on the transfer list."""
        return self.is_free_agent or self.is_transfer_listed

    @property
    def skills(self) -> dict[str, int]:
        return {name: getattr(self, name) for name in SKILL_NAMES}

    @property
    def total_skill(self) -> int:
        return sum(self.skills.values())


def parse_player(data: bytes, player_id: int = 0) -> PlayerRecord:
    """Parse a 42-byte player record.

    Args:
        data: Exactly 42 bytes of player record data.
        player_id: The player's index in the database (0-based).
    """
    if len(data) < RECORD_SIZE:
        raise ValueError(f"Player record too short: {len(data)} < {RECORD_SIZE}")
    d = data[:RECORD_SIZE]
    return PlayerRecord(
        player_id=player_id,
        rng_seed=struct.unpack(">I", d[0:4])[0],
        age=d[4],
        position=d[5],
        division=d[6],
        team_index=d[7],
        height=d[8],
        weight=d[9],
        stamina=d[10],
        resilience=d[11],
        pace=d[12],
        agility=d[13],
        # Aggression is inverted on disk: displayed = 200 - raw byte.
        aggression=200 - d[14],
        flair=d[15],
        passing=d[16],
        shooting=d[17],
        tackling=d[18],
        keeping=d[19],
        reserved=d[20],
        injury_weeks=d[21],
        disciplinary=d[22],
        morale=d[23],
        value=d[24],
        weeks_since_transfer=d[25],
        mystery3=d[26],
        reserved2=d[27],
        injuries_this_year=d[28],
        injuries_last_year=d[29],
        dsp_pts_this_year=d[30],
        dsp_pts_last_year=d[31],
        goals_this_year=d[32],
        goals_last_year=d[33],
        matches_this_year=d[34],
        matches_last_year=d[35],
        div1_years=d[36],
        div2_years=d[37],
        div3_years=d[38],
        div4_years=d[39],
        int_years=d[40],
        contract_years=d[41],
    )


def serialize_player(player: PlayerRecord) -> bytes:
    """Serialize a PlayerRecord back to 42 bytes.

    Round-trip with parse_player is byte-identical: aggression is inverted
    (raw = 200 - displayed) to cancel the inversion done on parse.
    """
    return (
        struct.pack(">I", player.rng_seed)
        + bytes([
            player.age,
            player.position,
            player.division,
            player.team_index,
            player.height,
            player.weight,
            player.stamina,
            player.resilience,
            player.pace,
            player.agility,
            (200 - player.aggression) & 0xFF,
            player.flair,
            player.passing,
            player.shooting,
            player.tackling,
            player.keeping,
            player.reserved,
            player.injury_weeks,
            player.disciplinary,
            player.morale,
            player.value,
            player.weeks_since_transfer,
            player.mystery3,
            player.reserved2,
            player.injuries_this_year,
            player.injuries_last_year,
            player.dsp_pts_this_year,
            player.dsp_pts_last_year,
            player.goals_this_year,
            player.goals_last_year,
            player.matches_this_year,
            player.matches_last_year,
            player.div1_years,
            player.div2_years,
            player.div3_years,
            player.div4_years,
            player.int_years,
            player.contract_years,
        ])
    )
