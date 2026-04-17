# Player Comparison Window + GUI Reskin — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Reskin the entire GUI with a Player Manager–inspired navy/amber/cyan palette, add a splash screen, and add a `PlayerCompareWindow` with radar chart and skill bars.

**Architecture:** All changes live in `PMSaveDiskTool_v2/pm_gui.py`. A `PAL` dict at module level is the single palette source of truth. `apply_theme(root)` configures `ttk.Style` globally once at startup. `PlayerCompareWindow` is a new `tk.Toplevel` class following the existing pattern of `CareerTrackerWindow`.

**Tech Stack:** Python 3.10+, tkinter stdlib only (`tk`, `ttk`), `tk.Canvas` for all custom drawing. Zero new external dependencies.

---

## File Map

| File | Change |
|------|--------|
| `PMSaveDiskTool_v2/pm_gui.py` | All changes: PAL, apply_theme, splash, title band, tree tags, skills bars, PlayerCompareWindow, menu/right-click wiring |
| `PMSaveDiskTool_v2/Loading_IMG.png` | Already committed — no changes needed |

---

## Task 1: PAL dict + apply_theme()

**Files:**
- Modify: `PMSaveDiskTool_v2/pm_gui.py` — add after line 66 (after `GITHUB_URL = ...`), add `apply_theme` function before the `CareerTrackerWindow` class, call in `PMSaveDiskToolGUI.__init__`

- [ ] **Step 1: Add the PAL dict after the existing module constants**

Insert after the `GITHUB_URL` / `LICENSE_URL` lines (after line ~66):

```python
PAL = {
    "bg":         "#000066",
    "bg_mid":     "#111188",
    "bg_header":  "#3355aa",
    "fg_title":   "#00ddff",
    "fg_data":    "#ffcc00",
    "fg_label":   "#7799cc",
    "fg_dim":     "#445588",
    "player_a":   "#44ccff",
    "player_b":   "#ff6666",
    "free_agent": "#44cc44",
    "btn_go":     "#006600",
    "btn_go_fg":  "#44ff44",
    "selected":   "#3344aa",
    "border":     "#2244aa",
}
```

- [ ] **Step 2: Add apply_theme() before the CareerTrackerWindow class**

Insert just before `class CareerTrackerWindow`:

```python
def apply_theme(root: tk.Tk) -> None:
    """Configure ttk.Style globally with the Player Manager palette."""
    style = ttk.Style(root)
    # Pick a base theme that allows full colour overrides on all platforms.
    try:
        style.theme_use("clam")
    except tk.TclError:
        pass  # fall back to whatever is available

    bg      = PAL["bg"]
    bg_mid  = PAL["bg_mid"]
    bg_hdr  = PAL["bg_header"]
    fg_data = PAL["fg_data"]
    fg_lbl  = PAL["fg_label"]
    fg_dim  = PAL["fg_dim"]
    sel     = PAL["selected"]
    border  = PAL["border"]

    style.configure("TFrame",        background=bg)
    style.configure("TLabel",        background=bg,     foreground=fg_data)
    style.configure("TButton",       background=bg_mid, foreground=fg_data,
                    relief="flat",   borderwidth=1)
    style.map("TButton",
              background=[("active", sel)],
              foreground=[("active", "#ffffff")])
    style.configure("TEntry",        fieldbackground="#000044", foreground=fg_data,
                    insertcolor=fg_data, bordercolor=border, selectbackground=sel)
    style.configure("TCombobox",     fieldbackground="#000044", foreground=fg_data,
                    selectbackground=sel, arrowcolor=fg_lbl)
    style.map("TCombobox",
              fieldbackground=[("readonly", "#000044")],
              foreground=[("readonly", fg_data)])
    style.configure("Treeview",      background=bg,  foreground=fg_data,
                    fieldbackground=bg, rowheight=20)
    style.map("Treeview",
              background=[("selected", sel)],
              foreground=[("selected", "#ffffff")])
    style.configure("Treeview.Heading", background=bg_hdr, foreground=PAL["fg_title"],
                    relief="flat")
    style.map("Treeview.Heading",
              background=[("active", sel)])
    style.configure("TNotebook",     background=bg, borderwidth=0)
    style.configure("TNotebook.Tab", background=bg_mid, foreground=fg_dim,
                    padding=(8, 3))
    style.map("TNotebook.Tab",
              background=[("selected", bg)],
              foreground=[("selected", fg_data)])
    style.configure("TSeparator",    background=border)
    style.configure("TScrollbar",    background=bg_mid, troughcolor=bg,
                    arrowcolor=fg_lbl, borderwidth=0)

    root.configure(bg=bg)
```

- [ ] **Step 3: Call apply_theme at the top of PMSaveDiskToolGUI.__init__**

Find `def __init__(self, root):` in `PMSaveDiskToolGUI` (around line 732). Add `apply_theme(root)` as the very first line of the method body, before any widget creation:

```python
def __init__(self, root):
    apply_theme(root)          # ← add this line
    self.root = root
    self.root.geometry("1100x700")
    ...
```

- [ ] **Step 4: Visual check — launch the GUI**

```bash
python3 PMSaveDiskTool_v2/pm_gui.py
```

Expected: window opens with navy background throughout — toolbar, menus, tree area, detail pane. Amber text. No layout breakage.

- [ ] **Step 5: Commit**

```bash
git add PMSaveDiskTool_v2/pm_gui.py
git commit -m "feat: add PAL palette and apply_theme() — global GUI reskin"
```

