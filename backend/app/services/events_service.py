import os
from typing import List, Dict, Any

import httpx

from app.core.config import settings
from app.core.logging import get_logger


logger = get_logger(__name__)


GOOGLE_PLACES_API_KEY = os.getenv("GOOGLE_PLACES_API_KEY", "").strip() or settings.google_maps_api_key


async def _google_text_search(query: str, location: str) -> List[Dict[str, Any]]:
    """
    เรียก Google Places Text Search เพื่อค้นหาอีเวนต์/สถานที่ที่เกี่ยวกับ event รอบ ๆ ปลายทาง
    NOTE: Google Places ไม่มี event endpoint ตรง ๆ จึงใช้ keyword-based search แทน
    """
    if not GOOGLE_PLACES_API_KEY:
        logger.info("Google Places API key not configured – skip event search")
        return []

    url = "https://maps.googleapis.com/maps/api/place/textsearch/json"
    params = {
        "query": f"{query} events near {location}",
        "language": "th",
        "key": GOOGLE_PLACES_API_KEY,
    }

    try:
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.get(url, params=params)
            resp.raise_for_status()
            data = resp.json()
    except Exception as e:
        logger.warning(f"Google Places Text Search failed: {e}")
        return []

    results = data.get("results") or []
    logger.info(f"Google Places: query='{query}' location='{location}' -> {len(results)} results")
    return results


def _normalize_google_places(results: List[Dict[str, Any]], location_hint: str) -> List[Dict[str, Any]]:
    """
    แปลงผลลัพธ์จาก Google Places ให้เป็นโครง event กลางที่ Agent/Frontend ใช้ได้
    หมายเหตุ: Google Places ไม่บอกวันที่เริ่ม/จบงานตรง ๆ จึงปล่อย start_date/end_date เป็น None
    แล้วให้ LLM หรือ business logic ด้านบนตีความต่อ
    """
    events: List[Dict[str, Any]] = []
    for r in results:
        name = r.get("name")
        if not name:
            continue
        events.append(
            {
                "name": name,
                "location": r.get("formatted_address") or location_hint,
                "start_date": None,
                "end_date": None,
                "url": None,
                "source": "google_places",
                "raw": r,
            }
        )
    return events


async def get_events_from_google(location: str) -> List[Dict[str, Any]]:
    """
    ค้นหาอีเวนต์/กิจกรรมจาก Google Places รอบ ๆ location ที่ระบุ
    ใช้หลาย keyword เพื่อครอบคลุมกรณี festival / concert / market / exhibition ฯลฯ
    """
    location = (location or "").strip()
    if not location:
        return []

    queries = ["festival", "events", "concert", "exhibition", "market"]
    all_results: List[Dict[str, Any]] = []

    for q in queries:
        res = await _google_text_search(q, location)
        if res:
            all_results.extend(res)

    normalized = _normalize_google_places(all_results, location)

    # ลบชื่อซ้ำกันออก (ใช้ชื่อเป็น key หลัก)
    seen = set()
    unique: List[Dict[str, Any]] = []
    for ev in normalized:
        key = ev.get("name")
        if not key or key in seen:
            continue
        seen.add(key)
        unique.append(ev)

    logger.info(f"Normalized Google events for '{location}': {len(unique)} unique items")
    return unique

