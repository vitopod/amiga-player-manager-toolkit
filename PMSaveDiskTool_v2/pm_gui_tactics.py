"""Tactic Editor — drag shirts 2..11 on a pitch diagram per pitch zone.

Thin Tkinter wrapper over :mod:`pm_core.tactics`. Lets the user pick a `.tac`
file on the loaded ADF, cycle through the 20 pitch zones, and drag shirts to
new (x, y) positions. Save writes through ``adf.write_at`` and creates the
usual sibling ``.bak`` via :func:`pm_core.adf.ensure_backup`.

The pitch is drawn procedurally — no sprite image needed. World coordinates
map linearly to canvas pixels; zone geometry is only approximate, since the
original Anco / Dino Dini match engine's exact world bounds aren't published.
Position accuracy for editing is not affected: what you drag is what gets
written byte-for-byte.
"""

import os
import tkinter as tk
from tkinter import ttk, messagebox

from pm_core.adf import ADF, ensure_backup
from pm_core import tactics

from pm_gui_theme import PAL
from pm_gui_help import help_button


# World coordinate bounds (slightly padded vs the empirical max of ~900 × ~1400
# seen in PM tactics). The world is stored portrait in .tac — we display it
# landscape (90° CCW) because it's friendlier to vertical screen space.
_WORLD_W = 1024
_WORLD_H = 1536
_CANVAS_W = 660
_CANVAS_H = 440
_SHIRT_RADIUS = 14


def _grid_box(col: int, row: int) -> tuple[int, int, int, int]:
    """World-coordinate rect for one cell of the 3 × 4 `areaN` grid."""
    cw, ch = _WORLD_W // 3, _WORLD_H // 4
    return (col * cw, row * ch, (col + 1) * cw, (row + 1) * ch)