---

## Task 2: Splash Screen

**Files:**
- Modify: `PMSaveDiskTool_v2/pm_gui.py` — add `_show_splash()` function near `main()`, call from `main()`

- [ ] **Step 1: Add _show_splash() just before the main() function (around line 1624)**

```python
def _show_splash(root: tk.Tk) -> None:
    """Show a 3-second borderless splash screen, dismissable on click/key."""
    img_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "Loading_IMG.png")
    try:
        photo = tk.PhotoImage(file=img_path)
    except tk.TclError:
        return  # missing asset — skip splash silently

    splash = tk.Toplevel(root)
    splash.overrideredirect(True)

    w, h = photo.width(), photo.height()
    sw = root.winfo_screenwidth()
    sh = root.winfo_screenheight()
    x = (sw - w) // 2
    y = (sh - h) // 2
    splash.geometry(f"{w}x{h}+{x}+{y}")

    lbl = tk.Label(splash, image=photo, bd=0)
    lbl.pack()
    lbl.image = photo  # prevent GC

    def _dismiss():
        try:
            splash.destroy()
        except tk.TclError:
            pass
        root.deiconify()

    _id = root.after(3000, _dismiss)

    def _early(event=None):
        root.after_cancel(_id)
        _dismiss()

    splash.bind("<Button-1>", _early)
    splash.bind("<Key>", _early)
    splash.focus_set()
```

- [ ] **Step 2: Call _show_splash from main()**

Replace the current `main()` function:

```python
def main():
    root = tk.Tk()
    root.withdraw()          # hide while splash shows
    _show_splash(root)
    apply_theme(root)        # theme before main window builds
    app = PMSaveDiskToolGUI(root)
    root.mainloop()
```

**Note:** Move the `apply_theme(root)` call from `PMSaveDiskToolGUI.__init__` to `main()` so it runs once in the right place. Remove the `apply_theme(root)` line added in Task 1 from `__init__`.

- [ ] **Step 3: Visual check**

```bash
python3 PMSaveDiskTool_v2/pm_gui.py
```

Expected: Loading_IMG.png appears centred for ~3 seconds, then main window appears. Clicking the splash dismisses early.

- [ ] **Step 4: Commit**

```bash
git add PMSaveDiskTool_v2/pm_gui.py
git commit -m "feat: add 3-second splash screen with Loading_IMG.png"
```

---

## Task 3: App Title Band + Root Background

**Files:**
- Modify: `PMSaveDiskTool_v2/pm_gui.py` — add `_build_title_band()`, call in `__init__`, update `_update_title()`

- [ ] **Step 1: Add _build_title_band() method to PMSaveDiskToolGUI**

Add this method to `PMSaveDiskToolGUI`, just before `_build_menu`:

```python
def _build_title_band(self):
    """Cyan-on-blue title header, like the original game's screen headers."""
    band = tk.Frame(self.root, bg=PAL["bg_header"], height=28)
    band.pack(fill=tk.X, side=tk.TOP)
    band.pack_propagate(False)

    self._title_left = tk.Label(
        band, text="PLAYER MANAGER TOOLKIT",
        bg=PAL["bg_header"], fg=PAL["fg_title"],
        font=("Courier New", 12, "bold"),
    )
    self._title_left.pack(side=tk.LEFT, padx=10)

    self._title_right = tk.Label(
        band, text="",
        bg=PAL["bg_header"], fg=PAL["fg_label"],
        font=("Courier New", 9),
    )
    self._title_right.pack(side=tk.RIGHT, padx=10)
```

- [ ] **Step 2: Add _refresh_title_band() and call it from _update_title()**

Add this method:

```python
def _refresh_title_band(self):
    if self.adf_path and self.slot:
        slot_name = self.save_var.get()
        self._title_right.config(
            text=f"{os.path.basename(self.adf_path)}  ·  {slot_name}"
        )
    elif self.adf_path:
        self._title_right.config(text=os.path.basename(self.adf_path))
    else:
        self._title_right.config(text="")
```

Then in `_update_title()`, add a call at the end:

```python
def _update_title(self):
    if self.adf_path:
        base = f"PMSaveDiskToolkit — {os.path.basename(self.adf_path)}"
        if self.dirty:
            base += " •"
    else:
        base = f"PMSaveDiskToolkit — {__version__}"
    self.root.title(base)
    self._refresh_title_band()   # ← add this
```

- [ ] **Step 3: Wire _build_title_band into __init__**

In `PMSaveDiskToolGUI.__init__`, add `self._build_title_band()` as the first build call, before `self._build_menu()`:

```python
self._build_title_band()
self._build_menu()
self._build_toolbar()
self._build_main()
self._build_status_bar()
self._update_title()
```

- [ ] **Step 4: Visual check**

```bash
python3 PMSaveDiskTool_v2/pm_gui.py
```

Expected: cyan "PLAYER MANAGER TOOLKIT" title band visible at the very top of the window. Right side shows filename + slot name once an ADF is loaded.

- [ ] **Step 5: Commit**

```bash
git add PMSaveDiskTool_v2/pm_gui.py
git commit -m "feat: add game-inspired title band to main window"
```

---

## Task 4: Player List Tree — Free Agent Colouring + Status Bar

**Files:**
- Modify: `PMSaveDiskTool_v2/pm_gui.py` — `_build_main()` tree setup, `_refresh_player_list()`, `_build_status_bar()`

