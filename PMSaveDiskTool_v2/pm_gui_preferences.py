"""Preferences dialog (Help → Preferences…).

Collects launch behaviour (splash, welcome, auto-open), defaults (view,
formation, theme, font), and update-check opt-in. Writes through
:mod:`pm_core.preferences` and :mod:`pm_core.updates`.

``xi_entries`` is passed in so the "Default view" list can include the
formation-specific XI entries without having to import from
``pm_gui`` (which would create a cycle).
"""

import os
import tkinter as tk
from tkinter import ttk

from pm_core import preferences, updates


def open_preferences(parent: tk.Tk | tk.Toplevel, xi_entries: dict) -> None:
    """Build and display the modal preferences dialog."""
    top = tk.Toplevel(parent)
    top.title("Preferences")
    top.resizable(False, False)
    top.transient(parent)

    body = ttk.Frame(top, padding=(18, 16, 18, 12))
    body.pack()

    prefs = preferences.load()
    update_state = updates.load_state()

    # ── On launch ──────────────────────────────────────────
    ttk.Label(body, text="On launch",
              font=("TkDefaultFont", 10, "bold")).pack(anchor="w")

    splash_var = tk.BooleanVar(value=bool(prefs["show_splash"]))
    ttk.Checkbutton(body, text="Show splash screen",
                    variable=splash_var).pack(anchor="w", pady=(4, 0))

    welcome_var = tk.BooleanVar(value=bool(prefs["show_welcome"]))
    ttk.Checkbutton(body, text="Show welcome screen",
                    variable=welcome_var).pack(anchor="w", pady=(6, 0))

    auto_save_var = tk.BooleanVar(value=bool(prefs["auto_open_last_save"]))
    ttk.Checkbutton(body, text="Auto-open last save disk",
                    variable=auto_save_var).pack(anchor="w", pady=(6, 0))
    ttk.Label(body,
              text=_pref_path_label(prefs["last_save_adf"]),
              foreground="#888", justify=tk.LEFT, wraplength=360).pack(
        anchor="w", padx=(22, 0))

    auto_game_var = tk.BooleanVar(value=bool(prefs["auto_open_last_game"]))
    ttk.Checkbutton(body, text="Auto-open last game disk",
                    variable=auto_game_var).pack(anchor="w", pady=(6, 0))
    ttk.Label(body,
              text=_pref_path_label(prefs["last_game_adf"]),
              foreground="#888", justify=tk.LEFT, wraplength=360).pack(
        anchor="w", padx=(22, 0))

    ttk.Separator(body, orient=tk.HORIZONTAL).pack(
        fill=tk.X, pady=(12, 10))

    # ── Defaults ───────────────────────────────────────────
    ttk.Label(body, text="Defaults",
              font=("TkDefaultFont", 10, "bold")).pack(anchor="w")

    view_choices = [
        "(first team in save)",
        "All Players",
        "Free Agents",
        "— Young Talents (≤21)",
        "— Top Scorers",
        "— Squad Analyst (all teams)",
    ] + list(xi_entries.keys())
    current_view = prefs["default_view"] or "(first team in save)"
    if current_view not in view_choices:
        current_view = "(first team in save)"
    view_var = tk.StringVar(value=current_view)
    ttk.Label(body, text="Default view when opening a save disk:").pack(
        anchor="w", pady=(4, 2))
    ttk.Combobox(body, textvariable=view_var,
                 values=view_choices, state="readonly", width=34).pack(
        anchor="w", padx=(22, 0))

    fmt_choices = ["4-4-2", "4-3-3", "3-5-2"]
    current_fmt = prefs["default_formation"] if prefs["default_formation"] in fmt_choices else "4-4-2"
    fmt_var = tk.StringVar(value=current_fmt)
    ttk.Label(body, text="Default formation (Line-up Coach):").pack(
        anchor="w", pady=(8, 2))
    ttk.Combobox(body, textvariable=fmt_var,
                 values=fmt_choices, state="readonly", width=10).pack(
        anchor="w", padx=(22, 0))

    theme_choices = [
        ("retro", "Retro (Amiga navy / amber / cyan)"),
        ("light", "Light (accessible high-contrast)"),
    ]
    theme_labels = [label for _, label in theme_choices]
    theme_lookup = dict(theme_choices)
    reverse_theme_lookup = {label: key for key, label in theme_choices}
    current_theme_key = prefs["theme"] if prefs["theme"] in theme_lookup else "retro"
    theme_var = tk.StringVar(value=theme_lookup[current_theme_key])
    ttk.Label(body, text="Colour theme:").pack(anchor="w", pady=(8, 2))
    ttk.Combobox(body, textvariable=theme_var,
                 values=theme_labels, state="readonly", width=34).pack(
        anchor="w", padx=(22, 0))

    font_var = tk.BooleanVar(value=bool(prefs["use_system_font"]))
    ttk.Checkbutton(body,
                    text="Use system font instead of retro Topaz",
                    variable=font_var).pack(anchor="w", pady=(10, 0))
    ttk.Label(body,
              text="Font and theme changes take effect on next launch.",
              foreground="#888").pack(anchor="w", padx=(22, 0))

    ttk.Separator(body, orient=tk.HORIZONTAL).pack(
        fill=tk.X, pady=(12, 10))

    # ── Updates ────────────────────────────────────────────
    ttk.Label(body, text="Updates",
              font=("TkDefaultFont", 10, "bold")).pack(anchor="w")

    update_var = tk.BooleanVar(value=bool(update_state.get("opted_in")))
    ttk.Checkbutton(
        body,
        text="Check GitHub for updates once a day",
        variable=update_var,
    ).pack(anchor="w", pady=(4, 0))
    ttk.Label(
        body,
        text="When enabled, a small “Update available” banner appears "
             "next to\nthe title whenever a newer release is published.",
        foreground="#888",
        justify=tk.LEFT,
    ).pack(anchor="w", pady=(4, 0))

    btns = ttk.Frame(body)
    btns.pack(fill=tk.X, pady=(14, 0))

    def _save_and_close():
        prefs["show_splash"] = bool(splash_var.get())
        prefs["show_welcome"] = bool(welcome_var.get())
        prefs["auto_open_last_save"] = bool(auto_save_var.get())
        prefs["auto_open_last_game"] = bool(auto_game_var.get())
        picked_view = view_var.get()
        prefs["default_view"] = (
            "" if picked_view == "(first team in save)" else picked_view
        )
        prefs["default_formation"] = fmt_var.get()
        prefs["use_system_font"] = bool(font_var.get())
        prefs["theme"] = reverse_theme_lookup.get(theme_var.get(), "retro")
        preferences.save(prefs)
        update_state["opted_in"] = bool(update_var.get())
        updates.save_state(update_state)
        top.destroy()

    ttk.Button(btns, text="Cancel",
               command=top.destroy).pack(side=tk.RIGHT)
    ttk.Button(btns, text="Save",
               command=_save_and_close).pack(side=tk.RIGHT, padx=(0, 8))

    top.grab_set()


def _pref_path_label(path: str) -> str:
    """Format a remembered path for display under its checkbox."""
    if not path:
        return "(none recorded yet)"
    if not os.path.isfile(path):
        return f"⚠ missing: {path}"
    return path
