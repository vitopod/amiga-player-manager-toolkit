# PMSaveDiskTool GUI Redesign — Design Spec

## Goal

Redesign the PMSaveDiskTool GUI from a generic tkinter app into a cohesive, themed tool with a layout that reflects how the app is actually used: focused save-disk editing, one task at a time. All 7 views (main editor + 6 tool windows) share the same visual language.

## Theme: Hybrid — Amiga Bones, Modern Skin

Dark theme with subtle Amiga nods. Orange highlights from Workbench, monospace for data/hex, but modern layout and spacing.

### Color Palette

| Role | Color | Hex | Usage |
|------|-------|-----|-------|
| Background (deep) | Dark navy | `#1E1E2E` | Main content area, tab bodies |
| Background (elevated) | Dark slate | `#2A2A3C` | Sidebar, cards, table alt-rows, tab content |
| Background (surface) | Lighter slate | `#363650` | Buttons (secondary), borders, separators |
| Header/chrome | Deepest navy | `#16162A` | Title bar, status bar |
| Primary accent | Amiga orange | `#F28C28` | Primary buttons, active tab, section headers, selected items, left border accents |
| Secondary accent | Cyan | `#4FC3F7` | Data values (IDs, team section header), links, informational badges |
| Positive | Green | `#44CC44` | Positive values (team value surplus), success states |
| Negative | Soft red | `#E57373` | Negative values (debt), destructive actions (remove player) |
| Text (primary) | Light gray | `#C8C8D0` | Body text |
| Text (bright) | White | `#FFFFFF` | Team names, player names, emphasized text |
| Text (muted) | Mid gray | `#888888` | Labels, column headers, secondary info |
| Text (dim) | Dark gray | `#555555` | Empty slots, disabled items, placeholder text |

### Typography

| Context | Font | Size |
|---------|------|------|
| Data fields, hex dumps, IDs, tables | Menlo (monospace) | 11px |
| Section headers | Menlo Bold, uppercase, letter-spacing 1px | 10px |
| Team name in header bar | Menlo Bold | 14px |
| Status bar | Menlo | 10px |
| Buttons | Menlo Bold | 10px |

Menlo throughout — monospace fits the reverse-engineering/data-editing nature of the tool. No sans-serif mixing.

## Main Window Layout

### Structure

```
┌─────────────────────────────────────────────────────────────────┐
│ [PM] Save Disk Tool    ▸ File  ▸ Tools     ⬡ GameDisk loaded   │ Title bar (#16162A)
├─────────────────────────────────────────────────────────────────┤
│ [Open ADF] [Save] [Save As…]              DataDisk.adf         │ Toolbar (#22223A)
├──────────────┬──────────────────────────────────────────────────┤
│ SAVE SLOTS   │ ┌─ BAYERN MUNCHEN ─── [DIV 1] +4357  46 ─────┐ │ Team header bar
│ ► START.sav  │ │                     [Become Mgr] [Apply]    │ │ (#2A2A3C)
│   WIN.sav    │ ├─────────────────────────────────────────────┤ │
│   SEASON3.sav│ │ [Roster]  Team Info  League Stats  Hex Dump │ │ Tabs
│              │ ├─────────────────────────────────────────────┤ │
│ TEAMS (44)   │ │                                             │ │
│ 🔍 Filter…   │ │  #  ID    Player Name                      │ │
│ ▼ Division 1 │ │  0  473   Zinetti                    edit   │ │ Tab content
│  BAYERN MUN. │ │  1  637   Nava                       edit   │ │
│  1. FC KOLN  │ │  2  816   Florentini                 edit   │ │
│ ▼ Division 2 │ │  3   15   Bergomi                    edit   │ │
│  BOR. DORT.  │ │  4   —    empty slot                        │ │
│ ...          │ │                                             │ │
│              │ │ [Set Player ID]  [Remove Player]  18/25     │ │ Roster actions
├──────────────┴─┴─────────────────────────────────────────────┴─┤
│ Game disk: PlayerManagerITA.adf — 245 names  START.sav→BAYERN  │ Status bar (#16162A)
└────────────────────────────────────────────────────────────────-┘
```

### Empty States

**No file loaded** (app launch, before Open ADF):
- Sidebar: Save Slots and Teams sections visible but empty, muted placeholder text ("No save disk loaded")
- Right panel: no team header bar, no tabs. Instead, a centered vertical layout:
  - "PM" in large orange text (24px)
  - "Save Disk Tool" in primary text (16px)
  - [Open ADF] button (orange, prominent)
  - Muted hint text: "Open a Player Manager save disk ADF to begin"
  - If game disk loaded, show below: "Game disk ready: PlayerManagerITA.adf" in cyan

