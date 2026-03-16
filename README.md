# T20 Oracle

![Python](https://img.shields.io/badge/python-3.10+-blue.svg)
![FastAPI](https://img.shields.io/badge/FastAPI-0.100+-05998b.svg?style=flat&logo=fastapi&logoColor=white)
![LangGraph](https://img.shields.io/badge/LangGraph-Build-orange)
![Gemini](https://img.shields.io/badge/Google%20Gemini-AI-blue)
![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)
![Repo Size](https://img.shields.io/github/repo-size/agam25rpro/T20Oracle)
![Last Commit](https://img.shields.io/github/last-commit/agam25rpro/T20Oracle)

A **multi-agent AI system** that predicts T20 cricket match outcomes using historical data, venue analysis, real-time player form, and LLM-powered reasoning — powered by Google Gemini, Groq (Llama), and LangGraph.

---

## Table of Contents

- [Architecture Overview](#architecture-overview)
- [How It Works](#how-it-works)
  - [Agent Pipeline](#agent-pipeline)
  - [Data Sources](#data-sources)
  - [LLM Provider Strategy](#llm-provider-strategy)
- [Database Schema](#database-schema)
- [Project Structure](#project-structure)
- [API Endpoints](#api-endpoints)
- [Quick Start](#quick-start)
- [Environment Variables](#environment-variables)
- [Deployment](#deployment)

---

## Architecture Overview

T20 Oracle uses a **panel-of-experts** approach. Instead of one LLM trying to predict everything at once, four specialized agents each analyze a different dimension of the match and report their findings to a Boss Agent who synthesizes the final prediction.

```
                        ┌─────────────────────────────────┐
                        │         User Request            │
                        │  (team1, team2, venue, toss)    │
                        └───────────────┬─────────────────┘
                                        │
                                        ▼
                                ┌───────────────┐
                                │  Stats Agent  │
                                │ (H2H, Form,   │
                                │  Toss Stats)  │
                                └───────┬───────┘
                                        │
                                        ▼
                                ┌───────────────┐
                                │  Venue Agent  │
                                │ (Avg Score,   │
                                │  Chase %)     │
                                └───────┬───────┘
                                        │
                                        ▼
                              ┌─────────────────────┐
                              │  Player Form Agent  │
                              │ (Top Batters/Bowlers │
                              │  + Live CricAPI)     │
                              └─────────┬───────────┘
                                        │
                                        ▼
                                ┌───────────────┐
                                │  Boss Agent   │
                                │ (Synthesize   │
                                │  → Predict)   │
                                └───────┬───────┘
                                        │
                                        ▼
                        ┌─────────────────────────────────┐
                        │        Final Prediction         │
                        │  { winner, confidence, reason }  │
                        └─────────────────────────────────┘
```

---

## How It Works

### Agent Pipeline

The system is built using **LangGraph**, which models the prediction workflow as a directed state graph. A shared `GraphState` dictionary is passed sequentially through each agent node.

Each agent follows a strict **3-step pattern**:

| Step | Action | Purpose |
|------|--------|---------|
| 1 | **Query Data** | Fetch structured evidence from SQLite or CricAPI |
| 2 | **Build Prompt** | Inject raw JSON evidence into a grounded LLM prompt |
| 3 | **Call LLM** | Send to Gemini/Groq via `safe_generate()`, write result to state |

#### 1. Stats Agent (`app/graph/nodes/stats_agent.py`)
Queries the SQLite database to gather:
- **Head-to-head records** between the two teams
- **Recent form** (last 5 matches for each team — wins/losses)
- **Toss statistics** (toss win rates and their correlation with match wins)

The LLM summarizes these stats into a concise analytical paragraph.

#### 2. Venue Agent (`app/graph/nodes/venue_agent.py`)
Uses a **venue normalizer** (`app/tools/venue_normalizer.py`) to:
- Calculate the **average first innings score** at the venue
- Determine the **chasing win percentage**
- Assess **sample size reliability** (if < 5 matches, the LLM is told to reduce certainty)

The LLM evaluates whether the pitch favors batting first or chasing.

#### 3. Player Form Agent (`app/graph/nodes/player_form_agent.py`)
Uses a **hybrid data strategy** combining two sources:

| Source | Data | Coverage |
|--------|------|----------|
| **SQLite DB** (Cricsheet) | Top 5 batters & bowlers from the last 5 historical matches (runs, strike rate, wickets, economy) | Deep historical (4,900+ matches) |
| **CricAPI** (Live API) | The 3 most recent senior-team matches with scores from `currentMatches` + paginated `/matches` endpoints | Real-time / last few days |

The LLM is explicitly told to **prioritize live API data** for assessing current form.

> **Key Design Choice:** The CricAPI client uses **exact team name matching** to filter out A-teams, U19, Women's teams, and domestic sides. Only senior international team matches are considered.

#### 4. Boss Agent (`app/graph/nodes/boss_agent.py`)
The decision-maker. It:
- Reads all three analyst reports from the `GraphState`
- Weighs stats, venue conditions, and player form equally
- Returns **strict JSON** with `predicted_winner`, `confidence` (50–90%), and `reasoning`
- Has robust JSON parsing with fallback handling for markdown-wrapped LLM responses

---

### Data Sources

```
┌──────────────────────────────────────────────────────────┐
│                     DATA LAYER                           │
│                                                          │
│  ┌──────────────────┐    ┌─────────────────────────┐    │
│  │   Cricsheet       │    │       CricAPI            │    │
│  │   (JSON files)    │    │   (REST API, Free Tier)  │    │
│  │                   │    │                          │    │
│  │  4,900+ T20       │    │  /currentMatches         │    │
│  │  matches          │    │  (live tournament data)  │    │
│  │                   │    │                          │    │
│  │  Ball-by-ball     │    │  /matches?offset=N       │    │
│  │  granularity      │    │  (recent history,        │    │
│  │                   │    │   paginated)             │    │
│  └────────┬─────────┘    └────────────┬────────────┘    │
│           │                           │                  │
│           ▼                           ▼                  │
│  ┌──────────────────┐    ┌─────────────────────────┐    │
│  │  scripts/ingest.py│    │ app/tools/               │    │
│  │  (ETL Pipeline)   │    │   cricapi_client.py      │    │
│  └────────┬─────────┘    │ (Dual-endpoint fetcher   │    │
│           │               │  + exact team matching)  │    │
│           ▼               └────────────┬────────────┘    │
│  ┌──────────────────┐                  │                 │
│  │  SQLite Database  │◄────────────────┘                 │
│  │  cricket.db       │   (augments DB at query time)     │
│  └──────────────────┘                                    │
└──────────────────────────────────────────────────────────┘
```

**Ingestion Pipeline** (`scripts/ingest.py`):
1. Reads raw JSON match files from Cricsheet (`data/raw/t20s_json/`)
2. Parses every ball bowled to aggregate player stats
3. Inserts into 3 SQLite tables using `INSERT OR REPLACE`

**Live API Client** (`app/tools/cricapi_client.py`):
1. Hits `/currentMatches` for live/ongoing tournament data (e.g., T20 World Cup)
2. Paginates through `/matches` (up to 200 results) for broader recent history
3. Merges both sources, deduplicates by match ID
4. Filters for exact senior team names only (no A-teams, U19, domestic)
5. Returns the 3 most recent matches with scores per team

---

### LLM Provider Strategy

The system uses a **multi-provider fallback strategy** (`app/tools/api_clients.py`):

```
Priority Order:
  1. Groq (Llama 3.3 70B) ──► fastest, free tier
  2. Groq (Llama 3.1 70B) ──► fallback model
  3. Gemini (key #1, model #1) ──► Google AI
  4. Gemini (key #1, model #2) ──► next model
  5. Gemini (key #2, model #1) ──► next API key
  ...and so on for all key × model combinations
```

**How it works:**
- All providers are arranged in a priority list
- If a provider hits a **rate limit / quota error** (429, "resource exhausted"), the system automatically **rotates** to the next provider
- Non-quota errors trigger an **exponential backoff** retry
- This ensures near-zero downtime even under heavy usage

---

## Database Schema

The SQLite database (`data/processed/cricket.db`) contains three tables:

### `matches`
| Column | Type | Description |
|--------|------|-------------|
| `match_id` | TEXT (PK) | Unique identifier from Cricsheet |
| `date` | TEXT | Match date (YYYY-MM-DD) |
| `team1` | TEXT | First team |
| `team2` | TEXT | Second team |
| `venue` | TEXT | Stadium name |
| `toss_winner` | TEXT | Team that won the toss |
| `toss_decision` | TEXT | "bat" or "field" |
| `winner` | TEXT | Match winner |

### `innings_summary`
| Column | Type | Description |
|--------|------|-------------|
| `match_id` | TEXT (FK) | References `matches` |
| `batting_team` | TEXT | Team batting |
| `total_runs` | INTEGER | Innings total |
| `wickets` | INTEGER | Wickets lost |
| `overs` | REAL | Overs bowled |
| `innings_number` | INTEGER | 1st or 2nd innings |

### `player_performances`
| Column | Type | Description |
|--------|------|-------------|
| `match_id` | TEXT (FK) | References `matches` |
| `player` | TEXT | Player name |
| `team` | TEXT | Player's team |
| `runs_scored` | INTEGER | Runs scored as batter |
| `balls_faced` | INTEGER | Balls faced (excl. wides) |
| `wickets_taken` | INTEGER | Wickets taken as bowler |
| `balls_bowled` | INTEGER | Balls bowled (excl. wides) |
| `runs_conceded` | INTEGER | Runs conceded as bowler |

---

## Project Structure

```
T20Oracle/
├── app/
│   ├── main.py                  # FastAPI app + endpoints
│   ├── config.py                # Environment variable loader
│   ├── schemas.py               # Pydantic request/response models
│   ├── graph/
│   │   ├── state.py             # GraphState TypedDict definition
│   │   ├── builder.py           # LangGraph state graph construction
│   │   └── nodes/
│   │       ├── stats_agent.py   # H2H, form, toss analysis
│   │       ├── venue_agent.py   # Venue/pitch analysis
│   │       ├── player_form_agent.py  # Player stats (DB + live API)
│   │       └── boss_agent.py    # Final prediction synthesizer
│   ├── services/
│   │   └── prediction_service.py  # Graph invocation wrapper
│   ├── tools/
│   │   ├── db.py                # SQLite connection + table creation
│   │   ├── api_clients.py       # Multi-provider LLM client (Gemini/Groq)
│   │   ├── cricapi_client.py    # CricAPI live data fetcher
│   │   └── venue_normalizer.py  # Venue stats calculator
│   └── utils/
│       └── logger.py            # Logging utility
├── frontend/
│   ├── index.html               # Single-page UI
│   ├── styles.css               # Premium dark-mode styling
│   ├── script.js                # API interaction logic
│   └── favicon.svg              # App icon
├── scripts/
│   ├── ingest.py                # Cricsheet → SQLite ETL pipeline
│   └── verify_db.py             # Database verification utility
├── data/
│   ├── raw/                     # Cricsheet JSON files (gitignored)
│   └── processed/
│       └── cricket.db           # SQLite database
├── .env                         # API keys (gitignored)
├── .gitignore
├── requirements.txt
├── run.py                       # Server entry point
├── render.yaml                  # Render deployment config
└── vercel.json                  # Vercel frontend deployment config
```

---

## API Endpoints

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/` | Health check |
| `GET` | `/teams` | List all teams in the database |
| `GET` | `/venues` | List all venues in the database |
| `POST` | `/predict` | Run the full multi-agent prediction pipeline |

### `POST /predict` — Request

```json
{
  "team1": "India",
  "team2": "New Zealand",
  "venue": "Wankhede Stadium, Mumbai",
  "toss_winner": "India",
  "batting_first": "India"
}
```

### `POST /predict` — Response

```json
{
  "predicted_winner": "India",
  "confidence": 70.0,
  "reasoning": "India's recent form and historical dominance over New Zealand give them an edge, with key batters like SA Yadav and Ishan Kishan in good form. The venue conditions suggest a balanced contest, but India's decision to bat first after winning the toss could allow them to set a competitive score."
}
```

---

## Quick Start

```bash
# 1. Clone the repository
git clone https://github.com/agam25rpro/T20Oracle.git
cd T20Oracle

# 2. Install dependencies
pip install -r requirements.txt

# 3. Create .env file with your API keys
cp .env.example .env

# 4. Ingest match data into SQLite (one-time setup)
python scripts/ingest.py

# 5. Run the backend server
python run.py

# 6. Open the frontend
# Simply open frontend/index.html in your browser
```

Server starts at `http://localhost:8000`.

---

## Environment Variables

| Variable | Required | Description |
|----------|----------|-------------|
| `GEMINI_API_KEYS` | Yes | Comma-separated Google Gemini API keys |
| `GROQ_API_KEY` | No | Groq API key for Llama models |
| `CRICAPI_KEY` | No | CricketData.org API key for live match data |
| `GEMINI_MODELS` | No | Comma-separated model names in priority order (default: `gemini-2.0-flash`) |
| `DB_PATH` | No | Path to SQLite database (default: `data/processed/cricket.db`) |

---

## Frontend

The frontend is a lightweight, responsive **Vanilla HTML/CSS/JS** Single-Page Application (SPA) located in the `frontend/` directory. It features a premium dark-mode UI that allows users to select teams and venues seamlessly. It communicates with the backend via REST API to fetch predictions and elegantly displays the step-by-step LLM reasoning process. Because it is purely static, it can be simply opened in a browser or easily hosted on a static hosting service.

## Backend

The backend is a robust **FastAPI** application (`app/main.py`) serving as the orchestration engine. It utilizes **LangGraph** to manage the multi-agent workflow (Stats, Venue, Player Form, and Boss Agents) and interfaces with multiple LLM providers (Google Gemini and Groq) via an automated fallback system. The backend asynchronously queries both the local SQLite database and live cricket APIs, feeds this structured evidence into the LLM prompts, and serves the resulting consolidated predictions via fastREST endpoints.

---

## Deployment

### Backend (Render)

The backend is configured for deployment on [Render](https://render.com) via `render.yaml`. It uses the free tier with a keep-alive GitHub Action (`.github/workflows/keep-alive.yml`) to prevent spindown.

### Frontend (Vercel)

The static frontend is configured for deployment on [Vercel](https://vercel.com) via `vercel.json`. It serves the `frontend/` directory as a static site.

---

## Tech Stack

| Layer | Technology |
|-------|-----------|
| Backend Framework | FastAPI |
| Agent Orchestration | LangGraph |
| LLM Providers | Google Gemini, Groq (Llama 3.3/3.1 70B) |
| Database | SQLite |
| Data Source (Historical) | Cricsheet (4,900+ T20 matches) |
| Data Source (Live) | CricAPI (cricketdata.org) |
| Frontend | Vanilla HTML/CSS/JS |
| Backend Hosting | Render |
| Frontend Hosting | Vercel |
