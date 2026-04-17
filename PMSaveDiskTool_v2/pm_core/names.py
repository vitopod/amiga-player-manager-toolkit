"""Player name generation from RNG seeds and game disk surname table.

The game generates player names procedurally:
  - Surname: derived from the RNG seed via a hash algorithm, index into
    the surname table embedded in the game disk
  - Initials: 1–3 chars chosen from character-set tables based on the seed

The hash algorithm was reverse-engineered from the Windows PMSaveDiskTool
PE32 binary (function at file offset 0x50F0–0x5384).

Two build layouts are supported:

  * Italian (stable): surname table embedded in the DEFAJAM-packed '2507'
    executable on an AmigaDOS OFS disk. 245 surnames. Initials charsets
    reverse-engineered.

  * English (BETA): surname table stored as plaintext NUL-separated ASCII
    on a PM-custom-file-table disk (no AmigaDOS filesystem). 183 surnames.
    Located by anchor-scan on known leading surnames. Surnames and the
    reused Italian initials charsets were cross-checked against an in-game
    roster screen (2026-04-17) and every observed surname and initial
    letter was consistent. What's still BETA is the exact seed→name
    mapping: individual players could in principle resolve to slightly
    different names than the live game displays.

Usage:
    gd = GameDisk.load("PlayerManagerITA.adf")
    print(gd.player_full_name(rng_seed))   # e.g. "A. Baresi"
    print(gd.build)                         # 'italian' or 'english'
    print(gd.is_beta)                       # True for non-Italian builds
"""

import struct


# ── DEFAJAM decompressor ─────────────────────────────────────────────────────

class _DEFAJAMDecompressor:
    """Two-phase decompressor for DEFAJAM-packed Amiga executables.

    Phase 1: backward LZ77 with Huffman-coded literals through a 256-byte LUT.
    Phase 2: RLE expansion using 0x9B as the marker byte.
    """

    def __init__(self, hunk_code: bytes):
        self._lut = hunk_code[0x0190:0x0190 + 256]
        packed_full = hunk_code[0x0290:]
        self._packed = packed_full[:-8]
        self._write_offset = struct.unpack_from('>I', packed_full, len(packed_full) - 4)[0]
        self._d0_init      = struct.unpack_from('>I', packed_full, len(packed_full) - 8)[0]

    def decompress(self) -> bytes:
        return self._phase2_rle(self._phase1_lz())

    def _phase1_lz(self) -> bytes:
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
            return refill() if d0 == 0 else carry

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
                        v2 = read_bits(12)
                        lc = (v2 + 265) if v2 else (read_bits(15) + 4363)
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

    @staticmethod
    def _phase2_rle(data: bytes) -> bytes:
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


# ── OFS filesystem reader ────────────────────────────────────────────────────

def _ofs_read_file(adf_data: bytes, filename: str) -> bytes | None:
    """Read a named file from an AmigaDOS OFS disk image.

    Returns None if the disk isn't OFS, the file doesn't exist, or any
    on-disk pointer points outside the image. Non-OFS disks (e.g. PM's
    custom-file-table game/save disks) are silently ignored here — callers
    fall back to PM-specific detection.
    """
    BLOCK = 512
    total_blocks = len(adf_data) // BLOCK
    if total_blocks <= 880:
        return None
    root = adf_data[880 * BLOCK:(880 + 1) * BLOCK]

    def _block(blk):
        if blk <= 0 or blk >= total_blocks:
            return None
        return adf_data[blk * BLOCK:(blk + 1) * BLOCK]

    def read_header(blk):
        b = _block(blk)
        if b is None:
            return None
        btype    = struct.unpack_from('>I', b, 0)[0]
        sec_type = struct.unpack_from('>i', b, 508)[0]
        nl = b[432]
        if nl > 30:
            return None
        name  = b[433:433+nl].decode('latin-1', errors='replace')
        fsize = struct.unpack_from('>I', b, 324)[0]
        chain = struct.unpack_from('>I', b, 316)[0]
        first = struct.unpack_from('>I', b, 16)[0]
        return btype, sec_type, name, fsize, chain, first

    for i in range(72):
        blk = struct.unpack_from('>I', root, 24 + i * 4)[0]
        seen = set()
        while blk and blk not in seen:
            seen.add(blk)
            hdr = read_header(blk)
            if hdr is None:
                break
            btype, sec_type, name, fsize, chain, first = hdr
            if btype == 2 and sec_type == -3 and name == filename:
                result = bytearray()
                db = first
                data_seen = set()
                while db and db not in data_seen and len(result) < fsize:
                    data_seen.add(db)
                    block = _block(db)
                    if block is None:
                        return None
                    ds  = struct.unpack_from('>I', block, 12)[0]
                    nxt = struct.unpack_from('>I', block, 16)[0]
                    if ds > BLOCK - 24:
                        return None
                    result.extend(block[24:24 + ds])
                    db = nxt
                return bytes(result[:fsize])
            blk = chain
    return None


