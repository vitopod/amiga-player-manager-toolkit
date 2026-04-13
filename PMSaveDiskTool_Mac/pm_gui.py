#!/usr/bin/env python3
"""
pm_gui — GUI layer for PMSaveDiskTool.
All tkinter windows and the main application class.
"""

import os
import tkinter as tk
from tkinter import ttk, filedialog, messagebox, simpledialog
from pm_data import *


# ─── Theme ───────────────────────────────────────────────────────────

_THEME = {
    'bg_deep':     '#1E1E2E',
    'bg_elevated': '#2A2A3C',
    'bg_surface':  '#363650',
    'bg_chrome':   '#16162A',
    'bg_toolbar':  '#22223A',
    'accent':      '#F28C28',
    'accent2':     '#4FC3F7',
    'positive':    '#44CC44',
    'negative':    '#E57373',
    'text':        '#C8C8D0',
    'text_bright': '#FFFFFF',
    'text_muted':  '#888888',
    'text_dim':    '#555555',
    'promo_bg':    '#1E3E2E',
    'relegate_bg': '#3E1E2E',
    'font':        (_MONO, 11),
    'font_header': (_MONO, 14, 'bold'),
    'font_section':(_MONO, 10, 'bold'),
    'font_small':  (_MONO, 10),
    'font_button': (_MONO, 10, 'bold'),
}


def _apply_theme(root):
    """Configure ttk styles for the dark Amiga theme."""
    T = _THEME
    root.configure(bg=T['bg_deep'])
    s = ttk.Style()
    s.theme_use('clam')

    # Global defaults
    s.configure('.', background=T['bg_deep'], foreground=T['text'],
                font=T['font'], borderwidth=0)
    s.configure('TFrame', background=T['bg_deep'])
    s.configure('TLabel', background=T['bg_deep'], foreground=T['text'])
    s.configure('TLabelframe', background=T['bg_deep'], foreground=T['accent'])
    s.configure('TLabelframe.Label', background=T['bg_deep'],
                foreground=T['accent'], font=T['font_section'])

    # Buttons
    s.configure('TButton', background=T['bg_surface'], foreground=T['text'],
                font=T['font_button'], padding=(8, 4))
    s.map('TButton',
          background=[('active', T['bg_elevated']), ('pressed', T['bg_deep'])],
          foreground=[('disabled', T['text_dim'])])

    # Primary (orange) button
    s.configure('Primary.TButton', background=T['accent'],
                foreground=T['bg_chrome'], font=T['font_button'])
    s.map('Primary.TButton',
          background=[('active', '#E07C18'), ('pressed', '#C06C08')])

    # Danger (red) button
    s.configure('Danger.TButton', background=T['negative'],
                foreground=T['bg_chrome'], font=T['font_button'])
    s.map('Danger.TButton',
          background=[('active', '#C05555'), ('pressed', '#A04040')])

    # Entry
    s.configure('TEntry', fieldbackground=T['bg_elevated'],
                foreground=T['text_bright'], insertcolor=T['text_bright'],
                bordercolor=T['bg_surface'], lightcolor=T['bg_surface'],
                darkcolor=T['bg_surface'])

    # Combobox
    s.configure('TCombobox', fieldbackground=T['bg_elevated'],
                foreground=T['text_bright'], selectbackground=T['bg_surface'],
                selectforeground=T['text_bright'],
                arrowcolor=T['text_muted'])
    s.map('TCombobox',
          fieldbackground=[('readonly', T['bg_elevated'])],
          foreground=[('readonly', T['text_bright'])])
    # Combobox dropdown list
    root.option_add('*TCombobox*Listbox.background', T['bg_elevated'])
    root.option_add('*TCombobox*Listbox.foreground', T['text_bright'])
    root.option_add('*TCombobox*Listbox.selectBackground', T['accent'])
    root.option_add('*TCombobox*Listbox.selectForeground', T['bg_chrome'])

    # Spinbox
    s.configure('TSpinbox', fieldbackground=T['bg_elevated'],
                foreground=T['text_bright'], arrowcolor=T['text_muted'],
                bordercolor=T['bg_surface'])

    # Notebook
    s.configure('TNotebook', background=T['bg_deep'], borderwidth=0)
    s.configure('TNotebook.Tab', background=T['bg_deep'],
                foreground=T['text_muted'], padding=(12, 4),
                font=T['font_button'])
    s.map('TNotebook.Tab',
          background=[('selected', T['bg_elevated'])],
          foreground=[('selected', T['accent'])])

    # Treeview
    s.configure('Treeview', background=T['bg_deep'],
                foreground=T['text'], fieldbackground=T['bg_deep'],
                font=T['font'], rowheight=22, borderwidth=0)
    s.configure('Treeview.Heading', background=T['bg_elevated'],
                foreground=T['text_muted'], font=T['font_section'],
                borderwidth=1, relief='flat')
    s.map('Treeview',
          background=[('selected', T['bg_surface'])],
          foreground=[('selected', T['accent'])])

    # Scrollbar
    s.configure('TScrollbar', background=T['bg_deep'],
                troughcolor=T['bg_deep'], arrowcolor=T['text_dim'],
                borderwidth=0)
    s.map('TScrollbar',
          background=[('active', T['bg_surface']),
                      ('!active', T['bg_surface'])])

    # Separator
    s.configure('TSeparator', background=T['bg_surface'])

    # Checkbutton
    s.configure('TCheckbutton', background=T['bg_deep'],
                foreground=T['text'])
    s.map('TCheckbutton',
          background=[('active', T['bg_deep'])])

    # Panedwindow
    s.configure('TPanedwindow', background=T['bg_surface'])
    s.configure('Sash', sashthickness=4)

    # Listbox (tk, not ttk — configure via root option_add)
    root.option_add('*Listbox.background', T['bg_elevated'])
    root.option_add('*Listbox.foreground', T['text_bright'])
    root.option_add('*Listbox.selectBackground', T['accent'])
    root.option_add('*Listbox.selectForeground', T['bg_chrome'])
    root.option_add('*Listbox.highlightThickness', 0)
    root.option_add('*Listbox.borderWidth', 0)
    root.option_add('*Listbox.relief', 'flat')


# ─── Shared GUI Helpers ─────────────────────────────────────────────

def _make_scrolled_tree(parent, columns, headings, widths, anchors=None,
                        on_double_click=None, heading_command=None, hscroll=False):
    """Build a Treeview with vertical scrollbar (optional horizontal).

    Returns the tree widget.  The tree has a ``_pid_map`` dict attribute
    that callers can use to map iid → player_id.
    """
    frame = ttk.Frame(parent)
    frame.pack(fill=tk.BOTH, expand=True, padx=4, pady=4)
    tree = ttk.Treeview(frame, columns=columns, show='headings')
    for col, hd, w in zip(columns, headings, widths):
        anc = (anchors or {}).get(col, 'center')
        cmd = (lambda c=col: heading_command(c)) if heading_command else ''
        tree.heading(col, text=hd, command=cmd)
        tree.column(col, width=w, anchor=anc)
    vsb = ttk.Scrollbar(frame, orient='vertical', command=tree.yview)
    tree.configure(yscrollcommand=vsb.set)
    if hscroll:
        hsb = ttk.Scrollbar(frame, orient='horizontal', command=tree.xview)
        tree.configure(xscrollcommand=hsb.set)
        hsb.pack(side=tk.BOTTOM, fill=tk.X)
    vsb.pack(side=tk.RIGHT, fill=tk.Y)
    tree.pack(fill=tk.BOTH, expand=True)
    tree._pid_map = {}
    # Alternating row colors for dark theme
    T = _THEME
    tree.tag_configure('oddrow',  background=T['bg_elevated'])
    tree.tag_configure('evenrow', background=T['bg_deep'])
    if on_double_click:
        tree.bind('<Double-1>', on_double_click)
    return tree



