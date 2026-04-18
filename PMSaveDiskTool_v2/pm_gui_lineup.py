"""Line-up Coach (BETA) — suggested XI + reassignments window."""

import tkinter as tk
from tkinter import ttk

from pm_core import lineup, preferences
from pm_core.save import SaveSlot

from pm_gui_theme import PAL
from pm_gui_help import help_button


class LineupCoachWindow(tk.Toplevel):
    """Line-up Coach (BETA).

    Suggests formation + XI + per-player role reassignments from a pool
    (one team or the whole championship). Scoring is a heuristic layered
    on PM's 10 skill fields, not a reconstruction of the match engine —
    the output is labelled BETA throughout.
    """

    BETA_DISCLAIMER = (
        "BETA — scoring is a football-management heuristic built on top of PM's "
        "skill fields. PM's match-engine weights are not reverse-engineered; "
        "treat output as 'suggested,' not 'optimal.'"
    )

    def __init__(self, parent, slot: SaveSlot, game_disk=None):
        super().__init__(parent)
        self.title("Line-up Coach (BETA)")
        self.geometry("940x620")
        self.minsize(820, 520)

        self.slot = slot
        self.game_disk = game_disk

        header = ttk.Frame(self, padding=(8, 8, 8, 4))
        header.pack(fill=tk.X)
        ttk.Label(header, text="Line-up Coach",
                  font=("TkDefaultFont", 13, "bold")).pack(side=tk.LEFT)
        ttk.Label(header, text="  BETA",
                  foreground="#c2410c",
                  font=("TkDefaultFont", 10, "bold")).pack(side=tk.LEFT)
        help_button(header, "lineup_coach").pack(side=tk.RIGHT)

        disclaimer = ttk.Label(self, text=self.BETA_DISCLAIMER,
                               foreground=PAL["fg_label"], wraplength=900,
                               justify=tk.LEFT)
        disclaimer.pack(fill=tk.X, padx=10, pady=(0, 6))

        ctrl = ttk.Frame(self, padding=(8, 4))
        ctrl.pack(fill=tk.X)

        ttk.Label(ctrl, text="Team:").pack(side=tk.LEFT)
        self.team_var = tk.StringVar(value="— Whole championship")
        team_choices = ["— Whole championship"] + [
            f"{i:>3}  {slot.get_team_name(i)}" for i in range(len(slot.team_names))
        ]
        self.team_cb = ttk.Combobox(ctrl, textvariable=self.team_var,
                                    values=team_choices, state="readonly",
                                    width=26)
        self.team_cb.pack(side=tk.LEFT, padx=(4, 10))

        ttk.Label(ctrl, text="Formation:").pack(side=tk.LEFT)
        pref_fmt = preferences.load().get("default_formation", "4-4-2")
        if pref_fmt not in lineup.FORMATION_ROLES:
            pref_fmt = "— Rank all"
        self.formation_var = tk.StringVar(value=pref_fmt)
        self.formation_cb = ttk.Combobox(
            ctrl, textvariable=self.formation_var,
            values=["— Rank all"] + list(lineup.FORMATION_ROLES),
            state="readonly", width=12,
        )
        self.formation_cb.pack(side=tk.LEFT, padx=(4, 10))

        self.cross_pos_var = tk.BooleanVar(value=False)
        ttk.Checkbutton(ctrl, text="Allow cross-position",
                        variable=self.cross_pos_var).pack(side=tk.LEFT, padx=6)

        self.include_injured_var = tk.BooleanVar(value=False)
        ttk.Checkbutton(ctrl, text="Include injured",
                        variable=self.include_injured_var).pack(side=tk.LEFT, padx=6)

        ttk.Button(ctrl, text="Compute",
                   command=self._compute).pack(side=tk.LEFT, padx=(16, 4))

        body = ttk.PanedWindow(self, orient=tk.HORIZONTAL)
        body.pack(fill=tk.BOTH, expand=True, padx=8, pady=6)

        # Left: formation ranking
        left = ttk.Frame(body)
        body.add(left, weight=1)
        ttk.Label(left, text="Formation ranking",
                  font=("TkDefaultFont", 10, "bold")).pack(anchor="w")
        self.rank_tree = ttk.Treeview(
            left, show="headings",
            columns=("form", "comp", "skill", "fit"),
            height=5,
        )
        for c, txt, w, anc in [
            ("form", "Formation", 80, tk.W),
            ("comp", "Composite", 90, tk.E),
            ("skill", "Skill", 70, tk.E),
            ("fit", "Fit%", 60, tk.E),
        ]:
            self.rank_tree.heading(c, text=txt)
            self.rank_tree.column(c, width=w, anchor=anc)
        self.rank_tree.pack(fill=tk.BOTH, expand=True, pady=(2, 6))
        self.rank_tree.bind("<<TreeviewSelect>>", self._on_rank_select)

        ttk.Label(left, text="Reassignment suggestions",
                  font=("TkDefaultFont", 10, "bold")).pack(anchor="w")
        self.reassign_tree = ttk.Treeview(
            left, show="headings",
            columns=("id", "nominal", "suggested", "gap"),
            height=10,
        )
        for c, txt, w, anc in [
            ("id", "Player", 140, tk.W),
            ("nominal", "Nominal", 80, tk.W),
            ("suggested", "Suggested", 80, tk.W),
            ("gap", "Gap", 70, tk.E),
        ]:
            self.reassign_tree.heading(c, text=txt)
            self.reassign_tree.column(c, width=w, anchor=anc)
        self.reassign_tree.pack(fill=tk.BOTH, expand=True, pady=(2, 0))

        # Right: recommended XI
        right = ttk.Frame(body)
        body.add(right, weight=2)
        self.summary_var = tk.StringVar(
            value="Click Compute to generate a suggested XI."
        )
        ttk.Label(right, textvariable=self.summary_var,
                  font=("TkDefaultFont", 10, "bold")).pack(anchor="w")
        self.xi_tree = ttk.Treeview(
            right, show="headings",
            columns=("role", "pid", "name", "age", "team", "skill", "fit"),
        )
        for c, txt, w, anc in [
            ("role", "Role", 55, tk.W),
            ("pid", "ID", 55, tk.E),
            ("name", "Name", 150, tk.W),
            ("age", "Age", 45, tk.E),
            ("team", "Team", 140, tk.W),
            ("skill", "Skill", 60, tk.E),
            ("fit", "Fit%", 55, tk.E),
        ]:
            self.xi_tree.heading(c, text=txt)
            self.xi_tree.column(c, width=w, anchor=anc)
        sb = ttk.Scrollbar(right, orient=tk.VERTICAL, command=self.xi_tree.yview)
        self.xi_tree.configure(yscrollcommand=sb.set)
        self.xi_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, pady=(2, 0))
        sb.pack(side=tk.LEFT, fill=tk.Y, pady=(2, 0))

        self.breakdown_var = tk.StringVar(value="")
        ttk.Label(self, textvariable=self.breakdown_var,
                  foreground=PAL["fg_label"], wraplength=900,
                  justify=tk.LEFT).pack(fill=tk.X, padx=10, pady=(2, 8))

        self._current_ranked: list[lineup.LineupResult] = []
        self._current_pool: list = []
        self._current_allow_cross: bool = False
        self._current_eligibility = lineup._is_eligible

    def _compute(self):
        team_label = self.team_var.get()
        if team_label.startswith("—"):
            pool = [p for p in self.slot.players
                    if SaveSlot._is_real_player(p)]
            pool_label = "whole championship"
        else:
            team_index = int(team_label.split()[0])
            pool = self.slot.get_players_by_team(team_index)
            pool_label = f"team {team_index} — {self.slot.get_team_name(team_index)}"

        formation_choice = self.formation_var.get()
        formations = (None if formation_choice.startswith("—")
                      else [formation_choice])
        include_injured = self.include_injured_var.get()
        allow_cross = self.cross_pos_var.get()

        eligibility = lineup._is_eligible
        if include_injured:
            eligibility = lambda p: (p.position in (1, 2, 3, 4) and p.age > 0)

        ranked: list[lineup.LineupResult] = []
        fmt_keys = formations if formations else list(lineup.FORMATION_ROLES)
        for f in fmt_keys:
            try:
                xi = lineup.assemble_xi(pool, f,
                                        allow_cross_position=allow_cross,
                                        eligibility=eligibility)
            except ValueError:
                continue
            comp, br = lineup.score_xi(xi)
            ranked.append(lineup.LineupResult(
                formation=f, assignments=xi, composite=comp, breakdown=br,
            ))
        ranked.sort(key=lambda r: r.composite, reverse=True)
        self._current_ranked = ranked
        self._current_pool = pool
        self._current_allow_cross = allow_cross
        self._current_eligibility = eligibility

        self.rank_tree.delete(*self.rank_tree.get_children())
        self.xi_tree.delete(*self.xi_tree.get_children())
        self.reassign_tree.delete(*self.reassign_tree.get_children())
        self.breakdown_var.set("")

        if not ranked:
            self.summary_var.set(
                f"No formation could be filled from {pool_label} "
                f"({len(pool)} players). Try 'Include injured' or "
                f"'Allow cross-position'."
            )
            return

        for r in ranked:
            self.rank_tree.insert(
                "", "end", iid=r.formation,
                values=(r.formation, f"{r.composite:.1f}", r.total_skill,
                        f"{r.breakdown['mean_fit']*100:.1f}"),
            )
        self.rank_tree.selection_set(ranked[0].formation)
        self._show_result(ranked[0], pool_label)

        flags = lineup.suggest_reassignments(pool, threshold=0.15)
        for s in flags[:40]:
            name = (self.game_disk.player_full_name(s.player.rng_seed)
                    if self.game_disk and s.player.rng_seed else "")
            label = f"#{s.player.player_id}" + (f"  {name}" if name else "")
            self.reassign_tree.insert(
                "", "end",
                values=(label, s.nominal_role, s.best_role,
                        f"{s.gap*100:+.0f}%"),
            )

    def _on_rank_select(self, _evt=None):
        sel = self.rank_tree.selection()
        if not sel:
            return
        target = sel[0]
        for r in self._current_ranked:
            if r.formation == target:
                self._show_result(r)
                return

    def _show_result(self, result: "lineup.LineupResult", pool_label=None):
        self.xi_tree.delete(*self.xi_tree.get_children())
        for a in result.assignments:
            team = self.slot.get_team_name(a.player.team_index)
            name = (self.game_disk.player_full_name(a.player.rng_seed)
                    if self.game_disk and a.player.rng_seed else "")
            self.xi_tree.insert("", "end", values=(
                a.role, a.player.player_id, name,
                a.player.age, team, a.player.total_skill,
                f"{a.fit*100:.1f}",
            ))

        reserves: list[lineup.RoleAssignment] = []
        if self._current_pool:
            try:
                md = lineup.assemble_matchday_squad(
                    self._current_pool, result.formation, n_reserves=2,
                    allow_cross_position=self._current_allow_cross,
                    eligibility=self._current_eligibility,
                )
                reserves = md.reserves
            except ValueError:
                reserves = []

        if reserves:
            self.xi_tree.insert("", "end",
                                values=("— Reserves —", "", "", "", "", "", ""),
                                tags=("bench_header",))
            for i, a in enumerate(reserves, 1):
                team = self.slot.get_team_name(a.player.team_index)
                name = (self.game_disk.player_full_name(a.player.rng_seed)
                        if self.game_disk and a.player.rng_seed else "")
                self.xi_tree.insert("", "end", values=(
                    f"R{i} {a.role}", a.player.player_id, name,
                    a.player.age, team, a.player.total_skill,
                    f"{a.fit*100:.1f}",
                ), tags=("bench_row",))
        self.xi_tree.tag_configure("bench_header", foreground=PAL["fg_label"])
        self.xi_tree.tag_configure("bench_row", foreground=PAL["player_a"])

        suffix = f" ({pool_label})" if pool_label else ""
        self.summary_var.set(
            f"{result.formation}{suffix}  —  composite {result.composite:.1f}, "
            f"skill {result.total_skill}"
        )
        br = result.breakdown
        self.breakdown_var.set(
            f"Fit {br['mean_fit']*100:.1f}% · "
            f"Morale {br['mean_morale']*100:.1f}% · "
            f"Fatigue {br['mean_fatigue']*100:.1f}% · "
            f"Card risk {br['mean_card_risk']*100:.1f}% · "
            f"Form (FWDs) {br['mean_form']*100:.1f}%"
        )
