from typing import TypedDict, Optional

class GraphState(TypedDict, total=False):
    query: str
    team1: str
    team2: str
    venue: str
    toss_winner: Optional[str]
    batting_first: Optional[str]
    stats_report: Optional[str]
    venue_report: Optional[str]
    player_form_report: Optional[str]
    predicted_winner: Optional[str]
    confidence: Optional[float]
    reasoning: Optional[str]