"""Player name generation from RNG seeds and game disk surname table.

The game generates player names procedurally:
  - Surname: derived from the RNG seed via a hash algorithm, index into
    the surname table embedded in the DEFAJAM-packed '2507' executable
  - Initials: 1–3 chars chosen from character-set tables based on the seed

The hash algorithm was reverse-engineered from the Windows PMSaveDiskTool
PE32 binary (function at file offset 0x50F0–0x5384). The surname table is
extracted by decompressing the Italian game disk's '2507' executable with
the DEFAJAM decompressor.

Usage:
    gd = GameDisk.load("PlayerManagerITA.adf")
    print(gd.player_full_name(rng_seed))   # e.g. "A. Baresi"
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
    """Read a named file from an AmigaDOS OFS disk image."""
    BLOCK = 512
    root = adf_data[880 * BLOCK:(880 + 1) * BLOCK]

    def read_header(blk):
        b = adf_data[blk * BLOCK:(blk + 1) * BLOCK]
        btype    = struct.unpack_from('>I', b, 0)[0]
        sec_type = struct.unpack_from('>i', b, 508)[0]
        nl = b[432]
        name  = b[433:433+nl].decode('latin-1', errors='replace')
        fsize = struct.unpack_from('>I', b, 324)[0]
        chain = struct.unpack_from('>I', b, 316)[0]
        first = struct.unpack_from('>I', b, 16)[0]
        return btype, sec_type, name, fsize, chain, first

    for i in range(72):
        blk = struct.unpack_from('>I', root, 24 + i * 4)[0]
        while blk:
            btype, sec_type, name, fsize, chain, first = read_header(blk)
            if btype == 2 and sec_type == -3 and name == filename:
                result = bytearray()
                db = first
                while db and len(result) < fsize:
                    block = adf_data[db * BLOCK:(db + 1) * BLOCK]
                    ds  = struct.unpack_from('>I', block, 12)[0]
                    nxt = struct.unpack_from('>I', block, 16)[0]
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


# ── GameDisk ─────────────────────────────────────────────────────────────────

class GameDisk:
    """Loads a Player Manager game ADF and provides player name generation.

    Usage:
        gd = GameDisk.load("PlayerManagerITA.adf")
        print(gd.player_full_name(rng_seed))   # "A. Baresi"
        print(gd.surname_count)                 # 245
    """

    # Surname table location in the decompressed game image
    _NAME_START = 0x15B02
    _NAME_END   = 0x162E6

    def __init__(self, surnames: list[str]):
        self.surnames = surnames

    @classmethod
    def load(cls, path: str) -> "GameDisk":
        """Load and decompress the game ADF, extracting the surname table."""
        with open(path, "rb") as f:
            adf_data = f.read()
        return cls.from_bytes(adf_data)

    @classmethod
    def from_bytes(cls, adf_data: bytes) -> "GameDisk":
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

        return cls(surnames)

    @property
    def surname_count(self) -> int:
        return len(self.surnames)

    def player_full_name(self, rng_seed: int) -> str:
        """Return 'I. Surname' name for a given RNG seed."""
        return _name_from_seed(rng_seed, self.surnames)

    def player_surname(self, rng_seed: int) -> str:
        """Return just the surname for a given RNG seed."""
        return _name_from_seed(rng_seed, self.surnames).split(" ", 1)[-1]
