"""Runtime registration of bundled TrueType fonts.

tkinter has no built-in TTF loader — it only sees fonts the operating
system already knows about. This module registers bundled fonts with
the OS at process scope so tkinter can pick them up by family name,
without asking the user to install anything.

All operations are best-effort: on any failure the helpers silently do
nothing and callers should fall back to a system monospace font.
"""

from __future__ import annotations

import ctypes
import os
import sys


ASSETS_DIR = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "assets",
)
TOPAZ_TTF = os.path.join(ASSETS_DIR, "Topaz_a1200_v1.0.ttf")

# Family name as reported by the TTF 'name' table.
TOPAZ_FAMILY = "Topaz a600a1200a400"

_registered_paths: set[str] = set()


def register_ttf(path: str) -> bool:
    """Register the TTF at `path` for this process.

    Returns True on success (or if already registered in this process).
    Returns False if the file is missing, the OS call fails, or we're on
    an unsupported platform.
    """
    if path in _registered_paths:
        return True
    if not os.path.isfile(path):
        return False
    try:
        if sys.platform == "darwin":
            ok = _register_macos(path)
        elif sys.platform == "win32":
            ok = _register_windows(path)
        else:
            ok = _register_linux(path)
    except Exception:
        ok = False
    if ok:
        _registered_paths.add(path)
    return ok


def _register_macos(path: str) -> bool:
    ct = ctypes.CDLL(
        "/System/Library/Frameworks/CoreText.framework/CoreText"
    )
    cf = ctypes.CDLL(
        "/System/Library/Frameworks/"
        "CoreFoundation.framework/CoreFoundation"
    )
    cf.CFURLCreateFromFileSystemRepresentation.restype = ctypes.c_void_p
    cf.CFURLCreateFromFileSystemRepresentation.argtypes = [
        ctypes.c_void_p, ctypes.c_char_p, ctypes.c_long, ctypes.c_bool,
    ]
    ct.CTFontManagerRegisterFontsForURL.restype = ctypes.c_bool
    ct.CTFontManagerRegisterFontsForURL.argtypes = [
        ctypes.c_void_p, ctypes.c_uint32, ctypes.c_void_p,
    ]
    encoded = path.encode("utf-8")
    url = cf.CFURLCreateFromFileSystemRepresentation(
        None, encoded, len(encoded), False,
    )
    if not url:
        return False
    # kCTFontManagerScopeProcess = 1 — registration lasts only for this
    # process; nothing is left behind on the user's system.
    return bool(ct.CTFontManagerRegisterFontsForURL(url, 1, None))


def _register_windows(path: str) -> bool:
    FR_PRIVATE = 0x10
    gdi32 = ctypes.windll.gdi32
    gdi32.AddFontResourceExW.argtypes = [
        ctypes.c_wchar_p, ctypes.c_uint32, ctypes.c_void_p,
    ]
    gdi32.AddFontResourceExW.restype = ctypes.c_int
    return gdi32.AddFontResourceExW(path, FR_PRIVATE, None) > 0


def _register_linux(path: str) -> bool:
    # tkinter on Linux uses fontconfig/Xft. There is no in-process
    # equivalent of the macOS/Windows APIs, so we drop the file into the
    # user font directory and refresh the fontconfig cache. This is
    # idempotent and reversible — the user can simply delete the file.
    import shutil
    import subprocess

    target_dir = os.path.expanduser("~/.local/share/fonts")
    try:
        os.makedirs(target_dir, exist_ok=True)
        target = os.path.join(target_dir, os.path.basename(path))
        if not os.path.exists(target):
            shutil.copy2(path, target)
            subprocess.run(
                ["fc-cache", "-f", target_dir],
                check=False,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                timeout=5,
            )
        return True
    except Exception:
        return False


def register_bundled_fonts() -> None:
    """Register every bundled font. Safe to call once at GUI startup."""
    register_ttf(TOPAZ_TTF)


def topaz_available() -> bool:
    """True when the bundled Topaz TTF was registered this process."""
    return TOPAZ_TTF in _registered_paths
