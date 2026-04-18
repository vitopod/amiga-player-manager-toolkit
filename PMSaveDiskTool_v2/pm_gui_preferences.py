"""Preferences dialog (Help -> Preferences...).

Collects launch behaviour (splash, welcome, auto-open), defaults (view,
formation, theme, font, language), and update-check opt-in. Writes through
:mod:`pm_core.preferences` and :mod:`pm_core.updates`.

``xi_entries`` is passed in so the "Default view" list can include the
formation-specific XI entries without having to import from
``pm_gui`` (which would create a cycle).
"""

import os
import tkinter as tk
from collections.abc import Callable
from tkinter import ttk

from pm_core import preferences, updates
from pm_core.strings import t


def open_preferences(
    parent: tk.Tk | tk.Toplevel,
    xi_entries: dict,
    on_saved: Callable[[], None] | None = None,
) -> None:
    """Build and display the modal preferences dialog.

    ``on_saved`` fires after preferences are persisted and the dialog
    closes -- used by the main window to refresh state that applies
    live (e.g. the skill-threshold warning toggle).
    """
    top = tk.Toplevel(parent)
    top.title(t("pref.title"))
    top.resizable(False, False)
    top.transient(parent)

    body = ttk.Frame(top, padding=(18, 16, 18, 12))
    body.pack()

    prefs = preferences.load()
    update_state = updates.load_state()

    # -- On launch --------------------------------------------------
    ttk.Label(body, text=t("pref.on_launch"),
              font=("TkDefaultFont", 10, "bold")).pack(anchor="w")

    splash_var = tk.BooleanVar(value=bool(prefs["show_splash"]))
    ttk.Checkbutton(body, text=t("pref.splash"),
                    variable=splash_var).pack(anchor="w", pady=(4, 0))

    welcome_var = tk.BooleanVar(value=bool(prefs["show_welcome"]))
    ttk.Checkbutton(body, text=t("pref.welcome"),
                    variable=welcome_var).pack(anchor="w", pady=(6, 0))

    auto_save_var = tk.BooleanVar(value=bool(prefs["auto_open_last_save"]))
    ttk.Checkbutton(body, text=t("pref.auto_save"),
                    variable=auto_save_var).pack(anchor="w", pady=(6, 0))
    ttk.Label(body,
              text=_pref_path_label(prefs["last_save_adf"]),
              foreground="#888", justify=tk.LEFT, wraplength=360).pack(
        anchor="w", padx=(22, 0))

    auto_game_var = tk.BooleanVar(value=bool(prefs["auto_open_last_game"]))
    ttk.Checkbutton(body, text=t("pref.auto_game"),
                    variable=auto_game_var).pack(anchor="w", pady=(6, 0))
    ttk.Label(body,
              text=_pref_path_label(prefs["last_game_adf"]),
              foreground="#888", justify=tk.LEFT, wraplength=360).pack(
        anchor="w", padx=(22, 0))

    ttk.Separator(body, orient=tk.HORIZONTAL).pack(
        fill=tk.X, pady=(12, 10))

    # -- Defaults ---------------------------------------------------
    ttk.Label(body, text=t("pref.defaults"),
              font=("TkDefaultFont", 10, "bold")).pack(anchor="w")

    first_team_label = t("pref.first_team")
    view_choices = [
        first_team_label,
        t("view.all"),
        t("view.free_agents"),
        t("view.young"),
        t("view.scorers"),
        t("view.squad"),
    ] + list(xi_entries.keys())
    current_view = prefs["default_view"] or first_team_label
    if current_view not in view_choices:
        current_view = first_team_label
    view_var = tk.StringVar(value=current_view)
    ttk.Label(body, text=t("pref.default_view")).pack(
        anchor="w", pady=(4, 2))
    ttk.Combobox(body, textvariable=view_var,
                 values=view_choices, state="readonly", width=34).pack(
        anchor="w", padx=(22, 0))

    fmt_choices = ["4-4-2", "4-3-3", "3-5-2"]
    current_fmt = prefs["default_formation"] if prefs["default_formation"] in fmt_choices else "4-4-2"
    fmt_var = tk.StringVar(value=current_fmt)
    ttk.Label(body, text=t("pref.default_form")).pack(
        anchor="w", pady=(8, 2))
    ttk.Combobox(body, textvariable=fmt_var,
                 values=fmt_choices, state="readonly", width=10).pack(
        anchor="w", padx=(22, 0))

    theme_choices = [
        ("retro", t("pref.theme_retro")),
        ("light", t("pref.theme_light")),
    ]
    theme_labels = [label for _, label in theme_choices]
    theme_lookup = dict(theme_choices)
    reverse_theme_lookup = {label: key for key, label in theme_choices}
    current_theme_key = prefs["theme"] if prefs["theme"] in theme_lookup else "retro"
    theme_var = tk.StringVar(value=theme_lookup[current_theme_key])
    ttk.Label(body, text=t("pref.theme")).pack(anchor="w", pady=(8, 2))
    ttk.Combobox(body, textvariable=theme_var,
                 values=theme_labels, state="readonly", width=34).pack(
        anchor="w", padx=(22, 0))

    font_var = tk.BooleanVar(value=bool(prefs["use_system_font"]))
    ttk.Checkbutton(body,
                    text=t("pref.system_font"),
                    variable=font_var).pack(anchor="w", pady=(10, 0))
    ttk.Label(body,
              text=t("pref.font_note"),
              foreground="#888").pack(anchor="w", padx=(22, 0))

    warn_var = tk.BooleanVar(value=bool(prefs["skill_warnings"]))
    ttk.Checkbutton(body,
                    text=t("pref.skill_warn"),
                    variable=warn_var).pack(anchor="w", pady=(10, 0))
    ttk.Label(body,
              text=t("pref.skill_warn_note"),
              foreground="#888", justify=tk.LEFT).pack(
        anchor="w", padx=(22, 0))

    ttk.Separator(body, orient=tk.HORIZONTAL).pack(
        fill=tk.X, pady=(12, 10))

    # -- Updates ----------------------------------------------------
    ttk.Label(body, text=t("pref.updates"),
              font=("TkDefaultFont", 10, "bold")).pack(anchor="w")

    _freq_saved = prefs.get("update_interval", "weekly")
    if _freq_saved not in ("daily", "weekly"):
        _freq_saved = "weekly"
    _current_freq = "disabled" if not update_state.get("opted_in") else _freq_saved
    freq_var = tk.StringVar(value=_current_freq)
    ttk.Label(body, text=t("pref.update_freq")).pack(anchor="w", pady=(4, 2))
    for _label, _val in [(t("pref.upd_disabled"), "disabled"),
                         (t("pref.upd_daily"),    "daily"),
                         (t("pref.upd_weekly"),   "weekly")]:
        ttk.Radiobutton(body, text=_label,
                        variable=freq_var, value=_val).pack(
            anchor="w", padx=(22, 0))
    ttk.Label(
        body,
        text=t("pref.upd_note"),
        foreground="#888",
        justify=tk.LEFT,
    ).pack(anchor="w", pady=(4, 0))

    ttk.Separator(body, orient=tk.HORIZONTAL).pack(
        fill=tk.X, pady=(12, 10))

    # -- Language ---------------------------------------------------
    ttk.Label(body, text=t("pref.language"),
              font=("TkDefaultFont", 10, "bold")).pack(anchor="w")

    lang_choices = [("en", "English"), ("it", "Italiano")]
    lang_labels = [lbl for _, lbl in lang_choices]
    lang_lookup = dict(lang_choices)
    reverse_lang_lookup = {lbl: code for code, lbl in lang_choices}
    current_lang_code = prefs.get("language", "en")
    if current_lang_code not in lang_lookup:
        current_lang_code = "en"
    lang_var = tk.StringVar(value=lang_lookup[current_lang_code])
    ttk.Combobox(body, textvariable=lang_var,
                 values=lang_labels, state="readonly", width=14).pack(
        anchor="w", pady=(4, 0))
    ttk.Label(body,
              text=t("pref.lang_note"),
              foreground="#888").pack(anchor="w")

    btns = ttk.Frame(body)
    btns.pack(fill=tk.X, pady=(14, 0))

    def _save_and_close():
        prefs["show_splash"] = bool(splash_var.get())
        prefs["show_welcome"] = bool(welcome_var.get())
        prefs["auto_open_last_save"] = bool(auto_save_var.get())
        prefs["auto_open_last_game"] = bool(auto_game_var.get())
        picked_view = view_var.get()
        prefs["default_view"] = (
            "" if picked_view == first_team_label else picked_view
        )
        prefs["default_formation"] = fmt_var.get()
        prefs["use_system_font"] = bool(font_var.get())
        prefs["theme"] = reverse_theme_lookup.get(theme_var.get(), "retro")
        prefs["skill_warnings"] = bool(warn_var.get())
        freq = freq_var.get()
        update_state["opted_in"] = (freq != "disabled")
        if freq in ("daily", "weekly"):
            prefs["update_interval"] = freq
        prefs["language"] = reverse_lang_lookup.get(lang_var.get(), "en")
        preferences.save(prefs)
        updates.save_state(update_state)
        top.destroy()
        if on_saved is not None:
            on_saved()

    ttk.Button(btns, text=t("btn.cancel"),
               command=top.destroy).pack(side=tk.RIGHT)
    ttk.Button(btns, text=t("btn.save"),
               command=_save_and_close).pack(side=tk.RIGHT, padx=(0, 8))

    top.grab_set()


def _pref_path_label(path: str) -> str:
    """Format a remembered path for display under its checkbox."""
    if not path:
        return t("pref.path_none")
    if not os.path.isfile(path):
        return t("pref.path_missing") + path
    return path
