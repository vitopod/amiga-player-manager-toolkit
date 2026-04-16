"""Save file handler — ties together ADF, team names, and player database.

A save slot (e.g. pm1.sav) contains 44 teams × 100 bytes of team data.
Immediately after the save file in the ADF image sits the player database:
a 2-byte BE header followed by 1536 player records of 42 bytes each.
"""

import struct
from .adf import ADF, FileEntry
from .player import (
    PlayerRecord, parse_player, serialize_player,
    RECORD_SIZE, PLAYER_DB_HEADER_SIZE, TOTAL_PLAYERS,
)

NUM_TEAMS = 44
TEAM_NAME_RECORD_SIZE = 20
TEAM_NAMES_FILE = "PM1.nam"


class SaveSlot:
    """Represents one save slot with its player database.

    Usage:
        adf = ADF.load("Save1_PM.adf")
        slot = SaveSlot(adf, "pm1.sav")
        for p in slot.get_players_by_team(0):
            print(p.age, p.position_name)
        slot.players[42].age = 20
        slot.write_player(42)
        adf.save("Save1_PM.adf")
    """

    def __init__(self, adf: ADF, save_name: str):
        self.adf = adf
        self.entry = adf.find_file(save_name)
        self.team_names = self._load_team_names()
        self.db_header, self.players = self._load_player_db()

    def _load_team_names(self) -> list[str]:
        """Load 44 team names from PM1.nam."""
        try:
            nam_data = self.adf.read_file(TEAM_NAMES_FILE)
        except FileNotFoundError:
            return [f"Team {i}" for i in range(NUM_TEAMS)]
        names = []
        for i in range(NUM_TEAMS):
            rec = nam_data[i * TEAM_NAME_RECORD_SIZE:(i + 1) * TEAM_NAME_RECORD_SIZE]
            null_pos = rec.index(0) if 0 in rec else TEAM_NAME_RECORD_SIZE
            names.append(rec[:null_pos].decode("latin-1", errors="replace"))
        return names

    @property
    def _db_offset(self) -> int:
        """Byte offset of the player database in the ADF image."""
        return self.entry.byte_offset + self.entry.size

    def _load_player_db(self) -> tuple[int, list[PlayerRecord]]:
        """Load the player database that follows the save file."""
        db_off = self._db_offset
        header = struct.unpack(">H", self.adf.read_at(db_off, 2))[0]
        players = []
        base = db_off + PLAYER_DB_HEADER_SIZE
        for i in range(TOTAL_PLAYERS):
            rec_data = self.adf.read_at(base + i * RECORD_SIZE, RECORD_SIZE)
            players.append(parse_player(rec_data, player_id=i))
        return header, players

    def get_player(self, player_id: int) -> PlayerRecord:
        """Get a player by ID (0-based index)."""
        if not 0 <= player_id < len(self.players):
            raise IndexError(f"Player ID {player_id} out of range (0-{len(self.players)-1})")
        return self.players[player_id]

    def get_players_by_team(self, team_index: int) -> list[PlayerRecord]:
        """Get all players belonging to a team."""
        return [p for p in self.players if p.team_index == team_index]

    def get_free_agents(self) -> list[PlayerRecord]:
        """Get all unassigned players."""
        return [p for p in self.players if p.is_free_agent]

    def get_team_name(self, team_index: int) -> str:
        """Get the name of a team by index."""
        if 0 <= team_index < len(self.team_names):
            return self.team_names[team_index]
        if team_index == 0xFF:
            return "Free Agent"
        return f"Team {team_index}"

    def write_player(self, player_id: int) -> None:
        """Write a modified player record back to the ADF image."""
        player = self.get_player(player_id)
        data = serialize_player(player)
        offset = self._db_offset + PLAYER_DB_HEADER_SIZE + player_id * RECORD_SIZE
        self.adf.write_at(offset, data)

    def write_all_players(self) -> None:
        """Write all player records back to the ADF image."""
        for i in range(len(self.players)):
            self.write_player(i)

    @staticmethod
    def _is_real_player(p: PlayerRecord) -> bool:
        """Return True if the record looks like a genuine player.

        Filters out garbage/sentinel records near the end of the database that
        have age > 0 but invalid position or out-of-range team indices.
        """
        valid_team = p.team_index <= 43 or p.team_index == 0xFF
        valid_position = p.position in (1, 2, 3, 4)
        return p.age > 0 and valid_team and valid_position

    def get_young_talents(self, max_age: int = 21) -> list[PlayerRecord]:
        """Players aged ≤ max_age, sorted by total skill descending."""
        return sorted(
            [p for p in self.players if self._is_real_player(p) and p.age <= max_age],
            key=lambda p: p.total_skill,
            reverse=True,
        )

    def get_top_scorers(self) -> list[PlayerRecord]:
        """Real players sorted by division, then goals this year descending."""
        return sorted(
            [p for p in self.players if self._is_real_player(p)],
            key=lambda p: (p.division, -p.goals_this_year),
        )
