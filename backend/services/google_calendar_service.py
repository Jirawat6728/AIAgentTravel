"""
Google Calendar API service for trip planning.
Features:
- Check Public Holidays by country
- Create calendar events for trips
- Set up travel reminders
"""
from __future__ import annotations

import os
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional
import json

try:
    import httpx
    HTTPX_AVAILABLE = True
except ImportError:
    HTTPX_AVAILABLE = False
    import requests


GOOGLE_CALENDAR_API_KEY = os.getenv("GOOGLE_CALENDAR_API_KEY", "")
GOOGLE_CALENDAR_API_ENABLED = bool(GOOGLE_CALENDAR_API_KEY)

# Country code mapping (for Public Holidays API)
COUNTRY_CODE_MAP = {
    "ไทย": "th",
    "thailand": "th",
    "ญี่ปุ่น": "jp",
    "japan": "jp",
    "เกาหลี": "kr",
    "korea": "kr",
    "จีน": "cn",
    "china": "cn",
    "สิงคโปร์": "sg",
    "singapore": "sg",
    "มาเลเซีย": "my",
    "malaysia": "my",
    "เวียดนาม": "vn",
    "vietnam": "vn",
    "ฟิลิปปินส์": "ph",
    "philippines": "ph",
    "อินโดนีเซีย": "id",
    "indonesia": "id",
    "อินเดีย": "in",
    "india": "in",
    "ออสเตรเลีย": "au",
    "australia": "au",
    "สหรัฐอเมริกา": "us",
    "usa": "us",
    "united states": "us",
    "อังกฤษ": "gb",
    "uk": "gb",
    "united kingdom": "gb",
    "ฝรั่งเศส": "fr",
    "france": "fr",
    "เยอรมนี": "de",
    "germany": "de",
    "อิตาลี": "it",
    "italy": "it",
    "สเปน": "es",
    "spain": "es",
}


async def get_public_holidays(
    country: str,
    year: Optional[int] = None,
    month: Optional[int] = None
) -> Dict[str, Any]:
    """
    Get Public Holidays for a country using external API (holidays-api.com or similar).
    
    Args:
        country: Country name (Thai or English)
        year: Year (default: current year)
        month: Month (optional, 1-12)
    
    Returns:
        Dict with holidays list and metadata
    """
    if not year:
        year = datetime.now().year
    
    # Map country name to country code
    country_lower = country.lower().strip()
    country_code = COUNTRY_CODE_MAP.get(country_lower)
    
    if not country_code:
        # Try to find partial match
        for key, code in COUNTRY_CODE_MAP.items():
            if country_lower in key or key in country_lower:
                country_code = code
                break
    
    if not country_code:
        return {
            "ok": False,
            "error": f"Country '{country}' not found or not supported",
            "holidays": [],
        }
    
    # Use holidays-api.com (free public API)
    # Alternative: Use Google Calendar API or other holiday APIs
    base_url = f"https://date.nager.at/api/v3/PublicHolidays/{year}/{country_code.upper()}"
    
    try:
        if HTTPX_AVAILABLE:
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.get(base_url)
                if response.status_code == 200:
                    holidays_data = response.json()
                else:
                    return {
                        "ok": False,
                        "error": f"API returned status {response.status_code}",
                        "holidays": [],
                    }
        else:
            import requests
            response = requests.get(base_url, timeout=10.0)
            if response.status_code == 200:
                holidays_data = response.json()
            else:
                return {
                    "ok": False,
                    "error": f"API returned status {response.status_code}",
                    "holidays": [],
                }
        
        # Filter by month if specified
        holidays = []
        for holiday in holidays_data:
            holiday_date = datetime.fromisoformat(holiday["date"])
            if month and holiday_date.month != month:
                continue
            
            holidays.append({
                "date": holiday["date"],
                "name": holiday.get("name", ""),
                "local_name": holiday.get("localName", ""),
                "country_code": country_code.upper(),
                "fixed": holiday.get("fixed", False),
                "global": holiday.get("global", False),
                "counties": holiday.get("counties"),
                "launch_year": holiday.get("launchYear"),
            })
        
        # Sort by date
        holidays.sort(key=lambda x: x["date"])
        
        return {
            "ok": True,
            "country": country,
            "country_code": country_code.upper(),
            "year": year,
            "month": month,
            "holidays": holidays,
            "count": len(holidays),
        }
    
    except Exception as e:
        return {
            "ok": False,
            "error": str(e),
            "holidays": [],
        }


