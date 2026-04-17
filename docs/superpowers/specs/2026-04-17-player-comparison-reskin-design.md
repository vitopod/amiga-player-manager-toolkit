# Design Spec: Player Comparison Window + Full GUI Reskin
**Date:** 2026-04-17  
**Status:** Approved  
**Scope:** `PMSaveDiskTool_v2/pm_gui.py` only — zero new files, zero new dependencies

---

## 1. Goals

1. Add a **Compare Players** window that shows a radar chart + skill bars for any two players side-by-side.
2. Reskin the **entire main GUI** with a visual identity inspired by the original Player Manager (Amiga) game: deep navy, amber data text, cyan accents, green action bar.

Both goals are implemented together because the Compare window's canvas palette and the main window's theme share the same `PAL` dict — designing them separately would require rework.

---

## 2. Colour Palette (`PAL`)

A single dict at module level in `pm_gui.py`. Every colour reference in the file uses a key from this dict — no hex literals elsewhere.

| Key | Hex | Usage |
|-----|-----|-------|
| `bg` | `#000066` | Main window/pane background |
| `bg_mid` | `#111188` | Toolbar, selector rows, identity header |
| `bg_header` | `#3355aa` | Title bands (app header, window headers, tree headings) |
| `fg_title` | `#00ddff` | Cyan — window/band titles, Player A accent |
| `fg_data` | `#ffcc00` | Amber — all data values, skill numbers, player names |
| `fg_label` | `#7799cc` | Muted blue — secondary labels, column headers |
| `fg_dim` | `#445588` | Dimmed — IDs, inactive text |
| `player_a` | `#44ccff` | Player A radar polygon stroke + bar fills |
| `player_b` | `#ff6666` | Player B radar polygon stroke + bar fills |
| `player_a_stipple` | `"gray25"` | Stipple pattern for Player A polygon fill — approximates transparency |
| `player_b_stipple` | `"gray25"` | Stipple pattern for Player B polygon fill |
| `free_agent` | `#44cc44` | Green — free agent names in player list |
| `btn_go` | `#006600` | Green — action button / footer bar background |
| `btn_go_fg` | `#44ff44` | Bright green — text on green action buttons |
| `selected` | `#3344aa` | Selected row / active tab background |
| `border` | `#2244aa` | Widget borders, separators |

**Note on transparency:** `tk.Canvas` does not support alpha fills natively. Player radar polygons use `stipple="gray25"` with the solid colour to approximate translucency.

---

## 3. Theme System

### 3.1 `apply_theme(root)`

Called once at `PMSaveDiskToolGUI.__init__` before any widgets are built. Configures `ttk.Style` globally:

| Widget | Property | Value |
|--------|----------|-------|
| `TFrame` | background | `PAL["bg"]` |
| `TLabel` | background / foreground | `PAL["bg"]` / `PAL["fg_data"]` |
| `TButton` | background / foreground | `PAL["bg_mid"]` / `PAL["fg_data"]` |
| `TEntry` | fieldbackground / foreground | `#000044` / `PAL["fg_data"]` |
| `TCombobox` | fieldbackground / foreground | `#000044` / `PAL["fg_data"]` |
| `Treeview` | background / foreground / fieldbackground | `PAL["bg"]` / `PAL["fg_data"]` / `PAL["bg"]` |
| `Treeview` (selected) | background / foreground | `PAL["selected"]` / `#ffffff` |
| `Treeview.Heading` | background / foreground | `PAL["bg_header"]` / `PAL["fg_title"]` |
| `TNotebook` | background | `PAL["bg"]` |
| `TNotebook.Tab` | background / foreground | `PAL["bg_mid"]` / `PAL["fg_dim"]` |
| `TNotebook.Tab` (selected) | background / foreground | `PAL["bg"]` / `PAL["fg_data"]` |
| `TSeparator` | background | `PAL["border"]` |

OS window chrome (title bar, scrollbar arrows on macOS) remains native — unavoidable.

### 3.2 App title band

A `tk.Label` packed at the very top of the root window (above the native menu bar area), styled with `bg=PAL["bg_header"]`, `fg=PAL["fg_title"]`, monospace bold, all-caps: **"PLAYER MANAGER TOOLKIT"**. Right-aligned: current ADF filename + slot name.

### 3.3 Skills tab enhancement

The existing Skills tab spinboxes stay (edit behaviour unchanged). Each spinbox is preceded by a `tk.Canvas` mini-bar (height 6px) that fills proportionally to the skill value / 99. Redraws whenever `_load_player_detail` is called and also on each spinbox `<<Increment>>`/`<<Decrement>>`/`<KeyRelease>` event so the bar tracks live edits.

