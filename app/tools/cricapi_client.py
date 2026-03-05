import requests
from app.config import CRICAPI_KEY

BASE_URL = "https://api.cricapi.com/v1"
TIMEOUT = 15

def _get(endpoint, params=None):
    if not CRICAPI_KEY:
        return None
    params = params or {}
    params["apikey"] = CRICAPI_KEY
    try:
        resp = requests.get(f"{BASE_URL}/{endpoint}", params=params, timeout=TIMEOUT)
        if resp.status_code != 200:
            return None
        data = resp.json()
        if data.get("status") != "success":
            return None
        return data
    except Exception:
        return None

def _fetch_from_endpoint(endpoint, params=None):
    """Fetch matches from any CricAPI endpoint and normalize the response."""
    data = _get(endpoint, params)
    if not data:
        return []
    matches = data.get("data", [])
    results = []
    for m in matches:
        if not m.get("matchType"):
            continue
        results.append({
            "id": m.get("id", ""),
            "name": m.get("name", ""),
            "status": m.get("status", ""),
            "match_type": m.get("matchType", ""),
            "venue": m.get("venue", ""),
            "date": m.get("date", ""),
            "teams": m.get("teams", []),
            "score": m.get("score", []),
        })
    return results


def _is_exact_senior_team(api_team_name: str, requested_team: str) -> bool:
    """Return True only if the API team name exactly matches the requested team.
    This filters out 'India A', 'India U19', 'India Women', 'England Lions', etc."""
    return api_team_name.strip().lower() == requested_team.strip().lower()


def _team_in_match(match_teams: list, requested_team: str) -> bool:
    """Check if the requested senior team is playing in this match."""
    return any(_is_exact_senior_team(t, requested_team) for t in match_teams)


def _extract_team_matches(all_matches: list, team: str, limit: int = 3) -> list:
    """Filter matches for a specific senior team and return up to `limit` results."""
    seen_ids = set()
    team_matches = []
    for m in all_matches:
        mid = m.get("id", "")
        if mid in seen_ids:
            continue
        if not _team_in_match(m.get("teams", []), team):
            continue
        scores = m.get("score") or []
        score_lines = []
        for s in scores:
            score_lines.append(
                f"{s.get('inning', '?')}: {s.get('r', 0)}/{s.get('w', 0)} ({s.get('o', 0)} ov)"
            )
        if score_lines:
            seen_ids.add(mid)
            team_matches.append({
                "match": m.get("name", ""),
                "status": m.get("status", ""),
                "match_type": m.get("match_type", ""),
                "venue": m.get("venue", ""),
                "date": m.get("date", ""),
                "scores": score_lines,
            })
        if len(team_matches) >= limit:
            break
    return team_matches


def get_live_team_form(team1: str, team2: str):
    """Fetch the 3 most recent senior-team matches for each team.
    
    Combines two CricAPI endpoints for maximum coverage:
      1. /currentMatches  – live & recently completed tournament matches (e.g. T20 WC)
      2. /matches          – broader historical list (paginated)
    Results are deduplicated by match ID.
    """
    result = {
        "api_available": bool(CRICAPI_KEY),
        "team1_recent": [],
        "team2_recent": [],
    }
    if not CRICAPI_KEY:
        return result

    # --- Source 1: currentMatches (live / ongoing tournaments) ---
    current = _fetch_from_endpoint("currentMatches")

    # --- Source 2: paginated /matches (broader recent history) ---
    historical = []
    max_pages = 8  # up to 200 matches
    for page in range(max_pages):
        batch = _fetch_from_endpoint("matches", {"offset": page * 25})
        if not batch:
            break
        historical.extend(batch)

    # Merge: current matches first (higher priority), then historical
    all_matches = current + historical

    for team, key in [(team1, "team1_recent"), (team2, "team2_recent")]:
        result[key] = _extract_team_matches(all_matches, team, limit=3)

    return result