import json
from pathlib import Path
from collections import defaultdict
from app.tools.db import get_connection, create_tables

RAW_JSON_PATH = Path("data/raw/t20s_json")

def parse_match(file_path: Path) -> dict:
    with open(file_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    info = data.get("info", {})
    match_id = file_path.stem
    date = (info.get("dates") or [""])[0]
    teams = info.get("teams", ["", ""])
    venue = info.get("venue", "")
    outcome = info.get("outcome", {})
    winner = outcome.get("winner")

    toss = info.get("toss", {})
    toss_winner = toss.get("winner")
    toss_decision = toss.get("decision")

    innings_list = []
    player_stats = defaultdict(lambda: {
        "runs_scored": 0, "balls_faced": 0,
        "wickets_taken": 0, "balls_bowled": 0, "runs_conceded": 0,
        "team": ""
    })

    for idx, innings in enumerate(data.get("innings", []), start=1):
        batting_team = innings.get("team", "")
        overs_list = innings.get("overs", [])
        total_runs = 0
        wickets = 0
        last_over = 0

        for over_block in overs_list:
            over_no = over_block.get("over", 0)
            deliveries = over_block.get("deliveries", [])
            last_over = max(last_over, over_no)

            for ball in deliveries:
                batter = ball.get("batter", "")
                bowler = ball.get("bowler", "")
                runs = ball.get("runs", {})
                batter_runs = runs.get("batter", 0)
                total_ball = runs.get("total", 0)

                total_runs += total_ball
                player_stats[batter]["team"] = batting_team
                player_stats[batter]["runs_scored"] += batter_runs

                wide = ball.get("extras", {}).get("wides", 0)
                if wide == 0:
                    player_stats[batter]["balls_faced"] += 1

                bowling_team = teams[1] if batting_team == teams[0] else teams[0]
                player_stats[bowler]["team"] = bowling_team
                player_stats[bowler]["runs_conceded"] += total_ball
                if wide == 0:
                    player_stats[bowler]["balls_bowled"] += 1

                if "wickets" in ball:
                    for w in ball["wickets"]:
                        wickets += 1
                        if w.get("kind") != "run out":
                            player_stats[bowler]["wickets_taken"] += 1

        innings_list.append({
            "batting_team": batting_team,
            "total_runs": total_runs,
            "wickets": wickets,
            "overs": last_over + 1,
            "innings_number": idx,
        })

    player_rows = []
    for player, stats in player_stats.items():
        if not player:
            continue
        player_rows.append({
            "player": player,
            "team": stats["team"],
            "runs_scored": stats["runs_scored"],
            "balls_faced": stats["balls_faced"],
            "wickets_taken": stats["wickets_taken"],
            "balls_bowled": stats["balls_bowled"],
            "runs_conceded": stats["runs_conceded"],
        })

    return {
        "match": {
            "match_id": match_id,
            "date": date,
            "team1": teams[0] if len(teams) > 0 else "",
            "team2": teams[1] if len(teams) > 1 else "",
            "venue": venue,
            "toss_winner": toss_winner,
            "toss_decision": toss_decision,
            "winner": winner,
        },
        "innings": innings_list,
        "players": player_rows,
    }

def ingest():
    create_tables()
    conn = get_connection()
    cur = conn.cursor()
    files = sorted(RAW_JSON_PATH.glob("*.json"))
    print(f"Found {len(files)} match files...")

    for i, fp in enumerate(files, 1):
        try:
            parsed = parse_match(fp)
        except Exception as e:
            continue
        m = parsed["match"]
        cur.execute("""
            INSERT OR REPLACE INTO matches
            (match_id, date, team1, team2, venue, toss_winner, toss_decision, winner)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (m["match_id"], m["date"], m["team1"], m["team2"], m["venue"], m["toss_winner"], m["toss_decision"], m["winner"]))

        for inn in parsed["innings"]:
            cur.execute("""
                INSERT OR IGNORE INTO innings_summary
                (match_id, batting_team, total_runs, wickets, overs, innings_number)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (m["match_id"], inn["batting_team"], inn["total_runs"], inn["wickets"], inn["overs"], inn["innings_number"]))

        for p in parsed["players"]:
            cur.execute("""
                INSERT OR IGNORE INTO player_performances
                (match_id, player, team, runs_scored, balls_faced, wickets_taken, balls_bowled, runs_conceded)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (m["match_id"], p["player"], p["team"], p["runs_scored"], p["balls_faced"], p["wickets_taken"], p["balls_bowled"], p["runs_conceded"]))

        if i % 500 == 0:
            conn.commit()

    conn.commit()
    conn.close()
    print(f"[OK] Ingestion complete -- {len(files)} matches loaded.")

if __name__ == "__main__":
    ingest()
