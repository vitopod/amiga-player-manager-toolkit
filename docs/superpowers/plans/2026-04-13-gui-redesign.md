# GUI Redesign Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace the default aqua/clam tkinter UI with a cohesive dark Amiga-themed design (orange + cyan on deep navy) with tabbed layout, division-grouped team sidebar, and Treeview roster table.

**Architecture:** All changes are in `PMSaveDiskTool_Mac/PMSaveDiskTool.py` (single-file app, ~3260 lines). The data layer (everything before `# ─── GUI`) is untouched. The GUI rebuild proceeds task by task, keeping the app runnable after every commit. Instance variable names used by business-logic methods are preserved wherever possible.

**Tech Stack:** Python 3.11, tkinter + ttk, Menlo font, macOS

---

## File changes

One file modified throughout:  
`PMSaveDiskTool_Mac/PMSaveDiskTool.py`

New instance variables introduced (replacing old ones):
- `self.roster_tree` replaces `self.pv_vars` (25 StringVar Entry fields → Treeview)
- `self._player_ids` — `list[int]` of 25 values, kept in sync with `self.roster_tree`, read by `apply_team_changes()`
- `self.nav_var` — StringVar for right side of status bar (breadcrumb)
- `self._inline_entry` — temporary Entry widget during inline roster edit

Instance variables **preserved** (existing methods reference these):
- `self.status_var`, `self.filename_var`
- `self.saves_listbox`
- `self.teams_tree`
- `self.team_name_var`, `self.division_var`, `self.word62_var`, `self.word64_var`
- `self.stat_vars`
- `self.hex_text`

---

## Task 1: Theme infrastructure — `_THEME` dict + `_apply_theme()`

**Files:**
- Modify: `PMSaveDiskTool_Mac/PMSaveDiskTool.py:37` (after constants block)
- Modify: `PMSaveDiskTool_Mac/PMSaveDiskTool.py:3248` (`main()` function)

- [ ] **Step 1: Insert `_THEME` dict after the constants block (after line 37, before `# ─── ADF Layer`)**

```python
# ─── Theme ───────────────────────────────────────────────────────────

_THEME = {
    'bg_deep':     '#1E1E2E',
    'bg_elevated': '#2A2A3C',
    'bg_surface':  '#363650',
    'bg_chrome':   '#16162A',
    'bg_toolbar':  '#22223A',
    'accent':      '#F28C28',
    'cyan':        '#4FC3F7',
    'positive':    '#44CC44',
    'negative':    '#E57373',
    'text':        '#C8C8D0',
    'text_bright': '#FFFFFF',
    'text_muted':  '#888888',
    'text_dim':    '#555555',
    'font':        ('Menlo', 11),
    'font_hdr':    ('Menlo', 14, 'bold'),
    'font_sec':    ('Menlo', 10, 'bold'),
    'font_sm':     ('Menlo', 10),
    'font_btn':    ('Menlo', 10, 'bold'),
}


def _apply_theme(root):
    """Configure ttk.Style globally before any widgets are created."""
    T = _THEME
    root.configure(bg=T['bg_deep'])

    style = ttk.Style(root)
    # Use 'clam' as base — it accepts colour overrides unlike 'aqua'
    if 'clam' in style.theme_names():
        style.theme_use('clam')

    # TFrame
    style.configure('TFrame', background=T['bg_deep'])
    style.configure('Toolbar.TFrame', background=T['bg_toolbar'])
    style.configure('Sidebar.TFrame', background=T['bg_elevated'])
    style.configure('Chrome.TFrame', background=T['bg_chrome'])
    style.configure('Surface.TFrame', background=T['bg_elevated'])

    # TLabel
    style.configure('TLabel', background=T['bg_deep'], foreground=T['text'],
                    font=T['font'])
    style.configure('Chrome.TLabel', background=T['bg_chrome'],
                    foreground=T['text_muted'], font=T['font_sm'])
    style.configure('Toolbar.TLabel', background=T['bg_toolbar'],
                    foreground=T['text_muted'], font=T['font_sm'])
    style.configure('Section.TLabel', background=T['bg_elevated'],
                    foreground=T['accent'], font=T['font_sec'])
    style.configure('SectionCyan.TLabel', background=T['bg_elevated'],
                    foreground=T['cyan'], font=T['font_sec'])
    style.configure('Muted.TLabel', background=T['bg_deep'],
                    foreground=T['text_muted'], font=T['font_sm'])
    style.configure('Dim.TLabel', background=T['bg_deep'],
                    foreground=T['text_dim'], font=T['font_sm'])
    style.configure('Bright.TLabel', background=T['bg_elevated'],
                    foreground=T['text_bright'], font=T['font_hdr'])
    style.configure('Status.TLabel', background=T['bg_chrome'],
                    foreground=T['text_muted'], font=T['font_sm'])
    style.configure('NavStatus.TLabel', background=T['bg_chrome'],
                    foreground=T['cyan'], font=T['font_sm'])

    # TButton
    style.configure('TButton', background=T['bg_surface'],
                    foreground=T['text'], font=T['font_btn'],
                    borderwidth=1, focusthickness=0, padding=(6, 3))
    style.map('TButton',
              background=[('active', T['bg_elevated']), ('pressed', T['bg_elevated'])],
              foreground=[('active', T['text_bright'])])
    style.configure('Primary.TButton', background=T['accent'],
                    foreground=T['bg_deep'], font=T['font_btn'])
    style.map('Primary.TButton',
              background=[('active', '#D97B20'), ('pressed', '#C06A10')],
              foreground=[('active', T['bg_deep'])])
    style.configure('Danger.TButton', background=T['bg_surface'],
                    foreground=T['negative'], font=T['font_btn'])
    style.map('Danger.TButton',
              background=[('active', T['bg_elevated'])],
              foreground=[('active', T['negative'])])

    # TEntry
    style.configure('TEntry', fieldbackground=T['bg_elevated'],
                    foreground=T['text_bright'], insertcolor=T['text_bright'],
                    bordercolor=T['bg_surface'], lightcolor=T['bg_surface'],
                    darkcolor=T['bg_surface'], font=T['font'])
    style.map('TEntry', fieldbackground=[('focus', T['bg_elevated'])],
              bordercolor=[('focus', T['accent'])])

    # TCombobox
    style.configure('TCombobox', fieldbackground=T['bg_elevated'],
                    foreground=T['text_bright'], background=T['bg_surface'],
                    selectbackground=T['bg_surface'], selectforeground=T['text_bright'],
                    font=T['font'])
    style.map('TCombobox', fieldbackground=[('readonly', T['bg_elevated'])],
              foreground=[('readonly', T['text_bright'])],
              selectbackground=[('readonly', T['bg_surface'])])
    root.option_add('*TCombobox*Listbox.background', T['bg_elevated'])
    root.option_add('*TCombobox*Listbox.foreground', T['text_bright'])
    root.option_add('*TCombobox*Listbox.selectBackground', T['bg_surface'])
    root.option_add('*TCombobox*Listbox.selectForeground', T['text_bright'])
    root.option_add('*TCombobox*Listbox.font', 'Menlo 11')

    # TScrollbar
    style.configure('TScrollbar', background=T['bg_surface'],
                    troughcolor=T['bg_deep'], bordercolor=T['bg_deep'],
                    arrowcolor=T['text_muted'])

    # TNotebook
    style.configure('TNotebook', background=T['bg_deep'],
                    bordercolor=T['bg_surface'])
    style.configure('TNotebook.Tab', background=T['bg_deep'],
                    foreground=T['text_muted'], font=T['font_sm'],
                    padding=(12, 5))
    style.map('TNotebook.Tab',
              background=[('selected', T['bg_elevated'])],
              foreground=[('selected', T['accent'])],
              expand=[('selected', [1, 1, 1, 0])])

    # Treeview
    style.configure('Treeview', background=T['bg_deep'],
                    foreground=T['text'], fieldbackground=T['bg_deep'],
                    font=T['font'], rowheight=22, borderwidth=0)
    style.configure('Treeview.Heading', background=T['bg_elevated'],
                    foreground=T['text_muted'], font=T['font_sec'],
                    relief='flat', borderwidth=0)
    style.map('Treeview',
              background=[('selected', T['bg_surface'])],
              foreground=[('selected', T['text_bright'])])
    style.map('Treeview.Heading',
              background=[('active', T['bg_surface'])])

    # TLabelframe
    style.configure('TLabelframe', background=T['bg_elevated'],
                    bordercolor=T['bg_surface'])
    style.configure('TLabelframe.Label', background=T['bg_elevated'],
                    foreground=T['accent'], font=T['font_sec'])

    # TSpinbox (inherits from TEntry mostly)
    style.configure('TSpinbox', fieldbackground=T['bg_elevated'],
                    foreground=T['text_bright'], font=T['font'],
                    background=T['bg_surface'], arrowcolor=T['text_muted'])
```

- [ ] **Step 2: Replace the `main()` theme block with `_apply_theme()` call**

Find (lines 3248–3254):
```python
    style = ttk.Style()
    available_themes = style.theme_names()
    if 'aqua' in available_themes:
        style.theme_use('aqua')
    elif 'clam' in available_themes:
        style.theme_use('clam')
```
Replace with:
```python
    _apply_theme(root)
```

- [ ] **Step 3: Run the app and verify the dark theme applies**

```bash
/usr/local/bin/python3.11 PMSaveDiskTool_Mac/PMSaveDiskTool.py
```
Expected: app launches with dark background, orange buttons, styled widgets. Layout is unchanged — only colours differ.

- [ ] **Step 4: Commit**

```bash
git add PMSaveDiskTool_Mac/PMSaveDiskTool.py
git commit -m "feat: add _THEME dict and _apply_theme() — dark theme infrastructure"
```

---

## Task 2: Rebuild `_build_ui()` — outer layout skeleton

**Files:**
- Modify: `PMSaveDiskTool_Mac/PMSaveDiskTool.py:1511` (replace `_build_ui` method)

