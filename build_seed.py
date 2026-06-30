"""
Generates data.json with the real 2026 FIFA World Cup groups (48 teams) and the
official Round-of-32 bracket structure. Run once: `python build_seed.py`.
Re-running overwrites data.json, so only do it if you want to reset everything.
"""
import json

# ---- Real 2026 World Cup groups (final draw + March 2026 play-off winners) ----
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

# ---- Official R32 slot pairings (FIFA 2026 knockout schedule) ----
# Each tuple = (slot1 label, slot2 label). Replace labels with real teams in the
# admin panel once each group placement is confirmed.
R32_SLOTS = [
    ("Runner-up A", "Runner-up B"),
    ("Winner C", "Runner-up F"),
    ("Winner E", "3rd A/B/C/D/F"),
    ("Winner F", "Runner-up C"),
    ("Runner-up E", "Runner-up I"),
    ("Winner I", "3rd C/D/F/G/H"),
    ("Winner A", "3rd C/E/F/H/I"),
    ("Winner L", "3rd E/H/I/J/K"),
    ("Winner G", "3rd A/E/H/I/J"),
    ("Winner D", "3rd B/E/F/I/J"),
    ("Winner H", "Runner-up J"),
    ("Runner-up K", "Runner-up L"),
    ("Winner B", "3rd E/F/G/I/J"),
    ("Runner-up D", "Runner-up G"),
    ("Winner J", "Runner-up H"),
    ("Winner K", "3rd D/E/I/J/L"),
]


def build_matches():
    matches = {"R32": [], "R16": [], "QF": [], "SF": [], "F": []}

    # R32: 16 matches, each feeds a slot in one of 8 R16 matches
    for i, (a, b) in enumerate(R32_SLOTS):
        feed_match = i // 2 + 1          # R16-1 .. R16-8
        feed_slot = 1 if i % 2 == 0 else 2
        matches["R32"].append({
            "id": f"R32-{i+1}", "team1": a, "team2": b,
            "score1": None, "score2": None, "winner": None,
            "feeds_to": {"round": "R16", "match": f"R16-{feed_match}", "slot": feed_slot},
        })

    # R16: 8 matches -> 4 QF
    for i in range(8):
        feed_match = i // 2 + 1
        feed_slot = 1 if i % 2 == 0 else 2
        matches["R16"].append({
            "id": f"R16-{i+1}", "team1": "", "team2": "",
            "score1": None, "score2": None, "winner": None,
            "feeds_to": {"round": "QF", "match": f"QF-{feed_match}", "slot": feed_slot},
        })

    # QF: 4 -> 2 SF
    for i in range(4):
        feed_match = i // 2 + 1
        feed_slot = 1 if i % 2 == 0 else 2
        matches["QF"].append({
            "id": f"QF-{i+1}", "team1": "", "team2": "",
            "score1": None, "score2": None, "winner": None,
            "feeds_to": {"round": "SF", "match": f"SF-{feed_match}", "slot": feed_slot},
        })

    # SF: 2 -> Final
    for i in range(2):
        feed_slot = 1 if i % 2 == 0 else 2
        matches["SF"].append({
            "id": f"SF-{i+1}", "team1": "", "team2": "",
            "score1": None, "score2": None, "winner": None,
            "feeds_to": {"round": "F", "match": "F-1", "slot": feed_slot},
        })

    # Final
    matches["F"].append({
        "id": "F-1", "team1": "", "team2": "",
        "score1": None, "score2": None, "winner": None, "feeds_to": None,
    })
    return matches


def build_players():
    """Deal all 48 teams round-robin to 6 housemates (8 each) as a starting point."""
    names = ["You", "Alex", "Sam", "Priya", "Jordan", "Riley"]
    flat = [t for g in GROUPS.values() for t in g]
    players = {n: [] for n in names}
    for idx, team in enumerate(flat):
        players[names[idx % len(names)]].append(team)
    return players


def main():
    matches = build_matches()
    for round_matches in matches.values():
        for m in round_matches:
            m["final"] = False
    data = {
        "config": {
            "title": "House World Cup 2026",
            "subtitle": "Sweepstake tracker · USA · Canada · Mexico",
            "admin_password": "housecup2026",
        },
        "groups": GROUPS,
        "round_names": ROUND_NAMES,
        "matches": matches,
        "players": build_players(),
        "group_stage_out": [],   # teams eliminated in the group stage (set in admin)
    }
    with open("data.json", "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    print("Wrote data.json:", len(data["players"]), "players,",
          sum(len(v) for v in GROUPS.values()), "teams")


if __name__ == "__main__":
    main()
