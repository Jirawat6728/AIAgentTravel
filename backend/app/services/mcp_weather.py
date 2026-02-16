"""
MCP (Model Context Protocol) - เครื่องมือ Weather & Timezone
ใช้ Open-Meteo (ฟรี ไม่ต้องใช้ API key) สำหรับสภาพอากาศปลายทาง และ timezone
เพิ่มความแม่นยำในการวางแผน: อุณหภูมิ ฝน โอกาสพายุ เวลาท้องถิ่น
"""

from __future__ import annotations
from typing import Any, Dict, List, Optional
import asyncio
import httpx

from app.core.logging import get_logger
from app.services.travel_service import TravelOrchestrator

logger = get_logger(__name__)

OPEN_METEO_BASE = "https://api.open-meteo.com/v1"

# -----------------------------------------------------------------------------
# Weather & Timezone MCP Tool Definitions (Function Calling Schema for Gemini)
# -----------------------------------------------------------------------------

WEATHER_TOOLS = [
    {
        "name": "get_weather_forecast",
        "description": "Get weather forecast for a destination on a specific date using Open-Meteo. Returns max/min temperature (°C), precipitation (mm), and timezone. Use this to advise travelers on what to pack and best time to visit.",
        "parameters": {
            "type": "object",
            "properties": {
                "place_name": {
                    "type": "string",
                    "description": "City or place name (e.g., 'Bangkok', 'Tokyo', 'Phuket')"
                },
                "date": {
                    "type": "string",
                    "description": "Date in YYYY-MM-DD format (e.g., '2025-02-15')"
                },
                "latitude": {
                    "type": "number",
                    "description": "Optional: latitude if already known (skip place_name)"
                },
                "longitude": {
                    "type": "number",
                    "description": "Optional: longitude if already known (skip place_name)"
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


class WeatherMCP:
    """
    Weather & Timezone MCP executor using Open-Meteo (free, no API key).
    Uses TravelOrchestrator for geocoding when place_name is given.
    """

    def __init__(self, orchestrator: Optional[TravelOrchestrator] = None):
        self.orchestrator = orchestrator or TravelOrchestrator()
        logger.info("WeatherMCP initialized (Open-Meteo + TravelOrchestrator)")

    async def get_weather_forecast(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Get weather forecast for a place and date."""
        place_name = params.get("place_name", "").strip()
        date_str = params.get("date", "").strip()
        lat = params.get("latitude")
        lng = params.get("longitude")

        if not date_str:
            from datetime import datetime, timedelta
            date_str = (datetime.utcnow() + timedelta(days=1)).strftime("%Y-%m-%d")
        if not place_name and lat is None and lng is None:
            return {"success": False, "tool": "get_weather_forecast", "error": "Provide place_name or latitude/longitude"}

        try:
            if lat is None or lng is None:
                if not place_name:
                    return {"success": False, "tool": "get_weather_forecast", "error": "place_name or lat/lng required"}
                coords = await self.orchestrator.get_coordinates(place_name)
                lat, lng = coords["lat"], coords["lng"]
            else:
                place_name = place_name or f"{lat},{lng}"

            url = (
                f"{OPEN_METEO_BASE}/forecast"
                f"?latitude={lat}&longitude={lng}"
                "&daily=temperature_2m_max,temperature_2m_min,precipitation_sum,weather_code"
                "&timezone=auto"
                "&past_days=0"
            )
            if date_str:
                url += f"&start_date={date_str}&end_date={date_str}"

            async with httpx.AsyncClient(timeout=10.0) as client:
                resp = await client.get(url)
                resp.raise_for_status()
                data = resp.json()

            daily = data.get("daily", {})
            times = daily.get("time", [])
            tz = data.get("timezone", "UTC")
            tz_abbrev = data.get("timezone_abbreviation", "")

            if not times:
                return {
                    "success": True,
                    "tool": "get_weather_forecast",
                    "place": place_name,
                    "date": date_str or (times[0] if times else None),
                    "timezone": tz,
                    "timezone_abbreviation": tz_abbrev,
                    "message": "No daily data for this date; try a date within the next 16 days.",
                    "temperature_2m_max": None,
                    "temperature_2m_min": None,
                    "precipitation_sum_mm": None,
                    "weather_code": None,
                }

            idx = 0
            if date_str and times:
                try:
                    idx = times.index(date_str)
                except ValueError:
                    idx = 0

            t_max = daily.get("temperature_2m_max")
            t_min = daily.get("temperature_2m_min")
            precip = daily.get("precipitation_sum")
            wcode = daily.get("weather_code")

            def at(i: int, arr: Optional[List]) -> Any:
                if arr is None or i >= len(arr):
                    return None
                return arr[i]

            weather_desc = self._weather_code_to_desc(at(idx, wcode))

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
                "weather_code": at(idx, wcode),
                "weather_description": weather_desc,
            }
        except httpx.HTTPError as e:
            logger.warning(f"Open-Meteo request failed: {e}")
            return {"success": False, "tool": "get_weather_forecast", "error": str(e)[:200]}
        except Exception as e:
            logger.exception("get_weather_forecast failed")
            return {"success": False, "tool": "get_weather_forecast", "error": str(e)[:200]}

    def _weather_code_to_desc(self, code: Optional[int]) -> str:
        if code is None:
            return "Unknown"
        wmo = {
            0: "ท้องฟ้าแจ่มใส",
            1: "ส่วนใหญ่แจ่มใส",
            2: "มีเมฆบางส่วน",
            3: "เมฆมาก",
            45: "หมอก",
            48: "หมอกน้ำค้าง",
            51: "ฝนตกปรายเล็กน้อย",
            53: "ฝนตกปราย",
            55: "ฝนตกปรายหนาแน่น",
            61: "ฝนตกเล็กน้อย",
            63: "ฝนตกปานกลาง",
            65: "ฝนตกหนัก",
            71: "หิมะตกเล็กน้อย",
            73: "หิมะตกปานกลาง",
            75: "หิมะตกหนัก",
            80: "ฝนตกเป็นช่วงๆ",
            81: "ฝนตกเป็นช่วงๆ ค่อนข้างหนัก",
            82: "ฝนตกเป็นช่วงๆ หนักมาก",
            95: "พายุฝนฟ้าคะนอง",
            96: "พายุฝนฟ้าคะนองพร้อมลูกเห็บ",
        }
        return wmo.get(int(code), "Unknown")

    async def get_destination_timezone(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Get timezone and current local time for a destination."""
        place_name = (params.get("place_name") or "").strip()
        if not place_name:
            return {"success": False, "tool": "get_destination_timezone", "error": "place_name required"}

        try:
            coords = await self.orchestrator.get_coordinates(place_name)
            lat, lng = coords["lat"], coords["lng"]

            url = (
                f"{OPEN_METEO_BASE}/forecast"
                f"?latitude={lat}&longitude={lng}"
                "&current=time"
                "&timezone=auto"
            )
            async with httpx.AsyncClient(timeout=10.0) as client:
                resp = await client.get(url)
                resp.raise_for_status()
                data = resp.json()

            tz = data.get("timezone", "UTC")
            tz_abbrev = data.get("timezone_abbreviation", "")
            current = data.get("current", {})
            local_time = current.get("time")

            return {
                "success": True,
                "tool": "get_destination_timezone",
                "place": place_name,
                "timezone": tz,
                "timezone_abbreviation": tz_abbrev,
                "local_time_iso": local_time,
                "coordinates": {"latitude": lat, "longitude": lng},
            }
        except Exception as e:
            logger.warning(f"get_destination_timezone failed: {e}")
            return {"success": False, "tool": "get_destination_timezone", "error": str(e)[:200]}

    async def close(self) -> None:
        pass


# Singleton for optional use
_weather_mcp: Optional[WeatherMCP] = None


def get_weather_mcp() -> WeatherMCP:
    global _weather_mcp
    if _weather_mcp is None:
        _weather_mcp = WeatherMCP()
    return _weather_mcp
