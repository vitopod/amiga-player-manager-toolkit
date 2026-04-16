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

    # Bytes +0A-13: Skills (0-200)
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

    # Byte +14: Reserved
    reserved: int = 0

    # Bytes +15-1A: Status
    injury_weeks: int = 0
    disciplinary: int = 0
    morale: int = 0
    value: int = 0
    transfer_weeks: int = 0
    mystery3: int = 0

    # Bytes +1B-22: Season stats
    injuries_this_year: int = 0
    injuries_last_year: int = 0
    dsp_pts_this_year: int = 0
    dsp_pts_last_year: int = 0
    goals_this_year: int = 0
    goals_last_year: int = 0
    matches_this_year: int = 0
    matches_last_year: int = 0

    # Bytes +23-29: Career
    div1_years: int = 0
    div2_years: int = 0
    div3_years: int = 0
    div4_years: int = 0
    int_years: int = 0
    contract_years: int = 0
    last_byte: int = 0

    @property
    def position_name(self) -> str:
        return POSITION_NAMES.get(self.position, "???")

    @property
    def is_free_agent(self) -> bool:
        return self.team_index == 0xFF

    @property
    def is_market_available(self) -> bool:
        """True if the player can be purchased: free agent or listed for transfer."""
        return self.is_free_agent or self.transfer_weeks > 0

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
        aggression=d[14],
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
        transfer_weeks=d[25],
        mystery3=d[26],
        injuries_this_year=d[27],
        injuries_last_year=d[28],
        dsp_pts_this_year=d[29],
        dsp_pts_last_year=d[30],
        goals_this_year=d[31],
        goals_last_year=d[32],
        matches_this_year=d[33],
        matches_last_year=d[34],
        div1_years=d[35],
        div2_years=d[36],
        div3_years=d[37],
        div4_years=d[38],
        int_years=d[39],
        contract_years=d[40],
        last_byte=d[41],
    )


def serialize_player(player: PlayerRecord) -> bytes:
    """Serialize a PlayerRecord back to 42 bytes."""
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
            player.aggression,
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
            player.transfer_weeks,
            player.mystery3,
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
            player.last_byte,
        ])
    )
