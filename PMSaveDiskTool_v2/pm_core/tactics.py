"""Parser/serializer for the `.tac` tactic files stored on PM save disks.

The `.tac` format is shared with Kick Off 2 (both games use Dino Dini's match
engine); the layout below was decoded from the Java editor at
`github.com/ssenegas/tacticaleditor` and cross-verified byte-for-byte against
PM's own `4-4-2.tac` (which is byte-identical to KO2's) and `4-2-4.tac` (the
PM-edited 928-byte shape).

Byte layout
-----------
- **Bytes 0..799 (800 bytes, required):** 20 zones × 10 players × (x, y) as
  big-endian `u16`. Zone order is the :data:`ZONE_NAMES` tuple. The 10 players
  are outfield shirt numbers 2..11 (GK = #1 is implicit and never stored).
  The outer dimension in the file is **player**, inner is **zone**:
  `[p2_z0_x, p2_z0_y, p2_z1_x, ..., p2_z19_y, p3_z0_x, ...]`.
- **Bytes 800..(end) (variable-length trailer):** preserved verbatim.
  Observed sizes on real disks:
  * 928 bytes total → 128-byte trailer, PM-edited tactics. First 2 bytes are
    `\\x00\\x00`, then a NUL-padded ASCII description (e.g. "an attacking
    formation...").
  * 980 bytes total → 180-byte trailer, stock Anco/KO2 templates (sparse
    bitfield around offsets 0x85..0xac; semantics not yet reversed).
  * 1118 bytes has been observed on KO2's `zxcross.tac` (outlier).

This module does not interpret the trailer — it round-trips it byte-exact.
A :attr:`Tactic.description` helper is provided for the 928-byte shape.
"""

from __future__ import annotations

import struct
from dataclasses import dataclass

__all__ = [
    "ZONE_NAMES", "SHIRT_NUMBERS", "NUM_PLAYERS", "NUM_ZONES",
    "POSITIONS_SIZE", "Tactic", "parse_tac", "serialize_tac",
    "tactic_to_json", "tactic_from_json",
]

ZONE_NAMES: tuple[str, ...] = (
    "area1", "area2", "area3", "area4", "area5", "area6",
    "area7", "area8", "area9", "area10", "area11", "area12",
    "kickoff_own", "kickoff_def",
    "goalkick_def", "goalkick_own",
    "corner1", "corner2", "corner3", "corner4",
)

SHIRT_NUMBERS: tuple[int, ...] = tuple(range(2, 12))  # 2..11; GK (#1) implicit.

NUM_PLAYERS = 10
NUM_ZONES = 20
POSITIONS_SIZE = NUM_PLAYERS * NUM_ZONES * 4  # 800 bytes


@dataclass
class Tactic:
    """A parsed `.tac` file.

    :attr:`positions` maps each zone name to a dict of
    shirt-number → (x, y) world coordinate. :attr:`trailer` is the opaque
    byte block past the 800-byte coordinate payload; its length determines
    the total file size on disk.
    """

    positions: dict[str, dict[int, tuple[int, int]]]
    trailer: bytes = b""

    @property
    def total_size(self) -> int:
        return POSITIONS_SIZE + len(self.trailer)

    @property
    def description(self) -> str:
        """Human-readable description text found in the trailer, or ``""``.

        Scans the whole trailer for the longest contiguous run of printable
        ASCII bytes (≥ 8 chars). In practice this picks up PM's NUL-padded
        blurb starting two bytes into the 128-byte trailer (e.g. ``"2-4 an
        attacking formation..."``) without needing to hardcode that offset.
        Returns empty for stock Anco / KO2 980-byte templates, which carry
        no such text.
        """
        best: bytes = b""
        current = bytearray()
        for b in self.trailer:
            if 32 <= b < 127:
                current.append(b)
                continue
            if len(current) > len(best):
                best = bytes(current)
            current.clear()
        if len(current) > len(best):
            best = bytes(current)
        return best.decode("ascii") if len(best) >= 8 else ""

    @property
    def description_is_truncated(self) -> bool:
        """Heuristic: did PM run out of room storing the description?

        PM allocates a fixed ~126-char slot inside the 128-byte trailer and
        writes plain text into it with no overflow handling — long blurbs
        get chopped mid-word (e.g. ``"...wingers and mid"`` should be
        ``"...midfielders"``). We call it truncated when the description is
        long, ends on an alphanumeric character, and is followed by NUL
        padding rather than proper sentence-terminating punctuation.
        """
        desc = self.description
        if len(desc) < 40:
            return False
        last = desc[-1]
        if not last.isalnum():
            return False
        encoded = desc.encode("ascii")
        idx = self.trailer.find(encoded)
        if idx < 0:
            return False
        # Anything past the description must be NUL padding — no follow-up
        # text, no punctuation.
        tail = self.trailer[idx + len(encoded):]
        return len(tail) > 0 and all(b == 0 for b in tail)


