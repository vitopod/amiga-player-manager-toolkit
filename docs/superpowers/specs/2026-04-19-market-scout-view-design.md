# Market Scout View — Design Spec

**Date:** 2026-04-19
**Status:** Approved

## Problem

When a key player gets injured you need to know quickly who is available on the
transfer market to replace them. The existing "Free Agents" view shows everyone
but provides no positional shortlist. The dropdown also mixes market and
analytical views without any visual distinction, making navigation harder as the
list grows.

## Solution

1. Add a new dropdown entry **"★ Transfer Market (Top 3/pos)"** showing the top 3
   market-available players per native PM position (GK / DEF / MID / FWD),
   ranked by `total_skill` descending — up to 12 rows total.
2. Rename the existing "Free Agents" entry to **"★ Free Agents"** to group it
   visually with other market views.
3. All analytical views (Young Talents, Top Scorers, Squad Analyst, Best XI
   entries) keep the `—` em-dash prefix.

The `★` prefix reuses the app's existing market badge, so the grouping reads
naturally without needing non-selectable separator rows.

## Navigation grouping — combo order

```
[team names …]
All Players / Tutti i Giocatori
★ Free Agents / ★ Svincolati            ← market group
★ Transfer Market (Top 3/pos) / ★ Mercato (Top 3/pos)
— Young Talents (≤21) / — Giovani Talenti   ← analysis group
— Top Scorers / — Capocannonieri
— Squad Analyst / — Analisi Squadre
— Top 11 (4-4-2) / — Migliore XI (4-4-2)
— Top 11 (4-3-3) / — Migliore XI (4-3-3)
— Young XI (≤21) / — XI Giovani
— Free-Agent XI / — XI Svincolati
```

## Scope

- GUI only. No CLI subcommand in this iteration.
- No new module or window — the existing player list tree is reused as-is.

## Data & Filtering (market scout view)

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
| Toolbar combo — market scout | `★ Transfer Market (Top 3/pos)` | `★ Mercato (Top 3/pos)` |
| Toolbar combo — free agents (renamed) | `★ Free Agents` | `★ Svincolati` |
| View menu — market scout | `Transfer Market Scout` | `Scout Mercato` |
| View menu — free agents | unchanged label | unchanged label |

Detection in `_refresh_player_list()`:
- Market views detected with `startswith("★")`.
- Analytical views detected with `startswith("\u2014")` (unchanged).
- The `view.free_agents` string value changes to `"★ Free Agents"` / `"★ Svincolati"`;
  all internal comparisons use `t("view.free_agents")` so no hardcoded strings break.

File → Export Players… already uses em-dash detection for analytical views; the
market scout export path is handled by the `startswith("★")` branch (same logic,
same export schema).

## Strings

Six changed/new keys in `pm_core/strings.py` (EN + IT blocks):

```
"view.free_agents"       → "★ Free Agents"                  / "★ Svincolati"          (value changed)
"view.market_scout"      → "★ Transfer Market (Top 3/pos)"  / "★ Mercato (Top 3/pos)" (new)
"menu.view.market_scout" → "Transfer Market Scout"           / "Scout Mercato"          (new)
```

(`menu.view.free_agents` label in the View menu is unchanged.)

## Files Changed

| File | Change |
|---|---|
| `pm_core/strings.py` | Update `view.free_agents` EN+IT values; add 4 new keys |
| `pm_gui.py` | `_top_n_per_position()` helper; reorder combo entries; View menu item for market scout; branch in `_refresh_player_list()` for `startswith("★")` |
| `tests/test_unit.py` | Unit test for `_top_n_per_position()`: correct N limit, position order, fewer-than-3 fallback |

`tests/test_strings.py` passes automatically once all keys are present in both
EN and IT blocks.

## Out of Scope

- CLI `market-scout` subcommand (future).
- Ranking by role-fit score from the Line-up Coach taxonomy (PM doesn't model sub-roles natively).
- Configurable N (hardcoded to 3).
