"""
Live score fetch from football-data.org (v4).

Get a free API key at https://www.football-data.org/client/register and put it in
.streamlit/secrets.toml as FOOTBALL_DATA_API_KEY (or an env var of the same name).
World Cup is competition code "WC" on the free tier.

This module is deliberately defensive: the 2026 tournament uses a new 48-team
format, so stage names and a few team-name spellings may differ from what's mapped
below. Anything it can't match is reported back to the UI (unmatched teams / unknown
stages) so you can extend ALIASES or STAGE_MAP without guessing.
"""
import unicodedata

import requests

import core

DEFAULT_BASE = "https://api.football-data.org/v4"


class LiveError(Exception):
    """Raised for any problem fetching/understanding the API response."""


# --------------------------------------------------------------------------- #
# Name normalisation
# --------------------------------------------------------------------------- #
CANON = set(core.FLAGS)  # the 48 canonical team names this app uses


def _deaccent(s):
    return "".join(c for c in unicodedata.normalize("NFKD", s)
                   if not unicodedata.combining(c))


# Keys are deaccented + lowercased API spellings -> our canonical names.
ALIASES = {
    "united states": "USA", "united states of america": "USA", "usa": "USA",
    "korea republic": "South Korea", "republic of korea": "South Korea",
    "south korea": "South Korea", "korea": "South Korea",
    "ir iran": "Iran", "iran": "Iran",
    "cote d'ivoire": "Ivory Coast", "ivory coast": "Ivory Coast",
    "czech republic": "Czechia", "czechia": "Czechia",
    "turkey": "Türkiye", "turkiye": "Türkiye",
    "cabo verde": "Cape Verde", "cape verde": "Cape Verde",
    "dr congo": "DR Congo", "congo dr": "DR Congo",
    "democratic republic of congo": "DR Congo",
    "democratic republic of the congo": "DR Congo",
    "bosnia and herzegovina": "Bosnia and Herzegovina",
    "bosnia-herzegovina": "Bosnia and Herzegovina",
    "bosnia & herzegovina": "Bosnia and Herzegovina", "bosnia": "Bosnia and Herzegovina",
    "curacao": "Curaçao",
}


def normalize_team(name):
    """Map an API team name to our canonical spelling, or return it unchanged."""
    if not name:
        return ""
    raw = name.strip()
    if raw in CANON:
        return raw
    key = _deaccent(raw).lower().strip()
    if key in ALIASES:
        return ALIASES[key]
    for c in CANON:                      # diacritic-insensitive fallback
        if _deaccent(c).lower() == key:
            return c
    return raw                           # unknown -> caller reports it


# --------------------------------------------------------------------------- #
# Stage mapping
# --------------------------------------------------------------------------- #
STAGE_MAP = {
    "LAST_32": "R32", "ROUND_OF_32": "R32", "R32": "R32",
    "LAST_16": "R16", "ROUND_OF_16": "R16", "R16": "R16",
    "QUARTER_FINALS": "QF", "QUARTER_FINAL": "QF",
    "SEMI_FINALS": "SF", "SEMI_FINAL": "SF",
    "FINAL": "F",
}
GROUP_STAGES = {"GROUP_STAGE", "GROUP"}
SKIP_STAGES = {"THIRD_PLACE", "3RD_PLACE", "PLAY_OFF_FOR_THIRD_PLACE"}

FINISHED = {"FINISHED", "AWARDED"}
IN_PLAY = {"IN_PLAY", "PAUSED", "SUSPENDED"}


# --------------------------------------------------------------------------- #
# Fetch + parse
# --------------------------------------------------------------------------- #
def fetch_raw(api_key, competition="WC", base_url=DEFAULT_BASE, timeout=15):
    if not api_key:
        raise LiveError("No API key set. Add FOOTBALL_DATA_API_KEY in Secrets, "
                        "or paste a key into the field.")
    url = f"{base_url}/competitions/{competition}/matches"
    try:
        r = requests.get(url, headers={"X-Auth-Token": api_key}, timeout=timeout)
    except requests.RequestException as e:
        raise LiveError(f"Network error reaching the API: {e}")

    if r.status_code in (401, 403):
        raise LiveError("API rejected the request (401/403) — the key is invalid "
                        "or this competition isn't included in your plan.")
    if r.status_code == 404:
        raise LiveError(f"Competition '{competition}' not found (404). Try code 'WC'.")
    if r.status_code == 429:
        raise LiveError("Rate-limited (429). The free tier allows ~10 requests/min — "
                        "wait a minute and try again.")
    if r.status_code != 200:
        raise LiveError(f"API returned HTTP {r.status_code}: {r.text[:200]}")
    try:
        return r.json()
    except ValueError:
        raise LiveError("API response wasn't valid JSON.")


