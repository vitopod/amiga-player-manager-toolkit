"""Compare Players window — radar chart + skill bars for two players."""

import math
import tkinter as tk
from tkinter import ttk

from pm_core.player import SKILL_NAMES, POSITION_NAMES

from pm_gui_theme import PAL, _retro


class PlayerCompareWindow(tk.Toplevel):

    _SKILL_LABELS = [s.upper()[:7] for s in SKILL_NAMES]
    _MAX_SKILL = 99
    _N = len(SKILL_NAMES)
    _CX, _CY, _R = 148, 148, 108

    def __init__(self, parent, slot, game_disk, player_a=None):
        super().__init__(parent)
        self.title("Compare Players")
        self.geometry("980x560")
        self.minsize(960, 480)
        self.configure(bg=PAL["bg"])

        self._slot = slot
        self._game_disk = game_disk
        self._player_a = player_a
        self._player_b = None

        self._build_title_band()
        self._build_selector_row()
        self._build_body()
        self._build_legend_row()
        self._build_bottom_bar()

        self._populate_team_combo()
        if player_a:
            self._refresh_player_a_labels()

    def _build_title_band(self):
        band = tk.Frame(self, bg=PAL["bg_header"], height=30)
        band.pack(fill=tk.X)
        band.pack_propagate(False)
        tk.Label(band, text="COMPARE PLAYERS",
                 bg=PAL["bg_header"], fg=PAL["fg_title"],
                 font=_retro(13, "bold")).pack(side=tk.LEFT, padx=10)

    def _build_selector_row(self):
        row = tk.Frame(self, bg=PAL["bg_mid"])
        row.pack(fill=tk.X)
        tk.Frame(row, bg=PAL["border"], height=1).pack(fill=tk.X, side=tk.BOTTOM)

        a_frame = tk.Frame(row, bg=PAL["bg_mid"])
        a_frame.pack(side=tk.LEFT, padx=10, pady=6)
        tk.Label(a_frame, text="PLAYER A", bg=PAL["bg_mid"],
                 fg=PAL["fg_label"], font=("Courier New", 9, "bold")).pack(anchor="w")
        self._a_name_lbl = tk.Label(a_frame, text="—",
                                    bg=PAL["bg_mid"], fg=PAL["player_a"],
                                    font=("Courier New", 12, "bold"))
        self._a_name_lbl.pack(anchor="w")
        self._a_meta_lbl = tk.Label(a_frame, text="",
                                    bg=PAL["bg_mid"], fg=PAL["fg_data"],
                                    font=("Courier New", 9))
        self._a_meta_lbl.pack(anchor="w")

        tk.Button(row, text="⇄", bg=PAL["bg_mid"], fg=PAL["fg_data"],
                  font=("Courier New", 16, "bold"), relief="flat", bd=0,
                  activebackground=PAL["selected"], activeforeground=PAL["fg_white"],
                  command=self._swap).pack(side=tk.LEFT, padx=8)

        b_frame = tk.Frame(row, bg=PAL["bg_mid"])
        b_frame.pack(side=tk.LEFT, padx=10, pady=6)
        tk.Label(b_frame, text="PLAYER B", bg=PAL["bg_mid"],
                 fg=PAL["fg_label"], font=("Courier New", 9, "bold")).pack(anchor="w")
        self._b_name_lbl = tk.Label(b_frame, text="—",
                                    bg=PAL["bg_mid"], fg=PAL["player_b"],
                                    font=("Courier New", 12, "bold"))
        self._b_name_lbl.pack(anchor="w")
        self._b_meta_lbl = tk.Label(b_frame, text="",
                                    bg=PAL["bg_mid"], fg=PAL["fg_data"],
                                    font=("Courier New", 9))
        self._b_meta_lbl.pack(anchor="w")

        pick_frame = tk.Frame(row, bg=PAL["bg_mid"])
        pick_frame.pack(side=tk.RIGHT, padx=10, pady=6)

        tk.Label(pick_frame, text="TEAM", bg=PAL["bg_mid"],
                 fg=PAL["fg_label"], font=("Courier New", 9, "bold")).grid(
                     row=0, column=0, sticky="w", padx=(0, 4))
        self._team_var = tk.StringVar()
        self._team_combo = ttk.Combobox(pick_frame, textvariable=self._team_var,
                                        state="readonly", width=18)
        self._team_combo.grid(row=0, column=1, padx=(4, 0), pady=2)
        self._team_combo.bind("<<ComboboxSelected>>", self._on_team_selected)

        tk.Label(pick_frame, text="PLAYER", bg=PAL["bg_mid"],
                 fg=PAL["fg_label"], font=("Courier New", 9, "bold")).grid(
                     row=1, column=0, sticky="w", padx=(0, 4))
        self._player_var = tk.StringVar()
        self._player_combo = ttk.Combobox(pick_frame, textvariable=self._player_var,
                                          state="readonly", width=18)
        self._player_combo.grid(row=1, column=1, padx=(4, 0), pady=2)
        self._player_combo.bind("<<ComboboxSelected>>", self._on_player_b_selected)

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
        tk.Button(bar, text="DONE", bg=PAL["btn_go"], fg=PAL["btn_go_fg"],
                  highlightbackground=PAL["btn_go"], highlightthickness=0,
                  font=("Courier New", 10, "bold"),
                  relief="flat", bd=0, padx=18, pady=4,
                  activebackground=PAL["selected"], activeforeground=PAL["fg_white"],
                  command=self.destroy).pack(side=tk.RIGHT, padx=8, pady=4)

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

    def _populate_team_combo(self):
        team_names = sorted(
            self._slot.get_team_name(i)
            for i in range(1, len(self._slot.team_names))
        )
        teams = ["★ Free Agents"] + team_names
        self._team_combo["values"] = teams

    def _on_team_selected(self, event=None):
        team_sel = self._team_var.get()
        if team_sel == "★ Free Agents":
            players = [p for p in self._slot.players if p.is_free_agent
                       and self._slot._is_real_player(p)]
        else:
            team_name = team_sel
            team_idx = next(
                (i for i, n in enumerate(self._slot.team_names) if n == team_name),
                None,
            )
            if team_idx is None:
                return
            players = self._slot.get_players_by_team(team_idx)

        entries = [self._player_name(p) for p in players]
        self._team_players = players
        self._player_combo["values"] = entries
        self._player_var.set("")

    def _on_player_b_selected(self, event=None):
        idx = self._player_combo.current()
        if idx < 0 or not hasattr(self, "_team_players"):
            return
        self._player_b = self._team_players[idx]
        self._refresh_player_b_labels()
        self._draw()

    def _refresh_player_a_labels(self):
        if not self._player_a:
            return
        name = self._player_name(self._player_a)
        self._a_name_lbl.config(text=name)
        self._a_meta_lbl.config(text=self._player_meta(self._player_a))
        self._leg_a.config(text=name)

    def _refresh_player_b_labels(self):
        if not self._player_b:
            return
        name = self._player_name(self._player_b)
        self._b_name_lbl.config(text=name)
        self._b_meta_lbl.config(text=self._player_meta(self._player_b))
        self._leg_b.config(text=name)

    def set_player_a(self, player) -> None:
        self._player_a = player
        self._refresh_player_a_labels()
        if self._player_b:
            self._draw()

    def _swap(self):
        self._player_a, self._player_b = self._player_b, self._player_a
        self._refresh_player_a_labels()
        self._refresh_player_b_labels()
        if self._player_a and self._player_b:
            self._draw()

    def _draw(self):
        if not (self._player_a and self._player_b):
            return
        self._draw_radar()
        self._draw_bars()
        self._update_status()

    def _skill_values(self, p) -> list[int]:
        return [getattr(p, s) for s in SKILL_NAMES]

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
            msg = f"{name_a} leads on {wins_a}/10 skills"
        elif wins_b > wins_a:
            msg = f"{name_b} leads on {wins_b}/10 skills"
        else:
            msg = "Tied — equal wins across all skills"
        self._status_lbl.config(text=msg)
