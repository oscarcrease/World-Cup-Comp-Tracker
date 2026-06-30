"""Pure logic and persistence helpers for the World Cup tracker."""
from __future__ import annotations

import base64
import copy
import json
import os
from functools import lru_cache
from urllib.parse import quote, urlparse

import requests

ROUND_ORDER = ["R32", "R16", "QF", "SF", "F"]

# The list order is the visual order in the left-to-right bracket. Adjacent
# matches in one round feed the same match in the next round.
ROUND_CHRONO_IDS = {
    # Chronological kickoff order within each knockout round. This is used only
    # to place API fixtures whose teams are still both TBD.
    "R32": [],  # R32 fixtures are identified by their known team pair.
    "R16": ["M90", "M89", "M91", "M92", "M93", "M94", "M95", "M96"],
    "QF": ["M97", "M98", "M99", "M100"],
    "SF": ["M101", "M102"],
    "F": ["M104"],
}

ROUND_MATCH_IDS = {
    "R32": [
        "M74", "M77", "M73", "M75",  # -> M89, M90
        "M83", "M84", "M81", "M82",  # -> M93, M94
        "M76", "M78", "M79", "M80",  # -> M91, M92
        "M86", "M88", "M85", "M87",  # -> M95, M96
    ],
    "R16": ["M89", "M90", "M93", "M94", "M91", "M92", "M95", "M96"],
    "QF": ["M97", "M98", "M99", "M100"],
    "SF": ["M101", "M102"],
    "F": ["M104"],
}

# Official 2026 knockout topology. The values are (next match, next slot).
OFFICIAL_FEEDS = {
    "M74": ("M89", 1), "M77": ("M89", 2),
    "M73": ("M90", 1), "M75": ("M90", 2),
    "M83": ("M93", 1), "M84": ("M93", 2),
    "M81": ("M94", 1), "M82": ("M94", 2),
    "M76": ("M91", 1), "M78": ("M91", 2),
    "M79": ("M92", 1), "M80": ("M92", 2),
    "M86": ("M95", 1), "M88": ("M95", 2),
    "M85": ("M96", 1), "M87": ("M96", 2),
    "M89": ("M97", 1), "M90": ("M97", 2),
    "M93": ("M98", 1), "M94": ("M98", 2),
    "M91": ("M99", 1), "M92": ("M99", 2),
    "M95": ("M100", 1), "M96": ("M100", 2),
    "M97": ("M101", 1), "M98": ("M101", 2),
    "M99": ("M102", 1), "M100": ("M102", 2),
    "M101": ("M104", 1), "M102": ("M104", 2),
}

# The completed 2026 Round-of-32 draw. These pairs let the app identify an API
# fixture without relying on the API's chronological ordering.
R32_FIXTURES = {
    "M73": ("South Africa", "Canada"),
    "M74": ("Germany", "Paraguay"),
    "M75": ("Netherlands", "Morocco"),
    "M76": ("Brazil", "Japan"),
    "M77": ("France", "Sweden"),
    "M78": ("Ivory Coast", "Norway"),
    "M79": ("Mexico", "Ecuador"),
    "M80": ("England", "DR Congo"),
    "M81": ("USA", "Bosnia and Herzegovina"),
    "M82": ("Belgium", "Senegal"),
    "M83": ("Portugal", "Croatia"),
    "M84": ("Spain", "Austria"),
    "M85": ("Switzerland", "Algeria"),
    "M86": ("Argentina", "Cape Verde"),
    "M87": ("Colombia", "Ghana"),
    "M88": ("Australia", "Egypt"),
}

FLAG_CODES = {
    "Mexico": "mx", "South Korea": "kr", "Czechia": "cz", "South Africa": "za",
    "Canada": "ca", "Switzerland": "ch", "Bosnia and Herzegovina": "ba", "Qatar": "qa",
    "Scotland": "gb-sct", "Brazil": "br", "Morocco": "ma", "Haiti": "ht",
    "USA": "us", "Australia": "au", "Türkiye": "tr", "Paraguay": "py",
    "Germany": "de", "Ivory Coast": "ci", "Ecuador": "ec", "Curaçao": "cw",
    "Sweden": "se", "Netherlands": "nl", "Japan": "jp", "Tunisia": "tn",
    "Belgium": "be", "Egypt": "eg", "Iran": "ir", "New Zealand": "nz",
    "Spain": "es", "Cape Verde": "cv", "Saudi Arabia": "sa", "Uruguay": "uy",
    "Norway": "no", "France": "fr", "Senegal": "sn", "Iraq": "iq",
    "Argentina": "ar", "Austria": "at", "Jordan": "jo", "Algeria": "dz",
    "Colombia": "co", "DR Congo": "cd", "Portugal": "pt", "Uzbekistan": "uz",
    "England": "gb-eng", "Ghana": "gh", "Panama": "pa", "Croatia": "hr",
}