- [ ] **Step 1: Register the "free" tag after tree construction in _build_main()**

Find the line `self.tree.bind("<<TreeviewSelect>>", self._on_player_selected)` (around line 939). Add the tag configuration immediately after:

```python
self.tree.bind("<<TreeviewSelect>>", self._on_player_selected)
self.tree.tag_configure("free", foreground=PAL["free_agent"])
```

- [ ] **Step 2: Apply the "free" tag in _refresh_player_list()**

In `_refresh_player_list` (around line 1199), every `self.tree.insert(...)` call that inserts a real player should have `tags=("free",)` when the player is a free agent. Find the insert calls and add tag logic. The insert calls look like:

```python
self.tree.insert("", "end", iid=str(p.player_id), values=(...))
```

Change them to:

```python
tags = ("free",) if p.is_free_agent else ()
self.tree.insert("", "end", iid=str(p.player_id), values=(...), tags=tags)
```

Apply this pattern to every `self.tree.insert` call in `_refresh_player_list` that inserts a player row (not squad-analyst section headers).

- [ ] **Step 3: Restyle the status bar**

In `_build_status_bar()`, change the `bar` frame and labels to use the palette:

```python
def _build_status_bar(self):
    bar = tk.Frame(self.root, bg="#000033", height=22)
    bar.pack(fill=tk.X, side=tk.BOTTOM)
    bar.pack_propagate(False)

    self.status_var = tk.StringVar(value="Open a save disk to begin.")
    tk.Label(bar, textvariable=self.status_var, anchor="w",
             bg="#000033", fg=PAL["fg_dim"],
             font=("Courier New", 9)).pack(
                 side=tk.LEFT, fill=tk.X, expand=True, padx=6)

    self.game_label = tk.Label(bar, text="No game disk",
                               bg="#000033", fg=PAL["fg_dim"],
                               font=("Courier New", 9), anchor="e")
    self.game_label.pack(side=tk.RIGHT, padx=6)

    self.beta_pill = tk.Label(
        bar, text=" BETA ",
        bg="#b36b00", fg="white", font=("Courier New", 9, "bold"),
        padx=4,
    )
```

Also update the three `self.game_label.config(foreground=...)` calls in `_open_game_adf` to use palette colours:
- Success (Italian): `foreground=PAL["free_agent"]`
- BETA: `foreground="#b36b00"` (unchanged — intentional amber warning)
- No names: `foreground="#b36b00"` (unchanged)

- [ ] **Step 4: Visual check**

```bash
python3 PMSaveDiskTool_v2/pm_gui.py
```

Open an ADF. Free agents should appear in green in the player list. Status bar should be dark with dim text.

- [ ] **Step 5: Commit**

```bash
git add PMSaveDiskTool_v2/pm_gui.py
git commit -m "feat: free agent green tagging in tree, restyle status bar"
```

---

## Task 5: Detail Pane — Identity Header + Footer Bar

**Files:**
- Modify: `PMSaveDiskTool_v2/pm_gui.py` — `_build_main()` identity header section, `_build_detail_fields()` header, footer frame/buttons

- [ ] **Step 1: Restyle the identity header frame**

In `_build_main()`, find:

```python
self.detail_header = ttk.Frame(right)
self.detail_header.pack(fill=tk.X, padx=6, pady=(6, 2))
```

Change to a raw `tk.Frame` so we can colour it:

```python
self.detail_header = tk.Frame(right, bg=PAL["bg_mid"])
self.detail_header.pack(fill=tk.X)
```

- [ ] **Step 2: Restyle the identity header labels and entries in _build_detail_fields()**

Find the identity header loop (around line 990–1000):

```python
for i, (label, key) in enumerate(
    [("Player #", "player_id"), ("Name", "name"), ("Seed", "rng_seed")]
):
    ttk.Label(self.detail_header, text=label, anchor="e").grid(...)
    var = tk.StringVar()
    entry = ttk.Entry(self.detail_header, textvariable=var,
                      state="readonly", width=14)
    entry.grid(...)
```

Replace with:

```python
for i, (label, key) in enumerate(
    [("Player #", "player_id"), ("Name", "name"), ("Seed", "rng_seed")]
):
    tk.Label(self.detail_header, text=label.upper(), anchor="e",
             bg=PAL["bg_mid"], fg=PAL["fg_dim"],
             font=("Courier New", 8)).grid(
                 row=0, column=i * 2, sticky="e", padx=(6, 3), pady=6)
    var = tk.StringVar()
    tk.Label(self.detail_header, textvariable=var,
             bg=PAL["bg_mid"], fg=PAL["fg_title"],
             font=("Courier New", 10, "bold"), anchor="w").grid(
                 row=0, column=i * 2 + 1, sticky="w", padx=(0, 16), pady=6)
    self.fields[key] = var
```

Note: we switch from `ttk.Entry(state="readonly")` to a `tk.Label` for the identity row — the values are display-only, and a Label is cleaner and easier to style.

- [ ] **Step 3: Restyle the footer bar**

Find the footer section in `_build_main()` (around line 952–958):

```python
footer = ttk.Frame(right)
footer.pack(fill=tk.X, side=tk.BOTTOM, padx=6, pady=(0, 6))
ttk.Separator(footer, orient="horizontal").pack(fill=tk.X, pady=(0, 4))
self.apply_button = ttk.Button(footer, text="Apply Changes",
                               command=self._apply_changes)
self.apply_button.pack(side=tk.RIGHT)
ttk.Button(footer, text="Revert",
           command=self._revert_player).pack(side=tk.RIGHT, padx=(0, 6))
```

