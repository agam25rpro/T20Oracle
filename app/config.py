import os
from dotenv import load_dotenv

load_dotenv()

GOOGLE_API_KEYS = [k.strip() for k in os.getenv("GEMINI_API_KEYS", "").split(",") if k.strip()]
GROQ_API_KEY = os.getenv("GROQ_API_KEY", "")

GEMINI_MODELS = [m.strip() for m in os.getenv("GEMINI_MODELS", "gemini-2.0-flash").split(",") if m.strip()]

DB_PATH = os.getenv("DB_PATH", "data/processed/cricket.db")
CRICAPI_KEY = os.getenv("CRICAPI_KEY", "")