class PMSaveDiskToolApp:
    def __init__(self, root):
        self.root = root
        self.root.title("PM Save Disk Tool")
        self.root.geometry("1060x800")

        self.adf = None
        self.dir_entries = []
        self.liga_names = []      # Canonical team names from LigaName.nam
        self.current_save = None
        self.current_team = None
        self.game_disk = None     # GameDisk instance (auto-loaded from script dir)

        self._build_menu()
        self._build_ui()

        # Auto-load game disk if found next to the script
        game_path = _find_game_disk()
        if game_path:
            try:
                self.game_disk = GameDisk(game_path)
                n = len(self.game_disk.player_names)
                self._gd_status.config(
                    text=f"Game disk: {os.path.basename(game_path)} ({n} names)",
                    fg=_THEME['positive'])
                self.status_var.set(
                    f"Game disk loaded: {os.path.basename(game_path)} \u2014 "
                    f"{n} player names extracted")
            except Exception as e:
                self._gd_status.config(text=f"Game disk error", fg=_THEME['negative'])
                self.status_var.set(f"Game disk error: {e}")
        else:
            self._gd_status.config(text="No game disk found", fg=_THEME['text_dim'])

    # ── Menu ──

    def _build_menu(self):
        menubar = tk.Menu(self.root)

        file_menu = tk.Menu(menubar, tearoff=0)
        file_menu.add_command(label="Open ADF…", command=self.open_adf, accelerator=f"{_MOD_DISP}O")
        file_menu.add_command(label="Save ADF", command=self.save_adf, accelerator=f"{_MOD_DISP}S")
        file_menu.add_command(label="Save ADF As…", command=self.save_adf_as, accelerator=f"{_MOD_DISP}Shift+S")
        file_menu.add_separator()
        file_menu.add_command(label="Export Save as Binary…", command=self.export_save)
        file_menu.add_separator()
        file_menu.add_command(label="Quit", command=self.root.quit, accelerator=f"{_MOD_DISP}Q")
        menubar.add_cascade(label="File", menu=file_menu)

        tools_menu = tk.Menu(menubar, tearoff=0)
        tools_menu.add_command(label="Hex Viewer…", command=self.hex_viewer)
        tools_menu.add_command(label="Disk Info", command=self.show_disk_info)
        tools_menu.add_separator()
        tools_menu.add_command(label="Patch Composer…", command=self.open_patch_composer)
        tools_menu.add_separator()
        tools_menu.add_command(label="League Tables…", command=self.show_league_tables)
        tools_menu.add_command(label="Compare Saves…", command=self.show_compare_saves)
        tools_menu.add_command(label="Championship Highlights…", command=self.show_highlights)
        tools_menu.add_command(label="Transfer Market…", command=self.show_transfer_market)
        tools_menu.add_separator()
        tools_menu.add_command(label="Tactics Viewer…", command=self.show_tactics_viewer)
        tools_menu.add_command(label="Disassembler…", command=self.show_disassembler)
        menubar.add_cascade(label="Tools", menu=tools_menu)

        self.root.config(menu=menubar)

        # Key bindings
        self.root.bind_all(f'<{_MOD}-o>', lambda e: self.open_adf())
        self.root.bind_all(f'<{_MOD}-s>', lambda e: self.save_adf())

        # Tab shortcuts (Cmd+1-4)
        for i in range(4):
            self.root.bind_all(
                f'<{_MOD}-Key-{i + 1}>',
                lambda e, idx=i: self._nb.select(idx) if hasattr(self, '_nb') else None)

    # ── Layout ──

    def _build_ui(self):
        T = _THEME

        # ── Title bar ──
        title_bar = tk.Frame(self.root, bg=T['bg_chrome'], height=32)
        title_bar.pack(fill=tk.X)
        title_bar.pack_propagate(False)

        tk.Label(title_bar, text="PM", font=(_MONO, 14, 'bold'),
                 bg=T['bg_chrome'], fg=T['accent']).pack(side=tk.LEFT, padx=(10, 4))
        tk.Label(title_bar, text="Save Disk Tool", font=(_MONO, 11),
                 bg=T['bg_chrome'], fg=T['text_muted']).pack(side=tk.LEFT)

        self._gd_status = tk.Label(title_bar, text="", font=T['font_small'],
                                   bg=T['bg_chrome'], fg=T['text_dim'])
        self._gd_status.pack(side=tk.RIGHT, padx=10)

        # ── Toolbar ──
        toolbar = tk.Frame(self.root, bg=T['bg_toolbar'], height=36)
        toolbar.pack(fill=tk.X)
        toolbar.pack_propagate(False)

        ttk.Button(toolbar, text="Open ADF", style='Primary.TButton',
                   command=self.open_adf).pack(side=tk.LEFT, padx=(8, 4), pady=4)
        ttk.Button(toolbar, text="Save", command=self.save_adf).pack(
            side=tk.LEFT, padx=2, pady=4)
        ttk.Button(toolbar, text="Save As\u2026", command=self.save_adf_as).pack(
            side=tk.LEFT, padx=2, pady=4)

        self.filename_var = tk.StringVar(value="No file loaded")
        tk.Label(toolbar, textvariable=self.filename_var, font=T['font_small'],
                 bg=T['bg_toolbar'], fg=T['text_muted']).pack(
            side=tk.LEFT, padx=(12, 0))

        # ── Body ──
        body = ttk.Frame(self.root)
        body.pack(fill=tk.BOTH, expand=True)

        # -- Sidebar (fixed 250px) --
        sidebar = tk.Frame(body, bg=T['bg_elevated'], width=250)
        sidebar.pack(side=tk.LEFT, fill=tk.Y)
        sidebar.pack_propagate(False)

        # Save Slots section
        tk.Label(sidebar, text="SAVE SLOTS", font=T['font_section'],
                 bg=T['bg_elevated'], fg=T['accent']).pack(
            anchor='w', padx=8, pady=(8, 2))

        self.saves_listbox = tk.Listbox(sidebar, height=5, exportselection=False,
                                        font=T['font_small'],
                                        bg=T['bg_deep'], fg=T['text_bright'],
                                        selectbackground=T['accent'],
                                        selectforeground=T['bg_chrome'],
                                        highlightthickness=0, borderwidth=0,
                                        relief='flat')
        self.saves_listbox.pack(fill=tk.X, padx=8, pady=(0, 4))
        self.saves_listbox.bind('<<ListboxSelect>>', self.on_save_select)

        # Teams section
        self._teams_label = tk.Label(sidebar, text="TEAMS", font=T['font_section'],
                                     bg=T['bg_elevated'], fg=T['accent2'])
        self._teams_label.pack(anchor='w', padx=8, pady=(8, 2))

        # Filter entry
        self._filter_var = tk.StringVar()
        self._filter_var.trace_add('write', lambda *_a: self._filter_teams())
        filter_entry = tk.Entry(sidebar, textvariable=self._filter_var,
                                font=T['font_small'],
                                bg=T['bg_deep'], fg=T['text_bright'],
                                insertbackground=T['text_bright'],
                                highlightthickness=0, borderwidth=1,
                                relief='flat')
        filter_entry.pack(fill=tk.X, padx=8, pady=(0, 4))

        # Division-grouped teams tree
        teams_container = tk.Frame(sidebar, bg=T['bg_elevated'])
        teams_container.pack(fill=tk.BOTH, expand=True, padx=0, pady=0)

        self.teams_tree = ttk.Treeview(teams_container, columns=("name",),
                                       show='tree', selectmode='browse')
        self.teams_tree.heading('#0', text='')
        self.teams_tree.column('#0', width=40, stretch=False)
        self.teams_tree.column('name', width=200, stretch=True)
        self.teams_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        teams_sb = ttk.Scrollbar(teams_container, orient='vertical',
                                 command=self.teams_tree.yview)
        self.teams_tree.configure(yscrollcommand=teams_sb.set)
        teams_sb.pack(side=tk.RIGHT, fill=tk.Y)

        self.teams_tree.bind('<<TreeviewSelect>>', self.on_team_select)

        # Division group nodes
        self._div_nodes = {}
        for d in range(4):
            node = self.teams_tree.insert('', 'end', text=f"Division {d + 1}",
                                          values=('',), open=True,
                                          tags=('divheader',))
            self._div_nodes[d] = node

        self.teams_tree.tag_configure('divheader',
                                      background=T['bg_surface'],
                                      foreground=T['accent2'],
                                      font=T['font_section'])
        self.teams_tree.tag_configure('teamrow',
                                      foreground=T['text'])
        self.teams_tree.tag_configure('teamrow_odd',
                                      background=T['bg_elevated'],
                                      foreground=T['text'])

        # -- Right panel --
        right = tk.Frame(body, bg=T['bg_deep'])
        right.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        # Team header bar (hidden initially)
        self._team_hdr_frame = tk.Frame(right, bg=T['bg_chrome'], height=44)
        self._team_hdr_lbl = tk.Label(self._team_hdr_frame, text="",
                                      font=T['font_header'],
                                      bg=T['bg_chrome'], fg=T['text_bright'])
        self._team_hdr_lbl.pack(side=tk.LEFT, padx=12)
        self._team_hdr_div = tk.Label(self._team_hdr_frame, text="",
                                      font=T['font_small'],
                                      bg=T['bg_chrome'], fg=T['accent2'])
        self._team_hdr_div.pack(side=tk.LEFT, padx=4)

        ttk.Button(self._team_hdr_frame, text="Apply Changes",
                   style='Primary.TButton',
                   command=self.apply_team_changes).pack(
            side=tk.RIGHT, padx=(4, 12), pady=6)
        ttk.Button(self._team_hdr_frame, text="Become Manager",
                   command=self.become_manager).pack(
            side=tk.RIGHT, padx=4, pady=6)

        # Empty state (shown initially)
        self._empty_frame = tk.Frame(right, bg=T['bg_deep'])
        self._empty_frame.pack(fill=tk.BOTH, expand=True)
        tk.Label(self._empty_frame, text="Open an ADF and select a team",
                 font=(_MONO, 13), bg=T['bg_deep'], fg=T['text_dim']).pack(
            expand=True)

        # Notebook (hidden initially)
        self._nb = ttk.Notebook(right)

        # Build tabs
        roster_frame = ttk.Frame(self._nb)
        info_frame = ttk.Frame(self._nb)
        stats_frame = ttk.Frame(self._nb)
        hex_frame = ttk.Frame(self._nb)

        self._build_roster_tab(roster_frame)
        self._build_team_info_tab(info_frame)
        self._build_stats_tab(stats_frame)
        self._build_hex_tab(hex_frame)

        self._nb.add(roster_frame, text=f" {_MOD_DISP}1 Roster ")
        self._nb.add(info_frame,   text=f" {_MOD_DISP}2 Team Info ")
        self._nb.add(stats_frame,  text=f" {_MOD_DISP}3 Stats ")
        self._nb.add(hex_frame,    text=f" {_MOD_DISP}4 Hex Dump ")

        self._tab_names = ['Roster', 'Team Info', 'Stats', 'Hex Dump']
        self._nb.bind('<<NotebookTabChanged>>', self._on_tab_changed)

        # ── Status bar ──
        status_bar = tk.Frame(self.root, bg=T['bg_chrome'], height=24)
        status_bar.pack(fill=tk.X, side=tk.BOTTOM)
        status_bar.pack_propagate(False)

        self.status_var = tk.StringVar(value="Ready \u2014 Open an ADF to begin")
        tk.Label(status_bar, textvariable=self.status_var, font=T['font_small'],
                 bg=T['bg_chrome'], fg=T['text_muted'], anchor='w').pack(
            side=tk.LEFT, padx=8, fill=tk.X, expand=True)

        self.nav_var = tk.StringVar(value="")
        tk.Label(status_bar, textvariable=self.nav_var, font=T['font_small'],
                 bg=T['bg_chrome'], fg=T['text_dim'], anchor='e').pack(
            side=tk.RIGHT, padx=8)

    # ── Tab builders ──

    def _build_roster_tab(self, parent):
        T = _THEME

        # Action bar
        action = tk.Frame(parent, bg=T['bg_deep'])
        action.pack(fill=tk.X, padx=8, pady=(8, 4))

        ttk.Button(action, text="Edit ID", command=self._set_player_id_btn).pack(
            side=tk.LEFT, padx=(0, 4))
        ttk.Button(action, text="Remove", command=self._remove_player_btn).pack(
            side=tk.LEFT, padx=4)

        self._roster_count = tk.Label(action, text="0/25", font=T['font_small'],
                                      bg=T['bg_deep'], fg=T['text_muted'])
        self._roster_count.pack(side=tk.RIGHT, padx=8)

        # Roster treeview
        cols = ("slot", "id", "name")
        tree_frame = ttk.Frame(parent)
        tree_frame.pack(fill=tk.BOTH, expand=True, padx=8, pady=(0, 8))

        self.roster_tree = ttk.Treeview(tree_frame, columns=cols, show='headings',
                                        height=20)
        self.roster_tree.heading("slot", text="Slot")
        self.roster_tree.heading("id", text="ID")
        self.roster_tree.heading("name", text="Player Name")
        self.roster_tree.column("slot", width=50, anchor='center')
        self.roster_tree.column("id", width=70, anchor='center')
        self.roster_tree.column("name", width=200, anchor='w')

        rsb = ttk.Scrollbar(tree_frame, orient='vertical',
                            command=self.roster_tree.yview)
        self.roster_tree.configure(yscrollcommand=rsb.set)
        rsb.pack(side=tk.RIGHT, fill=tk.Y)
        self.roster_tree.pack(fill=tk.BOTH, expand=True)

        self.roster_tree.tag_configure('oddrow', background=T['bg_elevated'])
        self.roster_tree.tag_configure('evenrow', background=T['bg_deep'])
        self.roster_tree.tag_configure('empty', foreground=T['text_dim'])
        self.roster_tree.bind('<Double-1>', self._start_inline_edit)

        self._player_ids = [0xFFFF] * MAX_PLAYER_SLOTS
        self._inline_entry = None

    def _build_team_info_tab(self, parent):
        T = _THEME
        grid = ttk.Frame(parent)
        grid.pack(fill=tk.X, padx=16, pady=16)

        self.team_name_var = tk.StringVar()
        self.division_var = tk.StringVar()
        self.word62_var = tk.StringVar()
        self.word64_var = tk.StringVar()

        row = 0
        ttk.Label(grid, text="Team Name:").grid(row=row, column=0, sticky='e', padx=4, pady=4)
        ttk.Entry(grid, textvariable=self.team_name_var, width=24).grid(
            row=row, column=1, sticky='w', padx=4)

        ttk.Label(grid, text="Division:").grid(row=row, column=2, sticky='e', padx=8)
        div_combo = ttk.Combobox(grid, textvariable=self.division_var, width=12,
                                 values=["0 (Div 1)", "1 (Div 2)", "2 (Div 3)", "3 (Div 4)"])
        div_combo.grid(row=row, column=3, sticky='w', padx=4)

        row += 1
        ttk.Label(grid, text="Team Value:").grid(row=row, column=0, sticky='e', padx=4, pady=4)
        ttk.Entry(grid, textvariable=self.word62_var, width=8).grid(
            row=row, column=1, sticky='w', padx=4)
        ttk.Label(grid, text="Budget Tier:").grid(row=row, column=2, sticky='e', padx=8)
        ttk.Entry(grid, textvariable=self.word64_var, width=8).grid(
            row=row, column=3, sticky='w', padx=4)

    def _build_stats_tab(self, parent):
        grid = ttk.Frame(parent)
        grid.pack(fill=tk.X, padx=16, pady=16)

        self.stat_vars = []
        stat_labels = TeamRecord.STAT_LABELS
        for i, label in enumerate(stat_labels):
            ttk.Label(grid, text=f"{label}:").grid(
                row=i // 3, column=(i % 3) * 2, sticky='e', padx=4, pady=4)
            var = tk.StringVar()
            self.stat_vars.append(var)
            ttk.Entry(grid, textvariable=var, width=8).grid(
                row=i // 3, column=(i % 3) * 2 + 1, sticky='w', padx=4)

    def _build_hex_tab(self, parent):
        T = _THEME
        self.hex_text = tk.Text(parent, height=8, font=(_MONO, 11), state='disabled',
                                wrap='none', bg=T['bg_chrome'], fg='#00FF88',
                                insertbackground=T['text_bright'],
                                highlightthickness=0, borderwidth=0)
        self.hex_text.pack(fill=tk.BOTH, expand=True, padx=8, pady=8)

    # ── Sidebar helpers ──

    def _filter_teams(self):
        """Filter teams tree by the text in the filter entry."""
        query = self._filter_var.get().strip().lower()
        if not self.current_save:
            return

        # Re-populate tree with matching teams
        for node in self._div_nodes.values():
            for child in self.teams_tree.get_children(node):
                self.teams_tree.delete(child)

        counts = {d: 0 for d in range(4)}
        for team in self.current_save.teams:
            name = team.name if team.name else f"(record {team.index})"
            if query and query not in name.lower():
                continue
            d = team.division if team.division is not None else 0
            if d < 0 or d > 3:
                d = 0
            tag = 'teamrow' if counts[d] % 2 == 0 else 'teamrow_odd'
            self.teams_tree.insert(self._div_nodes[d], 'end',
                                   iid=f"team_{team.index}",
                                   text=f"{team.index:2d}",
                                   values=(name,), tags=(tag,))
            counts[d] += 1

    def _show_team_header(self, team):
        """Show team header bar and notebook, hide empty state."""
        T = _THEME
        name = team.name if team.name else f"(record {team.index})"
        div = team.division
        div_str = f"Division {div + 1}" if div is not None else f"Div ?"

        self._team_hdr_lbl.config(text=name)
        self._team_hdr_div.config(text=div_str)

        self._empty_frame.pack_forget()
        self._team_hdr_frame.pack(fill=tk.X)
        self._team_hdr_frame.pack_propagate(False)
        self._nb.pack(fill=tk.BOTH, expand=True)

        self.nav_var.set(f"{name} > Roster")

    def _on_tab_changed(self, event=None):
        """Update nav breadcrumb when tab changes."""
        if not self.current_team:
            return
        try:
            idx = self._nb.index(self._nb.select())
            tab_name = self._tab_names[idx]
        except (tk.TclError, IndexError):
            return
        name = self.current_team.name if self.current_team.name else f"(record {self.current_team.index})"
        self.nav_var.set(f"{name} > {tab_name}")

    # ── Inline roster editing ──

    def _start_inline_edit(self, event=None):
        """Begin inline editing of the ID column on the selected roster row."""
        sel = self.roster_tree.selection()
        if not sel:
            return
        item = sel[0]

        # Identify the ID column
        col_id = self.roster_tree.identify_column(event.x) if event else '#2'
        if col_id != '#2':
            return

        bbox = self.roster_tree.bbox(item, column='id')
        if not bbox:
            return

        x, y, w, h = bbox
        T = _THEME

        self._cancel_inline_edit()

        entry = tk.Entry(self.roster_tree, font=T['font'],
                         bg=T['bg_elevated'], fg=T['text_bright'],
                         insertbackground=T['text_bright'],
                         highlightthickness=1,
                         highlightcolor=T['accent'],
                         borderwidth=0)
        current_val = self.roster_tree.set(item, 'id')
        entry.insert(0, current_val)
        entry.select_range(0, tk.END)
        entry.place(x=x, y=y, width=w, height=h)
        entry.focus_set()

        entry.bind('<Return>', lambda e: self._confirm_inline_edit(item, entry))
        entry.bind('<Escape>', lambda e: self._cancel_inline_edit())
        entry.bind('<FocusOut>', lambda e: self._cancel_inline_edit())

        self._inline_entry = entry

    def _confirm_inline_edit(self, item, entry):
        """Apply inline edit — update player ID."""
        val_str = entry.get().strip().upper()
        entry.destroy()
        self._inline_entry = None

        try:
            slot_str = self.roster_tree.set(item, 'slot')
            slot = int(slot_str)
        except (ValueError, KeyError):
            return

        try:
            if val_str == 'FFFF' or val_str == '0XFFFF':
                pid = 0xFFFF
            elif val_str.startswith('0X'):
                pid = int(val_str, 16)
            else:
                pid = int(val_str)
        except ValueError:
            return

        self._player_ids[slot] = pid

        # Update display
        if pid == 0xFFFF:
            self.roster_tree.set(item, 'id', 'FFFF')
            self.roster_tree.set(item, 'name', '\u2014')
            self.roster_tree.item(item, tags=('empty',))
        else:
            self.roster_tree.set(item, 'id', str(pid))
            name = player_name_str(self.game_disk, pid)
            self.roster_tree.set(item, 'name', name)
            tag = 'oddrow' if slot % 2 else 'evenrow'
            self.roster_tree.item(item, tags=(tag,))

        self._update_roster_count()

    def _cancel_inline_edit(self):
        """Cancel any active inline edit."""
        if self._inline_entry:
            self._inline_entry.destroy()
            self._inline_entry = None

    def _set_player_id_btn(self):
        """Trigger inline edit on the currently selected roster row."""
        sel = self.roster_tree.selection()
        if not sel:
            return

        item = sel[0]
        bbox = self.roster_tree.bbox(item, column='id')
        if not bbox:
            return

        # Create a fake event-like trigger
        class _FakeEvent:
            pass
        evt = _FakeEvent()
        evt.x = bbox[0] + 1
        self._start_inline_edit(evt)

    def _remove_player_btn(self):
        """Set the selected roster slot to FFFF (empty)."""
        sel = self.roster_tree.selection()
        if not sel:
            return
        item = sel[0]
        try:
            slot = int(self.roster_tree.set(item, 'slot'))
        except (ValueError, KeyError):
            return

        self._player_ids[slot] = 0xFFFF
        self.roster_tree.set(item, 'id', 'FFFF')
        self.roster_tree.set(item, 'name', '\u2014')
        self.roster_tree.item(item, tags=('empty',))
        self._update_roster_count()

    def _update_roster_count(self):
        """Update the N/25 roster count label."""
        n = sum(1 for pid in self._player_ids if pid != 0xFFFF)
        self._roster_count.config(text=f"{n}/{MAX_PLAYER_SLOTS}")

    # ── File operations ──

    def open_adf(self):
        path = filedialog.askopenfilename(
            title="Open Player Manager ADF",
            filetypes=[("ADF files", "*.adf"), ("All files", "*.*")]
        )
        if not path:
            return

        try:
            self.adf = ADF(path)
        except Exception as e:
            messagebox.showerror("Error", f"Could not open file:\n{e}")
            return

        self.filename_var.set(os.path.basename(path))

        # Check if it's a save disk by looking at sector 2 for the file table
        try:
            self.dir_entries = parse_file_table(self.adf)
        except Exception:
            self.dir_entries = []

        if not self.dir_entries:
            messagebox.showinfo("Info",
                "No save file table found in sector 2.\n"
                "This may be a game disk, not a save/data disk.\n\n"
                "Use Tools → Hex Viewer to inspect the disk.")
            self.status_var.set(f"Loaded: {os.path.basename(path)} ({self.adf.filesystem_type}) — no save table found")
            return

        # Load canonical team names
        self.liga_names = parse_liga_names(self.adf, self.dir_entries)

        # Populate save slots (include .sav and .dat files)
        self.saves_listbox.delete(0, tk.END)
        save_entries = [e for e in self.dir_entries
                        if e.name.endswith('.sav') or e.name.endswith('.dat')]
        for e in save_entries:
            tag = " [template]" if e.name.endswith('.dat') else ""
            self.saves_listbox.insert(tk.END, f"{e.name}  ({e.size_bytes} bytes){tag}")

        self.status_var.set(
            f"Loaded: {os.path.basename(path)} ({self.adf.filesystem_type}) — "
            f"{len(self.dir_entries)} files, {len(save_entries)} saves"
            f"{', ' + str(len(self.liga_names)) + ' team names' if self.liga_names else ''}")

    def save_adf(self):
        if not self.adf:
            return
        try:
            self.adf.save()
            self.status_var.set(f"Saved: {os.path.basename(self.adf.path)}")
        except Exception as e:
            messagebox.showerror("Error", f"Could not save:\n{e}")

    def save_adf_as(self):
        if not self.adf:
            return
        path = filedialog.asksaveasfilename(
            title="Save ADF As",
            defaultextension=".adf",
            filetypes=[("ADF files", "*.adf"), ("All files", "*.*")]
        )
        if path:
            try:
                self.adf.save(path)
                self.adf.path = path
                self.filename_var.set(os.path.basename(path))
                self.status_var.set(f"Saved as: {os.path.basename(path)}")
            except Exception as e:
                messagebox.showerror("Error", f"Could not save:\n{e}")

    def export_save(self):
        if not self.current_save:
            messagebox.showinfo("Info", "Select a save slot first.")
            return
        path = filedialog.asksaveasfilename(
            title="Export Save Data",
            defaultextension=".bin",
            initialfile=self.current_save.entry.name.replace('.sav', '.bin')
        )
        if path:
            with open(path, 'wb') as f:
                f.write(bytes(self.current_save.data))
            self.status_var.set(f"Exported {len(self.current_save.data)} bytes to {os.path.basename(path)}")

    # ── Selection handlers ──

    def on_save_select(self, event):
        sel = self.saves_listbox.curselection()
        if not sel:
            return
        idx = sel[0]
        save_entries = [e for e in self.dir_entries
                        if e.name.endswith('.sav') or e.name.endswith('.dat')]
        entry = save_entries[idx]

        try:
            self.current_save = SaveFile(self.adf, entry)
        except Exception as e:
            messagebox.showerror("Error", f"Could not parse save:\n{e}")
            return

        # Clear filter
        self._filter_var.set("")

        # Populate division-grouped teams tree
        for node in self._div_nodes.values():
            for child in self.teams_tree.get_children(node):
                self.teams_tree.delete(child)

        counts = {d: 0 for d in range(4)}
        for team in self.current_save.teams:
            name = team.name if team.name else f"(record {team.index})"
            d = team.division if team.division is not None else 0
            if d < 0 or d > 3:
                d = 0
            tag = 'teamrow' if counts[d] % 2 == 0 else 'teamrow_odd'
            self.teams_tree.insert(self._div_nodes[d], 'end',
                                   iid=f"team_{team.index}",
                                   text=f"{team.index:2d}",
                                   values=(name,), tags=(tag,))
            counts[d] += 1

        total = len(self.current_save.teams)
        self._teams_label.config(text=f"TEAMS ({total})")

        self.status_var.set(
            f"Save: {entry.name} \u2014 {total} teams, "
            f"{entry.size_bytes} bytes")

    def on_team_select(self, event):
        sel = self.teams_tree.selection()
        if not sel or not self.current_save:
            return

        item_id = sel[0]
        # Ignore division header clicks
        if item_id in self._div_nodes.values():
            return

        # Extract team index from iid "team_N"
        if not item_id.startswith("team_"):
            return
        try:
            idx = int(item_id.split("_", 1)[1])
        except (ValueError, IndexError):
            return

        team = None
        for t in self.current_save.teams:
            if t.index == idx:
                team = t
                break
        if not team:
            return

        self.current_team = team
        self._show_team_header(team)
        self._display_team(team)

    def _display_team(self, team):
        self.team_name_var.set(team.name)
        div = team.division
        if div is not None:
            self.division_var.set(f"{div} (Div {div + 1})")
        else:
            self.division_var.set(f"{team.word_66:#06x}")
        self.word62_var.set(f"{team.team_value_signed}")
        self.word64_var.set(str(team.word_64))

        for i, var in enumerate(self.stat_vars):
            var.set(str(team.league_stats[i]))

        # Populate roster tree
        self.roster_tree.delete(*self.roster_tree.get_children())
        self._player_ids = list(team.player_values)
        for i in range(MAX_PLAYER_SLOTS):
            v = team.player_values[i]
            if v == 0xFFFF:
                self.roster_tree.insert('', 'end',
                                        values=(i, 'FFFF', '\u2014'),
                                        tags=('empty',))
            else:
                name = player_name_str(self.game_disk, v)
                tag = 'oddrow' if i % 2 else 'evenrow'
                self.roster_tree.insert('', 'end',
                                        values=(i, str(v), name),
                                        tags=(tag,))

        self._update_roster_count()

        # Hex dump
        self.hex_text.config(state='normal')
        self.hex_text.delete('1.0', tk.END)

        hex_lines = []
        for i in range(0, len(team.raw), 16):
            chunk = team.raw[i:i + 16]
            hex_str = ' '.join(f'{b:02X}' for b in chunk)
            asc_str = ''.join(chr(b) if 32 <= b < 127 else '\u00b7' for b in chunk)
            hex_lines.append(f"+{i:03d}  {hex_str:<48s}  {asc_str}")

        self.hex_text.insert('1.0', '\n'.join(hex_lines))
        self.hex_text.config(state='disabled')

    # ── Editing ──

    def apply_team_changes(self):
        if not self.current_team or not self.current_save:
            return

        team = self.current_team

        # Team name
        new_name = self.team_name_var.get().strip()
        max_name_len = 100 - TEAM_NAME_OFFSET - 1
        if len(new_name) > max_name_len:
            messagebox.showwarning("Warning", f"Name too long (max {max_name_len} chars)")
            return
        team.name = new_name

        # Division
        try:
            div_str = self.division_var.get().strip()
            team.word_66 = int(div_str.split()[0])
        except (ValueError, IndexError):
            pass

        # Team value (signed → unsigned)
        try:
            v = int(self.word62_var.get().strip())
            team.word_62 = v & 0xFFFF
        except ValueError:
            pass

        # Budget tier
        try:
            team.word_64 = int(self.word64_var.get().strip())
        except ValueError:
            pass

        # League stats
        for i, var in enumerate(self.stat_vars):
            try:
                team.league_stats[i] = int(var.get().strip())
            except ValueError:
                pass

        # Player values from roster
        for i in range(MAX_PLAYER_SLOTS):
            team.player_values[i] = self._player_ids[i]

        # Write back
        self.current_save.write_back()
        self._display_team(team)

        # Refresh sidebar tree
        item_id = f"team_{team.index}"
        if self.teams_tree.exists(item_id):
            name = team.name if team.name else f"(record {team.index})"
            self.teams_tree.item(item_id, values=(name,))

        self._show_team_header(team)
        self.status_var.set(f"Applied changes to {team.name}")

    def become_manager(self):
        if not self.current_team:
            return
        messagebox.showinfo("Become Manager",
            f"To become manager of {self.current_team.name}:\n\n"
            f"This team is record #{self.current_team.index}.\n"
            f"The manager team assignment is stored in the game's runtime data.\n\n"
            f"For the Italian version, the manager team index can be patched\n"
            f"in the game disk's Patch block (block 1137).\n\n"
            f"Word 64 = {self.current_team.word_64:#06x} may be related to\n"
            f"team assignment in the save data.")

    # ── Tools ──

    def hex_viewer(self):
        if not self.adf:
            messagebox.showinfo("Info", "Open an ADF first.")
            return

        T = _THEME
        win = tk.Toplevel(self.root)
        win.title("Hex Viewer")
        win.geometry("820x600")
        win.configure(bg=T['bg_deep'])

        ctrl = tk.Frame(win, bg=T['bg_deep'])
        ctrl.pack(fill=tk.X, padx=8, pady=4)

        tk.Label(ctrl, text="Sector:", bg=T['bg_deep'], fg=T['text_muted'], font=T['font_small']).pack(side=tk.LEFT)
        sector_var = tk.StringVar(value="0")
        sector_entry = ttk.Entry(ctrl, textvariable=sector_var, width=6)
        sector_entry.pack(side=tk.LEFT, padx=4)

        tk.Label(ctrl, text="or Byte offset:", bg=T['bg_deep'], fg=T['text_muted'], font=T['font_small']).pack(side=tk.LEFT, padx=(8, 0))
        offset_var = tk.StringVar(value="")
        offset_entry = ttk.Entry(ctrl, textvariable=offset_var, width=10)
        offset_entry.pack(side=tk.LEFT, padx=4)

        tk.Label(ctrl, text="Sectors:", bg=T['bg_deep'], fg=T['text_muted'], font=T['font_small']).pack(side=tk.LEFT, padx=(8, 0))
        count_var = tk.StringVar(value="2")
        ttk.Entry(ctrl, textvariable=count_var, width=4).pack(side=tk.LEFT, padx=4)

        text = tk.Text(win, font=(_MONO, 11), wrap='none',
                       bg='#1e1e1e', fg='#d4d4d4', selectbackground=T['bg_surface'])
        text.pack(fill=tk.BOTH, expand=True, padx=8, pady=4)

        def do_dump():
            text.delete('1.0', tk.END)
            try:
                count = int(count_var.get())
                off_str = offset_var.get().strip()
                if off_str:
                    start = int(off_str, 0)
                    length = count * SECTOR_SIZE
                else:
                    sec = int(sector_var.get())
                    start = sec * SECTOR_SIZE
                    length = count * SECTOR_SIZE
            except ValueError:
                text.insert('1.0', 'Invalid input')
                return

            data = self.adf.read_bytes(start, min(length, ADF_SIZE - start))
            lines = []
            for i in range(0, len(data), 16):
                addr = start + i
                chunk = data[i:i + 16]
                hex_str = ' '.join(f'{b:02X}' for b in chunk)
                asc_str = ''.join(chr(b) if 32 <= b < 127 else '·' for b in chunk)
                lines.append(f"{addr:06X}  {hex_str:<48s}  {asc_str}")
            text.insert('1.0', '\n'.join(lines))

        ttk.Button(ctrl, text="Dump", command=do_dump, style='Primary.TButton').pack(side=tk.LEFT, padx=8)
        do_dump()

    def open_patch_composer(self):
        PatchComposerWindow(self.root, game_disk=self.game_disk)

    def show_league_tables(self):
        if not self.current_save:
            messagebox.showinfo("Info", "Select a save slot first.")
            return
        LeagueDashboardWindow(self.root, self.current_save, self.liga_names)

    def show_compare_saves(self):
        if not self.adf or not self.dir_entries:
            messagebox.showinfo("Info", "Open a save disk ADF first.")
            return
        CompareSavesWindow(self.root, self.adf, self.dir_entries,
                           game_disk=self.game_disk, liga_names=self.liga_names)

    def show_highlights(self):
        if not self.current_save:
            messagebox.showinfo("Info", "Select a save slot first.")
            return
        if self.current_save.is_template:
            messagebox.showinfo("Info",
                "Championship Highlights requires a save slot (e.g. pm1.sav).\n\n"
                "start.dat is the factory template and has no player database.")
            return
        ChampionshipHighlightsWindow(
            self.root, self.current_save, self.adf,
            game_disk=self.game_disk, liga_names=self.liga_names)

    def show_transfer_market(self):
        if not self.current_save:
            messagebox.showinfo("Info", "Select a save slot first.")
            return
        TransferMarketWindow(
            self.root, self.current_save, self.adf,
            game_disk=self.game_disk, liga_names=self.liga_names)

    def show_disk_info(self):
        if not self.adf:
            messagebox.showinfo("Info", "Open an ADF first.")
            return

        info = [
            f"File: {os.path.basename(self.adf.path)}",
            f"Size: {len(self.adf.data)} bytes ({len(self.adf.data) // SECTOR_SIZE} sectors)",
            f"Filesystem: {self.adf.filesystem_type}",
            "",
            "File Table (sector 2):",
        ]

        if self.dir_entries:
            for e in self.dir_entries:
                info.append(f"  {e.name:<14s}  start={e.start_unit:#06x} "
                           f"(byte {e.byte_offset:6d})  size={e.size_bytes:5d}")
        else:
            info.append("  (none found)")

        if self.liga_names:
            info.append("")
            info.append(f"Canonical team names ({len(self.liga_names)}):")
            for i, name in enumerate(self.liga_names):
                info.append(f"  {i:2d}. {name}")

        # Show in a scrollable window instead of messagebox
        win = tk.Toplevel(self.root)
        win.title("Disk Info")
        win.geometry("500x600")
        win.configure(bg=_THEME['bg_deep'])
        text = tk.Text(win, font=(_MONO, 11), wrap='word',
                       bg='#1e1e1e', fg='#d4d4d4',
                       selectbackground=_THEME['bg_surface'])
        text.pack(fill=tk.BOTH, expand=True, padx=8, pady=8)
        text.insert('1.0', '\n'.join(info))
        text.config(state='disabled')

    def show_tactics_viewer(self):
        if not self.adf or not self.dir_entries:
            messagebox.showinfo("Info", "Open a save disk ADF first.")
            return
        tac_entries = [e for e in self.dir_entries if e.name.endswith('.tac')]
        if not tac_entries:
            messagebox.showinfo("Info", "No .tac files found on this disk.")
            return
        TacticsViewerWindow(self.root, self.adf, tac_entries)

    def show_disassembler(self):
        if not self.game_disk:
            messagebox.showinfo("Info",
                "No game disk loaded.\n\n"
                f"Place {_GAME_DISK_FILENAME} next to the script and restart.")
            return
        DisassemblerWindow(self.root, self.game_disk)


# ─── Patch Composer Window (Feature 1) ───────────────────────────────

class PatchComposerWindow(tk.Toplevel):
    """
    Standalone tool for editing block 1137 (the runtime Patch block) on the
    game disk ADF.  Opens a separate game-disk ADF, parses the callback's
    68000 patch instructions, lets you add / remove / preview patches, and
    writes back with a correct OFS checksum.
    """

    def __init__(self, parent, game_disk=None):
        super().__init__(parent)
        self.configure(bg=_THEME['bg_deep'])
        self.title("Patch Composer — Game Disk Block 1137")
        self.geometry("820x720")
        self.resizable(True, True)

        self._adf_path = None
        self._adf_data = None     # bytearray of the full ADF
        self._patches = []        # list[PatchEntry]

        self._build_ui()

        # Auto-load from pre-loaded game disk if available
        if game_disk is not None:
            self._adf_path = game_disk.path
            self._adf_data = bytearray(game_disk.adf_data)
            self._fname_var.set(os.path.basename(game_disk.path))
            sec_off = _PATCH_BLOCK_SECTOR * SECTOR_SIZE
            sector = bytes(self._adf_data[sec_off: sec_off + SECTOR_SIZE])
            self._patches = _parse_block1137(sector)
            self._refresh_list()

    # ── Build UI ──

    def _build_ui(self):
        T = _THEME
        # Top bar
        top = tk.Frame(self, bg=T['bg_chrome'])
        top.pack(fill=tk.X, padx=8, pady=6)
        ttk.Button(top, text="Open Game Disk ADF…",
                   command=self._open_adf, style='Primary.TButton').pack(side=tk.LEFT)
        self._fname_var = tk.StringVar(value="No game disk loaded")
        tk.Label(top, textvariable=self._fname_var,
                 bg=T['bg_chrome'], fg=T['text_muted'], font=T['font_small']).pack(
            side=tk.LEFT, padx=(10, 0))

        # Patch list
        lf = ttk.LabelFrame(self, text="Current Patches  (Block 1137, callback area)")
        lf.pack(fill=tk.BOTH, expand=True, padx=8, pady=4)

        cols = ("#", "Offset", "Size", "Value", "Description")
        self._tree = ttk.Treeview(lf, columns=cols, show='headings', height=10)
        self._tree.heading("#", text="#")
        self._tree.heading("Offset", text="Offset")
        self._tree.heading("Size", text="Size")
        self._tree.heading("Value", text="Value")
        self._tree.heading("Description", text="Description")
        self._tree.column("#", width=32, anchor='center')
        self._tree.column("Offset", width=90, anchor='center')
        self._tree.column("Size", width=44, anchor='center')
        self._tree.column("Value", width=120, anchor='center')
        self._tree.column("Description", width=400)

        vsb = ttk.Scrollbar(lf, orient='vertical', command=self._tree.yview)
        self._tree.configure(yscrollcommand=vsb.set)
        self._tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=4, pady=4)
        vsb.pack(side=tk.RIGHT, fill=tk.Y, pady=4)

        del_frame = ttk.Frame(self)
        del_frame.pack(fill=tk.X, padx=8)
        ttk.Button(del_frame, text="Delete Selected Patch",
                   command=self._delete_patch, style='Danger.TButton').pack(side=tk.LEFT, padx=4, pady=2)

        # Quick Patches
        qf = ttk.LabelFrame(self, text="Quick Patches")
        qf.pack(fill=tk.X, padx=8, pady=4)
        qg = ttk.Frame(qf)
        qg.pack(fill=tk.X, padx=8, pady=6)

        ttk.Label(qg, text="Manager Age:").grid(row=0, column=0, sticky='e', padx=4)
        self._age_var = tk.StringVar(value="18")
        ttk.Spinbox(qg, from_=16, to=99, textvariable=self._age_var,
                    width=5).grid(row=0, column=1, sticky='w', padx=4)
        ttk.Label(qg, text="displayed age; stored value = age − 1  "
                  "(WORD at $11740)").grid(row=0, column=2, sticky='w', padx=4)
        ttk.Button(qg, text="Apply Age Patch",
                   command=self._apply_age).grid(row=0, column=3, padx=12)

        # Custom Patch form
        cf = ttk.LabelFrame(self, text="Custom Patch")
        cf.pack(fill=tk.X, padx=8, pady=4)
        cg = ttk.Frame(cf)
        cg.pack(fill=tk.X, padx=8, pady=6)

        ttk.Label(cg, text="Offset (hex):").grid(row=0, column=0, sticky='e', padx=4)
        self._coff_var = tk.StringVar()
        ttk.Entry(cg, textvariable=self._coff_var, width=10).grid(
            row=0, column=1, sticky='w', padx=4)

        ttk.Label(cg, text="Size:").grid(row=0, column=2, sticky='e', padx=8)
        self._csize_var = tk.StringVar(value="B")
        for i, sz in enumerate(('B (byte)', 'W (word)', 'L (long)')):
            ttk.Radiobutton(cg, text=sz, value=sz[0],
                            variable=self._csize_var).grid(row=0, column=3 + i, padx=2)

        ttk.Label(cg, text="Value (hex):").grid(row=1, column=0, sticky='e', padx=4, pady=4)
        self._cval_var = tk.StringVar()
        ttk.Entry(cg, textvariable=self._cval_var, width=10).grid(
            row=1, column=1, sticky='w', padx=4)

        ttk.Label(cg, text="Description:").grid(row=1, column=2, sticky='e', padx=8)
        self._cdesc_var = tk.StringVar()
        ttk.Entry(cg, textvariable=self._cdesc_var, width=32).grid(
            row=1, column=3, sticky='w', padx=4, columnspan=3)

        ttk.Button(cg, text="Add Patch", command=self._add_patch).grid(
            row=2, column=0, columnspan=2, pady=6)

        # Space + action buttons
        bot = ttk.Frame(self)
        bot.pack(fill=tk.X, padx=8, pady=6)
        self._space_var = tk.StringVar(value="Space: open a game disk to begin")
        ttk.Label(bot, textvariable=self._space_var).pack(side=tk.LEFT)
        ttk.Button(bot, text="Write to Game Disk ADF",
                   command=self._write_adf, style='Primary.TButton').pack(side=tk.RIGHT, padx=4)
        ttk.Button(bot, text="Preview ASM",
                   command=self._preview_asm).pack(side=tk.RIGHT, padx=4)

    # ── File operations ──

    def _open_adf(self):
        path = filedialog.askopenfilename(
            parent=self, title="Open Game Disk ADF",
            filetypes=[("ADF files", "*.adf"), ("All files", "*.*")])
        if not path:
            return
        try:
            with open(path, 'rb') as f:
                data = bytearray(f.read())
            if len(data) != ADF_SIZE:
                raise ValueError(f"Expected {ADF_SIZE} bytes, got {len(data)}")
        except Exception as e:
            messagebox.showerror("Error", str(e), parent=self)
            return

        self._adf_path = path
        self._adf_data = data
        self._fname_var.set(os.path.basename(path))

        sec_off = _PATCH_BLOCK_SECTOR * SECTOR_SIZE
        sector = bytes(data[sec_off: sec_off + SECTOR_SIZE])
        self._patches = _parse_block1137(sector)
        self._refresh_list()

    # ── List management ──

    def _refresh_list(self):
        self._tree.delete(*self._tree.get_children())
        for i, p in enumerate(self._patches, 1):
            if p.size == 'L':
                val_str = f"LONG  ${p.value:08X}"
            elif p.size == 'W':
                val_str = f"WORD  ${p.value:04X}"
            else:
                val_str = f"BYTE  ${p.value:02X}"
            self._tree.insert('', 'end', iid=str(i - 1),
                              values=(i, f"${p.offset:06X}", p.size, val_str, p.description))
        self._update_space()

    def _update_space(self):
        used = sum(p.byte_size() for p in self._patches)
        avail = _MAX_PATCH_BYTES
        filled = int(used / avail * 20) if avail else 0
        bar = '█' * filled + '░' * (20 - filled)
        free_patches = (avail - used) // 12
        self._space_var.set(
            f"Space: {bar}  {used}/{avail} bytes  "
            f"({avail - used} free ≈ {free_patches} more byte/word patches)")

    def _delete_patch(self):
        sel = self._tree.selection()
        if not sel:
            return
        idx = int(sel[0])
        p = self._patches[idx]
        if p.offset in _COPYPROT_OFFSETS:
            if not messagebox.askyesno(
                    "Copy-Protection Patch",
                    f"Patch at ${p.offset:06X} is a copy-protection bypass.\n"
                    "Removing it will likely cause the game to crash.\n\n"
                    "Delete anyway?", parent=self):
                return
        del self._patches[idx]
        self._refresh_list()

    def _upsert_patch(self, offset, size, value, desc):
        """Update an existing patch at the same offset+size, or append a new one."""
        for p in self._patches:
            if p.offset == offset and p.size == size:
                p.value = value
                p.description = desc
                self._refresh_list()
                return
        new_p = PatchEntry(offset, size, value, desc)
        total = sum(q.byte_size() for q in self._patches) + new_p.byte_size()
        if total > _MAX_PATCH_BYTES:
            messagebox.showerror("No Space",
                f"Adding this patch would use {total}/{_MAX_PATCH_BYTES} bytes.",
                parent=self)
            return
        self._patches.append(new_p)
        self._refresh_list()

    # ── Quick Patches ──

    def _apply_age(self):
        try:
            age = int(self._age_var.get().strip())
            if not 16 <= age <= 99:
                raise ValueError
        except ValueError:
            messagebox.showwarning("Invalid", "Age must be 16–99.", parent=self)
            return
        stored = age - 1    # Game displays stored_value + 1
        self._upsert_patch(0x011740, 'W', stored,
                           f"Manager age = {age} (stored {stored})")

    # ── Custom Patch ──

    def _add_patch(self):
        try:
            offset = _parse_hex_str(self._coff_var.get())
        except ValueError:
            messagebox.showwarning("Invalid Offset",
                "Enter a hex offset, e.g.  11740  or  $11740", parent=self)
            return
        try:
            value = _parse_hex_str(self._cval_var.get())
        except ValueError:
            messagebox.showwarning("Invalid Value",
                "Enter a hex value, e.g.  0011  or  $0011", parent=self)
            return

        size = self._csize_var.get()
        max_val = {'B': 0xFF, 'W': 0xFFFF, 'L': 0xFFFFFFFF}[size]
        if value > max_val:
            messagebox.showwarning("Value Too Large",
                f"${value:X} exceeds {size} maximum (${max_val:X})", parent=self)
            return

        desc = self._cdesc_var.get().strip()
        new_p = PatchEntry(offset, size, value, desc)
        total = sum(q.byte_size() for q in self._patches) + new_p.byte_size()
        if total > _MAX_PATCH_BYTES:
            messagebox.showerror("No Space",
                f"This patch would need {total} bytes; only {_MAX_PATCH_BYTES} available.",
                parent=self)
            return

        self._patches.append(new_p)
        self._refresh_list()
        self._coff_var.set("")
        self._cval_var.set("")
        self._cdesc_var.set("")

    # ── Preview ──

    def _preview_asm(self):
        if not self._patches:
            messagebox.showinfo("Preview", "No patches to preview.", parent=self)
            return

        used = sum(p.byte_size() for p in self._patches)
        lines = [
            f"; Block 1137 callback — {len(self._patches)} patches, "
            f"{used}/{_MAX_PATCH_BYTES} bytes",
            "",
            f"        LEA     $50000,A0          ; base of decompressed game",
            "",
        ]
        for i, p in enumerate(self._patches, 1):
            label = p.description or "(no description)"
            lines.append(f"        ; [{i}] {label}")
            lines.append(f"        MOVE.L  #${p.offset:06X},D0")
            if p.size == 'B':
                lines.append(f"        MOVE.B  #${p.value:02X},(A0,D0.L)")
            elif p.size == 'W':
                lines.append(f"        MOVE.W  #${p.value:04X},(A0,D0.L)")
            else:
                lines.append(f"        MOVE.L  #${p.value:08X},(A0,D0.L)")
            lines.append("")

        lines.append("        JMP     (A0)               ; jump to $50000 bootstrap")
        lines.append("")
        lines.append("; ── Hex bytes for callback region ──")

        hex_data = _LEA_50000_A0
        for p in self._patches:
            hex_data += p.encode()
        hex_data += _JMP_A0

        for i in range(0, len(hex_data), 16):
            chunk = hex_data[i:i + 16]
            addr = _CB_LEA_AT + i
            hex_str = ' '.join(f'{b:02X}' for b in chunk)
            lines.append(f"  +{addr:03X}  {hex_str}")

        win = tk.Toplevel(self)
        win.title("ASM Preview — Block 1137 Callback")
        win.geometry("720x560")
        txt = tk.Text(win, font=(_MONO, 11), wrap='none',
                      bg='#1e1e1e', fg='#d4d4d4')
        vsb = ttk.Scrollbar(win, orient='vertical', command=txt.yview)
        txt.configure(yscrollcommand=vsb.set)
        vsb.pack(side=tk.RIGHT, fill=tk.Y)
        txt.pack(fill=tk.BOTH, expand=True, padx=8, pady=8)
        txt.insert('1.0', '\n'.join(lines))
        txt.config(state='disabled')

    # ── Write ──

    def _write_adf(self):
        if not self._adf_path or self._adf_data is None:
            messagebox.showinfo("No File", "Open a game disk ADF first.", parent=self)
            return
        if not self._patches:
            if not messagebox.askyesno("Confirm",
                    "No patches defined. Write an empty callback (JMP only)?\n\n"
                    "Without copy-protection patches the game will crash.",
                    parent=self):
                return

        # Check all copy-prot patches still present
        present = {p.offset for p in self._patches}
        missing = _COPYPROT_OFFSETS - present
        if missing:
            missing_str = ', '.join(f'${o:06X}' for o in sorted(missing))
            if not messagebox.askyesno("Missing Copy-Protection Patches",
                    f"The following copy-protection bypass offsets are not in the patch list:\n"
                    f"{missing_str}\n\n"
                    "The game will likely crash without them. Write anyway?",
                    parent=self):
                return

        try:
            sec_off = _PATCH_BLOCK_SECTOR * SECTOR_SIZE
            old_sector = bytes(self._adf_data[sec_off: sec_off + SECTOR_SIZE])
            new_sector = _write_block1137(old_sector, self._patches)
        except ValueError as e:
            messagebox.showerror("Error", str(e), parent=self)
            return

        used = sum(p.byte_size() for p in self._patches)
        if not messagebox.askyesno("Confirm Write",
                f"Write {len(self._patches)} patches ({used} bytes) to block 1137 of:\n"
                f"{os.path.basename(self._adf_path)}\n\n"
                "The OFS checksum will be recalculated automatically.\n"
                "Make sure you have a backup of the original ADF!", parent=self):
            return

        self._adf_data[sec_off: sec_off + SECTOR_SIZE] = new_sector

        save_path = filedialog.asksaveasfilename(
            parent=self,
            title="Save Patched Game Disk ADF As",
            defaultextension=".adf",
            initialfile=os.path.basename(self._adf_path),
            filetypes=[("ADF files", "*.adf"), ("All files", "*.*")])
        if save_path:
            try:
                with open(save_path, 'wb') as f:
                    f.write(self._adf_data)
                self._adf_path = save_path
                self._fname_var.set(os.path.basename(save_path))
                messagebox.showinfo("Done",
                    f"Saved: {os.path.basename(save_path)}\n"
                    f"{len(self._patches)} patches, {used} bytes.", parent=self)
            except Exception as e:
                messagebox.showerror("Write Error", str(e), parent=self)


# ─── League Dashboard (Feature 2a) ───────────────────────────────────

class LeagueDashboardWindow(tk.Toplevel):
    """
    Shows all four division league tables ranked by Points (then Goals) for
    the currently loaded save slot.
    """

    _DIV_NAMES = {0: "Division 1", 1: "Division 2", 2: "Division 3", 3: "Division 4"}
    _PROMOTE  = 2   # Top N teams marked as promotion zone
    _RELEGATE = 2   # Bottom N teams marked as relegation zone

    def __init__(self, parent, save, liga_names):
        super().__init__(parent)
        self.configure(bg=_THEME['bg_deep'])
        self.title(f"League Tables — {save.entry.name}")
        self.geometry("920x640")
        self.resizable(True, True)
        self._save = save
        self._liga = liga_names
        self._build_ui()

    def _build_ui(self):
        ttk.Label(self,
                  text=f"Save slot: {self._save.entry.name}  "
                       f"({len(self._save.teams)} teams)",
                  font=("", 12, "bold")).pack(pady=6)

        # Bucket teams by division, sort each bucket
        divs = {0: [], 1: [], 2: [], 3: []}
        for team in self._save.teams:
            d = team.division
            if d in divs:
                divs[d].append(team)

        for d in divs:
            divs[d].sort(key=lambda t: (-t.league_stats[0], -t.league_stats[1]))

        # Note on promotion/relegation counts
        info = ttk.Frame(self)
        info.pack(fill=tk.X, padx=8)
        ttk.Label(info, text="▲ = promotion zone (top 2)    "
                             "▼ = relegation zone (bottom 2)    "
                             "Sorted by Points, then Goals",
                  foreground=_THEME['text_muted']).pack(side=tk.LEFT)

        nb = ttk.Notebook(self)
        nb.pack(fill=tk.BOTH, expand=True, padx=8, pady=4)

        for d in range(4):
            teams = divs[d]
            tab = ttk.Frame(nb)
            label = self._DIV_NAMES.get(d, f"Div {d}") + f"  ({len(teams)})"
            nb.add(tab, text=label)
            self._build_table(tab, teams)

    def _build_table(self, parent, teams):
        cols = ("rank", "name", "pts", "goals", "value", "zone")
        tree = ttk.Treeview(parent, columns=cols, show='headings')
        tree.heading("rank",  text="#")
        tree.heading("name",  text="Team")
        tree.heading("pts",   text="Pts")
        tree.heading("goals", text="GF")
        tree.heading("value", text="Value")
        tree.heading("zone",  text="")
        tree.column("rank",  width=40,  anchor='center')
        tree.column("name",  width=260)
        tree.column("pts",   width=60,  anchor='center')
        tree.column("goals", width=60,  anchor='center')
        tree.column("value", width=80,  anchor='center')
        tree.column("zone",  width=100, anchor='center')

        n = len(teams)
        for rank, team in enumerate(teams, 1):
            if rank <= self._PROMOTE:
                zone, tag = "▲ Promotion", "promote"
            elif rank > n - self._RELEGATE:
                zone, tag = "▼ Relegation", "relegate"
            else:
                zone, tag = "", ""

            name = team.name or f"(team {team.index})"
            val = team.team_value_signed
            tree.insert('', 'end', tags=(tag,), values=(
                rank, name,
                team.league_stats[0],   # Points
                team.league_stats[1],   # Goals
                f"{val:+d}",
                zone))

        tree.tag_configure('promote',  background=_THEME['promo_bg'], foreground=_THEME['positive'])
        tree.tag_configure('relegate', background=_THEME['relegate_bg'], foreground=_THEME['negative'])

        vsb = ttk.Scrollbar(parent, orient='vertical', command=tree.yview)
        tree.configure(yscrollcommand=vsb.set)
        vsb.pack(side=tk.RIGHT, fill=tk.Y)
        tree.pack(fill=tk.BOTH, expand=True, padx=4, pady=4)


# ─── Compare Saves Window ────────────────────────────────────────────

class CompareSavesWindow(tk.Toplevel):
    """Tabbed comparison of two save slots.

    Tab 1 – Player Transfers  : players whose team changed between saves
    Tab 2 – Division & Budget : teams with division or value changes
    Tab 3 – Career Tracker    : full player DB diff with filters
    """

    _AGE_GROUPS = ["16-20", "21-25", "26-30", "31-35", "36+"]

    def __init__(self, parent, adf, dir_entries, game_disk=None, liga_names=None):
        super().__init__(parent)
        self.configure(bg=_THEME['bg_deep'])
        self.title("Compare Saves")
        self.geometry("1100x700")
        self.resizable(True, True)
        self._adf        = adf
        self._game_disk  = game_disk
        self._liga       = liga_names or []
        self._saves      = [e for e in dir_entries
                            if e.name.endswith('.sav') or e.name.endswith('.dat')]
        # Data loaded after Compare → is clicked
        self._db_a           = {}
        self._db_b           = {}
        self._entry_a        = None
        self._entry_b        = None
        self._sa             = None
        self._sb             = None
        self._career_rows    = []
        self._career_sort_col = 'role_delta'
        self._career_sort_rev = True     # descending by default
        self._xfer_pid_map   = {}        # treeview iid → pid (transfers tab)
        self._career_pid_map = {}        # treeview iid → pid (career tab)
        self._build_ui()

    # ── Helpers ─────────────────────────────────────────────────────

    @staticmethod
    def _age_group(age):
        if age is None:
            return "?"
        if age <= 20: return "16-20"
        if age <= 25: return "21-25"
        if age <= 30: return "26-30"
        if age <= 35: return "31-35"
        return "36+"

    # ── UI Construction ─────────────────────────────────────────────

    def _build_ui(self):
        # Save picker
        pick = ttk.LabelFrame(self, text="Select Two Save Slots to Compare")
        pick.pack(fill=tk.X, padx=8, pady=6)
        pg = ttk.Frame(pick)
        pg.pack(fill=tk.X, padx=8, pady=8)

        names = [e.name for e in self._saves]

        ttk.Label(pg, text="Save A:").grid(row=0, column=0, sticky='e', padx=4)
        self._var_a = tk.StringVar()
        ttk.Combobox(pg, textvariable=self._var_a, values=names,
                     width=22, state='readonly').grid(row=0, column=1, padx=4)

        ttk.Label(pg, text="Save B:").grid(row=0, column=2, sticky='e', padx=12)
        self._var_b = tk.StringVar()
        ttk.Combobox(pg, textvariable=self._var_b, values=names,
                     width=22, state='readonly').grid(row=0, column=3, padx=4)

        ttk.Button(pg, text="Compare →",
                   command=self._compare).grid(row=0, column=4, padx=12)

        # Notebook with three tabs
        self._nb = ttk.Notebook(self)
        self._nb.pack(fill=tk.BOTH, expand=True, padx=8, pady=4)

        self._tab_xfer = ttk.Frame(self._nb)
        self._nb.add(self._tab_xfer, text="Player Transfers")
        self._build_xfer_tab(self._tab_xfer)

        self._tab_div = ttk.Frame(self._nb)
        self._nb.add(self._tab_div, text="Division & Budget")
        self._build_div_tab(self._tab_div)

        self._tab_career = ttk.Frame(self._nb)
        self._nb.add(self._tab_career, text="Career Tracker")
        self._build_career_tab(self._tab_career)

    # ── Tab 1: Player Transfers ──────────────────────────────────────

    def _build_xfer_tab(self, parent):
        cols  = ('id', 'name', 'pos', 'from_team', 'to_team', 'role_avg')
        heads = ('ID', 'Name', 'Pos', 'From', 'To', 'Role Avg')
        widths = (50, 140, 50, 200, 200, 75)
        self._xfer_tree = _make_scrolled_tree(
            parent, cols, heads, widths,
            anchors={'name': 'w', 'from_team': 'w', 'to_team': 'w'},
            on_double_click=self._on_xfer_double_click)

    def _populate_transfers(self, sa, sb, db_a, db_b):
        tree = self._xfer_tree
        tree.delete(*tree.get_children())
        self._xfer_pid_map.clear()

        roster_a = build_roster_map(sa)
        roster_b = build_roster_map(sb)

        rows = []
        for pid in sorted(set(roster_a) | set(roster_b)):
            ta = roster_a.get(pid, "Unassigned")
            tb = roster_b.get(pid, "Unassigned")
            if ta != tb:
                name    = player_name_str(self._game_disk,pid)
                rec_b   = db_b.get(pid)
                pos_str = POSITION_NAMES.get(rec_b.position, "?") if rec_b else "?"
                role_avg = f"{rec_b.role_skill_avg():.0f}" if rec_b else "—"
                rows.append((name, pid, pos_str, ta, tb, role_avg))

        rows.sort(key=lambda r: r[0])   # sort by player name
        for name, pid, pos_str, ta, tb, role_avg in rows:
            iid = tree.insert('', 'end',
                              values=(pid, name, pos_str, ta, tb, role_avg))
            self._xfer_pid_map[iid] = pid

    def _on_xfer_double_click(self, event):
        item = self._xfer_tree.identify_row(event.y)
        if item:
            pid = self._xfer_pid_map.get(item)
            if pid is not None:
                self._open_player_detail(pid)

    # ── Tab 2: Division & Budget ─────────────────────────────────────

    def _build_div_tab(self, parent):
        cols  = ('team', 'div_a', 'div_b', 'change', 'val_a', 'val_b', 'delta')
        heads = ('Team', 'Div A', 'Div B', 'Change', 'Value A', 'Value B', 'Δ Value')
        widths = (200, 60, 60, 90, 80, 80, 80)
        self._div_tree = _make_scrolled_tree(
            parent, cols, heads, widths, anchors={'team': 'w'})
        self._div_tree.tag_configure('promoted', foreground=_THEME['positive'])
        self._div_tree.tag_configure('relegated', foreground=_THEME['negative'])

    def _populate_div_budget(self, sa, sb):
        tree = self._div_tree
        tree.delete(*tree.get_children())

        teams_a = {t.name: t for t in sa.teams if t.name}
        teams_b = {t.name: t for t in sb.teams if t.name}

        rows = []
        for name in sorted(set(teams_a) & set(teams_b)):
            ta_rec = teams_a[name]
            tb_rec = teams_b[name]
            da     = ta_rec.division
            db_    = tb_rec.division
            va     = ta_rec.team_value_signed
            vb     = tb_rec.team_value_signed
            delta  = vb - va
            div_changed = (da is not None and db_ is not None and da != db_)
            if not div_changed and delta == 0:
                continue
            change = ""
            if div_changed:
                change = "Promoted" if db_ < da else "Relegated"
            rows.append((div_changed, abs(delta), name, da, db_, change, va, vb, delta))

        rows.sort(key=lambda r: (-int(r[0]), -r[1]))   # div change first, |delta| desc
        for _, _, name, da, db_, change, va, vb, delta in rows:
            tag = ('promoted'  if change == "Promoted"  else
                   'relegated' if change == "Relegated" else '')
            tree.insert('', 'end', tags=(tag,), values=(
                name,
                f"Div {da + 1}" if da is not None else "?",
                f"Div {db_ + 1}" if db_ is not None else "?",
                change,
                f"{va:+d}", f"{vb:+d}", f"{delta:+d}",
            ))

    # ── Tab 3: Career Tracker ─────────────────────────────────────────

    def _build_career_tab(self, parent):
        # Filters bar
        filt = ttk.LabelFrame(parent, text="Filters")
        filt.pack(fill=tk.X, padx=4, pady=(6, 2))
        frow = ttk.Frame(filt)
        frow.pack(fill=tk.X, padx=4, pady=4)

        ttk.Label(frow, text="Team:").pack(side=tk.LEFT)
        self._filt_team_var = tk.StringVar(value="All")
        self._team_combo = ttk.Combobox(frow, textvariable=self._filt_team_var,
                                         values=["All"], state='readonly', width=20)
        self._team_combo.pack(side=tk.LEFT, padx=4)
        self._team_combo.bind('<<ComboboxSelected>>',
                              lambda e: self._apply_career_filters())

        ttk.Label(frow, text="Position:").pack(side=tk.LEFT, padx=(10, 0))
        self._filt_pos_var = tk.StringVar(value="All")
        pos_cb = ttk.Combobox(frow, textvariable=self._filt_pos_var,
                               values=["All", "GK", "DEF", "MID", "FWD"],
                               state='readonly', width=6)
        pos_cb.pack(side=tk.LEFT, padx=4)
        pos_cb.bind('<<ComboboxSelected>>', lambda e: self._apply_career_filters())

        ttk.Label(frow, text="Age:").pack(side=tk.LEFT, padx=(10, 0))
        self._filt_age_min_var = tk.IntVar(value=16)
        self._filt_age_max_var = tk.IntVar(value=40)
        ttk.Spinbox(frow, from_=16, to=50, textvariable=self._filt_age_min_var,
                    width=4).pack(side=tk.LEFT, padx=2)
        ttk.Label(frow, text="–").pack(side=tk.LEFT)
        ttk.Spinbox(frow, from_=16, to=50, textvariable=self._filt_age_max_var,
                    width=4).pack(side=tk.LEFT, padx=2)

        self._filt_changed_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(frow, text="Show only changed",
                        variable=self._filt_changed_var,
                        command=self._apply_career_filters).pack(side=tk.LEFT, padx=12)
        ttk.Button(frow, text="Apply",
                   command=self._apply_career_filters).pack(side=tk.LEFT, padx=8)

        # Summary bar
        self._summary_var = tk.StringVar(value="No comparison loaded.")
        ttk.Label(parent, textvariable=self._summary_var,
                  foreground=_THEME['text_muted']).pack(fill=tk.X, padx=8, pady=(0, 2))

        # Career treeview
        cols  = ('name', 'pos', 'age', 'team', 'role_delta', 'avg_delta',
                 'goals', 'matches', 'injuries', 'contract', 'age_group')
        heads = ('Name', 'Pos', 'Age', 'Team', 'Role Δ', 'Avg Δ',
                 'Goals', 'Mat', 'Inj', 'Ctr', 'Age Grp')
        widths = (140, 70, 40, 190, 65, 65, 50, 50, 50, 50, 60)
        self._career_tree = _make_scrolled_tree(
            parent, cols, heads, widths,
            anchors={'name': 'w', 'team': 'w'},
            on_double_click=self._on_career_double_click,
            heading_command=self._sort_career,
            hscroll=True)

        # Row color tags
        T = _THEME
        self._career_tree.tag_configure('improved',    background='#1E3E2E', foreground=T['positive'])
        self._career_tree.tag_configure('declined',    background='#3E1E2E', foreground=T['negative'])
        self._career_tree.tag_configure('transferred', background='#3E3E1E', foreground='#CCCC44')
        self._career_tree.tag_configure('only_a',      background=T['bg_surface'], foreground=T['text_dim'])
        self._career_tree.tag_configure('only_b',      background='#1E2E3E', foreground=T['accent2'])

        # Age–Skill Trend bar (hidden until there is enough data)
        self._age_trend_frame = ttk.Frame(parent)
        self._age_trend_text  = tk.Text(
            self._age_trend_frame, height=1, font=(_MONO, 10),
            relief='flat', bg=_THEME['bg_deep'], state='disabled', cursor='arrow',
        )
        self._age_trend_text.tag_configure('pos', foreground=_THEME['positive'])
        self._age_trend_text.tag_configure('neg', foreground=_THEME['negative'])
        self._age_trend_text.tag_configure('neu', foreground=_THEME['text_muted'])
        self._age_trend_text.pack(fill=tk.X, padx=4, pady=2)
        # Frame is shown/hidden dynamically by _update_age_trend

    # ── Compare ──────────────────────────────────────────────────────

    def _compare(self):
        name_a = self._var_a.get()
        name_b = self._var_b.get()
        if not name_a or not name_b:
            messagebox.showwarning("Select", "Choose two save slots.", parent=self)
            return
        if name_a == name_b:
            messagebox.showwarning("Same File",
                "Choose two different save slots.", parent=self)
            return

        entry_a = next((e for e in self._saves if e.name == name_a), None)
        entry_b = next((e for e in self._saves if e.name == name_b), None)
        if not entry_a or not entry_b:
            messagebox.showerror("Error", "Could not find save entries.", parent=self)
            return

        try:
            sa   = SaveFile(self._adf, entry_a)
            sb   = SaveFile(self._adf, entry_b)
            db_a = parse_player_db(self._adf, entry_a)
            db_b = parse_player_db(self._adf, entry_b)
        except Exception as exc:
            messagebox.showerror("Error", str(exc), parent=self)
            return

        self._sa      = sa
        self._sb      = sb
        self._db_a    = db_a
        self._db_b    = db_b
        self._entry_a = entry_a
        self._entry_b = entry_b

        self.title(f"Compare Saves — {name_a} vs {name_b}")
        self._populate_transfers(sa, sb, db_a, db_b)
        self._populate_div_budget(sa, sb)
        self._populate_career(sa, sb, db_a, db_b)

    # ── Career Tracker logic ──────────────────────────────────────────

    def _populate_career(self, sa, sb, db_a, db_b):
        """Build self._career_rows from both saves and player databases."""
        roster_a = build_roster_map(sa)
        roster_b = build_roster_map(sb)
        all_pids = set(db_a) | set(db_b)

        rows = []
        for pid in all_pids:
            rec_a = db_a.get(pid)
            rec_b = db_b.get(pid)
            name      = player_name_str(self._game_disk,pid)
            team_a    = roster_a.get(pid, "Free Agent")
            team_b    = roster_b.get(pid, "Free Agent")
            transferred = (team_a != team_b)

            if rec_a and rec_b:
                status      = 'both'
                pos_a, pos_b = rec_a.position, rec_b.position
                pos_changed  = (pos_a != pos_b)
                role_avg_a   = rec_a.role_skill_avg()
                role_avg_b   = rec_b.role_skill_avg()
                skill_avg_a  = rec_a.skill_avg
                skill_avg_b  = rec_b.skill_avg
                role_delta   = role_avg_b - role_avg_a
                avg_delta    = skill_avg_b - skill_avg_a
                any_skill    = any(a != b for a, b in zip(rec_a.skills, rec_b.skills))
                age_b        = rec_b.age
                goals_b      = rec_b.goals_this_year
                matches_b    = rec_b.matches_this_year
                injuries_b   = rec_b.injuries_this_year
                contract_b   = rec_b.contract_years
            elif rec_a:
                status      = 'only_a'
                pos_a, pos_b = rec_a.position, None
                pos_changed  = False
                role_avg_a   = rec_a.role_skill_avg()
                role_avg_b   = None
                skill_avg_a  = rec_a.skill_avg
                skill_avg_b  = None
                role_delta   = 0.0
                avg_delta    = 0.0
                any_skill    = False
                age_b        = rec_a.age
                goals_b = matches_b = injuries_b = contract_b = None
            else:
                status      = 'only_b'
                pos_a, pos_b = None, rec_b.position
                pos_changed  = False
                role_avg_a   = None
                role_avg_b   = rec_b.role_skill_avg()
                skill_avg_a  = None
                skill_avg_b  = rec_b.skill_avg
                role_delta   = 0.0
                avg_delta    = 0.0
                any_skill    = False
                age_b        = rec_b.age
                goals_b      = rec_b.goals_this_year
                matches_b    = rec_b.matches_this_year
                injuries_b   = rec_b.injuries_this_year
                contract_b   = rec_b.contract_years

            is_changed = (transferred or pos_changed or any_skill or status != 'both')

            rows.append({
                'pid': pid, 'name': name,
                'pos_a': pos_a, 'pos_b': pos_b,
                'age_b': age_b,
                'team_a': team_a, 'team_b': team_b,
                'role_avg_a': role_avg_a, 'role_avg_b': role_avg_b,
                'skill_avg_a': skill_avg_a, 'skill_avg_b': skill_avg_b,
                'role_delta': role_delta, 'avg_delta': avg_delta,
                'goals_b': goals_b, 'matches_b': matches_b,
                'injuries_b': injuries_b, 'contract_b': contract_b,
                'transferred': transferred, 'pos_changed': pos_changed,
                'any_skill_changed': any_skill, 'is_changed': is_changed,
                'status': status, 'age_group': self._age_group(age_b),
            })

        self._career_rows = rows

        # Populate team filter dropdown from Save B rosters
        team_names = sorted({r['team_b'] for r in rows if r['team_b'] != "Free Agent"})
        self._team_combo['values'] = ["All", "Free Agents"] + team_names
        self._filt_team_var.set("All")

        self._career_sort_col = 'role_delta'
        self._career_sort_rev = True
        self._apply_career_filters()

    def _apply_career_filters(self):
        if not self._career_rows:
            return
        rows = list(self._career_rows)

        team_filt = self._filt_team_var.get()
        if team_filt == "Free Agents":
            rows = [r for r in rows if r['team_b'] == "Free Agent"]
        elif team_filt != "All":
            rows = [r for r in rows if r['team_b'] == team_filt]

        pos_filt = self._filt_pos_var.get()
        if pos_filt != "All":
            code = {"GK": 1, "DEF": 2, "MID": 3, "FWD": 4}.get(pos_filt)
            if code:
                rows = [r for r in rows
                        if r['pos_b'] == code
                        or (r['pos_b'] is None and r['pos_a'] == code)]

        age_min = self._filt_age_min_var.get()
        age_max = self._filt_age_max_var.get()
        if age_min != 16 or age_max != 40:
            rows = [r for r in rows if age_min <= (r['age_b'] or 0) <= age_max]

        if self._filt_changed_var.get():
            rows = [r for r in rows if r['is_changed']]

        # Sort
        _key = {
            'name':       lambda r: r['name'],
            'pos':        lambda r: (r['pos_b'] or r['pos_a'] or 0),
            'age':        lambda r: (r['age_b'] or 0),
            'team':       lambda r: r['team_b'],
            'role_delta': lambda r: r['role_delta'],
            'avg_delta':  lambda r: r['avg_delta'],
            'goals':      lambda r: (r['goals_b'] or -1),
            'matches':    lambda r: (r['matches_b'] or -1),
            'injuries':   lambda r: (r['injuries_b'] or -1),
            'contract':   lambda r: (r['contract_b'] or -1),
            'age_group':  lambda r: (r['age_b'] or 0),
        }.get(self._career_sort_col, lambda r: r['name'])
        rows.sort(key=_key, reverse=self._career_sort_rev)

        # Repopulate tree
        tree = self._career_tree
        tree.delete(*tree.get_children())
        self._career_pid_map.clear()

        def _v(x):
            return x if x is not None else "—"

        for r in rows:
            # Position display
            pa, pb = r['pos_a'], r['pos_b']
            if r['pos_changed']:
                pos_disp = (f"{POSITION_NAMES.get(pa, '?')}->"
                            f"{POSITION_NAMES.get(pb, '?')}")
            else:
                pos_disp = POSITION_NAMES.get(pb if pb is not None else pa, "?")

            # Team display
            st = r['status']
            if st == 'only_a':
                team_disp = "(Removed)"
            elif st == 'only_b':
                team_disp = f"{r['team_b']} (New)"
            elif r['transferred']:
                team_disp = f"{r['team_a']}->{r['team_b']}"
            else:
                team_disp = r['team_b']

            # Delta strings
            if st == 'both':
                rd, ad = r['role_delta'], r['avg_delta']
                role_s = f"{rd:+.0f}" if rd != 0 else "0"
                avg_s  = f"{ad:+.0f}" if ad != 0 else "0"
            else:
                role_s = avg_s = "—"

            # Row tag
            if st == 'only_a':
                tag = 'only_a'
            elif st == 'only_b':
                tag = 'only_b'
            elif r['transferred']:
                tag = 'transferred'
            elif r['role_delta'] >= 5:
                tag = 'improved'
            elif r['role_delta'] <= -5:
                tag = 'declined'
            else:
                tag = ''

            iid = tree.insert('', 'end', tags=(tag,), values=(
                r['name'], pos_disp, _v(r['age_b']), team_disp,
                role_s, avg_s,
                _v(r['goals_b']), _v(r['matches_b']),
                _v(r['injuries_b']), _v(r['contract_b']),
                r['age_group'],
            ))
            self._career_pid_map[iid] = r['pid']

        self._update_career_summary(rows)
        self._update_age_trend(rows)

    def _sort_career(self, col):
        if self._career_sort_col == col:
            self._career_sort_rev = not self._career_sort_rev
        else:
            self._career_sort_col = col
            self._career_sort_rev = col in ('role_delta', 'avg_delta',
                                             'goals', 'matches', 'injuries')
        self._apply_career_filters()

    def _update_career_summary(self, visible_rows):
        total    = len(self._career_rows)
        showing  = len(visible_rows)
        improved = sum(1 for r in visible_rows
                       if r['status'] == 'both' and r['role_delta'] >= 5)
        declined = sum(1 for r in visible_rows
                       if r['status'] == 'both' and r['role_delta'] <= -5)
        xferred  = sum(1 for r in visible_rows if r['transferred'])
        self._summary_var.set(
            f"Showing {showing} of {total} players — "
            f"{improved} improved, {declined} declined, {xferred} transferred"
        )

    def _update_age_trend(self, visible_rows):
        changed = [r for r in visible_rows
                   if r['is_changed'] and r['status'] == 'both']
        if not self._filt_changed_var.get() or len(changed) < 20:
            self._age_trend_frame.pack_forget()
            return

        by_bracket = {b: [] for b in self._AGE_GROUPS}
        for r in changed:
            ag = r['age_group']
            if ag in by_bracket:
                by_bracket[ag].append(r['role_delta'])

        txt = self._age_trend_text
        txt.config(state='normal')
        txt.delete('1.0', tk.END)
        txt.insert(tk.END, "Age–Skill Trends (avg role Δ):  ")
        for i, bracket in enumerate(self._AGE_GROUPS):
            deltas = by_bracket[bracket]
            if deltas:
                avg  = sum(deltas) / len(deltas)
                lbl  = f"{bracket}: {avg:+.1f}"
                ctag = 'pos' if avg >= 1.0 else ('neg' if avg <= -1.0 else 'neu')
            else:
                lbl  = f"{bracket}: n/a"
                ctag = 'neu'
            txt.insert(tk.END, lbl, ctag)
            if i < len(self._AGE_GROUPS) - 1:
                txt.insert(tk.END, "  |  ")
        txt.config(state='disabled')
        self._age_trend_frame.pack(fill=tk.X, padx=4, pady=(0, 4))

    def _on_career_double_click(self, event):
        item = self._career_tree.identify_row(event.y)
        if item:
            pid = self._career_pid_map.get(item)
            if pid is not None:
                self._open_player_detail(pid)

    # ── Player Detail Popup ───────────────────────────────────────────

    def _open_player_detail(self, pid):
        _PlayerDetailPopup(self, pid,
                           self._db_a.get(pid), self._db_b.get(pid),
                           self._adf, self._entry_b, self._game_disk)


class _PlayerDetailPopup(tk.Toplevel):
    """Read-only side-by-side attribute comparison for one player."""

    _FIELDS = [
        ("Stamina",          "stamina"),
        ("Resilience",       "resilience"),
        ("Pace",             "pace"),
        ("Agility",          "agility"),
        ("Aggression",       "aggression"),
        ("Flair",            "flair"),
        ("Passing",          "passing"),
        ("Shooting",         "shooting"),
        ("Tackling",         "tackling"),
        ("Keeping",          "keeping"),
        ("Height (cm)",      "height"),
        ("Weight (kg)",      "weight"),
        ("Age",              "age"),
        ("Position",         "position"),
        ("Division",         "division"),
        ("Team index",       "team_index"),
        ("Injury weeks",     "injury_weeks"),
        ("Disciplinary",     "disciplinary"),
        ("Morale",           "morale"),
        ("Value",            "value"),
        ("Transfer weeks",   "transfer_weeks"),
        ("Injuries this yr", "injuries_this_year"),
        ("Injuries last yr", "injuries_last_year"),
        ("Disp pts this yr", "dsp_pts_this_year"),
        ("Disp pts last yr", "dsp_pts_last_year"),
        ("Goals this yr",    "goals_this_year"),
        ("Goals last yr",    "goals_last_year"),
        ("Matches this yr",  "matches_this_year"),
        ("Matches last yr",  "matches_last_year"),
        ("Div1 years",       "div1_years"),
        ("Div2 years",       "div2_years"),
        ("Div3 years",       "div3_years"),
        ("Div4 years",       "div4_years"),
        ("Int'l years",      "int_years"),
        ("Contract years",   "contract_years"),
    ]

    def __init__(self, parent, pid, rec_a, rec_b, adf, entry_b, game_disk):
        super().__init__(parent)
        self.configure(bg=_THEME['bg_deep'])
        rec  = rec_b or rec_a
        name = (game_disk.player_name(pid) or "") if game_disk else ""
        self.title(f"Player Detail — {name or f'#{pid}'}")
        self.geometry("480x640")
        self.resizable(False, True)
        self._rec_b     = rec_b
        self._adf       = adf
        self._entry_b   = entry_b
        self._game_disk = game_disk
        self._build_ui(pid, rec_a, rec_b, rec, name)

    def _build_ui(self, pid, rec_a, rec_b, rec, name):
        pos_name = POSITION_NAMES.get(rec.position, "?") if rec else "?"
        age      = rec.age if rec else "?"
        ttk.Label(self,
                  text=f"#{pid}  {name}  |  {pos_name}  |  Age {age}",
                  font=("", 13, "bold")).pack(padx=12, pady=(10, 4), anchor='w')

        # Column headers
        hdr_frame = ttk.Frame(self)
        hdr_frame.pack(fill=tk.X, padx=12, pady=(0, 2))
        for txt, width in [("Field", 22), ("Save A", 9), ("Save B", 9), ("Delta", 8)]:
            ttk.Label(hdr_frame, text=txt, font=("", 10, "bold"),
                      width=width).pack(side=tk.LEFT)
        ttk.Separator(self, orient='horizontal').pack(fill=tk.X, padx=8, pady=2)

        # Scrollable content
        canvas = tk.Canvas(self, borderwidth=0, bg=_THEME['bg_deep'])
        vsb    = ttk.Scrollbar(self, orient='vertical', command=canvas.yview)
        inner  = ttk.Frame(canvas)
        inner.bind("<Configure>",
                   lambda e: canvas.configure(scrollregion=canvas.bbox("all")))
        canvas.create_window((0, 0), window=inner, anchor='nw')
        canvas.configure(yscrollcommand=vsb.set)
        vsb.pack(side=tk.RIGHT, fill=tk.Y)
        canvas.pack(fill=tk.BOTH, expand=True)

        for label, attr in self._FIELDS:
            val_a     = getattr(rec_a, attr, None) if rec_a else None
            val_b     = getattr(rec_b, attr, None) if rec_b else None
            delta_str = ""
            delta_fg  = _THEME['text_muted']
            if val_a is not None and val_b is not None:
                try:
                    d = int(val_b) - int(val_a)
                    if d != 0:
                        delta_str = f"{d:+d}"
                    delta_fg = (_THEME['positive'] if d > 0 else
                                _THEME['negative'] if d < 0 else _THEME['text_muted'])
                except (TypeError, ValueError):
                    pass

            row = ttk.Frame(inner)
            row.pack(fill=tk.X, padx=8, pady=1)
            ttk.Label(row, text=label, width=22, anchor='w').pack(side=tk.LEFT)
            ttk.Label(row, text=(str(val_a) if val_a is not None else "—"),
                      width=9, anchor='center').pack(side=tk.LEFT)
            ttk.Label(row, text=(str(val_b) if val_b is not None else "—"),
                      width=9, anchor='center').pack(side=tk.LEFT)
            ttk.Label(row, text=delta_str, width=8, anchor='center',
                      foreground=delta_fg).pack(side=tk.LEFT)

        # Buttons
        ttk.Separator(self, orient='horizontal').pack(fill=tk.X, padx=8, pady=4)
        btn_f = ttk.Frame(self)
        btn_f.pack(pady=(0, 10))
        edit_btn = ttk.Button(btn_f, text="Edit in Save B…",
                              command=self._open_editor)
        edit_btn.pack(side=tk.LEFT, padx=8)
        if self._rec_b is None or self._entry_b is None:
            edit_btn.config(state='disabled')
        ttk.Button(btn_f, text="Close",
                   command=self.destroy).pack(side=tk.LEFT, padx=8)

    def _open_editor(self):
        if self._rec_b and self._entry_b:
            PlayerEditorWindow(self, self._rec_b, self._adf,
                               self._entry_b, game_disk=self._game_disk)


# ─── Tactics Viewer Window ──────────────────────────────────────────

class TacticsViewerWindow(tk.Toplevel):
    """Visual editor for .tac tactics files.  Shows a football pitch with
    draggable player dots for each zone and state (with/without ball)."""

    # Pitch drawing constants — coordinates scaled from game coords
    PITCH_W = 460     # Canvas width
    PITCH_H = 600     # Canvas height
    MARGIN = 30
    # Game coord ranges (discovered from data analysis)
    GAME_X_MIN = 0
    GAME_X_MAX = 912
    GAME_Y_MIN = 0
    GAME_Y_MAX = 1400
    DOT_R = 8

    # Player colors (10 outfield players)
    _PLAYER_COLORS = [
        '#E53935', '#1E88E5', '#43A047', '#FB8C00', '#8E24AA',
        '#00ACC1', '#FFB300', '#6D4C41', '#D81B60', '#546E7A',
    ]

    def __init__(self, parent, adf, tac_entries):
        super().__init__(parent)
        self.configure(bg=_THEME['bg_deep'])
        self.title("Tactics Viewer")
        self.geometry("560x780")
        self.resizable(True, True)

        self._adf = adf
        self._tac_entries = tac_entries
        self._tac = None           # Current TacticsFile
        self._tac_entry = None     # Current DirEntry
        self._zone = 0
        self._state = 0            # 0 = with ball, 1 = without ball
        self._drag_player = None   # Index of player being dragged

        self._build_ui()

    def _build_ui(self):
        # Top: file selector
        top = ttk.Frame(self)
        top.pack(fill=tk.X, padx=8, pady=6)

        ttk.Label(top, text="Tactics file:").pack(side=tk.LEFT, padx=4)
        self._file_var = tk.StringVar()
        names = [e.name for e in self._tac_entries]
        cb = ttk.Combobox(top, textvariable=self._file_var, values=names,
                          width=18, state='readonly')
        cb.pack(side=tk.LEFT, padx=4)
        cb.bind('<<ComboboxSelected>>', lambda e: self._load_tac())
        if names:
            cb.current(0)

        ttk.Button(top, text="Load", command=self._load_tac).pack(side=tk.LEFT, padx=4)
        ttk.Button(top, text="Save to Disk", command=self._save_tac, style='Primary.TButton').pack(side=tk.LEFT, padx=8)

        # Controls: zone and state
        ctrl = ttk.Frame(self)
        ctrl.pack(fill=tk.X, padx=8, pady=2)

        ttk.Label(ctrl, text="Zone:").pack(side=tk.LEFT, padx=4)
        self._zone_var = tk.StringVar(value="0")
        zone_cb = ttk.Combobox(ctrl, textvariable=self._zone_var,
                               values=[f"{i}: {_ZONE_NAMES[i]}" for i in range(TAC_NUM_ZONES)],
                               width=22, state='readonly')
        zone_cb.pack(side=tk.LEFT, padx=4)
        zone_cb.current(0)
        zone_cb.bind('<<ComboboxSelected>>', lambda e: self._on_zone_change())

        ttk.Label(ctrl, text="State:").pack(side=tk.LEFT, padx=(12, 4))
        self._state_var = tk.StringVar(value="With ball")
        state_cb = ttk.Combobox(ctrl, textvariable=self._state_var,
                                values=["With ball", "Without ball"],
                                width=14, state='readonly')
        state_cb.pack(side=tk.LEFT, padx=4)
        state_cb.current(0)
        state_cb.bind('<<ComboboxSelected>>', lambda e: self._on_state_change())

        # Description
        self._desc_var = tk.StringVar()
        ttk.Label(self, textvariable=self._desc_var, foreground=_THEME['text_muted'],
                  wraplength=520).pack(fill=tk.X, padx=12, pady=2)

        # Canvas — football pitch
        self._canvas = tk.Canvas(self, bg='#2E7D32', highlightthickness=0)
        self._canvas.pack(fill=tk.BOTH, expand=True, padx=8, pady=4)

        self._canvas.bind('<Configure>', lambda e: self._draw_pitch())
        self._canvas.bind('<Button-1>', self._on_click)
        self._canvas.bind('<B1-Motion>', self._on_drag)
        self._canvas.bind('<ButtonRelease-1>', self._on_release)

        # Legend
        leg = ttk.Frame(self)
        leg.pack(fill=tk.X, padx=8, pady=4)
        for i in range(TAC_NUM_PLAYERS):
            tk.Canvas(leg, width=12, height=12, bg=self._PLAYER_COLORS[i],
                      highlightthickness=1, highlightbackground='white'
                      ).pack(side=tk.LEFT, padx=1)
            ttk.Label(leg, text=f"P{i}", font=(_MONO, 9)).pack(side=tk.LEFT, padx=(0, 4))

        # Status
        self._status = tk.StringVar(value="Select a .tac file and click Load")
        ttk.Label(self, textvariable=self._status, relief='sunken',
                  anchor='w').pack(fill=tk.X, side=tk.BOTTOM, padx=2, pady=2)

        self._load_tac()

    def _load_tac(self):
        name = self._file_var.get()
        if not name:
            return
        for e in self._tac_entries:
            if e.name == name:
                raw = bytes(self._adf.data[e.byte_offset: e.byte_offset + e.size_bytes])
                try:
                    self._tac = TacticsFile(raw)
                    self._tac_entry = e
                    self._desc_var.set(self._tac.description or "(no description)")
                    self._status.set(f"Loaded {name} ({e.size_bytes} bytes)")
                    self._draw_pitch()
                except Exception as ex:
                    messagebox.showerror("Error", str(ex), parent=self)
                return

    def _save_tac(self):
        if not self._tac or not self._tac_entry:
            return
        packed = self._tac.pack()
        e = self._tac_entry
        self._adf.data[e.byte_offset: e.byte_offset + len(packed)] = packed
        self._status.set(f"Written {e.name} back to ADF buffer (use File → Save to write to disk)")

    def _on_zone_change(self):
        val = self._zone_var.get()
        self._zone = int(val.split(':')[0])
        self._draw_pitch()

    def _on_state_change(self):
        self._state = 0 if 'With' in self._state_var.get() else 1
        self._draw_pitch()

    def _game_to_canvas(self, gx, gy):
        cw = self._canvas.winfo_width()
        ch = self._canvas.winfo_height()
        m = self.MARGIN
        # Scale game coords to canvas, Y inverted (low Y = bottom = own goal)
        cx = m + (gx - self.GAME_X_MIN) / (self.GAME_X_MAX - self.GAME_X_MIN) * (cw - 2 * m)
        cy = ch - m - (gy - self.GAME_Y_MIN) / (self.GAME_Y_MAX - self.GAME_Y_MIN) * (ch - 2 * m)
        return cx, cy

    def _canvas_to_game(self, cx, cy):
        cw = self._canvas.winfo_width()
        ch = self._canvas.winfo_height()
        m = self.MARGIN
        gx = self.GAME_X_MIN + (cx - m) / (cw - 2 * m) * (self.GAME_X_MAX - self.GAME_X_MIN)
        gy = self.GAME_Y_MIN + (ch - m - cy) / (ch - 2 * m) * (self.GAME_Y_MAX - self.GAME_Y_MIN)
        return max(0, int(gx)), max(0, int(gy))

    def _draw_pitch(self):
        c = self._canvas
        c.delete('all')
        cw = c.winfo_width()
        ch = c.winfo_height()
        if cw < 50 or ch < 50:
            return
        m = self.MARGIN

        # Pitch outline
        c.create_rectangle(m, m, cw - m, ch - m, outline='white', width=2)
        # Center line
        cy_mid = ch / 2
        c.create_line(m, cy_mid, cw - m, cy_mid, fill='white', width=1)
        # Center circle
        cr = min(cw, ch) * 0.08
        c.create_oval(cw / 2 - cr, cy_mid - cr, cw / 2 + cr, cy_mid + cr,
                      outline='white', width=1)
        # Penalty areas
        pa_w = (cw - 2 * m) * 0.4
        pa_h = (ch - 2 * m) * 0.1
        # Bottom (own goal)
        c.create_rectangle(cw / 2 - pa_w / 2, ch - m - pa_h,
                           cw / 2 + pa_w / 2, ch - m, outline='white', width=1)
        # Top (opponent goal)
        c.create_rectangle(cw / 2 - pa_w / 2, m,
                           cw / 2 + pa_w / 2, m + pa_h, outline='white', width=1)

        # Goal labels
        c.create_text(cw / 2, ch - m + 12, text="OWN GOAL", fill='white',
                      font=(_MONO, 9))
        c.create_text(cw / 2, m - 12, text="OPPONENT", fill='white',
                      font=(_MONO, 9))

        if not self._tac:
            return

        # Draw players
        r = self.DOT_R
        z = self._zone
        s = self._state
        for p in range(TAC_NUM_PLAYERS):
            gx, gy = self._tac.positions[z][p][s]
            cx, cy = self._game_to_canvas(gx, gy)
            color = self._PLAYER_COLORS[p]
            c.create_oval(cx - r, cy - r, cx + r, cy + r,
                          fill=color, outline='white', width=2, tags=f'p{p}')
            c.create_text(cx, cy, text=str(p), fill='white',
                          font=(_MONO, 9, 'bold'), tags=f'p{p}')

    def _on_click(self, event):
        if not self._tac:
            return
        r = self.DOT_R + 4
        for p in range(TAC_NUM_PLAYERS):
            gx, gy = self._tac.positions[self._zone][p][self._state]
            cx, cy = self._game_to_canvas(gx, gy)
            if abs(event.x - cx) < r and abs(event.y - cy) < r:
                self._drag_player = p
                return
        self._drag_player = None

    def _on_drag(self, event):
        if self._drag_player is None or not self._tac:
            return
        gx, gy = self._canvas_to_game(event.x, event.y)
        gx = max(0, min(self.GAME_X_MAX, gx))
        gy = max(0, min(self.GAME_Y_MAX, gy))
        self._tac.set_pos(self._zone, self._drag_player, self._state, gx, gy)
        self._draw_pitch()
        self._status.set(f"Player {self._drag_player}: ({gx}, {gy})")

    def _on_release(self, event):
        self._drag_player = None


# ─── Championship Highlights ────────────────────────────────────────

class ChampionshipHighlightsWindow(tk.Toplevel):
    """Player attribute browser and championship highlights for a save slot.

    Tabs:
    - Best By Position: top 10 players for each role (GK/DEF/MID/FWD)
    - Top Scorers / Most Matches
    - Young Talents (age 16-22)
    - Market Values (highest value players)
    - Squad Analyst (per-team view with renew/sack hints)
    """

    _TOP_N = 15

    def __init__(self, parent, save, adf, game_disk=None, liga_names=None):
        super().__init__(parent)
        self.configure(bg=_THEME['bg_deep'])
        self.title(f"Championship Highlights — {save.entry.name}")
        self.geometry("1020x700")
        self.resizable(True, True)
        self._save = save
        self._adf = adf
        self._game_disk = game_disk
        self._liga = liga_names or []
        self._players = parse_player_db(adf, save.entry)
        self._build_ui()

    def _build_ui(self):
        if not self._players:
            ttk.Label(self, text="No player database found for this save slot.",
                      font=("", 13)).pack(pady=40)
            return

        ttk.Label(self,
                  text=f"{self._save.entry.name} — {len(self._players)} players",
                  font=("", 12, "bold")).pack(pady=6)

        nb = ttk.Notebook(self)
        nb.pack(fill=tk.BOTH, expand=True, padx=8, pady=4)

        # Tab 1: Best by Position
        tab_pos = ttk.Frame(nb)
        nb.add(tab_pos, text="Best By Position")
        self._build_position_tab(tab_pos)

        # Tab 2: Top Scorers / Matches
        tab_stats = ttk.Frame(nb)
        nb.add(tab_stats, text="Top Scorers")
        self._build_scorers_tab(tab_stats)

        # Tab 3: Young Talents
        tab_young = ttk.Frame(nb)
        nb.add(tab_young, text="Young Talents")
        self._build_young_tab(tab_young)

        # Tab 4: Market Values
        tab_value = ttk.Frame(nb)
        nb.add(tab_value, text="Market Values")
        self._build_value_tab(tab_value)

        # Tab 5: Squad Analyst
        tab_squad = ttk.Frame(nb)
        nb.add(tab_squad, text="Squad Analyst")
        self._build_squad_tab(tab_squad)

    def _team_name(self, team_idx):
        """Resolve team index → name using save's own team records (correct ordering)."""
        if team_idx == 0xFF:
            return "Free Agent"
        teams = self._save.teams
        if 0 <= team_idx < len(teams):
            return teams[team_idx].name
        return team_name_str(self._liga, team_idx)

    # ── Tab: Best by Position ──

    def _build_position_tab(self, parent):
        pos_nb = ttk.Notebook(parent)
        pos_nb.pack(fill=tk.BOTH, expand=True)
        for pos_code, pos_label in [(1, "Goalkeepers"), (2, "Defenders"),
                                     (3, "Midfielders"), (4, "Forwards")]:
            tab = ttk.Frame(pos_nb)
            pos_nb.add(tab, text=pos_label)
            self._build_pos_subtab(tab, pos_code)

    def _build_pos_subtab(self, parent, pos_code):
        players = [p for p in self._players.values() if p.position == pos_code]
        players.sort(key=lambda p: -p.role_skill_avg())
        players = players[:self._TOP_N]

        cols = ("rank", "name", "age", "team", "role_avg", "overall",
                "sk1", "sk2", "sk3", "sk4", "goals", "matches")
        # Pick position-relevant skill headers
        if pos_code == 1:
            sk_heads = ["Keep", "Agi", "Res"]
            sk_attrs = ["keeping", "agility", "resilience"]
        elif pos_code == 2:
            sk_heads = ["Tck", "Sta", "Agg", "Pac"]
            sk_attrs = ["tackling", "stamina", "aggression", "pace"]
        elif pos_code == 3:
            sk_heads = ["Pas", "Fla", "Sta", "Agi"]
            sk_attrs = ["passing", "flair", "stamina", "agility"]
        else:
            sk_heads = ["Sht", "Pac", "Fla", "Agi"]
            sk_attrs = ["shooting", "pace", "flair", "agility"]

        headings = ["#", "Name", "Age", "Team", "Role", "Avg"] + sk_heads + ["Gls", "Mat"]
        widths = [30, 140, 40, 140, 50, 50] + [45] * len(sk_heads) + [40, 40]
        tree = _make_scrolled_tree(parent, cols[:6 + len(sk_heads) + 2],
                               headings, widths,
                               anchors={"name": "w", "team": "w"},
                               on_double_click=self._open_editor)

        for rank, p in enumerate(players, 1):
            sk_vals = [str(getattr(p, a)) for a in sk_attrs]
            # Pad to 4 if fewer skills
            while len(sk_vals) < 4:
                sk_vals.append("")
            iid = tree.insert('', 'end', values=(
                rank,
                player_name_str(self._game_disk,p.player_id),
                p.age,
                self._team_name(p.team_index),
                f"{p.role_skill_avg():.0f}",
                f"{p.skill_avg:.0f}",
                *sk_vals[:len(sk_attrs)],
                p.goals_this_year,
                p.matches_this_year,
            ))
            tree._pid_map[iid] = p.player_id

    # ── Tab: Top Scorers ──

    def _build_scorers_tab(self, parent):
        scorer_nb = ttk.Notebook(parent)
        scorer_nb.pack(fill=tk.BOTH, expand=True)

        # Sub-tab: Goals this year
        tab_g = ttk.Frame(scorer_nb)
        scorer_nb.add(tab_g, text="Goals This Year")
        self._build_stat_list(tab_g, "goals_this_year", "Goals")

        # Sub-tab: Goals last year
        tab_gl = ttk.Frame(scorer_nb)
        scorer_nb.add(tab_gl, text="Goals Last Year")
        self._build_stat_list(tab_gl, "goals_last_year", "Goals")

        # Sub-tab: Matches this year
        tab_m = ttk.Frame(scorer_nb)
        scorer_nb.add(tab_m, text="Matches This Year")
        self._build_stat_list(tab_m, "matches_this_year", "Matches")

        # Sub-tab: Display points
        tab_d = ttk.Frame(scorer_nb)
        scorer_nb.add(tab_d, text="Display Pts This Year")
        self._build_stat_list(tab_d, "dsp_pts_this_year", "DspPts")

    def _build_stat_list(self, parent, attr, label):
        players = sorted(self._players.values(),
                         key=lambda p: -getattr(p, attr))
        players = [p for p in players if getattr(p, attr) > 0][:self._TOP_N]
        cols = ("rank", "name", "pos", "age", "team", "stat", "avg")
        headings = ["#", "Name", "Pos", "Age", "Team", label, "Skill Avg"]
        widths = [30, 140, 50, 40, 140, 60, 60]
        tree = _make_scrolled_tree(parent, cols, headings, widths,
                               anchors={"name": "w", "team": "w"},
                               on_double_click=self._open_editor)
        for rank, p in enumerate(players, 1):
            iid = tree.insert('', 'end', values=(
                rank,
                player_name_str(self._game_disk,p.player_id),
                p.position_name,
                p.age,
                self._team_name(p.team_index),
                getattr(p, attr),
                f"{p.skill_avg:.0f}",
            ))
            tree._pid_map[iid] = p.player_id

    # ── Tab: Young Talents ──

    def _build_young_tab(self, parent):
        young = [p for p in self._players.values() if 16 <= p.age <= 22]
        young.sort(key=lambda p: -p.role_skill_avg())
        young = young[:30]

        cols = ("rank", "name", "pos", "age", "team", "role_avg", "overall",
                "goals", "matches", "contract")
        headings = ["#", "Name", "Pos", "Age", "Team", "Role", "Avg",
                    "Gls", "Mat", "Contract"]
        widths = [30, 140, 50, 40, 140, 50, 50, 40, 40, 60]
        tree = _make_scrolled_tree(parent, cols, headings, widths,
                               anchors={"name": "w", "team": "w"},
                               on_double_click=self._open_editor)
        for rank, p in enumerate(young, 1):
            iid = tree.insert('', 'end', values=(
                rank,
                player_name_str(self._game_disk,p.player_id),
                p.position_name,
                p.age,
                self._team_name(p.team_index),
                f"{p.role_skill_avg():.0f}",
                f"{p.skill_avg:.0f}",
                p.goals_this_year,
                p.matches_this_year,
                p.contract_years,
            ))
            tree._pid_map[iid] = p.player_id

    # ── Tab: Market Values ──

    def _build_value_tab(self, parent):
        valued = sorted(self._players.values(), key=lambda p: -p.value)
        valued = [p for p in valued if p.value > 0][:30]

        cols = ("rank", "name", "pos", "age", "team", "value", "role_avg",
                "overall", "goals", "matches")
        headings = ["#", "Name", "Pos", "Age", "Team", "Value", "Role",
                    "Avg", "Gls", "Mat"]
        widths = [30, 140, 50, 40, 140, 50, 50, 50, 40, 40]
        tree = _make_scrolled_tree(parent, cols, headings, widths,
                               anchors={"name": "w", "team": "w"},
                               on_double_click=self._open_editor)
        for rank, p in enumerate(valued, 1):
            iid = tree.insert('', 'end', values=(
                rank,
                player_name_str(self._game_disk,p.player_id),
                p.position_name,
                p.age,
                self._team_name(p.team_index),
                p.value,
                f"{p.role_skill_avg():.0f}",
                f"{p.skill_avg:.0f}",
                p.goals_this_year,
                p.matches_this_year,
            ))
            tree._pid_map[iid] = p.player_id

    # ── Tab: Squad Analyst ──

    def _build_squad_tab(self, parent):
        top = ttk.Frame(parent)
        top.pack(fill=tk.X, padx=4, pady=4)
        ttk.Label(top, text="Team:").pack(side=tk.LEFT)
        self._squad_var = tk.StringVar()
        team_names = []
        self._squad_team_map = {}  # display_name → team_index
        for team in self._save.teams:
            if team.num_players > 0:
                disp = team.name or f"(team {team.index})"
                team_names.append(disp)
                self._squad_team_map[disp] = team.index
        combo = ttk.Combobox(top, textvariable=self._squad_var,
                             values=team_names, state='readonly', width=30)
        combo.pack(side=tk.LEFT, padx=8)
        combo.bind('<<ComboboxSelected>>', self._on_squad_selected)

        # Summary label
        self._squad_summary = ttk.Label(parent, text="", font=("", 11))
        self._squad_summary.pack(fill=tk.X, padx=8)

        # Player list
        cols = ("name", "pos", "age", "role_avg", "overall",
                "goals", "matches", "inj", "contract", "hint")
        headings = ["Name", "Pos", "Age", "Role", "Avg",
                    "Gls", "Mat", "Inj", "Contract", "Hint"]
        widths = [140, 50, 40, 50, 50, 40, 40, 35, 60, 120]
        self._squad_tree = _make_scrolled_tree(parent, cols, headings, widths,
                                           anchors={"name": "w", "hint": "w"},
                                           on_double_click=self._open_editor)
        self._squad_tree._pid_map = {}
        self._squad_tree.tag_configure('renew', background='#1E3E2E', foreground=_THEME['positive'])
        self._squad_tree.tag_configure('sack',  background='#3E1E2E', foreground=_THEME['negative'])
        self._squad_tree.tag_configure('watch', background='#3E3E1E', foreground='#CCCC44')

        if team_names:
            combo.current(0)
            self._on_squad_selected()

    def _on_squad_selected(self, event=None):
        disp = self._squad_var.get()
        team_idx = self._squad_team_map.get(disp)
        if team_idx is None:
            return
        team = self._save.teams[team_idx]

        # Collect roster player records
        roster = []
        for i in range(MAX_PLAYER_SLOTS):
            pid = struct.unpack_from('>H', team.raw, 12 + i * 2)[0]
            if pid != 0xFFFF and pid in self._players:
                roster.append(self._players[pid])

        # Summary
        if roster:
            avg_age = sum(p.age for p in roster) / len(roster)
            avg_skill = sum(p.skill_avg for p in roster) / len(roster)
            total_goals = sum(p.goals_this_year for p in roster)
            self._squad_summary.config(
                text=f"{len(roster)} players | Avg age: {avg_age:.1f} | "
                     f"Avg skill: {avg_skill:.0f} | Team goals: {total_goals}")
        else:
            self._squad_summary.config(text="No player data available")

        # Sort by position then role skill
        roster.sort(key=lambda p: (p.position, -p.role_skill_avg()))

        tree = self._squad_tree
        tree.delete(*tree.get_children())
        tree._pid_map = {}
        for p in roster:
            hint, tag = self._squad_hint(p)
            iid = tree.insert('', 'end', tags=(tag,), values=(
                player_name_str(self._game_disk,p.player_id),
                p.position_name,
                p.age,
                f"{p.role_skill_avg():.0f}",
                f"{p.skill_avg:.0f}",
                p.goals_this_year,
                p.matches_this_year,
                p.injury_weeks if p.injury_weeks else "",
                p.contract_years,
                hint,
            ))
            tree._pid_map[iid] = p.player_id

    def _squad_hint(self, p):
        """Return (hint_text, tag) for renew/sack/watch recommendations."""
        role_avg = p.role_skill_avg()
        # Young + high potential → renew
        if p.age <= 22 and role_avg >= 100:
            return "Young talent", "renew"
        # Star player with expiring contract → renew urgently
        if role_avg >= 130 and p.contract_years <= 1:
            return "Renew contract!", "renew"
        # Old + declining → consider selling
        if p.age >= 30 and role_avg < 100:
            return "Past peak", "sack"
        # Injury-prone
        if p.injuries_this_year + p.injuries_last_year >= 4:
            return "Injury prone", "watch"
        # Low skill for position
        if role_avg < 70:
            return "Below average", "sack"
        # Good performer
        if role_avg >= 130:
            return "Star player", "renew"
        return "", ""

    def _open_editor(self, event):
        """Open the Player Editor for the double-clicked row."""
        tree = event.widget
        sel = tree.selection()
        if not sel:
            return
        iid = sel[0]
        pid = tree._pid_map.get(iid)
        if pid is None or pid not in self._players:
            return
        PlayerEditorWindow(
            self, self._players[pid], self._adf, self._save.entry,
            game_disk=self._game_disk,
            on_save=lambda: self._refresh_tree(tree))

    def _refresh_tree(self, tree):
        """Placeholder for refreshing a tree after edits."""
        pass


# ─── Transfer Market Window ─────────────────────────────────────────

class TransferMarketWindow(tk.Toplevel):
    """Search, filter, and transfer players between teams."""

    def __init__(self, parent, save, adf, game_disk=None, liga_names=None):
        super().__init__(parent)
        self.configure(bg=_THEME['bg_deep'])
        self.title(f"Transfer Market — {save.entry.name}")
        self.geometry("1200x720")
        self.resizable(True, True)
        self._save = save
        self._adf = adf
        self._game_disk = game_disk
        self._liga = liga_names or []
        self._players = parse_player_db(adf, save.entry)
        self._build_ui()
        self._apply_filters()

    def _build_ui(self):
        if not self._players:
            ttk.Label(self, text="No player database found for this save slot.",
                      font=("", 13)).pack(pady=40)
            return

        # Filters
        filt = ttk.LabelFrame(self, text="Filters")
        filt.pack(fill=tk.X, padx=8, pady=(8, 4))

        r1 = ttk.Frame(filt)
        r1.pack(fill=tk.X, padx=4, pady=2)

        ttk.Label(r1, text="Search:").pack(side=tk.LEFT)
        self._search_var = tk.StringVar()
        search_entry = ttk.Entry(r1, textvariable=self._search_var, width=20)
        search_entry.pack(side=tk.LEFT, padx=4)
        search_entry.bind('<Return>', lambda e: self._apply_filters())

        ttk.Label(r1, text="Position:").pack(side=tk.LEFT, padx=(12, 0))
        self._pos_var = tk.StringVar(value="All")
        pos_combo = ttk.Combobox(r1, textvariable=self._pos_var,
                                 values=["All", "GK", "DEF", "MID", "FWD"],
                                 state='readonly', width=6)
        pos_combo.pack(side=tk.LEFT, padx=4)
        pos_combo.bind('<<ComboboxSelected>>', lambda e: self._apply_filters())

        ttk.Label(r1, text="Age:").pack(side=tk.LEFT, padx=(12, 0))
        self._age_min_var = tk.IntVar(value=16)
        self._age_max_var = tk.IntVar(value=50)
        ttk.Spinbox(r1, from_=16, to=50, textvariable=self._age_min_var,
                    width=4).pack(side=tk.LEFT, padx=2)
        ttk.Label(r1, text="–").pack(side=tk.LEFT)
        ttk.Spinbox(r1, from_=16, to=50, textvariable=self._age_max_var,
                    width=4).pack(side=tk.LEFT, padx=2)

        ttk.Label(r1, text="Min skill:").pack(side=tk.LEFT, padx=(12, 0))
        self._skill_min_var = tk.IntVar(value=0)
        ttk.Spinbox(r1, from_=0, to=200, textvariable=self._skill_min_var,
                    width=5).pack(side=tk.LEFT, padx=2)

        ttk.Button(r1, text="Apply",
                   command=self._apply_filters).pack(side=tk.LEFT, padx=8)

        r2 = ttk.Frame(filt)
        r2.pack(fill=tk.X, padx=4, pady=2)

        ttk.Label(r2, text="Team:").pack(side=tk.LEFT)
        team_values = ["All", "Free Agents"]
        for team in self._save.teams:
            if team.num_players > 0:
                team_values.append(team.name or f"(team {team.index})")
        self._team_filter_var = tk.StringVar(value="All")
        ttk.Combobox(r2, textvariable=self._team_filter_var,
                     values=team_values, state='readonly',
                     width=25).pack(side=tk.LEFT, padx=4)

        self._count_label = ttk.Label(r2, text="")
        self._count_label.pack(side=tk.RIGHT, padx=8)

        # Main PanedWindow
        pw = ttk.PanedWindow(self, orient=tk.HORIZONTAL)
        pw.pack(fill=tk.BOTH, expand=True, padx=8, pady=4)

        # Left: database list
        left = ttk.Frame(pw)
        pw.add(left, weight=3)

        cols = ("name", "pos", "age", "team", "role", "avg",
                "val", "goals", "mat")
        headings = ["Name", "Pos", "Age", "Team", "Role", "Avg",
                    "Val", "Gls", "Mat"]
        widths = [140, 45, 35, 130, 45, 45, 40, 35, 35]

        db_frame = ttk.Frame(left)
        db_frame.pack(fill=tk.BOTH, expand=True)
        self._db_tree = ttk.Treeview(db_frame, columns=cols, show='headings')
        for col, hd, w in zip(cols, headings, widths):
            self._db_tree.heading(col, text=hd,
                                  command=lambda c=col: self._sort_column(c))
            anc = 'w' if col in ('name', 'team') else 'center'
            self._db_tree.column(col, width=w, anchor=anc)
        vsb = ttk.Scrollbar(db_frame, orient='vertical',
                            command=self._db_tree.yview)
        self._db_tree.configure(yscrollcommand=vsb.set)
        vsb.pack(side=tk.RIGHT, fill=tk.Y)
        self._db_tree.pack(fill=tk.BOTH, expand=True)
        self._db_tree._pid_map = {}
        self._db_tree.bind('<Double-1>', self._on_db_double_click)

        btn_mid = ttk.Frame(left)
        btn_mid.pack(fill=tk.X, pady=4)
        ttk.Button(btn_mid, text="Transfer to Team →",
                   command=self._transfer_to_team).pack(side=tk.LEFT, padx=4)
        ttk.Button(btn_mid, text="Edit Player…",
                   command=self._edit_selected).pack(side=tk.LEFT, padx=4)

        # Right: team roster
        right = ttk.LabelFrame(pw, text="Team Roster")
        pw.add(right, weight=2)

        top_r = ttk.Frame(right)
        top_r.pack(fill=tk.X, padx=4, pady=4)
        ttk.Label(top_r, text="Team:").pack(side=tk.LEFT)
        self._roster_team_var = tk.StringVar()
        roster_teams = []
        self._roster_team_map = {}
        for team in self._save.teams:
            disp = team.name or f"(team {team.index})"
            roster_teams.append(disp)
            self._roster_team_map[disp] = team.index
        self._roster_combo = ttk.Combobox(
            top_r, textvariable=self._roster_team_var,
            values=roster_teams, state='readonly', width=25)
        self._roster_combo.pack(side=tk.LEFT, padx=4)
        self._roster_combo.bind('<<ComboboxSelected>>', self._load_roster)

        self._roster_summary = ttk.Label(right, text="")
        self._roster_summary.pack(fill=tk.X, padx=8)

        rcols = ("name", "pos", "age", "role", "avg")
        rheadings = ["Name", "Pos", "Age", "Role", "Avg"]
        rwidths = [140, 45, 35, 45, 45]
        roster_frame = ttk.Frame(right)
        roster_frame.pack(fill=tk.BOTH, expand=True, padx=4, pady=4)
        self._roster_tree = ttk.Treeview(roster_frame, columns=rcols,
                                         show='headings')
        for col, hd, w in zip(rcols, rheadings, rwidths):
            self._roster_tree.heading(col, text=hd)
            anc = 'w' if col == 'name' else 'center'
            self._roster_tree.column(col, width=w, anchor=anc)
        rvsb = ttk.Scrollbar(roster_frame, orient='vertical',
                             command=self._roster_tree.yview)
        self._roster_tree.configure(yscrollcommand=rvsb.set)
        rvsb.pack(side=tk.RIGHT, fill=tk.Y)
        self._roster_tree.pack(fill=tk.BOTH, expand=True)
        self._roster_tree._pid_map = {}

        rbtn = ttk.Frame(right)
        rbtn.pack(fill=tk.X, padx=4, pady=4)
        ttk.Button(rbtn, text="← Remove from Team",
                   command=self._remove_from_team).pack(side=tk.LEFT, padx=4)

        if roster_teams:
            self._roster_combo.current(0)
            self._load_roster()

    def _sort_column(self, col):
        reverse = getattr(self, '_sort_reverse', False)
        items = [(self._db_tree.set(iid, col), iid)
                 for iid in self._db_tree.get_children('')]
        try:
            items.sort(key=lambda t: float(t[0]), reverse=reverse)
        except ValueError:
            items.sort(key=lambda t: t[0].lower(), reverse=reverse)
        for idx, (_, iid) in enumerate(items):
            self._db_tree.move(iid, '', idx)
        self._sort_reverse = not reverse

    def _apply_filters(self):
        tree = self._db_tree
        tree.delete(*tree.get_children())
        tree._pid_map = {}

        search = self._search_var.get().lower().strip()
        pos_filter = self._pos_var.get()
        age_lo = self._age_min_var.get()
        age_hi = self._age_max_var.get()
        skill_min = self._skill_min_var.get()
        team_filter = self._team_filter_var.get()

        pos_code = {"GK": 1, "DEF": 2, "MID": 3, "FWD": 4}.get(pos_filter)
        team_idx_filter = None
        if team_filter == "Free Agents":
            team_idx_filter = 0xFF
        elif team_filter != "All":
            for team in self._save.teams:
                disp = team.name or f"(team {team.index})"
                if disp == team_filter:
                    team_idx_filter = team.index
                    break

        count = 0
        for pid, p in sorted(self._players.items()):
            if pos_code is not None and p.position != pos_code:
                continue
            if not (age_lo <= p.age <= age_hi):
                continue
            if p.role_skill_avg() < skill_min:
                continue
            if team_idx_filter is not None and p.team_index != team_idx_filter:
                continue
            if search:
                name = player_name_str(self._game_disk,pid).lower()
                if search not in name:
                    continue

            iid = tree.insert('', 'end', values=(
                player_name_str(self._game_disk,pid),
                p.position_name,
                p.age,
                self._team_name(p.team_index),
                f"{p.role_skill_avg():.0f}",
                f"{p.skill_avg:.0f}",
                p.value,
                p.goals_this_year,
                p.matches_this_year,
            ))
            tree._pid_map[iid] = pid
            count += 1

        self._count_label.config(text=f"{count} players")

    def _load_roster(self, event=None):
        disp = self._roster_team_var.get()
        team_idx = self._roster_team_map.get(disp)
        if team_idx is None:
            return
        team = self._save.teams[team_idx]

        tree = self._roster_tree
        tree.delete(*tree.get_children())
        tree._pid_map = {}

        roster = []
        for i in range(MAX_PLAYER_SLOTS):
            pid = struct.unpack_from('>H', team.raw, 12 + i * 2)[0]
            if pid != 0xFFFF and pid in self._players:
                roster.append(self._players[pid])

        roster.sort(key=lambda p: (p.position, -p.role_skill_avg()))
        for p in roster:
            iid = tree.insert('', 'end', values=(
                player_name_str(self._game_disk,p.player_id),
                p.position_name,
                p.age,
                f"{p.role_skill_avg():.0f}",
                f"{p.skill_avg:.0f}",
            ))
            tree._pid_map[iid] = p.player_id

        self._roster_summary.config(
            text=f"{len(roster)} / {MAX_PLAYER_SLOTS} slots filled")

    def _transfer_to_team(self):
        sel = self._db_tree.selection()
        if not sel:
            messagebox.showinfo("Info", "Select a player from the left list.",
                                parent=self)
            return
        pid = self._db_tree._pid_map.get(sel[0])
        if pid is None:
            return

        disp = self._roster_team_var.get()
        dest_idx = self._roster_team_map.get(disp)
        if dest_idx is None:
            messagebox.showinfo("Info", "Select a destination team.",
                                parent=self)
            return

        dest_team = self._save.teams[dest_idx]
        player = self._players[pid]

        filled = sum(1 for i in range(MAX_PLAYER_SLOTS)
                     if struct.unpack_from('>H', dest_team.raw, 12 + i * 2)[0]
                     != 0xFFFF)
        if filled >= MAX_PLAYER_SLOTS:
            messagebox.showwarning("Full",
                                   f"{disp} has no empty roster slots (25/25).",
                                   parent=self)
            return

        for i in range(MAX_PLAYER_SLOTS):
            existing = struct.unpack_from('>H', dest_team.raw, 12 + i * 2)[0]
            if existing == pid:
                messagebox.showinfo("Info",
                                    f"Player is already on {disp}.",
                                    parent=self)
                return

        old_idx = player.team_index
        if old_idx != 0xFF and old_idx < len(self._save.teams):
            old_team = self._save.teams[old_idx]
            for i in range(MAX_PLAYER_SLOTS):
                if struct.unpack_from('>H', old_team.raw, 12 + i * 2)[0] == pid:
                    struct.pack_into('>H', old_team.raw, 12 + i * 2, 0xFFFF)
                    old_team.player_values[i] = 0xFFFF
                    old_team.num_players = sum(
                        1 for v in old_team.player_values if v != 0xFFFF)
                    break

        for i in range(MAX_PLAYER_SLOTS):
            if struct.unpack_from('>H', dest_team.raw, 12 + i * 2)[0] == 0xFFFF:
                struct.pack_into('>H', dest_team.raw, 12 + i * 2, pid)
                dest_team.player_values[i] = pid
                dest_team.num_players = sum(
                    1 for v in dest_team.player_values if v != 0xFFFF)
                break

        player.team_index = dest_idx
        self._save.write_back()
        write_player_db(self._adf, self._save.entry, {pid: player})
        self._load_roster()
        self._apply_filters()

    def _remove_from_team(self):
        sel = self._roster_tree.selection()
        if not sel:
            messagebox.showinfo("Info", "Select a player from the roster.",
                                parent=self)
            return
        pid = self._roster_tree._pid_map.get(sel[0])
        if pid is None:
            return

        disp = self._roster_team_var.get()
        team_idx = self._roster_team_map.get(disp)
        if team_idx is None:
            return

        team = self._save.teams[team_idx]
        player = self._players[pid]

        for i in range(MAX_PLAYER_SLOTS):
            if struct.unpack_from('>H', team.raw, 12 + i * 2)[0] == pid:
                struct.pack_into('>H', team.raw, 12 + i * 2, 0xFFFF)
                team.player_values[i] = 0xFFFF
                team.num_players = sum(
                    1 for v in team.player_values if v != 0xFFFF)
                break

        player.team_index = 0xFF
        self._save.write_back()
        write_player_db(self._adf, self._save.entry, {pid: player})
        self._load_roster()
        self._apply_filters()

    def _on_db_double_click(self, event):
        sel = self._db_tree.selection()
        if not sel:
            return
        pid = self._db_tree._pid_map.get(sel[0])
        if pid is not None and pid in self._players:
            PlayerEditorWindow(
                self, self._players[pid], self._adf, self._save.entry,
                game_disk=self._game_disk,
                on_save=self._apply_filters)

    def _edit_selected(self):
        sel = self._db_tree.selection()
        if not sel:
            messagebox.showinfo("Info", "Select a player first.", parent=self)
            return
        pid = self._db_tree._pid_map.get(sel[0])
        if pid is not None and pid in self._players:
            PlayerEditorWindow(
                self, self._players[pid], self._adf, self._save.entry,
                game_disk=self._game_disk,
                on_save=self._apply_filters)


# ─── Player Editor Window ───────────────────────────────────────────

class PlayerEditorWindow(tk.Toplevel):
    """Edit a single player's attributes and write changes to the ADF."""

    _SKILL_FIELDS = [
        ("Stamina",    "stamina"),
        ("Resilience", "resilience"),
        ("Pace",       "pace"),
        ("Agility",    "agility"),
        ("Aggression", "aggression"),
        ("Flair",      "flair"),
        ("Passing",    "passing"),
        ("Shooting",   "shooting"),
        ("Tackling",   "tackling"),
        ("Keeping",    "keeping"),
    ]
    _INFO_FIELDS = [
        ("Age",             "age",             0, 50),
        ("Position (1-4)",  "position",        0, 4),
        ("Height (cm)",     "height",          140, 255),
        ("Weight (kg)",     "weight",          30, 150),
        ("Contract years",  "contract_years",  0, 20),
        ("Market value",    "value",           0, 255),
    ]
    _STAT_FIELDS = [
        ("Injury weeks",       "injury_weeks"),
        ("Injuries this year", "injuries_this_year"),
        ("Injuries last year", "injuries_last_year"),
        ("Goals this year",    "goals_this_year"),
        ("Goals last year",    "goals_last_year"),
        ("Matches this year",  "matches_this_year"),
        ("Matches last year",  "matches_last_year"),
    ]

    def __init__(self, parent, player, adf, dir_entry, game_disk=None,
                 on_save=None):
        """
        player:    PlayerRecord to edit (modified in place)
        adf:       ADF instance (for write-back)
        dir_entry: DirEntry of the .sav file this player DB belongs to
        game_disk: optional GameDisk for name lookup
        on_save:   optional callback() invoked after successful write
        """
        super().__init__(parent)
        self.configure(bg=_THEME['bg_deep'])
        self._player = player
        self._adf = adf
        self._dir_entry = dir_entry
        self._game_disk = game_disk
        self._on_save = on_save

        name = ""
        if game_disk:
            name = game_disk.player_name(player.player_id)
        self.title(f"Edit Player — {name or f'#{player.player_id}'}")
        self.geometry("480x620")
        self.resizable(False, True)

        self._vars = {}   # attr_name → tk.IntVar
        self._build_ui()

    def _build_ui(self):
        canvas = tk.Canvas(self, borderwidth=0, bg=_THEME['bg_deep'])
        scrollbar = ttk.Scrollbar(self, orient="vertical", command=canvas.yview)
        inner = ttk.Frame(canvas)
        inner.bind("<Configure>",
                   lambda e: canvas.configure(scrollregion=canvas.bbox("all")))
        canvas.create_window((0, 0), window=inner, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        row = 0

        # Player info header
        p = self._player
        pos_name = POSITION_NAMES.get(p.position, "?")
        ttk.Label(inner, text=f"ID {p.player_id}  |  {pos_name}  |  "
                              f"Age {p.age}  |  Avg {p.skill_avg:.0f}",
                  font=("", 12, "bold")).grid(
            row=row, column=0, columnspan=3, pady=(8, 12), padx=8, sticky="w")
        row += 1

        # Info fields
        ttk.Label(inner, text="Player Info",
                  font=("", 11, "bold")).grid(
            row=row, column=0, columnspan=3, pady=(8, 4), padx=8, sticky="w")
        row += 1

        for label, attr, lo, hi in self._INFO_FIELDS:
            ttk.Label(inner, text=label).grid(row=row, column=0, padx=(12, 4),
                                              sticky="e")
            var = tk.IntVar(value=getattr(p, attr))
            self._vars[attr] = var
            spin = ttk.Spinbox(inner, from_=lo, to=hi, textvariable=var,
                               width=6)
            spin.grid(row=row, column=1, padx=4, sticky="w")
            row += 1

        # Skills (0-200 sliders + spinboxes)
        ttk.Label(inner, text="Skills (0–200)",
                  font=("", 11, "bold")).grid(
            row=row, column=0, columnspan=3, pady=(12, 4), padx=8, sticky="w")
        row += 1

        for label, attr in self._SKILL_FIELDS:
            ttk.Label(inner, text=label).grid(row=row, column=0, padx=(12, 4),
                                              sticky="e")
            var = tk.IntVar(value=getattr(p, attr))
            self._vars[attr] = var
            scale = ttk.Scale(inner, from_=0, to=200, variable=var,
                              orient=tk.HORIZONTAL, length=180)
            scale.grid(row=row, column=1, padx=4, sticky="w")
            spin = ttk.Spinbox(inner, from_=0, to=200, textvariable=var,
                               width=5)
            spin.grid(row=row, column=2, padx=4, sticky="w")
            row += 1

        # Career stats
        ttk.Label(inner, text="Career Stats",
                  font=("", 11, "bold")).grid(
            row=row, column=0, columnspan=3, pady=(12, 4), padx=8, sticky="w")
        row += 1

        for label, attr in self._STAT_FIELDS:
            ttk.Label(inner, text=label).grid(row=row, column=0, padx=(12, 4),
                                              sticky="e")
            var = tk.IntVar(value=getattr(p, attr))
            self._vars[attr] = var
            spin = ttk.Spinbox(inner, from_=0, to=255, textvariable=var,
                               width=6)
            spin.grid(row=row, column=1, padx=4, sticky="w")
            row += 1

        # Buttons
        btn_frame = ttk.Frame(inner)
        btn_frame.grid(row=row, column=0, columnspan=3, pady=12)
        ttk.Button(btn_frame, text="Apply to ADF", style='Primary.TButton',
                   command=self._apply).pack(side=tk.LEFT, padx=8)
        ttk.Button(btn_frame, text="Reset",
                   command=self._reset).pack(side=tk.LEFT, padx=8)
        ttk.Button(btn_frame, text="Max All Skills",
                   command=self._max_skills).pack(side=tk.LEFT, padx=8)

    def _apply(self):
        """Copy UI values into the PlayerRecord and write to ADF."""
        p = self._player
        for attr, var in self._vars.items():
            val = var.get()
            val = max(0, min(255, val))
            setattr(p, attr, val)
        db_offset = self._dir_entry.byte_offset + self._dir_entry.size_bytes
        records_start = db_offset + PLAYER_DB_HEADER_SIZE
        off = records_start + p.player_id * PLAYER_RECORD_SIZE
        if off + PLAYER_RECORD_SIZE <= ADF_SIZE:
            self._adf.write_bytes(off, p.pack())
        if self._on_save:
            self._on_save()
        messagebox.showinfo("Applied",
                            f"Player #{p.player_id} updated in ADF buffer.\n"
                            "Use File → Save to write to disk.",
                            parent=self)

    def _reset(self):
        """Reset UI vars to current PlayerRecord values."""
        p = self._player
        for attr, var in self._vars.items():
            var.set(getattr(p, attr))

    def _max_skills(self):
        """Set all 10 skills to 200."""
        for _, attr in self._SKILL_FIELDS:
            self._vars[attr].set(200)


# ─── Disassembler Window ────────────────────────────────────────────

class DisassemblerWindow(tk.Toplevel):
    """Interactive 68000 disassembler and cross-reference browser for
    the decompressed Player Manager game image."""

    def __init__(self, parent, game_disk):
        super().__init__(parent)
        self.configure(bg=_THEME['bg_deep'])
        self.title("68000 Disassembler — Game Image")
        self.geometry("900x750")
        self.resizable(True, True)

        self._gd = game_disk
        self._disasm = Disasm68k(game_disk.game_image, base_addr=0)
        self._history = []        # Navigation history (list of offsets)

        self._build_ui()
        # Start at the entry point
        self._goto(0)

    def _build_ui(self):
        T = _THEME
        # Top bar: navigation
        nav = tk.Frame(self, bg=T['bg_deep'])
        nav.pack(fill=tk.X, padx=8, pady=6)

        ttk.Label(nav, text="Address:").pack(side=tk.LEFT, padx=4)
        self._addr_var = tk.StringVar(value="$000000")
        addr_entry = ttk.Entry(nav, textvariable=self._addr_var, width=10,
                               font=(_MONO, 12))
        addr_entry.pack(side=tk.LEFT, padx=4)
        addr_entry.bind('<Return>', lambda e: self._go_to_addr())

        ttk.Button(nav, text="Go", command=self._go_to_addr, style='Primary.TButton').pack(side=tk.LEFT, padx=2)
        ttk.Button(nav, text="← Back", command=self._go_back).pack(side=tk.LEFT, padx=8)

        ttk.Label(nav, text="Lines:").pack(side=tk.LEFT, padx=(12, 4))
        self._lines_var = tk.StringVar(value="80")
        ttk.Spinbox(nav, from_=20, to=500, textvariable=self._lines_var,
                    width=5).pack(side=tk.LEFT, padx=2)

        # Quick jumps
        qf = ttk.LabelFrame(self, text="Quick Navigation")
        qf.pack(fill=tk.X, padx=8, pady=2)
        qg = ttk.Frame(qf)
        qg.pack(fill=tk.X, padx=8, pady=4)

        quick_targets = [
            ("Entry ($0000)", 0x0000),
            ("Age ($11740)", 0x11740),
            ("Name char ($1608A)", 0x1608A),
            ("Names table ($15B02)", 0x15B02),
            ("JMP vectors ($134D8)", 0x134D8),
            ("Strings ($14000)", 0x14000),
        ]
        for i, (label, addr) in enumerate(quick_targets):
            ttk.Button(qg, text=label, style='Primary.TButton',
                       command=lambda a=addr: self._goto(a)).grid(
                row=0, column=i, padx=3, pady=2)

        # Search tools
        sf = ttk.LabelFrame(self, text="Search / Cross-Reference")
        sf.pack(fill=tk.X, padx=8, pady=2)
        sg = ttk.Frame(sf)
        sg.pack(fill=tk.X, padx=8, pady=4)

        ttk.Label(sg, text="Find references to:").grid(row=0, column=0, sticky='e', padx=4)
        self._xref_var = tk.StringVar()
        ttk.Entry(sg, textvariable=self._xref_var, width=10,
                  font=(_MONO, 11)).grid(row=0, column=1, padx=4)
        ttk.Button(sg, text="X-Ref", command=self._do_xref, style='Primary.TButton').grid(
            row=0, column=2, padx=4)

        ttk.Label(sg, text="Search word:").grid(row=0, column=3, sticky='e', padx=(12, 4))
        self._sword_var = tk.StringVar()
        ttk.Entry(sg, textvariable=self._sword_var, width=10,
                  font=(_MONO, 11)).grid(row=0, column=4, padx=4)
        ttk.Button(sg, text="Find", command=self._do_word_search, style='Primary.TButton').grid(
            row=0, column=5, padx=4)

        ttk.Label(sg, text="MULU/DIVU #imm:").grid(row=1, column=0, sticky='e', padx=4, pady=4)
        self._mulimm_var = tk.StringVar()
        ttk.Entry(sg, textvariable=self._mulimm_var, width=10,
                  font=(_MONO, 11)).grid(row=1, column=1, padx=4, pady=4)
        ttk.Button(sg, text="Find MUL/DIV", command=self._find_muldiv).grid(
            row=1, column=2, padx=4, pady=4)

        # Main disassembly output
        main = ttk.Frame(self)
        main.pack(fill=tk.BOTH, expand=True, padx=8, pady=4)

        self._text = tk.Text(main, font=(_MONO, 11), wrap='none',
                             bg='#1e1e1e', fg='#d4d4d4', insertbackground='white',
                             state='disabled')
        vsb = ttk.Scrollbar(main, orient='vertical', command=self._text.yview)
        hsb = ttk.Scrollbar(main, orient='horizontal', command=self._text.xview)
        self._text.configure(yscrollcommand=vsb.set, xscrollcommand=hsb.set)
        vsb.pack(side=tk.RIGHT, fill=tk.Y)
        hsb.pack(side=tk.BOTTOM, fill=tk.X)
        self._text.pack(fill=tk.BOTH, expand=True)

        # Tag colors
        self._text.tag_configure('addr', foreground='#569CD6')
        self._text.tag_configure('mnemonic', foreground='#DCDCAA')
        self._text.tag_configure('hex', foreground='#6A9955')
        self._text.tag_configure('comment', foreground='#6A9955')
        self._text.tag_configure('header', foreground='#CE9178')
        self._text.tag_configure('xref_result', foreground='#4EC9B0')

        # Double-click to follow address
        self._text.bind('<Double-Button-1>', self._on_double_click)

        # Status
        self._status = tk.StringVar(value="Ready")
        tk.Label(self, textvariable=self._status, relief='sunken',
                 anchor='w', bg=T['bg_chrome'], fg=T['text'],
                 font=T['font_small']).pack(fill=tk.X, side=tk.BOTTOM, padx=2, pady=2)

    def _goto(self, addr):
        self._history.append(addr)
        self._addr_var.set(f'${addr:06X}')
        self._disasm_at(addr)

    def _go_to_addr(self):
        try:
            addr = _parse_hex_str(self._addr_var.get())
        except ValueError:
            return
        self._goto(addr)

    def _go_back(self):
        if len(self._history) > 1:
            self._history.pop()
            addr = self._history[-1]
            self._addr_var.set(f'${addr:06X}')
            self._disasm_at(addr)

    def _disasm_at(self, addr):
        try:
            num_lines = int(self._lines_var.get())
        except ValueError:
            num_lines = 80

        t = self._text
        t.config(state='normal')
        t.delete('1.0', tk.END)

        # Header
        t.insert(tk.END, f"; Disassembly at ${addr:06X}\n", 'header')
        t.insert(tk.END, f"; Game image: {len(self._gd.game_image)} bytes "
                         f"({len(self._gd.game_image) // 1024}K)\n\n", 'header')

        off = addr
        count = 0
        while count < num_lines and off < len(self._gd.game_image):
            a, mne, n = self._disasm.disasm_one(off)
            raw = self._gd.game_image[off:off + n]
            hex_str = ' '.join(f'{b:02X}' for b in raw)

            t.insert(tk.END, f'${a:06X}', 'addr')
            t.insert(tk.END, f'  {hex_str:<20s}', 'hex')
            t.insert(tk.END, f'  {mne}', 'mnemonic')

            # Auto-annotate known offsets
            comment = self._auto_comment(a, mne)
            if comment:
                t.insert(tk.END, f'  ; {comment}', 'comment')
            t.insert(tk.END, '\n')

            off += n
            count += 1

        t.config(state='disabled')
        self._status.set(f"Showing {count} instructions from ${addr:06X}")

    def _auto_comment(self, addr, mne):
        """Generate automatic comments for known addresses and patterns."""
        comments = []
        if '$011740' in mne:
            comments.append('Manager age (displayed = stored + 1)')
        if '$01608A' in mne:
            comments.append('Manager name character')
        if '$015B02' in mne:
            comments.append('Player name table start')
        if '$0162E6' in mne:
            comments.append('Player name table end')
        if '$050000' in mne or '$50000' in mne.replace(' ', ''):
            comments.append('Game image base address')
        if 'MULU' in mne and '#$0064' in mne:
            comments.append('× 100 (team record size)')
        if 'DIVU' in mne and '#$0064' in mne:
            comments.append('÷ 100 (team record size)')
        if 'MULU' in mne and '#$002A' in mne:
            comments.append('× 42')
        if '$DFF09A' in mne:
            comments.append('INTENA')
        if '$DFF096' in mne:
            comments.append('DMACON')
        return ', '.join(comments)

    def _on_double_click(self, event):
        """Double-click an address in the disassembly to navigate there."""
        idx = self._text.index(f'@{event.x},{event.y}')
        line = self._text.get(f'{idx} linestart', f'{idx} lineend')
        # Look for $XXXXXX patterns in the line
        import re
        matches = re.findall(r'\$([0-9A-Fa-f]{4,8})', line)
        if matches:
            # Navigate to the last address-like match (skip the line's own address)
            for m in reversed(matches):
                val = int(m, 16)
                if val < len(self._gd.game_image) and val != self._history[-1]:
                    self._goto(val)
                    return

    def _do_xref(self):
        """Find all instructions referencing a given address."""
        try:
            target = _parse_hex_str(self._xref_var.get())
        except ValueError:
            return

        self._status.set(f"Searching cross-references to ${target:06X}...")
        self.update()

        code_end = min(len(self._gd.game_image), 0x134D8)
        results = self._disasm.xref_search(target, 0, code_end)

        t = self._text
        t.config(state='normal')
        t.delete('1.0', tk.END)
        t.insert(tk.END, f"; Cross-references to ${target:06X}\n", 'header')
        t.insert(tk.END, f"; Searched ${0:06X}–${code_end:06X} "
                         f"({len(results)} results)\n\n", 'header')

        for a, mne, n in results:
            raw = self._gd.game_image[a:a + n]
            hex_str = ' '.join(f'{b:02X}' for b in raw)
            t.insert(tk.END, f'${a:06X}', 'addr')
            t.insert(tk.END, f'  {hex_str:<20s}', 'hex')
            t.insert(tk.END, f'  {mne}\n', 'xref_result')

        if not results:
            t.insert(tk.END, '  (no references found)\n')

        t.config(state='disabled')
        self._status.set(f"Found {len(results)} references to ${target:06X}")

    def _do_word_search(self):
        """Find occurrences of a 16-bit word in the code region."""
        try:
            word = _parse_hex_str(self._sword_var.get()) & 0xFFFF
        except ValueError:
            return

        self._status.set(f"Searching for word ${word:04X}...")
        self.update()

        code_end = min(len(self._gd.game_image), 0x134D8)
        results = []
        for off in range(0, code_end, 2):
            if _read16(self._gd.game_image, off) == word:
                a, mne, n = self._disasm.disasm_one(off)
                results.append((a, mne, n))

        t = self._text
        t.config(state='normal')
        t.delete('1.0', tk.END)
        t.insert(tk.END, f"; Search for word ${word:04X}\n", 'header')
        t.insert(tk.END, f"; {len(results)} occurrences in code region\n\n", 'header')

        for a, mne, n in results[:200]:
            raw = self._gd.game_image[a:a + n]
            hex_str = ' '.join(f'{b:02X}' for b in raw)
            t.insert(tk.END, f'${a:06X}', 'addr')
            t.insert(tk.END, f'  {hex_str:<20s}', 'hex')
            t.insert(tk.END, f'  {mne}\n', 'xref_result')

        if len(results) > 200:
            t.insert(tk.END, f'\n  ... and {len(results) - 200} more\n')

        t.config(state='disabled')
        self._status.set(f"Found {len(results)} occurrences of ${word:04X}")

    def _find_muldiv(self):
        """Find all MULU/MULS/DIVU/DIVS with a specific immediate value."""
        try:
            val = int(self._mulimm_var.get().strip().replace('$', '').replace('0x', ''), 0)
        except ValueError:
            try:
                val = int(self._mulimm_var.get().strip())
            except ValueError:
                return

        self._status.set(f"Searching MULU/DIVU #{val}...")
        self.update()

        code_end = min(len(self._gd.game_image), 0x134D8)
        results = []
        off = 0
        while off < code_end:
            a, mne, n = self._disasm.disasm_one(off)
            if ('MULU' in mne or 'MULS' in mne or 'DIVU' in mne or 'DIVS' in mne):
                # Check if the immediate matches
                imm_hex4 = f'#${val:04X}'
                imm_hex2 = f'#${val:02X}'
                if imm_hex4 in mne or imm_hex2 in mne:
                    results.append((a, mne, n))
            off += n

        t = self._text
        t.config(state='normal')
        t.delete('1.0', tk.END)
        t.insert(tk.END, f"; MULU/MULS/DIVU/DIVS with immediate #{val} (${val:04X})\n", 'header')
        t.insert(tk.END, f"; {len(results)} results\n\n", 'header')

        for a, mne, n in results:
            raw = self._gd.game_image[a:a + n]
            hex_str = ' '.join(f'{b:02X}' for b in raw)
            t.insert(tk.END, f'${a:06X}', 'addr')
            t.insert(tk.END, f'  {hex_str:<20s}', 'hex')
            t.insert(tk.END, f'  {mne}', 'xref_result')
            comment = self._auto_comment(a, mne)
            if comment:
                t.insert(tk.END, f'  ; {comment}', 'comment')
            t.insert(tk.END, '\n')

        t.config(state='disabled')
        self._status.set(f"Found {len(results)} MULU/DIVU #{val}")


# ─── Main ────────────────────────────────────────────────────────────

def main():
    root = tk.Tk()

    # Retina / HiDPI scaling on macOS
    if _IS_MAC:
        try:
            root.tk.call('tk', 'scaling', 2.0)
        except tk.TclError:
            pass

    _apply_theme(root)

    app = PMSaveDiskToolApp(root)
    root.mainloop()


if __name__ == '__main__':
    main()