# Kept as a plain-text fallback for places that cannot render HTML images.
FLAGS = {
    "Mexico": "🇲🇽", "South Korea": "🇰🇷", "Czechia": "🇨🇿", "South Africa": "🇿🇦",
    "Canada": "🇨🇦", "Switzerland": "🇨🇭", "Bosnia and Herzegovina": "🇧🇦", "Qatar": "🇶🇦",
    "Scotland": "🏴", "Brazil": "🇧🇷", "Morocco": "🇲🇦", "Haiti": "🇭🇹",
    "USA": "🇺🇸", "Australia": "🇦🇺", "Türkiye": "🇹🇷", "Paraguay": "🇵🇾",
    "Germany": "🇩🇪", "Ivory Coast": "🇨🇮", "Ecuador": "🇪🇨", "Curaçao": "🇨🇼",
    "Sweden": "🇸🇪", "Netherlands": "🇳🇱", "Japan": "🇯🇵", "Tunisia": "🇹🇳",
    "Belgium": "🇧🇪", "Egypt": "🇪🇬", "Iran": "🇮🇷", "New Zealand": "🇳🇿",
    "Spain": "🇪🇸", "Cape Verde": "🇨🇻", "Saudi Arabia": "🇸🇦", "Uruguay": "🇺🇾",
    "Norway": "🇳🇴", "France": "🇫🇷", "Senegal": "🇸🇳", "Iraq": "🇮🇶",
    "Argentina": "🇦🇷", "Austria": "🇦🇹", "Jordan": "🇯🇴", "Algeria": "🇩🇿",
    "Colombia": "🇨🇴", "DR Congo": "🇨🇩", "Portugal": "🇵🇹", "Uzbekistan": "🇺🇿",
    "England": "🏴", "Ghana": "🇬🇭", "Panama": "🇵🇦", "Croatia": "🇭🇷",
}


def flag(team):
    return FLAGS.get(team, "")


def flag_code(team):
    return FLAG_CODES.get(team, "")


# ----------------------------- persistence -----------------------------------
def load_data(path):
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def save_data(path, data):
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    os.replace(tmp, path)


def _normalise_github_repo(repo):
    """Return an ``owner/repository`` value from a secret or GitHub URL."""
    value = str(repo or "").strip()
    if not value:
        raise ValueError("GITHUB_REPO is empty.")

    if "://" in value:
        parsed = urlparse(value)
        if parsed.netloc.lower() not in {"github.com", "www.github.com"}:
            raise ValueError("GITHUB_REPO must be an owner/repository value or a github.com URL.")
        value = parsed.path

    value = value.strip("/")
    if value.endswith(".git"):
        value = value[:-4]
    pieces = [piece for piece in value.split("/") if piece]
    if len(pieces) != 2:
        raise ValueError(
            "GITHUB_REPO must look like 'owner/repository', for example "
            "'oscarcrease/World-Cup-Comp-Tracker'."
        )
    return "/".join(pieces)


def _github_headers(token, media="json"):
    accepts = {
        "json": "application/vnd.github+json",
        "object": "application/vnd.github.object+json",
        "raw": "application/vnd.github.raw+json",
    }
    return {
        "Authorization": f"Bearer {token}",
        "Accept": accepts.get(media, accepts["json"]),
        "X-GitHub-Api-Version": "2022-11-28",
        "User-Agent": "world-cup-comp-tracker",
    }


def _decode_json_bytes(raw, label):
    """Decode UTF-8 JSON with a useful error for empty or invalid responses."""
    if not raw or not raw.strip():
        raise ValueError(f"{label} is empty.")
    try:
        text = raw.decode("utf-8-sig")
    except UnicodeDecodeError as exc:
        raise ValueError(f"{label} is not UTF-8 text.") from exc
    try:
        payload = json.loads(text)
    except json.JSONDecodeError as exc:
        raise ValueError(
            f"{label} is not valid JSON (line {exc.lineno}, column {exc.colno})."
        ) from exc
    if not isinstance(payload, dict):
        raise ValueError(f"{label} must contain one JSON object.")
    return payload


