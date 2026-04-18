"""Palette, fonts, and ttk.Style setup for the Player Manager GUI.

Extracted from ``pm_gui.py`` so the standalone Toplevel windows (Career
Tracker, Byte Workbench, Line-up Coach, Compare Players) can share theme
state without pulling the whole main window along.

``PAL`` is a mutable dict — ``main()`` calls :func:`set_theme` once
before any widget is built, and widget creation reads ``PAL["bg"]`` etc.
at that point. Existing widgets don't repaint when the dict later
mutates, which is why the Preferences dialog tells users the theme takes
effect on next launch.
"""

import tkinter as tk
from tkinter import ttk

from pm_core import fonts

# Dense data views (player list, entry fields, tiny labels) always use
# Courier New — pixel fonts become hard to read at small sizes and
# inside tight tables. Retro header/label helpers below prefer Topaz
# when it's bundled, falling back to Courier New transparently.
FONT_DATA = "Courier New"

# Read from preferences once at startup via :func:`set_use_system_font`.
# Toggling this flag mid-session would not repaint existing widgets
# because tk widgets fetch their font at creation time.
_USE_SYSTEM_FONT = False


def set_use_system_font(value: bool) -> None:
    """Switch the retro helper to Courier New only, before widgets exist."""
    global _USE_SYSTEM_FONT
    _USE_SYSTEM_FONT = bool(value)


def _retro(size: int, weight: str = "normal") -> tuple[str, int, str]:
    """Retro header/label font with automatic fallback to Courier New."""
    if _USE_SYSTEM_FONT:
        return (FONT_DATA, size, weight)
    family = fonts.TOPAZ_FAMILY if fonts.topaz_available() else FONT_DATA
    return (family, size, weight)


PAL_RETRO = {
    "bg":         "#000066",
    "bg_mid":     "#111188",
    "bg_header":  "#3355aa",
    "fg_title":   "#00ddff",
    "fg_data":    "#ffcc00",
    "fg_label":   "#7799cc",
    "fg_dim":     "#445588",
    "player_a":   "#44ccff",
    "player_b":   "#ff6666",
    "free_agent": "#44cc44",
    "btn_go":     "#006600",
    "btn_go_fg":  "#ffffff",
    "selected":   "#3344aa",
    "border":     "#2244aa",
    "field":      "#000044",   # entry/combobox field background
    "fg_white":   "#ffffff",   # selected/active foreground
    "radar_bg":   "#000055",   # radar canvas background (intentionally lighter than bg)
    "bar_trough": "#111144",   # skill bar trough fill
    "status_bar": "#000033",   # status bar frame background
    "warn_fg":    "#ff9944",   # ⚠ warning accent (skill-threshold flags)
}

# Accessible light theme. High-contrast (WCAG AA on all foregrounds),
# neutral greys for chrome, and muted blue/red/green accents for the
# player_a / player_b / free_agent markers so they stay
# distinguishable without the retro palette's saturation.
PAL_LIGHT = {
    "bg":         "#f5f5f5",
    "bg_mid":     "#e8e8e8",
    "bg_header":  "#4a6fa5",
    "fg_title":   "#1e3d6f",
    "fg_data":    "#1a1a1a",
    "fg_label":   "#555555",
    "fg_dim":     "#888888",
    "player_a":   "#0b61a4",
    "player_b":   "#a93226",
    "free_agent": "#1e7e34",
    "btn_go":     "#1e7e34",
    "btn_go_fg":  "#ffffff",
    "selected":   "#cce4f7",
    "border":     "#bdbdbd",
    "field":      "#ffffff",
    "fg_white":   "#1a1a1a",   # "active/selected foreground" — dark on pale selected bg
    "radar_bg":   "#ffffff",
    "bar_trough": "#dcdcdc",
    "status_bar": "#d6d6d6",
    "warn_fg":    "#a93226",
}

# Active palette. ``set_theme`` swaps its contents to ``PAL_LIGHT`` when
# the user has picked the light theme, before any widget is built —
# existing references like ``PAL["bg"]`` then resolve to the new values
# throughout the module.
PAL = dict(PAL_RETRO)


def set_theme(name: str) -> None:
    """Replace ``PAL`` contents in-place. Call before building any widget."""
    PAL.clear()
    PAL.update(PAL_LIGHT if name == "light" else PAL_RETRO)


def apply_theme(root: tk.Tk) -> None:
    """Configure ttk.Style globally with the active Player Manager palette."""
    style = ttk.Style(root)
    try:
        style.theme_use("clam")
    except tk.TclError:
        pass

    bg      = PAL["bg"]
    bg_mid  = PAL["bg_mid"]
    bg_hdr  = PAL["bg_header"]
    fg_data = PAL["fg_data"]
    fg_lbl  = PAL["fg_label"]
    fg_dim  = PAL["fg_dim"]
    sel     = PAL["selected"]
    border  = PAL["border"]

    style.configure("TFrame",        background=bg)
    style.configure("TLabel",        background=bg,     foreground=fg_data)
    style.configure("TButton",       background=bg_mid, foreground=fg_data,
                    relief="flat",   borderwidth=1)
    style.map("TButton",
              background=[("active", sel)],
              foreground=[("active", PAL["fg_white"])])
    style.configure("TEntry",        fieldbackground=PAL["field"], foreground=fg_data,
                    insertcolor=fg_data, bordercolor=border, selectbackground=sel)
    style.configure("TCombobox",     fieldbackground=PAL["field"], foreground=fg_data,
                    selectbackground=sel, arrowcolor=fg_lbl)
    style.map("TCombobox",
              fieldbackground=[("readonly", PAL["field"])],
              foreground=[("readonly", fg_data)])
    style.configure("Treeview",      background=bg,  foreground=fg_data,
                    fieldbackground=bg, rowheight=20)
    style.map("Treeview",
              background=[("selected", sel)],
              foreground=[("selected", PAL["fg_white"])])
    style.configure("Treeview.Heading", background=bg_hdr, foreground=PAL["fg_title"],
                    relief="flat", font=_retro(11, "bold"))
    style.map("Treeview.Heading",
              background=[("active", sel)])
    style.configure("TNotebook",     background=bg, borderwidth=0)
    style.configure("TNotebook.Tab", background=bg_mid, foreground=fg_lbl,
                    padding=(10, 4), font=_retro(11, "bold"))
    style.map("TNotebook.Tab",
              background=[("selected", bg)],
              foreground=[("selected", PAL["fg_data"])])
    style.configure("TSeparator",    background=border)
    style.configure("TScrollbar",    background=bg_mid, troughcolor=bg,
                    arrowcolor=fg_lbl, borderwidth=0)

    root.configure(bg=bg)
