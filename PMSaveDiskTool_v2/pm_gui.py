#!/usr/bin/env python3
"""Cross-platform tkinter GUI for PMSaveDiskToolkit.

Mirrors the workflow of the original Windows PMSaveDiskTool:
Open ADF -> Select save slot -> Browse players by team -> Edit attributes -> Save.
"""

import csv
import json
import os
import sys
import tkinter as tk
import webbrowser
from tkinter import ttk, filedialog, messagebox

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from pm_core import __version__
from pm_core.adf import ADF, ensure_backup
from pm_core.save import SaveSlot, player_to_row
from pm_core.player import (
    SKILL_NAMES, POSITION_NAMES, PlayerRecord,
    RECORD_SIZE, FIELD_LAYOUT, field_at_offset, serialize_player,
)
from pm_core.names import GameDisk
from pm_core import updates
from pm_core import fonts
from pm_core import preferences

from pm_gui_theme import (
    PAL, FONT_DATA, _retro, apply_theme, set_theme, set_use_system_font,
)
from pm_gui_help import HelpDialog, help_button
from pm_gui_help_search import HelpSearchWindow
from pm_gui_career import CareerTrackerWindow
from pm_gui_workbench import ByteWorkbenchWindow
from pm_gui_lineup import LineupCoachWindow
from pm_gui_compare import PlayerCompareWindow
from pm_gui_welcome import WelcomeDialog
from pm_gui_splash import show_splash
from pm_gui_preferences import open_preferences


XI_ENTRIES = {
    "— Top 11 (4-4-2)":   {"formation": "4-4-2", "filter_fn": None},
    "— Top 11 (4-3-3)":   {"formation": "4-3-3", "filter_fn": None},
    "— Young XI (≤21)":  {"formation": "4-4-2",
                           "filter_fn": lambda p: p.age <= 21},
    "— Free-Agent XI":    {"formation": "4-4-2",
                           "filter_fn": lambda p: p.is_free_agent},
}

# Platform-specific modifier for accelerators: Cmd on macOS, Ctrl elsewhere.
if sys.platform == "darwin":
    MOD, MOD_LABEL = "Command", "Cmd"
else:
    MOD, MOD_LABEL = "Control", "Ctrl"

CONFIG_DIR = os.path.expanduser("~/.pmsavedisktool")
RECENT_FILE = os.path.join(CONFIG_DIR, "recent.json")
RECENT_LIMIT = 5
GITHUB_URL = "https://github.com/vitopod/amiga-player-manager-toolkit"
LICENSE_URL = f"{GITHUB_URL}/blob/main/LICENSE"

def _load_recent() -> list[str]:
    try:
        with open(RECENT_FILE) as f:
            data = json.load(f)
        return [p for p in data.get("save_adfs", []) if isinstance(p, str)]
    except (OSError, json.JSONDecodeError):
        return []


def _save_recent(paths: list[str]) -> None:
    try:
        os.makedirs(CONFIG_DIR, exist_ok=True)
        with open(RECENT_FILE, "w") as f:
            json.dump({"save_adfs": paths[:RECENT_LIMIT]}, f, indent=2)
    except OSError:
        pass  # recent list is best-effort


def _pref_update(**fields) -> None:
    """Merge ``fields`` into the on-disk preferences file."""
    state = preferences.load()
    state.update(fields)
    preferences.save(state)


def _pref_initialdir(key: str) -> str:
    """Seed ``filedialog.askopenfilename`` from a remembered path.

    Returns the directory portion of ``preferences[key]`` if that file
    still exists, otherwise an empty string (tk uses CWD in that case).
    """
    path = preferences.load().get(key, "")
    if path and os.path.isfile(path):
        return os.path.dirname(path)
    return ""