Replace the entire `_build_ui` method body (lines 1512–1655) with the following. The new layout has four regions: title bar row, toolbar, body (sidebar + right panel), status bar. The old instance vars (`self.status_var`, `self.filename_var`) are preserved exactly.

- [ ] **Step 1: Replace `_build_ui` with the new skeleton**

```python
    def _build_ui(self):
        T = _THEME
        root = self.root

        # ── Title / chrome bar ──────────────────────────────────────────
        chrome = tk.Frame(root, bg=T['bg_chrome'], height=30)
        chrome.pack(fill=tk.X)
        chrome.pack_propagate(False)
        tk.Label(chrome, text='PM', bg=T['bg_chrome'], fg=T['accent'],
                 font=('Menlo', 13, 'bold')).pack(side=tk.LEFT, padx=(12, 4), pady=4)
        tk.Label(chrome, text='Save Disk Tool', bg=T['bg_chrome'], fg=T['text'],
                 font=('Menlo', 12)).pack(side=tk.LEFT, pady=4)
        self._gamedisk_label_var = tk.StringVar(value='(no game disk)')
        tk.Label(chrome, textvariable=self._gamedisk_label_var,
                 bg=T['bg_chrome'], fg=T['text_muted'],
                 font=('Menlo', 10)).pack(side=tk.RIGHT, padx=12, pady=4)

        # ── Toolbar ─────────────────────────────────────────────────────
        toolbar = tk.Frame(root, bg=T['bg_toolbar'], height=34)
        toolbar.pack(fill=tk.X)
        toolbar.pack_propagate(False)
        tk.Button(toolbar, text='Open ADF', command=self.open_adf,
                  bg=T['accent'], fg=T['bg_deep'], font=T['font_btn'],
                  relief='flat', padx=8, pady=2).pack(side=tk.LEFT, padx=(8, 4), pady=5)
        tk.Button(toolbar, text='Save', command=self.save_adf,
                  bg=T['bg_surface'], fg=T['text'], font=T['font_btn'],
                  relief='flat', padx=8, pady=2).pack(side=tk.LEFT, padx=2, pady=5)
        tk.Button(toolbar, text='Save As…', command=self.save_adf_as,
                  bg=T['bg_surface'], fg=T['text'], font=T['font_btn'],
                  relief='flat', padx=8, pady=2).pack(side=tk.LEFT, padx=2, pady=5)
        self.filename_var = tk.StringVar(value='No file loaded')
        tk.Label(toolbar, textvariable=self.filename_var,
                 bg=T['bg_toolbar'], fg=T['text_muted'],
                 font=T['font_sm']).pack(side=tk.RIGHT, padx=12)

        # ── Body: sidebar + right panel ─────────────────────────────────
        body = tk.Frame(root, bg=T['bg_deep'])
        body.pack(fill=tk.BOTH, expand=True)

        # Left sidebar (fixed 240 px)
        self._sidebar = tk.Frame(body, bg=T['bg_elevated'], width=240)
        self._sidebar.pack(side=tk.LEFT, fill=tk.Y)
        self._sidebar.pack_propagate(False)
        self._build_sidebar()

        # Separator
        tk.Frame(body, bg=T['bg_surface'], width=1).pack(side=tk.LEFT, fill=tk.Y)

        # Right panel
        self._right = tk.Frame(body, bg=T['bg_deep'])
        self._right.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        self._build_right_panel()

        # ── Status bar ───────────────────────────────────────────────────
        status_bar = tk.Frame(root, bg=T['bg_chrome'], height=22)
        status_bar.pack(fill=tk.X, side=tk.BOTTOM)
        status_bar.pack_propagate(False)
        self.nav_var = tk.StringVar(value='')
        tk.Label(status_bar, textvariable=self.nav_var,
                 bg=T['bg_chrome'], fg=T['cyan'],
                 font=T['font_sm']).pack(side=tk.RIGHT, padx=12)
        self.status_var = tk.StringVar(value='Ready — Open an ADF to begin')
        tk.Label(status_bar, textvariable=self.status_var,
                 bg=T['bg_chrome'], fg=T['text_muted'],
                 font=T['font_sm']).pack(side=tk.LEFT, padx=8)
```

- [ ] **Step 2: Add stub helper methods after `_build_ui` to prevent NameErrors**

Add these stubs right after `_build_ui` (before `_build_menu`). They will be replaced in later tasks:

```python
    def _build_sidebar(self):
        """Placeholder — replaced in Task 3."""
        T = _THEME
        # Temporary: recreate old save slots listbox and teams tree
        tk.Label(self._sidebar, text='SAVE SLOTS', bg=_THEME['bg_elevated'],
                 fg=_THEME['accent'], font=_THEME['font_sec']).pack(
                     anchor='w', padx=10, pady=(8, 2))
        self.saves_listbox = tk.Listbox(
            self._sidebar, height=4,
            bg=_THEME['bg_deep'], fg=_THEME['text'],
            selectbackground=_THEME['accent'], selectforeground=_THEME['bg_deep'],
            font=_THEME['font'], borderwidth=0, highlightthickness=0,
            exportselection=False)
        self.saves_listbox.pack(fill=tk.X, padx=8, pady=2)
        self.saves_listbox.bind('<<ListboxSelect>>', self.on_save_select)

        tk.Label(self._sidebar, text='TEAMS', bg=_THEME['bg_elevated'],
                 fg=_THEME['cyan'], font=_THEME['font_sec']).pack(
                     anchor='w', padx=10, pady=(8, 2))
        cols = ('name',)
        self.teams_tree = ttk.Treeview(self._sidebar, columns=cols,
                                       show='tree', height=18)
        self.teams_tree.column('#0', width=0, stretch=False)
        self.teams_tree.column('name', width=220)
        self.teams_tree.pack(fill=tk.BOTH, expand=True, padx=4, pady=2)
        self.teams_tree.bind('<<TreeviewSelect>>', self.on_team_select)

    def _build_right_panel(self):
        """Placeholder — replaced in Task 5+."""
        T = _THEME
        # Temporary: team info fields (preserve instance vars used by existing methods)
        self.team_name_var = tk.StringVar()
        self.division_var = tk.StringVar()
        self.word62_var = tk.StringVar()
        self.word64_var = tk.StringVar()
        self.stat_vars = []
        for _ in TeamRecord.STAT_LABELS:
            self.stat_vars.append(tk.StringVar())
        self._player_ids = [0xFFFF] * MAX_PLAYER_SLOTS
        self.pv_vars = []
        for _ in range(MAX_PLAYER_SLOTS):
            self.pv_vars.append(tk.StringVar())

        f = tk.Frame(self._right, bg=_THEME['bg_deep'])
        f.pack(fill=tk.BOTH, expand=True, padx=8, pady=8)
        ttk.Label(f, text='Select a team from the sidebar',
                  style='Muted.TLabel').pack(expand=True)

        self.hex_text = tk.Text(f, height=1, font=('Menlo', 11),
                                state='disabled', bg='#1e1e1e', fg='#d4d4d4')
        # Hidden for now; shown in hex tab later
```

- [ ] **Step 3: Run the app**

```bash
/usr/local/bin/python3.11 PMSaveDiskTool_Mac/PMSaveDiskTool.py
```
Expected: dark chrome bar at top, orange Open ADF button in toolbar, dark sidebar and right area, dark status bar at bottom. App is functional (open ADF, save, tool menus all work — sidebar populates on file load).

- [ ] **Step 4: Commit**

```bash
git add PMSaveDiskTool_Mac/PMSaveDiskTool.py
git commit -m "feat: new outer layout — chrome bar, toolbar, sidebar, status bar"
```

---

## Task 3: Sidebar — save slots section (final)

**Files:**
- Modify: `PMSaveDiskTool_Mac/PMSaveDiskTool.py` — replace `_build_sidebar` stub

- [ ] **Step 1: Replace `_build_sidebar` with the full implementation**

```python
    def _build_sidebar(self):
        T = _THEME
        sb = self._sidebar

        # ── Save Slots ──────────────────────────────────────────────────
        slots_hdr = tk.Frame(sb, bg=T['bg_elevated'])
        slots_hdr.pack(fill=tk.X)
        # Left-border accent
        tk.Frame(slots_hdr, bg=T['accent'], width=3).pack(side=tk.LEFT, fill=tk.Y)
        tk.Label(slots_hdr, text='SAVE SLOTS', bg=T['bg_elevated'], fg=T['accent'],
                 font=T['font_sec']).pack(side=tk.LEFT, padx=(6, 0), pady=(8, 2))

        slots_body = tk.Frame(sb, bg=T['bg_elevated'])
        slots_body.pack(fill=tk.X, padx=4, pady=(0, 4))
        self.saves_listbox = tk.Listbox(
            slots_body, height=4,
            bg=T['bg_elevated'], fg=T['text'],
            selectbackground=T['accent'], selectforeground=T['bg_deep'],
            font=T['font'], borderwidth=0, highlightthickness=0,
            exportselection=False)
        self.saves_listbox.pack(fill=tk.X, padx=4, pady=4)
        self.saves_listbox.bind('<<ListboxSelect>>', self.on_save_select)

        # ── Teams ────────────────────────────────────────────────────────
        tk.Frame(sb, bg=T['bg_surface'], height=1).pack(fill=tk.X)

        teams_hdr = tk.Frame(sb, bg=T['bg_elevated'])
        teams_hdr.pack(fill=tk.X)
        tk.Frame(teams_hdr, bg=T['cyan'], width=3).pack(side=tk.LEFT, fill=tk.Y)
        self._teams_count_var = tk.StringVar(value='TEAMS')
        tk.Label(teams_hdr, textvariable=self._teams_count_var,
                 bg=T['bg_elevated'], fg=T['cyan'],
                 font=T['font_sec']).pack(side=tk.LEFT, padx=(6, 0), pady=(8, 2))

        # Filter box
        filter_frame = tk.Frame(sb, bg=T['bg_elevated'])
        filter_frame.pack(fill=tk.X, padx=8, pady=(2, 4))
        self._filter_var = tk.StringVar()
        self._filter_var.trace_add('write', lambda *_: self._filter_teams())
        filter_entry = tk.Entry(
            filter_frame,
            textvariable=self._filter_var,
            bg=T['bg_deep'], fg=T['text_muted'],
            insertbackground=T['text'],
            font=T['font_sm'],
            borderwidth=1, relief='flat',
            highlightthickness=1, highlightbackground=T['bg_surface'],
            highlightcolor=T['accent'])
        filter_entry.pack(fill=tk.X)
        filter_entry.insert(0, 'Filter teams…')
        filter_entry.bind('<FocusIn>', lambda e: (
            filter_entry.delete(0, 'end')
            if filter_entry.get() == 'Filter teams…' else None))
        filter_entry.bind('<FocusOut>', lambda e: (
            filter_entry.insert(0, 'Filter teams…')
            if not filter_entry.get() else None))

        # Teams tree (division-grouped)
        teams_frame = tk.Frame(sb, bg=T['bg_elevated'])
        teams_frame.pack(fill=tk.BOTH, expand=True)

        self.teams_tree = ttk.Treeview(
            teams_frame, columns=('name',),
            show='tree', selectmode='browse')
        self.teams_tree.column('#0', width=0, stretch=False)
        self.teams_tree.column('name', width=224)
        vsb = ttk.Scrollbar(teams_frame, orient='vertical',
                             command=self.teams_tree.yview)
        self.teams_tree.configure(yscrollcommand=vsb.set)
        vsb.pack(side=tk.RIGHT, fill=tk.Y)
        self.teams_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        self.teams_tree.bind('<<TreeviewSelect>>', self.on_team_select)

        # Tags
        self.teams_tree.tag_configure(
            'div_header', foreground=T['accent'], font=T['font_sec'])
        self.teams_tree.tag_configure(
            'div_header_cyan', foreground=T['cyan'], font=T['font_sec'])
        self.teams_tree.tag_configure(
            'team_row', foreground=T['text'], font=T['font'])
        self.teams_tree.tag_configure(
            'team_selected', foreground=T['text_bright'], font=T['font'])
```

