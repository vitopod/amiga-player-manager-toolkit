# Changelog

All notable changes to Player Manager Toolkit are recorded here.
The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and the project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [2.6.1] — 2026-04-19

### Fixed
- **Line-up Coach no longer excludes healthy players.** Byte 0x15 (previously labelled "Injury Weeks") was found to carry an unknown value unrelated to injury status — healthy players had non-zero values while injured ones had zero. The eligibility filter and fatigue score now ignore this byte. The "Include Injured" checkbox and `--include-injured` CLI flag have been removed as they were based on the same incorrect field. The Status tab label for byte 0x15 now reads "Byte 0x15" to reflect that its meaning is still unconfirmed.

## [2.6.0] — 2026-04-19

### Added
- **Transfer Market Scout view.** Select **★ Transfer Market (Top 3/pos)** from
  the View dropdown to see the top 3 market-available players (free agents or
  transfer-listed) per position (GK / DEF / MID / FWD), ranked by total skill.
  Up to 12 rows; the summary line shows how many market-available players exist
  in total versus how many are shown. File → Export Players… from this view
  exports all market-available players.

### Changed
- **View dropdown navigation grouped by purpose.** Market views (Free Agents,
  Transfer Market Scout) are now prefixed with **★**; analytical views (Young
  Talents, Top Scorers, Squad Analyst, Best XI entries) keep the **—** prefix.
  The two groups appear in that order in the dropdown.

### Fixed
- **Line-up Coach diagnostic on failure.** When a formation cannot be filled,
  the coach now shows the number of eligible (non-injured) players per position
  and exactly which positions are short, instead of a generic "Try Include
  injured or Allow cross-position" message.

## [2.5.1] — 2026-04-18

### Fixed
- Italian skill names corrected: "Stamina" → "Energia", "Resistenza" → "Ricupero".

## [2.5.0] — 2026-04-18

### Added
- **Italian language support (Italiano).** Selectable in Help ->
  Preferences -> Language. Takes effect on the next launch, exactly
  like the colour theme. All visible UI text is translated: menus
  (File/Modifica/Vista/Strumenti/Aiuto), skill names, position
  abbreviations (Port./Dif./Cen./Att.), tab labels
  (Dati/Abilita'/Stato/Stagione/Storia), column headers, toolbar
  labels, the Welcome dialog, the Line-up Coach, Career Tracker, and
  Compare Players windows. Help body text remains in English.
- `pm_core/strings.py` -- flat EN/IT string table with `set_language(lang)`
  and `t(key)` helpers; full Italian string coverage enforced by
  `tests/test_strings.py`.
- `"language"` preference key (default `"en"`); persisted under
  `~/.pmsavedisktool/preferences.json` alongside theme and font.

## [2.4.6] — 2026-04-18

### Changed
- **Compare Players now shows only the 9 officially-labelled PM skills.**
  The radar chart and the side-by-side skill bars used to include 10
  axes, the tenth being `flair` — our internal placeholder for byte
  0x0F, which PM does *not* label on the in-game Player Information
  card. Dropped it to keep Compare Players consistent with the
  skill-threshold warnings (2.4.4): pace, agility, stamina, resilience,
  aggression, passing, shooting, tackling, keeping. The status footer
  auto-scales accordingly ("leads on 6/9 skills"). The field is still
  named `flair` in code and is unchanged in the Skills tab, the Byte
  Workbench, and exports, where a stable identifier matters.

### Fixed
- **Compare Players "DONE" button is now readable.** The native
  `tk.Button` on macOS Aqua repaints itself in system colours
  regardless of the explicit `bg`/`fg` we set, which turned the DONE
  text effectively invisible against the green footer. Replaced with a
  clickable `tk.Label` — the same workaround already used for the
  APPLY / REVERT footer in the main window. Hover feedback preserved.

## [2.4.5] — 2026-04-18

### Changed
- **Renamed the project from "PMSaveDiskToolkit" to "Player Manager
  Toolkit".** This is now the official product name, shown in the
  window title bar, the About dialog (and its macOS app-menu entry),
  the `--version` output, the update-check opt-in prompt, and every
  user-facing doc (README, MANUAL, CHANGELOG header, NOTICE). The new
  name reflects what the toolkit actually does: the save-disk editor is
  only one of many surfaces now (Squad Analyst, Career Tracker, Byte
  Workbench, Line-up Coach, Compare Players, Tactic Editor, …).
- **Preserved** for clarity of attribution and code identity:
  **PMSaveDiskTool v1.2** by UltimateBinary — still credited by name as
  the original Windows tool we ported from; the "Windows PMSaveDiskTool
  PE32" references in `pm_core/names.py` (naming the binary the hash
  algorithm was reversed from); the `PMSaveDiskTool_v2/` and
  `PMSaveDiskTool_v1.2/` folder paths; and the `PMSaveDiskToolGUI`
  Python class name.

## [2.4.4] — 2026-04-18

### Changed
- **Skill-threshold warnings (⚠) now reference only officially-labelled
  PM skills across all four positions.** Goalkeepers and defenders were
  already clean (GK → keeping/agility/resilience, DEF → tackling/stamina/
  pace); midfielders and forwards used to list "flair" — our internal
  placeholder name for byte 0x0F, which is *not* one of the nine skills
  Player Manager labels on the in-game Player Information card. The full
  table is now:
  - **GK** → keeping / agility / resilience *(unchanged)*
  - **DEF** → tackling / stamina / pace *(unchanged)*
  - **MID** → passing / stamina / tackling *(was: passing/stamina/flair)*
  - **FWD** → shooting / pace / agility *(was: shooting/pace/flair)*

  The field is still called `flair` in code, lineup role weights,
  exports and the Byte Workbench (where a stable identifier matters more
  than a guess at the in-game meaning); it's just no longer surfaced in
  user-facing warnings. Updated MANUAL, README, and the in-app `?` help.
  New regression test `test_warning_skills_are_all_official_pm_labels`
  guards the invariant.

