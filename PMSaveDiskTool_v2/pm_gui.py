#!/usr/bin/env python3
"""Cross-platform tkinter GUI for PMSaveDiskTool v2.

Mirrors the workflow of the original Windows PMSaveDiskTool:
Open ADF -> Select save slot -> Browse players by team -> Edit attributes -> Save.
"""

import os
import sys
import tkinter as tk
from tkinter import ttk, filedialog, messagebox

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from pm_core import __version__
from pm_core.adf import ADF
from pm_core.save import SaveSlot
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


class PMSaveDiskToolGUI:
    def __init__(self, root):
        self.root = root
        self.root.title(f"PMSaveDiskTool v2 — {__version__}")
        self.root.geometry("1100x700")
        self.root.minsize(900, 600)

        self.adf = None
        self.slot = None
        self.current_player = None
        self.adf_path = None
        self.game_disk = None   # GameDisk for name generation (optional)

        self._build_menu()
        self._build_toolbar()
        self._build_main()
        self._build_status_bar()

    # ── Menu ──────────────────────────────────────────────────

    def _build_menu(self):
        menubar = tk.Menu(self.root)
        file_menu = tk.Menu(menubar, tearoff=0)
        file_menu.add_command(label="Open Save Disk ADF...", command=self._open_adf, accelerator="Ctrl+O")
        file_menu.add_command(label="Open Game ADF (for names)...", command=self._open_game_adf, accelerator="Ctrl+G")
        file_menu.add_command(label="Save ADF", command=self._save_adf, accelerator="Ctrl+S")
        file_menu.add_command(label="Save ADF As...", command=self._save_adf_as)
        file_menu.add_separator()
        file_menu.add_command(label="Quit", command=self.root.quit, accelerator="Ctrl+Q")
        menubar.add_cascade(label="File", menu=file_menu)

        help_menu = tk.Menu(menubar, tearoff=0)
        help_menu.add_command(label="About", command=self._show_about)
        menubar.add_cascade(label="Help", menu=help_menu)

        self.root.config(menu=menubar)
        self.root.bind("<Control-o>", lambda e: self._open_adf())
        self.root.bind("<Control-g>", lambda e: self._open_game_adf())
        self.root.bind("<Control-s>", lambda e: self._save_adf())

    # ── Toolbar ───────────────────────────────────────────────

    def _build_toolbar(self):
        toolbar = ttk.Frame(self.root)
        toolbar.pack(fill=tk.X, padx=5, pady=(5, 0))

        ttk.Button(toolbar, text="Open Save Disk", command=self._open_adf).pack(side=tk.LEFT, padx=2)
        ttk.Button(toolbar, text="Load Game ADF (names)", command=self._open_game_adf).pack(side=tk.LEFT, padx=2)
        self.game_label = ttk.Label(toolbar, text="No game ADF", foreground="gray")
        self.game_label.pack(side=tk.LEFT, padx=(4, 10))

        ttk.Label(toolbar, text="Save:").pack(side=tk.LEFT, padx=(10, 2))
        self.save_var = tk.StringVar()
        self.save_combo = ttk.Combobox(toolbar, textvariable=self.save_var,
                                       state="readonly", width=12)
        self.save_combo.pack(side=tk.LEFT, padx=2)
        self.save_combo.bind("<<ComboboxSelected>>", self._on_save_selected)

        ttk.Label(toolbar, text="Team:").pack(side=tk.LEFT, padx=(10, 2))
        self.team_var = tk.StringVar()
        self.team_combo = ttk.Combobox(toolbar, textvariable=self.team_var,
                                       state="readonly", width=20)
        self.team_combo.pack(side=tk.LEFT, padx=2)
        self.team_combo.bind("<<ComboboxSelected>>", self._on_team_selected)

        ttk.Button(toolbar, text="Save Changes", command=self._save_adf).pack(
            side=tk.RIGHT, padx=2)

    # ── Main area ─────────────────────────────────────────────

    def _build_main(self):
        paned = ttk.PanedWindow(self.root, orient=tk.HORIZONTAL)
        paned.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

        # Left: Player list
        left = ttk.Frame(paned)
        paned.add(left, weight=1)

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

        # Right: Player detail
        right = ttk.Frame(paned)
        paned.add(right, weight=1)

        canvas = tk.Canvas(right)
        detail_scroll = ttk.Scrollbar(right, orient=tk.VERTICAL, command=canvas.yview)
        self.detail_frame = ttk.Frame(canvas)
        self.detail_frame.bind("<Configure>",
                               lambda e: canvas.configure(scrollregion=canvas.bbox("all")))
        canvas.create_window((0, 0), window=self.detail_frame, anchor="nw")
        canvas.configure(yscrollcommand=detail_scroll.set)
        canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        detail_scroll.pack(side=tk.RIGHT, fill=tk.Y)

        self.fields = {}
        self._build_detail_fields()

    def _build_detail_fields(self):
        frame = self.detail_frame
        row = 0

        def add_field(label, key, row_num, readonly=False):
            ttk.Label(frame, text=label).grid(row=row_num, column=0, sticky="e", padx=(5, 2), pady=1)
            var = tk.StringVar()
            state = "readonly" if readonly else "normal"
            entry = ttk.Entry(frame, textvariable=var, width=12, state=state)
            entry.grid(row=row_num, column=1, sticky="w", padx=(2, 5), pady=1)
            self.fields[key] = var
            return row_num + 1

        def add_section(title, row_num):
            ttk.Separator(frame, orient="horizontal").grid(
                row=row_num, column=0, columnspan=2, sticky="ew", pady=(8, 2))
            ttk.Label(frame, text=title, font=("TkDefaultFont", 0, "bold")).grid(
                row=row_num + 1, column=0, columnspan=2, sticky="w", padx=5)
            return row_num + 2

        row = add_field("Player ID:", "player_id", row, readonly=True)
        row = add_field("Name:", "name", row, readonly=True)
        row = add_field("RNG Seed:", "rng_seed", row, readonly=True)

        row = add_section("Core", row)
        row = add_field("Age:", "age", row)
        row = add_field("Position:", "position", row)
        row = add_field("Division:", "division", row)
        row = add_field("Team Index:", "team_index", row)
        row = add_field("Height (cm):", "height", row)
        row = add_field("Weight (kg):", "weight", row)

        row = add_section("Skills (0-200)", row)
        for skill in SKILL_NAMES:
            row = add_field(f"{skill.capitalize()}:", skill, row)

        row = add_section("Status", row)
        row = add_field("Injury Weeks:", "injury_weeks", row)
        row = add_field("Disciplinary:", "disciplinary", row)
        row = add_field("Morale:", "morale", row)
        row = add_field("Value:", "value", row)
        row = add_field("Wks Since Transfer:", "weeks_since_transfer", row)

        row = add_section("Season Stats", row)
        row = add_field("Injuries This Yr:", "injuries_this_year", row)
        row = add_field("Injuries Last Yr:", "injuries_last_year", row)
        row = add_field("DspPts This Yr:", "dsp_pts_this_year", row)
        row = add_field("DspPts Last Yr:", "dsp_pts_last_year", row)
        row = add_field("Goals This Yr:", "goals_this_year", row)
        row = add_field("Goals Last Yr:", "goals_last_year", row)
        row = add_field("Matches This Yr:", "matches_this_year", row)
        row = add_field("Matches Last Yr:", "matches_last_year", row)

        row = add_section("Career", row)
        row = add_field("Div1 Years:", "div1_years", row)
        row = add_field("Div2 Years:", "div2_years", row)
        row = add_field("Div3 Years:", "div3_years", row)
        row = add_field("Div4 Years:", "div4_years", row)
        row = add_field("Int Years:", "int_years", row)
        row = add_field("Contract Yrs:", "contract_years", row)

        ttk.Button(frame, text="Apply Changes", command=self._apply_changes).grid(
            row=row, column=0, columnspan=2, pady=10)

    # ── Status bar ────────────────────────────────────────────

    def _build_status_bar(self):
        self.status_var = tk.StringVar(value="Open an ADF file to begin.")
        status = ttk.Label(self.root, textvariable=self.status_var, relief=tk.SUNKEN)
        status.pack(fill=tk.X, side=tk.BOTTOM, padx=5, pady=2)

    # ── Actions ───────────────────────────────────────────────

    def _open_adf(self):
        path = filedialog.askopenfilename(
            title="Open Player Manager Save Disk",
            filetypes=[("ADF Disk Images", "*.adf"), ("All Files", "*.*")],
        )
        if not path:
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
        self.status_var.set(f"Loaded: {os.path.basename(path)}")

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
        team_options.extend(XI_ENTRIES.keys())
        self.team_combo["values"] = team_options
        self.team_combo.current(0)
        self._refresh_player_list()
        self.status_var.set(f"Loaded save: {save_name}")

    def _on_team_selected(self, event):
        self._refresh_player_list()

    def _refresh_player_list(self):
        if not self.slot:
            return
        self.tree.delete(*self.tree.get_children())

        team_sel = self.team_var.get()
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

        for p in players:
            team = self.slot.get_team_name(p.team_index)
            name = (self.game_disk.player_full_name(p.rng_seed)
                    if self.game_disk and p.rng_seed else "")
            mkt = "★" if p.is_market_available else ""
            self.tree.insert("", "end", iid=str(p.player_id),
                             values=(p.player_id, name, p.age, p.position_name,
                                     team, score_fn(p), mkt))

    def _on_player_selected(self, event):
        sel = self.tree.selection()
        if not sel or not self.slot:
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
            self.adf.save(self.adf_path)
            self.status_var.set(f"Saved: {os.path.basename(self.adf_path)}")
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
        except OSError as e:
            messagebox.showerror("Error", f"Failed to save: {e}")

    def _show_about(self):
        messagebox.showinfo(
            "About PMSaveDiskTool v2",
            f"PMSaveDiskTool v2 — {__version__}\n"
            "Cross-platform Player Manager Save Disk Editor\n\n"
            "Compatible with the original PMSaveDiskTool by UltimateBinary.\n"
            "Supports Player Manager (Amiga, 1990).\n\n"
            "Works on Mac, Linux, and Windows."
        )


def main():
    root = tk.Tk()
    app = PMSaveDiskToolGUI(root)
    root.mainloop()


if __name__ == "__main__":
    main()