Replace with:

```python
footer = tk.Frame(right, bg=PAL["btn_go"])
footer.pack(fill=tk.X, side=tk.BOTTOM)
self.apply_button = tk.Button(
    footer, text="APPLY",
    bg=PAL["btn_go"], fg=PAL["btn_go_fg"],
    font=("Courier New", 9, "bold"),
    relief="flat", bd=0, padx=14, pady=4,
    activebackground=PAL["selected"], activeforeground="#ffffff",
    command=self._apply_changes,
)
self.apply_button.pack(side=tk.RIGHT, padx=(4, 6), pady=4)
tk.Button(
    footer, text="REVERT",
    bg=PAL["bg_mid"], fg=PAL["fg_dim"],
    font=("Courier New", 9),
    relief="flat", bd=0, padx=10, pady=4,
    activebackground=PAL["selected"], activeforeground="#ffffff",
    command=self._revert_player,
).pack(side=tk.RIGHT, pady=4)
```

- [ ] **Step 4: Visual check**

```bash
python3 PMSaveDiskTool_v2/pm_gui.py
```

Open an ADF, select a player. Identity header should be dark blue with cyan values. Footer should be a green bar with APPLY / REVERT buttons.

- [ ] **Step 5: Commit**

```bash
git add PMSaveDiskTool_v2/pm_gui.py
git commit -m "feat: restyle detail pane identity header and footer bar"
```

---

## Task 6: Skills Tab Mini-Bars

**Files:**
- Modify: `PMSaveDiskTool_v2/pm_gui.py` — skills tab construction in `_build_detail_fields()`, `_populate_fields()`

- [ ] **Step 1: Rewrite the skills tab section in _build_detail_fields()**

Find the skills tab block (around lines 1019–1030):

```python
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
```

Replace entirely with:

```python
# Skills tab: label | entry | mini-bar, two column pairs side by side.
skills_tab = tk.Frame(self.notebook, bg=PAL["bg"])
self.notebook.add(skills_tab, text="Skills")
self._skill_bars: dict[str, tk.Canvas] = {}
half = (len(SKILL_NAMES) + 1) // 2
# Layout: left pair at cols 0,1,2 — right pair at cols 3,4,5
for i, skill in enumerate(SKILL_NAMES):
    if i < half:
        lc, ec, bc = 0, 1, 2
        row = i
    else:
        lc, ec, bc = 3, 4, 5
        row = i - half

    tk.Label(skills_tab, text=f"{skill.upper()}:", anchor="e",
             bg=PAL["bg"], fg=PAL["fg_label"],
             font=("Courier New", 8)).grid(
                 row=row, column=lc, sticky="e", padx=(8, 3), pady=3)

    var = tk.StringVar()
    tk.Entry(skills_tab, textvariable=var, width=5,
             bg="#000044", fg=PAL["fg_data"], insertbackground=PAL["fg_data"],
             relief="flat", bd=1, font=("Courier New", 10)).grid(
                 row=row, column=ec, sticky="w", padx=(2, 4), pady=3)
    self.fields[skill] = var

    bar = tk.Canvas(skills_tab, width=60, height=8,
                    bg=PAL["bg"], highlightthickness=0)
    bar.grid(row=row, column=bc, sticky="w", padx=(0, 10), pady=3)
    self._skill_bars[skill] = bar
```

- [ ] **Step 2: Add _redraw_skill_bars() method to PMSaveDiskToolGUI**

```python
def _redraw_skill_bars(self) -> None:
    """Redraw all 10 skill mini-bars from current field values."""
    for skill, bar in self._skill_bars.items():
        bar.delete("all")
        try:
            val = int(self.fields[skill].get())
        except ValueError:
            val = 0
        val = max(0, min(val, 99))
        fill_w = int(60 * val / 99)
        # Track
        bar.create_rectangle(0, 0, 60, 8, fill="#111144", outline=PAL["border"])
        # Fill
        if fill_w > 0:
            bar.create_rectangle(0, 0, fill_w, 8,
                                 fill=PAL["fg_title"], outline="")
```

- [ ] **Step 3: Call _redraw_skill_bars from _populate_fields()**

At the end of `_populate_fields()` (after all `self.fields[skill].set(...)` calls), add:

```python
self._redraw_skill_bars()
```

- [ ] **Step 4: Trace skill entries to redraw bars on live edit**

In the skills tab construction loop (from Step 1), after `self.fields[skill] = var`, add:

```python
var.trace_add("write", lambda *_, s=skill: self._redraw_skill_bar_single(s))
```

Add the single-bar helper:

```python
def _redraw_skill_bar_single(self, skill: str) -> None:
    bar = self._skill_bars.get(skill)
    if bar is None:
        return
    bar.delete("all")
    try:
        val = int(self.fields[skill].get())
    except ValueError:
        val = 0
    val = max(0, min(val, 99))
    fill_w = int(60 * val / 99)
    bar.create_rectangle(0, 0, 60, 8, fill="#111144", outline=PAL["border"])
    if fill_w > 0:
        bar.create_rectangle(0, 0, fill_w, 8, fill=PAL["fg_title"], outline="")
```

- [ ] **Step 5: Visual check**

```bash
python3 PMSaveDiskTool_v2/pm_gui.py
```

