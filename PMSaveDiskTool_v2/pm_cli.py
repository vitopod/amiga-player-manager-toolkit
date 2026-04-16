#!/usr/bin/env python3
"""Command-line interface for PMSaveDiskTool v2.

Usage:
    python pm_cli.py list-saves DISK.adf
    python pm_cli.py list-players DISK.adf --save pm1.sav [--team 0]
    python pm_cli.py show-player DISK.adf --save pm1.sav --id 42
    python pm_cli.py edit-player DISK.adf --save pm1.sav --id 42 --age 20 --pace 180
"""

import argparse
import csv
import dataclasses
import json
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from pm_core import __version__
from pm_core.adf import ADF, ensure_backup
from pm_core.save import SaveSlot, FORMATIONS
from pm_core.player import SKILL_NAMES, POSITION_NAMES, PlayerRecord
from pm_core.names import GameDisk


XI_FILTERS = {
    "young": lambda p: p.age <= 21,
    "veteran": lambda p: p.age >= 30,
    "free-agent": lambda p: p.is_free_agent,
    "market": lambda p: p.is_market_available,
}


def _load_game_disk(path):
    if not path:
        return None
    try:
        return GameDisk.load(path)
    except Exception as e:
        print(f"Warning: could not load game ADF: {e}", file=sys.stderr)
        return None


def cmd_list_saves(args):
    adf = ADF.load(args.adf)
    saves = adf.list_saves()
    if not saves:
        print("No save files found.")
        return
    print(f"{'Save File':<15} {'Offset':>8} {'Size':>6}")
    print("-" * 32)
    for entry in saves:
        print(f"{entry.name:<15} 0x{entry.byte_offset:06x} {entry.size:>6}")


def cmd_list_players(args):
    adf = ADF.load(args.adf)
    slot = SaveSlot(adf, args.save)
    gd = _load_game_disk(getattr(args, 'game_adf', None))

    if args.team is not None:
        players = slot.get_players_by_team(args.team)
        header = f"Team {args.team}: {slot.get_team_name(args.team)}"
    elif args.free_agents:
        players = slot.get_free_agents()
        header = "Free Agents"
    else:
        players = [p for p in slot.players if p.age > 0]
        header = "All Players"

    print(f"{header} ({len(players)} players)")
    if gd:
        print(f"{'ID':>5} {'Name':<18} {'Age':>4} {'Pos':>4} {'Team':<16} "
              f"{'Sta':>4} {'Res':>4} {'Pac':>4} {'Agi':>4} {'Agg':>4} "
              f"{'Fla':>4} {'Pas':>4} {'Sho':>4} {'Tac':>4} {'Kee':>4} {'Tot':>5}")
        print("-" * 115)
        for p in players:
            team = slot.get_team_name(p.team_index)
            name = gd.player_full_name(p.rng_seed) if p.rng_seed else ""
            print(f"{p.player_id:>5} {name:<18} {p.age:>4} {p.position_name:>4} {team:<16} "
                  f"{p.stamina:>4} {p.resilience:>4} {p.pace:>4} {p.agility:>4} "
                  f"{p.aggression:>4} {p.flair:>4} {p.passing:>4} {p.shooting:>4} "
                  f"{p.tackling:>4} {p.keeping:>4} {p.total_skill:>5}")
    else:
        print(f"{'ID':>5} {'Age':>4} {'Pos':>4} {'Team':<16} "
              f"{'Ht':>3} {'Wt':>3} {'Sta':>4} {'Res':>4} {'Pac':>4} "
              f"{'Agi':>4} {'Agg':>4} {'Fla':>4} {'Pas':>4} {'Sho':>4} "
              f"{'Tac':>4} {'Kee':>4} {'Tot':>5}")
        print("-" * 105)
        for p in players:
            team = slot.get_team_name(p.team_index)
            print(f"{p.player_id:>5} {p.age:>4} {p.position_name:>4} {team:<16} "
                  f"{p.height:>3} {p.weight:>3} {p.stamina:>4} {p.resilience:>4} "
                  f"{p.pace:>4} {p.agility:>4} {p.aggression:>4} {p.flair:>4} "
                  f"{p.passing:>4} {p.shooting:>4} {p.tackling:>4} {p.keeping:>4} "
                  f"{p.total_skill:>5}")