**File loaded, no team selected:**
- Sidebar: populated with save slots and teams
- Right panel: no team header bar. Tab area shows centered message: "Select a team from the sidebar" in muted text. No tabs visible.

**Team selected but save slot uses start.dat template:**
- Normal layout, but division column may show "?" for non-standard values. Team header badge shows "?" instead of "DIV N".

### Title Bar

- Left: "PM" in orange bold + "Save Disk Tool" in primary text
- Right: game disk status indicator — "⬡ PlayerManagerITA.adf loaded" in cyan if loaded, "(no game disk)" in muted if not

### Toolbar

- Buttons: "Open ADF" (primary/orange), "Save" (secondary/surface), "Save As…" (secondary)
- Right-aligned: loaded filename in muted text, or "No file loaded" in dim
- Background: `#22223A` (slightly lighter than deep bg)

### Left Sidebar (width: ~240px, fixed)

**Save Slots section:**
- Section header: "SAVE SLOTS" in orange, uppercase, letter-spacing
- Left border accent: 3px solid orange
- Selected slot: orange background with dark text
- Unselected: plain text
- Template entries: italic, muted color

**Teams section:**
- Section header: "TEAMS (N)" in cyan, uppercase
- Left border accent: 3px solid cyan
- Filter input: inline search box at top, filters teams as you type across all divisions. Placeholder text: "Filter teams…"
- **Grouped by division**: collapsible tree with division headers
  - "▼ Division 1 (11)" — expanded by default
  - "▼ Division 2 (11)" — expanded by default
  - "► Division 3 (11)" — collapsed by default
  - "► Division 4 (11)" — collapsed by default
  - Click header to toggle expand/collapse
  - Division header colors match the accent scheme: Div 1 header in orange, Div 2 in cyan, Div 3/4 in muted
- Selected team: surface background (`#363650`) with left orange border
- Each row: team name only (division is implicit from the group)
- When filter is active: all groups expand, non-matching teams hidden
- Right-click team → context menu: "Become Manager" / "View in League Table"

### Team Header Bar

Always visible above tabs when a team is selected. Hidden when no team selected. Shows at a glance:
- Team name (white, bold, 14px)
- Division badge: colored pill/rounded-rect (orange bg + dark text for D1, cyan bg + dark text for D2, surface bg + muted text for D3/D4)
- Team value: green if positive (`+4357`), red if negative (`-48`)
- Budget tier: plain muted text
- "Become Manager" button: secondary style
- "Apply Changes" button: right-aligned, orange primary style

### Tabs

Four tabs below the team header:
1. **Roster** (default) — player table + actions
2. **Team Info** — name, division, value, budget edit fields
3. **League Stats** — points, goals, rank A/B, flags
4. **Hex Dump** — raw 100-byte hex viewer (dark terminal style)

Active tab: orange text + 2px orange bottom border, elevated background.
Inactive tabs: muted text, no border, deep background.

**Keyboard shortcuts:** Cmd+1 = Roster, Cmd+2 = Team Info, Cmd+3 = League Stats, Cmd+4 = Hex Dump.

### Tab: Roster

**Player table (Treeview):**

| Column | Width | Content |
|--------|-------|---------|
| # | 30px | Slot index (0–24), muted |
| ID | 60px | Player ID in cyan, or "—" muted for FFFF |
| Player Name | flex | Name from game disk (white), or "empty slot" italic dim for FFFF |

- Alternating row backgrounds: `#2A2A3C` / `#1E1E2E` (via Treeview tags)
- Selected row: subtle highlight with left orange border
- Table scrolls if needed (25 rows max, typically fits without scrolling)
- Click to select a row (for action buttons below)

**Inline editing flow:**
- Double-click a row (or select + press Enter, or right-click → "Edit ID"): the ID column cell becomes an editable Entry widget overlaid on the Treeview cell.
- Type new player ID (numeric). Press Enter to confirm, Escape to cancel.
- On confirm: the player name updates immediately via `game_disk.player_name(new_id)`. The Treeview row refreshes with the new ID and name. Changes are applied to the in-memory team record (same as current `apply_team_changes` but per-field).
- Invalid input (non-numeric, out of range): entry border flashes red, not applied.

**Right-click context menu on a roster row:**
- "Edit Player ID" — triggers inline edit
- "Remove Player" — sets slot to FFFF, row updates to empty
- "Copy Player ID" — copies the numeric ID to clipboard

**Action bar below table:**
- "Set Player ID" button (secondary) — applies to selected row, triggers inline edit
- "Remove Player" button (secondary, red text) — sets selected slot to FFFF
- Right-aligned: "N players / 25 slots" counter in muted text

### Tab: Team Info

Edit fields for:
- Team Name (text entry, full width)
- Division (combobox: "0 (Div 1)", "1 (Div 2)", "2 (Div 3)", "3 (Div 4)")
- Team Value (numeric entry, shows signed integer)
- Budget Tier (numeric entry)