- [ ] **Step 2: Update `on_save_select()` to populate division-grouped tree**

Find the existing `on_save_select` method and replace its team-populating section (the block starting `# Populate teams tree`):

Old code (lines 1762–1768):
```python
        # Populate teams tree
        self.teams_tree.delete(*self.teams_tree.get_children())
        for team in self.current_save.teams:
            div = team.division
            div_str = str(div) if div is not None else "?"
            name = team.name if team.name else f"(record {team.index})"
            self.teams_tree.insert('', 'end', values=(team.index, name, div_str))
```

New code:
```python
        # Populate teams tree (division-grouped)
        self._populate_teams_tree(self.current_save.teams)
```

- [ ] **Step 3: Add `_populate_teams_tree()` and `_filter_teams()` methods**

Add after `on_save_select`:

```python
    def _populate_teams_tree(self, teams, filter_text=''):
        """Rebuild the division-grouped team tree. If filter_text, show only matches."""
        T = _THEME
        self.teams_tree.delete(*self.teams_tree.get_children())
        if not teams:
            return

        ft = filter_text.strip().lower()

        # Bucket teams by division
        divs = {0: [], 1: [], 2: [], 3: []}
        for team in teams:
            d = team.word_66 if team.word_66 in (0, 1, 2, 3) else 3
            divs[d].append(team)

        div_label_tag = {
            0: ('Division 1', 'div_header'),
            1: ('Division 2', 'div_header_cyan'),
            2: ('Division 3', 'div_header'),
            3: ('Division 4', 'div_header_cyan'),
        }
        # D1/D2 expanded by default, D3/D4 collapsed
        div_open = {0: True, 1: True, 2: False, 3: False}

        for d in range(4):
            bucket = divs[d]
            if ft:
                bucket = [t for t in bucket
                          if ft in (t.name or '').lower()]
            label, tag = div_label_tag[d]
            count = len(bucket)
            if count == 0 and ft:
                continue
            div_iid = f'div_{d}'
            self.teams_tree.insert(
                '', 'end', iid=div_iid,
                values=(f'▼ {label} ({count})',),
                open=True if ft else div_open[d],
                tags=(tag,))
            for team in bucket:
                name = team.name if team.name else f'(record {team.index})'
                self.teams_tree.insert(
                    div_iid, 'end',
                    iid=f'team_{team.index}',
                    values=(name,),
                    tags=('team_row',))

        count = sum(len(b) for b in divs.values())
        self._teams_count_var.set(f'TEAMS ({count})')

    def _filter_teams(self):
        if not self.current_save:
            return
        text = self._filter_var.get()
        if text == 'Filter teams…':
            text = ''
        self._populate_teams_tree(self.current_save.teams, filter_text=text)
```

- [ ] **Step 4: Update `on_team_select()` to work with new iid scheme**

Replace the existing `on_team_select` body:

```python
    def on_team_select(self, event):
        sel = self.teams_tree.selection()
        if not sel or not self.current_save:
            return
        iid = sel[0]
        # Division-header rows have iid like 'div_N' — ignore
        if not iid.startswith('team_'):
            return
        team_index = int(iid[5:])
        team = next((t for t in self.current_save.teams
                     if t.index == team_index), None)
        if not team:
            return
        self.current_team = team
        self._display_team(team)
        self._update_nav()
```

- [ ] **Step 5: Add `_update_nav()` helper**

```python
    def _update_nav(self):
        parts = []
        if self.current_save:
            parts.append(self.current_save.entry.name)
        if self.current_team:
            parts.append(self.current_team.name or f'team {self.current_team.index}')
        self.nav_var.set(' → '.join(parts))
```

Also call `self._update_nav()` at the end of `on_save_select()` after the status_var line.

- [ ] **Step 6: Update `apply_team_changes()` team-tree refresh at the end**

Find (lines 1888–1892):
```python
        # Refresh tree
        for item in self.teams_tree.get_children():
            vals = self.teams_tree.item(item, 'values')
            if int(vals[0]) == team.index:
                self.teams_tree.item(item, values=(team.index, team.name, str(team.word_66)))
                break
```

Replace with:
```python
        # Refresh the team's row in the division-grouped tree
        iid = f'team_{team.index}'
        if self.teams_tree.exists(iid):
            name = team.name if team.name else f'(record {team.index})'
            self.teams_tree.item(iid, values=(name,))
```

- [ ] **Step 7: Run and verify**

```bash
/usr/local/bin/python3.11 PMSaveDiskTool_Mac/PMSaveDiskTool.py
```
Open an ADF, select a save slot → teams grouped by division. Filter box narrows list. Clicking a team selects it. Nav breadcrumb updates bottom-right.

- [ ] **Step 8: Commit**

```bash
git add PMSaveDiskTool_Mac/PMSaveDiskTool.py
git commit -m "feat: sidebar — division-grouped team tree with filter + nav breadcrumb"
```

---

## Task 4: Team header bar

**Files:**
- Modify: `PMSaveDiskTool_Mac/PMSaveDiskTool.py` — update `_build_right_panel` stub

- [ ] **Step 1: Replace `_build_right_panel` stub with full implementation**

```python
    def _build_right_panel(self):
        T = _THEME
        rp = self._right

        # ── Empty-state panel (shown when no team selected) ──────────────
        self._empty_panel = tk.Frame(rp, bg=T['bg_deep'])
        self._empty_panel.place(relx=0, rely=0, relwidth=1, relheight=1)
        tk.Label(self._empty_panel, text='PM', bg=T['bg_deep'],
                 fg=T['accent'], font=('Menlo', 24, 'bold')).pack(expand=True, pady=(80, 0))
        tk.Label(self._empty_panel, text='Save Disk Tool', bg=T['bg_deep'],
                 fg=T['text'], font=('Menlo', 16)).pack()
        open_btn = tk.Button(self._empty_panel, text='Open ADF',
                             command=self.open_adf,
                             bg=T['accent'], fg=T['bg_deep'],
                             font=T['font_btn'], relief='flat',
                             padx=16, pady=6)
        open_btn.pack(pady=16)
        tk.Label(self._empty_panel, text='Open a Player Manager save disk ADF to begin',
                 bg=T['bg_deep'], fg=T['text_dim'],
                 font=T['font_sm']).pack()
        self._gamedisk_empty_var = tk.StringVar(value='')
        tk.Label(self._empty_panel, textvariable=self._gamedisk_empty_var,
                 bg=T['bg_deep'], fg=T['cyan'],
                 font=T['font_sm']).pack(pady=(8, 0))

        # ── Team-content panel (shown when a team is selected) ───────────
        self._team_panel = tk.Frame(rp, bg=T['bg_deep'])
        # Not placed yet — shown by _show_team_panel()

        # ── Team header bar ──────────────────────────────────────────────
        hdr = tk.Frame(self._team_panel, bg=T['bg_elevated'])
        hdr.pack(fill=tk.X)
        self._team_name_label = tk.Label(
            hdr, text='', bg=T['bg_elevated'], fg=T['text_bright'],
            font=T['font_hdr'])
        self._team_name_label.pack(side=tk.LEFT, padx=(14, 6), pady=8)
        self._div_badge = tk.Label(
            hdr, text='', bg=T['accent'], fg=T['bg_deep'],
            font=T['font_sm'], padx=8, pady=1)
        self._div_badge.pack(side=tk.LEFT, pady=8)
        self._value_label = tk.Label(
            hdr, text='', bg=T['bg_elevated'], fg=T['positive'],
            font=T['font_sm'])
        self._value_label.pack(side=tk.LEFT, padx=(10, 0), pady=8)
        self._budget_label = tk.Label(
            hdr, text='', bg=T['bg_elevated'], fg=T['text_muted'],
            font=T['font_sm'])
        self._budget_label.pack(side=tk.LEFT, padx=(6, 0), pady=8)
        tk.Button(hdr, text='Apply Changes',
                  command=self.apply_team_changes,
                  bg=T['accent'], fg=T['bg_deep'],
                  font=T['font_btn'], relief='flat',
                  padx=8, pady=2).pack(side=tk.RIGHT, padx=(0, 8), pady=6)
        tk.Button(hdr, text='Become Manager',
                  command=self.become_manager,
                  bg=T['bg_surface'], fg=T['text'],
                  font=T['font_btn'], relief='flat',
                  padx=8, pady=2).pack(side=tk.RIGHT, padx=4, pady=6)

        # Separator
        tk.Frame(self._team_panel, bg=T['bg_surface'], height=1).pack(fill=tk.X)

        # ── Notebook ─────────────────────────────────────────────────────
        self._notebook = ttk.Notebook(self._team_panel)
        self._notebook.pack(fill=tk.BOTH, expand=True)

        # Placeholder instance vars (will be set by tab builders)
        self.team_name_var = tk.StringVar()
        self.division_var = tk.StringVar()
        self.word62_var = tk.StringVar()
        self.word64_var = tk.StringVar()
        self.stat_vars = [tk.StringVar() for _ in TeamRecord.STAT_LABELS]
        self._player_ids = [0xFFFF] * MAX_PLAYER_SLOTS

        # Build tabs
        self._build_roster_tab()
        self._build_team_info_tab()
        self._build_stats_tab()
        self._build_hex_tab()

        # Keyboard shortcuts for tabs
        self.root.bind_all('<Command-Key-1>', lambda e: self._notebook.select(0))
        self.root.bind_all('<Command-Key-2>', lambda e: self._notebook.select(1))
        self.root.bind_all('<Command-Key-3>', lambda e: self._notebook.select(2))
        self.root.bind_all('<Command-Key-4>', lambda e: self._notebook.select(3))

    def _show_team_panel(self):
        """Switch right panel to the team-content view."""
        self._empty_panel.place_forget()
        self._team_panel.place(relx=0, rely=0, relwidth=1, relheight=1)

    def _show_empty_panel(self):
        """Switch right panel to the empty-state view."""
        self._team_panel.place_forget()
        self._empty_panel.place(relx=0, rely=0, relwidth=1, relheight=1)

    def _update_team_header(self, team):
        T = _THEME
        self._team_name_label.config(text=team.name or f'Team {team.index}')
        div = team.word_66
        if div == 0:
            badge_text, badge_bg = 'DIV 1', T['accent']
        elif div == 1:
            badge_text, badge_bg = 'DIV 2', T['cyan']
        elif div == 2:
            badge_text, badge_bg = 'DIV 3', T['bg_surface']
        elif div == 3:
            badge_text, badge_bg = 'DIV 4', T['bg_surface']
        else:
            badge_text, badge_bg = '?', T['bg_surface']
        self._div_badge.config(text=badge_text, bg=badge_bg,
                               fg=T['bg_deep'] if div in (0, 1) else T['text_muted'])
        val = team.team_value_signed
        self._value_label.config(
            text=f'Value: {val:+d}',
            fg=T['positive'] if val >= 0 else T['negative'])
        self._budget_label.config(text=f'Budget: {team.word_64}')
```

