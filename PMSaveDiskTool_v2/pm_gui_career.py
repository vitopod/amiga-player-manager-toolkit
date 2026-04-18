"""Career Tracker window — diffs two save slots side by side."""

import os
import tkinter as tk
from tkinter import ttk, filedialog, messagebox

from pm_core.adf import ADF
from pm_core.save import SaveSlot

from pm_gui_theme import PAL


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

        self.adf_b_label = ttk.Label(ctrls, text="(same ADF)", foreground=PAL["fg_dim"])
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
        self.adf_b_label.config(text="(same ADF)", foreground=PAL["fg_dim"])
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
