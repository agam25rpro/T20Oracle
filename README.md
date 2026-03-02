# 🏏 T20 Oracle

A **multi-agent AI system** that predicts T20 cricket match outcomes using historical data, venue analysis, and player form — powered by LLMs (Google Gemini + Groq).

## Architecture

```
┌──────────────┐     ┌──────────────┐
│ Stats Agent  │     │ Venue Agent  │    ← independent analysts
└──────┬───────┘     └──────┬───────┘
       │                    │
       └────────┬───────────┘
                ▼
       ┌──────────────────┐
       │ Player Form Agent│    ← reads real player data from DB
       └────────┬─────────┘
                ▼
       ┌──────────────────┐
       │    Boss Agent    │    ← synthesises all reports → final prediction
       └──────────────────┘
```

Each agent queries a **SQLite database** (4,900+ T20 matches from [Cricsheet](https://cricsheet.org/)) and asks an LLM to interpret the evidence.

## Quick Start

```bash
# 1. Install dependencies
pip install -r requirements.txt

# 2. Create .env file
cp .env.example .env   # then add your API keys

# 3. Ingest match data into SQLite
python scripts/ingest.py

# 4. Extract team/venue lists for the API
python scripts/extract_metadata.py

# 5. Run the server
python run.py

# 6. Open the Frontend UI
Simply open `frontend/index.html` in any web browser!
```

Server starts at `http://localhost:8000`.

## Premium Frontend UI
We have created a beautiful, modern web frontend inspired by clean, professional startup websites (like Stripe or Vercel). 
To use it:
1. Ensure the Python API `python run.py` is running in the background.
2. Double-click `frontend/index.html` to open it in your browser.
3. The UI explains exactly how the 4 agents work together and lets you run live predictions seamlessly.

## API Endpoints

| Method | Path       | Description                          |
|--------|-----------|--------------------------------------|
| GET    | `/`       | Health check                         |
| GET    | `/teams`  | List all teams in the database       |
| GET    | `/venues` | List all venues in the database      |
| POST   | `/predict`| Run prediction pipeline              |

### POST `/predict` — Example

```json
{
  "team1": "India",
  "team2": "Australia",
  "venue": "Eden Gardens, Kolkata",
  "toss_winner": "India",
  "batting_first": "India"
}
```

Response:
```json
{
  "predicted_winner": "India",
  "confidence": 72.0,
  "reasoning": "India's strong recent form (4/5 wins) combined with..."
}
```

## Database Schema

- **matches** — match metadata + toss info + winner
- **innings_summary** — per-innings totals (runs, wickets, overs)
- **player_performances** — per-player per-match stats (runs, balls, wickets, economy)

## Evaluate

Run the evaluation harness to test predictions against historical outcomes:

```bash
python scripts/evaluate_model.py        # run evaluation
python scripts/evaluate_model.py view   # view past results
```

## Environment Variables

| Variable          | Description                                    |
|-------------------|------------------------------------------------|
| `GEMINI_API_KEYS` | Comma-separated Google Gemini API keys          |
| `GROQ_API_KEY`    | Groq API key (for Llama models)                |
| `GEMINI_MODELS`   | Comma-separated model names (priority order)   |
| `DB_PATH`         | Path to SQLite database (default: `data/cricket.db`) |
| `CRICAPI_KEY`     | CricketData.org API key (optional)             |