- [ ] **Step 2: Remove the old `pv_vars` attribute creation**

In the placeholder `_build_right_panel` stub from Task 2, we had `self.pv_vars = []` and related code. In this replacement, `pv_vars` is gone. The real data is now in `self._player_ids`. However, `_display_team()` and `apply_team_changes()` still reference `self.pv_vars`. Do NOT update those yet — add a compat shim for now in `_build_right_panel` after the tab builds:

```python
        # Compat shim — removed in Task 8 when _display_team is updated
        self.pv_vars = [tk.StringVar() for _ in range(MAX_PLAYER_SLOTS)]
        self.hex_text = tk.Text(self._team_panel, height=1,
                                state='disabled', font=('Menlo', 11),
                                bg='#1e1e1e', fg='#d4d4d4')
        # hex_text is properly placed inside _build_hex_tab; this placeholder
        # prevents AttributeError before Task 7
```

Wait — `hex_text` is being created in `_build_hex_tab()`. Don't double-create it. Instead, in `_build_hex_tab()`, ensure `self.hex_text` is set before it's referenced. The compat shim for pv_vars will be removed when `_display_team()` is updated in Task 7.

Add only the pv_vars shim (hex_text will come from `_build_hex_tab()`):
```python
        # Compat shim for pv_vars — removed in Task 8
        self.pv_vars = [tk.StringVar() for _ in range(MAX_PLAYER_SLOTS)]
```

- [ ] **Step 3: Add stub tab-builder methods (replaced in Tasks 5–7)**

```python
    def _build_roster_tab(self):
        frame = tk.Frame(self._notebook, bg=_THEME['bg_deep'])
        self._notebook.add(frame, text='Roster')
        self.roster_tree = ttk.Treeview(frame, show='headings',
                                        columns=('#', 'id', 'name'))
        self.roster_tree.heading('#', text='#')
        self.roster_tree.heading('id', text='ID')
        self.roster_tree.heading('name', text='Player Name')
        self.roster_tree.column('#', width=34, anchor='center')
        self.roster_tree.column('id', width=60, anchor='center')
        self.roster_tree.column('name', width=300)
        self.roster_tree.pack(fill=tk.BOTH, expand=True, padx=8, pady=8)

    def _build_team_info_tab(self):
        frame = tk.Frame(self._notebook, bg=_THEME['bg_deep'])
        self._notebook.add(frame, text='Team Info')
        g = ttk.Frame(frame)
        g.pack(fill=tk.X, padx=16, pady=12)
        ttk.Label(g, text='Team Name:').grid(row=0, column=0, sticky='e', padx=6, pady=4)
        ttk.Entry(g, textvariable=self.team_name_var, width=24).grid(
            row=0, column=1, sticky='w', padx=4)
        ttk.Label(g, text='Division:').grid(row=0, column=2, sticky='e', padx=6)
        ttk.Combobox(g, textvariable=self.division_var, width=14, state='readonly',
                     values=['0 (Div 1)', '1 (Div 2)', '2 (Div 3)', '3 (Div 4)']).grid(
            row=0, column=3, sticky='w', padx=4)
        ttk.Label(g, text='Team Value:').grid(row=1, column=0, sticky='e', padx=6, pady=4)
        ttk.Entry(g, textvariable=self.word62_var, width=10).grid(
            row=1, column=1, sticky='w', padx=4)
        ttk.Label(g, text='Budget Tier:').grid(row=1, column=2, sticky='e', padx=6)
        ttk.Entry(g, textvariable=self.word64_var, width=10).grid(
            row=1, column=3, sticky='w', padx=4)

    def _build_stats_tab(self):
        frame = tk.Frame(self._notebook, bg=_THEME['bg_deep'])
        self._notebook.add(frame, text='League Stats')
        g = ttk.Frame(frame)
        g.pack(fill=tk.X, padx=16, pady=12)
        for i, label in enumerate(TeamRecord.STAT_LABELS):
            ttk.Label(g, text=f'{label}:').grid(
                row=i // 3, column=(i % 3) * 2, sticky='e', padx=6, pady=4)
            ttk.Entry(g, textvariable=self.stat_vars[i], width=10).grid(
                row=i // 3, column=(i % 3) * 2 + 1, sticky='w', padx=4)

    def _build_hex_tab(self):
        frame = tk.Frame(self._notebook, bg='#1e1e1e')
        self._notebook.add(frame, text='Hex Dump')
        self.hex_text = tk.Text(frame, font=('Menlo', 11), state='disabled',
                                wrap='none', bg='#1e1e1e', fg='#d4d4d4',
                                insertbackground='white')
        vsb = ttk.Scrollbar(frame, orient='vertical', command=self.hex_text.yview)
        self.hex_text.configure(yscrollcommand=vsb.set)
        vsb.pack(side=tk.RIGHT, fill=tk.Y)
        self.hex_text.pack(fill=tk.BOTH, expand=True, padx=4, pady=4)
```

- [ ] **Step 4: Call `_show_team_panel()` from `on_team_select()` and `_show_empty_panel()` on load**

In `on_team_select`, after setting `self.current_team = team`, add:
```python
        self._show_team_panel()
        self._update_team_header(team)
```

In `open_adf()`, after loading entries, add at the end (before the status_var line or replace it):  
Keep the status_var.set() as-is; just add `self._show_empty_panel()` at the start of `open_adf` after the ADF opens successfully, before the "no dir entries" check.

Actually the safest place: in `__init__`, after `_build_ui()` is called:
```python
        # Show empty panel at startup
        self._show_empty_panel()
```

- [ ] **Step 5: Run and verify**

```bash
/usr/local/bin/python3.11 PMSaveDiskTool_Mac/PMSaveDiskTool.py
```
Expected: right panel shows empty state with large "PM" and Open ADF button on launch. Load an ADF, select a save slot, click a team → team content panel slides in with team name, division badge, value, budget in the header bar. Four tabs visible.

- [ ] **Step 6: Commit**

```bash
git add PMSaveDiskTool_Mac/PMSaveDiskTool.py
git commit -m "feat: team header bar, notebook tabs shell, empty-state panel"
```

---

## Task 5: Roster tab — Treeview, `_display_team()`, `apply_team_changes()`

**Files:**
- Modify: `PMSaveDiskTool_Mac/PMSaveDiskTool.py`

This is the most significant task. Replace `_build_roster_tab` stub, update `_display_team`, and update `apply_team_changes` to read from `self._player_ids`.

- [ ] **Step 1: Replace `_build_roster_tab` stub**

