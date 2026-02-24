"""
MCP (Model Context Protocol) - เครื่องมือ Weather & Timezone
ใช้ Open-Meteo (ฟรี ไม่ต้องใช้ API key) สำหรับสภาพอากาศปลายทาง และ timezone
เพิ่มความแม่นยำในการวางแผน: อุณหภูมิ ฝน โอกาสพายุ เวลาท้องถิ่น
"""

from __future__ import annotations
from typing import Any, Dict, List, Optional
import asyncio
import re
from datetime import datetime, timedelta, timezone

import httpx

from app.core.logging import get_logger
from app.services.travel_service import TravelOrchestrator

logger = get_logger(__name__)

OPEN_METEO_BASE = "https://api.open-meteo.com/v1"

# Shared httpx client for connection pooling (created lazily)
_http_client: Optional[httpx.AsyncClient] = None


def _get_http_client() -> httpx.AsyncClient:
    global _http_client
    if _http_client is None or _http_client.is_closed:
        _http_client = httpx.AsyncClient(timeout=10.0)
    return _http_client


# -----------------------------------------------------------------------------
# Weather & Timezone MCP Tool Definitions (Function Calling Schema for Gemini)
# -----------------------------------------------------------------------------

WEATHER_TOOLS = [
    {
        "name": "get_weather_forecast",
        "description": (
            "Get weather forecast for a destination on a specific date using Open-Meteo. "
            "Returns max/min temperature (°C), precipitation (mm), weather description (English + Thai), "
            "and timezone. Use this to advise travelers on what to pack and best time to visit."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "place_name": {
                    "type": "string",
                    "description": "City or place name (e.g., 'Bangkok', 'Tokyo', 'Phuket')"
                },
                "date": {
                    "type": "string",
                    "description": "Date in YYYY-MM-DD format (e.g., '2025-02-15'). Must be within the next 16 days."
                },
                "latitude": {
                    "type": "number",
                    "description": "Optional: latitude if already known (skip geocoding)"
                },
                "longitude": {
                    "type": "number",
                    "description": "Optional: longitude if already known (skip geocoding)"
                }
            },
            "required": ["place_name"]
        }
    },
    {
        "name": "get_destination_timezone",
        "description": "Get IANA timezone and current local time for a destination. Use to show check-in times, flight arrival in local time, or suggest when to call.",
        "parameters": {
            "type": "object",
            "properties": {
                "place_name": {
                    "type": "string",
                    "description": "City or place name (e.g., 'Seoul', 'London')"
                }
            },
            "required": ["place_name"]
        }
    }
]

# WMO weather interpretation codes → (English, Thai)
_WMO_DESCRIPTIONS: Dict[int, tuple] = {
    0:  ("Clear sky", "ท้องฟ้าแจ่มใส"),
    1:  ("Mainly clear", "ส่วนใหญ่แจ่มใส"),
    2:  ("Partly cloudy", "มีเมฆบางส่วน"),
    3:  ("Overcast", "เมฆมาก"),
    45: ("Fog", "หมอก"),
    48: ("Icy fog", "หมอกน้ำค้าง"),
    51: ("Light drizzle", "ฝนตกปรายเล็กน้อย"),
    53: ("Moderate drizzle", "ฝนตกปราย"),
    55: ("Dense drizzle", "ฝนตกปรายหนาแน่น"),
    61: ("Slight rain", "ฝนตกเล็กน้อย"),
    63: ("Moderate rain", "ฝนตกปานกลาง"),
    65: ("Heavy rain", "ฝนตกหนัก"),
    71: ("Slight snow", "หิมะตกเล็กน้อย"),
    73: ("Moderate snow", "หิมะตกปานกลาง"),
    75: ("Heavy snow", "หิมะตกหนัก"),
    80: ("Slight showers", "ฝนตกเป็นช่วงๆ"),
    81: ("Moderate showers", "ฝนตกเป็นช่วงๆ ค่อนข้างหนัก"),
    82: ("Violent showers", "ฝนตกเป็นช่วงๆ หนักมาก"),
    95: ("Thunderstorm", "พายุฝนฟ้าคะนอง"),
    96: ("Thunderstorm with hail", "พายุฝนฟ้าคะนองพร้อมลูกเห็บ"),
}

_DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")


def _validate_date(date_str: str) -> Optional[str]:
    """
    Validate and normalise a date string to YYYY-MM-DD.
    Returns None if the string cannot be parsed.
    """
    if not date_str:
        return None
    date_str = date_str.strip()
    if _DATE_RE.match(date_str):
        try:
            datetime.strptime(date_str, "%Y-%m-%d")
            return date_str
        except ValueError:
            return None
    # Try common alternative formats
    for fmt in ("%d/%m/%Y", "%m/%d/%Y", "%B %d, %Y", "%d %B %Y"):
        try:
            return datetime.strptime(date_str, fmt).strftime("%Y-%m-%d")
        except ValueError:
            continue
    return None