Layout: 2-column grid, labels left (muted text), fields right (Entry with surface border, primary text). Fields use `#2A2A3C` background, `#363650` border, white text.

### Tab: League Stats

Six fields in a 3×2 grid: Points, Goals, Rank A, Rank B, Flag 1, Flag 2. Same field styling as Team Info.

### Tab: Hex Dump

Dark terminal view: `#1e1e1e` background, `#d4d4d4` text, Menlo 11px. Shows `+offset  hex bytes  ASCII` for the 100-byte team record. Read-only. Unchanged from current implementation.

### Status Bar

Full width at bottom. Two sections:
- Left: game disk info ("Game disk loaded: PlayerManagerITA.adf — 245 player names" in muted, or "Game disk error: …" in red, or "No game disk" in dim)
- Right: navigation breadcrumb ("START.sav → BAYERN MUNCHEN" in cyan when team selected, "START.sav" when only slot selected, empty when nothing selected)

### Keyboard Shortcuts

| Shortcut | Action |
|----------|--------|
| Cmd+O | Open ADF |
| Cmd+S | Save ADF |
| Cmd+Shift+S | Save ADF As… |
| Cmd+1 | Switch to Roster tab |
| Cmd+2 | Switch to Team Info tab |
| Cmd+3 | Switch to League Stats tab |
| Cmd+4 | Switch to Hex Dump tab |
| Up/Down | Navigate teams in sidebar (when sidebar has focus) |
| Enter | Begin inline edit on selected roster row |
| Escape | Cancel inline edit |
| Delete/Backspace | Remove player from selected roster slot |

## Tool Windows (Popups)

All Toplevel windows adopt the same theme. Specific changes per window:

### Shared Styling

- Window background: `#1E1E2E` (deep)
- All `ttk.LabelFrame` borders: `#363650`, header text in orange
- All `ttk.Entry` fields: bg `#2A2A3C`, fg `#FFFFFF`, border `#363650`, insert cursor white
- All `ttk.Button`: secondary style (bg `#363650`, fg `#C8C8D0`), primary buttons use orange bg + dark text
- All `ttk.Treeview`: bg `#1E1E2E`, fg `#C8C8D0`, heading bg `#2A2A3C`, heading fg `#888888`, selected row bg `#363650` with orange text. Alternating row tags: `oddrow` (`#2A2A3C`) and `evenrow` (`#1E1E2E`)
- All `tk.Text` (hex/code viewers): bg `#1e1e1e`, fg `#d4d4d4`, Menlo 11px
- All `ttk.Combobox`: same bg/fg as Entry, dropdown list matches theme
- All `ttk.Scrollbar`: trough `#1E1E2E`, thumb `#363650`
- Status bars in tool windows: same `#16162A` background, muted text

### Patch Composer

- Top bar: dark chrome bg (`#16162A`), "Open Game Disk ADF…" button orange if no disk loaded, secondary if loaded
- Patch list (Treeview): alternating rows, offset column in cyan, value column in white, description in muted. Copy-protection patches get a dim tag to de-emphasize them
- Quick Patches section: LabelFrame with orange header. Age spinbox uses themed Entry styling
- Custom Patch section: same field styling as main window Team Info tab
- Space indicator bar: render as a simple progress bar — filled portion in orange, empty in surface. Text shows "N/168 bytes used"
- "Preview ASM" button: secondary. "Write to Game Disk ADF" button: orange primary
- Delete patch button: red text, secondary bg

### League Tables

- Tab headers for each division: Div 1 tab in orange text, Div 2 in cyan, Div 3/4 in muted
- Table (Treeview): alternating rows. Promotion zone rows (top 2): row background tinted green — use `#1E3E2E` (dark green blend). Relegation zone rows (bottom 2): row background tinted red — use `#3E1E2E` (dark red blend)
- "Zone" column: "▲ Promotion" in green text, "▼ Relegation" in red text
- Team names in white, numeric columns in primary text

### Compare Saves

- Dropdowns (Combobox): themed to match
- Results text (tk.Text): dark terminal style
- Player transfer lines: player name in cyan, team names in white, arrow in muted
- Division change lines: "promoted" in green, "relegated" in red
- Budget delta: positive deltas in green, negative in red

### Tactics Viewer

- Surrounding frame: deep background
- File selector and controls: themed Combobox/buttons
- Zone selector: active zone button in orange, inactive in surface
- State toggle: "With ball" / "Without ball" buttons — active in cyan, inactive in surface
- Pitch canvas: stays `#2E7D32` green. Player dots keep their 10 distinct colors
- Legend: dark background strip below canvas
- "Save to Disk" button: orange primary

### Disassembler

