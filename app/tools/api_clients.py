import time
from google import genai
from google.genai import types
from app.config import GOOGLE_API_KEYS, GROQ_API_KEY, GEMINI_MODELS
from app.utils.logger import log

HAS_GROQ = False
groq_client = None

if GROQ_API_KEY:
    try:
        from groq import Groq
        groq_client = Groq(api_key=GROQ_API_KEY)
        HAS_GROQ = True
    except ImportError:
        pass

if not GOOGLE_API_KEYS:
    raise ValueError("No Gemini API keys found. Set GEMINI_API_KEYS in .env")

PROVIDERS = []
GROQ_MODELS = ["llama-3.3-70b-versatile", "llama-3.1-70b-versatile"]

if HAS_GROQ:
    for model in GROQ_MODELS:
        PROVIDERS.append({
            "type": "groq",
            "model": model,
            "client": groq_client,
            "label": f"Groq/{model}",
        })

gemini_clients = {key: genai.Client(api_key=key) for key in GOOGLE_API_KEYS}

for idx, key in enumerate(GOOGLE_API_KEYS):
    for model in GEMINI_MODELS:
        PROVIDERS.append({
            "type": "gemini",
            "model": model,
            "client": gemini_clients[key],
            "label": f"Gemini/key#{idx+1}/{model}",
        })

_current_idx = 0
_cached_provider = None

def _rotate_provider():
    global _current_idx, _cached_provider
    for _ in range(len(PROVIDERS)):
        _current_idx = (_current_idx + 1) % len(PROVIDERS)
        _cached_provider = PROVIDERS[_current_idx]
        return _cached_provider
    _cached_provider = None
    return None

def _get_provider():
    global _cached_provider
    if _cached_provider is None:
        _cached_provider = PROVIDERS[_current_idx]
    return _cached_provider

_QUOTA_HINTS = ("429", "quota", "rate limit", "resource exhausted", "too many requests", "exceeded your current quota")

def _is_quota_error(error):
    msg = str(error).lower()
    return any(h in msg for h in _QUOTA_HINTS)

def safe_generate(prompt: str, temperature: float = 0.7, max_retries: int = 3) -> str:
    last_error = None
    for attempt in range(max_retries * len(PROVIDERS)):
        provider = _get_provider()
        try:
            if provider["type"] == "groq":
                resp = provider["client"].chat.completions.create(
                    model=provider["model"],
                    messages=[{"role": "user", "content": prompt}],
                    temperature=temperature,
                    max_tokens=2048,
                )
                return resp.choices[0].message.content.strip()
            else:
                resp = provider["client"].models.generate_content(
                    model=provider["model"],
                    contents=prompt,
                    config=types.GenerateContentConfig(
                        temperature=temperature,
                        max_output_tokens=2048,
                    ),
                )
                return resp.text.strip()
        except Exception as e:
            last_error = e
            if _is_quota_error(e):
                _rotate_provider()
                continue
            delay = 2 ** (attempt % max_retries)
            time.sleep(delay)
            continue
    raise RuntimeError(f"All providers exhausted. Last error: {last_error}")

def reset_rotation():
    global _current_idx, _cached_provider
    _current_idx = 0
    _cached_provider = None

__all__ = ["safe_generate", "reset_rotation", "PROVIDERS"]