"""
เสริมข้อมูลที่พักจาก Google Places (ที่อยู่ + รูป) สำหรับผลค้นหา Amadeus
ใช้เมื่อ API Amadeus v3 ไม่คืน address และ media
"""

from __future__ import annotations
from typing import Any, Dict, List, Optional
import asyncio

from app.core.config import settings
from app.core.logging import get_logger

logger = get_logger(__name__)


def _get_gmaps():
    """Lazy Google Maps client (sync)."""
    if not getattr(settings, "google_maps_api_key", None):
        return None
    try:
        import googlemaps
        return googlemaps.Client(key=settings.google_maps_api_key)
    except Exception as e:
        logger.warning(f"Google Maps client init failed: {e}")
        return None


async def enrich_hotel_with_google_place(amadeus_hotel: Dict[str, Any]) -> Dict[str, Any]:
    """
    เสริมที่อยู่และรูปภาพจาก Google Places สำหรับรายการที่พัก 1 รายการ
    คืนค่า dict ที่มี key: address, image_urls (และคง key เดิมของ amadeus_hotel)
    ไม่แก้ amadeus_hotel เดิม; ถ้าไม่มี Google key หรือหา place ไม่เจอ คืนค่า address/image_urls เป็นค่าว่าง
    """
    out: Dict[str, Any] = {"address": "", "image_urls": []}
    gmaps = _get_gmaps()
    if not gmaps:
        return out

    hotel_meta = amadeus_hotel.get("hotel") or {}
    hotel_name = (hotel_meta.get("name") or amadeus_hotel.get("name") or "").strip()
    if not hotel_name:
        return out

    city_code = ""
    debug = amadeus_hotel.get("_debug") or {}
    city_raw = debug.get("city_code_used", "")
    if ":" in city_raw:
        part = city_raw.split(":")[-1].strip()
        if len(part) == 3 and part.isupper():
            city_code = part
        elif part and not (part and part[0].isdigit()):
            city_code = part.split(",")[0] if "," in part else part
    else:
        city_code = city_raw

    lat = hotel_meta.get("latitude")
    lng = hotel_meta.get("longitude")
    loop = asyncio.get_event_loop()

    place_id = None
    try:
        query = f"{hotel_name} {city_code}".strip()
        result = await loop.run_in_executor(
            None,
            lambda: gmaps.find_place(
                input=query,
                input_type="textquery",
                fields=["place_id", "name", "photos", "geometry"],
                language="th",
            ),
        )
        candidates = result.get("candidates") or []
        if candidates:
            place_id = candidates[0].get("place_id")
    except Exception as e:
        logger.debug(f"find_place failed for '{hotel_name}': {e}")

    if not place_id:
        try:
            text_result = await loop.run_in_executor(
                None,
                lambda: gmaps.places(query=f"{hotel_name} {city_code}".strip(), language="th"),
            )
            results = text_result.get("results") or []
            for p in results[:3]:
                if p.get("place_id"):
                    place_id = p["place_id"]
                    break
        except Exception as e:
            logger.debug(f"places text search failed for '{hotel_name}': {e}")

    if not place_id:
        return out

    try:
        place_result = await loop.run_in_executor(
            None,
            lambda: gmaps.place(
                place_id=place_id,
                # Request geometry so we can build a Static Map fallback if photos are missing.
                fields=["formatted_address", "photos", "name", "rating", "user_ratings_total", "geometry"],
                language="th",
            ),
        )
        result = place_result.get("result")
        if not result:
            return out

        out["address"] = result.get("formatted_address") or ""

        photos = result.get("photos") or []
        api_key = getattr(settings, "google_maps_api_key", "") or ""
        if photos and api_key:
            for p in photos[:5]:
                url = None
                ref = p.get("photo_reference")
                name = p.get("name")
                if ref:
                    url = f"https://maps.googleapis.com/maps/api/place/photo?maxwidth=400&photo_reference={ref}&key={api_key}"
                elif name:
                    url = f"https://places.googleapis.com/v1/{name}/media?maxWidthPx=400&key={api_key}"
                if url:
                    out["image_urls"].append(url)

        # ถ้า Google Places ไม่คืน photos เลย ให้ใช้ Static Map เป็นรูป fallback จากพิกัด
        if not out["image_urls"] and api_key:
            loc = (result.get("geometry") or {}).get("location") or {}
            static_lat = loc.get("lat") or lat
            static_lng = loc.get("lng") or lng
            if static_lat is not None and static_lng is not None:
                static_url = (
                    "https://maps.googleapis.com/maps/api/staticmap"
                    f"?center={static_lat},{static_lng}"
                    "&zoom=16&size=400x300&maptype=roadmap"
                    f"&markers=color:red%7C{static_lat},{static_lng}"
                    f"&key={api_key}"
                )
                out["image_urls"].append(static_url)
    except Exception as e:
        logger.debug(f"place details failed for place_id={place_id}: {e}")

    return out


async def enrich_hotels_with_google(hotels: List[Dict[str, Any]]) -> None:
    """
    แก้ไข list ของ hotel ใน place โดยเพิ่ม address และ image_urls จาก Google
    แก้ไขแต่ละ dict ใน hotels โดยตรง (in-place)
    """
    if not hotels:
        return
    tasks = [enrich_hotel_with_google_place(h) for h in hotels]
    results = await asyncio.gather(*tasks, return_exceptions=True)
    for h, res in zip(hotels, results):
        if isinstance(res, Exception):
            logger.debug(f"Enrich hotel failed: {res}")
            continue
        if res.get("address") and not (h.get("address") or (h.get("hotel") or {}).get("address")):
            h["address"] = res["address"]
        if res.get("image_urls"):
            h["image_urls"] = res["image_urls"]