```python
    def _build_roster_tab(self):
        T = _THEME
        frame = tk.Frame(self._notebook, bg=T['bg_deep'])
        self._notebook.add(frame, text='Roster')

        # Treeview
        tree_frame = tk.Frame(frame, bg=T['bg_deep'])
        tree_frame.pack(fill=tk.BOTH, expand=True, padx=0, pady=0)

        self.roster_tree = ttk.Treeview(
            tree_frame, columns=('#', 'id', 'name'),
            show='headings', selectmode='browse')
        self.roster_tree.heading('#', text='#')
        self.roster_tree.heading('id', text='ID')
        self.roster_tree.heading('name', text='Player Name')
        self.roster_tree.column('#',    width=34,  anchor='center', stretch=False)
        self.roster_tree.column('id',   width=60,  anchor='center', stretch=False)
        self.roster_tree.column('name', width=300, stretch=True)

        vsb = ttk.Scrollbar(tree_frame, orient='vertical',
                             command=self.roster_tree.yview)
        self.roster_tree.configure(yscrollcommand=vsb.set)
        vsb.pack(side=tk.RIGHT, fill=tk.Y)
        self.roster_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        # Row tags
        self.roster_tree.tag_configure('odd',   background=T['bg_elevated'])
        self.roster_tree.tag_configure('even',  background=T['bg_deep'])
        self.roster_tree.tag_configure('empty', foreground=T['text_dim'])

        # Bindings (implemented in Task 6)
        self.roster_tree.bind('<Double-Button-1>', self._start_inline_edit)
        self.roster_tree.bind('<Return>',          self._start_inline_edit)

        # Action bar
        action_bar = tk.Frame(frame, bg=T['bg_deep'])
        action_bar.pack(fill=tk.X, padx=8, pady=(4, 8))
        tk.Frame(action_bar, bg=T['bg_surface'], height=1).pack(fill=tk.X, pady=(0, 6))
        btn_frame = tk.Frame(action_bar, bg=T['bg_deep'])
        btn_frame.pack(fill=tk.X)
        tk.Button(btn_frame, text='Set Player ID',
                  command=self._roster_set_id,
                  bg=T['bg_surface'], fg=T['text'],
                  font=T['font_btn'], relief='flat', padx=8, pady=2
                  ).pack(side=tk.LEFT)
        tk.Button(btn_frame, text='Remove Player',
                  command=self._roster_remove,
                  bg=T['bg_surface'], fg=T['negative'],
                  font=T['font_btn'], relief='flat', padx=8, pady=2
                  ).pack(side=tk.LEFT, padx=(6, 0))
        self._roster_count_var = tk.StringVar(value='')
        tk.Label(btn_frame, textvariable=self._roster_count_var,
                 bg=T['bg_deep'], fg=T['text_muted'],
                 font=T['font_sm']).pack(side=tk.RIGHT)

        # Context menu
        self._roster_menu = tk.Menu(self.root, tearoff=0,
                                    bg=T['bg_elevated'], fg=T['text'],
                                    activebackground=T['bg_surface'],
                                    activeforeground=T['text_bright'])
        self._roster_menu.add_command(label='Edit Player ID',
                                      command=self._roster_set_id)
        self._roster_menu.add_command(label='Remove Player',
                                      command=self._roster_remove)
        self._roster_menu.add_separator()
        self._roster_menu.add_command(label='Copy Player ID',
                                      command=self._roster_copy_id)
        self.roster_tree.bind('<Button-2>', self._show_roster_menu)
        self.roster_tree.bind('<Control-Button-1>', self._show_roster_menu)
```

- [ ] **Step 2: Update `_display_team()` to populate the roster Treeview**

Replace the entire `_display_team` method:

```python
    def _display_team(self, team):
        # Header bar
        self._update_team_header(team)

        # Team Info tab
        self.team_name_var.set(team.name)
        div = team.division
        if div is not None:
            self.division_var.set(f'{div} (Div {div + 1})')
        else:
            self.division_var.set(f'{team.word_66:#06x}')
        self.word62_var.set(str(team.team_value_signed))
        self.word64_var.set(str(team.word_64))

        # League Stats tab
        for i, var in enumerate(self.stat_vars):
            var.set(str(team.league_stats[i]))

        # Roster Treeview
        self.roster_tree.delete(*self.roster_tree.get_children())
        self._player_ids = list(team.player_values)  # copy
        filled = 0
        for i, pid in enumerate(self._player_ids):
            tag = 'odd' if i % 2 == 0 else 'even'
            if pid == 0xFFFF:
                self.roster_tree.insert('', 'end', iid=f'slot_{i}',
                                        values=(i, '—', 'empty slot'),
                                        tags=(tag, 'empty'))
            else:
                if self.game_disk:
                    name = self.game_disk.player_name(pid) or ''
                else:
                    name = ''
                self.roster_tree.insert('', 'end', iid=f'slot_{i}',
                                        values=(i, pid, name),
                                        tags=(tag,))
                filled += 1

        self._roster_count_var.set(f'{filled} players / {MAX_PLAYER_SLOTS} slots')

        # Hex Dump tab
        self.hex_text.config(state='normal')
        self.hex_text.delete('1.0', tk.END)
        hex_lines = []
        for i in range(0, len(team.raw), 16):
            chunk = team.raw[i:i + 16]
            hex_str = ' '.join(f'{b:02X}' for b in chunk)
            asc_str = ''.join(chr(b) if 32 <= b < 127 else '·' for b in chunk)
            hex_lines.append(f'+{i:03d}  {hex_str:<48s}  {asc_str}')
        self.hex_text.insert('1.0', '\n'.join(hex_lines))
        self.hex_text.config(state='disabled')
```

- [ ] **Step 3: Update `apply_team_changes()` player values section**

In `apply_team_changes()`, replace the `# Player values` block (the `for i, var in enumerate(self.pv_vars)` loop):

Old:
```python
        # Player values (field may contain "123 Surname" — take first token)
        for i, var in enumerate(self.pv_vars):
            try:
                val = var.get().strip().split()[0].upper()
                if val == 'FFFF':
                    team.player_values[i] = 0xFFFF
                else:
                    team.player_values[i] = int(val, 16) if val.startswith('0X') else int(val)
            except (ValueError, IndexError):
                pass
```

New:
```python
        # Player values — read from _player_ids (kept in sync with roster Treeview)
        for i, pid in enumerate(self._player_ids):
            team.player_values[i] = pid
```

- [ ] **Step 4: Remove `pv_vars` compat shim**

In `_build_right_panel`, delete the line:
```python
        # Compat shim for pv_vars — removed in Task 8
        self.pv_vars = [tk.StringVar() for _ in range(MAX_PLAYER_SLOTS)]
```

Also remove `self.pv_vars = []` and `for _ in range(MAX_PLAYER_SLOTS): self.pv_vars.append(tk.StringVar())` from the old `_build_right_panel` placeholder if it's still there. `pv_vars` is no longer used anywhere.

- [ ] **Step 5: Run and verify**

```bash
/usr/local/bin/python3.11 PMSaveDiskTool_Mac/PMSaveDiskTool.py
```
Open ADF → select save slot → click BAYERN MUNCHEN → Roster tab shows table with slot index, player ID, player name. Empty slots show dimmed "empty slot". Player count shows "N players / 25 slots". Apply Changes saves correctly.

- [ ] **Step 6: Commit**

```bash
git add PMSaveDiskTool_Mac/PMSaveDiskTool.py
git commit -m "feat: roster tab — Treeview table replaces 25 entry fields"
```

---

## Task 6: Roster inline editing + action bar handlers

**Files:**
- Modify: `PMSaveDiskTool_Mac/PMSaveDiskTool.py` — add inline edit methods + action handlers

- [ ] **Step 1: Add inline edit methods**

Add after `_display_team`:

```python
    def _start_inline_edit(self, event=None):
        sel = self.roster_tree.selection()
        if not sel:
            return
        iid = sel[0]
        slot = int(iid[5:])  # 'slot_N' → N
        # Get bounding box of the 'id' column cell
        bbox = self.roster_tree.bbox(iid, column='id')
        if not bbox:
            return
        x, y, w, h = bbox

        current = self._player_ids[slot]
        init_val = '' if current == 0xFFFF else str(current)

        self._inline_slot = slot
        self._inline_entry = tk.Entry(
            self.roster_tree,
            font=_THEME['font'],
            bg=_THEME['bg_elevated'],
            fg=_THEME['text_bright'],
            insertbackground=_THEME['text_bright'],
            relief='flat',
            highlightthickness=1,
            highlightbackground=_THEME['accent'],
            highlightcolor=_THEME['accent'])
        self._inline_entry.insert(0, init_val)
        self._inline_entry.select_range(0, 'end')
        self._inline_entry.place(x=x, y=y, width=w, height=h)
        self._inline_entry.focus_set()
        self._inline_entry.bind('<Return>',  lambda e: self._confirm_inline_edit())
        self._inline_entry.bind('<Escape>',  lambda e: self._cancel_inline_edit())
        self._inline_entry.bind('<FocusOut>', lambda e: self._cancel_inline_edit())

    def _confirm_inline_edit(self):
        if not hasattr(self, '_inline_entry') or self._inline_entry is None:
            return
        raw = self._inline_entry.get().strip()
        self._cancel_inline_edit()  # removes widget first

        slot = self._inline_slot
        if not raw:
            new_pid = 0xFFFF
        else:
            try:
                new_pid = int(raw)
            except ValueError:
                # Flash invalid — just cancel
                return
            if new_pid < 0 or new_pid > 1036:
                return

        self._player_ids[slot] = new_pid
        # Refresh the row
        tag = 'odd' if slot % 2 == 0 else 'even'
        iid = f'slot_{slot}'
        if new_pid == 0xFFFF:
            self.roster_tree.item(iid, values=(slot, '—', 'empty slot'),
                                  tags=(tag, 'empty'))
        else:
            name = (self.game_disk.player_name(new_pid) or '') if self.game_disk else ''
            self.roster_tree.item(iid, values=(slot, new_pid, name),
                                  tags=(tag,))
        # Update count
        filled = sum(1 for p in self._player_ids if p != 0xFFFF)
        self._roster_count_var.set(f'{filled} players / {MAX_PLAYER_SLOTS} slots')

    def _cancel_inline_edit(self):
        if hasattr(self, '_inline_entry') and self._inline_entry is not None:
            self._inline_entry.destroy()
            self._inline_entry = None
```

- [ ] **Step 2: Add action bar and context menu handlers**