### 3.4 Footer bar

The existing Apply/Revert footer frame gets `bg=PAL["btn_go"]`. The Apply button: `bg=PAL["btn_go"]`, `fg=PAL["btn_go_fg"]`, bold. Revert button: `bg=PAL["bg_mid"]`, `fg=PAL["fg_dim"]`.

### 3.5 Free agent colouring in tree

`_refresh_player_list` applies a `"free"` tag to free-agent rows. `self.tree.tag_configure("free", foreground=PAL["free_agent"])`.

---

## 4. Main Window — Structural Changes Summary

No layout changes. Only colour/font changes applied via `apply_theme` + explicit `bg`/`fg` on raw `tk` widgets:

- Root window: `root.configure(bg=PAL["bg"])`
- Title band: new `tk.Label` at top
- Toolbar frame: `bg=PAL["bg_mid"]`
- Player list frame: `bg=PAL["bg"]`
- Detail pane frame: `bg=PAL["bg"]`
- Identity header frame: `bg=PAL["bg_mid"]`
- Status bar: `bg="#000033"`, `fg=PAL["fg_dim"]`

All existing accelerators, menu structure, dirty-state logic, backup behaviour, and edit flow are unchanged.

---

## 5. `PlayerCompareWindow`

### 5.1 Class signature

```python
class PlayerCompareWindow(tk.Toplevel):
    def __init__(self, parent, slot: SaveSlot, game_disk: GameDisk | None, player_a: PlayerRecord | None = None):
```

Window title: `"Compare Players"`. Initial geometry: `760×560`. Minimum: `640×480`.

### 5.2 Layout

```
┌─ COMPARE PLAYERS ─────────────────────── [title band: bg_header / fg_title] ──┐
│ [Player A header — read-only]  ⇄  [Team combo]  [Player B combo]              │  ← selector row (bg_mid)
├────────────────────────────────────────────────────────────────────────────────┤
│  [Radar Canvas 300×280 bg=#000055]  │  [Bars Canvas 340×280 bg=bg]            │  ← main body
├────────────────────────────────────────────────────────────────────────────────┤
│  ● Player A name            ● Player B name                                    │  ← legend row
├────────────────────────────────────────────────────────────────────────────────┤
│  A leads on N/10 skills                                          [DONE]         │  ← bottom bar (btn_go)
└────────────────────────────────────────────────────────────────────────────────┘
```

### 5.3 Selector row

- **Player A** — `tk.Label` widgets showing name, position, age, team, total skill. Read-only. Set at construction from `player_a`; updated by swap.
- **⇄ swap button** — calls `_swap()`: exchanges the two `PlayerRecord` references, refreshes player A labels, redraws.
- **Team combo** — `ttk.Combobox` (readonly). Values: `["★ Free Agents"] + sorted(slot.team_names[1:])`. Selecting triggers `_on_team_selected`.
- **Player B combo** — `ttk.Combobox` (readonly). Values: players in selected team, formatted as `"Name (ID)"` if game disk loaded, else `"#NNN"`. Selecting triggers `_draw`.

Both combos are disabled until `slot` is loaded (always true since window only opens from a loaded ADF).

### 5.4 Radar canvas (`tk.Canvas`)

Drawn by `_draw_radar(canvas, player_a, player_b)`:

1. `canvas.delete("all")`
2. Four concentric grid polygons at 25/50/75/100% — `outline=PAL["border"]`, `fill=""` (outermost: `fill=PAL["bg"]` tinted)
3. Ten spokes — `create_line`, colour `PAL["border"]`
4. Ten axis labels — `create_text`, `fill=PAL["fg_data"]`, font `("Courier New", 8)`, all-caps skill names
5. Player B polygon — drawn first (behind): `create_polygon`, `outline=PAL["player_b"]`, `stipple="gray25"`, `fill=PAL["player_b"]`
6. Player A polygon — drawn second (front): same with `player_a` colours
7. Dots at each vertex for both players — `create_oval`, radius 3

Axis order (clockwise from top): Stamina · Resilience · Pace · Agility · Aggression · Flair · Passing · Shooting · Tackling · Keeping

### 5.5 Bars canvas (`tk.Canvas`)

Drawn by `_draw_bars(canvas, player_a, player_b)`:

1. `canvas.delete("all")`
2. For each of the 10 skills, one row containing:
   - Value A (text, bright if winner, dim if not)
   - Bar track A (rectangle, fills right-to-left proportional to value/99)
   - Skill name label (centred, `fg_label`, uppercase, truncated to 7 chars)
   - Bar track B (fills left-to-right)
   - Value B
