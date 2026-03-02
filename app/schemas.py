from pydantic import BaseModel
from typing import Optional

class PredictionRequest(BaseModel):
    team1: str
    team2: str
    venue: str
    toss_winner: Optional[str] = None
    batting_first: Optional[str] = None

class PredictionResponse(BaseModel):
    predicted_winner: str
    confidence: float
    reasoning: str
