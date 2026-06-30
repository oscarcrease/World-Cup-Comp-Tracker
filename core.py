"""
Pure logic for the World Cup tracker. No Streamlit here, so it can be unit-tested
on its own. app.py imports from this module.
"""
import json
import os

ROUND_ORDER = ["R32", "R16", "QF", "SF", "F"]

FLAGS = {
    "Mexico": "🇲🇽", "South Korea": "🇰🇷", "Czechia": "🇨🇿", "South Africa": "🇿🇦",
    "Canada": "🇨🇦", "Switzerland": "🇨🇭", "Bosnia and Herzegovina": "🇧🇦", "Qatar": "🇶🇦",
    "Scotland": "🏴\U000e0067\U000e0062\U000e0073\U000e0063\U000e0074\U000e007f",
    "Brazil": "🇧🇷", "Morocco": "🇲🇦", "Haiti": "🇭🇹",
    "USA": "🇺🇸", "Australia": "🇦🇺", "Türkiye": "🇹🇷", "Paraguay": "🇵🇾",
    "Germany": "🇩🇪", "Ivory Coast": "🇨🇮", "Ecuador": "🇪🇨", "Curaçao": "🇨🇼",
    "Sweden": "🇸🇪", "Netherlands": "🇳🇱", "Japan": "🇯🇵", "Tunisia": "🇹🇳",
    "Belgium": "🇧🇪", "Egypt": "🇪🇬", "Iran": "🇮🇷", "New Zealand": "🇳🇿",
    "Spain": "🇪🇸", "Cape Verde": "🇨🇻", "Saudi Arabia": "🇸🇦", "Uruguay": "🇺🇾",
    "Norway": "🇳🇴", "France": "🇫🇷", "Senegal": "🇸🇳", "Iraq": "🇮🇶",
    "Argentina": "🇦🇷", "Austria": "🇦🇹", "Jordan": "🇯🇴", "Algeria": "🇩🇿",
    "Colombia": "🇨🇴", "DR Congo": "🇨🇩", "Portugal": "🇵🇹", "Uzbekistan": "🇺🇿",
    "England": "🏴\U000e0067\U000e0062\U000e0065\U000e006e\U000e0067\U000e007f",
    "Ghana": "🇬🇭", "Panama": "🇵🇦", "Croatia": "🇭🇷",
}


def flag(team):
    return FLAGS.get(team, "")


# ----------------------------- persistence -----------------------------------
def load_data(path):
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def save_data(path, data):
    """Atomic write so a crash mid-save can't corrupt the file."""
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    os.replace(tmp, path)


# ----------------------------- queries ---------------------------------------
def all_teams(data):
    return [t for g in data["groups"].values() for t in g]


def round_name(data, rk):
    return data.get("round_names", {}).get(rk, rk)


def _find(data, rk, match_id):
    for m in data["matches"].get(rk, []):
        if m["id"] == match_id:
            return m
    return None


def is_real_team(data, name):
    return name in set(all_teams(data))


def match_decided(m):
    # An explicit winner (e.g. penalties) always counts as decided.
    if m.get("winner"):
        return True
    s1, s2 = m.get("score1"), m.get("score2")
    if s1 is None or s2 is None:
        return False
    # 'final' defaults True so manually entered scores still count; live in-play
    # matches set final=False so a leading scoreline isn't treated as a result.
    if not m.get("final", True):
        return False
    return s1 != s2


def winner_of(m):
    if m.get("winner"):
        return m["winner"]
    if not match_decided(m):
        return None
    s1, s2 = m["score1"], m["score2"]
    return m["team1"] if s1 > s2 else m["team2"]


def is_live(m):
    """Scores present, but the match isn't final and has no decided winner."""
    return (m.get("score1") is not None and m.get("score2") is not None
            and not m.get("final", True) and not m.get("winner"))


def loser_of(m):
    w = winner_of(m)
    if not w:
        return None
    return m["team2"] if w == m["team1"] else m["team1"]


# ------------------------- bracket propagation -------------------------------
def recompute_feeds(data):
    """Push each decided match's winner into the slot it feeds, in round order.
    Only sets slots when there is a winner; never clears a manual entry."""
    for rk in ROUND_ORDER:
        for m in data["matches"].get(rk, []):
            feed = m.get("feeds_to")
            if not feed:
                continue
            w = winner_of(m)
            if not w:
                continue
            nm = _find(data, feed["round"], feed["match"])
            if nm is None:
                continue
            nm["team1" if feed["slot"] == 1 else "team2"] = w


def set_match(data, rk, match_id, team1, team2, score1, score2, winner=None, final=True):
    """Update a single match, then re-propagate the whole bracket."""
    m = _find(data, rk, match_id)
    if m is None:
        raise KeyError(f"No match {rk}/{match_id}")
    m["team1"] = team1
    m["team2"] = team2
    m["score1"] = score1
    m["score2"] = score2
    # Only 'final' when there are actually two scores recorded.
    m["final"] = bool(final) and score1 is not None and score2 is not None
    if winner and winner in (team1, team2):
        m["winner"] = winner
    else:
        m["winner"] = None  # let it derive from scores
    recompute_feeds(data)
    return m


# --------------------------- team statuses -----------------------------------
def _score_string(m, winner):
    s1, s2 = m.get("score1"), m.get("score2")
    if s1 is None or s2 is None:
        return None
    ws, ls = (s1, s2) if winner == m["team1"] else (s2, s1)
    return f"{ws}\u2013{ls} (pens)" if ws == ls else f"{ws}\u2013{ls}"


def compute_team_statuses(data):
    """Return {team: {status, by, score, round, stage}} for every team.
    status is 'active' or 'out'. Knockout losses override group-stage flags."""
    teams = set(all_teams(data))
    status = {t: {"status": "active", "by": None, "score": None,
                  "round": None, "stage": None} for t in teams}

    for t in data.get("group_stage_out", []):
        if t in status:
            status[t] = {"status": "out", "by": None, "score": None,
                         "round": None, "stage": "Group stage"}

    for rk in ROUND_ORDER:
        for m in data["matches"].get(rk, []):
            if not match_decided(m):
                continue
            w, l = winner_of(m), loser_of(m)
            if l in status:
                status[l] = {"status": "out", "by": w,
                             "score": _score_string(m, w),
                             "round": round_name(data, rk), "stage": None}
    return status


def player_summary(data, statuses, player):
    teams = data["players"].get(player, [])
    alive = sum(1 for t in teams if statuses.get(t, {}).get("status") == "active")
    return {"alive": alive, "total": len(teams), "teams": teams}


def champion(data):
    final = data["matches"]["F"][0]
    return winner_of(final)
