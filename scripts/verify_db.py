"""Quick verification of the database contents."""

import sqlite3
import sys
from pathlib import Path

DB = Path("data/processed/cricket.db")

if not DB.exists():
    print(f"DB not found at {DB}")
    sys.exit(1)

conn = sqlite3.connect(DB)
c = conn.cursor()

# Tables
c.execute("SELECT name FROM sqlite_master WHERE type='table'")
tables = [r[0] for r in c.fetchall()]
print(f"Tables: {tables}")

# Counts
for table in ["matches", "innings_summary", "player_performances"]:
    c.execute(f"SELECT COUNT(*) FROM {table}")
    print(f"  {table}: {c.fetchone()[0]} rows")

# Toss data
c.execute("SELECT COUNT(*) FROM matches WHERE toss_winner IS NOT NULL")
print(f"\nMatches with toss data: {c.fetchone()[0]}")

# Sample player data
c.execute("""
    SELECT player, team, runs_scored, balls_faced, wickets_taken
    FROM player_performances
    ORDER BY runs_scored DESC
    LIMIT 5
""")
print("\nTop 5 batting performances (single match):")
for r in c.fetchall():
    sr = round(r[2] / r[3] * 100, 1) if r[3] else 0
    print(f"  {r[0]} ({r[1]}): {r[2]} runs off {r[3]} balls (SR {sr}), {r[4]} wkt")

# Verify no duplicate innings
c.execute("""
    SELECT match_id, innings_number, COUNT(*) as cnt
    FROM innings_summary
    GROUP BY match_id, innings_number
    HAVING cnt > 1
""")
dupes = c.fetchall()
if dupes:
    print(f"\nWARNING: {len(dupes)} duplicate innings found!")
else:
    print("\nNo duplicate innings -- schema constraints working")

conn.close()
print("\nVerification complete!")