async def check_holidays_for_trip(
    destination: str,
    start_date: str,
    end_date: Optional[str] = None,
    nights: Optional[int] = None
) -> Dict[str, Any]:
    """
    Check if trip dates overlap with Public Holidays.
    
    Args:
        destination: Destination country/city
        start_date: Trip start date (YYYY-MM-DD)
        end_date: Trip end date (YYYY-MM-DD, optional)
        nights: Number of nights (optional, to calculate end_date)
    
    Returns:
        Dict with overlapping holidays and suggestions
    """
    try:
        start = datetime.fromisoformat(start_date)
        year = start.year
        month = start.month
        
        # Calculate end_date if not provided
        if not end_date and nights:
            end = start + timedelta(days=nights)
            end_date = end.isoformat()[:10]
        
        # Get holidays for the destination country
        holidays_result = await get_public_holidays(destination, year=year, month=month)
        
        if not holidays_result.get("ok"):
            return {
                "ok": False,
                "error": holidays_result.get("error"),
                "overlapping_holidays": [],
                "nearby_holidays": [],
            }
        
        holidays = holidays_result.get("holidays", [])
        
        # Find overlapping holidays
        overlapping = []
        nearby = []
        start_dt = datetime.fromisoformat(start_date)
        end_dt = datetime.fromisoformat(end_date) if end_date else start_dt + timedelta(days=7)
        
        for holiday in holidays:
            holiday_dt = datetime.fromisoformat(holiday["date"])
            
            # Check if holiday is during trip
            if start_dt <= holiday_dt <= end_dt:
                overlapping.append(holiday)
            # Check if holiday is within 7 days before/after trip
            elif abs((holiday_dt - start_dt).days) <= 7:
                nearby.append(holiday)
        
        return {
            "ok": True,
            "destination": destination,
            "trip_start": start_date,
            "trip_end": end_date,
            "overlapping_holidays": overlapping,
            "nearby_holidays": nearby,
            "suggestion": (
                f"พบวันหยุดนักขัตฤกษ์ในช่วงทริป" if overlapping else
                f"พบวันหยุดนักขัตฤกษ์ใกล้กับช่วงทริป" if nearby else
                "ไม่มีวันหยุดนักขัตฤกษ์ในช่วงทริป"
            ),
        }
    
    except Exception as e:
        return {
            "ok": False,
            "error": str(e),
            "overlapping_holidays": [],
            "nearby_holidays": [],
        }


async def create_calendar_event(
    summary: str,
    start_date: str,
    end_date: Optional[str] = None,
    description: Optional[str] = None,
    location: Optional[str] = None,
    reminders_minutes: Optional[List[int]] = None,  # [1440, 60] = 1 day before, 1 hour before
) -> Dict[str, Any]:
    """
    Create a calendar event (for future integration with Google Calendar API).
    Currently returns event structure that can be used with Google Calendar API.
    
    Args:
        summary: Event title
        start_date: Start date (YYYY-MM-DD or ISO format)
        end_date: End date (YYYY-MM-DD or ISO format, optional)
        description: Event description
        location: Event location
        reminders_minutes: List of reminder minutes before event
    
    Returns:
        Dict with event data (ready for Google Calendar API)
    """
    try:
        start_dt = datetime.fromisoformat(start_date[:10])
        if end_date:
            end_dt = datetime.fromisoformat(end_date[:10])
        else:
            # Default: same day event
            end_dt = start_dt + timedelta(days=1)
        
        # Build event structure (Google Calendar API format)
        event = {
            "summary": summary,
            "description": description or "",
            "location": location or "",
            "start": {
                "date": start_dt.strftime("%Y-%m-%d"),
                "timeZone": "Asia/Bangkok",
            },
            "end": {
                "date": end_dt.strftime("%Y-%m-%d"),
                "timeZone": "Asia/Bangkok",
            },
        }
        
        # Add reminders
        if reminders_minutes:
            event["reminders"] = {
                "useDefault": False,
                "overrides": [
                    {"method": "popup", "minutes": minutes}
                    for minutes in reminders_minutes
                ],
            }
        else:
            # Default reminders: 1 day before and 1 hour before
            event["reminders"] = {
                "useDefault": False,
                "overrides": [
                    {"method": "popup", "minutes": 1440},  # 1 day before
                    {"method": "popup", "minutes": 60},    # 1 hour before
                ],
            }
        
        return {
            "ok": True,
            "event": event,
            "calendar_link": None,  # Will be populated when integrated with Google Calendar API
        }
    
    except Exception as e:
        return {
            "ok": False,
            "error": str(e),
            "event": None,
        }


async def create_trip_calendar_event(
    trip_title: str,
    destination: str,
    start_date: str,
    nights: int,
    reminders_days_before: Optional[List[int]] = None,  # [7, 3, 1] = 7 days, 3 days, 1 day before
) -> Dict[str, Any]:
    """
    Create a calendar event for a trip with travel reminders.
    
    Args:
        trip_title: Trip title
        destination: Destination
        start_date: Start date (YYYY-MM-DD)
        nights: Number of nights
        reminders_days_before: List of days before trip to remind (default: [7, 3, 1])
    
    Returns:
        Dict with event data
    """
    start_dt = datetime.fromisoformat(start_date[:10])
    end_dt = start_dt + timedelta(days=nights)
    end_date = end_dt.strftime("%Y-%m-%d")
    
    # Convert days to minutes for reminders
    if reminders_days_before:
        reminders_minutes = [days * 24 * 60 for days in reminders_days_before]
    else:
        reminders_minutes = [7 * 24 * 60, 3 * 24 * 60, 1 * 24 * 60]  # 7 days, 3 days, 1 day before
    
    description = f"ทริป: {trip_title}\nปลายทาง: {destination}\nระยะเวลา: {nights} คืน"
    
    return await create_calendar_event(
        summary=f"✈️ {trip_title}",
        start_date=start_date,
        end_date=end_date,
        description=description,
        location=destination,
        reminders_minutes=reminders_minutes,
    )