Open an ADF, select a player, click the Skills tab. Each skill should have a label, entry box, and a blue fill bar. Editing a value in the entry box should update the bar live.

- [ ] **Step 6: Commit**

```bash
git add PMSaveDiskTool_v2/pm_gui.py
git commit -m "feat: add live skill mini-bars to Skills tab"
```

---

## Task 7: PlayerCompareWindow

**Files:**
- Modify: `PMSaveDiskTool_v2/pm_gui.py` — add `PlayerCompareWindow` class after `LineupCoachWindow` (around line 730)

- [ ] **Step 1: Add the PlayerCompareWindow class**

Insert the full class after the closing of `LineupCoachWindow` and before `class PMSaveDiskToolGUI`:

```python
class PlayerCompareWindow(tk.Toplevel):
    """Side-by-side radar chart + skill bars comparison for two players."""

    _SKILL_LABELS = [s.upper()[:7] for s in SKILL_NAMES]
    _MAX_SKILL = 99
    _N = len(SKILL_NAMES)          # 10
    _CX, _CY, _R = 148, 148, 108  # radar canvas centre and radius

    def __init__(self, parent, slot, game_disk, player_a=None):
        super().__init__(parent)
        self.title("Compare Players")
        self.geometry("760x540")
        self.minsize(640, 460)
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

    # ── UI construction ───────────────────────────────────────────

    def _build_title_band(self):
        band = tk.Frame(self, bg=PAL["bg_header"], height=26)
        band.pack(fill=tk.X)
        band.pack_propagate(False)
        tk.Label(band, text="COMPARE PLAYERS",
                 bg=PAL["bg_header"], fg=PAL["fg_title"],
                 font=("Courier New", 11, "bold")).pack(side=tk.LEFT, padx=10)

    def _build_selector_row(self):
        row = tk.Frame(self, bg=PAL["bg_mid"])
        row.pack(fill=tk.X)
        tk.Frame(row, bg=PAL["border"], height=1).pack(fill=tk.X, side=tk.BOTTOM)

        # Player A — read-only labels
        a_frame = tk.Frame(row, bg=PAL["bg_mid"])
        a_frame.pack(side=tk.LEFT, padx=10, pady=6)
        tk.Label(a_frame, text="PLAYER A", bg=PAL["bg_mid"],
                 fg=PAL["fg_dim"], font=("Courier New", 8)).pack(anchor="w")
        self._a_name_lbl = tk.Label(a_frame, text="—",
                                    bg=PAL["bg_mid"], fg=PAL["player_a"],
                                    font=("Courier New", 11, "bold"))
        self._a_name_lbl.pack(anchor="w")
        self._a_meta_lbl = tk.Label(a_frame, text="",
                                    bg=PAL["bg_mid"], fg=PAL["fg_label"],
                                    font=("Courier New", 8))
        self._a_meta_lbl.pack(anchor="w")

        # Swap button
        tk.Button(row, text="⇄", bg=PAL["bg_mid"], fg=PAL["fg_dim"],
                  font=("Courier New", 14), relief="flat", bd=0,
                  activebackground=PAL["selected"], activeforeground="#ffffff",
                  command=self._swap).pack(side=tk.LEFT, padx=8)

        # Player B — team combo + player combo
        b_frame = tk.Frame(row, bg=PAL["bg_mid"])
        b_frame.pack(side=tk.LEFT, padx=10, pady=6)
        tk.Label(b_frame, text="PLAYER B", bg=PAL["bg_mid"],
                 fg=PAL["fg_dim"], font=("Courier New", 8)).pack(anchor="w")
        self._b_name_lbl = tk.Label(b_frame, text="—",
                                    bg=PAL["bg_mid"], fg=PAL["player_b"],
                                    font=("Courier New", 11, "bold"))
        self._b_name_lbl.pack(anchor="w")
        self._b_meta_lbl = tk.Label(b_frame, text="",
                                    bg=PAL["bg_mid"], fg=PAL["fg_label"],
                                    font=("Courier New", 8))
        self._b_meta_lbl.pack(anchor="w")

        pick_frame = tk.Frame(row, bg=PAL["bg_mid"])
        pick_frame.pack(side=tk.RIGHT, padx=10, pady=6)

        tk.Label(pick_frame, text="TEAM", bg=PAL["bg_mid"],
                 fg=PAL["fg_dim"], font=("Courier New", 8)).grid(
                     row=0, column=0, sticky="w")
        self._team_var = tk.StringVar()
        self._team_combo = ttk.Combobox(pick_frame, textvariable=self._team_var,
                                        state="readonly", width=18)
        self._team_combo.grid(row=0, column=1, padx=(4, 0), pady=2)
        self._team_combo.bind("<<ComboboxSelected>>", self._on_team_selected)

        tk.Label(pick_frame, text="PLAYER", bg=PAL["bg_mid"],
                 fg=PAL["fg_dim"], font=("Courier New", 8)).grid(
                     row=1, column=0, sticky="w")
        self._player_var = tk.StringVar()
        self._player_combo = ttk.Combobox(pick_frame, textvariable=self._player_var,
                                          state="readonly", width=18)
        self._player_combo.grid(row=1, column=1, padx=(4, 0), pady=2)
        self._player_combo.bind("<<ComboboxSelected>>", self._on_player_b_selected)

    def _build_body(self):
        body = tk.Frame(self, bg=PAL["bg"])
        body.pack(fill=tk.BOTH, expand=True)
        tk.Frame(body, bg=PAL["border"], width=1).pack(side=tk.LEFT, fill=tk.Y)

        # Left: radar canvas
        radar_frame = tk.Frame(body, bg="#000055")
        radar_frame.pack(side=tk.LEFT, fill=tk.Y)
        self._radar_canvas = tk.Canvas(radar_frame, width=310, height=310,
                                       bg="#000055", highlightthickness=0)
        self._radar_canvas.pack(padx=6, pady=6)

        # Divider
        tk.Frame(body, bg=PAL["border"], width=1).pack(side=tk.LEFT, fill=tk.Y)

        # Right: skill bars canvas
        bars_frame = tk.Frame(body, bg=PAL["bg"])
        bars_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        self._bars_canvas = tk.Canvas(bars_frame, bg=PAL["bg"],
                                      highlightthickness=0)
        self._bars_canvas.pack(fill=tk.BOTH, expand=True, padx=8, pady=6)

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
                                    font=("Courier New", 9))
        self._status_lbl.pack(side=tk.LEFT, padx=10, pady=5)
        tk.Button(bar, text="DONE", bg=PAL["btn_go"], fg=PAL["btn_go_fg"],
                  font=("Courier New", 9, "bold"),
                  relief="flat", bd=0, padx=16, pady=3,
                  activebackground=PAL["selected"], activeforeground="#ffffff",
                  command=self.destroy).pack(side=tk.RIGHT, padx=8, pady=4)

    # ── Data population ───────────────────────────────────────────

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
        teams = ["★ Free Agents"] + [
            self._slot.get_team_name(i)
            for i in range(1, len(self._slot.team_names))
        ]
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
        """Called by main window when user right-clicks a new player."""
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

    # ── Drawing ───────────────────────────────────────────────────

    def _draw(self):
        if not (self._player_a and self._player_b):
            return
        self._draw_radar()
        self._draw_bars()
        self._update_status()

    def _skill_values(self, p) -> list[int]:
        return [getattr(p, s) for s in SKILL_NAMES]

    def _radar_point(self, i: int, val: int) -> tuple[float, float]:
        import math
        angle = (i * 2 * math.pi / self._N) - math.pi / 2
        ratio = max(0, min(val, self._MAX_SKILL)) / self._MAX_SKILL
        return (self._CX + ratio * self._R * math.cos(angle),
                self._CY + ratio * self._R * math.sin(angle))

    def _axis_tip(self, i: int) -> tuple[float, float]:
        import math
        angle = (i * 2 * math.pi / self._N) - math.pi / 2
        return (self._CX + self._R * math.cos(angle),
                self._CY + self._R * math.sin(angle))

    def _draw_radar(self):
        import math
        c = self._radar_canvas
        c.delete("all")
        cx, cy, r, n = self._CX, self._CY, self._R, self._N

        # Grid rings at 25 / 50 / 75 / 100 %
        for g in range(1, 5):
            ratio = g / 4
            pts = []
            for i in range(n):
                angle = (i * 2 * math.pi / n) - math.pi / 2
                pts += [cx + ratio * r * math.cos(angle),
                        cy + ratio * r * math.sin(angle)]
            c.create_polygon(pts, outline=PAL["border"],
                             fill="#000066" if g == 4 else "", width=0.8)

        # Spokes + labels
        for i, label in enumerate(self._SKILL_LABELS):
            tx, ty = self._axis_tip(i)
            c.create_line(cx, cy, tx, ty, fill=PAL["border"], width=0.8)
            lx = cx + (r + 14) * math.cos((i * 2 * math.pi / n) - math.pi / 2)
            ly = cy + (r + 14) * math.sin((i * 2 * math.pi / n) - math.pi / 2)
            c.create_text(lx, ly, text=label, fill=PAL["fg_data"],
                          font=("Courier New", 7), anchor="center")

        # Player B polygon (behind)
        pts_b = []
        for i, v in enumerate(self._skill_values(self._player_b)):
            x, y = self._radar_point(i, v)
            pts_b += [x, y]
        c.create_polygon(pts_b, outline=PAL["player_b"], fill=PAL["player_b"],
                         stipple="gray12", width=2)

        # Player A polygon (front)
        pts_a = []
        for i, v in enumerate(self._skill_values(self._player_a)):
            x, y = self._radar_point(i, v)
            pts_a += [x, y]
        c.create_polygon(pts_a, outline=PAL["player_a"], fill=PAL["player_a"],
                         stipple="gray12", width=2)

        # Dots
        for pts, col in [(pts_b, PAL["player_b"]), (pts_a, PAL["player_a"])]:
            for i in range(0, len(pts), 2):
                x, y = pts[i], pts[i + 1]
                c.create_oval(x - 3, y - 3, x + 3, y + 3, fill=col, outline="")

    def _draw_bars(self):
        c = self._bars_canvas
        c.update_idletasks()
        c.delete("all")
        cw = c.winfo_width()
        if cw < 10:
            cw = 340

        vals_a = self._skill_values(self._player_a)
        vals_b = self._skill_values(self._player_b)

        row_h = 24
        bar_max = max(60, cw - 120)   # width of each bar track
        val_w = 26                     # width for value labels
        label_w = 58                   # width for skill name label
        half_bar = (bar_max - label_w) // 2

        for idx, (skill_label, va, vb) in enumerate(
            zip(self._SKILL_LABELS, vals_a, vals_b)
        ):
            y = idx * row_h + 10
            win_a = va > vb
            win_b = vb > va

            col_a = PAL["player_a"] if win_a else "#223344"
            col_b = PAL["player_b"] if win_b else "#331111"
            fg_a  = PAL["player_a"] if win_a else PAL["fg_dim"]
            fg_b  = PAL["player_b"] if win_b else PAL["fg_dim"]

            x0 = 6
            # Value A
            c.create_text(x0 + val_w, y + 8, text=str(va),
                          fill=fg_a, font=("Courier New", 9, "bold" if win_a else "normal"),
                          anchor="e")
            # Bar A (fills right to left)
            bax2 = x0 + val_w + half_bar
            bax1 = x0 + val_w + 4
            fill_a = int((va / self._MAX_SKILL) * (half_bar - 4))
            c.create_rectangle(bax1, y + 5, bax2, y + 11,
                               fill="#111144", outline=PAL["border"])
            if fill_a:
                c.create_rectangle(bax2 - fill_a, y + 5, bax2, y + 11,
                                   fill=col_a, outline="")
            # Skill label
            mid_x = bax2 + label_w // 2
            c.create_text(mid_x, y + 8, text=skill_label,
                          fill=PAL["fg_label"], font=("Courier New", 7),
                          anchor="center")
            # Bar B (fills left to right)
            bbx1 = bax2 + label_w
            bbx2 = bbx1 + half_bar - 4
            fill_b = int((vb / self._MAX_SKILL) * (half_bar - 4))
            c.create_rectangle(bbx1, y + 5, bbx2, y + 11,
                               fill="#111144", outline=PAL["border"])
            if fill_b:
                c.create_rectangle(bbx1, y + 5, bbx1 + fill_b, y + 11,
                                   fill=col_b, outline="")
            # Value B
            c.create_text(bbx2 + 4, y + 8, text=str(vb),
                          fill=fg_b, font=("Courier New", 9, "bold" if win_b else "normal"),
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
```

