"""ADF disk image I/O for Player Manager save disks.

Handles the custom file table format used by Player Manager (not standard
AmigaDOS filesystem). The save disk stores a file table at block 2 with
16-byte entries encoding filename, offset (×32 multiplier), and size.
"""

import os
import shutil
import struct
from dataclasses import dataclass


def ensure_backup(path: str) -> str | None:
    """Copy `path` to `path + '.bak'` if the backup does not already exist.

    Returns the backup path if one was created, None otherwise. Idempotent:
    never overwrites an existing backup, so the first-ever state is preserved.
    """
    if not path or not os.path.isfile(path):
        return None
    bak = path + ".bak"
    if os.path.exists(bak):
        return None
    shutil.copy2(path, bak)
    return bak

ADF_SIZE = 901120  # Standard Amiga DD floppy: 2×80×11×512
BLOCK_SIZE = 512
FILE_TABLE_OFFSET = 2 * BLOCK_SIZE  # Block 2 = 0x400
FILE_TABLE_SIZE = BLOCK_SIZE  # One block for the file table
ENTRY_SIZE = 16
MAX_ENTRIES = FILE_TABLE_SIZE // ENTRY_SIZE  # 32
NAME_FIELD_SIZE = 12
OFFSET_MULTIPLIER = 32
BOOT_MAGIC = b"DOS\x00"
DISK_MARKER = "data.disk"


@dataclass
class FileEntry:
    """A file entry from the save disk's file table."""
    name: str
    raw_offset: int   # 16-bit value from the table
    size: int         # File size in bytes

    @property
    def byte_offset(self) -> int:
        """Actual byte offset within the ADF image."""
        return self.raw_offset * OFFSET_MULTIPLIER


class ADF:
    """Reader/writer for Player Manager save disk ADF images.

    Usage:
        adf = ADF.load("Save1_PM.adf")
        for entry in adf.list_files():
            print(entry.name, entry.size)
        data = adf.read_file("pm1.sav")
        adf.write_file("pm1.sav", modified_data)
        adf.save("Save1_PM.adf")
    """

    def __init__(self, data: bytes):
        if len(data) != ADF_SIZE:
            raise ValueError(f"Invalid ADF size: {len(data)} (expected {ADF_SIZE})")
        if data[:4] != BOOT_MAGIC:
            raise ValueError(f"Invalid ADF magic: {data[:4]!r} (expected {BOOT_MAGIC!r})")
        self._data = bytearray(data)
        self._entries = self._parse_file_table()
        if not any(e.name == DISK_MARKER for e in self._entries):
            raise ValueError("Not a Player Manager save disk (missing data.disk marker)")

    @classmethod
    def load(cls, path: str) -> "ADF":
        """Load an ADF image from a file path."""
        with open(path, "rb") as f:
            return cls(f.read())

    def save(self, path: str) -> None:
        """Write the ADF image to a file path."""
        with open(path, "wb") as f:
            f.write(bytes(self._data))

    def _parse_file_table(self) -> list[FileEntry]:
        """Parse the file table at block 2."""
        entries = []
        ft = self._data[FILE_TABLE_OFFSET:FILE_TABLE_OFFSET + FILE_TABLE_SIZE]
        for i in range(MAX_ENTRIES):
            raw = ft[i * ENTRY_SIZE:(i + 1) * ENTRY_SIZE]
            if raw[0] == 0:
                break
            null_pos = raw.index(0) if 0 in raw[:NAME_FIELD_SIZE] else NAME_FIELD_SIZE
            name = raw[:null_pos].decode("latin-1")
            raw_offset = struct.unpack(">H", raw[12:14])[0]
            size = struct.unpack(">H", raw[14:16])[0]
            entries.append(FileEntry(name=name, raw_offset=raw_offset, size=size))
        return entries

    def list_files(self) -> list[FileEntry]:
        """Return all file entries from the file table."""
        return list(self._entries)

    def find_file(self, name: str) -> FileEntry:
        """Find a file entry by name (case-insensitive)."""
        name_lower = name.lower()
        for entry in self._entries:
            if entry.name.lower() == name_lower:
                return entry
        raise FileNotFoundError(f"File not found in ADF: {name}")

    def read_file(self, name: str) -> bytes:
        """Read file contents by name."""
        entry = self.find_file(name)
        return bytes(self._data[entry.byte_offset:entry.byte_offset + entry.size])

    def read_at(self, offset: int, size: int) -> bytes:
        """Read raw bytes at a given offset in the ADF image."""
        return bytes(self._data[offset:offset + size])

    def write_at(self, offset: int, data: bytes) -> None:
        """Write raw bytes at a given offset in the ADF image."""
        self._data[offset:offset + len(data)] = data

    def list_saves(self) -> list[FileEntry]:
        """Return all save file entries (pm1.sav through pm7.sav)."""
        return [e for e in self._entries if e.name.lower().endswith(".sav")
                and e.name.lower() != "start.dat"]