def github_load_data(repo, token, path="data.json", branch="main"):
    """Load tracker JSON from GitHub, including files larger than 1 MB.

    Profile photos are embedded in ``data.json`` and can push it beyond the
    Contents API's one-megabyte inline-content limit. We first request the file
    metadata, then read the underlying Git blob by SHA. The blob endpoint always
    returns Base64 content and supports files up to 100 MB, so this path is much
    less fragile than calling ``response.json()`` on a raw-file response.
    """
    repo = _normalise_github_repo(repo)
    path = str(path or "data.json").strip().lstrip("/")
    branch = str(branch or "main").strip()
    if not path:
        raise ValueError("GITHUB_DATA_PATH is empty.")

    url = f"https://api.github.com/repos/{repo}/contents/{quote(path)}"
    metadata_response = requests.get(
        url,
        headers=_github_headers(token, media="object"),
        params={"ref": branch},
        timeout=30,
    )
    try:
        metadata_response.raise_for_status()
    except requests.HTTPError as exc:
        status = metadata_response.status_code
        detail = ""
        try:
            detail = (metadata_response.json().get("message") or "").strip()
        except ValueError:
            detail = metadata_response.text[:160].strip()
        suffix = f": {detail}" if detail else ""
        raise ValueError(
            f"GitHub could not read {repo}/{path} on branch {branch} "
            f"(HTTP {status}){suffix}"
        ) from exc
    try:
        metadata = metadata_response.json()
    except ValueError as exc:
        raise ValueError(
            f"GitHub returned an invalid metadata response for {repo}/{path}."
        ) from exc

    if not isinstance(metadata, dict) or metadata.get("type") not in (None, "file"):
        raise ValueError(f"GitHub path {repo}/{path} is not a file.")

    # Small files may still be supplied inline by the metadata endpoint.
    encoded = metadata.get("content") or ""
    if encoded and metadata.get("encoding") == "base64":
        try:
            raw = base64.b64decode(encoded, validate=False)
        except (ValueError, TypeError) as exc:
            raise ValueError(f"GitHub returned invalid Base64 for {repo}/{path}.") from exc
        return _decode_json_bytes(raw, f"GitHub file {repo}/{path}")

    sha = metadata.get("sha")
    if not sha:
        raise ValueError(f"GitHub did not return a file SHA for {repo}/{path}.")

    blob_url = metadata.get("git_url") or f"https://api.github.com/repos/{repo}/git/blobs/{sha}"
    blob_response = requests.get(
        blob_url,
        headers=_github_headers(token, media="json"),
        timeout=60,
    )
    try:
        blob_response.raise_for_status()
    except requests.HTTPError as exc:
        raise ValueError(
            f"GitHub found {repo}/{path}, but could not download its data blob "
            f"(HTTP {blob_response.status_code})."
        ) from exc
    try:
        blob = blob_response.json()
    except ValueError as exc:
        raise ValueError(f"GitHub returned invalid blob metadata for {repo}/{path}.") from exc
    blob_content = blob.get("content") if isinstance(blob, dict) else None
    if not blob_content:
        raise ValueError(f"GitHub returned an empty data blob for {repo}/{path}.")
    try:
        raw = base64.b64decode(blob_content, validate=False)
    except (ValueError, TypeError) as exc:
        raise ValueError(f"GitHub returned invalid blob content for {repo}/{path}.") from exc
    return _decode_json_bytes(raw, f"GitHub file {repo}/{path}")


def github_save_data(repo, token, data, path="data.json", branch="main",
                     message="Update World Cup tracker data"):
    """Commit JSON to GitHub. This makes Streamlit Cloud edits durable."""
    repo = _normalise_github_repo(repo)
    path = str(path or "data.json").strip().lstrip("/")
    branch = str(branch or "main").strip()
    url = f"https://api.github.com/repos/{repo}/contents/{quote(path)}"
    headers = _github_headers(token, media="json")
    object_headers = _github_headers(token, media="object")

    current = requests.get(url, headers=object_headers, params={"ref": branch}, timeout=30)
    if current.status_code == 404:
        sha = None
    else:
        current.raise_for_status()
        sha = current.json().get("sha")
        if not sha:
            raise ValueError(f"GitHub did not return a SHA for {repo}/{path}.")

    raw = json.dumps(data, indent=2, ensure_ascii=False).encode("utf-8")
    body = {
        "message": message,
        "content": base64.b64encode(raw).decode("ascii"),
        "branch": branch,
    }
    if sha:
        body["sha"] = sha

    response = requests.put(url, headers=headers, json=body, timeout=60)
    # A second browser session can update data.json between the GET and PUT.
    # Refresh the SHA and retry once instead of losing the admin's save.
    if response.status_code in (409, 422):
        latest = requests.get(url, headers=object_headers, params={"ref": branch}, timeout=30)
        latest.raise_for_status()
        latest_sha = latest.json().get("sha")
        if latest_sha:
            body["sha"] = latest_sha
            response = requests.put(url, headers=headers, json=body, timeout=60)
    response.raise_for_status()
    return response.json()


