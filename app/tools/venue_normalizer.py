from app.tools.db import get_connection

def normalize_venue_name(venue: str) -> str:
    if not venue:
        return venue
    venue = venue.lower().strip()
    if "," in venue:
        venue = venue.split(",")[0].strip()
    return venue

def get_matching_venues(cursor, venue: str):
    canonical = normalize_venue_name(venue)
    cursor.execute("SELECT DISTINCT venue FROM matches")
    all_venues = [row[0] for row in cursor.fetchall()]
    return [v for v in all_venues if normalize_venue_name(v) == canonical]

def compute_venue_stats(venue: str, min_matches: int = 5):
    conn = get_connection()
    cursor = conn.cursor()
    matched_venues = get_matching_venues(cursor, venue)

    if not matched_venues:
        conn.close()
        return {
            "average_first_innings_score": None,
            "chasing_win_percentage": None,
            "sample_size": 0,
            "is_reliable": False,
        }

    cursor.execute(
        f"""
        SELECT AVG(i.total_runs)
        FROM innings_summary i
        JOIN matches m ON i.match_id = m.match_id
        WHERE m.venue IN ({",".join(["?"] * len(matched_venues))})
        AND i.id IN (
            SELECT MIN(id) FROM innings_summary GROUP BY match_id
        )
        """,
        matched_venues,
    )
    avg_first = cursor.fetchone()[0]

    cursor.execute(
        f"""
        SELECT COUNT(*) FROM matches
        WHERE venue IN ({",".join(["?"] * len(matched_venues))})
        """,
        matched_venues,
    )
    total_matches = cursor.fetchone()[0] or 0

    cursor.execute(
        f"""
        SELECT COUNT(*)
        FROM matches m
        JOIN innings_summary i ON m.match_id = i.match_id
        WHERE m.venue IN ({",".join(["?"] * len(matched_venues))})
        AND i.id NOT IN (
            SELECT MIN(id) FROM innings_summary GROUP BY match_id
        )
        AND m.winner = i.batting_team
        """,
        matched_venues,
    )
    chasing_wins = cursor.fetchone()[0] or 0

    conn.close()

    chasing_pct = (chasing_wins / total_matches * 100) if total_matches else None
    return {
        "average_first_innings_score": round(avg_first, 2) if avg_first else None,
        "chasing_win_percentage": round(chasing_pct, 2) if chasing_pct is not None else None,
        "sample_size": total_matches,
        "is_reliable": total_matches >= min_matches,
    }
