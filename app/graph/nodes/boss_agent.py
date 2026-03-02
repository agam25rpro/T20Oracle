import json
from app.graph.state import GraphState
from app.tools.api_clients import safe_generate
from app.utils.logger import log

def boss_agent(state: GraphState) -> GraphState:
    team1 = state["team1"]
    team2 = state["team2"]
    venue = state["venue"]
    toss_winner = state.get("toss_winner")
    batting_first = state.get("batting_first")

    stats_report = state.get("stats_report", "")
    venue_report = state.get("venue_report", "")
    player_form_report = state.get("player_form_report", "")

    prompt = f"""You are the chief cricket match strategist responsible for the final prediction.
Match Details:
- Teams: {team1} vs {team2}
- Venue: {venue}
- Toss winner: {toss_winner}
- Batting first: {batting_first}

Analyst Reports:
[Statistics Analyst]
{stats_report}

[Venue Analyst]
{venue_report}

[Player Form Analyst]
{player_form_report}

Instructions:
1. Base reasoning ONLY on the analyst reports and match context above.
2. Do NOT invent statistics or use external knowledge.
3. Weigh all three reports: team stats, venue conditions, AND player form.
4. Pick the most likely winner from ONLY these two teams: "{team1}" or "{team2}".
5. Give a realistic confidence percentage (50–90 range).
6. Provide concise strategic reasoning in 2–4 sentences.

Return STRICT JSON (no markdown, no code fences):
{{
  "predicted_winner": "...",
  "confidence": 0,
  "reasoning": "..."
}}"""

    text = safe_generate(prompt, temperature=0.5)

    try:
        result = json.loads(text)
    except json.JSONDecodeError:
        if "```json" in text:
            start = text.find("```json") + 7
            end = text.find("```", start)
            text = text[start:end].strip()
        elif "```" in text:
            start = text.find("```") + 3
            end = text.find("```", start)
            text = text[start:end].strip()
        else:
            try:
                start = text.find("{")
                end = text.rfind("}") + 1
                text = text[start:end]
            except Exception:
                pass
        
        try:
            result = json.loads(text)
        except json.JSONDecodeError:
            result = {
                "predicted_winner": "Unknown",
                "confidence": 50,
                "reasoning": "Unable to parse LLM response.",
            }

    state["predicted_winner"] = result.get("predicted_winner", "Unknown")
    state["confidence"] = float(result.get("confidence", 50))
    state["reasoning"] = result.get("reasoning", "Unable to determine")

    log.info(f"Prediction: {state['predicted_winner']} ({state['confidence']:.0f}% confidence)")
    return state