## [2.4.3] — 2026-04-18

### Added
- **Sortable player-list columns.** Every heading (ID, Name, Age, Pos,
  Team, Skill, ⚠, Mkt) is now clickable. Click to sort ascending, click
  again to flip to descending; the active column shows a ▲ / ▼ arrow.
  **Name** sorts by family name — the last whitespace-separated token,
  so "S.D. Giannini" sorts under **G**. Numeric columns sort
  numerically; ⚠ and ★ group flagged rows first. The active sort
  persists across View, Filter, and save-slot changes. Documented in
  MANUAL and the main-window `?` help.
- **Position-based skill-threshold warnings (⚠).** A new ⚠ column on
  the player list flags any player whose position-essential skills
  fall below 100 — GK needs keeping/agility/resilience, DEF needs
  tackling/stamina/pace, MID needs passing/stamina/flair, FWD needs
  shooting/pace/flair. The Status tab's new **Weakness** row spells
  out which skills tripped the threshold for the selected player
  ("⚠ pace 85, stamina 92"). Toggle on/off in Help → Preferences… —
  the setting applies live, no relaunch needed. This is a tactic-
  agnostic sanity check; tactic-aware warnings will ship once
  shirt→player mapping is reverse-engineered from the `.sav`.
- `pm_core.warnings` module exposes the reusable pieces
  (`POSITION_REQUIRED_SKILLS`, `DEFAULT_THRESHOLD`, `weak_skills`,
  `has_weakness`, `describe_weaknesses`). Fully tested.

### Fixed
- **Skills tab entries readable on every theme.** The skill-value
  entry boxes used to hardcode their dark-navy background, so on the
  light theme the foreground text resolved to the same shade as the
  background and values looked blank. Entries now track `PAL["field"]`
  and use a slightly bolder, larger font so they read clearly on both
  themes.

## [2.4.2] — 2026-04-18

### Added
- **Tactic Editor — shirt movement overlay.** Switching zones now draws
  a ghost ring at each shirt's position in a reference zone plus a
  dashed arrow to its current position, so you can see at a glance how
  the shape shifts between the two snapshots. A new **Compare to:**
  combobox defaults to `(previous zone)` — the overlay auto-follows the
  last zone you left — but you can pin a specific zone to walk through
  all 20 while keeping the reference fixed, or pick `(none)` to hide
  the overlay entirely. Arrows recede into the pitch in a muted sage
  grey and tuck their heads under the shirt outline for a clean read.
  A `movement from: <zone>` legend in the bottom-right makes the
  overlay self-explanatory. Documented in the MANUAL Tactic Editor
  section and the in-app `?` help.

## [2.4.1] — 2026-04-18

### Changed
- **Tactic Editor — landscape pitch.** Rendering now flips 90° CCW so
  the 660×440 canvas is wider than tall, saving vertical space. The
  `.tac` world coordinates stay portrait on disk; only the display
  rotates, so edits remain byte-identical to what the engine reads.
- **Tactic Editor — clearer description line.** The trailer parser now
  scans for the longest printable-ASCII run (instead of hardcoding an
  offset), quotes the result, and appends `…` when PM truncated the
  text mid-word in its fixed ~126-char slot. Missing descriptions now
  read `No in-game description stored` and distinguish `PM-edited`
  from stock Anco / KO2 template tactics. Help text explains PM's
  `<mids>-<forwards> <blurb>` convention — the leading `"2-4"` on a
  4-2-4 file is PM's own label, not a parser bug.

### Added
- **Tactic Editor — shift-click to switch zones.** Shift-click anywhere
  on the pitch jumps to whichever zone the click lands in. Overlapping
  zones (corners inside `areaN`, kickoff and goalkick too) resolve to
  the smallest match so the tighter zone wins.
- **MANUAL.md** — Tactic Editor GUI section and `edit-tactics` CLI
  section. The `show-tactics` section is updated to point at the new
  editor instead of calling the format un-reversed.

### Fixed
- **Tactic Editor — hidden Save / Revert buttons.** The footer sat
  below the visible window because the 660-pixel canvas pushed it off
  the bottom. The footer and description labels now pack before the
  canvas so tkinter reserves their space first; the default window
  height was also bumped.

## [2.4.0] — 2026-04-18

### Added
- **`.tac` tactic editor.** The `.tac` file format is now decoded:
  20 pitch-zone snapshots × 10 players × (x, y) 16-bit big-endian
  coordinates (800 bytes), plus a variable trailer (preserved byte-exact)
  that carries either an ASCII formation description — PM's 928-byte
  shape — or the stock Anco / KO2 per-formation metadata of the 980-byte
  shape. Shirt #1 (goalkeeper) is implicit and never stored. The layout
  was cross-checked against the Java editor at
  `github.com/ssenegas/tacticaleditor` and verified round-trip byte-exact
  on every `.tac` entry present on Save1_PM.adf (both 928- and 980-byte
  variants).
- **`pm_core.tactics`** — pure library with `parse_tac`, `serialize_tac`,
  `tactic_to_json`, `tactic_from_json`, and a `Tactic` dataclass keyed by
  zone name → shirt number → `(x, y)`.