# ----------------------------- bracket model ---------------------------------
def _round_for_match_id(match_id):
    for rk, ids in ROUND_MATCH_IDS.items():
        if match_id in ids:
            return rk
    return None


def build_official_matches():
    """Return a fresh bracket using official FIFA match-number topology."""
    matches = {rk: [] for rk in ROUND_ORDER}
    for rk in ROUND_ORDER:
        for match_id in ROUND_MATCH_IDS[rk]:
            home, away = R32_FIXTURES.get(match_id, ("", ""))
            feed = OFFICIAL_FEEDS.get(match_id)
            matches[rk].append({
                "id": match_id,
                "fifa_match_number": int(match_id[1:]),
                "team1": home,
                "team2": away,
                "score1": None,
                "score2": None,
                "pen1": None,
                "pen2": None,
                "winner": None,
                "final": False,
                "in_play": False,
                "feeds_to": ({"round": _round_for_match_id(feed[0]),
                              "match": feed[0], "slot": feed[1]} if feed else None),
            })
    return matches


@lru_cache(maxsize=None)
def possible_teams_for_match(match_id):
    """All teams that can possibly appear in an official knockout match."""
    if match_id in R32_FIXTURES:
        return frozenset(R32_FIXTURES[match_id])
    sources = [src for src, (dest, _slot) in OFFICIAL_FEEDS.items() if dest == match_id]
    teams = set()
    for src in sources:
        teams.update(possible_teams_for_match(src))
    return frozenset(teams)


def _match_number(value):
    try:
        number = int(value)
    except (TypeError, ValueError):
        return None
    match_id = f"M{number}"
    return match_id if any(match_id in ids for ids in ROUND_MATCH_IDS.values()) else None


def identify_official_match(rk, team1="", team2="", match_number=None):
    """Identify a bracket slot using official number or team-path ancestry.

    This deliberately does not depend on API list order. Each national team has
    one unique route through the official bracket, so even one known team is
    normally enough to identify an upcoming fixture.
    """
    numbered = _match_number(match_number)
    if numbered in ROUND_MATCH_IDS.get(rk, []):
        return numbered

    known = {t for t in (team1, team2) if t and t in FLAG_CODES}
    if not known:
        return None

    candidates = []
    for match_id in ROUND_MATCH_IDS.get(rk, []):
        possible = possible_teams_for_match(match_id)
        if known.issubset(possible):
            candidates.append(match_id)
    return candidates[0] if len(candidates) == 1 else None


def normalize_penalty_score_fields(match):
    """Repair old API data where fullTime included shootout goals.

    football-data.org can return aggregate ``fullTime`` values such as 3-4 for
    a match that was 1-1 after play and 2-3 in the shootout. If subtraction
    yields the same non-negative play score for both teams, normalise it.
    """
    s1, s2 = match.get("score1"), match.get("score2")
    p1, p2 = match.get("pen1"), match.get("pen2")
    if None in (s1, s2, p1, p2):
        return False
    try:
        play1, play2 = int(s1) - int(p1), int(s2) - int(p2)
    except (TypeError, ValueError):
        return False
    if play1 >= 0 and play2 >= 0 and play1 == play2 and (s1 != s2):
        match["score1"], match["score2"] = play1, play2
        return True
    return False


