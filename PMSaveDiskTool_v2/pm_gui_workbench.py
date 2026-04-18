"""Byte Workbench — reverse-engineering UI for the 42-byte player record."""

import tkinter as tk
from tkinter import ttk, messagebox

from pm_core import workbench
from pm_core.save import SaveSlot
from pm_core.player import (
    RECORD_SIZE, FIELD_LAYOUT, field_at_offset, serialize_player,
)

from pm_gui_theme import PAL
from pm_gui_help import help_button


# Preset filters shared by the Byte Workbench tabs. "Real players" uses the
# same garbage-record guard as the Young Talents / Best XI views.
BYTE_PRESETS: dict[str, "callable"] = {
    "All (1536)": lambda p: True,
    "Real players": SaveSlot._is_real_player,
    "Free agents": lambda p: p.is_free_agent,
    "Contracted": lambda p: not p.is_free_agent,
    "On transfer list": lambda p: p.is_transfer_listed,
    "Not on transfer list": lambda p: not p.is_transfer_listed,
    "GK": lambda p: p.position == 1,
    "DEF": lambda p: p.position == 2,
    "MID": lambda p: p.position == 3,
    "FWD": lambda p: p.position == 4,
    "Young (≤21)": lambda p: 0 < p.age <= 21,
    "Veteran (≥30)": lambda p: p.age >= 30,
}