- **Tools → Tactic Editor… (Cmd/Ctrl+K).** New window that lists every
  `.tac` on the loaded disk, lets you pick one, cycle through the 20
  pitch zones, and drag shirts #2–#11 to new target positions. The area
  the selected zone covers is highlighted on the pitch so you can see
  where each zone lives on the field. Save writes through the normal
  `.bak` flow; the 128/180-byte trailer is preserved byte-for-byte.
- **`pm_cli edit-tactics ADF --file NAME --dump | --import PATH`** —
  CLI round-trip for scripting. `--dump` emits human-editable JSON to
  stdout; `--import` reads JSON and writes back through the ADF with a
  sibling `.bak` created on first edit. Refuses to write if the imported
  tactic's total size doesn't match the on-disk entry.

### Notes
- The `.tac` file does **not** encode which 11 players are starting —
  that lives inside the `.sav` team record and is still un-reversed.
  The deferred "Line-up Coach → apply suggested XI to disk" work now
  needs a `.sav` capture diff rather than a `.tac` one. Until then, the
  Tactic Editor shipped here lets you reshape the zone geometry your
  team plays with, which is the other half of the tactical loop.

## [2.3.1] — 2026-04-18

### Changed
- **Compare Players — symmetric two-panel selector.** The selection
  row at the top of the Compare window is now two mirrored panels, one
  per player, separated by a ⇄ swap button. Each panel has its own
  Team and Player dropdowns plus a name / meta line in the player's
  team color (amber on the left, red on the right). Previously the
  window gave player A a passive read-only label on the left and hid
  player B's selectors in a single right-side strip — awkward once
  you'd opened the window, because picking the two players to compare
  needed two different interaction paths. Now both players work the
  same way. Right-click → **Send to Compare…** still pre-fills side A
  and additionally mirrors that team over to side B so choosing an
  opponent is one click away.

## [2.3.0] — 2026-04-18

### Changed
- **GUI module split, part two.** Completes the refactor started in
  2.2.14. The remaining pieces left in `pm_gui.py` — `WelcomeDialog`,
  the splash screen, and the preferences dialog — move into three
  dedicated modules:
  - `pm_gui_welcome.py` — `WelcomeDialog` (first-run screen). Now
    takes an `on_dismiss(keep_showing: bool)` callback instead of
    reaching back into `pm_gui._pref_update`, so the dialog no longer
    depends on the main module.
  - `pm_gui_splash.py` — `show_splash(root)` (was the private
    `_show_splash` at the bottom of `pm_gui.py`).
  - `pm_gui_preferences.py` — `open_preferences(parent, xi_entries)`
    (was the 140-line `_show_preferences` method). `XI_ENTRIES` is
    passed in to avoid a cycle back into `pm_gui`.
  `pm_gui.py` drops from 1658 to 1368 lines (−17% on top of 2.2.14's
  −44%; −67% cumulative from the original 2936 lines). Zero behaviour
  change; 239 tests still passing. There is now no single dialog or
  Toplevel that lives inside `pm_gui.py` — the main module is purely
  the `PMSaveDiskToolGUI` class plus `main()`.

## [2.2.15] — 2026-04-18

### Added
- **Find in Help… (cross-topic search for `?` content).** New
  `Help → Find in Help…` entry (`Cmd/Ctrl+?`) opens a search window
  that scans every in-app help topic (main window, Line-up Coach,
  Byte Workbench, …) from a single box. Live filtering as you type;
  results list shows `topic — matching line`. Enter opens the top hit,
  double-click opens any row — and the target `HelpDialog` pre-
  highlights every occurrence of the query and scrolls to the first.
  With an empty query the window lists every help topic as an index
  so users can browse without knowing which surface owns the term.
  Search lives in `pm_core.help_text.search`, the window in
  `pm_gui_help_search.HelpSearchWindow` — both independently testable.

## [2.2.14] — 2026-04-18

### Changed
- **GUI module split.** `pm_gui.py` grew past 2900 lines as Tools windows
  and alternative themes piled onto the main module. Extracted the
  standalone pieces into six sibling modules with zero behaviour change:
  - `pm_gui_theme.py` — palette (`PAL_RETRO` / `PAL_LIGHT` / `PAL`), font
    helpers (`_retro`, `set_use_system_font`), `set_theme`, `apply_theme`.
  - `pm_gui_help.py` — `HelpDialog` + `help_button` (`?` trigger).
  - `pm_gui_career.py` — `CareerTrackerWindow`.
  - `pm_gui_workbench.py` — `ByteWorkbenchWindow` + `BYTE_PRESETS`.
  - `pm_gui_lineup.py` — `LineupCoachWindow`.
  - `pm_gui_compare.py` — `PlayerCompareWindow`.
  `pm_gui.py` drops from 2936 to 1658 lines (−44%) and now contains just
  the main `PMSaveDiskToolGUI` class, the Welcome/Splash/Preferences
  dialogs, and `main()`. All save-disk byte handling, tests, and user-
  facing behaviour are unchanged. The remaining dialogs and the
  preferences pane were later pulled out in 2.3.0.

## [2.2.13] — 2026-04-18

### Added
- **Accessible light theme.** New `theme` preference under
  `Help → Preferences…` with two choices: **Retro** (default — the
  existing Amiga navy / amber / cyan palette) and **Light** (high-
  contrast accessible theme: off-white background, near-black text,
  muted blue / red / green accents). Takes effect on next launch.
  Splash and welcome dialogs keep their PM-title palette regardless.

