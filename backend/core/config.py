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

def _env_host(v: str) -> str:
    v = (v or "").strip().lower()
    return "test" if v in {"test", "sandbox"} else "production"


# ----------------------------
# Amadeus (Search vs Booking)
#
# Requirement:
# - Search can use PRODUCTION credentials for real prices.
# - Booking must be SANDBOX/TEST only.
#
# Backward compatible:
# - If AMADEUS_SEARCH_* are not set, fall back to AMADEUS_*.
# - If AMADEUS_BOOKING_* are not set, fall back to AMADEUS_* (but forced to test host).
# ----------------------------

# Legacy (single-env)
AMADEUS_API_KEY = (os.getenv("AMADEUS_API_KEY") or "").strip()
AMADEUS_API_SECRET = (os.getenv("AMADEUS_API_SECRET") or "").strip()
AMADEUS_ENV = (os.getenv("AMADEUS_ENV") or "test").strip().lower()
AMADEUS_HOST = _env_host(AMADEUS_ENV)

# Search (prefer these)
AMADEUS_SEARCH_ENV = (os.getenv("AMADEUS_SEARCH_ENV") or AMADEUS_ENV or "test").strip().lower()
AMADEUS_SEARCH_HOST = _env_host(AMADEUS_SEARCH_ENV)
AMADEUS_SEARCH_API_KEY = (os.getenv("AMADEUS_SEARCH_API_KEY") or AMADEUS_API_KEY or "").strip()
AMADEUS_SEARCH_API_SECRET = (os.getenv("AMADEUS_SEARCH_API_SECRET") or AMADEUS_API_SECRET or "").strip()

# Booking (sandbox only)
_book_env_raw = (
    os.getenv("AMADEUS_BOOKING_ENV")
    or os.getenv("AMADEUS_BOOK_ENV")
    or "test"
)
AMADEUS_BOOKING_ENV = (str(_book_env_raw) or "test").strip().lower()

AMADEUS_BOOKING_API_KEY = (
    os.getenv("AMADEUS_BOOKING_API_KEY")
    or os.getenv("AMADEUS_BOOK_API_KEY")
    or AMADEUS_API_KEY
    or ""
).strip()
AMADEUS_BOOKING_API_SECRET = (
    os.getenv("AMADEUS_BOOKING_API_SECRET")
    or os.getenv("AMADEUS_BOOK_API_SECRET")
    or AMADEUS_API_SECRET
    or ""
).strip()

# Force booking host to test regardless of env var (Layer-1 guard)
AMADEUS_BOOKING_HOST = "test"

_amadeus_search_client: Optional[AmadeusClient] = None
_amadeus_booking_client: Optional[AmadeusClient] = None


def get_amadeus_search_client() -> Optional[AmadeusClient]:
    """Lazy init. Return None if not configured."""
    global _amadeus_search_client
    if _amadeus_search_client is not None:
        return _amadeus_search_client
    if not AMADEUS_SEARCH_API_KEY or not AMADEUS_SEARCH_API_SECRET:
        return None
    _amadeus_search_client = AmadeusClient(
        client_id=AMADEUS_SEARCH_API_KEY,
        client_secret=AMADEUS_SEARCH_API_SECRET,
        hostname=AMADEUS_SEARCH_HOST,
    )
    return _amadeus_search_client


def get_amadeus_booking_client() -> Optional[AmadeusClient]:
    """Lazy init. Return None if not configured.

    IMPORTANT:
    - Booking client is always forced to hostname='test' (sandbox).
    - Additional runtime guard exists in core/safety.py.
    """
    global _amadeus_booking_client
    if _amadeus_booking_client is not None:
        return _amadeus_booking_client
    if not AMADEUS_BOOKING_API_KEY or not AMADEUS_BOOKING_API_SECRET:
        return None
    _amadeus_booking_client = AmadeusClient(
        client_id=AMADEUS_BOOKING_API_KEY,
        client_secret=AMADEUS_BOOKING_API_SECRET,
        hostname=AMADEUS_BOOKING_HOST,
    )
    return _amadeus_booking_client


# Backwards-compatible alias (some modules may still call this)
def get_amadeus_client() -> Optional[AmadeusClient]:
    return get_amadeus_search_client()


# ----------------------------
# MongoDB
# ----------------------------
MONGODB_URL = (os.getenv("MONGODB_URL") or "").strip()
MONGODB_DB_NAME = (os.getenv("MONGODB_DB_NAME") or "travel_agent").strip()

def env_status() -> dict:
    """For /health: do not throw, just report."""
    # Backward-compatible keys (amadeus_ok/env/host) represent SEARCH side.
    return {
        "gemini_ok": bool(GEMINI_API_KEY),
        "amadeus_ok": bool(AMADEUS_SEARCH_API_KEY and AMADEUS_SEARCH_API_SECRET),
        "amadeus_search_ok": bool(AMADEUS_SEARCH_API_KEY and AMADEUS_SEARCH_API_SECRET),
        "amadeus_booking_ok": bool(AMADEUS_BOOKING_API_KEY and AMADEUS_BOOKING_API_SECRET),
        "gemini_model": GEMINI_MODEL_NAME,
        "amadeus_env": AMADEUS_SEARCH_ENV,
        "amadeus_host": AMADEUS_SEARCH_HOST,
        "amadeus_search_env": AMADEUS_SEARCH_ENV,
        "amadeus_search_host": AMADEUS_SEARCH_HOST,
        "amadeus_booking_env": AMADEUS_BOOKING_ENV,
        "amadeus_booking_host": AMADEUS_BOOKING_HOST,
        "amadeus_legacy_env": AMADEUS_ENV,
        "amadeus_legacy_host": AMADEUS_HOST,
    }