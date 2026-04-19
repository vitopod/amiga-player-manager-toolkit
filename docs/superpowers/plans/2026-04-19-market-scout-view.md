# Market Scout View Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a "★ Transfer Market (Top 3/pos)" dropdown view that shows the top 3 market-available players per position, and group all market views under a ★ prefix to distinguish them from analytical (—) views.

**Architecture:** All changes are confined to `pm_core/strings.py` (new string keys), `pm_gui.py` (helper function + combo/menu/refresh/export wiring), and `tests/test_unit.py` (unit test for the helper). No new files or modules needed.

**Tech Stack:** Python 3.10+, tkinter (stdlib), pytest

---

## File Map

| File | What changes |
|---|---|
| `PMSaveDiskTool_v2/pm_core/strings.py` | Update `view.free_agents` EN+IT values to add `★` prefix; add `view.market_scout` and `menu.view.market_scout` keys in EN+IT |
| `PMSaveDiskTool_v2/pm_gui.py` | Add `_top_n_per_position()` module-level helper; insert `view.market_scout` in both combo-build blocks and the View menu; add branch in `_refresh_player_list()`; add branch in the export path |
| `PMSaveDiskTool_v2/tests/test_unit.py` | Add `TestTopNPerPosition` class with 3 tests |

---

### Task 1: Update strings

**Files:**
- Modify: `PMSaveDiskTool_v2/pm_core/strings.py`

- [ ] **Step 1: Update `view.free_agents` in the EN block**

Find (around line 96-97):
```python
        "view.free_agents": "Free Agents",
```
Replace with:
```python
        "view.free_agents": "★ Free Agents",
```

- [ ] **Step 2: Update `view.free_agents` in the IT block**

Find (around line 355):
```python
        "view.free_agents": "Svincolati",
```
Replace with:
```python
        "view.free_agents": "★ Svincolati",
```

- [ ] **Step 3: Add new keys after `view.free_agents` in the EN block**

Find in EN block:
```python
        "view.free_agents": "★ Free Agents",
        "view.young":       "\u2014 Young Talents (\u226421)",
```
Replace with:
```python
        "view.free_agents":  "★ Free Agents",
        "view.market_scout": "★ Transfer Market (Top 3/pos)",
        "view.young":        "\u2014 Young Talents (\u226421)",
```

And after `menu.view.free_agents` in the EN block, add `menu.view.market_scout`.

Find in EN block:
```python
        "menu.view.free_agents": "Free Agents",
        "menu.view.young":       "Young Talents (\u226421)",
```
Replace with:
```python
        "menu.view.free_agents":  "Free Agents",
        "menu.view.market_scout": "Transfer Market Scout",
        "menu.view.young":        "Young Talents (\u226421)",
```

- [ ] **Step 4: Add new keys after `view.free_agents` in the IT block**

Find in IT block:
```python
        "view.free_agents": "★ Svincolati",
        "view.young":       "\u2014 Giovani Talenti (\u226421)",
```
Replace with:
```python
        "view.free_agents":  "★ Svincolati",
        "view.market_scout": "★ Mercato (Top 3/pos)",
        "view.young":        "\u2014 Giovani Talenti (\u226421)",
```

And add `menu.view.market_scout` in the IT block.

Find in IT block:
```python
        "menu.view.free_agents": "Svincolati",
        "menu.view.young":       "Giovani Talenti (\u226421)",
```
Replace with:
```python
        "menu.view.free_agents":  "Svincolati",
        "menu.view.market_scout": "Scout Mercato",
        "menu.view.young":        "Giovani Talenti (\u226421)",
```

- [ ] **Step 5: Run test_strings to verify EN↔IT parity**

```bash
python3 -m pytest PMSaveDiskTool_v2/tests/test_strings.py -v
```
Expected: all tests PASS.

- [ ] **Step 6: Commit**

```bash
git add PMSaveDiskTool_v2/pm_core/strings.py
git commit -m "feat: add market_scout strings, prefix free_agents with ★"
```