# ── Name hash algorithm (from Windows PMSaveDiskTool PE32 at 0x50F0–0x5384) ─

# Initial character tables (from Windows exe VA 0x41FA64 area)
_INITIALS_A = "ADJR"
_INITIALS_B = "CEGMS"
_INITIALS_C = "BFHILNTW"
_INITIALS_D = "O"


def _hash_round(buf: bytearray) -> None:
    """One iteration of the name hash function.

    Reverse-engineered from x86 code at file offset 0x5300 in the
    Windows PMSaveDiskTool PE32 binary.
    buf is a 6-byte working buffer (indices 0–5).
    """
    ah = (buf[3] >> 3) & 0xFF
    al = buf[5]
    ah ^= al
    # RCR AH, 1 (CF=0 because XOR clears CF)
    carry = ah & 1
    ah = ah >> 1  # CF=0, so no bit inserted at top
    # Now chain RCL through buf[1], buf[0], buf[3], buf[2], buf[5], buf[4]
    order = [1, 0, 3, 2, 5, 4]
    for idx in order:
        new_carry = (buf[idx] >> 7) & 1
        buf[idx] = ((buf[idx] << 1) | carry) & 0xFF
        carry = new_carry


def _name_from_seed(rng_seed: int, surnames: list[str]) -> str:
    """Derive a player name from a 4-byte RNG seed.

    Returns "I. Surname" format (1–3 initials + dot + space + surname).
    """
    buf = bytearray(6)
    buf[0] = (rng_seed >> 24) & 0xFF
    buf[1] = (rng_seed >> 16) & 0xFF
    buf[2] = (rng_seed >>  8) & 0xFF
    buf[3] =  rng_seed        & 0xFF
    buf[4] = 0
    buf[5] = 0

    # 20 warm-up rounds
    for _ in range(20):
        _hash_round(buf)

    # Determine number of initials
    _hash_round(buf)
    val = buf[0] * 256 + buf[1]
    v100 = val % 100
    if v100 < 75:
        n_parts = 1
    elif v100 < 98:
        n_parts = 2
    else:
        n_parts = 3

    # Choose each initial
    initials = []
    for _ in range(n_parts):
        _hash_round(buf)
        val = buf[0] * 256 + buf[1]
        v100 = val % 100
        if v100 < 44:
            charset = _INITIALS_A
        elif v100 < 76:
            charset = _INITIALS_B
        elif v100 < 99:
            charset = _INITIALS_C
        else:
            charset = _INITIALS_D
        _hash_round(buf)
        val = buf[0] * 256 + buf[1]
        initials.append(charset[val % len(charset)])

    # Surname
    _hash_round(buf)
    val = buf[0] * 256 + buf[1]
    surname = surnames[val % len(surnames)]

    return "".join(f"{c}." for c in initials) + " " + surname


# ── PM custom file table reader (same format as save disks) ─────────────────

