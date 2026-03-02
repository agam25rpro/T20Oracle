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

def fetch_current_matches():
    data = _get("currentMatches")
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
            "team_info": m.get("teamInfo", []),
        })
    return results

def get_live_team_form(team1: str, team2: str):
    result = {
        "api_available": bool(CRICAPI_KEY),
        "team1_recent": [],
        "team2_recent": [],
    }
    if not CRICAPI_KEY:
        return result

    all_matches = fetch_current_matches()
    for team, key in [(team1, "team1_recent"), (team2, "team2_recent")]:
        team_lower = team.lower()
        for m in all_matches:
            teams_lower = [t.lower() for t in m.get("teams", [])]
            if not any(team_lower in t for t in teams_lower):
                continue
            scores = []
            for s in m.get("score", []):
                scores.append(f"{s.get('inning', '?')}: {s.get('r', 0)}/{s.get('w', 0)} ({s.get('o', 0)} ov)")
            result[key].append({
                "match": m.get("name", ""),
                "status": m.get("status", ""),
                "match_type": m.get("match_type", ""),
                "venue": m.get("venue", ""),
                "date": m.get("date", ""),
                "scores": scores,
            })
    return result