def cmd_show_player(args):
    adf = ADF.load(args.adf)
    slot = SaveSlot(adf, args.save)
    p = slot.get_player(args.id)
    team = slot.get_team_name(p.team_index)

    print(f"Player #{p.player_id}")
    print(f"  RNG Seed:       0x{p.rng_seed:08x}")
    print(f"  Age:            {p.age}")
    print(f"  Position:       {p.position_name} ({p.position})")
    print(f"  Division:       {p.division}")
    print(f"  Team:           {team} ({p.team_index})")
    print(f"  Height:         {p.height} cm")
    print(f"  Weight:         {p.weight} kg")
    print()
    print("  Skills:")
    for name in SKILL_NAMES:
        val = getattr(p, name)
        bar = "#" * (val // 5)
        print(f"    {name.capitalize():<12} {val:>3}  {bar}")
    print(f"    {'Total':<12} {p.total_skill:>4}")
    print()
    print(f"  Injury Weeks:        {p.injury_weeks}")
    print(f"  Disciplinary:        {p.disciplinary}")
    print(f"  Morale:              {p.morale}")
    print(f"  Value:               {p.value}")
    print(f"  Weeks Since Transfer:{p.weeks_since_transfer}")
    print()
    print(f"  Injuries This Year:  {p.injuries_this_year}")
    print(f"  Injuries Last Year:  {p.injuries_last_year}")
    print(f"  DspPts This Year:    {p.dsp_pts_this_year}")
    print(f"  DspPts Last Year:    {p.dsp_pts_last_year}")
    print(f"  Goals This Year:     {p.goals_this_year}")
    print(f"  Goals Last Year:     {p.goals_last_year}")
    print(f"  Matches This Year:   {p.matches_this_year}")
    print(f"  Matches Last Year:   {p.matches_last_year}")
    print()
    print(f"  Div1 Years:          {p.div1_years}")
    print(f"  Div2 Years:          {p.div2_years}")
    print(f"  Div3 Years:          {p.div3_years}")
    print(f"  Div4 Years:          {p.div4_years}")
    print(f"  Int Years:           {p.int_years}")
    print(f"  Contract Years:      {p.contract_years}")


def cmd_young_talents(args):
    adf = ADF.load(args.adf)
    slot = SaveSlot(adf, args.save)
    gd = _load_game_disk(getattr(args, 'game_adf', None))
    max_age = args.max_age

    players = slot.get_young_talents(max_age)
    if args.market_only:
        players = [p for p in players if p.is_market_available]

    on_market = sum(1 for p in players if p.is_market_available)
    print(f"Young Talents — age ≤ {max_age}  ({len(players)} players, {on_market} on market)")

    if gd:
        print(f"{'ID':>5} {'Name':<18} {'Age':>4} {'Pos':>4} {'Team':<16} {'Skill':>5} {'Mkt':>3}")
        print("-" * 65)
        for p in players:
            team = slot.get_team_name(p.team_index)
            name = gd.player_full_name(p.rng_seed) if p.rng_seed else ""
            mkt = "★" if p.is_market_available else ""
            print(f"{p.player_id:>5} {name:<18} {p.age:>4} {p.position_name:>4} {team:<16} {p.total_skill:>5} {mkt:>3}")
    else:
        print(f"{'ID':>5} {'Age':>4} {'Pos':>4} {'Team':<16} {'Skill':>5} {'Mkt':>3}")
        print("-" * 45)
        for p in players:
            team = slot.get_team_name(p.team_index)
            mkt = "★" if p.is_market_available else ""
            print(f"{p.player_id:>5} {p.age:>4} {p.position_name:>4} {team:<16} {p.total_skill:>5} {mkt:>3}")


def cmd_highlights(args):
    adf = ADF.load(args.adf)
    slot = SaveSlot(adf, args.save)
    gd = _load_game_disk(getattr(args, 'game_adf', None))

    all_players = slot.get_top_scorers()  # sorted by division, then goals desc
    if args.market_only:
        all_players = [p for p in all_players if p.is_market_available]

    print("Championship Highlights\n")

    # Group by division
    divisions: dict[int, list] = {}
    for p in all_players:
        divisions.setdefault(p.division, []).append(p)

    for div in sorted(divisions.keys()):
        players = divisions[div]
        div_label = f"Division {div}" if div > 0 else "Division (unset)"
        on_market = sum(1 for p in players if p.is_market_available)
        print(f"=== {div_label} ({len(players)} players, {on_market} on market) ===")
        if gd:
            print(f"{'ID':>5} {'Name':<18} {'Age':>4} {'Pos':>4} {'Team':<16} {'Goals':>6} {'Matches':>8} {'Mkt':>3}")
            print("-" * 75)
            for p in players:
                team = slot.get_team_name(p.team_index)
                name = gd.player_full_name(p.rng_seed) if p.rng_seed else ""
                mkt = "★" if p.is_market_available else ""
                print(f"{p.player_id:>5} {name:<18} {p.age:>4} {p.position_name:>4} {team:<16} {p.goals_this_year:>6} {p.matches_this_year:>8} {mkt:>3}")
        else:
            print(f"{'ID':>5} {'Age':>4} {'Pos':>4} {'Team':<16} {'Goals':>6} {'Matches':>8} {'Mkt':>3}")
            print("-" * 55)
            for p in players:
                team = slot.get_team_name(p.team_index)
                mkt = "★" if p.is_market_available else ""
                print(f"{p.player_id:>5} {p.age:>4} {p.position_name:>4} {team:<16} {p.goals_this_year:>6} {p.matches_this_year:>8} {mkt:>3}")
        print()


def cmd_best_xi(args):
    adf = ADF.load(args.adf)
    slot = SaveSlot(adf, args.save)
    gd = _load_game_disk(getattr(args, 'game_adf', None))

    named_filter = XI_FILTERS.get(args.filter) if args.filter else None
    if args.market_only and named_filter:
        filter_fn = lambda p: named_filter(p) and p.is_market_available
    elif args.market_only:
        filter_fn = lambda p: p.is_market_available
    else:
        filter_fn = named_filter
    xi = slot.best_xi(
        args.formation,
        filter_fn=filter_fn,
        max_per_team=args.max_per_team,
    )

    label = f"Best XI ({args.formation})"
    if args.filter:
        label += f" — {args.filter}"
    if args.max_per_team:
        label += f", max {args.max_per_team}/team"
    print(f"{label}  ({len(xi)} players)\n")

    group_labels = {1: "Goalkeeper", 2: "Defenders", 3: "Midfielders", 4: "Forwards"}
    current_pos = None
    for p in xi:
        if p.position != current_pos:
            current_pos = p.position
            print(f"— {group_labels[current_pos]} —")
        team = slot.get_team_name(p.team_index)
        mkt = "★" if p.is_market_available else " "
        name = gd.player_full_name(p.rng_seed) if gd and p.rng_seed else ""
        if gd:
            print(f"  {p.player_id:>5} {name:<18} {p.age:>3}y {p.position_name:<3} "
                  f"{team:<16} skill {p.total_skill:>4} {mkt}")
        else:
            print(f"  {p.player_id:>5} {p.age:>3}y {p.position_name:<3} "
                  f"{team:<16} skill {p.total_skill:>4} {mkt}")


def cmd_career_tracker(args):
    adf_a = ADF.load(args.adf)
    adf_b = ADF.load(args.adf_b) if args.adf_b else adf_a
    slot_a = SaveSlot(adf_a, args.save_a)
    slot_b = SaveSlot(adf_b, args.save_b)
    gd = _load_game_disk(getattr(args, "game_adf", None))

    diffs = slot_a.diff_players(slot_b)
    if args.team_changes_only:
        diffs = [d for d in diffs if d["team_changed"]]

    sort_key = {
        "skill": lambda d: -d["skill_delta"],
        "id": lambda d: d["player_id"],
        "changes": lambda d: -len(d["changed"]),
    }[args.sort]
    diffs.sort(key=sort_key)
    if args.limit:
        diffs = diffs[: args.limit]

    print(f"Comparing A={args.save_a} -> B={args.save_b}  ({len(diffs)} players changed)")
    print()
    for d in diffs:
        p_old, p_new = d["old"], d["new"]
        name = (gd.player_full_name(p_new.rng_seed)
                if gd and p_new.rng_seed else "")
        team_old = slot_a.get_team_name(p_old.team_index)
        team_new = slot_b.get_team_name(p_new.team_index)
        header = f"#{d['player_id']:>4}"
        if name:
            header += f"  {name}"
        header += f"  skill {p_old.total_skill:>4} -> {p_new.total_skill:>4} "
        if d["skill_delta"]:
            header += f"({d['skill_delta']:+d})"
        print(header)
        if d["team_changed"]:
            print(f"      team: {team_old} -> {team_new}")
        if d["age_delta"]:
            print(f"      age:  {p_old.age} -> {p_new.age}")
        # Highlight skill-level changes to individual attributes
        for field, (va, vb) in sorted(d["changed"].items()):
            if field in SKILL_NAMES and va != vb:
                print(f"      {field:<10} {va:>3} -> {vb:>3} ({vb-va:+d})")


def cmd_squad_analyst(args):
    adf = ADF.load(args.adf)
    slot = SaveSlot(adf, args.save)

    if args.team is not None:
        summaries = [slot.squad_summary(args.team)]
    else:
        summaries = slot.all_squad_summaries()

    print(f"{'#':>3} {'Team':<16} {'Sz':>3} {'GK':>3} {'DEF':>4} {'MID':>4} {'FWD':>4} "
          f"{'Age':>5} {'Skill':>6} {'Young':>5} {'Old':>3} {'Mkt':>4}")
    print("-" * 80)
    for s in summaries:
        print(f"{s['team_index']:>3} {s['team_name'][:16]:<16} {s['size']:>3} "
              f"{s['by_position']['GK']:>3} {s['by_position']['DEF']:>4} "
              f"{s['by_position']['MID']:>4} {s['by_position']['FWD']:>4} "
              f"{s['avg_age']:>5.1f} {s['avg_skill']:>6.0f} "
              f"{s['min_age'] or 0:>5} {s['max_age'] or 0:>3} "
              f"{s['on_market']:>4}")

    if args.team is not None and summaries and summaries[0]["size"]:
        s = summaries[0]
        print()
        print(f"  Youngest: #{s['youngest'].player_id} ({s['youngest'].age}y, "
              f"{s['youngest'].position_name})")
        print(f"  Oldest:   #{s['oldest'].player_id} ({s['oldest'].age}y, "
              f"{s['oldest'].position_name})")
        print(f"  Best:     #{s['best'].player_id} "
              f"(skill {s['best'].total_skill}, {s['best'].position_name})")


def _player_to_row(p: PlayerRecord, slot: SaveSlot, gd) -> dict:
    row = {f.name: getattr(p, f.name) for f in dataclasses.fields(p)}
    row["position_name"] = p.position_name
    row["team_name"] = slot.get_team_name(p.team_index)
    row["is_free_agent"] = p.is_free_agent
    row["is_transfer_listed"] = p.is_transfer_listed
    row["is_market_available"] = p.is_market_available
    row["total_skill"] = p.total_skill
    row["name"] = (gd.player_full_name(p.rng_seed)
                   if gd and p.rng_seed else "")
    return row


def cmd_export_players(args):
    adf = ADF.load(args.adf)
    slot = SaveSlot(adf, args.save)
    gd = _load_game_disk(getattr(args, "game_adf", None))

    if args.team is not None:
        players = slot.get_players_by_team(args.team)
    elif args.free_agents:
        players = slot.get_free_agents()
    else:
        players = [p for p in slot.players if p.age > 0]

    rows = [_player_to_row(p, slot, gd) for p in players]

    out = open(args.output, "w", newline="", encoding="utf-8") if args.output else sys.stdout
    try:
        if args.format == "json":
            json.dump(rows, out, indent=2)
            out.write("\n")
        else:
            if not rows:
                return
            writer = csv.DictWriter(out, fieldnames=list(rows[0].keys()))
            writer.writeheader()
            writer.writerows(rows)
    finally:
        if args.output:
            out.close()
            print(f"Wrote {len(rows)} players to {args.output}", file=sys.stderr)


def cmd_edit_player(args):
    adf = ADF.load(args.adf)
    slot = SaveSlot(adf, args.save)
    p = slot.get_player(args.id)

    editable = [
        "age", "position", "division", "team_index", "height", "weight",
        *SKILL_NAMES,
        "injury_weeks", "disciplinary", "morale", "value", "weeks_since_transfer",
        "injuries_this_year", "injuries_last_year",
        "goals_this_year", "goals_last_year",
        "matches_this_year", "matches_last_year",
        "div1_years", "div2_years", "div3_years", "div4_years",
        "int_years", "contract_years",
    ]

    changes = []
    for field_name in editable:
        val = getattr(args, field_name, None)
        if val is not None:
            old = getattr(p, field_name)
            setattr(p, field_name, val)
            changes.append((field_name, old, val))

    if not changes:
        print("No changes specified. Use --age, --pace, etc. to set values.")
        return

    for field_name, old, new in changes:
        print(f"  {field_name}: {old} -> {new}")

    slot.write_player(args.id)

    dest = args.output or args.adf
    if dest == args.adf:
        bak = ensure_backup(dest)
        if bak:
            print(f"Backup created: {bak}")
    adf.save(dest)
    print(f"Saved to {dest}")


def main():
    parser = argparse.ArgumentParser(
        prog="pm_cli",
        description=f"PMSaveDiskTool v2 {__version__} — Player Manager Save Disk Editor",
    )
    parser.add_argument("--version", action="version",
                        version=f"PMSaveDiskTool v2 {__version__}")
    sub = parser.add_subparsers(dest="command", required=True)

    # list-saves
    p_ls = sub.add_parser("list-saves", help="List save files in the ADF")
    p_ls.add_argument("adf", help="Path to the ADF disk image")

    # list-players
    p_lp = sub.add_parser("list-players", help="List players in a save")
    p_lp.add_argument("adf", help="Path to the ADF disk image")
    p_lp.add_argument("--save", required=True, help="Save file name (e.g. pm1.sav)")
    p_lp.add_argument("--team", type=int, help="Filter by team index")
    p_lp.add_argument("--free-agents", action="store_true", help="Show free agents only")
    p_lp.add_argument("--game-adf", metavar="PATH", help="Game disk ADF for player names")

    # show-player
    p_sp = sub.add_parser("show-player", help="Show full player details")
    p_sp.add_argument("adf", help="Path to the ADF disk image")
    p_sp.add_argument("--save", required=True, help="Save file name")
    p_sp.add_argument("--id", type=int, required=True, help="Player ID (0-based)")

    # young-talents
    p_yt = sub.add_parser("young-talents", help="List young players sorted by skill")
    p_yt.add_argument("adf", help="Path to the ADF disk image")
    p_yt.add_argument("--save", required=True, help="Save file name (e.g. pm1.sav)")
    p_yt.add_argument("--max-age", type=int, default=21, help="Maximum age (default: 21)")
    p_yt.add_argument("--market-only", action="store_true", help="Show only players available on the market")
    p_yt.add_argument("--game-adf", metavar="PATH", help="Game disk ADF for player names")

    # highlights
    p_hl = sub.add_parser("highlights", help="Top scorers per division")
    p_hl.add_argument("adf", help="Path to the ADF disk image")
    p_hl.add_argument("--save", required=True, help="Save file name (e.g. pm1.sav)")
    p_hl.add_argument("--market-only", action="store_true", help="Show only players available on the market")
    p_hl.add_argument("--game-adf", metavar="PATH", help="Game disk ADF for player names")

    # best-xi
    p_xi = sub.add_parser("best-xi", help="Top XI of the championship by formation")
    p_xi.add_argument("adf", help="Path to the ADF disk image")
    p_xi.add_argument("--save", required=True, help="Save file name (e.g. pm1.sav)")
    p_xi.add_argument("--formation", default="4-4-2", choices=list(FORMATIONS),
                      help="Formation (default: 4-4-2)")
    p_xi.add_argument("--max-per-team", type=int, metavar="N",
                      help="Cap selections per team (free agents exempt)")
    p_xi.add_argument("--filter", choices=list(XI_FILTERS),
                      help="Pre-filter the pool")
    p_xi.add_argument("--market-only", action="store_true",
                      help="Restrict to players available on the market (free agent or transfer-listed)")
    p_xi.add_argument("--game-adf", metavar="PATH", help="Game disk ADF for player names")

    # career-tracker
    p_ct = sub.add_parser("career-tracker",
                          help="Diff two save slots to track player progression")
    p_ct.add_argument("adf", help="Path to the ADF disk image (side A)")
    p_ct.add_argument("--save-a", default="pm1.sav", help="Save slot A (default: pm1.sav)")
    p_ct.add_argument("--save-b", default="pm2.sav", help="Save slot B (default: pm2.sav)")
    p_ct.add_argument("--adf-b", metavar="PATH",
                      help="Second ADF for slot B (default: same ADF)")
    p_ct.add_argument("--sort", choices=("skill", "id", "changes"), default="skill",
                      help="Sort output (default: skill delta descending)")
    p_ct.add_argument("--limit", type=int, help="Show only the top N players")
    p_ct.add_argument("--team-changes-only", action="store_true",
                      help="Show only players whose team changed")
    p_ct.add_argument("--game-adf", metavar="PATH", help="Game disk ADF for player names")

    # squad-analyst
    p_sa = sub.add_parser("squad-analyst", help="Per-team composition breakdown")
    p_sa.add_argument("adf", help="Path to the ADF disk image")
    p_sa.add_argument("--save", required=True, help="Save file name (e.g. pm1.sav)")
    p_sa.add_argument("--team", type=int, help="Single team (omit for all teams)")

    # export-players
    p_ex = sub.add_parser("export-players", help="Export players as CSV or JSON")
    p_ex.add_argument("adf", help="Path to the ADF disk image")
    p_ex.add_argument("--save", required=True, help="Save file name (e.g. pm1.sav)")
    p_ex.add_argument("--format", choices=("csv", "json"), default="csv",
                      help="Output format (default: csv)")
    p_ex.add_argument("--output", "-o", help="Output file (default: stdout)")
    p_ex.add_argument("--team", type=int, help="Filter by team index")
    p_ex.add_argument("--free-agents", action="store_true", help="Free agents only")
    p_ex.add_argument("--game-adf", metavar="PATH", help="Game disk ADF for player names")

    # edit-player
    p_ep = sub.add_parser("edit-player", help="Edit player attributes")
    p_ep.add_argument("adf", help="Path to the ADF disk image")
    p_ep.add_argument("--save", required=True, help="Save file name")
    p_ep.add_argument("--id", type=int, required=True, help="Player ID (0-based)")
    p_ep.add_argument("--output", "-o", help="Output file (default: overwrite input)")
    p_ep.add_argument("--age", type=int)
    p_ep.add_argument("--position", type=int)
    p_ep.add_argument("--division", type=int)
    p_ep.add_argument("--team-index", type=int)
    p_ep.add_argument("--height", type=int)
    p_ep.add_argument("--weight", type=int)
    for skill in SKILL_NAMES:
        p_ep.add_argument(f"--{skill}", type=int)
    p_ep.add_argument("--injury-weeks", type=int)
    p_ep.add_argument("--disciplinary", type=int)
    p_ep.add_argument("--morale", type=int)
    p_ep.add_argument("--value", type=int)
    p_ep.add_argument("--weeks-since-transfer", type=int)
    p_ep.add_argument("--injuries-this-year", type=int)
    p_ep.add_argument("--injuries-last-year", type=int)
    p_ep.add_argument("--goals-this-year", type=int)
    p_ep.add_argument("--goals-last-year", type=int)
    p_ep.add_argument("--matches-this-year", type=int)
    p_ep.add_argument("--matches-last-year", type=int)
    p_ep.add_argument("--div1-years", type=int)
    p_ep.add_argument("--div2-years", type=int)
    p_ep.add_argument("--div3-years", type=int)
    p_ep.add_argument("--div4-years", type=int)
    p_ep.add_argument("--int-years", type=int)
    p_ep.add_argument("--contract-years", type=int)

    args = parser.parse_args()
    commands = {
        "list-saves": cmd_list_saves,
        "list-players": cmd_list_players,
        "show-player": cmd_show_player,
        "edit-player": cmd_edit_player,
        "young-talents": cmd_young_talents,
        "highlights": cmd_highlights,
        "best-xi": cmd_best_xi,
        "squad-analyst": cmd_squad_analyst,
        "career-tracker": cmd_career_tracker,
        "export-players": cmd_export_players,
    }
    commands[args.command](args)


if __name__ == "__main__":
    main()
