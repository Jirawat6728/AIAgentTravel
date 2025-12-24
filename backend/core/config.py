from __future__ import annotations

import os
from typing import Optional

from pathlib import Path

from dotenv import load_dotenv
from amadeus import Client as AmadeusClient
from google import genai

"""Central config + lazy clients.

Why we load .env this way:
- On Windows + uvicorn --reload, the reloader subprocess may start with a different
  working directory than you expect.
- If we rely on CWD, env vars may appear "missing" even though backend/.env exists.

Rules:
- Prefer DOTENV_PATH if provided.
- Otherwise, load backend/.env relative to this file.
"""

_BASE_DIR = Path(__file__).resolve().parents[1]  # .../backend
_DOTENV_PATH = Path(os.getenv("DOTENV_PATH") or (_BASE_DIR / ".env"))
load_dotenv(dotenv_path=_DOTENV_PATH, override=True)

# ----------------------------
# Gemini
# ----------------------------
GEMINI_API_KEY = (os.getenv("GEMINI_API_KEY") or "").strip()
GEMINI_MODEL_NAME = (os.getenv("GEMINI_MODEL_NAME") or "gemini-1.5-flash").strip()

_gemini_client: Optional[genai.Client] = None

def get_gemini_client() -> genai.Client:
    """Lazy init. Raise only when actually used."""
    global _gemini_client
    if _gemini_client is not None:
        return _gemini_client
    if not GEMINI_API_KEY:
        raise RuntimeError("GEMINI_API_KEY not set in .env")
    _gemini_client = genai.Client(api_key=GEMINI_API_KEY)
    return _gemini_client

# ----------------------------
# Amadeus
# ----------------------------
AMADEUS_API_KEY = (os.getenv("AMADEUS_API_KEY") or "").strip()
AMADEUS_API_SECRET = (os.getenv("AMADEUS_API_SECRET") or "").strip()
AMADEUS_ENV = (os.getenv("AMADEUS_ENV") or "test").strip().lower()
AMADEUS_HOST = "test" if AMADEUS_ENV == "test" else "production"

_amadeus_client: Optional[AmadeusClient] = None

def get_amadeus_client() -> Optional[AmadeusClient]:
    """Lazy init. Return None if not configured."""
    global _amadeus_client
    if _amadeus_client is not None:
        return _amadeus_client
    if not AMADEUS_API_KEY or not AMADEUS_API_SECRET:
        return None
    _amadeus_client = AmadeusClient(
        client_id=AMADEUS_API_KEY,
        client_secret=AMADEUS_API_SECRET,
        hostname=AMADEUS_HOST,
    )
    return _amadeus_client

def env_status() -> dict:
    """For /health: do not throw, just report."""
    return {
        "gemini_ok": bool(GEMINI_API_KEY),
        "amadeus_ok": bool(AMADEUS_API_KEY and AMADEUS_API_SECRET),
        "gemini_model": GEMINI_MODEL_NAME,
        "amadeus_env": AMADEUS_ENV,
        "amadeus_host": AMADEUS_HOST,
    }