3. All drawn with `create_rectangle` / `create_text` — no widgets, pure canvas

### 5.6 Bottom bar

- Status text: `"A leads on N/10 skills"` / `"B leads on N/10 skills"` / `"Tied"` — recomputed in `_update_status`
- DONE button: `tk.Button`, `bg=PAL["btn_go"]`, `fg=PAL["btn_go_fg"]`, command `self.destroy`

### 5.7 `_draw()` — master redraw

Called whenever player B changes or swap occurs:
```python
def _draw(self):
    if not (self._player_a and self._player_b):
        return
    self._draw_radar(self._radar_canvas, self._player_a, self._player_b)
    self._draw_bars(self._bars_canvas, self._player_a, self._player_b)
    self._update_status()
```

### 5.8 `set_player_a(player)`

Public method — called by `PMSaveDiskToolGUI._open_compare` when the window is already open and the user right-clicks a new player. Updates player A labels and calls `_draw()` if player B is also set.

---

## 6. Integration in `PMSaveDiskToolGUI`

### 6.1 Tools menu

```
Career Tracker…       Cmd+T
Byte Workbench…       Cmd+B
Line-up Coach (BETA)… Cmd+L
Compare Players…      Cmd+P      ← new
```

### 6.2 `_open_compare(player=None)`

```python
def _open_compare(self, player=None):
    if hasattr(self, '_compare_win') and self._compare_win.winfo_exists():
        self._compare_win.lift()
        if player:
            self._compare_win.set_player_a(player)
    else:
        self._compare_win = PlayerCompareWindow(
            self.root, self.slot, self.game_disk, player_a=player
        )
```

Disabled (menu item greyed) when no ADF is loaded.

### 6.3 Right-click context menu on player list

```python
self.tree.bind("<Button-2>", self._on_tree_right_click)   # macOS
self.tree.bind("<Button-3>", self._on_tree_right_click)   # Windows/Linux
```

`_on_tree_right_click` selects the row under cursor, builds a `tk.Menu` with a single item **"Send to Compare…"** (plus a separator and **"Copy ID"** for future use), posts it, and calls `_open_compare(player)` on selection.

---

## 7. What Is Not Changing

- File format, ADF parsing, player serialisation — untouched
- All existing keyboard shortcuts and menu structure (except adding Compare Players)
- Dirty state, Apply/Revert, backup-on-first-write logic
- Career Tracker, Byte Workbench, Line-up Coach windows — they gain the theme automatically via `apply_theme`, no internal changes needed
- CLI — unaffected
- Tests — unaffected (GUI is not tested; no new public API in `pm_core`)

---

## 8. Constraints

- Zero external dependencies — radar and bars drawn with `tk.Canvas` primitives only
- Python 3.10+ (existing constraint)
- `ttk.Style` alpha transparency not supported — use `stipple="gray25"` for radar polygon fills
- OS window chrome stays native on all platforms

---

## 9. Splash Screen

### 9.1 Asset

`Loading_IMG.jpg` (already in repo root) is converted once to `Loading_IMG.png` and committed alongside it. `tk.PhotoImage` supports PNG natively in Tk 8.6+ (Python 3.x standard) — no external libraries needed. The JPG is kept as the authoritative source; the PNG is the runtime asset.

### 9.2 Behaviour

- On launch, before `PMSaveDiskToolGUI.__init__`, a `_SplashScreen` function (or small class) runs:
  1. `root.withdraw()` — main window invisible
  2. Create borderless `tk.Toplevel` (`overrideredirect(True)`)
  3. Load `Loading_IMG.png` via `tk.PhotoImage`, display in a `tk.Label` filling the toplevel
  4. Centre the toplevel on screen using `winfo_screenwidth/height`
  5. `root.after(3000, _dismiss)` — after 3 s, destroy toplevel + `root.deiconify()`
  6. Bind `<Button-1>` and `<Key>` on the splash to also call `_dismiss` (early exit on click/keypress)

### 9.3 Theming

The splash is shown **before** `apply_theme` runs — it is intentionally raw: just the image, no chrome, no palette applied. The first themed surface the user sees is the main window appearing after the splash dismisses.

### 9.4 Constraints

- PNG must live in the same directory as `pm_gui.py` (`PMSaveDiskTool_v2/`)
- If the file is missing at runtime, splash is skipped silently (no crash) — a `try/except` guards the `PhotoImage` load

---

## 10. Out of Scope

- Comparing players across different save slots or ADFs (Career Tracker covers cross-slot diffs)
- Saving/exporting a comparison as an image or CSV
- Animated transitions
- Internationalisation (UI stays English for now)
