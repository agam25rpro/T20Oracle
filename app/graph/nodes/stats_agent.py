import json
from app.graph.state import GraphState
from app.tools.db import get_connection
from app.tools.api_clients import safe_generate

def fetch_head_to_head(team1: str, team2: str) -> dict:
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("""
        SELECT winner, COUNT(*) as wins
        FROM matches
        WHERE ((team1 = ? AND team2 = ?) OR (team1 = ? AND team2 = ?))
          AND winner IS NOT NULL
        GROUP BY winner
    """, (team1, team2, team2, team1))
    result = {team1: 0, team2: 0, "total": 0}
    for winner, count in cur.fetchall():
        if winner in result:
            result[winner] = count
        result["total"] += count
    conn.close()
    return result

def fetch_recent_form(team: str, limit: int = 5) -> list[dict]:
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("""
        SELECT team1, team2, venue, winner, date
        FROM matches
        WHERE (team1 = ? OR team2 = ?)
          AND winner IS NOT NULL
        ORDER BY date DESC
        LIMIT ?
    """, (team, team, limit))
    matches = []
    for team1, team2, venue, winner, date in cur.fetchall():
        opponent = team2 if team1 == team else team1
        matches.append({
            "opponent": opponent,
            "venue": venue,
            "result": "Won" if winner == team else "Lost",
            "date": date,
        })
    conn.close()
    return matches

def fetch_toss_stats(team1: str, team2: str) -> dict:
    conn = get_connection()
    cur = conn.cursor()
    stats = {}
    for team in [team1, team2]:
        cur.execute("""
            SELECT COUNT(*) as total, SUM(CASE WHEN winner = ? THEN 1 ELSE 0 END) as wins
            FROM matches
            WHERE (team1 = ? OR team2 = ?) AND winner IS NOT NULL AND toss_decision IS NOT NULL
        """, (team, team, team))
        row = cur.fetchone()
        cur.execute("""
            SELECT SUM(CASE WHEN toss_winner = ? THEN 1 ELSE 0 END) as toss_wins
            FROM matches
            WHERE (team1 = ? OR team2 = ?) AND toss_winner IS NOT NULL
        """, (team, team, team))
        toss_row = cur.fetchone()
        stats[team] = {
            "total_matches": row[0] if row else 0,
            "total_wins": row[1] if row else 0,
            "toss_wins": toss_row[0] if toss_row else 0,
        }
    conn.close()
    return stats

def stats_agent(state: GraphState) -> GraphState:
    team1 = state["team1"]
    team2 = state["team2"]
    h2h = fetch_head_to_head(team1, team2)
    form1 = fetch_recent_form(team1)
    form2 = fetch_recent_form(team2)
    toss = fetch_toss_stats(team1, team2)

    evidence = {
        "head_to_head": h2h,
        "recent_form": {team1: form1, team2: form2},
        "toss_stats": toss,
    }

    prompt = f"""You are a professional cricket statistics analyst.
Use ONLY the evidence below. Do NOT invent numbers.
Evidence:
{json.dumps(evidence, indent=2)}

Task:
Write a concise analytical paragraph (4-6 sentences) comparing:
1. Head-to-head historical dominance
2. Recent form (last 5 matches each)
3. Toss win tendencies and impact
Mention key numbers explicitly.
Return ONLY plain text paragraph."""

    state["stats_report"] = safe_generate(prompt)
    return state