def parse_tac(buf: bytes) -> Tactic:
    """Parse a `.tac` file buffer.

    Any buffer of at least 800 bytes is accepted; anything past that is kept
    in :attr:`Tactic.trailer` verbatim for round-trip safety.
    """
    if len(buf) < POSITIONS_SIZE:
        raise ValueError(
            f".tac buffer too small: {len(buf)} bytes "
            f"(need at least {POSITIONS_SIZE})"
        )

    coords = struct.unpack(f">{NUM_PLAYERS * NUM_ZONES * 2}H", buf[:POSITIONS_SIZE])
    positions: dict[str, dict[int, tuple[int, int]]] = {z: {} for z in ZONE_NAMES}
    # Outer loop is player, inner is zone (matches KO2 Tactic.java).
    idx = 0
    for shirt in SHIRT_NUMBERS:
        for zone in ZONE_NAMES:
            x, y = coords[idx], coords[idx + 1]
            positions[zone][shirt] = (x, y)
            idx += 2

    return Tactic(positions=positions, trailer=bytes(buf[POSITIONS_SIZE:]))


def serialize_tac(tactic: Tactic) -> bytes:
    """Serialize a :class:`Tactic` back to its on-disk form.

    `serialize_tac(parse_tac(b)) == b` for any valid `.tac` buffer.
    """
    if set(tactic.positions.keys()) != set(ZONE_NAMES):
        missing = set(ZONE_NAMES) - set(tactic.positions.keys())
        extra = set(tactic.positions.keys()) - set(ZONE_NAMES)
        raise ValueError(
            f"tactic.positions has wrong zone keys "
            f"(missing={sorted(missing)}, extra={sorted(extra)})"
        )

    coords: list[int] = []
    for shirt in SHIRT_NUMBERS:
        for zone in ZONE_NAMES:
            xy = tactic.positions[zone].get(shirt)
            if xy is None:
                raise ValueError(
                    f"tactic.positions[{zone!r}] missing shirt {shirt}"
                )
            x, y = xy
            if not (0 <= x <= 0xFFFF and 0 <= y <= 0xFFFF):
                raise ValueError(
                    f"coord out of u16 range at zone={zone} shirt={shirt}: ({x}, {y})"
                )
            coords.extend((x, y))

    return struct.pack(f">{len(coords)}H", *coords) + tactic.trailer


def tactic_to_json(tactic: Tactic) -> dict:
    """Convert a :class:`Tactic` to a JSON-safe dict.

    Shirt numbers become string keys (JSON has no int keys); coordinates
    are 2-element lists; the opaque trailer is preserved as a hex string.
    """
    return {
        "zones": {
            zone: {str(shirt): list(xy)
                   for shirt, xy in tactic.positions[zone].items()}
            for zone in ZONE_NAMES
        },
        "trailer_hex": tactic.trailer.hex(),
    }


def tactic_from_json(data: dict) -> Tactic:
    """Inverse of :func:`tactic_to_json`. Validates shape; round-trip safe."""
    zones = data.get("zones")
    if not isinstance(zones, dict):
        raise ValueError("expected 'zones' dict")
    if set(zones.keys()) != set(ZONE_NAMES):
        raise ValueError(f"'zones' keys must be exactly {list(ZONE_NAMES)}")

    positions: dict[str, dict[int, tuple[int, int]]] = {}
    for zone in ZONE_NAMES:
        shirts = zones[zone]
        positions[zone] = {}
        for key, xy in shirts.items():
            shirt = int(key)
            if shirt not in SHIRT_NUMBERS:
                raise ValueError(f"zone {zone!r}: shirt {shirt} not in 2..11")
            if not (isinstance(xy, (list, tuple)) and len(xy) == 2):
                raise ValueError(f"zone {zone!r} shirt {shirt}: expected [x, y]")
            positions[zone][shirt] = (int(xy[0]), int(xy[1]))
        if set(positions[zone].keys()) != set(SHIRT_NUMBERS):
            raise ValueError(f"zone {zone!r} missing shirts")

    trailer_hex = data.get("trailer_hex", "")
    try:
        trailer = bytes.fromhex(trailer_hex) if trailer_hex else b""
    except ValueError as exc:
        raise ValueError(f"invalid trailer_hex: {exc}") from exc

    return Tactic(positions=positions, trailer=trailer)
