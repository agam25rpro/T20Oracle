from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.schemas import PredictionRequest, PredictionResponse
from app.services.prediction_service import run_prediction
from app.tools.db import get_connection

app = FastAPI(title="T20 Oracle")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
def root():
    return {"message": "T20 Oracle is running"}

@app.get("/teams")
def list_teams():
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT DISTINCT team1 FROM matches UNION SELECT DISTINCT team2 FROM matches")
    teams = sorted([row[0] for row in cur.fetchall() if row[0]])
    conn.close()
    return teams

@app.get("/venues")
def list_venues():
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT DISTINCT venue FROM matches")
    venues = sorted([row[0] for row in cur.fetchall() if row[0]])
    conn.close()
    return venues

@app.post("/predict", response_model=PredictionResponse)
def predict_match(req: PredictionRequest):
    state = {
        "team1": req.team1,
        "team2": req.team2,
        "venue": req.venue,
        "toss_winner": req.toss_winner,
        "batting_first": req.batting_first,
    }
    result = run_prediction(state)
    return PredictionResponse(
        predicted_winner=result.get("predicted_winner", "Unknown"),
        confidence=result.get("confidence", 50.0),
        reasoning=result.get("reasoning", ""),
    )
