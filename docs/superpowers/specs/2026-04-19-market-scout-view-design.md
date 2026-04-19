# Market Scout View — Design Spec

**Date:** 2026-04-19
**Status:** Approved

## Problem

When a key player gets injured you need to know quickly who is available on the
transfer market to replace them. The existing "Free Agents" view shows everyone
but provides no positional shortlist.

## Solution

Add a new dropdown entry **"— Transfer Market (Top 3/pos)"** to the main player
list combo and the View menu. It shows the top 3 market-available players per
native PM position (GK / DEF / MID / FWD), ranked by `total_skill` descending —
up to 12 rows total, in position order.

## Scope

- GUI only. No CLI subcommand in this iteration.
- No new module or window — the existing player list tree is reused as-is.

## Data & Filtering

Selection predicate: `SaveSlot._is_real_player(p) and p.is_market_available`
(`is_market_available` = `is_free_agent OR is_transfer_listed`).

Grouping and ordering:
1. Group by `p.position` (1 GK, 2 DEF, 3 MID, 4 FWD).
2. Within each group, sort by `total_skill` descending.
3. Keep the top 3. If a position has fewer than 3 available players, show all of
   them (no padding or error).
4. Concatenate groups in order GK → DEF → MID → FWD.

A private helper `_top_n_per_position(players: list[PlayerRecord], n: int = 3)`
in `pm_gui.py` encapsulates this logic.

## Display

- Existing player-list tree, columns, and detail pane are unchanged.
- Free agents rendered in amber (existing `"free"` tag).
- Transfer-listed players show ★ in the Mkt column (existing behaviour).
- Summary line at the bottom of the tree: `"N available · M shown"` (where N is
  total market-available real players, M is the displayed count ≤ 12).

## Entry Points

| Surface | Label (EN) | Label (IT) |
|---|---|---|
| Toolbar combo | `— Transfer Market (Top 3/pos)` | `— Mercato (Top 3/pos)` |
| View menu | `Transfer Market Scout` | `Scout Mercato` |

Combo placement: immediately after the `"view.free_agents"` entry, before the
XI entries.

Detection in `_refresh_player_list()` uses the existing `startswith("\u2014")`
pattern — no structural change needed.

File → Export Players… works automatically via the same em-dash detection.

## Strings

Four new keys in `pm_core/strings.py` (EN + IT blocks):

```
"view.market_scout"      → "— Transfer Market (Top 3/pos)" / "— Mercato (Top 3/pos)"
"menu.view.market_scout" → "Transfer Market Scout"          / "Scout Mercato"
```

## Files Changed

| File | Change |
|---|---|
| `pm_core/strings.py` | 4 new string entries |
| `pm_gui.py` | `_top_n_per_position()` helper; combo entry; View menu item; branch in `_refresh_player_list()` |
| `tests/test_unit.py` | Unit test for `_top_n_per_position()`: correct N limit, position order, fewer-than-3 fallback |

`tests/test_strings.py` passes automatically once the keys are added to both EN
and IT blocks.

## Out of Scope

- CLI `market-scout` subcommand (future).
- Ranking by role-fit score from the Line-up Coach taxonomy (PM doesn't model sub-roles natively).
- Configurable N (hardcoded to 3).
