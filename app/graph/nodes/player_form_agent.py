import json
from app.graph.state import GraphState
from app.tools.db import get_connection
from app.tools.cricapi_client import get_live_team_form
from app.tools.api_clients import safe_generate

def fetch_recent_match_ids(team: str, limit: int = 5) -> list[str]:
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("""
        SELECT match_id FROM matches
        WHERE (team1 = ? OR team2 = ?) AND winner IS NOT NULL
        ORDER BY date DESC LIMIT ?
    """, (team, team, limit))
    ids = [row[0] for row in cur.fetchall()]
    conn.close()
    return ids

def fetch_top_batters(team: str, match_ids: list[str], top_n: int = 5) -> list[dict]:
    if not match_ids:
        return []
    conn = get_connection()
    cur = conn.cursor()
    placeholders = ",".join(["?"] * len(match_ids))
    cur.execute(f"""
        SELECT player, COUNT(DISTINCT match_id) AS matches, SUM(runs_scored) AS total_runs,
               SUM(balls_faced) AS total_balls, ROUND(AVG(runs_scored), 1) AS avg_runs
        FROM player_performances
        WHERE team = ? AND match_id IN ({placeholders}) AND balls_faced > 0
        GROUP BY player ORDER BY total_runs DESC LIMIT ?
    """, [team] + match_ids + [top_n])
    batters = []
    for player, matches, runs, balls, avg in cur.fetchall():
        sr = round(runs / balls * 100, 1) if balls else 0
        batters.append({"player": player, "matches": matches, "runs": runs, "balls": balls, "avg_runs": avg, "strike_rate": sr})
    conn.close()
    return batters

def fetch_top_bowlers(team: str, match_ids: list[str], top_n: int = 5) -> list[dict]:
    if not match_ids:
        return []
    conn = get_connection()
    cur = conn.cursor()
    placeholders = ",".join(["?"] * len(match_ids))
    cur.execute(f"""
        SELECT player, COUNT(DISTINCT match_id) AS matches, SUM(wickets_taken) AS total_wickets,
               SUM(balls_bowled) AS total_balls, SUM(runs_conceded) AS total_runs
        FROM player_performances
        WHERE team = ? AND match_id IN ({placeholders}) AND balls_bowled > 0
        GROUP BY player ORDER BY total_wickets DESC, total_runs ASC LIMIT ?
    """, [team] + match_ids + [top_n])
    bowlers = []
    for player, matches, wickets, balls, runs in cur.fetchall():
        overs = balls / 6
        econ = round(runs / overs, 2) if overs > 0 else 0
        bowlers.append({"player": player, "matches": matches, "wickets": wickets, "balls_bowled": balls, "economy": econ})
    conn.close()
    return bowlers

def player_form_agent(state: GraphState) -> GraphState:
    team1 = state.get("team1", "")
    team2 = state.get("team2", "")

    ids1 = fetch_recent_match_ids(team1, limit=5)
    ids2 = fetch_recent_match_ids(team2, limit=5)

    db_evidence = {
        team1: {"source": "historical_database", "recent_matches_used": len(ids1), "top_batters": fetch_top_batters(team1, ids1), "top_bowlers": fetch_top_bowlers(team1, ids1)},
        team2: {"source": "historical_database", "recent_matches_used": len(ids2), "top_batters": fetch_top_batters(team2, ids2), "top_bowlers": fetch_top_bowlers(team2, ids2)},
    }

    try:
        live_data = get_live_team_form(team1, team2)
    except Exception:
        live_data = {"api_available": False, "team1_recent": [], "team2_recent": []}

    live_section = ""
    if live_data.get("team1_recent") or live_data.get("team2_recent"):
        live_section = f"""
LIVE / VERY RECENT MATCH DATA (from CricAPI):
{json.dumps({team1 + " (recent)": live_data.get("team1_recent", []), team2 + " (recent)": live_data.get("team2_recent", [])}, indent=2)}
Note: This live data may include matches completed in the last few days that are NOT yet in the historical database. Prioritise this for assessing CURRENT form."""
    else:
        live_section = "\n(No live/very recent match data available from API.)\n"

    prompt = f"""You are a professional cricket player-form analyst.
Use ONLY the data below. Do NOT invent player names or statistics.
HISTORICAL PERFORMANCE DATA (last 5 matches each, from database):
{json.dumps(db_evidence, indent=2)}
{live_section}
Task:
Write a concise paragraph (4-6 sentences) analyzing:
1. Key batters in form for each team (mention actual runs, strike rate)
2. Key bowlers in form for each team (mention wickets, economy)
3. Which player matchups could decide the contest
4. If live data is available, highlight any recent form changes
5. If data is limited for a team, state this clearly
Return ONLY plain text paragraph."""

    try:
        report = safe_generate(prompt, temperature=0.6)
    except Exception:
        report = "Player form analysis unavailable (LLM call failed). The stats and venue reports should be used instead."

    state["player_form_report"] = report
    return state