- [ ] **Step 2: Visual check — open window standalone by temporarily calling it from __init__**

Add at the very end of `PMSaveDiskToolGUI.__init__` (temporarily, remove after check):

```python
# TEMP: remove after visual check
self.root.after(500, lambda: PlayerCompareWindow(self.root, self.slot, self.game_disk) if self.slot else None)
```

```bash
python3 PMSaveDiskTool_v2/pm_gui.py
```

Load an ADF, wait 0.5 s. The Compare window should open. Pick a team + player B. Radar and bars should appear.

Remove the TEMP line after verification.

- [ ] **Step 3: Commit**

```bash
git add PMSaveDiskTool_v2/pm_gui.py
git commit -m "feat: add PlayerCompareWindow with radar chart and skill bars"
```

---

## Task 8: Menu Integration + Right-Click

**Files:**
- Modify: `PMSaveDiskTool_v2/pm_gui.py` — `_build_menu()`, add `_open_compare()` and `_on_tree_right_click()`, add key binding

- [ ] **Step 1: Add "Compare Players…" to the Tools menu in _build_menu()**

Find the tools menu block (around line 836):

```python
tools_menu = tk.Menu(menubar, tearoff=0)
tools_menu.add_command(label="Career Tracker…", ...)
tools_menu.add_command(label="Byte Workbench…", ...)
tools_menu.add_command(label="Line-up Coach (BETA)…", ...)
menubar.add_cascade(label="Tools", menu=tools_menu)
```

