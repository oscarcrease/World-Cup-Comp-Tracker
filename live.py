"""Live fixture/score fetch from football-data.org v4."""
import unicodedata
from datetime import datetime

import requests
import core

DEFAULT_BASE = "https://api.football-data.org/v4"

class LiveError(Exception):
    pass

CANON = set(core.FLAGS)

def _deaccent(s):
    return "".join(c for c in unicodedata.normalize("NFKD", s) if not unicodedata.combining(c))

ALIASES = {
    "united states": "USA", "united states of america": "USA", "usa": "USA",
    "korea republic": "South Korea", "republic of korea": "South Korea", "south korea": "South Korea",
    "ir iran": "Iran", "cote d'ivoire": "Ivory Coast", "czech republic": "Czechia",
    "turkey": "Türkiye", "turkiye": "Türkiye", "cabo verde": "Cape Verde",
    "dr congo": "DR Congo", "congo dr": "DR Congo", "democratic republic of congo": "DR Congo",
    "bosnia-herzegovina": "Bosnia and Herzegovina", "bosnia & herzegovina": "Bosnia and Herzegovina",
    "bosnia": "Bosnia and Herzegovina", "curacao": "Curaçao",
}

def normalize_team(name):
    if not name:
        return ""
    raw = name.strip()
    if raw in CANON:
        return raw
    key = _deaccent(raw).lower().strip()
    if key in ALIASES:
        return ALIASES[key]
    for c in CANON:
        if _deaccent(c).lower() == key:
            return c
    return raw

STAGE_MAP = {
    "LAST_32": "R32", "ROUND_OF_32": "R32", "R32": "R32",
    "LAST_16": "R16", "ROUND_OF_16": "R16", "R16": "R16",
    "QUARTER_FINALS": "QF", "QUARTER_FINAL": "QF",
    "SEMI_FINALS": "SF", "SEMI_FINAL": "SF", "FINAL": "F",
}
GROUP_STAGES = {"GROUP_STAGE", "GROUP"}
SKIP_STAGES = {"THIRD_PLACE", "3RD_PLACE", "PLAY_OFF_FOR_THIRD_PLACE"}
FINISHED = {"FINISHED", "AWARDED"}
IN_PLAY = {"IN_PLAY", "PAUSED", "SUSPENDED"}

def fetch_raw(api_key, competition="WC", base_url=DEFAULT_BASE, timeout=15):
    if not api_key:
        raise LiveError("No API key set. Add FOOTBALL_DATA_API_KEY in Streamlit Secrets.")
    url = f"{base_url}/competitions/{competition}/matches"
    try:
        r = requests.get(url, headers={"X-Auth-Token": api_key}, timeout=timeout)
    except requests.RequestException as e:
        raise LiveError(f"Network error reaching the API: {e}") from e
    if r.status_code in (401, 403):
        raise LiveError("API rejected the request. Check the key and competition access.")
    if r.status_code == 429:
        raise LiveError("API rate limit reached. Wait a minute and try again.")
    if not r.ok:
        raise LiveError(f"API returned HTTP {r.status_code}: {r.text[:200]}")
    return r.json()

def _score_pair(node):
    if not isinstance(node, dict):
        return None, None
    return (node.get("home") if "home" in node else node.get("homeTeam"),
            node.get("away") if "away" in node else node.get("awayTeam"))

def parse_matches(payload):
    out = []
    for m in payload.get("matches", []):
        score = m.get("score") or {}
        hs, aas = _score_pair(score.get("fullTime"))
        p1, p2 = _score_pair(score.get("penalties"))
        status = (m.get("status") or "").upper()
        home_obj, away_obj = m.get("homeTeam") or {}, m.get("awayTeam") or {}
        out.append({
            "id": m.get("id"), "stage": (m.get("stage") or "").upper(), "status": status,
            "home": normalize_team(home_obj.get("name") or home_obj.get("shortName") or ""),
            "away": normalize_team(away_obj.get("name") or away_obj.get("shortName") or ""),
            "home_score": hs, "away_score": aas, "pen1": p1, "pen2": p2,
            "finished": status in FINISHED, "in_play": status in IN_PLAY,
            "winner_code": score.get("winner"), "utc_date": m.get("utcDate"),
            "last_updated": m.get("lastUpdated"),
        })
    return out

def apply_live(data, parsed):
    report = {"knockout_set": 0, "finished": 0, "in_play": 0, "advanced": 0,
              "group_out": 0, "unmatched_teams": set(), "unknown_stages": set(), "skipped": 0}
    valid = set(core.all_teams(data))
    advanced, by_round = set(), {k: [] for k in core.ROUND_ORDER}
    for pm in parsed:
        stage = pm["stage"]
        if stage in GROUP_STAGES:
            continue
        if stage in SKIP_STAGES:
            report["skipped"] += 1; continue
        rk = STAGE_MAP.get(stage)
        if not rk:
            if stage: report["unknown_stages"].add(stage)
            continue
        for t in (pm["home"], pm["away"]):
            if t in valid: advanced.add(t)
            elif t: report["unmatched_teams"].add(t)
        by_round[rk].append(pm)

    for rk, pms in by_round.items():
        # API order is normally chronological; preserve it consistently.
        pms.sort(key=lambda x: (x.get("utc_date") or "", x.get("id") or 0))
        for i, pm in enumerate(pms[:len(data["matches"].get(rk, []))]):
            slot = data["matches"][rk][i]
            slot.update({"api_id": pm["id"], "team1": pm["home"], "team2": pm["away"],
                         "utc_date": pm["utc_date"], "in_play": pm["in_play"]})
            hs, as_ = pm["home_score"], pm["away_score"]
            if (pm["finished"] or pm["in_play"]) and hs is not None and as_ is not None:
                slot.update({"score1": hs, "score2": as_, "pen1": pm["pen1"], "pen2": pm["pen2"],
                             "final": pm["finished"]})
                if pm["finished"]:
                    if pm["winner_code"] == "HOME_TEAM": slot["winner"] = pm["home"]
                    elif pm["winner_code"] == "AWAY_TEAM": slot["winner"] = pm["away"]
                    else: slot["winner"] = None
                    report["finished"] += 1
                else:
                    slot["winner"] = None; report["in_play"] += 1
            else:
                slot.update({"score1": None, "score2": None, "pen1": None, "pen2": None,
                             "winner": None, "final": False})
            report["knockout_set"] += 1

    # Critical fix: propagate winners after all API slots have been populated.
    core.recompute_feeds(data, clear_stale=False)
    if advanced:
        data["group_stage_out"] = [t for t in core.all_teams(data) if t not in advanced]
        report["group_out"] = len(data["group_stage_out"])
    report["advanced"] = len(advanced)
    report["unmatched_teams"] = sorted(report["unmatched_teams"])
    report["unknown_stages"] = sorted(report["unknown_stages"])
    return report
