"""Reverse-engineering workbench for the 42-byte player record.

This module turns the ad-hoc process that cracked ``mystery3`` bit 0x80 (manual
byte-diffing of the nine visible LISTA TRASFERIMENTI players against the rest
of the DB) into reusable primitives:

- :func:`byte_histogram` — value distribution at an offset, optionally masked.
- :func:`bit_probability` — P(bit set) over a set of players.
- :func:`diff_sets` — rank bits by how strongly they discriminate set A from B.
- :func:`query` — select players by a raw byte/bit predicate.

All functions operate on iterables of :class:`~pm_core.player.PlayerRecord`.
The GUI's Byte Workbench and the ``byte-stats`` / ``byte-diff`` CLI subcommands
are thin wrappers around these.
"""

from collections import Counter
from dataclasses import dataclass
from typing import Callable, Iterable

from .player import (
    PlayerRecord, RECORD_SIZE, FIELD_LAYOUT,
    field_at_offset, serialize_player,
)

__all__ = [
    "byte_histogram", "bit_probability", "diff_sets", "query",
    "raw_bytes", "BitDiff", "FIELD_LAYOUT", "field_at_offset",
]


def raw_bytes(player: PlayerRecord) -> bytes:
    """Return the 42-byte serialized form of a single player."""
    return serialize_player(player)


def _validate_offset(offset: int) -> None:
    if not 0 <= offset < RECORD_SIZE:
        raise ValueError(f"offset {offset} out of range [0, {RECORD_SIZE})")


def _validate_mask(mask: int) -> None:
    if not 0 <= mask <= 0xFF:
        raise ValueError(f"mask {mask} must be in [0, 0xFF]")


def _validate_single_bit(bit: int) -> None:
    if not (1 <= bit <= 0x80 and bin(bit).count("1") == 1):
        raise ValueError(
            f"bit must be a single-bit mask in [0x01, 0x80], got {bit:#x}"
        )


def byte_histogram(players: Iterable[PlayerRecord], offset: int,
                   mask: int = 0xFF) -> Counter:
    """Count occurrences of ``(byte & mask)`` at ``offset`` across ``players``."""
    _validate_offset(offset)
    _validate_mask(mask)
    counter: Counter = Counter()
    for p in players:
        counter[serialize_player(p)[offset] & mask] += 1
    return counter


def bit_probability(players: Iterable[PlayerRecord], offset: int, bit: int) -> float:
    """Return the fraction of players with ``bit`` set at ``offset``.

    ``bit`` must be a single-bit mask (0x01, 0x02, 0x04, …, 0x80).
    Empty input returns 0.0.
    """
    _validate_offset(offset)
    _validate_single_bit(bit)
    plist = list(players)
    if not plist:
        return 0.0
    hit = sum(1 for p in plist if serialize_player(p)[offset] & bit)
    return hit / len(plist)


@dataclass
class BitDiff:
    """A single-bit discrimination result for set A vs set B."""
    offset: int
    bit: int               # single-bit mask (0x01..0x80)
    bit_index: int         # 0..7 (0 = LSB, 7 = MSB)
    p_a: float             # P(bit=1|A)
    p_b: float             # P(bit=1|B)
    delta: float           # |p_a - p_b|
    field_name: str        # field this byte belongs to
    field_byte: int        # sub-index within the field

    @property
    def bit_label(self) -> str:
        """Human-readable location, e.g. ``'mystery3 bit 7 (0x80)'``."""
        return f"{self.field_name} bit {self.bit_index} ({self.bit:#04x})"


def diff_sets(set_a: Iterable[PlayerRecord], set_b: Iterable[PlayerRecord],
              top_n: int = 20) -> list[BitDiff]:
    """Rank the bits that most discriminate set A from set B.

    For every bit in the 42-byte record (42 × 8 = 336 bits) computes
    ``|P(bit=1|A) - P(bit=1|B)|`` and returns the top ``top_n`` bits by that
    delta, ignoring bits that are constant across both sets. Bits that are
    already identified (via :data:`FIELD_LAYOUT` notes) still appear — they
    just serve as useful sanity anchors.

    Either empty set short-circuits to ``[]``.
    """
    a = list(set_a)
    b = list(set_b)
    if not a or not b:
        return []
    raw_a = [serialize_player(p) for p in a]
    raw_b = [serialize_player(p) for p in b]
    len_a, len_b = len(raw_a), len(raw_b)
    diffs: list[BitDiff] = []
    for offset in range(RECORD_SIZE):
        name, sub, _size = field_at_offset(offset)
        for bit_index in range(8):
            bit = 1 << bit_index
            hits_a = sum(1 for rec in raw_a if rec[offset] & bit)
            hits_b = sum(1 for rec in raw_b if rec[offset] & bit)
            p_a = hits_a / len_a
            p_b = hits_b / len_b
            delta = abs(p_a - p_b)
            if delta == 0.0:
                continue
            diffs.append(BitDiff(
                offset=offset, bit=bit, bit_index=bit_index,
                p_a=p_a, p_b=p_b, delta=delta,
                field_name=name, field_byte=sub,
            ))
    diffs.sort(key=lambda d: d.delta, reverse=True)
    return diffs[:top_n]


_OPS: dict[str, Callable[[int, int], bool]] = {
    "==": lambda x, y: x == y,
    "!=": lambda x, y: x != y,
    "<":  lambda x, y: x < y,
    "<=": lambda x, y: x <= y,
    ">":  lambda x, y: x > y,
    ">=": lambda x, y: x >= y,
}


def query(players: Iterable[PlayerRecord], offset: int, value: int,
          mask: int = 0xFF, op: str = "==") -> list[PlayerRecord]:
    """Return players where ``(raw_byte[offset] & mask) <op> value``.

    ``op`` is one of ``==``, ``!=``, ``<``, ``<=``, ``>``, ``>=``. This is
    deliberately raw-byte oriented: use ``mask=0x80, op='=='`` to find a
    specific bit set (the caller should set ``value=0x80`` too), or use
    ``mask=0xFF`` to compare the whole byte.
    """
    _validate_offset(offset)
    _validate_mask(mask)
    if op not in _OPS:
        raise ValueError(f"unknown op {op!r}; expected one of {list(_OPS)}")
    if not 0 <= value <= 0xFF:
        raise ValueError(f"value {value} must be in [0, 0xFF]")
    fn = _OPS[op]
    return [p for p in players if fn(serialize_player(p)[offset] & mask, value)]