class WeatherMCP:
    """
    Weather & Timezone MCP executor using Open-Meteo (free, no API key).
    Uses TravelOrchestrator for geocoding when place_name is given.
    """

    def __init__(self, orchestrator: Optional[TravelOrchestrator] = None):
        self.orchestrator = orchestrator or TravelOrchestrator()
        logger.info("WeatherMCP initialized (Open-Meteo + TravelOrchestrator)")

    @staticmethod
    def _weather_desc(code: Optional[int]) -> Dict[str, str]:
        """Return bilingual weather description for a WMO weather code."""
        if code is None:
            return {"en": "Unknown", "th": "ไม่ทราบ"}
        entry = _WMO_DESCRIPTIONS.get(int(code))
        if entry:
            return {"en": entry[0], "th": entry[1]}
        return {"en": "Unknown", "th": "ไม่ทราบ"}

    async def get_weather_forecast(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Get weather forecast for a place and date."""
        place_name = (params.get("place_name") or "").strip()
        raw_date = (params.get("date") or "").strip()
        lat = params.get("latitude")
        lng = params.get("longitude")

        # Validate / normalise date
        date_str: Optional[str] = _validate_date(raw_date) if raw_date else None
        if raw_date and date_str is None:
            return {
                "success": False,
                "tool": "get_weather_forecast",
                "error": (
                    f"Invalid date format: '{raw_date}'. "
                    "Please use YYYY-MM-DD (e.g. 2025-06-15)."
                ),
            }
        if not date_str:
            date_str = (datetime.utcnow() + timedelta(days=1)).strftime("%Y-%m-%d")

        if not place_name and (lat is None or lng is None):
            return {
                "success": False,
                "tool": "get_weather_forecast",
                "error": "Provide place_name or both latitude and longitude.",
            }

        try:
            if lat is None or lng is None:
                coords = await self.orchestrator.get_coordinates(place_name)
                lat, lng = coords["lat"], coords["lng"]
            else:
                if not place_name:
                    place_name = f"{lat},{lng}"

            url = (
                f"{OPEN_METEO_BASE}/forecast"
                f"?latitude={lat}&longitude={lng}"
                "&daily=temperature_2m_max,temperature_2m_min,precipitation_sum,weather_code"
                "&timezone=auto"
                "&past_days=0"
                f"&start_date={date_str}&end_date={date_str}"
            )

            client = _get_http_client()
            resp = await client.get(url)
            resp.raise_for_status()
            data = resp.json()

            daily = data.get("daily", {})
            times: List[str] = daily.get("time", [])
            tz = data.get("timezone", "UTC")
            tz_abbrev = data.get("timezone_abbreviation", "")

            if not times:
                return {
                    "success": True,
                    "tool": "get_weather_forecast",
                    "place": place_name,
                    "date": date_str,
                    "timezone": tz,
                    "timezone_abbreviation": tz_abbrev,
                    "message": "No daily data for this date; try a date within the next 16 days.",
                    "temperature_2m_max_c": None,
                    "temperature_2m_min_c": None,
                    "precipitation_sum_mm": None,
                    "weather_code": None,
                    "weather_description": self._weather_desc(None),
                }

            idx = 0
            try:
                idx = times.index(date_str)
            except ValueError:
                idx = 0

            def at(i: int, arr: Optional[List]) -> Any:
                if arr is None or i >= len(arr):
                    return None
                return arr[i]

            t_max = daily.get("temperature_2m_max")
            t_min = daily.get("temperature_2m_min")
            precip = daily.get("precipitation_sum")
            wcode = daily.get("weather_code")
            code_val = at(idx, wcode)

            return {
                "success": True,
                "tool": "get_weather_forecast",
                "place": place_name,
                "date": times[idx] if idx < len(times) else date_str,
                "timezone": tz,
                "timezone_abbreviation": tz_abbrev,
                "temperature_2m_max_c": at(idx, t_max),
                "temperature_2m_min_c": at(idx, t_min),
                "precipitation_sum_mm": at(idx, precip),
                "weather_code": code_val,
                "weather_description": self._weather_desc(code_val),
            }

        except httpx.HTTPError as e:
            logger.warning(f"Open-Meteo request failed: {e}")
            return {"success": False, "tool": "get_weather_forecast", "error": str(e)[:200]}
        except Exception as e:
            logger.exception("get_weather_forecast failed")
            return {"success": False, "tool": "get_weather_forecast", "error": str(e)[:200]}

    async def get_destination_timezone(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Get timezone and current local time for a destination."""
        place_name = (params.get("place_name") or "").strip()
        if not place_name:
            return {
                "success": False,
                "tool": "get_destination_timezone",
                "error": "place_name required",
            }

        try:
            coords = await self.orchestrator.get_coordinates(place_name)
            lat, lng = coords["lat"], coords["lng"]

            url = (
                f"{OPEN_METEO_BASE}/forecast"
                f"?latitude={lat}&longitude={lng}"
                "&current=apparent_temperature"  # lightweight field — we only need timezone metadata
                "&timezone=auto"
            )
            client = _get_http_client()
            resp = await client.get(url)
            resp.raise_for_status()
            data = resp.json()

            tz = data.get("timezone", "UTC")
            tz_abbrev = data.get("timezone_abbreviation", "")
            utc_offset_s = data.get("utc_offset_seconds", 0)

            # Derive local time from UTC + offset (reliable regardless of `current.time` semantics)
            local_dt = datetime.now(timezone.utc) + timedelta(seconds=utc_offset_s)
            local_time_iso = local_dt.strftime("%Y-%m-%dT%H:%M:%S")

            return {
                "success": True,
                "tool": "get_destination_timezone",
                "place": place_name,
                "timezone": tz,
                "timezone_abbreviation": tz_abbrev,
                "utc_offset_hours": round(utc_offset_s / 3600, 2),
                "local_time_iso": local_time_iso,
                "coordinates": {"latitude": lat, "longitude": lng},
            }
        except Exception as e:
            logger.warning(f"get_destination_timezone failed: {e}")
            return {
                "success": False,
                "tool": "get_destination_timezone",
                "error": str(e)[:200],
            }

    async def close(self) -> None:
        pass


# Singleton for optional standalone use
_weather_mcp: Optional[WeatherMCP] = None


def get_weather_mcp() -> WeatherMCP:
    global _weather_mcp
    if _weather_mcp is None:
        _weather_mcp = WeatherMCP()
    return _weather_mcp