Add the new item after Line-up Coach:

```python
tools_menu.add_command(label="Compare Players…",
                       command=self._open_compare,
                       accelerator=f"{MOD_LABEL}+P")
```

Then in the accelerator bindings section, add:

```python
bind(f"<{MOD}-p>", lambda e: self._open_compare())
```

- [ ] **Step 2: Add _open_compare() method**

Add this method near `_open_career_tracker`, `_open_byte_workbench`, `_open_lineup_coach`:

```python
def _open_compare(self, player=None):
    if not self.slot:
        messagebox.showwarning("Warning", "Open a save disk first.")
        return
    if hasattr(self, "_compare_win") and self._compare_win.winfo_exists():
        self._compare_win.lift()
        if player:
            self._compare_win.set_player_a(player)
    else:
        self._compare_win = PlayerCompareWindow(
            self.root, self.slot, self.game_disk, player_a=player
        )
```

- [ ] **Step 3: Add right-click context menu on the player list tree**

Add the handler method:

```python
def _on_tree_right_click(self, event):
    row = self.tree.identify_row(event.y)
    if not row or row.startswith("squad-") or not self.slot:
        return
    self.tree.selection_set(row)
    try:
        player = self.slot.get_player(int(row))
    except (ValueError, KeyError):
        return

    menu = tk.Menu(self.root, tearoff=0)
    menu.add_command(
        label="Send to Compare…",
        command=lambda: self._open_compare(player),
    )
    menu.add_separator()
    menu.add_command(
        label=f"Copy ID #{player.player_id}",
        command=lambda: (self.root.clipboard_clear(),
                         self.root.clipboard_append(str(player.player_id))),
    )
    try:
        menu.tk_popup(event.x_root, event.y_root)
    finally:
        menu.grab_release()
```

Then in `_build_main()`, after `self.tree.bind("<<TreeviewSelect>>", ...)`, add:

```python
self.tree.bind("<Button-2>", self._on_tree_right_click)   # macOS
self.tree.bind("<Button-3>", self._on_tree_right_click)   # Windows/Linux
```

