#!/usr/bin/env python3
"""Command-line interface for PMSaveDiskTool v2.

Usage:
    python pm_cli.py list-saves DISK.adf
    python pm_cli.py list-players DISK.adf --save pm1.sav [--team 0]
    python pm_cli.py show-player DISK.adf --save pm1.sav --id 42
    python pm_cli.py edit-player DISK.adf --save pm1.sav --id 42 --age 20 --pace 180
"""

import argparse
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from pm_core.adf import ADF
from pm_core.save import SaveSlot
from pm_core.player import SKILL_NAMES, POSITION_NAMES
from pm_core.names import GameDisk


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
    print(f"  Transfer Weeks:      {p.transfer_weeks}")
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


def cmd_edit_player(args):
    adf = ADF.load(args.adf)
    slot = SaveSlot(adf, args.save)
    p = slot.get_player(args.id)

    editable = [
        "age", "position", "division", "team_index", "height", "weight",
        *SKILL_NAMES,
        "injury_weeks", "disciplinary", "morale", "value", "transfer_weeks",
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

    if args.output:
        adf.save(args.output)
        print(f"Saved to {args.output}")
    else:
        adf.save(args.adf)
        print(f"Saved to {args.adf}")


def main():
    parser = argparse.ArgumentParser(
        prog="pm_cli",
        description="PMSaveDiskTool v2 — Player Manager Save Disk Editor",
    )
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
    p_ep.add_argument("--transfer-weeks", type=int)
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
    }
    commands[args.command](args)


if __name__ == "__main__":
    main()
