import json
from app.graph.state import GraphState
from app.tools.venue_normalizer import compute_venue_stats
from app.tools.api_clients import safe_generate

def venue_agent(state: GraphState) -> GraphState:
    venue = state["venue"]
    toss_winner = state.get("toss_winner")
    batting_first = state.get("batting_first")

    evidence = compute_venue_stats(venue, min_matches=5)

    prompt = f"""You are a professional cricket venue analyst.
Use ONLY the factual evidence below. Do NOT invent statistics.
Venue Evidence:
{json.dumps(evidence, indent=2)}

Reliability Rules:
- If sample_size < 5 OR is_reliable is False:
  • State that venue data is limited.
  • Reduce certainty in conclusions.
  • Avoid strong claims.

Match Context:
- Toss winner: {toss_winner}
- Batting first: {batting_first}

Task:
Write a concise analytical paragraph (3-5 sentences) covering:
1. Whether the pitch favors batting first or chasing
2. Competitive score range at this venue
3. How the toss decision may influence the match
4. Mention uncertainty if data is limited
Return ONLY plain text paragraph."""

    state["venue_report"] = safe_generate(prompt)
    return state