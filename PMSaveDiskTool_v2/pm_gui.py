#!/usr/bin/env python3
"""Cross-platform tkinter GUI for PMSaveDiskTool v2.

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
from pm_core.player import SKILL_NAMES, POSITION_NAMES, PlayerRecord
from pm_core.names import GameDisk


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


class CareerTrackerWindow(tk.Toplevel):
    """Modal-ish window that diffs two save slots and shows changed players.

    Slot B may live on the same ADF as slot A or on a second ADF selected
    via 'Load side-B ADF'. Output columns mirror the CLI career-tracker.
    """

    def __init__(self, parent, adf_a, adf_a_path, game_disk):
        super().__init__(parent)
        self.title("Career Tracker")
        self.geometry("900x520")
        self.minsize(700, 400)

        self.adf_a = adf_a
        self.adf_a_path = adf_a_path
        self.adf_b = adf_a  # default: same ADF
        self.adf_b_path = adf_a_path
        self.game_disk = game_disk

        ctrls = ttk.Frame(self)
        ctrls.pack(fill=tk.X, padx=6, pady=6)

        save_names = [e.name for e in adf_a.list_saves()]
        ttk.Label(ctrls, text="Slot A:").pack(side=tk.LEFT, padx=(0, 2))
        self.save_a_var = tk.StringVar(value=save_names[0] if save_names else "")
        ttk.Combobox(ctrls, textvariable=self.save_a_var, values=save_names,
                     state="readonly", width=10).pack(side=tk.LEFT, padx=2)

        ttk.Label(ctrls, text="Slot B:").pack(side=tk.LEFT, padx=(10, 2))
        self.save_b_var = tk.StringVar(
            value=save_names[1] if len(save_names) > 1 else (save_names[0] if save_names else "")
        )
        self.save_b_combo = ttk.Combobox(ctrls, textvariable=self.save_b_var,
                                         values=save_names, state="readonly", width=10)
        self.save_b_combo.pack(side=tk.LEFT, padx=2)

        self.adf_b_label = ttk.Label(ctrls, text="(same ADF)", foreground="gray")
        self.adf_b_label.pack(side=tk.LEFT, padx=(10, 4))
        ttk.Button(ctrls, text="Load side-B ADF...",
                   command=self._load_adf_b).pack(side=tk.LEFT, padx=2)
        ttk.Button(ctrls, text="Reset to same ADF",
                   command=self._reset_adf_b).pack(side=tk.LEFT, padx=2)

        self.team_changes_var = tk.BooleanVar(value=False)
        ttk.Checkbutton(ctrls, text="Team changes only",
                        variable=self.team_changes_var).pack(side=tk.LEFT, padx=(10, 2))

        ttk.Button(ctrls, text="Compare", command=self._compare).pack(
            side=tk.RIGHT, padx=2)

        cols = ("id", "name", "age_a", "age_b", "skill_a", "skill_b",
                "delta", "team_a", "team_b")
        self.tree = ttk.Treeview(self, columns=cols, show="headings")
        for c, text, w, anc in [
            ("id", "ID", 50, "e"),
            ("name", "Name", 140, "w"),
            ("age_a", "Age A", 55, "e"),
            ("age_b", "Age B", 55, "e"),
            ("skill_a", "Skill A", 65, "e"),
            ("skill_b", "Skill B", 65, "e"),
            ("delta", "ΔSkill", 55, "e"),
            ("team_a", "Team A", 130, "w"),
            ("team_b", "Team B", 130, "w"),
        ]:
            self.tree.heading(c, text=text)
            self.tree.column(c, width=w, anchor=anc)
        scrollbar = ttk.Scrollbar(self, orient=tk.VERTICAL,
                                  command=self.tree.yview)
        self.tree.configure(yscrollcommand=scrollbar.set)
        self.tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(6, 0), pady=(0, 6))
        scrollbar.pack(side=tk.LEFT, fill=tk.Y, padx=(0, 6), pady=(0, 6))

        self.status_var = tk.StringVar(value="Ready.")
        ttk.Label(self, textvariable=self.status_var, relief=tk.SUNKEN).pack(
            fill=tk.X, side=tk.BOTTOM)

    def _load_adf_b(self):
        path = filedialog.askopenfilename(
            parent=self, title="Open Side-B ADF",
            filetypes=[("ADF Disk Images", "*.adf"), ("All Files", "*.*")],
        )
        if not path:
            return
        try:
            self.adf_b = ADF.load(path)
        except (ValueError, OSError) as e:
            messagebox.showerror("Error", str(e), parent=self)
            return
        self.adf_b_path = path
        self.adf_b_label.config(text=os.path.basename(path), foreground="black")
        self.save_b_combo["values"] = [e.name for e in self.adf_b.list_saves()]

    def _reset_adf_b(self):
        self.adf_b = self.adf_a
        self.adf_b_path = self.adf_a_path
        self.adf_b_label.config(text="(same ADF)", foreground="gray")
        self.save_b_combo["values"] = [e.name for e in self.adf_a.list_saves()]

    def _compare(self):
        if not self.save_a_var.get() or not self.save_b_var.get():
            return
        try:
            slot_a = SaveSlot(self.adf_a, self.save_a_var.get())
            slot_b = SaveSlot(self.adf_b, self.save_b_var.get())
        except Exception as e:
            messagebox.showerror("Error", f"Failed to load slots: {e}", parent=self)
            return

        diffs = slot_a.diff_players(slot_b)
        if self.team_changes_var.get():
            diffs = [d for d in diffs if d["team_changed"]]
        diffs.sort(key=lambda d: d["skill_delta"], reverse=True)

        self.tree.delete(*self.tree.get_children())
        for d in diffs:
            a, b = d["old"], d["new"]
            name = (self.game_disk.player_full_name(a.rng_seed)
                    if self.game_disk and a.rng_seed else "")
            self.tree.insert("", "end", values=(
                d["player_id"], name, a.age, b.age,
                a.total_skill, b.total_skill,
                f"{d['skill_delta']:+d}",
                slot_a.get_team_name(a.team_index),
                slot_b.get_team_name(b.team_index),
            ))
        self.status_var.set(
            f"{len(diffs)} players changed "
            f"({self.save_a_var.get()} -> {self.save_b_var.get()})"
        )


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

        self._build_menu()
        self._build_toolbar()
        self._build_main()
        self._build_status_bar()
        self._update_title()

        self.root.protocol("WM_DELETE_WINDOW", self._on_quit)
        if sys.platform == "darwin":
            self.root.createcommand("tk::mac::Quit", self._on_quit)

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
        menubar.add_cascade(label="Tools", menu=tools_menu)

        # Help
        help_menu = tk.Menu(menubar, tearoff=0)
        if not is_mac:
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
        bind(f"<{MOD}-y>", lambda e: self._set_view("— Young Talents (≤21)"))
        bind(f"<{MOD}-Return>", lambda e: self._apply_changes())
        bind("<Escape>", lambda e: self._on_escape())
        if not is_mac:
            bind(f"<{MOD}-q>", lambda e: self._on_quit())

    # ── Toolbar ───────────────────────────────────────────────

    def _build_toolbar(self):
        toolbar = ttk.Frame(self.root)
        toolbar.pack(fill=tk.X, padx=5, pady=(5, 0))

        ttk.Label(toolbar, text="Save:").pack(side=tk.LEFT, padx=(2, 2))
        self.save_var = tk.StringVar()
        self.save_combo = ttk.Combobox(toolbar, textvariable=self.save_var,
                                       state="readonly", width=12)
        self.save_combo.pack(side=tk.LEFT, padx=2)
        self.save_combo.bind("<<ComboboxSelected>>", self._on_save_selected)

        ttk.Label(toolbar, text="View:").pack(side=tk.LEFT, padx=(14, 2))
        self.team_var = tk.StringVar()
        self.team_combo = ttk.Combobox(toolbar, textvariable=self.team_var,
                                       state="readonly", width=28)
        self.team_combo.pack(side=tk.LEFT, padx=2)
        self.team_combo.bind("<<ComboboxSelected>>", self._on_team_selected)

    # ── Main area ─────────────────────────────────────────────

    def _build_main(self):
        paned = ttk.PanedWindow(self.root, orient=tk.HORIZONTAL)
        paned.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

        # Left: Player list
        left = ttk.Frame(paned)
        paned.add(left, weight=1)

        self.summary_var = tk.StringVar(value="")
        self.summary_label = ttk.Label(left, textvariable=self.summary_var,
                                       anchor="w", foreground="gray30")
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

        # Right: header (identity) + notebook (editable fields) + sticky footer (Apply)
        right = ttk.Frame(paned)
        paned.add(right, weight=1)

        self.detail_header = ttk.Frame(right)
        self.detail_header.pack(fill=tk.X, padx=6, pady=(6, 2))

        self.notebook = ttk.Notebook(right)
        self.notebook.pack(fill=tk.BOTH, expand=True, padx=4, pady=4)

        footer = ttk.Frame(right)
        footer.pack(fill=tk.X, side=tk.BOTTOM, padx=6, pady=(0, 6))
        ttk.Separator(footer, orient="horizontal").pack(fill=tk.X, pady=(0, 4))
        self.apply_button = ttk.Button(footer, text="Apply Changes",
                                       command=self._apply_changes)
        self.apply_button.pack(side=tk.RIGHT)
        ttk.Button(footer, text="Revert",
                   command=self._revert_player).pack(side=tk.RIGHT, padx=(0, 6))

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
        ("DspPts This Yr:", "dsp_pts_this_year"),
        ("DspPts Last Yr:", "dsp_pts_last_year"),
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
            ttk.Label(self.detail_header, text=label, anchor="e").grid(
                row=0, column=i * 2, sticky="e", padx=(0, 3))
            var = tk.StringVar()
            entry = ttk.Entry(self.detail_header, textvariable=var,
                              state="readonly", width=14)
            entry.grid(row=0, column=i * 2 + 1, sticky="w", padx=(0, 10))
            self.fields[key] = var

        def add_field(parent, label, key, row):
            ttk.Label(parent, text=label).grid(
                row=row, column=0, sticky="e", padx=(6, 3), pady=2)
            var = tk.StringVar()
            ttk.Entry(parent, textvariable=var, width=12).grid(
                row=row, column=1, sticky="w", padx=(3, 6), pady=2)
            self.fields[key] = var

        def add_tab(title, fields):
            tab = ttk.Frame(self.notebook)
            self.notebook.add(tab, text=title)
            for r, (label, key) in enumerate(fields):
                add_field(tab, label, key, r)
            return tab

        add_tab("Core", self._CORE_FIELDS)

        # Skills tab: two columns so all 10 fit without scrolling.
        skills_tab = ttk.Frame(self.notebook)
        self.notebook.add(skills_tab, text="Skills")
        half = (len(SKILL_NAMES) + 1) // 2
        for i, skill in enumerate(SKILL_NAMES):
            col_block, row = (0, i) if i < half else (2, i - half)
            ttk.Label(skills_tab, text=f"{skill.capitalize()}:").grid(
                row=row, column=col_block, sticky="e", padx=(6, 3), pady=2)
            var = tk.StringVar()
            ttk.Entry(skills_tab, textvariable=var, width=8).grid(
                row=row, column=col_block + 1, sticky="w", padx=(3, 16), pady=2)
            self.fields[skill] = var

        add_tab("Status", self._STATUS_FIELDS)
        add_tab("Season", self._SEASON_FIELDS)
        add_tab("Career", self._CAREER_FIELDS)

    # ── Status bar ────────────────────────────────────────────

    def _build_status_bar(self):
        bar = ttk.Frame(self.root, relief=tk.SUNKEN, borderwidth=1)
        bar.pack(fill=tk.X, side=tk.BOTTOM, padx=5, pady=2)

        self.status_var = tk.StringVar(value="Open a save disk to begin.")
        ttk.Label(bar, textvariable=self.status_var,
                  anchor="w").pack(side=tk.LEFT, fill=tk.X, expand=True, padx=4)

        self.game_label = ttk.Label(bar, text="No game disk",
                                    foreground="gray", anchor="e")
        self.game_label.pack(side=tk.RIGHT, padx=4)

    # ── Actions ───────────────────────────────────────────────

    def _open_adf(self):
        path = filedialog.askopenfilename(
            title="Open Player Manager Save Disk",
            filetypes=[("ADF Disk Images", "*.adf"), ("All Files", "*.*")],
        )
        if path:
            self._open_adf_path(path)

    def _open_game_adf(self):
        path = filedialog.askopenfilename(
            title="Open Player Manager Game Disk",
            filetypes=[("ADF Disk Images", "*.adf"), ("All Files", "*.*")],
        )
        if not path:
            return
        try:
            self.game_disk = GameDisk.load(path)
            self.game_label.config(
                text=f"{os.path.basename(path)} ({self.game_disk.surname_count} names)",
                foreground="green",
            )
            self.status_var.set(
                f"Game ADF loaded: {self.game_disk.surname_count} Italian surnames available"
            )
        except Exception as e:
            messagebox.showerror("Error", f"Failed to load game ADF:\n{e}")
            return
        # Refresh list if a save is already open
        if self.slot:
            self._refresh_player_list()

    def _on_save_selected(self, event):
        save_name = self.save_var.get()
        if not save_name or not self.adf:
            return
        try:
            self.slot = SaveSlot(self.adf, save_name)
        except Exception as e:
            messagebox.showerror("Error", f"Failed to load save: {e}")
            return

        # Populate team filter
        team_options = ["All Players", "Free Agents"]
        for i, name in enumerate(self.slot.team_names):
            team_options.append(f"{i}: {name}")
        team_options.append("— Young Talents (≤21)")
        team_options.append("— Top Scorers")
        team_options.append("— Squad Analyst (all teams)")
        team_options.extend(XI_ENTRIES.keys())
        self.team_combo["values"] = team_options
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
            self.tree.insert("", "end", iid=str(p.player_id),
                             values=(p.player_id, name, p.age, p.position_name,
                                     team, score_fn(p), mkt))

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
        self.status_var.set(f"Loaded: {os.path.basename(path)}")

    def _update_title(self):
        if self.adf_path:
            base = f"PMSaveDiskTool v2 — {os.path.basename(self.adf_path)}"
            if self.dirty:
                base += " •"
        else:
            base = f"PMSaveDiskTool v2 — {__version__}"
        self.root.title(base)

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

    def _show_about(self):
        top = tk.Toplevel(self.root)
        top.title("About PMSaveDiskTool")
        top.resizable(False, False)
        top.transient(self.root)

        body = ttk.Frame(top, padding=(24, 20, 24, 16))
        body.pack()

        ttk.Label(body, text="PMSaveDiskTool v2",
                  font=("TkDefaultFont", 14, "bold")).pack(anchor="w")
        ttk.Label(body, text=f"Version {__version__}",
                  foreground="gray30").pack(anchor="w", pady=(0, 12))
        ttk.Label(
            body, justify=tk.LEFT,
            text=("Cross-platform save-disk editor for Player Manager\n"
                  "(Anco Software, 1990 — Amiga)."),
        ).pack(anchor="w", pady=(0, 12))
        ttk.Label(
            body, justify=tk.LEFT, foreground="gray30",
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
    root = tk.Tk()
    app = PMSaveDiskToolGUI(root)
    root.mainloop()


if __name__ == "__main__":
    main()
