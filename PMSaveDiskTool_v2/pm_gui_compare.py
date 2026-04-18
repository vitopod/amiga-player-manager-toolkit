"""Compare Players window — radar chart + skill bars for two players."""

import math
import tkinter as tk
from tkinter import ttk

from pm_core.player import POSITION_NAMES

from pm_gui_theme import PAL, _retro


class PlayerCompareWindow(tk.Toplevel):

    # Comparison uses only the 9 skills PM labels on the in-game Player
    # Information card. Byte 0x0F (named ``flair`` internally) is unlabelled
    # in-game, so showing it here would imply our placeholder name is
    # canonical — same policy as pm_core/warnings.py applies.
    _COMPARE_SKILLS = (
        "pace", "agility", "stamina", "resilience", "aggression",
        "passing", "shooting", "tackling", "keeping",
    )
    _SKILL_LABELS = [s.upper()[:7] for s in _COMPARE_SKILLS]
    _MAX_SKILL = 99
    _N = len(_COMPARE_SKILLS)
    _CX, _CY, _R = 148, 148, 108

    def __init__(self, parent, slot, game_disk, player_a=None):
        super().__init__(parent)
        self.title("Compare Players")
        self.geometry("980x620")
        self.minsize(960, 540)
        self.configure(bg=PAL["bg"])

        self._slot = slot
        self._game_disk = game_disk
        self._player_a = player_a
        self._player_b = None

        # Per-side state so swap and lookup stay symmetric.
        self._team_players = {"a": [], "b": []}

        self._build_title_band()
        self._build_selector_row()
        self._build_body()
        self._build_legend_row()
        self._build_bottom_bar()

        self._populate_team_combos()
        self._seed_initial_selection(player_a)

    def _build_title_band(self):
        band = tk.Frame(self, bg=PAL["bg_header"], height=30)
        band.pack(fill=tk.X)
        band.pack_propagate(False)
        tk.Label(band, text="COMPARE PLAYERS",
                 bg=PAL["bg_header"], fg=PAL["fg_title"],
                 font=_retro(13, "bold")).pack(side=tk.LEFT, padx=10)

    def _build_selector_row(self):
        """Two symmetric panels (A left, B right) with a swap button between."""
        row = tk.Frame(self, bg=PAL["bg_mid"])
        row.pack(fill=tk.X)
        tk.Frame(row, bg=PAL["border"], height=1).pack(fill=tk.X, side=tk.BOTTOM)

        # Side A
        a_panel = self._build_side_panel(row, "a", PAL["player_a"])
        a_panel.pack(side=tk.LEFT, fill=tk.Y, padx=(10, 4), pady=6)

        # Swap
        swap_frame = tk.Frame(row, bg=PAL["bg_mid"])
        swap_frame.pack(side=tk.LEFT, fill=tk.Y)
        tk.Frame(swap_frame, bg=PAL["bg_mid"], height=20).pack()  # top spacer
        tk.Button(swap_frame, text="⇄", bg=PAL["bg_mid"], fg=PAL["fg_data"],
                  font=("Courier New", 18, "bold"), relief="flat", bd=0,
                  activebackground=PAL["selected"],
                  activeforeground=PAL["fg_white"],
                  command=self._swap).pack(padx=10)

        # Side B
        b_panel = self._build_side_panel(row, "b", PAL["player_b"])
        b_panel.pack(side=tk.LEFT, fill=tk.Y, padx=(4, 10), pady=6)

    def _build_side_panel(self, parent, side: str, accent: str) -> tk.Frame:
        """Build one of the two symmetric player-selection panels.

        Stores references to the combos and labels under ``self._<name>[side]``
        so swap / selection handlers stay side-agnostic.
        """
        panel = tk.Frame(parent, bg=PAL["bg_mid"])

        header = f"PLAYER {side.upper()}"
        tk.Label(panel, text=header, bg=PAL["bg_mid"],
                 fg=PAL["fg_label"],
                 font=("Courier New", 9, "bold")).grid(
                     row=0, column=0, columnspan=2, sticky="w")

        tk.Label(panel, text="Team", bg=PAL["bg_mid"],
                 fg=PAL["fg_label"], font=("Courier New", 9)).grid(
                     row=1, column=0, sticky="w", padx=(0, 6), pady=(2, 0))
        team_var = tk.StringVar()
        team_combo = ttk.Combobox(panel, textvariable=team_var,
                                  state="readonly", width=22)
        team_combo.grid(row=1, column=1, sticky="w", pady=(2, 0))
        team_combo.bind(
            "<<ComboboxSelected>>",
            lambda e, s=side: self._on_team_selected(s),
        )

        tk.Label(panel, text="Player", bg=PAL["bg_mid"],
                 fg=PAL["fg_label"], font=("Courier New", 9)).grid(
                     row=2, column=0, sticky="w", padx=(0, 6), pady=(2, 0))
        player_var = tk.StringVar()
        player_combo = ttk.Combobox(panel, textvariable=player_var,
                                    state="readonly", width=22)
        player_combo.grid(row=2, column=1, sticky="w", pady=(2, 0))
        player_combo.bind(
            "<<ComboboxSelected>>",
            lambda e, s=side: self._on_player_selected(s),
        )

        name_lbl = tk.Label(panel, text="—",
                            bg=PAL["bg_mid"], fg=accent,
                            font=("Courier New", 12, "bold"))
        name_lbl.grid(row=3, column=0, columnspan=2, sticky="w", pady=(6, 0))

        meta_lbl = tk.Label(panel, text="",
                            bg=PAL["bg_mid"], fg=PAL["fg_data"],
                            font=("Courier New", 9))
        meta_lbl.grid(row=4, column=0, columnspan=2, sticky="w")

        # Stash refs keyed by side so handlers don't branch on A/B.
        if not hasattr(self, "_team_var"):
            self._team_var: dict = {}
            self._team_combo: dict = {}
            self._player_var: dict = {}
            self._player_combo: dict = {}
            self._name_lbl: dict = {}
            self._meta_lbl: dict = {}
        self._team_var[side] = team_var
        self._team_combo[side] = team_combo
        self._player_var[side] = player_var
        self._player_combo[side] = player_combo
        self._name_lbl[side] = name_lbl
        self._meta_lbl[side] = meta_lbl

        return panel

    def _build_body(self):
        body = tk.Frame(self, bg=PAL["bg"])
        body.pack(fill=tk.BOTH, expand=True)
        tk.Frame(body, bg=PAL["border"], width=1).pack(side=tk.LEFT, fill=tk.Y)

        radar_frame = tk.Frame(body, bg=PAL["radar_bg"])
        radar_frame.pack(side=tk.LEFT, fill=tk.Y)
        self._radar_canvas = tk.Canvas(radar_frame, width=310, height=310,
                                       bg=PAL["radar_bg"], highlightthickness=0)
        self._radar_canvas.pack(padx=6, pady=6)

        tk.Frame(body, bg=PAL["border"], width=1).pack(side=tk.LEFT, fill=tk.Y)

        bars_frame = tk.Frame(body, bg=PAL["bg"])
        bars_frame.pack(side=tk.LEFT, fill=tk.Y)
        self._bars_canvas = tk.Canvas(bars_frame, bg=PAL["bg"],
                                      width=600, highlightthickness=0)
        self._bars_canvas.pack(padx=8, pady=6, fill=tk.Y)

    def _build_legend_row(self):
        leg = tk.Frame(self, bg=PAL["bg_mid"])
        leg.pack(fill=tk.X)
        tk.Label(leg, text="●", bg=PAL["bg_mid"], fg=PAL["player_a"],
                 font=("Courier New", 10)).pack(side=tk.LEFT, padx=(10, 2), pady=3)
        self._leg_a = tk.Label(leg, text="Player A", bg=PAL["bg_mid"],
                               fg=PAL["fg_label"], font=("Courier New", 9))
        self._leg_a.pack(side=tk.LEFT, padx=(0, 16))
        tk.Label(leg, text="●", bg=PAL["bg_mid"], fg=PAL["player_b"],
                 font=("Courier New", 10)).pack(side=tk.LEFT, padx=(0, 2))
        self._leg_b = tk.Label(leg, text="Player B", bg=PAL["bg_mid"],
                               fg=PAL["fg_label"], font=("Courier New", 9))
        self._leg_b.pack(side=tk.LEFT)

    def _build_bottom_bar(self):
        bar = tk.Frame(self, bg=PAL["btn_go"])
        bar.pack(fill=tk.X, side=tk.BOTTOM)
        self._status_lbl = tk.Label(bar, text="Select two players to compare.",
                                    bg=PAL["btn_go"], fg=PAL["btn_go_fg"],
                                    font=("Courier New", 10, "bold"))
        self._status_lbl.pack(side=tk.LEFT, padx=10, pady=5)
        # Clickable tk.Label instead of tk.Button — native tk.Button on
        # macOS Aqua ignores bg/fg and repaints in system colours, which
        # turned DONE into an invisible-text button. Same workaround as
        # the APPLY / REVERT footer in pm_gui.py.
        done = tk.Label(bar, text="DONE",
                        bg=PAL["btn_go"], fg=PAL["btn_go_fg"],
                        font=("Courier New", 10, "bold"),
                        padx=14, pady=5,
                        borderwidth=0, highlightthickness=0,
                        cursor="hand2")
        done.bind("<Button-1>", lambda _e: self.destroy())
        done.bind("<Enter>", lambda _e: done.configure(bg=PAL["selected"]))
        done.bind("<Leave>", lambda _e: done.configure(bg=PAL["btn_go"]))
        done.pack(side=tk.RIGHT, padx=8, pady=4)

    def _player_name(self, p) -> str:
        if self._game_disk and p.rng_seed:
            n = self._game_disk.player_full_name(p.rng_seed)
            if n:
                return n
        return f"#{p.player_id}"

    def _player_meta(self, p) -> str:
        pos = POSITION_NAMES.get(p.position, "?")
        team = self._slot.get_team_name(p.team_index)
        mkt = " ★" if p.is_market_available else ""
        return f"{pos} · age {p.age} · {team}{mkt} · skill {p.total_skill}"

    # ── Combo population / selection ──────────────────────────

    def _populate_team_combos(self):
        team_names = sorted(
            self._slot.get_team_name(i)
            for i in range(1, len(self._slot.team_names))
        )
        teams = ["★ Free Agents"] + team_names
        for side in ("a", "b"):
            self._team_combo[side]["values"] = teams

    def _players_for_team_label(self, team_label: str):
        """Return the player list for a team-combo value (or []) for bad input."""
        if team_label == "★ Free Agents":
            return [p for p in self._slot.players
                    if p.is_free_agent and self._slot._is_real_player(p)]
        team_idx = next(
            (i for i, n in enumerate(self._slot.team_names) if n == team_label),
            None,
        )
        if team_idx is None:
            return []
        return self._slot.get_players_by_team(team_idx)

    def _on_team_selected(self, side: str):
        team_label = self._team_var[side].get()
        players = self._players_for_team_label(team_label)
        self._team_players[side] = players
        self._player_combo[side]["values"] = [
            self._player_name(p) for p in players
        ]
        self._player_var[side].set("")
        # Team changed → that side's player selection is now stale.
        if side == "a":
            self._player_a = None
        else:
            self._player_b = None
        self._refresh_side_labels(side)

    def _on_player_selected(self, side: str):
        idx = self._player_combo[side].current()
        if idx < 0 or idx >= len(self._team_players[side]):
            return
        player = self._team_players[side][idx]
        if side == "a":
            self._player_a = player
        else:
            self._player_b = player
        self._refresh_side_labels(side)
        self._draw()

    # ── Label / combo sync helpers ────────────────────────────

    def _refresh_side_labels(self, side: str):
        player = self._player_a if side == "a" else self._player_b
        if player is None:
            self._name_lbl[side].config(text="—")
            self._meta_lbl[side].config(text="")
            leg = self._leg_a if side == "a" else self._leg_b
            leg.config(text=f"Player {side.upper()}")
            return
        name = self._player_name(player)
        self._name_lbl[side].config(text=name)
        self._meta_lbl[side].config(text=self._player_meta(player))
        leg = self._leg_a if side == "a" else self._leg_b
        leg.config(text=name)

    def _sync_side_combos(self, side: str, player):
        """Drive combos for ``side`` so they reflect ``player``."""
        if player is None:
            self._team_var[side].set("")
            self._team_players[side] = []
            self._player_combo[side]["values"] = []
            self._player_var[side].set("")
            return
        team_label = ("★ Free Agents" if player.is_free_agent
                      else self._slot.get_team_name(player.team_index))
        self._team_var[side].set(team_label)
        players = self._players_for_team_label(team_label)
        self._team_players[side] = players
        self._player_combo[side]["values"] = [
            self._player_name(p) for p in players
        ]
        try:
            idx = players.index(player)
            self._player_combo[side].current(idx)
        except ValueError:
            self._player_var[side].set("")

    # ── Entry points ──────────────────────────────────────────

    def set_player_a(self, player) -> None:
        """External hook: right-click → Send to Compare sends a player here."""
        self._player_a = player
        self._sync_side_combos("a", player)
        self._refresh_side_labels("a")
        if self._player_a and self._player_b:
            self._draw()

    def _swap(self):
        self._player_a, self._player_b = self._player_b, self._player_a
        self._sync_side_combos("a", self._player_a)
        self._sync_side_combos("b", self._player_b)
        self._refresh_side_labels("a")
        self._refresh_side_labels("b")
        if self._player_a and self._player_b:
            self._draw()

    def _seed_initial_selection(self, player_a):
        """Pre-fill the panels so the window is immediately useful.

        - If ``player_a`` was passed in (right-click → Send to Compare),
          A's combos follow it and B's team combo mirrors A's team so a
          single extra click picks an opponent.
        - With no ``player_a``, both sides stay blank and the user picks
          from scratch; the team-name list is already populated.
        """
        if player_a is None:
            return
        self._sync_side_combos("a", player_a)
        self._refresh_side_labels("a")
        # Convenience: give B the same team pre-selected but no player chosen.
        team_label = self._team_var["a"].get()
        if team_label:
            self._team_var["b"].set(team_label)
            players = self._players_for_team_label(team_label)
            self._team_players["b"] = players
            self._player_combo["b"]["values"] = [
                self._player_name(p) for p in players
            ]

    def _draw(self):
        if not (self._player_a and self._player_b):
            return
        self._draw_radar()
        self._draw_bars()
        self._update_status()

    def _skill_values(self, p) -> list[int]:
        return [getattr(p, s) for s in self._COMPARE_SKILLS]

    def _radar_point(self, i: int, val: int) -> tuple[float, float]:
        angle = (i * 2 * math.pi / self._N) - math.pi / 2
        ratio = max(0, min(val, self._MAX_SKILL)) / self._MAX_SKILL
        return (self._CX + ratio * self._R * math.cos(angle),
                self._CY + ratio * self._R * math.sin(angle))

    def _axis_tip(self, i: int) -> tuple[float, float]:
        angle = (i * 2 * math.pi / self._N) - math.pi / 2
        return (self._CX + self._R * math.cos(angle),
                self._CY + self._R * math.sin(angle))

    def _draw_radar(self):
        c = self._radar_canvas
        c.delete("all")
        cx, cy, r, n = self._CX, self._CY, self._R, self._N

        for g in range(1, 5):
            ratio = g / 4
            pts = []
            for i in range(n):
                angle = (i * 2 * math.pi / n) - math.pi / 2
                pts += [cx + ratio * r * math.cos(angle),
                        cy + ratio * r * math.sin(angle)]
            c.create_polygon(pts, outline=PAL["border"],
                             fill="#000066" if g == 4 else "", width=0.8)

        for i, label in enumerate(self._SKILL_LABELS):
            tx, ty = self._axis_tip(i)
            c.create_line(cx, cy, tx, ty, fill=PAL["border"], width=0.8)
            lx = cx + (r + 18) * math.cos((i * 2 * math.pi / n) - math.pi / 2)
            ly = cy + (r + 18) * math.sin((i * 2 * math.pi / n) - math.pi / 2)
            c.create_text(lx, ly, text=label, fill=PAL["fg_data"],
                          font=("Courier New", 9, "bold"), anchor="center")

        pts_b = []
        for i, v in enumerate(self._skill_values(self._player_b)):
            x, y = self._radar_point(i, v)
            pts_b += [x, y]
        c.create_polygon(pts_b, outline=PAL["player_b"], fill="", width=2)

        pts_a = []
        for i, v in enumerate(self._skill_values(self._player_a)):
            x, y = self._radar_point(i, v)
            pts_a += [x, y]
        c.create_polygon(pts_a, outline=PAL["player_a"], fill="", width=2)

        for pts, col in [(pts_b, PAL["player_b"]), (pts_a, PAL["player_a"])]:
            for i in range(0, len(pts), 2):
                x, y = pts[i], pts[i + 1]
                c.create_oval(x - 3, y - 3, x + 3, y + 3, fill=col, outline="")

    def _draw_bars(self):
        c = self._bars_canvas
        c.delete("all")

        vals_a = self._skill_values(self._player_a)
        vals_b = self._skill_values(self._player_b)

        row_h = 28
        val_w = 30
        label_w = 90
        half_bar = 200  # max bar length in pixels (full skill = 200px)
        canvas_w = 600
        # Centre the block: val_w + half_bar + label_w + half_bar + val_w
        x0 = (canvas_w - val_w - half_bar - label_w - half_bar - val_w) // 2

        bax1 = x0 + val_w          # bar A left edge
        bax2 = bax1 + half_bar     # bar A right edge
        bbx1 = bax2 + label_w      # bar B left edge
        bbx2 = bbx1 + half_bar     # bar B right edge

        for idx, (skill_label, va, vb) in enumerate(
            zip(self._SKILL_LABELS, vals_a, vals_b)
        ):
            y = idx * row_h + 10
            win_a = va > vb
            win_b = vb > va

            col_a = PAL["player_a"] if win_a else "#223344"
            col_b = PAL["player_b"] if win_b else "#331111"
            # Losers still need to be legible; fg_label (mid blue) stays
            # clearly readable against the navy background while leaving
            # the winner's bright team color as the visual emphasis.
            fg_a  = PAL["player_a"] if win_a else PAL["fg_label"]
            fg_b  = PAL["player_b"] if win_b else PAL["fg_label"]

            fill_a = int((va / 200) * half_bar)
            fill_b = int((vb / 200) * half_bar)

            c.create_text(bax1 - 3, y + 8, text=str(va),
                          fill=fg_a, font=("Courier New", 10, "bold" if win_a else "normal"),
                          anchor="e")
            c.create_rectangle(bax1, y + 5, bax2, y + 11,
                               fill=PAL["bar_trough"], outline=PAL["border"])
            if fill_a:
                c.create_rectangle(bax2 - fill_a, y + 5, bax2, y + 11,
                                   fill=col_a, outline="")
            c.create_text(bax2 + label_w // 2, y + 8, text=skill_label,
                          fill=PAL["fg_data"], font=("Courier New", 9, "bold"),
                          anchor="center")
            c.create_rectangle(bbx1, y + 5, bbx2, y + 11,
                               fill=PAL["bar_trough"], outline=PAL["border"])
            if fill_b:
                c.create_rectangle(bbx1, y + 5, bbx1 + fill_b, y + 11,
                                   fill=col_b, outline="")
            c.create_text(bbx2 + 3, y + 8, text=str(vb),
                          fill=fg_b, font=("Courier New", 10, "bold" if win_b else "normal"),
                          anchor="w")

    def _update_status(self):
        vals_a = self._skill_values(self._player_a)
        vals_b = self._skill_values(self._player_b)
        wins_a = sum(1 for a, b in zip(vals_a, vals_b) if a > b)
        wins_b = sum(1 for a, b in zip(vals_a, vals_b) if b > a)
        name_a = self._player_name(self._player_a)
        name_b = self._player_name(self._player_b)
        if wins_a > wins_b:
            msg = f"{name_a} leads on {wins_a}/{self._N} skills"
        elif wins_b > wins_a:
            msg = f"{name_b} leads on {wins_b}/{self._N} skills"
        else:
            msg = "Tied — equal wins across all skills"
        self._status_lbl.config(text=msg)