class PMSaveDiskToolGUI:
    def __init__(self, root):
        self.root = root
        self.root.geometry("1100x700")
        self.root.minsize(900, 600)

        self.adf = None
        self.slot = None
        self.current_player = None
        self.adf_path = None
        self.game_disk = None   # GameDisk for name generation (optional)
        self.dirty = False

        self._build_title_band()
        self._build_menu()
        self._build_toolbar()
        self._build_main()
        self._build_status_bar()
        self._update_title()

        self.root.protocol("WM_DELETE_WINDOW", self._on_quit)
        if sys.platform == "darwin":
            self.root.createcommand("tk::mac::Quit", self._on_quit)

        # Fire the daily update check after the window has mapped and the
        # splash screen has had a moment to settle. 800 ms is enough for
        # both on every OS the toolkit targets.
        self.root.after(800, self._schedule_startup_update_check)

    # ── Title band ────────────────────────────────────────────

    def _build_title_band(self):
        band = tk.Frame(self.root, bg=PAL["bg_header"], height=32)
        band.pack(fill=tk.X, side=tk.TOP)
        band.pack_propagate(False)

        self._title_left = tk.Label(
            band, text="PLAYER MANAGER TOOLKIT",
            bg=PAL["bg_header"], fg=PAL["fg_title"],
            font=_retro(14, "bold"),
        )
        self._title_left.pack(side=tk.LEFT, padx=10)

        # Update banner sits next to the title; hidden until the
        # background or manual check finds a newer release on GitHub.
        self._title_banner = tk.Label(
            band, text="",
            bg=PAL["fg_data"], fg=PAL["bg_header"],
            font=_retro(10, "bold"),
            cursor="hand2",
        )
        # intentionally not packed here — shown later via _show_update_banner

        self._title_right = tk.Label(
            band, text="",
            bg=PAL["bg_header"], fg=PAL["fg_label"],
            font=_retro(10),
        )
        self._title_right.pack(side=tk.RIGHT, padx=10)

    # ── Menu ──────────────────────────────────────────────────

    def _build_menu(self):
        menubar = tk.Menu(self.root)
        is_mac = sys.platform == "darwin"

        # macOS apple menu (holds About per platform convention).
        if is_mac:
            app_menu = tk.Menu(menubar, name="apple", tearoff=0)
            app_menu.add_command(label="About PMSaveDiskTool",
                                 command=self._show_about)
            menubar.add_cascade(menu=app_menu)

        # File
        file_menu = tk.Menu(menubar, tearoff=0)
        file_menu.add_command(label="Open Save Disk…",
                              command=self._open_adf,
                              accelerator=f"{MOD_LABEL}+O")
        file_menu.add_command(label="Open Game Disk…",
                              command=self._open_game_adf,
                              accelerator=f"{MOD_LABEL}+G")
        self.recent_menu = tk.Menu(file_menu, tearoff=0)
        file_menu.add_cascade(label="Open Recent", menu=self.recent_menu)
        self._rebuild_recent_menu()
        file_menu.add_separator()
        file_menu.add_command(label="Save",
                              command=self._save_adf,
                              accelerator=f"{MOD_LABEL}+S")
        file_menu.add_command(label="Save As…",
                              command=self._save_adf_as,
                              accelerator=f"{MOD_LABEL}+Shift+S")
        file_menu.add_separator()
        file_menu.add_command(label="Export Players…",
                              command=self._export_players,
                              accelerator=f"{MOD_LABEL}+E")
        if not is_mac:
            file_menu.add_separator()
            file_menu.add_command(label="Quit",
                                  command=self._on_quit,
                                  accelerator=f"{MOD_LABEL}+Q")
        menubar.add_cascade(label="File", menu=file_menu)

        # Edit
        edit_menu = tk.Menu(menubar, tearoff=0)
        edit_menu.add_command(label="Apply Changes",
                              command=self._apply_changes,
                              accelerator=f"{MOD_LABEL}+Return")
        edit_menu.add_command(label="Revert Player",
                              command=self._revert_player,
                              accelerator="Esc")
        edit_menu.add_separator()
        edit_menu.add_command(label="Find Player…",
                              command=self._find_player,
                              accelerator=f"{MOD_LABEL}+F")
        menubar.add_cascade(label="Edit", menu=edit_menu)

        # View — mirrors the team-combo analytical entries with accelerators.
        view_menu = tk.Menu(menubar, tearoff=0)
        view_menu.add_command(label="All Players",
                              command=lambda: self._set_view("All Players"))
        view_menu.add_command(label="Free Agents",
                              command=lambda: self._set_view("Free Agents"))
        view_menu.add_separator()
        view_menu.add_command(label="Young Talents (≤21)",
                              command=lambda: self._set_view("— Young Talents (≤21)"),
                              accelerator=f"{MOD_LABEL}+Y")
        view_menu.add_command(label="Top Scorers",
                              command=lambda: self._set_view("— Top Scorers"))
        view_menu.add_command(label="Squad Analyst (all teams)",
                              command=lambda: self._set_view("— Squad Analyst (all teams)"))
        view_menu.add_separator()
        xi_menu = tk.Menu(view_menu, tearoff=0)
        for label in XI_ENTRIES:
            display = label.lstrip("— ").rstrip()
            xi_menu.add_command(
                label=display,
                command=lambda L=label: self._set_view(L),
            )
        view_menu.add_cascade(label="Best XI", menu=xi_menu)
        menubar.add_cascade(label="View", menu=view_menu)

        # Tools
        tools_menu = tk.Menu(menubar, tearoff=0)
        tools_menu.add_command(label="Career Tracker…",
                               command=self._open_career_tracker,
                               accelerator=f"{MOD_LABEL}+T")
        tools_menu.add_command(label="Byte Workbench…",
                               command=self._open_byte_workbench,
                               accelerator=f"{MOD_LABEL}+B")
        tools_menu.add_command(label="Line-up Coach (BETA)…",
                               command=self._open_lineup_coach,
                               accelerator=f"{MOD_LABEL}+L")
        tools_menu.add_command(label="Compare Players…",
                               command=self._open_compare,
                               accelerator=f"{MOD_LABEL}+P")
        menubar.add_cascade(label="Tools", menu=tools_menu)

        # Help
        help_menu = tk.Menu(menubar, tearoff=0)
        help_menu.add_command(label="Find in Help…",
                              command=self._open_help_search,
                              accelerator=f"{MOD_LABEL}+?")
        help_menu.add_separator()
        help_menu.add_command(label="Open Manual", command=self._open_manual)
        help_menu.add_command(label="Check for Updates…",
                              command=self._check_for_updates)
        help_menu.add_command(label="Preferences…",
                              command=self._show_preferences)
        if not is_mac:
            help_menu.add_separator()
            help_menu.add_command(label="About", command=self._show_about)
        menubar.add_cascade(label="Help", menu=help_menu)

        self.root.config(menu=menubar)

        # Accelerator bindings (menu `accelerator=` only displays — doesn't bind).
        bind = self.root.bind
        bind(f"<{MOD}-o>", lambda e: self._open_adf())
        bind(f"<{MOD}-g>", lambda e: self._open_game_adf())
        bind(f"<{MOD}-s>", lambda e: self._save_adf())
        bind(f"<{MOD}-S>", lambda e: self._save_adf_as())  # Shift+S
        bind(f"<{MOD}-e>", lambda e: self._export_players())
        bind(f"<{MOD}-f>", lambda e: self._find_player())
        bind(f"<{MOD}-t>", lambda e: self._open_career_tracker())
        bind(f"<{MOD}-b>", lambda e: self._open_byte_workbench())
        bind(f"<{MOD}-l>", lambda e: self._open_lineup_coach())
        bind(f"<{MOD}-p>", lambda e: self._open_compare())
        bind(f"<{MOD}-question>", lambda e: self._open_help_search())
        bind(f"<{MOD}-y>", lambda e: self._set_view("— Young Talents (≤21)"))
        bind(f"<{MOD}-Return>", lambda e: self._apply_changes())
        bind("<Escape>", lambda e: self._on_escape())
        if not is_mac:
            bind(f"<{MOD}-q>", lambda e: self._on_quit())

    # ── Toolbar ───────────────────────────────────────────────

    def _build_toolbar(self):
        toolbar = tk.Frame(self.root, bg=PAL["bg_mid"])
        toolbar.pack(fill=tk.X, padx=0, pady=0)

        tk.Label(toolbar, text="SAVE:", bg=PAL["bg_mid"], fg=PAL["fg_label"],
                 font=("Courier New", 8)).pack(side=tk.LEFT, padx=(10, 2))
        self.save_var = tk.StringVar()
        self.save_combo = ttk.Combobox(toolbar, textvariable=self.save_var,
                                       state="readonly", width=12)
        self.save_combo.pack(side=tk.LEFT, padx=2)
        self.save_combo.bind("<<ComboboxSelected>>", self._on_save_selected)

        tk.Label(toolbar, text="VIEW:", bg=PAL["bg_mid"], fg=PAL["fg_label"],
                 font=("Courier New", 8)).pack(side=tk.LEFT, padx=(14, 2))
        self.team_var = tk.StringVar()
        self.team_combo = ttk.Combobox(toolbar, textvariable=self.team_var,
                                       state="readonly", width=28)
        self.team_combo.pack(side=tk.LEFT, padx=2)
        self.team_combo.bind("<<ComboboxSelected>>", self._on_team_selected)

        help_button(toolbar, "main_window").pack(side=tk.RIGHT, padx=(4, 10))

    # ── Main area ─────────────────────────────────────────────

    def _build_main(self):
        paned = ttk.PanedWindow(self.root, orient=tk.HORIZONTAL)
        paned.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

        # Left: Player list
        left = ttk.Frame(paned)
        paned.add(left, weight=1)

        self.summary_var = tk.StringVar(value="")
        self.summary_label = ttk.Label(left, textvariable=self.summary_var,
                                       anchor="w", foreground=PAL["fg_label"])
        self.summary_label.pack(fill=tk.X, padx=3, pady=(0, 2))

        search_bar = ttk.Frame(left)
        search_bar.pack(fill=tk.X, padx=0, pady=(0, 3))
        ttk.Label(search_bar, text="Filter:").pack(side=tk.LEFT, padx=(2, 4))
        self.search_var = tk.StringVar()
        self.search_var.trace_add("write", lambda *_: self._refresh_player_list())
        self.search_entry = ttk.Entry(search_bar, textvariable=self.search_var)
        self.search_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 2))
        ttk.Button(search_bar, text="×", width=2,
                   command=lambda: self.search_var.set("")).pack(side=tk.LEFT)

        cols = ("id", "name", "age", "pos", "team", "total", "mkt")
        self.tree = ttk.Treeview(left, columns=cols, show="headings", selectmode="browse")
        self.tree.heading("id", text="ID")
        self.tree.heading("name", text="Name")
        self.tree.heading("age", text="Age")
        self.tree.heading("pos", text="Pos")
        self.tree.heading("team", text="Team")
        self.tree.heading("total", text="Skill")
        self.tree.heading("mkt", text="Mkt")
        self.tree.column("id", width=50, anchor="e")
        self.tree.column("name", width=140)
        self.tree.column("age", width=40, anchor="e")
        self.tree.column("pos", width=45, anchor="center")
        self.tree.column("team", width=120)
        self.tree.column("total", width=50, anchor="e")
        self.tree.column("mkt", width=30, anchor="center", stretch=False)

        scrollbar = ttk.Scrollbar(left, orient=tk.VERTICAL, command=self.tree.yview)
        self.tree.configure(yscrollcommand=scrollbar.set)
        self.tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.tree.bind("<<TreeviewSelect>>", self._on_player_selected)
        self.tree.bind("<Button-2>", self._on_tree_right_click)   # macOS
        self.tree.bind("<Button-3>", self._on_tree_right_click)   # Windows/Linux
        self.tree.tag_configure("free", foreground=PAL["free_agent"])

        # Right: header (identity) + notebook (editable fields) + sticky footer (Apply)
        right = ttk.Frame(paned)
        paned.add(right, weight=1)

        self.detail_header = tk.Frame(right, bg=PAL["bg_mid"])
        self.detail_header.pack(fill=tk.X)

        self.notebook = ttk.Notebook(right)
        self.notebook.pack(fill=tk.BOTH, expand=True, padx=4, pady=4)

        footer = tk.Frame(right, bg=PAL["btn_go"])
        footer.pack(fill=tk.X, side=tk.BOTTOM)
        # Clickable tk.Label instead of tk.Button — on macOS Aqua a native
        # tk.Button silently ignores bg/fg and re-paints itself in system
        # colours after focus returns from a modal Toplevel (e.g. after
        # closing Preferences), turning these into unreadable amber blobs.
        # tk.Label honours bg/fg on every platform.
        self.apply_button = self._make_footer_button(
            footer, "APPLY",
            bg=PAL["btn_go"], fg=PAL["btn_go_fg"],
            hover=PAL["selected"], command=self._apply_changes,
        )
        self.apply_button.pack(side=tk.RIGHT, padx=(4, 6), pady=4)
        self._make_footer_button(
            footer, "REVERT",
            bg=PAL["bg_mid"], fg=PAL["fg_data"],
            hover=PAL["selected"], command=self._revert_player,
        ).pack(side=tk.RIGHT, pady=4)

        self.fields = {}
        self._build_detail_fields()

    _CORE_FIELDS = [
        ("Age:", "age"), ("Position:", "position"), ("Division:", "division"),
        ("Team Index:", "team_index"),
        ("Height (cm):", "height"), ("Weight (kg):", "weight"),
    ]
    _STATUS_FIELDS = [
        ("Injury Weeks:", "injury_weeks"), ("Disciplinary:", "disciplinary"),
        ("Morale:", "morale"), ("Value:", "value"),
        ("Wks Since Transfer:", "weeks_since_transfer"),
    ]
    _SEASON_FIELDS = [
        ("Injuries This Yr:", "injuries_this_year"),
        ("Injuries Last Yr:", "injuries_last_year"),
        ("Dsp.Pts. This Yr:", "dsp_pts_this_year"),
        ("Dsp.Pts. Last Yr:", "dsp_pts_last_year"),
        ("Goals This Yr:", "goals_this_year"),
        ("Goals Last Yr:", "goals_last_year"),
        ("Matches This Yr:", "matches_this_year"),
        ("Matches Last Yr:", "matches_last_year"),
    ]
    _CAREER_FIELDS = [
        ("Div1 Years:", "div1_years"), ("Div2 Years:", "div2_years"),
        ("Div3 Years:", "div3_years"), ("Div4 Years:", "div4_years"),
        ("Int Years:", "int_years"), ("Contract Yrs:", "contract_years"),
    ]

    def _build_detail_fields(self):
        # Identity header (read-only; always visible above the tabs).
        for i, (label, key) in enumerate(
            [("Player #", "player_id"), ("Name", "name"), ("Seed", "rng_seed")]
        ):
            tk.Label(self.detail_header, text=label.upper(), anchor="e",
                     bg=PAL["bg_mid"], fg=PAL["fg_label"],
                     font=_retro(9, "bold")).grid(
                         row=0, column=i * 2, sticky="e", padx=(8, 4), pady=8)
            var = tk.StringVar()
            tk.Label(self.detail_header, textvariable=var,
                     bg=PAL["bg_mid"], fg=PAL["fg_title"],
                     font=_retro(12, "bold"), anchor="w").grid(
                         row=0, column=i * 2 + 1, sticky="w", padx=(0, 18), pady=8)
            self.fields[key] = var

        def add_field(parent, label, key, row):
            tk.Label(parent, text=label.upper(), anchor="e",
                     bg=PAL["bg"], fg=PAL["fg_data"],
                     font=_retro(10, "bold")).grid(
                         row=row, column=0, sticky="e", padx=(8, 4), pady=4)
            var = tk.StringVar()
            tk.Entry(parent, textvariable=var, width=12,
                     bg=PAL["field"], fg=PAL["fg_data"],
                     insertbackground=PAL["fg_data"],
                     relief="flat", bd=1,
                     font=("Courier New", 10)).grid(
                         row=row, column=1, sticky="w", padx=(2, 8), pady=3)
            self.fields[key] = var

        def add_tab(title, fields):
            tab = tk.Frame(self.notebook, bg=PAL["bg"])
            self.notebook.add(tab, text=title)
            for r, (label, key) in enumerate(fields):
                add_field(tab, label, key, r)
            return tab

        add_tab("Core", self._CORE_FIELDS)

        # Skills tab: two columns so all 10 fit without scrolling.
        skills_tab = tk.Frame(self.notebook, bg=PAL["bg"])
        self.notebook.add(skills_tab, text="Skills")
        self._skill_bars: dict[str, tk.Canvas] = {}
        half = (len(SKILL_NAMES) + 1) // 2
        for i, skill in enumerate(SKILL_NAMES):
            if i < half:
                lc, ec, bc = 0, 1, 2
                row = i
            else:
                lc, ec, bc = 3, 4, 5
                row = i - half

            tk.Label(skills_tab, text=f"{skill.upper()}:", anchor="e",
                     bg=PAL["bg"], fg=PAL["fg_data"],
                     font=("Courier New", 10, "bold")).grid(
                         row=row, column=lc, sticky="e", padx=(8, 3), pady=4)

            var = tk.StringVar()
            tk.Entry(skills_tab, textvariable=var, width=5,
                     bg="#000044", fg=PAL["fg_data"], insertbackground=PAL["fg_data"],
                     relief="flat", bd=1, font=("Courier New", 10)).grid(
                         row=row, column=ec, sticky="w", padx=(2, 4), pady=3)
            self.fields[skill] = var
            var.trace_add("write", lambda *_, s=skill: self._redraw_skill_bar_single(s))

            bar = tk.Canvas(skills_tab, width=60, height=8,
                            bg=PAL["bg"], highlightthickness=0)
            bar.grid(row=row, column=bc, sticky="w", padx=(0, 10), pady=3)
            self._skill_bars[skill] = bar

        add_tab("Status", self._STATUS_FIELDS)
        add_tab("Season", self._SEASON_FIELDS)
        add_tab("Career", self._CAREER_FIELDS)

    # ── Status bar ────────────────────────────────────────────

    def _build_status_bar(self):
        bar = tk.Frame(self.root, bg=PAL["status_bar"], height=22)
        bar.pack(fill=tk.X, side=tk.BOTTOM)
        bar.pack_propagate(False)

        self.status_var = tk.StringVar(value="Open a save disk to begin.")
        tk.Label(bar, textvariable=self.status_var, anchor="w",
                 bg=PAL["status_bar"], fg=PAL["fg_dim"],
                 font=("Courier New", 9)).pack(
                     side=tk.LEFT, fill=tk.X, expand=True, padx=6)

        self.game_label = tk.Label(bar, text="No game disk",
                                   bg=PAL["status_bar"], fg=PAL["fg_dim"],
                                   font=("Courier New", 9), anchor="e")
        self.game_label.pack(side=tk.RIGHT, padx=6)

        self.beta_pill = tk.Label(
            bar, text=" BETA ",
            bg="#b36b00", fg="white", font=("Courier New", 9, "bold"),
            padx=4,
        )

    # ── Actions ───────────────────────────────────────────────

    def _open_adf(self):
        path = filedialog.askopenfilename(
            title="Open Player Manager Save Disk",
            filetypes=[("ADF Disk Images", "*.adf"), ("All Files", "*.*")],
            initialdir=_pref_initialdir("last_save_adf"),
        )
        if path:
            self._open_adf_path(path)

    def _open_game_adf(self):
        path = filedialog.askopenfilename(
            title="Open Player Manager Game Disk",
            filetypes=[("ADF Disk Images", "*.adf"), ("All Files", "*.*")],
            initialdir=_pref_initialdir("last_game_adf"),
        )
        if not path:
            return
        self._load_game_adf_path(path)

    def _load_game_adf_path(self, path: str):
        """Load a specific game ADF path (used by Open Game Disk + auto-open)."""
        try:
            self.game_disk = GameDisk.load(path)
        except Exception as e:
            messagebox.showerror("Error", f"Failed to load game ADF:\n{e}")
            return
        _pref_update(last_game_adf=path)

        gd = self.game_disk
        fname = os.path.basename(path)
        # Toggle BETA pill: visible only for builds whose name generation
        # hasn't been verified against the live game.
        if gd.is_beta:
            self.beta_pill.pack(side=tk.RIGHT, padx=(0, 2))
        else:
            self.beta_pill.pack_forget()

        if gd.names_available and not gd.is_beta:
            self.game_label.config(
                text=f"{fname} ({gd.surname_count} names)",
                foreground=PAL["free_agent"],
            )
            self.status_var.set(
                f"Game ADF loaded: {gd.surname_count} Italian surnames available"
            )
        elif gd.names_available and gd.is_beta:
            self.game_label.config(
                text=f"{fname} ({gd.surname_count} names, {gd.build})",
                foreground="#b36b00",
            )
            self.status_var.set(
                f"Game ADF loaded ({gd.build} BETA): {gd.surname_count} surnames. "
                "Initials are a best-guess — may not match in-game exactly."
            )
            messagebox.showwarning(
                "English name resolution (BETA)",
                f"Loaded as '{gd.build}' build: {gd.surname_count} English "
                "surnames extracted from the disk.\n\n"
                "Surnames and initials charsets have been cross-checked "
                "against a real in-game roster screen and match. What's "
                "still unverified is the full seed → exact-name mapping "
                "— individual players could in principle resolve to "
                "slightly different names than the game displays. Hence "
                "BETA.\n\n"
                "Save editing and all other features work normally.",
            )
        else:
            self.game_label.config(
                text=f"{fname} (no names — {gd.build})",
                foreground="#b36b00",
            )
            self.status_var.set(
                f"Game ADF loaded ({gd.build} build) — player names "
                f"unavailable for this version; save editing works normally"
            )
            messagebox.showwarning(
                "Player names unavailable",
                f"Loaded a recognisable Player Manager game disk "
                f"(detected build: {gd.build}), but no surname table could "
                "be located for this version.\n\n"
                "Player names will stay blank. All other features "
                "(rosters, editing, Best XI, Line-up Coach, exports) work "
                "normally.",
            )
        # Apply team-name fallback for saves without PM1.nam (English/BETA).
        if self.slot and gd.team_names:
            self.slot.apply_team_name_fallback(gd.team_names)
        # Refresh list if a save is already open
        if self.slot:
            self._refresh_team_combo()
            self._refresh_player_list()

    def _refresh_team_combo(self):
        """Rebuild the team filter combo from the current slot."""
        team_options = ["All Players", "Free Agents"]
        for i, name in enumerate(self.slot.team_names):
            team_options.append(f"{i}: {name}")
        team_options.append("— Young Talents (≤21)")
        team_options.append("— Top Scorers")
        team_options.append("— Squad Analyst (all teams)")
        team_options.extend(XI_ENTRIES.keys())
        current = self.team_combo.get()
        self.team_combo["values"] = team_options
        if current in team_options:
            self.team_combo.set(current)
        else:
            self.team_combo.current(0)

    def _on_save_selected(self, event):
        save_name = self.save_var.get()
        if not save_name or not self.adf:
            return
        try:
            self.slot = SaveSlot(self.adf, save_name)
        except Exception as e:
            messagebox.showerror("Error", f"Failed to load save: {e}")
            return

        # If a game disk is already loaded, apply its team-name fallback.
        if self.game_disk and self.game_disk.team_names:
            self.slot.apply_team_name_fallback(self.game_disk.team_names)

        # Populate team filter
        team_options = ["All Players", "Free Agents"]
        for i, name in enumerate(self.slot.team_names):
            team_options.append(f"{i}: {name}")
        team_options.append("— Young Talents (≤21)")
        team_options.append("— Top Scorers")
        team_options.append("— Squad Analyst (all teams)")
        team_options.extend(XI_ENTRIES.keys())
        self.team_combo["values"] = team_options
        pref_view = preferences.load().get("default_view", "")
        if pref_view and pref_view in team_options:
            self.team_combo.set(pref_view)
        else:
            self.team_combo.current(0)
        self._refresh_player_list()
        self.status_var.set(f"Loaded save: {save_name}")

    def _on_team_selected(self, event):
        self._refresh_player_list()

    _DEFAULT_TREE_HEADINGS = {
        "id": "ID", "name": "Name", "age": "Age", "pos": "Pos",
        "team": "Team", "total": "Skill", "mkt": "Mkt",
    }

    def _set_tree_headings(self, **overrides):
        for col, text in self._DEFAULT_TREE_HEADINGS.items():
            self.tree.heading(col, text=overrides.get(col, text))

    def _refresh_player_list(self):
        if not self.slot:
            return
        self.tree.delete(*self.tree.get_children())
        self.summary_var.set("")

        team_sel = self.team_var.get()
        if team_sel == "— Squad Analyst (all teams)":
            self._populate_squad_analyst()
            return

        self._set_tree_headings()

        if team_sel == "— Young Talents (≤21)":
            players = self.slot.get_young_talents()
            self.tree.heading("total", text="Skill")
            score_fn = lambda p: p.total_skill
        elif team_sel == "— Top Scorers":
            players = self.slot.get_top_scorers()
            self.tree.heading("total", text="Goals")
            score_fn = lambda p: p.goals_this_year
        elif team_sel in XI_ENTRIES:
            cfg = XI_ENTRIES[team_sel]
            players = self.slot.best_xi(cfg["formation"], filter_fn=cfg["filter_fn"])
            self.tree.heading("total", text="Skill")
            score_fn = lambda p: p.total_skill
        elif team_sel == "Free Agents":
            players = self.slot.get_free_agents()
            self.tree.heading("total", text="Skill")
            score_fn = lambda p: p.total_skill
        elif team_sel.startswith("All"):
            players = [p for p in self.slot.players if p.age > 0]
            self.tree.heading("total", text="Skill")
            score_fn = lambda p: p.total_skill
        else:
            team_idx = int(team_sel.split(":")[0])
            players = self.slot.get_players_by_team(team_idx)
            self.tree.heading("total", text="Skill")
            score_fn = lambda p: p.total_skill
            s = self.slot.squad_summary(team_idx)
            if s["size"] > 0:
                self.summary_var.set(
                    f"{s['size']} players  ·  avg {s['avg_age']:.1f}y  ·  "
                    f"skill {s['avg_skill']:.0f}  ·  {s['on_market']} on market"
                )

        needle = self.search_var.get().strip().lower() if hasattr(self, "search_var") else ""
        for p in players:
            team = self.slot.get_team_name(p.team_index)
            name = (self.game_disk.player_full_name(p.rng_seed)
                    if self.game_disk and p.rng_seed else "")
            if needle:
                haystack = f"{p.player_id} {name} {team} {p.position_name}".lower()
                if needle not in haystack:
                    continue
            mkt = "★" if p.is_market_available else ""
            tags = ("free",) if p.is_free_agent else ()
            self.tree.insert("", "end", iid=str(p.player_id),
                             values=(p.player_id, name, p.age, p.position_name,
                                     team, score_fn(p), mkt), tags=tags)

    def _populate_squad_analyst(self):
        """Render one row per team with composition summary columns.

        Repurposes the existing tree: id=team_index, name=team_name,
        age=avg_age, pos=size (roster count), team='GK/DEF/MID/FWD'
        breakdown, total=avg_skill, mkt=on_market count.
        """
        self._set_tree_headings(
            id="Tm", name="Team", age="AvgAge", pos="Size",
            team="GK·DEF·MID·FWD", total="AvgSkl", mkt="Mkt",
        )
        needle = self.search_var.get().strip().lower() if hasattr(self, "search_var") else ""
        for s in self.slot.all_squad_summaries():
            team_name = s["team_name"]
            if needle and needle not in f"{s['team_index']} {team_name}".lower():
                continue
            bp = s["by_position"]
            breakdown = f"{bp['GK']}·{bp['DEF']}·{bp['MID']}·{bp['FWD']}"
            self.tree.insert(
                "", "end", iid=f"squad-{s['team_index']}",
                values=(s["team_index"], team_name,
                        f"{s['avg_age']:.1f}", s["size"], breakdown,
                        f"{s['avg_skill']:.0f}", s["on_market"]),
            )

    def _on_player_selected(self, event):
        sel = self.tree.selection()
        if not sel or not self.slot:
            return
        # Squad Analyst rows are not players — skip the detail-panel update.
        if sel[0].startswith("squad-"):
            return
        player_id = int(sel[0])
        p = self.slot.get_player(player_id)
        self.current_player = p
        self._populate_fields(p)

    def _redraw_skill_bars(self) -> None:
        for skill, bar in self._skill_bars.items():
            bar.delete("all")
            try:
                val = int(self.fields[skill].get())
            except ValueError:
                val = 0
            val = max(0, min(val, 99))
            fill_w = int(60 * val / 99)
            bar.create_rectangle(0, 0, 60, 8, fill=PAL["bar_trough"], outline=PAL["border"])
            if fill_w > 0:
                bar.create_rectangle(0, 0, fill_w, 8,
                                     fill=PAL["fg_title"], outline="")

    def _redraw_skill_bar_single(self, skill: str) -> None:
        bar = self._skill_bars.get(skill)
        if bar is None:
            return
        bar.delete("all")
        try:
            val = int(self.fields[skill].get())
        except ValueError:
            val = 0
        val = max(0, min(val, 99))
        fill_w = int(60 * val / 99)
        bar.create_rectangle(0, 0, 60, 8, fill=PAL["bar_trough"], outline=PAL["border"])
        if fill_w > 0:
            bar.create_rectangle(0, 0, fill_w, 8, fill=PAL["fg_title"], outline="")

    def _populate_fields(self, p: PlayerRecord):
        self.fields["player_id"].set(str(p.player_id))
        name = (self.game_disk.player_full_name(p.rng_seed)
                if self.game_disk and p.rng_seed else "")
        self.fields["name"].set(name)
        self.fields["rng_seed"].set(f"0x{p.rng_seed:08x}")
        self.fields["age"].set(str(p.age))
        self.fields["position"].set(str(p.position))
        self.fields["division"].set(str(p.division))
        self.fields["team_index"].set(str(p.team_index))
        self.fields["height"].set(str(p.height))
        self.fields["weight"].set(str(p.weight))
        for skill in SKILL_NAMES:
            self.fields[skill].set(str(getattr(p, skill)))
        self.fields["injury_weeks"].set(str(p.injury_weeks))
        self.fields["disciplinary"].set(str(p.disciplinary))
        self.fields["morale"].set(str(p.morale))
        self.fields["value"].set(str(p.value))
        self.fields["weeks_since_transfer"].set(str(p.weeks_since_transfer))
        self.fields["injuries_this_year"].set(str(p.injuries_this_year))
        self.fields["injuries_last_year"].set(str(p.injuries_last_year))
        self.fields["dsp_pts_this_year"].set(str(p.dsp_pts_this_year))
        self.fields["dsp_pts_last_year"].set(str(p.dsp_pts_last_year))
        self.fields["goals_this_year"].set(str(p.goals_this_year))
        self.fields["goals_last_year"].set(str(p.goals_last_year))
        self.fields["matches_this_year"].set(str(p.matches_this_year))
        self.fields["matches_last_year"].set(str(p.matches_last_year))
        self.fields["div1_years"].set(str(p.div1_years))
        self.fields["div2_years"].set(str(p.div2_years))
        self.fields["div3_years"].set(str(p.div3_years))
        self.fields["div4_years"].set(str(p.div4_years))
        self.fields["int_years"].set(str(p.int_years))
        self.fields["contract_years"].set(str(p.contract_years))
        self._redraw_skill_bars()

    @staticmethod
    def _make_footer_button(parent, text, *, bg, fg, hover, command):
        """Clickable ``tk.Label`` styled as a button.

        Used instead of ``tk.Button`` for the APPLY / REVERT footer —
        see the note in ``_build_*`` where this is instantiated.
        """
        lbl = tk.Label(
            parent, text=text,
            bg=bg, fg=fg,
            font=("Courier New", 10, "bold"),
            padx=14, pady=5,
            borderwidth=0, highlightthickness=0,
            cursor="hand2",
        )
        lbl.bind("<Button-1>", lambda _e: command())
        lbl.bind("<Enter>", lambda _e: lbl.configure(bg=hover))
        lbl.bind("<Leave>", lambda _e: lbl.configure(bg=bg))
        return lbl

    def _apply_changes(self):
        if not self.current_player or not self.slot:
            messagebox.showwarning("Warning", "No player selected.")
            return

        p = self.current_player
        editable_int_fields = [
            "age", "position", "division", "team_index", "height", "weight",
            *SKILL_NAMES,
            "injury_weeks", "disciplinary", "morale", "value", "weeks_since_transfer",
            "injuries_this_year", "injuries_last_year",
            "dsp_pts_this_year", "dsp_pts_last_year",
            "goals_this_year", "goals_last_year",
            "matches_this_year", "matches_last_year",
            "div1_years", "div2_years", "div3_years", "div4_years",
            "int_years", "contract_years",
        ]

        try:
            for field_name in editable_int_fields:
                val_str = self.fields[field_name].get()
                val = int(val_str)
                setattr(p, field_name, val)
        except ValueError as e:
            messagebox.showerror("Error", f"Invalid value for {field_name}: {val_str}")
            return

        self.slot.write_player(p.player_id)
        self._set_dirty(True)
        self._refresh_player_list()
        # Re-select the player
        try:
            self.tree.selection_set(str(p.player_id))
            self.tree.see(str(p.player_id))
        except tk.TclError:
            pass
        self.status_var.set(f"Applied changes to Player #{p.player_id}")

    def _save_adf(self):
        if not self.adf or not self.adf_path:
            messagebox.showwarning("Warning", "No ADF loaded.")
            return
        try:
            bak = ensure_backup(self.adf_path)
            self.adf.save(self.adf_path)
            msg = f"Saved: {os.path.basename(self.adf_path)}"
            if bak:
                msg += f"  (backup: {os.path.basename(bak)})"
            self.status_var.set(msg)
            self._set_dirty(False)
        except OSError as e:
            messagebox.showerror("Error", f"Failed to save: {e}")

    def _save_adf_as(self):
        if not self.adf:
            messagebox.showwarning("Warning", "No ADF loaded.")
            return
        path = filedialog.asksaveasfilename(
            title="Save ADF As",
            defaultextension=".adf",
            filetypes=[("ADF Disk Images", "*.adf"), ("All Files", "*.*")],
        )
        if not path:
            return
        try:
            self.adf.save(path)
            self.adf_path = path
            self.status_var.set(f"Saved: {os.path.basename(path)}")
            self._set_dirty(False)
            self._update_title()
        except OSError as e:
            messagebox.showerror("Error", f"Failed to save: {e}")

    def _rebuild_recent_menu(self):
        self.recent_menu.delete(0, "end")
        paths = _load_recent()
        if not paths:
            self.recent_menu.add_command(label="(empty)", state="disabled")
            return
        for p in paths:
            self.recent_menu.add_command(
                label=os.path.basename(p),
                command=lambda path=p: self._open_adf_path(path),
            )
        self.recent_menu.add_separator()
        self.recent_menu.add_command(label="Clear Recent",
                                     command=self._clear_recent)

    def _add_recent(self, path: str):
        paths = [p for p in _load_recent() if p != path]
        paths.insert(0, path)
        _save_recent(paths)
        self._rebuild_recent_menu()

    def _clear_recent(self):
        _save_recent([])
        self._rebuild_recent_menu()

    def _open_adf_path(self, path: str):
        """Open a specific ADF path (used by Recent menu)."""
        if not os.path.isfile(path):
            messagebox.showerror("Not found",
                                 f"File no longer exists:\n{path}")
            # Prune and rebuild
            _save_recent([p for p in _load_recent() if p != path])
            self._rebuild_recent_menu()
            return
        if self.dirty:
            answer = messagebox.askyesnocancel(
                "Unsaved changes",
                "Save current changes before opening a new ADF?",
            )
            if answer is None:
                return
            if answer:
                self._save_adf()
                if self.dirty:
                    return
        try:
            self.adf = ADF.load(path)
            self.adf_path = path
        except (ValueError, OSError) as e:
            messagebox.showerror("Error", str(e))
            return
        saves = self.adf.list_saves()
        save_names = [e.name for e in saves]
        self.save_combo["values"] = save_names
        if save_names:
            self.save_combo.current(0)
            self._on_save_selected(None)
        self._set_dirty(False)
        self._update_title()
        self._add_recent(path)
        _pref_update(last_save_adf=path)
        self.status_var.set(f"Loaded: {os.path.basename(path)}")

    def _refresh_title_band(self):
        if self.adf_path and self.slot:
            slot_name = self.save_var.get()
            self._title_right.config(
                text=f"{os.path.basename(self.adf_path)}  ·  {slot_name}"
            )
        elif self.adf_path:
            self._title_right.config(text=os.path.basename(self.adf_path))
        else:
            self._title_right.config(text="")

    def _update_title(self):
        if self.adf_path:
            base = f"PMSaveDiskToolkit — {os.path.basename(self.adf_path)}"
            if self.dirty:
                base += " •"
        else:
            base = f"PMSaveDiskToolkit — {__version__}"
        self.root.title(base)
        self._refresh_title_band()

    def _set_dirty(self, flag: bool = True):
        if self.dirty != flag:
            self.dirty = flag
            self._update_title()

    def _on_quit(self):
        if self.dirty:
            answer = messagebox.askyesnocancel(
                "Unsaved changes",
                "You have unsaved changes to the ADF.\n\nSave before quitting?",
            )
            if answer is None:
                return  # Cancel — stay open
            if answer:
                self._save_adf()
                if self.dirty:
                    return  # Save failed; stay open
        self.root.quit()

    def _set_view(self, label: str):
        """Switch the Team dropdown (and list) to the named view."""
        if not self.slot:
            return
        values = self.team_combo["values"]
        if label not in values:
            return
        self.team_var.set(label)
        self._refresh_player_list()

    def _revert_player(self):
        """Reload the detail panel from the current in-memory record."""
        if not self.current_player:
            return
        self._populate_fields(self.current_player)
        self.status_var.set(f"Reverted Player #{self.current_player.player_id}")

    def _find_player(self):
        """Focus the filter entry so the user can start typing."""
        if hasattr(self, "search_entry"):
            self.search_entry.focus_set()
            self.search_entry.selection_range(0, tk.END)

    def _on_escape(self):
        """Esc: clear the filter if it has focus; otherwise revert the player."""
        try:
            focused = self.root.focus_get()
        except KeyError:
            focused = None
        if focused is getattr(self, "search_entry", None):
            self.search_var.set("")
        else:
            self._revert_player()

    def _export_players(self):
        if not self.slot:
            messagebox.showwarning("Warning", "No save loaded.")
            return
        path = filedialog.asksaveasfilename(
            title="Export Players",
            defaultextension=".csv",
            filetypes=[("CSV", "*.csv"), ("JSON", "*.json")],
        )
        if not path:
            return
        fmt = "json" if path.lower().endswith(".json") else "csv"

        team_sel = self.team_var.get()
        if team_sel == "Free Agents":
            players = self.slot.get_free_agents()
        elif team_sel.startswith("— ") or team_sel.startswith("All"):
            players = [p for p in self.slot.players if p.age > 0]
        elif ":" in team_sel:
            players = self.slot.get_players_by_team(int(team_sel.split(":")[0]))
        else:
            players = [p for p in self.slot.players if p.age > 0]

        rows = [player_to_row(p, self.slot, self.game_disk) for p in players]
        try:
            with open(path, "w", newline="", encoding="utf-8") as out:
                if fmt == "json":
                    json.dump(rows, out, indent=2)
                    out.write("\n")
                elif rows:
                    writer = csv.DictWriter(out, fieldnames=list(rows[0].keys()))
                    writer.writeheader()
                    writer.writerows(rows)
        except OSError as e:
            messagebox.showerror("Error", f"Failed to write: {e}")
            return
        self.status_var.set(
            f"Exported {len(rows)} players to {os.path.basename(path)}"
        )

    def _open_career_tracker(self):
        if not self.adf or not self.slot:
            messagebox.showwarning("Warning", "Open a save disk first.")
            return
        CareerTrackerWindow(self.root, self.adf, self.adf_path, self.game_disk)

    def _open_help_search(self):
        HelpSearchWindow(self.root)

    def _open_byte_workbench(self):
        if not self.slot:
            messagebox.showwarning("Warning", "Open a save disk first.")
            return
        ByteWorkbenchWindow(self.root, self.slot, self.game_disk)

    def _open_lineup_coach(self):
        if not self.slot:
            messagebox.showwarning("Warning", "Open a save disk first.")
            return
        LineupCoachWindow(self.root, self.slot, self.game_disk)

    def _open_compare(self, player=None):
        if not self.slot:
            messagebox.showwarning("Warning", "Open a save disk first.")
            return
        if hasattr(self, "_compare_win") and self._compare_win.winfo_exists():
            self._compare_win.lift()
            if player:
                self._compare_win.set_player_a(player)
        else:
            self._compare_win = PlayerCompareWindow(
                self.root, self.slot, self.game_disk, player_a=player
            )

    def _on_tree_right_click(self, event):
        row = self.tree.identify_row(event.y)
        if not row or row.startswith("squad-") or not self.slot:
            return
        self.tree.selection_set(row)
        try:
            player = self.slot.get_player(int(row))
        except (ValueError, KeyError):
            return

        menu = tk.Menu(self.root, tearoff=0)
        menu.add_command(
            label="Send to Compare…",
            command=lambda: self._open_compare(player),
        )
        menu.add_separator()
        menu.add_command(
            label=f"Copy ID #{player.player_id}",
            command=lambda: (self.root.clipboard_clear(),
                             self.root.clipboard_append(str(player.player_id))),
        )
        try:
            menu.tk_popup(event.x_root, event.y_root)
        finally:
            menu.grab_release()

    def _open_manual(self):
        manual = os.path.join(os.path.dirname(os.path.abspath(__file__)), "MANUAL.md")
        webbrowser.open(f"file://{manual}")

    def _check_for_updates(self):
        """Help → Check for Updates… — synchronous, user-driven path."""
        result = updates.fetch_latest()
        if result is None:
            messagebox.showerror(
                "Check for Updates",
                "Could not reach GitHub. Check your internet connection "
                "and try again.",
                parent=self.root,
            )
            return
        latest, url = result
        self._persist_latest_result(latest, url)
        if updates.is_newer(latest, __version__):
            self._show_update_banner(latest, url)
            if messagebox.askyesno(
                "Update available",
                f"A newer version is available.\n\n"
                f"Current:  {__version__}\n"
                f"Latest:   {latest}\n\n"
                f"Open the release page in your browser?",
                parent=self.root,
            ):
                webbrowser.open(url)
        else:
            self._hide_update_banner()
            messagebox.showinfo(
                "Up to date",
                f"You're running the latest version ({__version__}).",
                parent=self.root,
            )

    # ── Automatic (opt-in, daily) update check ─────────────────

    def _schedule_startup_update_check(self):
        """Run after the main window is mapped — never blocks startup.

        First launch shows a yes/no opt-in; subsequent launches only hit
        the network when the 24 h cache window has elapsed. The actual
        fetch runs in a daemon thread; the result is marshalled back to
        the Tk thread via ``root.after``.
        """
        state = updates.load_state()
        if state.get("opted_in") is None:
            self._prompt_update_optin(state)
            state = updates.load_state()
        if not updates.should_check(state):
            # Still surface a previously-cached update, if any.
            latest = state.get("latest_version") or ""
            if latest and updates.is_newer(latest, __version__):
                self._show_update_banner(latest,
                                         state.get("release_url") or
                                         updates.RELEASES_PAGE_URL)
            return
        import threading
        threading.Thread(target=self._bg_fetch_update,
                         daemon=True).start()

    def _prompt_update_optin(self, state: dict):
        answer = messagebox.askyesno(
            "Check for updates?",
            "Should PMSaveDiskToolkit check GitHub once a day for new "
            "releases?\n\n"
            "It never sends anything about you or your save files — just a "
            "single HTTPS request to the public release feed.\n\n"
            "You can change this any time in Help → Preferences.",
            parent=self.root,
        )
        state["opted_in"] = bool(answer)
        updates.save_state(state)

    def _bg_fetch_update(self):
        result = updates.fetch_latest()
        self.root.after(0, self._apply_bg_update_result, result)

    def _apply_bg_update_result(self, result):
        if result is None:
            return  # silent on network failure; retry next launch
        latest, url = result
        self._persist_latest_result(latest, url)
        if updates.is_newer(latest, __version__):
            self._show_update_banner(latest, url)

    def _persist_latest_result(self, latest: str, url: str):
        import time
        state = updates.load_state()
        state["last_check_at"] = time.time()
        state["latest_version"] = latest
        state["release_url"] = url
        updates.save_state(state)

    # ── Update banner (inline next to the title) ───────────────

    def _show_update_banner(self, latest: str, url: str):
        if not hasattr(self, "_title_banner"):
            return
        self._title_banner.configure(
            text=f"  Update available: v{latest} ▸  "
        )
        self._title_banner.bind(
            "<Button-1>", lambda _e: webbrowser.open(url)
        )
        if not self._title_banner.winfo_ismapped():
            self._title_banner.pack(side=tk.LEFT, padx=(8, 0))

    def _hide_update_banner(self):
        if hasattr(self, "_title_banner") \
                and self._title_banner.winfo_ismapped():
            self._title_banner.pack_forget()

    # ── Preferences ───────────────────────────────────────────

    def _show_preferences(self):
        open_preferences(self.root, XI_ENTRIES)

    def _show_about(self):
        top = tk.Toplevel(self.root)
        top.title("About PMSaveDiskTool")
        top.resizable(False, False)
        top.transient(self.root)

        body = ttk.Frame(top, padding=(24, 20, 24, 16))
        body.pack()

        ttk.Label(body, text="PMSaveDiskToolkit",
                  font=("TkDefaultFont", 14, "bold")).pack(anchor="w")
        ttk.Label(body, text=f"Version {__version__}",
                  foreground=PAL["fg_label"]).pack(anchor="w", pady=(0, 12))
        ttk.Label(
            body, justify=tk.LEFT,
            text=("Cross-platform save-disk editor for Player Manager\n"
                  "(Anco Software, 1990 — Amiga)."),
        ).pack(anchor="w", pady=(0, 12))
        ttk.Label(
            body, justify=tk.LEFT, foreground=PAL["fg_label"],
            text=("Based on PMSaveDiskTool v1.2 by UltimateBinary.\n"
                  "Original game by Dino Dini."),
        ).pack(anchor="w", pady=(0, 12))

        def add_link(text, url):
            lbl = ttk.Label(body, text=text, foreground="#1a56db",
                            cursor="hand2")
            lbl.pack(anchor="w")
            lbl.bind("<Button-1>", lambda e: webbrowser.open(url))

        add_link("GitHub repository", GITHUB_URL)
        add_link("MIT License", LICENSE_URL)

        ttk.Button(body, text="OK", command=top.destroy).pack(
            anchor="e", pady=(16, 0))
        top.bind("<Escape>", lambda e: top.destroy())
        top.grab_set()



