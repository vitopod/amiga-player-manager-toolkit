"""Line-up Coach (BETA) -- suggested XI + reassignments window."""

import tkinter as tk
from collections import Counter
from tkinter import ttk

from pm_core import lineup, preferences
from pm_core.save import SaveSlot
from pm_core.strings import t

from pm_gui_theme import PAL
from pm_gui_help import help_button


class LineupCoachWindow(tk.Toplevel):
    """Line-up Coach (BETA).

    Suggests formation + XI + per-player role reassignments from a pool
    (one team or the whole championship). Scoring is a heuristic layered
    on PM's 10 skill fields, not a reconstruction of the match engine --
    the output is labelled BETA throughout.
    """

    BETA_DISCLAIMER = (
        "BETA -- scoring is a football-management heuristic built on top of PM's "
        "skill fields. PM's match-engine weights are not reverse-engineered; "
        "treat output as 'suggested,' not 'optimal.'"
    )

    def __init__(self, parent, slot: SaveSlot, game_disk=None):
        super().__init__(parent)
        self.title(t("lineup.title"))
        self.geometry("940x620")
        self.minsize(820, 520)

        self.slot = slot
        self.game_disk = game_disk

        header = ttk.Frame(self, padding=(8, 8, 8, 4))
        header.pack(fill=tk.X)
        ttk.Label(header, text=t("lineup.header"),
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

        ttk.Label(ctrl, text=t("lineup.team")).pack(side=tk.LEFT)
        self.team_var = tk.StringVar(value=t("lineup.whole_champ"))
        team_choices = [t("lineup.whole_champ")] + [
            f"{i:>3}  {slot.get_team_name(i)}" for i in range(len(slot.team_names))
        ]
        self.team_cb = ttk.Combobox(ctrl, textvariable=self.team_var,
                                    values=team_choices, state="readonly",
                                    width=26)
        self.team_cb.pack(side=tk.LEFT, padx=(4, 10))

        ttk.Label(ctrl, text=t("lineup.formation")).pack(side=tk.LEFT)
        pref_fmt = preferences.load().get("default_formation", "4-4-2")
        if pref_fmt not in lineup.FORMATION_ROLES:
            pref_fmt = t("lineup.rank_all")
        self.formation_var = tk.StringVar(value=pref_fmt)
        self.formation_cb = ttk.Combobox(
            ctrl, textvariable=self.formation_var,
            values=[t("lineup.rank_all")] + list(lineup.FORMATION_ROLES),
            state="readonly", width=12,
        )
        self.formation_cb.pack(side=tk.LEFT, padx=(4, 10))

        self.cross_pos_var = tk.BooleanVar(value=False)
        ttk.Checkbutton(ctrl, text=t("lineup.cross_pos"),
                        variable=self.cross_pos_var).pack(side=tk.LEFT, padx=6)

        self.include_injured_var = tk.BooleanVar(value=False)
        ttk.Checkbutton(ctrl, text=t("lineup.include_inj"),
                        variable=self.include_injured_var).pack(side=tk.LEFT, padx=6)

        ttk.Button(ctrl, text=t("lineup.compute"),
                   command=self._compute).pack(side=tk.LEFT, padx=(16, 4))

        body = ttk.PanedWindow(self, orient=tk.HORIZONTAL)
        body.pack(fill=tk.BOTH, expand=True, padx=8, pady=6)

        # Left: formation ranking
        left = ttk.Frame(body)
        body.add(left, weight=1)
        ttk.Label(left, text=t("lineup.form_ranking"),
                  font=("TkDefaultFont", 10, "bold")).pack(anchor="w")
        self.rank_tree = ttk.Treeview(
            left, show="headings",
            columns=("form", "comp", "skill", "fit"),
            height=5,
        )
        for c, tkey, w, anc in [
            ("form", "lineup.col.form",  80, tk.W),
            ("comp", "lineup.col.comp",  90, tk.E),
            ("skill", "lineup.col.skill", 70, tk.E),
            ("fit",  "lineup.col.fit",   60, tk.E),
        ]:
            self.rank_tree.heading(c, text=t(tkey))
            self.rank_tree.column(c, width=w, anchor=anc)
        self.rank_tree.pack(fill=tk.BOTH, expand=True, pady=(2, 6))
        self.rank_tree.bind("<<TreeviewSelect>>", self._on_rank_select)

        ttk.Label(left, text=t("lineup.reassign"),
                  font=("TkDefaultFont", 10, "bold")).pack(anchor="w")
        self.reassign_tree = ttk.Treeview(
            left, show="headings",
            columns=("id", "nominal", "suggested", "gap"),
            height=10,
        )
        for c, tkey, w, anc in [
            ("id",        "lineup.col.player",    140, tk.W),
            ("nominal",   "lineup.col.nominal",    80, tk.W),
            ("suggested", "lineup.col.suggested",  80, tk.W),
            ("gap",       "lineup.col.gap",        70, tk.E),
        ]:
            self.reassign_tree.heading(c, text=t(tkey))
            self.reassign_tree.column(c, width=w, anchor=anc)
        self.reassign_tree.pack(fill=tk.BOTH, expand=True, pady=(2, 0))

        # Right: recommended XI
        right = ttk.Frame(body)
        body.add(right, weight=2)
        self.summary_var = tk.StringVar(value=t("lineup.click_compute"))
        ttk.Label(right, textvariable=self.summary_var,
                  font=("TkDefaultFont", 10, "bold")).pack(anchor="w")
        self.xi_tree = ttk.Treeview(
            right, show="headings",
            columns=("role", "pid", "name", "age", "team", "skill", "fit"),
        )
        for c, tkey, w, anc in [
            ("role",  "lineup.col.role",  55, tk.W),
            ("pid",   "lineup.col.pid",   55, tk.E),
            ("name",  "lineup.col.name", 150, tk.W),
            ("age",   "lineup.col.age",   45, tk.E),
            ("team",  "lineup.col.team", 140, tk.W),
            ("skill", "lineup.col.skill", 60, tk.E),
            ("fit",   "lineup.col.fit",   55, tk.E),
        ]:
            self.xi_tree.heading(c, text=t(tkey))
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
        if team_label.startswith("\u2014"):
            pool = [p for p in self.slot.players
                    if SaveSlot._is_real_player(p)]
            pool_label = "whole championship"
        else:
            team_index = int(team_label.split()[0])
            pool = self.slot.get_players_by_team(team_index)
            pool_label = f"team {team_index} -- {self.slot.get_team_name(team_index)}"

        formation_choice = self.formation_var.get()
        formations = (None if formation_choice.startswith("\u2014")
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
            eligible = [p for p in pool if eligibility(p)]
            pos_names = {1: "GK", 2: "DEF", 3: "MID", 4: "FWD"}
            have = {pos: sum(1 for p in eligible if p.position == pos)
                    for pos in (1, 2, 3, 4)}
            have_str = " \u00b7 ".join(
                f"{have[pos]} {pos_names[pos]}" for pos in (1, 2, 3, 4)
            )
            self.summary_var.set(
                f"No formation could be filled from {pool_label} "
                f"({len(pool)} players, {len(eligible)} eligible)."
            )
            lines = [f"Eligible (not injured): {len(eligible)}  ({have_str})"]
            fmt_keys_diag = formations if formations else list(lineup.FORMATION_ROLES)
            for f in fmt_keys_diag:
                needed = Counter(
                    lineup.ROLES[role]["position"]
                    for role in lineup.FORMATION_ROLES[f]
                )
                need_str = " \u00b7 ".join(
                    f"{needed[pos]} {pos_names[pos]}" for pos in (1, 2, 3, 4)
                )
                short = [
                    f"{pos_names[pos]} (need {needed[pos]}, have {have[pos]})"
                    for pos in (1, 2, 3, 4)
                    if have[pos] < needed[pos]
                ]
                short_str = ", ".join(short) if short else "none"
                lines.append(f"{f}: needs {need_str}  \u2014  short: {short_str}")
            self.breakdown_var.set("\n".join(lines))
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
                                values=(t("lineup.reserves"), "", "", "", "", "", ""),
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
            f"{result.formation}{suffix}  --  composite {result.composite:.1f}, "
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