```python
    def _roster_set_id(self):
        sel = self.roster_tree.selection()
        if sel:
            self._start_inline_edit()

    def _roster_remove(self):
        sel = self.roster_tree.selection()
        if not sel:
            return
        iid = sel[0]
        slot = int(iid[5:])
        self._player_ids[slot] = 0xFFFF
        tag = 'odd' if slot % 2 == 0 else 'even'
        self.roster_tree.item(iid, values=(slot, '—', 'empty slot'),
                              tags=(tag, 'empty'))
        filled = sum(1 for p in self._player_ids if p != 0xFFFF)
        self._roster_count_var.set(f'{filled} players / {MAX_PLAYER_SLOTS} slots')

    def _roster_copy_id(self):
        sel = self.roster_tree.selection()
        if not sel:
            return
        iid = sel[0]
        slot = int(iid[5:])
        pid = self._player_ids[slot]
        if pid != 0xFFFF:
            self.root.clipboard_clear()
            self.root.clipboard_append(str(pid))

    def _show_roster_menu(self, event):
        iid = self.roster_tree.identify_row(event.y)
        if iid:
            self.roster_tree.selection_set(iid)
            self._roster_menu.post(event.x_root, event.y_root)
```

- [ ] **Step 3: Add keyboard shortcut for Delete key on roster**

In `_build_roster_tab`, add after the `<Return>` binding:
```python
        self.roster_tree.bind('<Delete>',    lambda e: self._roster_remove())
        self.roster_tree.bind('<BackSpace>', lambda e: self._roster_remove())
```

- [ ] **Step 4: Run and verify**

```bash
/usr/local/bin/python3.11 PMSaveDiskTool_Mac/PMSaveDiskTool.py
```
- Double-click a roster row → inline Entry appears over the ID column, pre-filled with current ID
- Type a valid ID (0–1036), press Enter → row updates with new name
- Press Escape → edit cancelled
- Right-click → context menu with Edit/Remove/Copy
- Delete key → removes selected player
- "Set Player ID" button → triggers inline edit
- "Remove Player" button → clears slot

- [ ] **Step 5: Commit**

```bash
git add PMSaveDiskTool_Mac/PMSaveDiskTool.py
git commit -m "feat: roster inline editing, context menu, action bar handlers"
```

---

## Task 7: Keyboard shortcuts + title bar game disk indicator

**Files:**
- Modify: `PMSaveDiskTool_Mac/PMSaveDiskTool.py`

- [ ] **Step 1: Update `_build_menu` to add Cmd+Shift+S and tab shortcuts**

In `_build_menu`, after the existing `bind_all` calls, add:
```python
        self.root.bind_all('<Command-S>', lambda e: self.save_adf())
        self.root.bind_all('<Command-Shift-S>', lambda e: self.save_adf_as())
        # Sidebar navigation
        self.root.bind_all('<Up>',   self._sidebar_up)
        self.root.bind_all('<Down>', self._sidebar_down)
```

Note: the existing `<Command-s>` (lowercase) bind stays; add `<Command-S>` (uppercase/shift) only for save-as.

- [ ] **Step 2: Add sidebar keyboard navigation helpers**

```python
    def _sidebar_up(self, event=None):
        sel = self.teams_tree.selection()
        if not sel:
            return
        prev = self.teams_tree.prev(sel[0])
        # Skip division headers
        while prev and not prev.startswith('team_'):
            prev = self.teams_tree.prev(prev)
        if prev:
            self.teams_tree.selection_set(prev)
            self.teams_tree.see(prev)

    def _sidebar_down(self, event=None):
        sel = self.teams_tree.selection()
        if not sel:
            children = [c for c in self.teams_tree.get_children()
                        if c.startswith('team_')]
            if children:
                self.teams_tree.selection_set(children[0])
            return
        nxt = self.teams_tree.next(sel[0])
        while nxt and not nxt.startswith('team_'):
            # If it's a division header, go to its first child
            children = self.teams_tree.get_children(nxt)
            if children:
                nxt = children[0]
                break
            nxt = self.teams_tree.next(nxt)
        if nxt and nxt.startswith('team_'):
            self.teams_tree.selection_set(nxt)
            self.teams_tree.see(nxt)
```

- [ ] **Step 3: Update game disk loading to update the chrome bar label**

In `__init__`, in the game disk auto-load block, after setting `self.game_disk`:
```python
                self._gamedisk_label_var.set(
                    f'⬡ {os.path.basename(game_path)} loaded')
                self._gamedisk_label_var  # StringVar is already set in _build_ui
                self._gamedisk_empty_var.set(
                    f'Game disk ready: {os.path.basename(game_path)}')
```

And on error, add:
```python
                self._gamedisk_label_var.set('(game disk error)')
```

Note: `_gamedisk_label_var` and `_gamedisk_empty_var` are created in `_build_right_panel → _build_ui`. Since `__init__` calls `_build_ui()` before the game disk load, the vars exist.

- [ ] **Step 4: Run and verify**

```bash
/usr/local/bin/python3.11 PMSaveDiskTool_Mac/PMSaveDiskTool.py
```
- Chrome bar shows "⬡ PlayerManagerITA.adf loaded" in top-right when game disk found
- Empty state shows "Game disk ready: PlayerManagerITA.adf"
- Cmd+1/2/3/4 switch tabs
- Up/Down keys navigate team list (skipping division headers)

- [ ] **Step 5: Commit**

```bash
git add PMSaveDiskTool_Mac/PMSaveDiskTool.py
git commit -m "feat: keyboard shortcuts — tab switching, sidebar navigation, game disk chrome label"
```

---

## Task 8: PatchComposer window theme

**Files:**
- Modify: `PMSaveDiskTool_Mac/PMSaveDiskTool.py:2073` (`PatchComposerWindow._build_ui`)

- [ ] **Step 1: Replace `_build_ui` body in `PatchComposerWindow`**

Replace the method body (from `top = ttk.Frame(self)` through `ttk.Button(bot, text="Write to Game Disk ADF",…`). Keep all logic methods (`_open_adf`, `_add_patch`, `_delete_patch`, `_apply_age`, `_refresh_list`, `_preview_asm`, `_write_adf`) untouched.

```python
    def _build_ui(self):
        T = _THEME
        self.configure(bg=T['bg_deep'])

        # Top bar
        top = tk.Frame(self, bg=T['bg_chrome'])
        top.pack(fill=tk.X)
        open_btn_style = {'bg': T['accent'], 'fg': T['bg_deep'],
                          'font': T['font_btn'], 'relief': 'flat', 'padx': 8, 'pady': 3}
        tk.Button(top, text='Open Game Disk ADF…',
                  command=self._open_adf, **open_btn_style).pack(
                      side=tk.LEFT, padx=8, pady=5)
        self._fname_var = tk.StringVar(value='No game disk loaded')
        tk.Label(top, textvariable=self._fname_var,
                 bg=T['bg_chrome'], fg=T['text_muted'],
                 font=T['font_sm']).pack(side=tk.LEFT, padx=8)

        # Patch list
        lf = tk.LabelFrame(self, text='  Current Patches  (Block 1137, callback area)  ',
                           bg=T['bg_elevated'], fg=T['accent'],
                           font=T['font_sec'], bd=1, relief='flat')
        lf.pack(fill=tk.BOTH, expand=True, padx=8, pady=4)

        cols = ('#', 'Offset', 'Size', 'Value', 'Description')
        self._tree = ttk.Treeview(lf, columns=cols, show='headings', height=10)
        self._tree.heading('#', text='#')
        self._tree.heading('Offset', text='Offset')
        self._tree.heading('Size', text='Size')
        self._tree.heading('Value', text='Value')
        self._tree.heading('Description', text='Description')
        self._tree.column('#', width=32, anchor='center')
        self._tree.column('Offset', width=90, anchor='center')
        self._tree.column('Size', width=44, anchor='center')
        self._tree.column('Value', width=120, anchor='center')
        self._tree.column('Description', width=400)
        self._tree.tag_configure('odd',  background=T['bg_elevated'])
        self._tree.tag_configure('even', background=T['bg_deep'])
        self._tree.tag_configure('copyprot', foreground=T['text_dim'])

        vsb = ttk.Scrollbar(lf, orient='vertical', command=self._tree.yview)
        self._tree.configure(yscrollcommand=vsb.set)
        self._tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=4, pady=4)
        vsb.pack(side=tk.RIGHT, fill=tk.Y, pady=4)

        del_frame = tk.Frame(self, bg=T['bg_deep'])
        del_frame.pack(fill=tk.X, padx=8)
        tk.Button(del_frame, text='Delete Selected Patch',
                  command=self._delete_patch,
                  bg=T['bg_surface'], fg=T['negative'],
                  font=T['font_btn'], relief='flat', padx=8, pady=2
                  ).pack(side=tk.LEFT, padx=4, pady=4)

        # Quick Patches
        qf = tk.LabelFrame(self, text='  Quick Patches  ',
                           bg=T['bg_elevated'], fg=T['accent'],
                           font=T['font_sec'], bd=1, relief='flat')
        qf.pack(fill=tk.X, padx=8, pady=4)
        qg = tk.Frame(qf, bg=T['bg_elevated'])
        qg.pack(fill=tk.X, padx=8, pady=6)

        tk.Label(qg, text='Manager Age:', bg=T['bg_elevated'],
                 fg=T['text'], font=T['font']).grid(row=0, column=0, sticky='e', padx=4)
        self._age_var = tk.StringVar(value='18')
        ttk.Spinbox(qg, from_=16, to=99, textvariable=self._age_var,
                    width=5).grid(row=0, column=1, sticky='w', padx=4)
        tk.Label(qg, text='displayed age; stored = age − 1  (WORD at $11740)',
                 bg=T['bg_elevated'], fg=T['text_muted'],
                 font=T['font_sm']).grid(row=0, column=2, sticky='w', padx=4)
        tk.Button(qg, text='Apply Age Patch',
                  command=self._apply_age,
                  bg=T['accent'], fg=T['bg_deep'],
                  font=T['font_btn'], relief='flat', padx=8, pady=2
                  ).grid(row=0, column=3, padx=12)

        # Custom Patch form
        cf = tk.LabelFrame(self, text='  Custom Patch  ',
                           bg=T['bg_elevated'], fg=T['accent'],
                           font=T['font_sec'], bd=1, relief='flat')
        cf.pack(fill=tk.X, padx=8, pady=4)
        cg = tk.Frame(cf, bg=T['bg_elevated'])
        cg.pack(fill=tk.X, padx=8, pady=6)

        tk.Label(cg, text='Offset (hex):', bg=T['bg_elevated'],
                 fg=T['text'], font=T['font']).grid(row=0, column=0, sticky='e', padx=4)
        self._coff_var = tk.StringVar()
        ttk.Entry(cg, textvariable=self._coff_var, width=10).grid(
            row=0, column=1, sticky='w', padx=4)
        tk.Label(cg, text='Size:', bg=T['bg_elevated'],
                 fg=T['text'], font=T['font']).grid(row=0, column=2, sticky='e', padx=8)
        self._csize_var = tk.StringVar(value='B')
        for i, sz in enumerate(('B (byte)', 'W (word)', 'L (long)')):
            ttk.Radiobutton(cg, text=sz, value=sz[0],
                            variable=self._csize_var).grid(row=0, column=3 + i, padx=2)
        tk.Label(cg, text='Value (hex):', bg=T['bg_elevated'],
                 fg=T['text'], font=T['font']).grid(row=1, column=0, sticky='e', padx=4, pady=4)
        self._cval_var = tk.StringVar()
        ttk.Entry(cg, textvariable=self._cval_var, width=10).grid(
            row=1, column=1, sticky='w', padx=4)
        tk.Label(cg, text='Description:', bg=T['bg_elevated'],
                 fg=T['text'], font=T['font']).grid(row=1, column=2, sticky='e', padx=8)
        self._cdesc_var = tk.StringVar()
        ttk.Entry(cg, textvariable=self._cdesc_var, width=32).grid(
            row=1, column=3, sticky='w', padx=4, columnspan=3)
        tk.Button(cg, text='Add Patch', command=self._add_patch,
                  bg=T['accent'], fg=T['bg_deep'],
                  font=T['font_btn'], relief='flat', padx=8, pady=2
                  ).grid(row=2, column=0, columnspan=2, pady=6)

        # Space bar + actions
        bot = tk.Frame(self, bg=T['bg_deep'])
        bot.pack(fill=tk.X, padx=8, pady=6)
        self._space_var = tk.StringVar(value='Space: open a game disk to begin')
        tk.Label(bot, textvariable=self._space_var,
                 bg=T['bg_deep'], fg=T['text_muted'],
                 font=T['font_sm']).pack(side=tk.LEFT)
        tk.Button(bot, text='Write to Game Disk ADF',
                  command=self._write_adf,
                  bg=T['accent'], fg=T['bg_deep'],
                  font=T['font_btn'], relief='flat', padx=8, pady=3
                  ).pack(side=tk.RIGHT)
        tk.Button(bot, text='Preview ASM',
                  command=self._preview_asm,
                  bg=T['bg_surface'], fg=T['text'],
                  font=T['font_btn'], relief='flat', padx=8, pady=3
                  ).pack(side=tk.RIGHT, padx=(0, 6))
```

