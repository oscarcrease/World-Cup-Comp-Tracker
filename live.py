"""Live fixture/score fetch from football-data.org v4."""
from __future__ import annotations

import unicodedata

import requests

import core

DEFAULT_BASE = "https://api.football-data.org/v4"


class LiveError(Exception):
    pass


CANON = set(core.FLAG_CODES)


def _deaccent(value):
    return "".join(
        c for c in unicodedata.normalize("NFKD", value)
        if not unicodedata.combining(c)
    )


ALIASES = {
    "united states": "USA", "united states of america": "USA", "usa": "USA",
    "korea republic": "South Korea", "republic of korea": "South Korea",
    "south korea": "South Korea", "korea": "South Korea",
    "ir iran": "Iran", "cote d'ivoire": "Ivory Coast", "côte d'ivoire": "Ivory Coast",
    "czech republic": "Czechia", "turkey": "Türkiye", "turkiye": "Türkiye",
    "cabo verde": "Cape Verde", "dr congo": "DR Congo", "congo dr": "DR Congo",
    "democratic republic of congo": "DR Congo",
    "democratic republic of the congo": "DR Congo",
    "bosnia-herzegovina": "Bosnia and Herzegovina",
    "bosnia & herzegovina": "Bosnia and Herzegovina",
    "bosnia and herzegovina": "Bosnia and Herzegovina",
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
    for canonical in CANON:
        if _deaccent(canonical).lower() == key:
            return canonical
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
        response = requests.get(url, headers={"X-Auth-Token": api_key}, timeout=timeout)
    except requests.RequestException as exc:
        raise LiveError(f"Network error reaching the API: {exc}") from exc
    if response.status_code in (401, 403):
        raise LiveError("API rejected the request. Check the key and competition access.")
    if response.status_code == 429:
        raise LiveError("API rate limit reached. Wait a minute and try again.")
    if not response.ok:
        raise LiveError(f"API returned HTTP {response.status_code}: {response.text[:200]}")
    return response.json()


def _score_pair(node):
    if not isinstance(node, dict):
        return None, None
    return (
        node.get("home") if "home" in node else node.get("homeTeam"),
        node.get("away") if "away" in node else node.get("awayTeam"),
    )


def _sum_pairs(first, second):
    if first[0] is None or first[1] is None:
        return None, None
    extra_home = second[0] if second[0] is not None else 0
    extra_away = second[1] if second[1] is not None else 0
    return first[0] + extra_home, first[1] + extra_away


def _play_score(score):
    """Return goals scored during play, excluding the penalty shootout.

    football-data.org's v4 ``fullTime`` can include shootout conversions. Prefer
    regularTime + extraTime; otherwise subtract the penalties from fullTime.
    """
    full_time = _score_pair(score.get("fullTime"))
    regular_time = _score_pair(score.get("regularTime"))
    extra_time = _score_pair(score.get("extraTime"))
    penalties = _score_pair(score.get("penalties"))
    duration = (score.get("duration") or "").upper()

    if penalties[0] is not None and penalties[1] is not None:
        combined = _sum_pairs(regular_time, extra_time)
        if combined[0] is not None:
            return combined
        if full_time[0] is not None and full_time[1] is not None:
            home = full_time[0] - penalties[0]
            away = full_time[1] - penalties[1]
            if home >= 0 and away >= 0:
                return home, away

    if duration == "EXTRA_TIME":
        combined = _sum_pairs(regular_time, extra_time)
        if combined[0] is not None:
            return combined

    return full_time


def parse_matches(payload):
    out = []
    for match in payload.get("matches", []):
        score = match.get("score") or {}
        home_score, away_score = _play_score(score)
        pen1, pen2 = _score_pair(score.get("penalties"))
        status = (match.get("status") or "").upper()
        home_obj = match.get("homeTeam") or {}
        away_obj = match.get("awayTeam") or {}
        out.append({
            "id": match.get("id"),
            "matchday": match.get("matchday"),
            "stage": (match.get("stage") or "").upper(),
            "status": status,
            "home": normalize_team(home_obj.get("name") or home_obj.get("shortName") or ""),
            "away": normalize_team(away_obj.get("name") or away_obj.get("shortName") or ""),
            "home_score": home_score,
            "away_score": away_score,
            "pen1": pen1,
            "pen2": pen2,
            "duration": (score.get("duration") or "").upper(),
            "finished": status in FINISHED,
            "in_play": status in IN_PLAY,
            "winner_code": score.get("winner"),
            "utc_date": match.get("utcDate"),
            "last_updated": match.get("lastUpdated"),
        })
    return out


def _all_slots(data):
    for rk in core.ROUND_ORDER:
        for match in data["matches"].get(rk, []):
            yield rk, match


def _find_target(data, rk, fixture, api_map):
    if fixture.get("id") in api_map:
        old_rk, match_id = api_map[fixture["id"]]
        if old_rk == rk:
            return core._find(data, rk, match_id)

    match_id = core.identify_official_match(
        rk,
        fixture.get("home") or "",
        fixture.get("away") or "",
        fixture.get("matchday"),
    )
    if match_id:
        return core._find(data, rk, match_id)

    # A date match is a safe fallback for a fixture previously stored with TBDs.
    utc_date = fixture.get("utc_date")
    if utc_date:
        matches = [m for m in data["matches"].get(rk, []) if m.get("utc_date") == utc_date]
        if len(matches) == 1:
            return matches[0]
    return None


def apply_live(data, parsed):
    core.ensure_official_bracket(data)
    report = {
        "knockout_set": 0,
        "finished": 0,
        "in_play": 0,
        "advanced": 0,
        "group_out": 0,
        "unmatched_teams": set(),
        "unmatched_fixtures": [],
        "unknown_stages": set(),
        "skipped": 0,
    }
    valid = set(core.all_teams(data))
    advanced = set()
    api_map = {
        match.get("api_id"): (rk, match["id"])
        for rk, match in _all_slots(data)
        if match.get("api_id") is not None
    }

    by_round = {rk: [] for rk in core.ROUND_ORDER}
    for fixture in parsed:
        stage = fixture["stage"]
        if stage in GROUP_STAGES:
            continue
        if stage in SKIP_STAGES:
            report["skipped"] += 1
            continue
        rk = STAGE_MAP.get(stage)
        if not rk:
            if stage:
                report["unknown_stages"].add(stage)
            continue
        for team in (fixture["home"], fixture["away"]):
            if team in valid:
                advanced.add(team)
            elif team:
                report["unmatched_teams"].add(team)
        by_round[rk].append(fixture)

    planned = []
    for rk in core.ROUND_ORDER:
        assigned_ids = set()
        unresolved = []
        for fixture in by_round[rk]:
            slot = _find_target(data, rk, fixture, api_map)
            if slot is None:
                unresolved.append(fixture)
            else:
                assigned_ids.add(slot["id"])
                planned.append((rk, fixture, slot))

        # When both teams are still TBD, ancestry cannot identify the slot.
        # Place those fixtures by official kickoff order, not by visual list order.
        remaining_ids = [
            match_id for match_id in core.ROUND_CHRONO_IDS.get(rk, [])
            if match_id not in assigned_ids
        ]
        unresolved.sort(key=lambda fixture: (fixture.get("utc_date") or "", fixture.get("id") or 0))
        for fixture, match_id in zip(unresolved, remaining_ids):
            slot = core._find(data, rk, match_id)
            assigned_ids.add(match_id)
            planned.append((rk, fixture, slot))
        for fixture in unresolved[len(remaining_ids):]:
            if fixture.get("home") or fixture.get("away"):
                report["unmatched_fixtures"].append(
                    f"{rk}: {fixture.get('home') or 'TBD'} v {fixture.get('away') or 'TBD'}"
                )

    # Apply source rounds first so winner propagation can fill later fixtures.
    planned.sort(key=lambda item: core.ROUND_ORDER.index(item[0]))
    for rk, fixture, slot in planned:
        if slot is None:
            continue
        if fixture.get("home"):
            slot["team1"] = fixture["home"]
            slot.pop("team1_source", None)
        if fixture.get("away"):
            slot["team2"] = fixture["away"]
            slot.pop("team2_source", None)

        slot.update({
            "api_id": fixture.get("id"),
            "utc_date": fixture.get("utc_date"),
            "last_updated": fixture.get("last_updated"),
            "status": fixture.get("status"),
            "duration": fixture.get("duration"),
            "in_play": fixture.get("in_play", False),
        })
        if fixture.get("id") is not None:
            api_map[fixture["id"]] = (rk, slot["id"])

        home_score, away_score = fixture.get("home_score"), fixture.get("away_score")
        if (fixture.get("finished") or fixture.get("in_play")) and home_score is not None and away_score is not None:
            slot.update({
                "score1": home_score,
                "score2": away_score,
                "pen1": fixture.get("pen1"),
                "pen2": fixture.get("pen2"),
                "final": bool(fixture.get("finished")),
            })
            if fixture.get("finished"):
                if fixture.get("winner_code") == "HOME_TEAM":
                    slot["winner"] = slot.get("team1")
                elif fixture.get("winner_code") == "AWAY_TEAM":
                    slot["winner"] = slot.get("team2")
                else:
                    slot["winner"] = None
                report["finished"] += 1
            else:
                slot["winner"] = None
                report["in_play"] += 1
        else:
            slot.update({
                "score1": None,
                "score2": None,
                "pen1": None,
                "pen2": None,
                "winner": None,
                "final": False,
            })
        report["knockout_set"] += 1

    core.recompute_feeds(data, clear_stale=True)
    if advanced:
        data["group_stage_out"] = [team for team in core.all_teams(data) if team not in advanced]
        report["group_out"] = len(data["group_stage_out"])
    report["advanced"] = len(advanced)
    report["unmatched_teams"] = sorted(report["unmatched_teams"])
    report["unknown_stages"] = sorted(report["unknown_stages"])
    return report