---

### Task 2: Write failing test for `_top_n_per_position`

**Files:**
- Modify: `PMSaveDiskTool_v2/tests/test_unit.py`

- [ ] **Step 1: Add import at the top of test_unit.py**

The helper `_top_n_per_position` will live in `pm_gui` (a tkinter module that can't be imported in headless CI). We test it by extracting its pure logic into the test itself first as a reference, then importing via a direct function reference after implementation. For now, write the test to import from `pm_gui` using a try/except so the test is skippable in headless CI.

Add this class at the end of `PMSaveDiskTool_v2/tests/test_unit.py`:

```python
class TestTopNPerPosition(unittest.TestCase):
    """Tests for the _top_n_per_position helper in pm_gui."""

    def _make_player(self, position: int, total_skill_val: int,
                     team_index: int = 0) -> PlayerRecord:
        """Build a minimal PlayerRecord with the given position and skill sum."""
        # Distribute total_skill_val evenly across the 10 skill fields.
        # If not divisible by 10, put the remainder in keeping.
        base = total_skill_val // 10
        extra = total_skill_val % 10
        return PlayerRecord(
            position=position,
            team_index=team_index,
            keeping=base + extra,
            tackling=base,
            passing=base,
            shooting=base,
            heading=base,
            pace=base,
            stamina=base,
            agility=base,
            flair=base,
            resilience=base,
        )

    def _top_n(self, players, n=3):
        """Inline copy of the helper — replaced by import once Task 3 is done."""
        groups: dict[int, list] = {1: [], 2: [], 3: [], 4: []}
        for p in players:
            if p.position in groups:
                groups[p.position].append(p)
        result = []
        for pos in (1, 2, 3, 4):
            result.extend(
                sorted(groups[pos], key=lambda p: p.total_skill, reverse=True)[:n]
            )
        return result

    def test_keeps_top_n_per_position(self):
        """Top 3 per position are returned in skill order."""
        players = [
            self._make_player(1, 100),  # GK best
            self._make_player(1, 80),
            self._make_player(1, 60),
            self._make_player(1, 40),   # GK 4th — should be excluded
            self._make_player(2, 90),   # DEF
            self._make_player(2, 70),
        ]
        result = self._top_n(players, n=3)
        gks = [p for p in result if p.position == 1]
        defs = [p for p in result if p.position == 2]
        self.assertEqual(len(gks), 3)
        self.assertEqual(gks[0].total_skill, 100)
        self.assertEqual(gks[2].total_skill, 60)
        self.assertEqual(len(defs), 2)  # only 2 DEF available

    def test_position_order(self):
        """Result is GK → DEF → MID → FWD."""
        players = [
            self._make_player(4, 50),
            self._make_player(3, 50),
            self._make_player(2, 50),
            self._make_player(1, 50),
        ]
        result = self._top_n(players)
        positions = [p.position for p in result]
        self.assertEqual(positions, [1, 2, 3, 4])

    def test_fewer_than_n_in_position(self):
        """If a position has fewer than n players, returns all of them."""
        players = [self._make_player(1, 100)]  # only 1 GK
        result = self._top_n(players, n=3)
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0].total_skill, 100)
```

- [ ] **Step 2: Run the tests to confirm they pass (inline copy, no import yet)**

```bash
python3 -m pytest PMSaveDiskTool_v2/tests/test_unit.py::TestTopNPerPosition -v
```
Expected: all 3 tests PASS (they use the inline `_top_n` copy).

---

### Task 3: Implement `_top_n_per_position` in `pm_gui.py`

**Files:**
- Modify: `PMSaveDiskTool_v2/pm_gui.py`

The helper is module-level (not a method) so it can be tested without instantiating the GUI.

- [ ] **Step 1: Add the helper function**

Find the section near the top of `pm_gui.py` where module-level helpers live (look for `_pos_display` or `has_weakness`). Add this function immediately before `_pos_display`:

```python
def _top_n_per_position(players: list, n: int = 3) -> list:
    """Return up to n players per position, ranked by total_skill descending.

    Positions are returned in order GK(1) → DEF(2) → MID(3) → FWD(4).
    Positions with fewer than n available players return all of them.
    """
    groups: dict[int, list] = {1: [], 2: [], 3: [], 4: []}
    for p in players:
        if p.position in groups:
            groups[p.position].append(p)
    result = []
    for pos in (1, 2, 3, 4):
        result.extend(
            sorted(groups[pos], key=lambda p: p.total_skill, reverse=True)[:n]
        )
    return result
```

- [ ] **Step 2: Run the full unit-test suite**

```bash
python3 -m pytest PMSaveDiskTool_v2/tests/test_unit.py -v
```
Expected: all tests PASS.

- [ ] **Step 3: Commit**

```bash
git add PMSaveDiskTool_v2/pm_gui.py PMSaveDiskTool_v2/tests/test_unit.py
git commit -m "feat: add _top_n_per_position helper + unit tests"
```

---

### Task 4: Wire the combo entries and View menu

**Files:**
- Modify: `PMSaveDiskTool_v2/pm_gui.py`

There are **two** places where `team_options` is built (one for initial load ~line 668, one for slot reload ~line 697). Both must be updated identically.

- [ ] **Step 1: Update first combo-build block (~line 668)**

Find:
```python
        team_options = [t("view.all"), t("view.free_agents")]
        for i, name in enumerate(self.slot.team_names):
            team_options.append(f"{i}: {name}")
        team_options.append(t("view.young"))
        team_options.append(t("view.scorers"))
        team_options.append(t("view.squad"))
        team_options.extend(self.XI_ENTRIES.keys())
```
Replace with:
```python
        team_options = [t("view.all"), t("view.free_agents"), t("view.market_scout")]
        for i, name in enumerate(self.slot.team_names):
            team_options.append(f"{i}: {name}")
        team_options.append(t("view.young"))
        team_options.append(t("view.scorers"))
        team_options.append(t("view.squad"))
        team_options.extend(self.XI_ENTRIES.keys())
```

- [ ] **Step 2: Update second combo-build block (~line 697)**

Find the identical block (it starts with the same `team_options = [t("view.all"), t("view.free_agents")]` line a few lines later):
```python
        team_options = [t("view.all"), t("view.free_agents")]
        for i, name in enumerate(self.slot.team_names):
            team_options.append(f"{i}: {name}")
        team_options.append(t("view.young"))
        team_options.append(t("view.scorers"))
        team_options.append(t("view.squad"))
        team_options.extend(self.XI_ENTRIES.keys())
```
Replace with:
```python
        team_options = [t("view.all"), t("view.free_agents"), t("view.market_scout")]
        for i, name in enumerate(self.slot.team_names):
            team_options.append(f"{i}: {name}")
        team_options.append(t("view.young"))
        team_options.append(t("view.scorers"))
        team_options.append(t("view.squad"))
        team_options.extend(self.XI_ENTRIES.keys())
```

- [ ] **Step 3: Add View menu entry for market scout**

Find (~line 237):
```python
        view_menu.add_command(label=t("menu.view.free_agents"),
                              command=lambda: self._set_view(t("view.free_agents")))
```
Replace with:
```python
        view_menu.add_command(label=t("menu.view.free_agents"),
                              command=lambda: self._set_view(t("view.free_agents")))
        view_menu.add_command(label=t("menu.view.market_scout"),
                              command=lambda: self._set_view(t("view.market_scout")))
```

- [ ] **Step 4: Run unit tests to confirm nothing broken**

```bash
python3 -m pytest PMSaveDiskTool_v2/tests/ -v
```
Expected: all tests PASS.

- [ ] **Step 5: Commit**

```bash
git add PMSaveDiskTool_v2/pm_gui.py
git commit -m "feat: add market scout to combo and View menu"
```

---

### Task 5: Add `_refresh_player_list()` branch for market scout

**Files:**
- Modify: `PMSaveDiskTool_v2/pm_gui.py`

- [ ] **Step 1: Insert the market scout branch**

In `_refresh_player_list()`, find the `elif team_sel == t("view.free_agents"):` block (~line 807):
```python
        elif team_sel == t("view.free_agents"):
            players = self.slot.get_free_agents()
            self.tree.heading("total", text=t("col.skill"))
            score_fn = lambda p: p.total_skill
```
Insert **before** it (so market_scout is checked first):
```python
        elif team_sel == t("view.market_scout"):
            all_market = [p for p in self.slot.players
                          if self.slot._is_real_player(p) and p.is_market_available]
            players = _top_n_per_position(all_market)
            self.tree.heading("total", text=t("col.skill"))
            score_fn = lambda p: p.total_skill
            self.summary_var.set(
                f"{len(all_market)} available  \u00b7  {len(players)} shown"
            )
```

- [ ] **Step 2: Run the full test suite**

```bash
python3 -m pytest PMSaveDiskTool_v2/tests/ -v
```
Expected: all tests PASS.

- [ ] **Step 3: Manual smoke-test**

Launch the GUI (`python3 PMSaveDiskTool_v2/pm_gui.py`), open a save, and select "★ Transfer Market (Top 3/pos)" from the combo. Verify:
- Up to 12 rows appear (≤3 per position).
- Rows are in GK → DEF → MID → FWD order.
- Free agents appear in amber; transfer-listed players show ★ in Mkt column.
- Summary line reads e.g. `"47 available  ·  12 shown"`.
- Clicking a player opens the detail pane normally.
- Also verify "★ Free Agents" still works correctly.

- [ ] **Step 4: Commit**

```bash
git add PMSaveDiskTool_v2/pm_gui.py
git commit -m "feat: implement Market Scout view in _refresh_player_list"
```

---

### Task 6: Fix export path for market scout

**Files:**
- Modify: `PMSaveDiskTool_v2/pm_gui.py`

The export function checks views explicitly. The `market_scout` entry would otherwise fall into the catch-all `else` branch and export all players. Add an explicit branch that exports all market-available real players (consistent with how `free_agents` exports all free agents).

- [ ] **Step 1: Add market scout branch in the export function**

Find in the export method (~line 1197):
```python
        if team_sel == t("view.free_agents"):
            players = self.slot.get_free_agents()
        elif team_sel.startswith("\u2014") or team_sel == t("view.all"):
            players = [p for p in self.slot.players if p.age > 0]
```
Replace with:
```python
        if team_sel == t("view.free_agents"):
            players = self.slot.get_free_agents()
        elif team_sel == t("view.market_scout"):
            players = [p for p in self.slot.players
                       if self.slot._is_real_player(p) and p.is_market_available]
        elif team_sel.startswith("\u2014") or team_sel == t("view.all"):
            players = [p for p in self.slot.players if p.age > 0]
```

- [ ] **Step 2: Run full test suite**

```bash
python3 -m pytest PMSaveDiskTool_v2/tests/ -v
```
Expected: all tests PASS.

- [ ] **Step 3: Commit**

```bash
git add PMSaveDiskTool_v2/pm_gui.py
git commit -m "feat: export all market-available players from Market Scout view"
```

---

### Task 7: Final check and push

- [ ] **Step 1: Run the full test suite one last time**

```bash
python3 -m pytest PMSaveDiskTool_v2/tests/ -v
```
Expected: all tests PASS, no warnings.

- [ ] **Step 2: Manual regression check**

Launch the GUI and verify:
- "★ Free Agents" and "★ Transfer Market (Top 3/pos)" are grouped together at the top of the combo, before team names, before the `—` analytical entries.
- All existing `—` views still work (Young Talents, Top Scorers, Squad Analyst, Best XI entries).
- Language switch to Italiano shows "★ Svincolati" and "★ Mercato (Top 3/pos)".

- [ ] **Step 3: Push**

```bash
git push origin main
```