- [ ] **Step 2: Update `_refresh_list()` to use alternating row tags**

In `_refresh_list`, find the `self._tree.insert(...)` call and add alternating tags:

Current:
```python
            self._tree.insert('', 'end', values=(...))
```
Replace with:
```python
            tag = 'odd' if i % 2 == 0 else 'even'
            if 'copy' in p.description.lower() or 'protection' in p.description.lower():
                tag = 'copyprot'
            self._tree.insert('', 'end', values=(...), tags=(tag,))
```

(The `i` variable comes from `enumerate(self._patches)` — ensure `_refresh_list` uses `enumerate`.)

- [ ] **Step 3: Set themed background on the window itself**

In `PatchComposerWindow.__init__`, after `super().__init__(parent)`:
```python
        self.configure(bg=_THEME['bg_deep'])
```

- [ ] **Step 4: Run and verify**

```bash
/usr/local/bin/python3.11 PMSaveDiskTool_Mac/PMSaveDiskTool.py
```
Open Tools → Patch Composer. Verify dark chrome top bar, themed LabelFrames (orange header text), styled buttons, alternating rows in patch list.

- [ ] **Step 5: Commit**

```bash
git add PMSaveDiskTool_Mac/PMSaveDiskTool.py
git commit -m "feat: PatchComposer window — dark theme, orange LabelFrames, styled buttons"
```

---

## Task 9: LeagueDashboard + CompareSaves window themes

**Files:**
- Modify: `PMSaveDiskTool_Mac/PMSaveDiskTool.py:2439` (`LeagueDashboardWindow._build_ui`, `_build_table`)
- Modify: `PMSaveDiskTool_Mac/PMSaveDiskTool.py:2537` (`CompareSavesDialog._build_ui`)

- [ ] **Step 1: Theme `LeagueDashboardWindow`**

Replace `_build_ui` and `_build_table` method bodies:

```python
    def _build_ui(self):
        T = _THEME
        self.configure(bg=T['bg_deep'])
        tk.Label(self,
                 text=f'Save slot: {self._save.entry.name}  ({len(self._save.teams)} teams)',
                 bg=T['bg_deep'], fg=T['text'], font=('Menlo', 12, 'bold')).pack(pady=6)

        info = tk.Frame(self, bg=T['bg_deep'])
        info.pack(fill=tk.X, padx=8)
        tk.Label(info,
                 text='▲ = promotion zone (top 2)    ▼ = relegation zone (bottom 2)'
                      '    Sorted by Points, then Goals',
                 bg=T['bg_deep'], fg=T['text_muted'],
                 font=T['font_sm']).pack(side=tk.LEFT)

        # Bucket and sort
        divs = {0: [], 1: [], 2: [], 3: []}
        for team in self._save.teams:
            d = team.division
            if d in divs:
                divs[d].append(team)
        for d in divs:
            divs[d].sort(key=lambda t: (-t.league_stats[0], -t.league_stats[1]))

        nb = ttk.Notebook(self)
        nb.pack(fill=tk.BOTH, expand=True, padx=8, pady=4)

        for d in range(4):
            teams = divs[d]
            tab = tk.Frame(nb, bg=T['bg_deep'])
            label = self._DIV_NAMES.get(d, f'Div {d}') + f'  ({len(teams)})'
            nb.add(tab, text=label)
            self._build_table(tab, teams)

    def _build_table(self, parent, teams):
        T = _THEME
        cols = ('rank', 'name', 'pts', 'goals', 'value', 'zone')
        tree = ttk.Treeview(parent, columns=cols, show='headings')
        tree.heading('rank',  text='#')
        tree.heading('name',  text='Team')
        tree.heading('pts',   text='Pts')
        tree.heading('goals', text='GF')
        tree.heading('value', text='Value')
        tree.heading('zone',  text='')
        tree.column('rank',  width=40,  anchor='center')
        tree.column('name',  width=260)
        tree.column('pts',   width=60,  anchor='center')
        tree.column('goals', width=60,  anchor='center')
        tree.column('value', width=80,  anchor='center')
        tree.column('zone',  width=100, anchor='center')

        n = len(teams)
        for rank, team in enumerate(teams, 1):
            if rank <= self._PROMOTE:
                zone, tag = '▲ Promotion', 'promote'
            elif rank > n - self._RELEGATE:
                zone, tag = '▼ Relegation', 'relegate'
            else:
                zone, tag = '', 'normal'
            row_bg = 'odd' if rank % 2 == 0 else 'even'
            name = team.name or f'(team {team.index})'
            val = team.team_value_signed
            tree.insert('', 'end', tags=(tag, row_bg), values=(
                rank, name,
                team.league_stats[0],
                team.league_stats[1],
                f'{val:+d}',
                zone))

        tree.tag_configure('promote', background='#1E3E2E',
                           foreground=T['positive'])
        tree.tag_configure('relegate', background='#3E1E2E',
                           foreground=T['negative'])
        tree.tag_configure('normal',  foreground=T['text'])
        tree.tag_configure('odd',  background=T['bg_elevated'])
        tree.tag_configure('even', background=T['bg_deep'])

        vsb = ttk.Scrollbar(parent, orient='vertical', command=tree.yview)
        tree.configure(yscrollcommand=vsb.set)
        vsb.pack(side=tk.RIGHT, fill=tk.Y)
        tree.pack(fill=tk.BOTH, expand=True, padx=4, pady=4)
```

- [ ] **Step 2: Theme `CompareSavesDialog`**

Replace `_build_ui` body:

```python
    def _build_ui(self):
        T = _THEME
        self.configure(bg=T['bg_deep'])

        pick = tk.LabelFrame(self, text='  Select Two Save Slots to Compare  ',
                             bg=T['bg_elevated'], fg=T['accent'],
                             font=T['font_sec'], bd=1, relief='flat')
        pick.pack(fill=tk.X, padx=8, pady=6)
        pg = tk.Frame(pick, bg=T['bg_elevated'])
        pg.pack(fill=tk.X, padx=8, pady=8)

        names = [e.name for e in self._saves]
        tk.Label(pg, text='Save A:', bg=T['bg_elevated'],
                 fg=T['text'], font=T['font']).grid(row=0, column=0, sticky='e', padx=4)
        self._var_a = tk.StringVar()
        ttk.Combobox(pg, textvariable=self._var_a, values=names,
                     width=22, state='readonly').grid(row=0, column=1, padx=4)
        tk.Label(pg, text='Save B:', bg=T['bg_elevated'],
                 fg=T['text'], font=T['font']).grid(row=0, column=2, sticky='e', padx=12)
        self._var_b = tk.StringVar()
        ttk.Combobox(pg, textvariable=self._var_b, values=names,
                     width=22, state='readonly').grid(row=0, column=3, padx=4)
        tk.Button(pg, text='Compare →', command=self._compare,
                  bg=T['accent'], fg=T['bg_deep'],
                  font=T['font_btn'], relief='flat', padx=10, pady=3
                  ).grid(row=0, column=4, padx=12)

        res = tk.LabelFrame(self, text='  Comparison Results  ',
                            bg=T['bg_deep'], fg=T['accent'],
                            font=T['font_sec'], bd=1, relief='flat')
        res.pack(fill=tk.BOTH, expand=True, padx=8, pady=4)

        self._txt = tk.Text(res, font=('Menlo', 11), wrap='none',
                            bg='#1e1e1e', fg='#d4d4d4', state='disabled')
        self._txt.tag_configure('player', foreground=T['cyan'])
        self._txt.tag_configure('promo',  foreground=T['positive'])
        self._txt.tag_configure('relg',   foreground=T['negative'])
        self._txt.tag_configure('pos',    foreground=T['positive'])
        self._txt.tag_configure('neg',    foreground=T['negative'])
        vsb = ttk.Scrollbar(res, orient='vertical',   command=self._txt.yview)
        hsb = ttk.Scrollbar(res, orient='horizontal', command=self._txt.xview)
        self._txt.configure(yscrollcommand=vsb.set, xscrollcommand=hsb.set)
        vsb.pack(side=tk.RIGHT, fill=tk.Y)
        hsb.pack(side=tk.BOTTOM, fill=tk.X)
        self._txt.pack(fill=tk.BOTH, expand=True, padx=4, pady=4)
```

