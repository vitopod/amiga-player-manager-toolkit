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

# Formations map position code (1=GK, 2=DEF, 3=MID, 4=FWD) to slot counts.
FORMATIONS = {
    "4-4-2": {1: 1, 2: 4, 3: 4, 4: 2},
    "4-3-3": {1: 1, 2: 4, 3: 3, 4: 3},
    "3-5-2": {1: 1, 2: 3, 3: 5, 4: 2},
}


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

        Filters out garbage/sentinel records that have age > 0 but invalid
        position, out-of-range team indices, or uninitialised physical fields.
        """
        valid_team = p.team_index <= 43 or p.team_index == 0xFF
        valid_position = p.position in (1, 2, 3, 4)
        valid_physical = p.height >= 100 and p.weight > 0
        return p.age > 0 and valid_team and valid_position and valid_physical

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

    def diff_players(self, other: "SaveSlot") -> list[dict]:
        """Return per-player diffs between this slot and another.

        Each diff is a dict with player_id, a mapping of field -> (old, new)
        for fields that changed, plus convenience aggregates:
          - skill_delta: total_skill(new) - total_skill(old)
          - age_delta:   age(new) - age(old)
          - team_changed: bool
        Only real players in either slot are considered; unreal entries produce
        no diff entry.
        """
        import dataclasses as _dc
        n = min(len(self.players), len(other.players))
        results: list[dict] = []
        for pid in range(n):
            a = self.players[pid]
            b = other.players[pid]
            if not (self._is_real_player(a) or self._is_real_player(b)):
                continue
            changed = {}
            for f in _dc.fields(a):
                if f.name == "player_id":
                    continue
                va = getattr(a, f.name)
                vb = getattr(b, f.name)
                if va != vb:
                    changed[f.name] = (va, vb)
            if not changed:
                continue
            results.append({
                "player_id": pid,
                "changed": changed,
                "skill_delta": b.total_skill - a.total_skill,
                "age_delta": b.age - a.age,
                "team_changed": a.team_index != b.team_index,
                "old": a,
                "new": b,
            })
        return results

    def squad_summary(self, team_index: int) -> dict:
        """Return a summary dict describing the squad of a single team.

        Keys:
            team_name, size, by_position (dict position_name->count),
            avg_age, avg_skill, min_age, max_age, youngest, oldest, best,
            on_market (int).
        """
        roster = [p for p in self.get_players_by_team(team_index)
                  if self._is_real_player(p)]
        by_pos = {"GK": 0, "DEF": 0, "MID": 0, "FWD": 0}
        for p in roster:
            if p.position_name in by_pos:
                by_pos[p.position_name] += 1

        def _safe(key, seq):
            return key(seq) if seq else None

        return {
            "team_index": team_index,
            "team_name": self.get_team_name(team_index),
            "size": len(roster),
            "by_position": by_pos,
            "avg_age": (sum(p.age for p in roster) / len(roster)) if roster else 0.0,
            "avg_skill": (sum(p.total_skill for p in roster) / len(roster)) if roster else 0.0,
            "min_age": _safe(lambda s: min(p.age for p in s), roster),
            "max_age": _safe(lambda s: max(p.age for p in s), roster),
            "youngest": _safe(lambda s: min(s, key=lambda p: p.age), roster),
            "oldest": _safe(lambda s: max(s, key=lambda p: p.age), roster),
            "best": _safe(lambda s: max(s, key=lambda p: p.total_skill), roster),
            "on_market": sum(1 for p in roster if p.is_market_available),
        }

    def all_squad_summaries(self) -> list[dict]:
        """Summaries for every real team that has at least one player."""
        summaries = []
        for i in range(NUM_TEAMS):
            s = self.squad_summary(i)
            if s["size"] > 0:
                summaries.append(s)
        return summaries

    def best_xi(self, formation: str = "4-4-2", *,
                filter_fn=None, max_per_team: int = None) -> list[PlayerRecord]:
        """Select the top XI for a given formation.

        Returns players ordered GK → DEF → MID → FWD. Within each position,
        players are sorted by total_skill descending, picked greedily while
        respecting max_per_team (free agents are exempt from the cap).

        Args:
            formation: Key from FORMATIONS (e.g. "4-4-2").
            filter_fn: Optional extra predicate applied on top of _is_real_player.
            max_per_team: If set, cap selections per team_index (0xFF exempt).
        """
        if formation not in FORMATIONS:
            raise ValueError(
                f"Unknown formation {formation!r}. Available: {list(FORMATIONS)}"
            )
        slots = FORMATIONS[formation]

        pool = [p for p in self.players if self._is_real_player(p)]
        if filter_fn is not None:
            pool = [p for p in pool if filter_fn(p)]

        selected: list[PlayerRecord] = []
        team_counts: dict[int, int] = {}
        for pos in (1, 2, 3, 4):
            need = slots[pos]
            candidates = sorted(
                (p for p in pool if p.position == pos),
                key=lambda p: p.total_skill,
                reverse=True,
            )
            picked = 0
            for p in candidates:
                if picked >= need:
                    break
                if (max_per_team is not None
                        and p.team_index != 0xFF
                        and team_counts.get(p.team_index, 0) >= max_per_team):
                    continue
                selected.append(p)
                team_counts[p.team_index] = team_counts.get(p.team_index, 0) + 1
                picked += 1
        return selected