- [ ] **Step 4: Visual check — full end-to-end flow**

```bash
python3 PMSaveDiskTool_v2/pm_gui.py
```

1. Open an ADF.
2. Right-click any player → "Send to Compare…" → Compare window opens with that player as Player A.
3. Pick a team + Player B from the dropdowns → radar and bars appear.
4. Click ⇄ → players swap.
5. Open Tools menu → "Compare Players…" is listed with Cmd/Ctrl+P.
6. Press Cmd/Ctrl+P with the window already open → it lifts instead of reopening.

- [ ] **Step 5: Commit**

```bash
git add PMSaveDiskTool_v2/pm_gui.py
git commit -m "feat: wire Compare Players menu item, Cmd+P, right-click context menu"
```

---

## Task 9: Toolbar Restyle + Final Polish

**Files:**
- Modify: `PMSaveDiskTool_v2/pm_gui.py` — `_build_toolbar()`, minor colour fixes throughout

- [ ] **Step 1: Restyle the toolbar frame and labels**

In `_build_toolbar()`, change the toolbar frame and labels to use raw `tk` widgets:

```python
def _build_toolbar(self):
    toolbar = tk.Frame(self.root, bg=PAL["bg_mid"])
    toolbar.pack(fill=tk.X, padx=0, pady=0)

    tk.Label(toolbar, text="SAVE:", bg=PAL["bg_mid"], fg=PAL["fg_label"],
             font=("Courier New", 8)).pack(side=tk.LEFT, padx=(10, 2))
    self.save_var = tk.StringVar()
    self.save_combo = ttk.Combobox(toolbar, textvariable=self.save_var,
                                   state="readonly", width=12)
    self.save_combo.pack(side=tk.LEFT, padx=2)
    self.save_combo.bind("<<ComboboxSelected>>", self._on_save_selected)

    tk.Label(toolbar, text="VIEW:", bg=PAL["bg_mid"], fg=PAL["fg_label"],
             font=("Courier New", 8)).pack(side=tk.LEFT, padx=(14, 2))
    self.team_var = tk.StringVar()
    self.team_combo = ttk.Combobox(toolbar, textvariable=self.team_var,
                                   state="readonly", width=28)
    self.team_combo.pack(side=tk.LEFT, padx=2)
    self.team_combo.bind("<<ComboboxSelected>>", self._on_team_selected)
```

- [ ] **Step 2: Fix any remaining hardcoded colour strings**

Search for remaining `foreground="green"` or `foreground="gray"` literals outside of the BETA pill and fix them to use PAL values:

```bash
grep -n 'foreground="gray\|foreground="green\|foreground="gray30' PMSaveDiskTool_v2/pm_gui.py
```

For each hit that is NOT inside the BETA pill or the About dialog link colour (`#1a56db`), replace with the appropriate PAL value:
- `"gray"` → `PAL["fg_dim"]`
- `"gray30"` → `PAL["fg_label"]`
- `"green"` → `PAL["free_agent"]`

- [ ] **Step 3: Final visual walkthrough**

```bash
python3 PMSaveDiskTool_v2/pm_gui.py
```

Walk through every surface:
- [ ] Splash screen appears for 3 s, dismisses on click
- [ ] Title band shows "PLAYER MANAGER TOOLKIT" in cyan
- [ ] Toolbar shows SAVE/VIEW labels in muted blue
- [ ] Player list: navy background, amber names, green free agents, cyan headings
- [ ] Select a player: identity header dark blue with cyan name, Skills tab shows bars
- [ ] Edit a skill value: bar updates live
- [ ] Footer: green bar, APPLY/REVERT buttons
- [ ] Right-click player → "Send to Compare…" → Compare window opens
- [ ] Compare window: picks team + player, radar draws, bars draw, status line updates
- [ ] Swap button exchanges players
- [ ] Cmd+P opens/lifts compare window
- [ ] Career Tracker, Byte Workbench, Line-up Coach all still work

- [ ] **Step 4: Commit**

```bash
git add PMSaveDiskTool_v2/pm_gui.py
git commit -m "feat: restyle toolbar, fix remaining hardcoded colours — reskin complete"
```

---

## Self-Review Notes

**Spec coverage check:**
- ✅ PAL dict (Section 2)
- ✅ apply_theme() (Section 3.1) — Task 1
- ✅ Splash screen (Section 9) — Task 2
- ✅ App title band (Section 3.2) — Task 3
- ✅ Free agent colouring (Section 3.5) — Task 4
- ✅ Status bar reskin (Section 4) — Task 4
- ✅ Identity header (Section 4) — Task 5
- ✅ Footer bar (Section 3.4) — Task 5
- ✅ Skills tab mini-bars (Section 3.3) — Task 6
- ✅ PlayerCompareWindow — all subsections (Section 5) — Task 7
- ✅ Tools menu + Cmd+P (Section 6.1, 6.2) — Task 8
- ✅ Right-click context menu (Section 6.3) — Task 8
- ✅ Toolbar restyle (Section 4) — Task 9

**Type consistency:**
- `_skill_bars` dict used in Task 6 matches `_redraw_skill_bars` / `_redraw_skill_bar_single`
- `_compare_win` attribute set in `_open_compare` and checked with `winfo_exists()`
- `set_player_a(player)` public method name consistent between Task 7 definition and Task 8 call site
- `_team_players` list set in `_on_team_selected` and read in `_on_player_b_selected` — both in Task 7

**Placeholder scan:** None found.