### Fixed
- **APPLY / REVERT buttons unreadable after closing Preferences
  (macOS).** Both were `tk.Button` widgets with
  `highlightthickness=0`, which on macOS hands rendering to native
  Aqua and makes the buttons re-paint in system colours after focus
  returns from a modal Toplevel — the explicit `fg` then landed on a
  mismatched background and turned the text invisible. Replaced with
  clickable `tk.Label` widgets + click/hover bindings (same pattern
  used for the Welcome dialog's OK button since 2.2.10). Labels
  honour `bg`/`fg` on every platform.

## [2.2.12] — 2026-04-18

### Added
- **New Preferences: Defaults section.** `Help → Preferences…` now
  exposes three new personalisation toggles:
  - **Default view** — the View combo's selection after a save disk
    loads. Defaults to "(first team in save)" which matches the
    pre-2.2.12 behaviour, but can be set to All Players, Free Agents,
    Young Talents, Top Scorers, Squad Analyst, or any of the XI views.
  - **Default formation** — the Line-up Coach window now initialises
    its Formation combo with the preferred formation (4-4-2 / 4-3-3 /
    3-5-2) instead of the neutral "— Rank all".
  - **Use system font instead of retro Topaz** — accessibility toggle
    that swaps the bundled pixel font for Courier New throughout the
    GUI. Takes effect on next launch.
  Persisted via `pm_core.preferences`; schema-validated loader so old
  preferences files continue to load cleanly with the new keys filled
  in from defaults.

## [2.2.11] — 2026-04-18

### Changed
- **In-game English labels honoured across the detail panel.** The
  Season tab now shows `Dsp.Pts. This Yr` / `Dsp.Pts. Last Yr`
  (matching the dots used on the in-game Player Information screen)
  instead of the abbreviated `DspPts`.

### Added
- **Main-window `?` guide now explains every detail-panel field.**
  Previous help gave one-line tab summaries; the Detail panel section
  now walks through Core, Skills, Status, Season and Career one field
  at a time, using the same English labels as the in-game Player
  Information screen. Highlights include: Injury Weeks vs Injuries
  This Yr (current downtime vs season tally), Aggression (stored
  inverted on disk), position codes, team-index semantics, Morale
  numeric scale vs the in-game OK/Low/High label, and the Div1..4 /
  Int Years mapping to the in-game 1st / 2nd / 3rd / 4th / Int columns.

## [2.2.10] — 2026-04-18

### Added
- **First-run welcome screen.** On first launch the GUI now shows a
  Player-Manager-styled welcome dialog (teal / red / navy palette,
  Topaz font) with five quick-start cards: open save disk, open game
  disk, browse/edit/save, explore the Tools menu, and the in-app help
  pointer. A checkbox ("Show this at every launch", unticked by
  default) lets users keep the dialog on next launch; the toggle also
  lives in `Help → Preferences…` under "Show welcome screen".

## [2.2.9] — 2026-04-18

### Added
- **Preferences: remembered paths + splash toggle.** The GUI now
  persists user preferences at `~/.pmsavedisktool/preferences.json`.
  New toggles in `Help → Preferences…`:
  - Show splash screen (default on, matching previous behaviour).
  - Auto-open last save disk at launch (default off).
  - Auto-open last game disk at launch (default off).
  Paths are always recorded after a successful open (regardless of the
  auto-open toggles), so the file-open dialog now seeds `initialdir`
  from the last-used folder — less clicking on every relaunch.
  Persistence layer lives in the new `pm_core.preferences` module
  (pure Python, atomic writes, round-trip unit-tested).

## [2.2.8] — 2026-04-17

### Added
- **In-app help popovers** — a small `?` button is now wired into three
  surfaces that open a styled help dialog. The **main window** toolbar
  (next to SAVE / VIEW) gets a comprehensive guide to save slots, every
  VIEW entry (regular teams, All Players, Free Agents, Young Talents,
  Top Scorers, Squad Analyst, Top 11 / Young XI / Free-Agent XI),
  the Filter field, player-list columns, the ★ market marker, and the
  detail panel tabs. The **Line-up Coach** and **Byte Workbench**
  windows each get their own scoped help (with per-tab guidance for
  Byte Workbench's Raw View / Histogram / Diff). Text lives in
  `pm_core.help_text.HELP`, rendered by a shared `HelpDialog` class.

## [2.2.7] — 2026-04-17

### Added
- **Line-up Coach bench (2 reserves)** — `assemble_matchday_squad()` in
  `pm_core.lineup` returns the starting XI plus a short bench. Default:
  one backup goalkeeper (when available) plus the best remaining
  outfielder by total skill. Bench size is configurable; the backup-GK
  preference can be disabled. Reserves are surfaced in both the GUI
  Line-up Coach window (below the XI, under a `— Reserves —` header)
  and the `suggest-xi` CLI via a new `--reserves N` flag (default 2,
  set to `0` to skip).
- **`show-tactics` CLI subcommand** — hex-dumps the `.tac` tactic files
  stored on every save disk (`4-4-2.tac`, `4-3-3.tac`, `5-3-2.tac`,
  `4-2-4.tac`, plus per-save variants), with a `--diff OTHER_ADF` mode
  that reports byte-level differences between the same tactic in two
  disks. Discovery aid for ongoing reverse-engineering of how PM
  encodes the selected XI inside those files.

## [2.2.6] — 2026-04-17

### Fixed
- **Identity header** (PLAYER# / NAME / SEED above the tabs) used
  `fg_dim` labels that were almost invisible on the mid-navy band.
  Labels are now `fg_label` retro bold 9 pt; values bumped to retro
  bold 12 pt so ID, name and seed stand out.
- **Core / Status / Season / Career tabs** relied on the ttk default
  label styling, which rendered as faint small text. Rebuilt the
  field helper to use `tk.Label` / `tk.Entry` with explicit amber
  `fg_data` at retro bold 10 pt and a navy entry field, matching the
  Skills tab treatment.

## [2.2.5] — 2026-04-17

### Fixed
- **Skills tab** labels were in dim blue (`fg_label`) at 8 pt, making
  STAMINA / PACE / AGGRESSION / … nearly invisible against the navy
  background. Brought them in line with the other detail tabs:
  amber `fg_data` at 10 pt bold.
- **Notebook tabs** (Core / Skills / Status / Season / Career):
  unselected tabs used `fg_dim` (#445588) on `bg_mid` (#111188) —
  basically unreadable. Unselected is now `fg_label`; the selected
  tab is now amber instead of white, matching PM's in-game convention
  for highlighted text.
- **Compare Players** window was riddled with low-contrast text:
  PLAYER A / B / TEAM / PLAYER headers, the meta line, the radar
  axis labels, the skill-bar middle labels, and losing values were
  all brightened and enlarged. Bar row height, value font, and the
  window width were bumped so the new labels fit.
- **APPLY / REVERT / DONE** buttons rendered as green-on-green on
  macOS (Aqua silently drops `bg` on native buttons). Switched the
  foreground to white, added `highlightbackground` so macOS actually
  paints the green, and replaced REVERT's dim grey with bold amber.

## [2.2.4] — 2026-04-17

### Added
- **Amiga-era Topaz font** now ships in `PMSaveDiskTool_v2/assets/` and is
  used for the main title band, Update-available banner, ttk Notebook
  tabs, Treeview column headings, and the Compare Players title —
  bringing the GUI's chrome closer to Player Manager's in-game look.
  Player-list rows, entry fields, and small labels stay on Courier New
  for legibility.
- `pm_core.fonts` registers the bundled TTF at process scope using
  `CTFontManagerRegisterFontsForURL` on macOS, `AddFontResourceEx` on
  Windows, and `~/.local/share/fonts/` + `fc-cache` on Linux. Silent
  fallback to Courier New when registration fails — zero new
  dependencies. Nothing is installed system-wide on macOS or Windows.
- `assets/NOTICE.md` documents the CC BY-NC-SA 3.0 license that applies
  to the bundled Topaz file (commercial redistributors should remove the
  `.ttf`; the GUI degrades gracefully).

### Credits
- **Topaz** font: TrueType rendition © 2009 dMG of Trueschool and
  Divine Stylers, sourced from https://github.com/rewtnull/amigafonts.

## [2.2.3] — 2026-04-17

### Added
- **Automatic daily update check (opt-in).** First launch asks once
  whether the toolkit may check GitHub once a day for new releases.
  Subsequent launches run the check in a background thread (never blocks
  startup), throttled by a 24 h cache. When a newer release is found, a
  small amber *“Update available: vX.Y.Z ▸”* banner appears next to the
  title bar; clicking it opens the release page.
- **Help → Preferences…** — one checkbox to toggle the automatic check
  on or off without touching any files.
- State persists in `~/.pmsavedisktool/update_check.json` (next to
  `recent.json`), so the opt-in choice, cache timestamp, and last-seen
  release all survive reinstalling or upgrading the toolkit. A test
  pins `STATE_DIR` under the home directory to prevent a future
  refactor from accidentally moving it into the source tree.

### Changed
- Help → Check for Updates… now shares the same module as the automatic
  path, so both update the banner and the cache in one place.

### Tests
- 24 new unit tests covering version parsing, newer-than logic, cache
  windowing, state file round-trip / malformed JSON / partial JSON, the
  home-directory invariant, and the network error paths for
  `fetch_latest`.

## [2.2.2] — 2026-04-17

### Added
- **Help → Check for Updates…** — on-demand check against the GitHub
  Releases API. Compares the latest `tag_name` to the running version and
  either confirms you're up to date or offers to open the release page in
  your browser. Uses `urllib.request` only (zero new dependencies) with a
  5-second timeout; does nothing automatically on launch.

## [2.2.1] — 2026-04-17

### Fixed
- **Season & career fields were misaligned by one byte.** Everything from
  offset `0x1B` onwards in the 42-byte player record was read one byte too
  early, so (for example) *Matches Last Year* surfaced as *Div1 Years*,
  *Contract Years* surfaced as an unidentified "last_byte", and every
  other season/career stat was off by one slot. Verified against an
  in-game career screen (Galassi, HURGADA: matches_last=5, div3=4, div4=1,
  contract=3 all now match). The real layout is: reserved2 at `0x1B`
  (zero for 1033/1035 real players), season stats at `0x1C..0x23`, career
  years div1..4 + international at `0x24..0x28`, and `contract_years`
  (1..5) at `0x29`.
- **Aggression displayed the raw on-disk byte instead of the in-game
  value.** The stat is stored *inverted* — raw disk byte = 200 − displayed.
  A "calm" player (in-game aggression 28) was showing as 172 throughout
  the GUI, CLI, Compare Players, Line-up Coach card-risk heuristic, and
  CSV/JSON exports. `parse_player` / `serialize_player` now invert, so
  `PlayerRecord.aggression` holds the in-game value; round-trip
  serialization remains byte-identical.
- Applies equally to Italian and English/BETA save disks — both builds
  share the same 42-byte record format.

### Changed
- `PlayerRecord.last_byte` is gone; its byte (`0x29`) is now
  `contract_years`. `PlayerRecord.reserved2` (new) holds `0x1B`.
- CSV/JSON exports gain a `reserved2` column and drop `last_byte`; all
  season/career columns now carry correct values.

### Tests
- Round-trip (`test_roundtrip_all_players`, `test_roundtrip_full_adf`)
  still passes — byte-identical across parse → serialize.
- Renamed `test_last_byte_in_expected_range` → `test_contract_years_in_expected_range`.
- Added `test_reserved2_mostly_zero` documenting the 0x1B invariant.

### Known remaining mystery
- `injuries_last_year` (byte `0x1D`) for Galassi is `9` on disk but the
  game displays `3`. Possibly a weeks-vs-events or scaling difference on
  that single byte; unrelated to the alignment bug and worth a separate
  investigation.

## [2.1.2] — 2026-04-17

### Fixed
- **Wrong team rosters on saves after standings reshuffle.** From pm2.sav
  onward the team ordering inside each save slot shifts as teams move in
  the league standings, but the toolkit was resolving team names through
  `PM1.nam` — a static snapshot of the *initial* standings. This made
  players in later saves (e.g. pm6.sav, pm7.sav) display under the wrong
  team label and caused the entire roster for teams like HURGADA to look
  nothing like the in-game squad. `SaveSlot` now reads team names
  directly from each `.sav`'s 44 × 100-byte team records (NUL-terminated
  ASCII at sub-offset 68, same layout `start.dat` uses), matching the
  1-based `team_index` → record[N−1] mapping the game engine uses. Slot
  0 (the user's own team) still falls back to `PM1.nam[0]` when present.
- Documented that `player.team_index` is **1-based** against the save's
  team records (team_index=0 = user's own team, team_index=N → record N−1).

### Changed
- `SaveSlot.apply_team_name_fallback` is now a no-op whenever the save's
  own records populated that slot — which is the common case for both
  Italian and English save disks.

### Tests
- New regression tests: HURGADA moves between saves as standings shift;
  slot 0 falls back to `PM1.nam[0]` on Italian saves and to the
  placeholder on English saves without `PM1.nam`.

## [2.1.1] — 2026-04-17

### Added
- **Team-name fallback for English / BETA save disks.** English save
  disks don't ship `PM1.nam`, so team names previously showed as
  `"Team 0".."Team 43"` placeholders. When a game disk is loaded the
  toolkit now extracts real team names from `start.dat` on the game
  disk (44 × 100-byte team records; NUL-terminated name at sub-offset
  0x3C) and fills them in everywhere — roster, Squad Analyst, Best XI,
  Career Tracker, CSV/JSON export, Line-up Coach. Italian saves are
  unaffected: `PM1.nam` still wins.
- `GameDisk.team_names` (list of 44 strings, empty for unused slots) and
  `GameDisk.team_names_available` on any PM custom-file-table game disk
  where `start.dat` parses cleanly.
- `SaveSlot.apply_team_name_fallback(team_names)` — no-op when the save
  already had real names; returns `True` if anything changed.
- `SaveSlot.team_names_from_save` flag indicating whether names came
  from `PM1.nam` (True) or the placeholder path (False).
- Tests: 5 new (English start.dat extraction, malformed-disk fallback,
  save-slot fallback applied + no-op when PM1.nam present).

### Changed
- CLI `_load_game_disk` now takes an optional `slot` argument and
  applies the team-name fallback automatically when it runs. The GUI
  applies it in both directions (save-then-game or game-then-save).

## [2.1.0] — 2026-04-17

### Added
- **English game disk support (BETA).** The game-disk loader now accepts
  English (Anco 1990) disks in addition to the Italian build. 183 English
  surnames are extracted by anchor-scan on `Adams\0Adcock\0Addison\0
  Aldridge\0Alexander\0` out of a PM-custom-file-table disk; the Italian
  initials charsets (ADJR / CEGMS / BFHILNTW / O) are reused. Surnames
  and initials verified against a real in-game roster screen on
  2026-04-17. BETA because the full seed → displayed-name mapping is not
  yet locked against a known seed; individual resolutions could in
  principle drift.
- `GameDisk.build`, `GameDisk.names_available`, `GameDisk.is_beta`
  exposed so callers can adapt their UI. GUI shows an amber BETA pill
  and a one-time warning dialog for BETA builds; CLI prints a stderr
  `Note:` on BETA loads.
- The loader is deliberately lenient: any disk that looks PM-shaped is
  accepted. Unknown builds load with `surnames=[]` so save editing still
  works; names stay blank rather than erroring.
- Tests: 8 new tests in `TestEnglishGameDiskBeta`
  (`tests/test_names.py`), gated on `PM_EN_GAME_ADF`.

## [2.0.0] — 2026-04-16

### Added
- **Line-up Coach (BETA)** — Tools → Line-up Coach (BETA)… (accelerator
  Cmd/Ctrl+L). Suggests a starting XI for a team or the whole championship.
  Scores every (player, role) pair over a 12-role taxonomy (GK / CB·FB·SW
  / DM·CM·AM·WM / POA·TGT·WNG·DLF), assembles the best XI via global-greedy
  assignment, and ranks the three supported formations (4-4-2 / 4-3-3 /
  3-5-2) by a composite of skill, role fit, morale, fatigue, card-risk and
  form. Also flags players whose best-fit role lies **outside** their
  nominal position — useful for squad rotation experiments.
  BETA: scoring is a modern football-management heuristic, **not** a
  reconstruction of PM's match-engine weights. Treat output as "suggested,"
  not "optimal."
- **CLI** `suggest-xi` — same engine on the command line. Ranks formations,
  prints the recommended XI with role tags and fit percentages, and lists
  reassignment suggestions with a configurable gap threshold. `--team`,
  `--formation`, `--allow-cross-position`, `--include-injured`, `--weights
  KEY=VAL…`, `--reassign-threshold`, `--reassign-limit`.
- **`pm_core.lineup`** — pure library module (zero external deps). Exposes
  `ROLES`, `FORMATION_ROLES`, `role_fit`, `best_role`, `assemble_xi`,
  `score_xi`, `suggest_reassignments`, `rank_formations`, plus the
  composite-weight defaults and result dataclasses. 33 unit tests pin
  down the role maths, taxonomy consistency (FORMATION_ROLES must match
  `pm_core.save.FORMATIONS` at the position-count level), XI-assembly
  invariants, and reassignment flagging.

## [1.1.0] — 2026-04-16

### Added
- **Byte Workbench** — Tools → Byte Workbench… (accelerator Cmd/Ctrl+B). A
  reverse-engineering UI for the 42-byte player record with three tabs:
  - **Raw View** — hex / decimal / binary dump of the selected player, each
    byte annotated with the field it belongs to and any known invariants.
  - **Histogram** — value distribution at any offset, optionally masked to
    a single bit. Preset filters (real / free agents / transfer-listed /
    by position / young / veteran / contracted) narrow the input set.
  - **Diff** — picks two player sets by preset filter and ranks the bits
    whose probability of being set differs most between them. Reproduces
    the manual process that originally cracked `mystery3 bit 0x80`, now as
    a push-button tool for cracking the remaining unknowns (`mystery3`
    lower 7 bits, `last_byte` skew).
- **CLI** `byte-stats` — histogram a byte/bit across a preset set, e.g.
  `byte-stats … --offset 0x1A --mask 0x80 --filter real`.
- **CLI** `byte-diff` — rank the top-N discriminative bits between two
  preset sets, e.g. `byte-diff … --set-a transfer-listed --set-b not-transfer-listed`.
- **`pm_core.workbench`** — pure analysis module: `byte_histogram`,
  `bit_probability`, `diff_sets`, `query`. Operates on iterables of
  `PlayerRecord`; no `SaveSlot` dependency. 26 unit tests.
- **`pm_core.player.FIELD_LAYOUT`** and **`field_at_offset(offset)`** — the
  single source of truth mapping each of the 42 bytes to its field, size,
  and note. Used by the workbench UI and CLI to label every offset.

## [1.0.0] — 2026-04-16

### Added
- **Reorganised menu bar** — File / Edit / View / Tools / Help with
  proper accelerators. File: Open Save Disk…, Open Game Disk…, Open
  Recent ▸, Save, Save As…, Export Players…, Quit. Edit: Apply
  Changes, Revert Player, Find Player…. View: All Players, Free
  Agents, Young Talents, Top Scorers, Squad Analyst, Best XI ▸. Tools:
  Career Tracker…. All actions are keyboard-reachable on macOS (Cmd)
  and Windows/Linux (Ctrl).
- **macOS native menu conventions** — About appears in the apple menu,
  Cmd+Q routes through the same dirty-state guard as WM_DELETE_WINDOW.
- **Detail panel refactored into tabs** — Core · Skills · Status ·
  Season · Career, with an always-visible identity header (Player #,
  Name, Seed) above and a sticky footer below (Apply Changes / Revert).
  No more long scrolling form; Apply is always in view.
- **Dirty-state tracking** — window title shows the open file name,
  with a "•" marker while unsaved edits are pending. Quitting,
  closing the window, or opening a different ADF prompts to save.
- **File → Open Recent** — last five save disks, persisted to
  `~/.pmsavedisktool/recent.json`.
- **Polished About dialog** — versioned header, attribution, clickable
  GitHub and MIT License links.
- **Status bar split** — left: transient status messages; right:
  persistent game-disk indicator.
- Search-entry focus via Ctrl/Cmd+F; Esc clears the filter when the
  filter entry has focus, otherwise reverts the current player.

### Changed
- **Toolbar slimmed** — Open / Load Game / Save Changes buttons
  removed (all in File menu with accelerators). Team dropdown
  relabeled **View** since it holds both teams and analytical views.
- **Renamed labels** — "Open Game ADF (for names)" →
  "Open Game Disk"; "Save ADF" → "Save"; "Save ADF As…" → "Save As…".

## [0.99] — 2026-04-16

### Added
- **Squad Analyst in the GUI** — "— Squad Analyst (all teams)" entry in the
  team dropdown, reusing the tree with repurposed column headings (Team, Age,
  Size, GK·DEF·MID·FWD, AvgSkill, Mkt). Squad rows are non-selectable for
  editing.
- **Per-team Squad Summary label** above the roster whenever a specific team
  is selected — `"17 players · avg 25.2y · skill 1238 · 2 on market"` — so
  the roster view and the composition snapshot coexist.
- **Career Tracker window** under a new Tools menu — diff any two save slots
  on the current ADF or bring in a second ADF via "Load side-B ADF". Output
  columns mirror the CLI (id, name, age A/B, skill A/B, Δ, team A/B), with a
  "Team changes only" filter.
- **File → Export Players...** — export the current view (all / free agents /
  team) as CSV or JSON from the GUI. Uses the same schema as the CLI
  `export-players` subcommand via the new `pm_core.save.player_to_row` helper.
- **Live player filter** Entry above the tree (filter by id/name/team/position).
- CLI smoke tests for `squad-analyst` and `career-tracker`
  (`tests/test_cli.py`, now 19 tests).
- Unit tests for `SaveSlot.squad_summary`, `SaveSlot.all_squad_summaries`,
  and `SaveSlot.diff_players` (`tests/test_read_save.py::TestSquadSummary`,
  `TestDiffPlayers`).
- `MANUAL.md` sections for `squad-analyst`, `career-tracker`,
  `export-players`, GUI Squad Analyst / filter / Tools menu / Export,
  automatic `.bak` on first write, the `--version` flag, and `python -m`
  entry points.

### Changed
- `pm_core.save.player_to_row` is the single source of truth for the export
  row shape; `pm_cli` and the GUI both call it. (Previously duplicated as a
  private helper in `pm_cli`.)

### Fixed
- 0.98 shipped the Squad Analyst CLI but neither a GUI entry nor updated
  READMEs listing the feature. 0.99 closes that gap and adds Career Tracker
  and Export parity between CLI and GUI.

## [0.98] — 2026-04-16

### Added
- `export-players` CLI subcommand — dump the player database as CSV or JSON,
  with optional team/free-agent filters and game-ADF name resolution.
- `squad-analyst` CLI subcommand — per-team composition breakdown
  (size, counts by position, average age and skill, youngest/oldest/best,
  players on the market). `--team N` drills into a single team.
- `career-tracker` CLI subcommand — diff two save slots (same ADF or
  different ADFs) to surface skill/age/team changes per player.
  `--sort {skill,id,changes}`, `--limit N`, `--team-changes-only` for
  zeroing in on the interesting records.
- `best-xi --market-only` — consistent with `young-talents` and `highlights`.
- `python -m PMSaveDiskTool_v2.pm_cli` and `python -m pm_core` entry points.
- Automatic `.bak` creation on first write. The CLI `edit-player` and the
  GUI "Save Changes" action both create a sibling `<file>.adf.bak` the
  first time they write to a loaded ADF; subsequent writes leave the
  original backup untouched so the first-known-good state is recoverable.
- Live player filter box in the GUI — narrow the list by id, name,
  team, or position as you type.
- GitHub Actions CI running the ADF-independent tests on Python 3.10,
  3.11, and 3.12 across Linux, macOS, and Windows.
- `tests/test_unit.py` (18 tests), `tests/test_names.py` (15 tests,
  4 require a game ADF), `tests/test_cli.py` (14 subprocess smoke
  tests), and a new `TestUnknownFieldObservations` in
  `tests/test_read_save.py` that locks in the observed invariants for
  `reserved`, `mystery3`, and `last_byte`. Total test count: 79.

### Changed
- `PlayerRecord.reserved`, `PlayerRecord.mystery3`, and
  `PlayerRecord.last_byte` are now documented with empirical findings
  from Save1_PM (1031 real players): `reserved` is always 0;
  `mystery3` bit 5 is never set; `last_byte` is always in 1..5.
  The bit-level analysis of `mystery3` (value 19 → free agents, value
  18 → veterans) and the skill/age skew of `last_byte` are recorded
  inline for future reverse engineering.
- Documented Python 3.10 as the minimum supported version (the codebase
  already used PEP 604 `X | None` annotations and PEP 585 generics).

## [0.97] — 2026-04-16

### Added
- **Top 11 of the Championship** — pick the best starting XI in a chosen
  formation (4-4-2, 4-3-3, 3-5-2). CLI subcommand `best-xi`; GUI team
  dropdown entries "— Top 11 (4-4-2)", "— Top 11 (4-3-3)", "— Young XI
  (≤21)", "— Free-Agent XI". Supports an optional per-team cap (free
  agents exempt) and filters (young, veteran, free-agent, market).
- `is_transfer_listed` player property (mystery3 bit 0x80) — identified
  empirically by byte-diffing records of players known to be on the
  in-game LISTA TRASFERIMENTI. 255 matches DB-wide with a realistic
  position/division/age distribution.
- `--version` flag on the CLI.
- Version string in the GUI window title.

### Changed
- `PlayerRecord.is_market_available` is now `is_free_agent or
  is_transfer_listed` (union of free agency and the transfer-list flag).
  Previously used a `transfer_weeks > 0` heuristic that produced false
  positives (e.g. A. Attrice was starred without being on LISTA
  TRASFERIMENTI in-game).
- Renamed `transfer_weeks` → `weeks_since_transfer`. The field is a
  post-transfer cooldown counter, not a "listed for sale" flag.

### Fixed
- "Young Talents" and "Championship Highlights" no longer include garbage
  sentinel records from the tail of the player database.

## [Pre-0.97]

- Ground-up cross-platform rewrite of
  [PMSaveDiskTool v1.2](http://www.ultimatebinary.com) by UltimateBinary
  for Mac, Linux, and Windows.
- ADF save-disk reader/writer with byte-for-byte round trip compatibility.
- tkinter GUI and argparse CLI.
- Player name generation from the 4-byte RNG seed, using surnames
  decompressed from the DEFAJAM-packed game executable.
- Young Talents view (≤21 by skill) and Championship Highlights
  (top scorers per division).
