from __future__ import annotations

from fastapi import APIRouter

from core.config import env_status
from core.context import USER_CONTEXTS

router = APIRouter()

@router.get("/health")
async def health():
    s = env_status()
    return {
        "status": "ok",
        **s,
        "users_in_memory": len(USER_CONTEXTS),
        "flow": [
            "slot_extract(gemini,no-tools)+regex",
            "autopilot_defaults(no ask core)",
            "autonomous_iata(ref-data)",
            "flight_offers_search",
            "hotels(v3: by_city -> hotelIds -> hotel-offers, date shift + fallback)",
            "plan_builder(3 detailed choices)",
            "choice_select",
            "trip_title(gemini)",
        ],
    }