- Navigation bar: deep chrome bg, Address entry themed, "Go" button orange, "← Back" secondary
- Quick Navigation buttons: orange pill-style (rounded, orange bg, dark text, small)
- Search section: field styling matches main window. "X-Ref" and "Find" buttons orange, "Find MUL/DIV" secondary
- Code view (tk.Text): stays as-is — `#1e1e1e` bg with syntax coloring already matching the palette (address blue, mnemonic yellow, hex green, comments green)
- Results view: same styling, xref results in cyan

## Implementation Approach

### Custom tkinter theming

tkinter + ttk allows full custom theming via `ttk.Style()`. The approach:

1. **Configure `ttk.Style` globally** at app startup — set colors for all widget types (TButton, TLabel, TFrame, TNotebook, Treeview, TEntry, TCombobox, TScrollbar, etc.) before any widgets are created
2. **Use `tk.Frame(bg=...)` for major containers** — ttk frames don't support direct bg color on all platforms; use tk.Frame where precise background control is needed (sidebar, team header bar, toolbar, status bar)
3. **Use `ttk.Notebook` for tabs** — native tab widget, style the tabs via `TNotebook` and `TNotebook.Tab` layout/configure
4. **Use `ttk.Treeview` for the roster table and teams list** — configure row colors via tags (`oddrow`, `evenrow`, `selected`)
5. **Team header bar**: custom `tk.Frame` with packed `tk.Label` and `tk.Button` widgets (not ttk — for precise bg/fg control)
6. **Inline editing overlay**: create a `ttk.Entry` widget, position it over the Treeview cell using `bbox()`, destroy on confirm/cancel

### Theme constants

Module-level dict at the top of the file (after existing constants):

```python
_THEME = {
    'bg_deep': '#1E1E2E',
    'bg_elevated': '#2A2A3C',
    'bg_surface': '#363650',
    'bg_chrome': '#16162A',
    'bg_toolbar': '#22223A',
    'accent_primary': '#F28C28',
    'accent_secondary': '#4FC3F7',
    'positive': '#44CC44',
    'negative': '#E57373',
    'text_primary': '#C8C8D0',
    'text_bright': '#FFFFFF',
    'text_muted': '#888888',
    'text_dim': '#555555',
    'font_main': ('Menlo', 11),
    'font_header': ('Menlo', 14, 'bold'),
    'font_section': ('Menlo', 10, 'bold'),
    'font_small': ('Menlo', 10),
    'font_button': ('Menlo', 10, 'bold'),
}
```

An `_apply_theme(root)` function configures all `ttk.Style` options using this dict. Called once in `main()` before creating the app.

### File structure

Keep single-file architecture. Added code:
- `_THEME` dict: after existing constants (~line 35)
- `_apply_theme(root)` function: before GUI section
- Rebuilt `PMSaveDiskToolApp._build_ui()`: replaces current method entirely
- Rebuilt `PMSaveDiskToolApp._build_menu()`: minor changes (same structure, add tab shortcuts)
- New `_build_roster_tab()`, `_build_team_info_tab()`, `_build_stats_tab()`, `_build_hex_tab()` helper methods
- Updated `_display_team()`: populates roster Treeview instead of 25 StringVars
- New `_start_inline_edit()`, `_confirm_inline_edit()`, `_cancel_inline_edit()` methods
- New `_filter_teams()` method for sidebar search
- Each Toplevel window `__init__` / `_build_ui` updated for themed widget construction

### Migration strategy

1. Add `_THEME` and `_apply_theme()` — no UI changes yet, just infrastructure
2. Rebuild `PMSaveDiskToolApp._build_ui()` from scratch — new sidebar, team header, notebook tabs, roster table
3. Update `_display_team()` and `apply_team_changes()` to work with the new widget structure (Treeview instead of StringVars for roster)
4. Add inline editing, context menus, keyboard shortcuts, empty states
5. Restyle each Toplevel window class — update widget constructors, add tags for Treeview rows
6. Test the full app

### What doesn't change

- Data layer classes (ADF, SaveFile, TeamRecord, GameDisk, TacticsFile, Disasm68k, etc.) — untouched
- All file I/O, parsing, decompression, and game-disk logic — untouched
- Window class count and overall structure (main + 6 Toplevels) — preserved
- Menu items and their commands — preserved

### What changes

- Main window layout: PanedWindow → fixed sidebar + team header + Notebook tabs
- Player ID grid (25 entry fields + StringVars) → Treeview table with inline editing and action buttons
- LabelFrame vertical scroll → Notebook tabs
- Default aqua/clam theme → custom dark theme via `_THEME` + `_apply_theme()`
- Status bar: single StringVar → two-section contextual bar
- Teams list: flat list → division-grouped tree with filter
- Team header: fields inside scrollable area → fixed bar above tabs
- All Toplevel windows: generic ttk styling → themed widgets matching main window