def parse_matches(payload):
    """Turn the raw API payload into a flat list of normalised match dicts."""
    out = []
    for m in payload.get("matches", []):
        home_obj = m.get("homeTeam") or {}
        away_obj = m.get("awayTeam") or {}
        score = m.get("score") or {}
        ft = score.get("fullTime") or {}
        status = (m.get("status") or "").upper()
        out.append({
            "stage": (m.get("stage") or "").upper(),
            "status": status,
            "group": m.get("group"),
            "home": normalize_team(home_obj.get("name") or home_obj.get("shortName") or ""),
            "away": normalize_team(away_obj.get("name") or away_obj.get("shortName") or ""),
            "home_score": ft.get("home"),
            "away_score": ft.get("away"),
            "finished": status in FINISHED,
            "in_play": status in IN_PLAY,
            "winner_code": score.get("winner"),   # HOME_TEAM / AWAY_TEAM / DRAW / None
        })
    return out


# --------------------------------------------------------------------------- #
# Apply onto app data
# --------------------------------------------------------------------------- #
def apply_live(data, parsed):
    """Mutate `data` from parsed matches. Returns a human-readable report dict.

    - Knockout matches fill the bracket slots for their round (in API order) with
      teams and, if final, scores. In-play scores are stored but not treated as a
      result. Scheduled fixtures fill team names only.
    - Any team that appears in a knockout match is 'through'; every other group-stage
      team is marked out (so housemate cards cross them out automatically).
    """
    report = {"knockout_set": 0, "finished": 0, "in_play": 0, "advanced": 0,
              "group_out": 0, "unmatched_teams": set(), "unknown_stages": set(),
              "skipped": 0}
    valid = set(core.all_teams(data))

    advanced = set()
    by_round = {"R32": [], "R16": [], "QF": [], "SF": [], "F": []}

    for pm in parsed:
        stage = pm["stage"]
        if stage in GROUP_STAGES:
            for t in (pm["home"], pm["away"]):
                if t and t not in valid:
                    report["unmatched_teams"].add(t)
            continue
        if stage in SKIP_STAGES:
            report["skipped"] += 1
            continue
        rk = STAGE_MAP.get(stage)
        if not rk:
            report["unknown_stages"].add(stage)
            continue
        for t in (pm["home"], pm["away"]):
            if t and t in valid:
                advanced.add(t)
            elif t:
                report["unmatched_teams"].add(t)
        by_round[rk].append(pm)

    for rk, pms in by_round.items():
        slots = data["matches"].get(rk, [])
        for i, pm in enumerate(pms):
            if i >= len(slots):
                break
            slot = slots[i]
            slot["team1"] = pm["home"] or slot.get("team1", "")
            slot["team2"] = pm["away"] or slot.get("team2", "")
            hs, as_ = pm["home_score"], pm["away_score"]

            if pm["finished"] and hs is not None and as_ is not None:
                slot["score1"], slot["score2"], slot["final"] = hs, as_, True
                if hs == as_:  # drawn in normal/extra time -> decided on penalties
                    slot["winner"] = (pm["home"] if pm["winner_code"] == "HOME_TEAM"
                                      else pm["away"] if pm["winner_code"] == "AWAY_TEAM"
                                      else None)
                else:
                    slot["winner"] = None
                report["finished"] += 1
            elif pm["in_play"] and hs is not None and as_ is not None:
                slot["score1"], slot["score2"] = hs, as_
                slot["final"], slot["winner"] = False, None
                report["in_play"] += 1
            else:  # scheduled / timed -> teams only, clear any stale score
                slot["score1"], slot["score2"] = None, None
                slot["final"], slot["winner"] = False, None
            report["knockout_set"] += 1

    if advanced:  # only rewrite group exits once we actually have knockout data
        group_out = [t for t in core.all_teams(data) if t not in advanced]
        data["group_stage_out"] = group_out
        report["group_out"] = len(group_out)
    report["advanced"] = len(advanced)

    report["unmatched_teams"] = sorted(report["unmatched_teams"])
    report["unknown_stages"] = sorted(report["unknown_stages"])
    return report