def _pm_custom_file_table_entries(adf_data: bytes) -> list[tuple[str, int, int]]:
    """Read (name, byte_offset, size) entries from PM's custom 16-byte file
    table at block 2 (0x400). Each entry is 12 bytes name + 2 bytes offset
    (×32 multiplier) + 2 bytes size.

    Returns [] if the layout doesn't look like a PM custom file table.
    """
    BLOCK = 512
    ENTRY = 16
    FT_OFFSET = 2 * BLOCK
    if len(adf_data) < FT_OFFSET + BLOCK:
        return []
    entries = []
    for i in range(BLOCK // ENTRY):
        raw = adf_data[FT_OFFSET + i * ENTRY : FT_OFFSET + (i + 1) * ENTRY]
        if raw[0] == 0:
            break
        null_pos = raw.index(0) if 0 in raw[:12] else 12
        try:
            name = raw[:null_pos].decode('ascii')
        except UnicodeDecodeError:
            return []
        if not all(0x20 <= b < 0x7f for b in raw[:null_pos]):
            return []
        byte_off = struct.unpack_from('>H', raw, 12)[0] * 32
        size     = struct.unpack_from('>H', raw, 14)[0]
        entries.append((name, byte_off, size))
    return entries


def _pm_custom_file_table_names(adf_data: bytes) -> list[str]:
    return [name for name, _, _ in _pm_custom_file_table_entries(adf_data)]


def _pm_read_file(adf_data: bytes, filename: str) -> bytes | None:
    """Read a named file from a PM custom-file-table disk. Returns None if
    not found or the referenced region is out of bounds."""
    for name, off, sz in _pm_custom_file_table_entries(adf_data):
        if name == filename:
            if off < 0 or off + sz > len(adf_data):
                return None
            return adf_data[off:off + sz]
    return None


# Known PM game-disk executable names, per build.
_PM_GAME_EXECUTABLES = {"2507", "manager.prg"}


def _detect_game_disk_build(adf_data: bytes) -> str | None:
    """Return a short build hint (e.g. 'italian', 'english', 'unknown-pm')
    if adf_data looks like *some* Player Manager game disk, else None.

    Detection is intentionally loose: we want to accept any disk whose layout
    is clearly PM's, even if we can't extract names from it.
    """
    # Italian build: AmigaDOS OFS with file '2507'
    if _ofs_read_file(adf_data, "2507") is not None:
        return "italian"

    # English / cracked builds: PM's custom file table at 0x400
    names = _pm_custom_file_table_names(adf_data)
    if not names:
        return None
    name_set = set(names)
    if "2507" in name_set:
        return "italian-custom"
    if "manager.prg" in name_set:
        return "english"
    # Heuristic: multiple PM-style files (tactics, etc.) are a strong signal
    tac_count = sum(1 for n in names if n.endswith(".tac"))
    if tac_count >= 2 and any(n.endswith(".prg") for n in names):
        return "unknown-pm"
    return None


# ── GameDisk ─────────────────────────────────────────────────────────────────

class GameDisk:
    """Loads a Player Manager game ADF and provides player name generation.

    Only the Italian build ('2507' executable) has a known surname-table
    layout. Other PM builds load successfully but with `surnames=[]` and
    `names_available=False` — save editing still works; player names stay
    blank as if no game disk were loaded.

    Usage:
        gd = GameDisk.load("PlayerManagerITA.adf")
        print(gd.player_full_name(rng_seed))   # "A. Baresi"
        print(gd.surname_count)                 # 245
        print(gd.build)                         # "italian"
    """

    # Surname table location in the decompressed Italian game image
    _NAME_START = 0x15B02
    _NAME_END   = 0x162E6

    def __init__(self, surnames: list[str], build: str = "italian",
                 team_names: list[str] | None = None):
        self.surnames = surnames
        self.build = build
        self.team_names = team_names or []

    @classmethod
    def load(cls, path: str) -> "GameDisk":
        """Load a game ADF. Accepts any recognizable PM build; names are
        only populated for the Italian build."""
        with open(path, "rb") as f:
            adf_data = f.read()
        return cls.from_bytes(adf_data)

    @classmethod
    def from_bytes(cls, adf_data: bytes) -> "GameDisk":
        build = _detect_game_disk_build(adf_data)
        if build is None:
            raise ValueError(
                "Not a recognizable Player Manager game disk "
                "(no '2507' via OFS and no PM custom file table found)"
            )

        if build == "italian":
            # Italian save disks carry team names in PM1.nam; nothing to
            # extract from the game disk.
            return cls(cls._extract_italian_surnames(adf_data), build="italian")
        if build == "english":
            surnames = cls._extract_english_surnames(adf_data)
            team_names = cls._extract_start_dat_team_names(adf_data)
            # If the anchor scan misses (non-standard crack), downgrade to
            # "loaded but no names" rather than hard-failing.
            return cls(surnames, build="english", team_names=team_names)
        # Recognised as PM-ish but no known surname layout. Team names may
        # still be present in start.dat, so try anyway.
        return cls(surnames=[], build=build,
                   team_names=cls._extract_start_dat_team_names(adf_data))

    @classmethod
    def _extract_italian_surnames(cls, adf_data: bytes) -> list[str]:
        raw = _ofs_read_file(adf_data, "2507")
        if raw is None:
            raise ValueError("File '2507' not found — is this a Player Manager game disk?")

        # Parse AmigaDOS hunk format
        pos = 0
        hunk_code = None
        while pos + 4 <= len(raw):
            marker = struct.unpack_from('>I', raw, pos)[0]; pos += 4
            if marker == 0x3F3:   # HUNK_HEADER
                pos += 4          # resident lib count (0)
                table_size = struct.unpack_from('>I', raw, pos)[0]; pos += 4
                pos += 4 + 4 + table_size * 4
            elif marker == 0x3E9: # HUNK_CODE
                size_longs = struct.unpack_from('>I', raw, pos)[0]; pos += 4
                hunk_code = raw[pos:pos + size_longs * 4]
                break
            else:
                break

        if hunk_code is None:
            raise ValueError("HUNK_CODE not found in '2507'")

        game_image = _DEFAJAMDecompressor(hunk_code).decompress()

        if len(game_image) < cls._NAME_END:
            raise ValueError(f"Decompressed image too short ({len(game_image)} < {cls._NAME_END})")

        surnames = []
        pos = cls._NAME_START
        while pos < cls._NAME_END:
            if game_image[pos] == 0:
                pos += 1; continue
            end = pos
            while end < cls._NAME_END and game_image[end] != 0:
                end += 1
            try:
                text = game_image[pos:end].decode('ascii')
                if len(text) >= 2 and text[0].isupper():
                    surnames.append(text)
            except UnicodeDecodeError:
                pass
            pos = end + 1

        if not surnames:
            raise ValueError("No surnames found in decompressed game image")

        return surnames

    # Anchor: the first five surnames in the English surname table, in order.
    # They appear as one contiguous NUL-separated block and are unlikely to
    # occur elsewhere in the 900KB image, which makes this a robust locator
    # regardless of how the game disk was cracked/reassembled.
    _ENGLISH_ANCHOR = b"Adams\x00Adcock\x00Addison\x00Aldridge\x00Alexander\x00"
    # Boundary marker immediately following the table in known dumps.
    _ENGLISH_TERMINATOR = b"JOYSTICK"

    @classmethod
    def _extract_english_surnames(cls, adf_data: bytes) -> list[str]:
        """Extract the English surname table by anchor-scan.

        Returns [] if the anchor isn't found — the disk is accepted as PM
        but names stay blank (handled by the caller).
        """
        start = adf_data.find(cls._ENGLISH_ANCHOR)
        if start < 0:
            return []
        # Find the end: nearest known non-surname UI string after the anchor.
        term = adf_data.find(cls._ENGLISH_TERMINATOR, start)
        if term < 0:
            return []
        # Strip trailing NULs before the terminator.
        end = term
        while end > start and adf_data[end - 1] == 0:
            end -= 1
        surnames = []
        for chunk in adf_data[start:end].split(b"\x00"):
            if not chunk:
                continue
            try:
                text = chunk.decode("ascii")
            except UnicodeDecodeError:
                continue
            # Surnames only: capitalised, alphabetic, 2–20 chars.
            if 2 <= len(text) <= 20 and text[0].isupper() and text.isalpha():
                surnames.append(text)
        return surnames

    # start.dat on PM custom-file-table game disks: 8-byte header + 44
    # team records × 100 bytes. Team name is NUL-terminated ASCII at
    # offset 0x3C within each record. Slot 43 is unused template garbage
    # on the English disk; filtered by the isalpha check below.
    _START_DAT_SIZE = 4408
    _START_DAT_HEADER = 8
    _START_DAT_SLOT = 100
    _START_DAT_NAME_OFFSET = 0x3C
    _START_DAT_TEAM_COUNT = 44

    @classmethod
    def _extract_start_dat_team_names(cls, adf_data: bytes) -> list[str]:
        """Pull team names out of start.dat on a PM custom-file-table game disk.

        Returns [] if start.dat is missing, the wrong size, or the slot at
        offset 0x3C doesn't look like printable ASCII. Filters out template
        garbage (unused slot 43 on the English disk) by requiring each
        name to be alphabetic/space-only and at least 2 chars.
        """
        data = _pm_read_file(adf_data, "start.dat")
        if data is None or len(data) != cls._START_DAT_SIZE:
            return []
        names = []
        for i in range(cls._START_DAT_TEAM_COUNT):
            slot_start = cls._START_DAT_HEADER + i * cls._START_DAT_SLOT
            raw = data[slot_start + cls._START_DAT_NAME_OFFSET
                       : slot_start + cls._START_DAT_SLOT]
            end = raw.index(0) if 0 in raw else len(raw)
            try:
                text = raw[:end].decode("ascii")
            except UnicodeDecodeError:
                names.append("")
                continue
            # Accept A–Z plus space; drop anything else as unused/garbage.
            if (len(text) >= 2
                    and all(c.isalpha() or c == " " for c in text)
                    and text[0].isalpha()):
                names.append(text)
            else:
                names.append("")
        return names

    @property
    def surname_count(self) -> int:
        return len(self.surnames)

    @property
    def team_names_available(self) -> bool:
        return any(self.team_names)

    @property
    def names_available(self) -> bool:
        return bool(self.surnames)

    @property
    def is_beta(self) -> bool:
        """True for builds whose name generation is unverified against the
        live game (anything non-Italian)."""
        return self.build != "italian"

    def player_full_name(self, rng_seed: int) -> str:
        """Return 'I. Surname' name for a given RNG seed, or '' if this
        build has no known surname table."""
        if not self.surnames:
            return ""
        return _name_from_seed(rng_seed, self.surnames)

    def player_surname(self, rng_seed: int) -> str:
        """Return just the surname for a given RNG seed, or '' if unavailable."""
        if not self.surnames:
            return ""
        return _name_from_seed(rng_seed, self.surnames).split(" ", 1)[-1]