def main():
    # Register bundled fonts before any Tk widget is created so they show
    # up in the font family list. Best-effort: silent fallback to system
    # fonts if registration fails.
    fonts.register_bundled_fonts()

    prefs = preferences.load()
    set_use_system_font(prefs["use_system_font"])
    set_theme(prefs.get("theme", "retro"))

    root = tk.Tk()
    root.withdraw()          # hide while splash shows
    if prefs["show_splash"]:
        show_splash(root)
    else:
        root.deiconify()
    apply_theme(root)        # theme before main window builds
    app = PMSaveDiskToolGUI(root)

    # Auto-open remembered paths. Silent on missing-file — the user can
    # always open manually. Game disk loads after the save so the roster
    # refresh triggered by _load_game_adf_path picks up real names.
    if prefs["auto_open_last_save"] and os.path.isfile(prefs["last_save_adf"]):
        root.after(0, lambda p=prefs["last_save_adf"]: app._open_adf_path(p))
    if prefs["auto_open_last_game"] and os.path.isfile(prefs["last_game_adf"]):
        root.after(50, lambda p=prefs["last_game_adf"]: app._load_game_adf_path(p))

    if prefs["show_welcome"]:
        root.after(100, lambda: WelcomeDialog(
            root,
            on_dismiss=lambda keep: _pref_update(show_welcome=keep),
        ))

    root.mainloop()


if __name__ == "__main__":
    main()