class ByteWorkbenchWindow(tk.Toplevel):
    """Reverse-engineering workbench for the 42-byte player record.

    Three tabs on the same SaveSlot:
      - Raw View: hex/dec/bin dump of one player's bytes with field labels.
      - Histogram: value distribution at a byte (optionally masked to a bit).
      - Diff: bits most discriminative between two player sets.
    """

    def __init__(self, parent, slot: SaveSlot, game_disk=None):
        super().__init__(parent)
        self.title("Byte Workbench")
        self.geometry("920x560")
        self.minsize(760, 420)

        self.slot = slot
        self.game_disk = game_disk

        header = ttk.Frame(self, padding=(8, 8, 8, 4))
        header.pack(fill=tk.X)
        ttk.Label(header, text="Byte Workbench",
                  font=("TkDefaultFont", 13, "bold")).pack(side=tk.LEFT)
        help_button(header, "byte_workbench").pack(side=tk.RIGHT)

        nb = ttk.Notebook(self)
        nb.pack(fill=tk.BOTH, expand=True, padx=6, pady=6)

        self._build_raw_tab(nb)
        self._build_histogram_tab(nb)
        self._build_diff_tab(nb)

    # ── Raw View ──────────────────────────────────────────────

    def _build_raw_tab(self, nb):
        frame = ttk.Frame(nb)
        nb.add(frame, text="Raw View")

        top = ttk.Frame(frame)
        top.pack(fill=tk.X, padx=4, pady=(4, 6))
        ttk.Label(top, text="Player #:").pack(side=tk.LEFT)
        self.raw_pid = tk.IntVar(value=0)
        spin = ttk.Spinbox(top, from_=0, to=len(self.slot.players) - 1,
                           textvariable=self.raw_pid, width=6,
                           command=self._refresh_raw)
        spin.pack(side=tk.LEFT, padx=(4, 10))
        spin.bind("<Return>", lambda e: self._refresh_raw())

        self.raw_header = ttk.Label(top, text="", foreground=PAL["fg_label"])
        self.raw_header.pack(side=tk.LEFT, padx=8)

        cols = ("offset", "hex", "dec", "bin", "field", "note")
        self.raw_tree = ttk.Treeview(frame, columns=cols, show="headings",
                                     height=20)
        for c, txt, w, anc in [
            ("offset", "Offset", 70, "e"),
            ("hex", "Hex", 50, "e"),
            ("dec", "Dec", 55, "e"),
            ("bin", "Bin", 85, "e"),
            ("field", "Field", 200, "w"),
            ("note", "Note", 330, "w"),
        ]:
            self.raw_tree.heading(c, text=txt)
            self.raw_tree.column(c, width=w, anchor=anc)
        sb = ttk.Scrollbar(frame, orient=tk.VERTICAL,
                           command=self.raw_tree.yview)
        self.raw_tree.configure(yscrollcommand=sb.set)
        self.raw_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True,
                           padx=(4, 0), pady=(0, 4))
        sb.pack(side=tk.LEFT, fill=tk.Y, padx=(0, 4), pady=(0, 4))

        self._refresh_raw()

    def _refresh_raw(self):
        try:
            pid = int(self.raw_pid.get())
        except (tk.TclError, ValueError):
            return
        if not 0 <= pid < len(self.slot.players):
            return
        p = self.slot.players[pid]
        data = serialize_player(p)

        name = (self.game_disk.player_full_name(p.rng_seed)
                if self.game_disk and p.rng_seed else "")
        team = self.slot.get_team_name(p.team_index)
        self.raw_header.config(
            text=f"{name or '(no name)'} · age {p.age} · {p.position_name} · {team}"
        )

        notes = {off: note for off, _, _, note in FIELD_LAYOUT}
        self.raw_tree.delete(*self.raw_tree.get_children())
        for offset in range(RECORD_SIZE):
            b = data[offset]
            name_, sub, size = field_at_offset(offset)
            field_label = name_ + (f"[{sub}/{size}]" if size > 1 else "")
            note = notes.get(offset, "") if sub == 0 else ""
            self.raw_tree.insert("", "end", values=(
                f"0x{offset:02X}",
                f"0x{b:02X}",
                b,
                f"{b:08b}",
                field_label,
                note,
            ))

    # ── Histogram ─────────────────────────────────────────────

    def _build_histogram_tab(self, nb):
        frame = ttk.Frame(nb)
        nb.add(frame, text="Histogram")

        top = ttk.Frame(frame)
        top.pack(fill=tk.X, padx=4, pady=(4, 6))

        ttk.Label(top, text="Set:").pack(side=tk.LEFT)
        self.hist_preset = tk.StringVar(value="Real players")
        ttk.Combobox(top, textvariable=self.hist_preset,
                     values=list(BYTE_PRESETS), state="readonly",
                     width=22).pack(side=tk.LEFT, padx=(4, 12))

        ttk.Label(top, text="Offset (hex):").pack(side=tk.LEFT)
        self.hist_offset = tk.StringVar(value="1A")
        ttk.Entry(top, textvariable=self.hist_offset, width=5).pack(
            side=tk.LEFT, padx=(4, 12))

        ttk.Label(top, text="Mask (hex):").pack(side=tk.LEFT)
        self.hist_mask = tk.StringVar(value="FF")
        ttk.Entry(top, textvariable=self.hist_mask, width=5).pack(
            side=tk.LEFT, padx=(4, 12))

        ttk.Button(top, text="Compute",
                   command=self._compute_histogram).pack(side=tk.LEFT, padx=4)

        self.hist_info = ttk.Label(frame, text="", foreground=PAL["fg_label"])
        self.hist_info.pack(anchor="w", padx=6, pady=(0, 4))

        cols = ("value_dec", "value_hex", "value_bin", "count", "pct")
        self.hist_tree = ttk.Treeview(frame, columns=cols, show="headings")
        for c, txt, w, anc in [
            ("value_dec", "Value (dec)", 90, "e"),
            ("value_hex", "Hex", 70, "e"),
            ("value_bin", "Bin", 100, "e"),
            ("count", "Count", 80, "e"),
            ("pct", "Percent", 80, "e"),
        ]:
            self.hist_tree.heading(c, text=txt)
            self.hist_tree.column(c, width=w, anchor=anc)
        sb = ttk.Scrollbar(frame, orient=tk.VERTICAL,
                           command=self.hist_tree.yview)
        self.hist_tree.configure(yscrollcommand=sb.set)
        self.hist_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True,
                            padx=(4, 0), pady=(0, 4))
        sb.pack(side=tk.LEFT, fill=tk.Y, padx=(0, 4), pady=(0, 4))

    def _parse_hex(self, s: str, ceiling: int) -> int | None:
        try:
            v = int(s, 16)
        except ValueError:
            return None
        return v if 0 <= v <= ceiling else None

    def _compute_histogram(self):
        offset = self._parse_hex(self.hist_offset.get(), RECORD_SIZE - 1)
        mask = self._parse_hex(self.hist_mask.get(), 0xFF)
        if offset is None or mask is None:
            messagebox.showerror("Bad input",
                                 "Offset must be 0x00–0x29, mask 0x00–0xFF.",
                                 parent=self)
            return
        predicate = BYTE_PRESETS[self.hist_preset.get()]
        players = [p for p in self.slot.players if predicate(p)]
        hist = workbench.byte_histogram(players, offset, mask)
        total = sum(hist.values())

        name, sub, size = field_at_offset(offset)
        loc = f"0x{offset:02X} = {name}" + (f"[{sub}/{size}]" if size > 1 else "")
        notes = {o: n for o, _, _, n in FIELD_LAYOUT}
        note = notes.get(offset, "") if sub == 0 else ""
        mask_label = f" · mask 0x{mask:02X}" if mask != 0xFF else ""
        self.hist_info.config(
            text=f"{loc}{mask_label} · {total} players" + (f" — {note}" if note else "")
        )

        self.hist_tree.delete(*self.hist_tree.get_children())
        for v, c in hist.most_common():
            pct = 100.0 * c / total if total else 0.0
            self.hist_tree.insert("", "end", values=(
                v, f"0x{v:02X}", f"{v:08b}", c, f"{pct:.1f}%",
            ))

    # ── Diff ──────────────────────────────────────────────────

    def _build_diff_tab(self, nb):
        frame = ttk.Frame(nb)
        nb.add(frame, text="Diff")

        top = ttk.Frame(frame)
        top.pack(fill=tk.X, padx=4, pady=(4, 6))

        ttk.Label(top, text="Set A:").pack(side=tk.LEFT)
        self.diff_a = tk.StringVar(value="On transfer list")
        ttk.Combobox(top, textvariable=self.diff_a, values=list(BYTE_PRESETS),
                     state="readonly", width=22).pack(side=tk.LEFT, padx=(4, 12))

        ttk.Label(top, text="Set B:").pack(side=tk.LEFT)
        self.diff_b = tk.StringVar(value="Not on transfer list")
        ttk.Combobox(top, textvariable=self.diff_b, values=list(BYTE_PRESETS),
                     state="readonly", width=22).pack(side=tk.LEFT, padx=(4, 12))

        ttk.Label(top, text="Top:").pack(side=tk.LEFT)
        self.diff_top = tk.IntVar(value=20)
        ttk.Spinbox(top, from_=5, to=60, textvariable=self.diff_top,
                    width=5).pack(side=tk.LEFT, padx=(4, 12))

        ttk.Button(top, text="Compute",
                   command=self._compute_diff).pack(side=tk.LEFT, padx=4)

        self.diff_info = ttk.Label(frame, text="", foreground=PAL["fg_label"])
        self.diff_info.pack(anchor="w", padx=6, pady=(0, 4))

        cols = ("offset", "field", "bit", "p_a", "p_b", "delta")
        self.diff_tree = ttk.Treeview(frame, columns=cols, show="headings")
        for c, txt, w, anc in [
            ("offset", "Offset", 70, "e"),
            ("field", "Field", 200, "w"),
            ("bit", "Bit", 100, "e"),
            ("p_a", "P(A)", 85, "e"),
            ("p_b", "P(B)", 85, "e"),
            ("delta", "|ΔP|", 85, "e"),
        ]:
            self.diff_tree.heading(c, text=txt)
            self.diff_tree.column(c, width=w, anchor=anc)
        sb = ttk.Scrollbar(frame, orient=tk.VERTICAL,
                           command=self.diff_tree.yview)
        self.diff_tree.configure(yscrollcommand=sb.set)
        self.diff_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True,
                            padx=(4, 0), pady=(0, 4))
        sb.pack(side=tk.LEFT, fill=tk.Y, padx=(0, 4), pady=(0, 4))

    def _compute_diff(self):
        pred_a = BYTE_PRESETS[self.diff_a.get()]
        pred_b = BYTE_PRESETS[self.diff_b.get()]
        a = [p for p in self.slot.players if pred_a(p)]
        b = [p for p in self.slot.players if pred_b(p)]
        self.diff_info.config(
            text=f"A = {self.diff_a.get()} ({len(a)}) · "
                 f"B = {self.diff_b.get()} ({len(b)})"
        )
        self.diff_tree.delete(*self.diff_tree.get_children())
        if not a or not b:
            return
        try:
            top_n = max(1, int(self.diff_top.get()))
        except (tk.TclError, ValueError):
            top_n = 20
        for d in workbench.diff_sets(a, b, top_n=top_n):
            field = d.field_name + (f"[{d.field_byte}]" if d.field_byte > 0 else "")
            self.diff_tree.insert("", "end", values=(
                f"0x{d.offset:02X}",
                field,
                f"{d.bit_index} (0x{d.bit:02X})",
                f"{d.p_a*100:.1f}%",
                f"{d.p_b*100:.1f}%",
                f"{d.delta*100:.1f}%",
            ))