def ensure_official_bracket(data):
    """Migrate old index-based brackets to official match-number slots.

    Existing scores, API ids, dates and manual edits are preserved whenever a
    slot can be identified from its teams. This also repairs the old penalty
    aggregate-score bug. Returns True when the in-memory data changed.
    """
    old = data.get("matches") or {}
    expected_ids = {rk: ROUND_MATCH_IDS[rk] for rk in ROUND_ORDER}
    current_ids = {rk: [m.get("id") for m in old.get(rk, [])] for rk in ROUND_ORDER}

    fresh = build_official_matches()
    migrated_any = False
    seen_targets = set()

    for rk in ROUND_ORDER:
        for source in old.get(rk, []):
            source = copy.deepcopy(source)
            match_id = source.get("id") if source.get("id") in ROUND_MATCH_IDS[rk] else None
            if not match_id:
                match_id = identify_official_match(
                    rk,
                    source.get("team1") or "",
                    source.get("team2") or "",
                    source.get("fifa_match_number") or source.get("matchday"),
                )
            if not match_id or (rk, match_id) in seen_targets:
                continue
            target = next(m for m in fresh[rk] if m["id"] == match_id)
            for key in (
                "api_id", "utc_date", "last_updated", "status", "duration",
                "score1", "score2", "pen1", "pen2", "winner", "final", "in_play",
            ):
                if key in source:
                    target[key] = source[key]
            # Preserve actual team names, never old placeholder labels.
            for key in ("team1", "team2"):
                value = source.get(key) or ""
                if value in FLAG_CODES:
                    target[key] = value
            normalize_penalty_score_fields(target)
            seen_targets.add((rk, match_id))
            migrated_any = True

    data["matches"] = fresh
    recompute_feeds(data, clear_stale=False)
    return current_ids != expected_ids or migrated_any


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
    winner = winner_of(m)
    if not winner:
        return None
    return m["team2"] if winner == m["team1"] else m["team1"]


def is_live(m):
    return bool(m.get("in_play")) or (
        m.get("score1") is not None and m.get("score2") is not None
        and not m.get("final", True) and not m.get("winner")
    )


# ------------------------- bracket propagation -------------------------------
def recompute_feeds(data, clear_stale=True):
    """Push winners into their exact official downstream slots.

    Source markers let a changed result clear only the slot it previously
    populated, without wiping fixtures supplied directly by the live API.
    """
    for rk in ROUND_ORDER:
        for match in data["matches"].get(rk, []):
            feed = match.get("feeds_to")
            if not feed:
                continue
            target = _find(data, feed["round"], feed["match"])
            if target is None:
                continue
            field = "team1" if feed["slot"] == 1 else "team2"
            source_field = f"{field}_source"
            winner = winner_of(match)
            if winner:
                target[field] = winner
                target[source_field] = match["id"]
            elif clear_stale and target.get(source_field) == match["id"]:
                target[field] = ""
                target.pop(source_field, None)


def set_match(data, rk, match_id, team1, team2, score1, score2, winner=None,
              final=True, pen1=None, pen2=None):
    ensure_official_bracket(data)
    match = _find(data, rk, match_id)
    if match is None:
        raise KeyError(f"No match {rk}/{match_id}")
    match.update({
        "team1": team1,
        "team2": team2,
        "score1": score1,
        "score2": score2,
        "pen1": pen1,
        "pen2": pen2,
        "in_play": False,
        "final": bool(final) and score1 is not None and score2 is not None,
    })
    match["winner"] = winner if winner in (team1, team2) else None
    recompute_feeds(data, clear_stale=True)
    return match


# --------------------------- team statuses -----------------------------------
def _score_string(match, winner):
    s1, s2 = match.get("score1"), match.get("score2")
    if s1 is None or s2 is None:
        return None
    ws, ls = (s1, s2) if winner == match["team1"] else (s2, s1)
    p1, p2 = match.get("pen1"), match.get("pen2")
    if p1 is not None and p2 is not None:
        wp, lp = (p1, p2) if winner == match["team1"] else (p2, p1)
        return f"{ws}–{ls} ({wp}–{lp} pens)"
    return f"{ws}–{ls}"


def compute_team_statuses(data):
    teams = set(all_teams(data))
    status = {
        t: {"status": "active", "by": None, "score": None, "round": None, "stage": None}
        for t in teams
    }
    for team in data.get("group_stage_out", []):
        if team in status:
            status[team] = {
                "status": "out", "by": None, "score": None,
                "round": None, "stage": "Group stage",
            }
    for rk in ROUND_ORDER:
        for match in data["matches"].get(rk, []):
            if not match_decided(match):
                continue
            winner, loser = winner_of(match), loser_of(match)
            if loser in status:
                status[loser] = {
                    "status": "out",
                    "by": winner,
                    "score": _score_string(match, winner),
                    "round": round_name(data, rk),
                    "stage": None,
                }
    return status


def player_summary(data, statuses, player):
    teams = data["players"].get(player, [])
    alive = sum(1 for t in teams if statuses.get(t, {}).get("status") == "active")
    return {"alive": alive, "total": len(teams), "teams": teams}


def champion(data):
    return winner_of(data["matches"]["F"][0])
