"""Pure logic and persistence helpers for the World Cup tracker."""
import base64
import json
import os
from urllib.parse import quote

import requests

ROUND_ORDER = ["R32", "R16", "QF", "SF", "F"]

FLAGS = {
    "Mexico": "🇲🇽", "South Korea": "🇰🇷", "Czechia": "🇨🇿", "South Africa": "🇿🇦",
    "Canada": "🇨🇦", "Switzerland": "🇨🇭", "Bosnia and Herzegovina": "🇧🇦", "Qatar": "🇶🇦",
    "Scotland": "🏴\U000e0067\U000e0062\U000e0073\U000e0063\U000e0074\U000e007f",
    "Brazil": "🇧🇷", "Morocco": "🇲🇦", "Haiti": "🇭🇹", "USA": "🇺🇸",
    "Australia": "🇦🇺", "Türkiye": "🇹🇷", "Paraguay": "🇵🇾", "Germany": "🇩🇪",
    "Ivory Coast": "🇨🇮", "Ecuador": "🇪🇨", "Curaçao": "🇨🇼", "Sweden": "🇸🇪",
    "Netherlands": "🇳🇱", "Japan": "🇯🇵", "Tunisia": "🇹🇳", "Belgium": "🇧🇪",
    "Egypt": "🇪🇬", "Iran": "🇮🇷", "New Zealand": "🇳🇿", "Spain": "🇪🇸",
    "Cape Verde": "🇨🇻", "Saudi Arabia": "🇸🇦", "Uruguay": "🇺🇾", "Norway": "🇳🇴",
    "France": "🇫🇷", "Senegal": "🇸🇳", "Iraq": "🇮🇶", "Argentina": "🇦🇷",
    "Austria": "🇦🇹", "Jordan": "🇯🇴", "Algeria": "🇩🇿", "Colombia": "🇨🇴",
    "DR Congo": "🇨🇩", "Portugal": "🇵🇹", "Uzbekistan": "🇺🇿",
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
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    os.replace(tmp, path)


def github_load_data(repo, token, path="data.json", branch="main"):
    """Load JSON from a GitHub repository using the Contents API."""
    url = f"https://api.github.com/repos/{repo}/contents/{quote(path)}"
    r = requests.get(url, headers={"Authorization": f"Bearer {token}",
                                   "Accept": "application/vnd.github+json"},
                     params={"ref": branch}, timeout=20)
    r.raise_for_status()
    payload = r.json()
    return json.loads(base64.b64decode(payload["content"]).decode("utf-8"))


def github_save_data(repo, token, data, path="data.json", branch="main",
                     message="Update World Cup tracker data"):
    """Commit JSON to GitHub. This makes Streamlit Cloud edits durable."""
    url = f"https://api.github.com/repos/{repo}/contents/{quote(path)}"
    headers = {"Authorization": f"Bearer {token}", "Accept": "application/vnd.github+json"}
    current = requests.get(url, headers=headers, params={"ref": branch}, timeout=20)
    sha = current.json().get("sha") if current.ok else None
    raw = json.dumps(data, indent=2, ensure_ascii=False).encode("utf-8")
    body = {"message": message, "content": base64.b64encode(raw).decode("ascii"), "branch": branch}
    if sha:
        body["sha"] = sha
    r = requests.put(url, headers=headers, json=body, timeout=25)
    r.raise_for_status()
    return r.json()


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


def match_decided(m):
    if m.get("winner"):
        return True
    s1, s2 = m.get("score1"), m.get("score2")
    return s1 is not None and s2 is not None and m.get("final", True) and s1 != s2


def winner_of(m):
    if m.get("winner"):
        return m["winner"]
    if not match_decided(m):
        return None
    return m["team1"] if m["score1"] > m["score2"] else m["team2"]


def loser_of(m):
    w = winner_of(m)
    if not w:
        return None
    return m["team2"] if w == m["team1"] else m["team1"]


def is_live(m):
    return bool(m.get("in_play")) or (m.get("score1") is not None and m.get("score2") is not None
            and not m.get("final", True) and not m.get("winner"))


# ------------------------- bracket propagation -------------------------------
def recompute_feeds(data, clear_stale=True):
    """Rebuild every downstream slot from decided upstream matches."""
    if clear_stale:
        for rk in ROUND_ORDER[1:]:
            for m in data["matches"].get(rk, []):
                m["team1"] = ""
                m["team2"] = ""
    for rk in ROUND_ORDER:
        for m in data["matches"].get(rk, []):
            feed = m.get("feeds_to")
            w = winner_of(m)
            if not feed or not w:
                continue
            nm = _find(data, feed["round"], feed["match"])
            if nm:
                nm["team1" if feed["slot"] == 1 else "team2"] = w


def set_match(data, rk, match_id, team1, team2, score1, score2, winner=None,
              final=True, pen1=None, pen2=None):
    m = _find(data, rk, match_id)
    if m is None:
        raise KeyError(f"No match {rk}/{match_id}")
    m.update({"team1": team1, "team2": team2, "score1": score1, "score2": score2,
              "pen1": pen1, "pen2": pen2, "in_play": False,
              "final": bool(final) and score1 is not None and score2 is not None})
    m["winner"] = winner if winner in (team1, team2) else None
    recompute_feeds(data)
    return m


# --------------------------- team statuses -----------------------------------
def _score_string(m, winner):
    s1, s2 = m.get("score1"), m.get("score2")
    if s1 is None or s2 is None:
        return None
    ws, ls = (s1, s2) if winner == m["team1"] else (s2, s1)
    p1, p2 = m.get("pen1"), m.get("pen2")
    if p1 is not None and p2 is not None:
        wp, lp = (p1, p2) if winner == m["team1"] else (p2, p1)
        return f"{ws}–{ls} ({wp}–{lp} pen.)"
    return f"{ws}–{ls}"


def compute_team_statuses(data):
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
                status[l] = {"status": "out", "by": w, "score": _score_string(m, w),
                             "round": round_name(data, rk), "stage": None}
    return status


def player_summary(data, statuses, player):
    teams = data["players"].get(player, [])
    alive = sum(1 for t in teams if statuses.get(t, {}).get("status") == "active")
    return {"alive": alive, "total": len(teams), "teams": teams}


def champion(data):
    return winner_of(data["matches"]["F"][0])