# Approximate pitch regions each zone represents (derived from centroid
# analysis of PM's 4-2-4.tac — area1..12 form a 3-column × 4-row grid, with
# the named zones covering goal area, centre circle, and corner regions).
_ZONE_BOXES: dict[str, tuple[int, int, int, int]] = {
    # Column 0 (left), rows 0..3 top→bottom.
    "area1":  _grid_box(0, 0), "area2":  _grid_box(0, 1),
    "area3":  _grid_box(0, 2), "area4":  _grid_box(0, 3),
    # Column 1 (middle).
    "area5":  _grid_box(1, 0), "area6":  _grid_box(1, 1),
    "area7":  _grid_box(1, 2), "area8":  _grid_box(1, 3),
    # Column 2 (right).
    "area9":  _grid_box(2, 0), "area10": _grid_box(2, 1),
    "area11": _grid_box(2, 2), "area12": _grid_box(2, 3),
    # Kickoff: centre circle region.
    "kickoff_own": (_WORLD_W // 3, _WORLD_H * 3 // 8,
                    _WORLD_W * 2 // 3, _WORLD_H * 5 // 8),
    "kickoff_def": (_WORLD_W // 3, _WORLD_H * 3 // 8,
                    _WORLD_W * 2 // 3, _WORLD_H * 5 // 8),
    # Goal-kick: the penalty box at each end.
    "goalkick_def": (_WORLD_W // 4, 0, _WORLD_W * 3 // 4, _WORLD_H // 7),
    "goalkick_own": (_WORLD_W // 4, _WORLD_H * 6 // 7,
                     _WORLD_W * 3 // 4, _WORLD_H),
    # Corners: small boxes in each pitch corner.
    "corner1": (0, 0, _WORLD_W // 5, _WORLD_H // 8),
    "corner3": (_WORLD_W * 4 // 5, 0, _WORLD_W, _WORLD_H // 8),
    "corner2": (0, _WORLD_H * 7 // 8, _WORLD_W // 5, _WORLD_H),
    "corner4": (_WORLD_W * 4 // 5, _WORLD_H * 7 // 8, _WORLD_W, _WORLD_H),
}


class TacticEditorWindow(tk.Toplevel):
    """Pitch-zone editor for PM `.tac` files.

    Reads tactics from an open ADF, allows drag editing of shirt positions
    per zone, and writes the edited tactic back through the ADF (backup +
    `adf.save`). Never touches the trailer bytes — only the 800-byte
    positional payload is mutated.
    """

    def __init__(self, parent, adf: ADF, adf_path: str, on_saved=None):
        super().__init__(parent)
        self.title("Tactic Editor")
        self.geometry("760x600")
        self.minsize(720, 560)

        self.adf = adf
        self.adf_path = adf_path
        self.on_saved = on_saved
        self.tactic: tactics.Tactic | None = None
        self.tac_name: str | None = None
        self.tac_entry = None
        self.tac_original: bytes | None = None
        self.current_zone = tactics.ZONE_NAMES[0]
        self.dirty = False

        # Canvas item ids for each shirt (circle, text).
        self.shirt_items: dict[int, tuple[int, int]] = {}
        self._drag_shirt: int | None = None
        self._drag_offset: tuple[int, int] = (0, 0)

        self._build_ui()
        self._refresh_file_list()

    # ── UI construction ───────────────────────────────────────

    def _build_ui(self):
        header = ttk.Frame(self, padding=(8, 8, 8, 4))
        header.pack(fill=tk.X)
        ttk.Label(header, text="Tactic Editor",
                  font=("TkDefaultFont", 13, "bold")).pack(side=tk.LEFT)
        help_button(header, "tactic_editor").pack(side=tk.RIGHT)

        ctrl = ttk.Frame(self, padding=(8, 4))
        ctrl.pack(fill=tk.X)

        ttk.Label(ctrl, text="File:").pack(side=tk.LEFT)
        self.file_var = tk.StringVar()
        self.file_cb = ttk.Combobox(ctrl, textvariable=self.file_var,
                                    state="readonly", width=14)
        self.file_cb.pack(side=tk.LEFT, padx=(4, 12))
        self.file_cb.bind("<<ComboboxSelected>>", self._on_file_selected)

        ttk.Label(ctrl, text="Zone:").pack(side=tk.LEFT)
        self.zone_var = tk.StringVar(value=self.current_zone)
        self.zone_cb = ttk.Combobox(ctrl, textvariable=self.zone_var,
                                    values=list(tactics.ZONE_NAMES),
                                    state="readonly", width=14)
        self.zone_cb.pack(side=tk.LEFT, padx=(4, 12))
        self.zone_cb.bind("<<ComboboxSelected>>", self._on_zone_selected)

        ttk.Button(ctrl, text="Revert zone",
                   command=self._revert_current_zone).pack(side=tk.LEFT)

        # Pack the footer and description BEFORE the canvas so they're always
        # visible even when the canvas's natural height pushes past the window
        # bounds — tkinter gives `side=BOTTOM` children their space first.
        footer = ttk.Frame(self, padding=(8, 6))
        footer.pack(fill=tk.X, side=tk.BOTTOM)
        self.status_var = tk.StringVar(value="")
        ttk.Label(footer, textvariable=self.status_var,
                  foreground=PAL["fg_label"]).pack(side=tk.LEFT)
        ttk.Button(footer, text="Save to ADF",
                   command=self._save).pack(side=tk.RIGHT, padx=(4, 0))
        ttk.Button(footer, text="Revert file",
                   command=self._revert_file).pack(side=tk.RIGHT)

        self.desc_var = tk.StringVar(value="")
        desc = ttk.Label(self, textvariable=self.desc_var,
                         foreground=PAL["fg_label"], wraplength=720,
                         justify=tk.LEFT)
        desc.pack(fill=tk.X, side=tk.BOTTOM, padx=10)

        self.canvas = tk.Canvas(
            self, width=_CANVAS_W, height=_CANVAS_H,
            bg="#2f6a38", highlightthickness=1,
            highlightbackground=PAL["fg_label"],
        )
        self.canvas.pack(padx=10, pady=8)
        self.canvas.bind("<ButtonPress-1>", self._on_mouse_down)
        self.canvas.bind("<B1-Motion>", self._on_mouse_drag)
        self.canvas.bind("<ButtonRelease-1>", self._on_mouse_up)

    # ── File / zone selection ─────────────────────────────────

    def _refresh_file_list(self):
        tac_names = [e.name for e in self.adf.list_files()
                     if e.name.lower().endswith(".tac")]
        if not tac_names:
            self.file_cb.config(values=[])
            self.status_var.set("No .tac files on this disk.")
            return
        self.file_cb.config(values=tac_names)
        self.file_var.set(tac_names[0])
        self._load_tac(tac_names[0])

    def _on_file_selected(self, _event=None):
        name = self.file_var.get()
        if not name:
            return
        if self.dirty and not messagebox.askyesno(
            "Discard changes?",
            f"Unsaved edits to {self.tac_name}. Discard and load {name}?",
            parent=self,
        ):
            if self.tac_name:
                self.file_var.set(self.tac_name)
            return
        self._load_tac(name)

    def _on_zone_selected(self, _event=None):
        zone = self.zone_var.get()
        if zone in tactics.ZONE_NAMES:
            self.current_zone = zone
            self._draw_pitch()

    # ── Load / save ───────────────────────────────────────────

    def _load_tac(self, name: str):
        entry = self.adf.find_file(name)
        buf = self.adf.read_at(entry.byte_offset, entry.size)
        self.tac_entry = entry
        self.tac_name = name
        self.tac_original = buf
        self.tactic = tactics.parse_tac(buf)
        self._set_dirty(False)
        self._update_description()
        self._draw_pitch()

    def _revert_current_zone(self):
        if self.tactic is None or self.tac_original is None:
            return
        fresh = tactics.parse_tac(self.tac_original)
        self.tactic.positions[self.current_zone] = fresh.positions[self.current_zone]
        self._set_dirty(self._has_any_diff())
        self._draw_pitch()

    def _revert_file(self):
        if self.tac_original is None or not self.dirty:
            return
        if not messagebox.askyesno(
            "Revert?", f"Discard all unsaved edits to {self.tac_name}?",
            parent=self,
        ):
            return
        self.tactic = tactics.parse_tac(self.tac_original)
        self._set_dirty(False)
        self._draw_pitch()

    def _save(self):
        if self.tactic is None or self.tac_entry is None:
            return
        new_buf = tactics.serialize_tac(self.tactic)
        if len(new_buf) != self.tac_entry.size:
            messagebox.showerror(
                "Size mismatch",
                f"Serialized tactic is {len(new_buf)} bytes but the on-disk entry "
                f"is {self.tac_entry.size}. Aborting.",
                parent=self,
            )
            return
        try:
            bak = ensure_backup(self.adf_path)
            self.adf.write_at(self.tac_entry.byte_offset, new_buf)
            self.adf.save(self.adf_path)
        except OSError as exc:
            messagebox.showerror("Save failed", str(exc), parent=self)
            return

        self.tac_original = new_buf
        self._set_dirty(False)
        msg = f"Saved {self.tac_name}"
        if bak:
            msg += f" (backup: {os.path.basename(bak)})"
        self.status_var.set(msg)
        if callable(self.on_saved):
            self.on_saved()

    def _has_any_diff(self) -> bool:
        if self.tactic is None or self.tac_original is None:
            return False
        return tactics.serialize_tac(self.tactic) != self.tac_original

    def _set_dirty(self, dirty: bool):
        self.dirty = dirty
        mark = "•" if dirty else ""
        name = self.tac_name or "—"
        self.title(f"Tactic Editor — {name} {mark}".rstrip())

    def _update_description(self):
        if self.tactic is None:
            self.desc_var.set("")
            return
        desc = self.tactic.description
        size = self.tactic.total_size
        if desc:
            self.desc_var.set(f"Description: {desc}    ({size} bytes)")
        else:
            self.desc_var.set(f"(no description — {size}-byte tactic)")

    # ── Canvas drawing + drag ─────────────────────────────────

    def _world_to_canvas(self, x: int, y: int) -> tuple[int, int]:
        # 90° CCW rotation: world y → canvas x, world x → canvas y.
        cx = round(y * _CANVAS_W / _WORLD_H)
        cy = round(x * _CANVAS_H / _WORLD_W)
        return cx, cy

    def _canvas_to_world(self, cx: int, cy: int) -> tuple[int, int]:
        y = round(cx * _WORLD_H / _CANVAS_W)
        x = round(cy * _WORLD_W / _CANVAS_H)
        x = max(0, min(_WORLD_W - 1, x))
        y = max(0, min(_WORLD_H - 1, y))
        return x, y

    def _draw_pitch(self):
        self.canvas.delete("all")
        self.shirt_items.clear()

        # Touchlines + halfway line + centre circle + penalty/goal areas
        # (landscape: halfway line is vertical, penalty boxes at left/right).
        line = "#e8e8e8"
        w, h = _CANVAS_W, _CANVAS_H
        self.canvas.create_rectangle(1, 1, w - 1, h - 1, outline=line, width=2)
        self.canvas.create_line(w // 2, 0, w // 2, h, fill=line, width=1)
        cr = 45
        self.canvas.create_oval(w // 2 - cr, h // 2 - cr,
                                w // 2 + cr, h // 2 + cr,
                                outline=line, width=1)
        # Left and right penalty boxes.
        pw, ph = int(w * 0.14), int(h * 0.5)
        self.canvas.create_rectangle(0, (h - ph) // 2,
                                     pw, (h + ph) // 2,
                                     outline=line, width=1)
        self.canvas.create_rectangle(w - pw, (h - ph) // 2,
                                     w, (h + ph) // 2,
                                     outline=line, width=1)
        gw, gh = int(w * 0.06), int(h * 0.25)
        self.canvas.create_rectangle(0, (h - gh) // 2,
                                     gw, (h + gh) // 2,
                                     outline=line, width=1)
        self.canvas.create_rectangle(w - gw, (h - gh) // 2,
                                     w, (h + gh) // 2,
                                     outline=line, width=1)

        # Highlight the on-pitch region this zone represents.
        box = _ZONE_BOXES.get(self.current_zone)
        if box:
            x0, y0 = self._world_to_canvas(box[0], box[1])
            x1, y1 = self._world_to_canvas(box[2], box[3])
            self.canvas.create_rectangle(
                x0, y0, x1, y1,
                fill="#f0e4a1", stipple="gray25",
                outline="#f0e4a1", width=2,
            )

        # Zone label top-left.
        self.canvas.create_text(8, 8, anchor=tk.NW, fill=line,
                                text=f"zone: {self.current_zone}",
                                font=("TkDefaultFont", 10, "bold"))

        if self.tactic is None:
            return

        positions = self.tactic.positions[self.current_zone]
        for shirt in tactics.SHIRT_NUMBERS:
            x, y = positions[shirt]
            cx, cy = self._world_to_canvas(x, y)
            r = _SHIRT_RADIUS
            oval = self.canvas.create_oval(
                cx - r, cy - r, cx + r, cy + r,
                fill="#f0e4a1", outline="#222", width=2,
                tags=(f"shirt-{shirt}", "shirt"),
            )
            text = self.canvas.create_text(
                cx, cy, text=str(shirt),
                fill="#222", font=("TkDefaultFont", 10, "bold"),
                tags=(f"shirt-{shirt}", "shirt"),
            )
            self.shirt_items[shirt] = (oval, text)

    def _shirt_at(self, cx: int, cy: int) -> int | None:
        for shirt, (oval, _) in self.shirt_items.items():
            x0, y0, x1, y1 = self.canvas.coords(oval)
            if x0 <= cx <= x1 and y0 <= cy <= y1:
                return shirt
        return None

    def _on_mouse_down(self, event):
        shirt = self._shirt_at(event.x, event.y)
        if shirt is None:
            return
        self._drag_shirt = shirt
        oval, _ = self.shirt_items[shirt]
        x0, y0, x1, y1 = self.canvas.coords(oval)
        self._drag_offset = (event.x - (x0 + x1) / 2,
                             event.y - (y0 + y1) / 2)

    def _on_mouse_drag(self, event):
        if self._drag_shirt is None:
            return
        cx = event.x - self._drag_offset[0]
        cy = event.y - self._drag_offset[1]
        cx = max(_SHIRT_RADIUS, min(_CANVAS_W - _SHIRT_RADIUS, cx))
        cy = max(_SHIRT_RADIUS, min(_CANVAS_H - _SHIRT_RADIUS, cy))
        oval, text = self.shirt_items[self._drag_shirt]
        r = _SHIRT_RADIUS
        self.canvas.coords(oval, cx - r, cy - r, cx + r, cy + r)
        self.canvas.coords(text, cx, cy)

    def _on_mouse_up(self, _event):
        if self._drag_shirt is None or self.tactic is None:
            self._drag_shirt = None
            return
        oval, _ = self.shirt_items[self._drag_shirt]
        x0, y0, x1, y1 = self.canvas.coords(oval)
        cx, cy = (x0 + x1) / 2, (y0 + y1) / 2
        world = self._canvas_to_world(int(cx), int(cy))
        self.tactic.positions[self.current_zone][self._drag_shirt] = world
        self._drag_shirt = None
        self._set_dirty(self._has_any_diff())