- [ ] **Step 3: Run and verify**

```bash
/usr/local/bin/python3.11 PMSaveDiskTool_Mac/PMSaveDiskTool.py
```
Open Tools → League Tables: dark window, promotion rows green-tinted, relegation rows red-tinted. Open Tools → Compare Saves: dark window with orange LabelFrame headers.

- [ ] **Step 4: Commit**

```bash
git add PMSaveDiskTool_Mac/PMSaveDiskTool.py
git commit -m "feat: LeagueDashboard + CompareSaves window themes"
```

---

## Task 10: TacticsViewer + Disassembler window themes

**Files:**
- Modify: `PMSaveDiskTool_Mac/PMSaveDiskTool.py:2711` (`TacticsViewerWindow._build_ui`)
- Modify: `PMSaveDiskTool_Mac/PMSaveDiskTool.py:2928` (`DisassemblerWindow._build_ui`)

Note: Both windows have complex `_build_ui` methods. The theme changes are primarily: add `self.configure(bg=T['bg_deep'])`, wrap `ttk.Frame` → `tk.Frame(bg=T['bg_deep'])` for outer containers, switch `ttk.Button` → `tk.Button` with explicit colours for primary/secondary distinction, and add `self.configure(bg=...)` to each window. The TacticsViewer pitch canvas stays green. The Disassembler code view already matches the dark theme.

- [ ] **Step 1: Theme `TacticsViewerWindow._build_ui`**

Add at the very start of `_build_ui` (after `def _build_ui(self):`):
```python
        T = _THEME
        self.configure(bg=T['bg_deep'])
```

Then update the outer frame creations from `ttk.Frame(self)` to `tk.Frame(self, bg=T['bg_deep'])`, and the LabelFrames to `tk.LabelFrame` with themed colours:

Find each `ttk.LabelFrame(self, text=...)` and replace with:
```python
tk.LabelFrame(self, text='  …  ', bg=T['bg_elevated'], fg=T['accent'],
              font=T['font_sec'], bd=1, relief='flat')
```

Find each `ttk.Frame(self)` outer container and replace with `tk.Frame(self, bg=T['bg_deep'])`.

Find zone selector buttons (the loop that creates `ttk.Button` per zone) and switch to:
```python
                btn = tk.Button(zone_frame, text=f'Z{z+1}',
                                command=lambda z=z: self._select_zone(z),
                                bg=T['accent'] if z == self._zone else T['bg_surface'],
                                fg=T['bg_deep'] if z == self._zone else T['text'],
                                font=T['font_sm'], relief='flat', padx=6, pady=1)
```
Store button references in `self._zone_btns` list; update colours in `_select_zone`.

Find state toggle buttons and switch to:
```python
                btn_ball = tk.Button(ctrl_frame, text='With ball',
                                     command=lambda: self._set_state(0), ...)
                btn_noball = tk.Button(ctrl_frame, text='Without ball',
                                       command=lambda: self._set_state(1), ...)
```
Active state: `bg=T['cyan']`, inactive: `bg=T['bg_surface']`.

Find the Save button and change to:
```python
tk.Button(…, bg=T['accent'], fg=T['bg_deep'], font=T['font_btn'], relief='flat')
```

- [ ] **Step 2: Update `_select_zone` and `_set_state` to refresh button colours**

At the end of `_select_zone(self, z)`:
```python
        if hasattr(self, '_zone_btns'):
            for i, btn in enumerate(self._zone_btns):
                T = _THEME
                btn.config(bg=T['accent'] if i == self._zone else T['bg_surface'],
                           fg=T['bg_deep'] if i == self._zone else T['text'])
```

At the end of `_set_state(self, s)` (or wherever state changes):
```python
        if hasattr(self, '_state_btns'):
            T = _THEME
            for i, btn in enumerate(self._state_btns):
                btn.config(bg=T['cyan'] if i == self._state else T['bg_surface'],
                           fg=T['bg_deep'] if i == self._state else T['text'])
```

- [ ] **Step 3: Theme `DisassemblerWindow._build_ui`**

Add at the very start:
```python
        T = _THEME
        self.configure(bg=T['bg_deep'])
```

Replace the nav bar `ttk.Frame(self)` with `tk.Frame(self, bg=T['bg_chrome'])` and update its label/button styles:
- Address label: `tk.Label(nav, text='Address:', bg=T['bg_chrome'], fg=T['text'], font=T['font'])`
- Go button: `tk.Button(nav, text='Go', command=self._go_to_addr, bg=T['accent'], fg=T['bg_deep'], font=T['font_btn'], relief='flat', padx=6, pady=2)`
- Back button: `tk.Button(nav, text='← Back', command=self._go_back, bg=T['bg_surface'], fg=T['text'], font=T['font_btn'], relief='flat', padx=6, pady=2)`

Replace Quick Navigation `ttk.LabelFrame(self, text=...)` with `tk.LabelFrame` themed:
```python
qf = tk.LabelFrame(self, text='  Quick Navigation  ',
                   bg=T['bg_elevated'], fg=T['accent'],
                   font=T['font_sec'], bd=1, relief='flat')
```
Each quick-jump button: `tk.Button(qg, text=label, command=..., bg=T['accent'], fg=T['bg_deep'], font=T['font_sm'], relief='flat', padx=6, pady=1)`

Replace Search LabelFrame similarly; X-Ref and Find buttons orange primary, Find MUL/DIV secondary.

Replace status label: `tk.Label(self, textvariable=self._status, bg=T['bg_chrome'], fg=T['text_muted'], font=T['font_sm'], anchor='w').pack(fill=tk.X, side=tk.BOTTOM, padx=8, pady=2)`

The `self._text` Text widget already uses `bg='#1e1e1e', fg='#d4d4d4'` — leave unchanged.

- [ ] **Step 4: Run and verify**

```bash
/usr/local/bin/python3.11 PMSaveDiskTool_Mac/PMSaveDiskTool.py
```
- Tools → Tactics Viewer: dark frame, orange zone buttons (active zone highlighted), cyan state toggle, green pitch canvas unchanged.
- Tools → Disassembler: dark chrome nav bar, orange quick-jump buttons, dark code view unchanged.

- [ ] **Step 5: Commit**

```bash
git add PMSaveDiskTool_Mac/PMSaveDiskTool.py
git commit -m "feat: TacticsViewer + Disassembler window themes — orange/cyan controls, dark chrome"
```

---

## Task 11: Push to GitHub

- [ ] **Step 1: Final smoke test**

```bash
/usr/local/bin/python3.11 PMSaveDiskTool_Mac/PMSaveDiskTool.py
```
Run through the full golden path:
1. Launch → empty state visible, game disk status in chrome bar
2. Open ADF → save slots populate
3. Select save slot → team list groups by division
4. Type in filter box → teams narrow
5. Click BAYERN MUNCHEN → team panel appears, header bar shows name/badge/value
6. Cmd+1 → Roster tab; double-click a row → inline edit; Enter → confirms
7. Cmd+2 → Team Info; edit name → Apply Changes
8. Cmd+3 → League Stats
9. Cmd+4 → Hex Dump
10. Tools → Patch Composer → dark themed
11. Tools → League Tables → promotion/relegation zone colours
12. Tools → Compare Saves → compare two saves
13. Tools → Tactics Viewer → green pitch, orange zone buttons
14. Tools → Disassembler → dark chrome, orange buttons

- [ ] **Step 2: Push**

```bash
git push origin main
```

---

## Spec coverage check

| Spec section | Tasks |
|---|---|
| `_THEME` dict | Task 1 |
| `_apply_theme()` | Task 1 |
| Title bar chrome + game disk indicator | Task 2, Task 7 |
| Toolbar (Open/Save/Save As + filename) | Task 2 |
| Sidebar — Save Slots with orange accent | Task 3 |
| Sidebar — Teams grouped by division | Task 3 |
| Sidebar — filter box | Task 3 |
| Sidebar — collapsible division groups | Task 3 |
| Team header bar (name, badge, value, budget, buttons) | Task 4 |
| Notebook with 4 tabs | Task 4 |
| Cmd+1–4 tab shortcuts | Task 4, Task 7 |
| Roster Treeview with alternating rows | Task 5 |
| Inline editing on double-click/Enter | Task 6 |
| Context menu on roster | Task 6 |
| Action bar (Set ID / Remove / counter) | Task 5, Task 6 |
| Team Info tab | Task 4 (stub), fully functional |
| League Stats tab | Task 4 (stub), fully functional |
| Hex Dump tab | Task 4 (stub), fully functional |
| Two-section status bar | Task 2 |
| Nav breadcrumb | Task 3 |
| Empty state (no file / no team) | Task 4 |
| Keyboard shortcuts (Cmd+O/S/Shift+S, Up/Down, Delete) | Task 7 |
| PatchComposer theme | Task 8 |
| LeagueDashboard theme (zone colours) | Task 9 |
| CompareSaves theme | Task 9 |
| TacticsViewer theme | Task 10 |
| Disassembler theme | Task 10 |
