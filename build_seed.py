"""Regenerate data.json with the 2026 World Cup teams and official bracket."""
import json

import core

GROUPS = {
    "A": ["Mexico", "South Korea", "Czechia", "South Africa"],
    "B": ["Canada", "Switzerland", "Bosnia and Herzegovina", "Qatar"],
    "C": ["Scotland", "Brazil", "Morocco", "Haiti"],
    "D": ["USA", "Australia", "Türkiye", "Paraguay"],
    "E": ["Germany", "Ivory Coast", "Ecuador", "Curaçao"],
    "F": ["Sweden", "Netherlands", "Japan", "Tunisia"],
    "G": ["Belgium", "Egypt", "Iran", "New Zealand"],
    "H": ["Spain", "Cape Verde", "Saudi Arabia", "Uruguay"],
    "I": ["Norway", "France", "Senegal", "Iraq"],
    "J": ["Argentina", "Austria", "Jordan", "Algeria"],
    "K": ["Colombia", "DR Congo", "Portugal", "Uzbekistan"],
    "L": ["England", "Ghana", "Panama", "Croatia"],
}

ROUND_NAMES = {
    "R32": "Round of 32",
    "R16": "Round of 16",
    "QF": "Quarter-finals",
    "SF": "Semi-finals",
    "F": "Final",
}


def build_players():
    names = ["You", "Alex", "Sam", "Priya", "Jordan", "Riley"]
    flat = [team for group in GROUPS.values() for team in group]
    players = {name: [] for name in names}
    for index, team in enumerate(flat):
        players[names[index % len(names)]].append(team)
    return players


def main():
    data = {
        "config": {
            "title": "House World Cup 2026",
            "subtitle": "Sweepstake tracker · USA · Canada · Mexico",
            "admin_password": "housecup2026",
            "auto_update": False,
            "auto_update_seconds": 90,
        },
        "groups": GROUPS,
        "round_names": ROUND_NAMES,
        "matches": core.build_official_matches(),
        "players": build_players(),
        "player_photos": {},
        "group_stage_out": [],
    }
    with open("data.json", "w", encoding="utf-8") as handle:
        json.dump(data, handle, indent=2, ensure_ascii=False)
    print("Wrote data.json with official FIFA match-number bracket topology.")


if __name__ == "__main__":
    main()
