"""
MCP (Model Context Protocol) - เครื่องมือ Amadeus API
นิยามและตัวดำเนินการสำหรับเที่ยวบิน โรงแรม การรับส่ง กิจกรรม
"""

from __future__ import annotations
from typing import Any, Dict, List, Optional
import asyncio
from datetime import datetime, timedelta

from app.core.logging import get_logger
from app.core.exceptions import AmadeusException, AgentException
from app.services.travel_service import TravelOrchestrator

logger = get_logger(__name__)

# -----------------------------------------------------------------------------
# Amadeus MCP Tool Definitions (Function Calling Schema for Gemini)
# -----------------------------------------------------------------------------

AMADEUS_TOOLS = [
    {
        "name": "search_flights",
        "description": "Search for flight offers using Amadeus API. Returns up to 10 flight options with prices, airlines, and schedules.",
        "parameters": {
            "type": "object",
            "properties": {
                "origin": {
                    "type": "string",
                    "description": "Origin airport IATA code (e.g., 'BKK') or city name (e.g., 'Bangkok')"
                },
                "destination": {
                    "type": "string",
                    "description": "Destination airport IATA code (e.g., 'NRT') or city name (e.g., 'Tokyo')"
                },
                "departure_date": {
                    "type": "string",
                    "description": "Departure date in YYYY-MM-DD format (e.g., '2025-02-15')"
                },
                "adults": {
                    "type": "integer",
                    "description": "Number of adult passengers (default: 1)",
                    "default": 1
                },
                "return_date": {
                    "type": "string",
                    "description": "Optional return date for round-trip in YYYY-MM-DD format"
                }
            },
            "required": ["origin", "destination", "departure_date"]
        }
    },
    {
        "name": "search_hotels",
        "description": "Search for hotel offers using Amadeus API. Returns up to 10 hotel options with prices, ratings, and locations.",
        "parameters": {
            "type": "object",
            "properties": {
                "location": {
                    "type": "string",
                    "description": "City name or IATA code (e.g., 'Tokyo' or 'TYO')"
                },
                "check_in": {
                    "type": "string",
                    "description": "Check-in date in YYYY-MM-DD format"
                },
                "check_out": {
                    "type": "string",
                    "description": "Check-out date in YYYY-MM-DD format"
                },
                "guests": {
                    "type": "integer",
                    "description": "Number of guests (default: 1)",
                    "default": 1
                }
            },
            "required": ["location", "check_in", "check_out"]
        }
    },
    {
        "name": "search_transfers",
        "description": "Search for ground transfer options (taxis, private cars, shuttles) using Amadeus API.",
        "parameters": {
            "type": "object",
            "properties": {
                "origin": {
                    "type": "string",
                    "description": "Origin location (airport code or address)"
                },
                "destination": {
                    "type": "string",
                    "description": "Destination address or location name"
                },
                "date": {
                    "type": "string",
                    "description": "Transfer date in YYYY-MM-DD format"
                },
                "passengers": {
                    "type": "integer",
                    "description": "Number of passengers (default: 1)",
                    "default": 1
                }
            },
            "required": ["origin", "destination", "date"]
        }
    },
    {
        "name": "search_transfers_by_geo",
        "description": "Search for transfers using exact GPS coordinates. More precise than address search. Use 'geocode_location' first to get coordinates.",
        "parameters": {
            "type": "object",
            "properties": {
                "start_lat": {"type": "number", "description": "Start location latitude"},
                "start_lng": {"type": "number", "description": "Start location longitude"},
                "end_lat": {"type": "number", "description": "End location latitude"},
                "end_lng": {"type": "number", "description": "End location longitude"},
                "start_time": {
                    "type": "string",
                    "description": "Start date/time in YYYY-MM-DDTHH:MM:SS format (e.g., 2025-02-15T10:00:00)"
                },
                "passengers": {
                    "type": "integer",
                    "description": "Number of passengers (default: 1)",
                    "default": 1
                }
            },
            "required": ["start_lat", "start_lng", "end_lat", "end_lng", "start_time"]
        }
    },
    {
        "name": "search_activities",
        "description": "Search for tours, activities, and experiences using Amadeus API.",
        "parameters": {
            "type": "object",
            "properties": {
                "location": {
                    "type": "string",
                    "description": "City name or location (e.g., 'Tokyo', 'Paris')"
                },
                "radius": {
                    "type": "integer",
                    "description": "Search radius in kilometers (default: 10)",
                    "default": 10
                }
            },
            "required": ["location"]
        }
    }
]


class AmadeusMCP:
    """
    Amadeus MCP executor: flights, hotels, transfers, activities.
    Uses TravelOrchestrator for Amadeus API calls.
    """

    def __init__(self, orchestrator: Optional[TravelOrchestrator] = None):
        self.orchestrator = orchestrator or TravelOrchestrator()
        logger.info("AmadeusMCP initialized with TravelOrchestrator")

    def _normalize_flight_date(self, date_str: Optional[str]) -> Optional[str]:
        """Ensure date is YYYY-MM-DD (Christian year). Convert Buddhist year if needed."""
        if not date_str or not isinstance(date_str, str):
            return None
        date_str = date_str.strip()
        if not date_str:
            return None
        try:
            parts = date_str.split("-")
            if len(parts) == 3:
                y, m, d = int(parts[0]), int(parts[1]), int(parts[2])
                if y > 2100:
                    y = y - 543
                return f"{y:04d}-{m:02d}-{d:02d}"
        except (ValueError, IndexError):
            pass
        return date_str

    async def search_flights(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Search flights using Amadeus API. Returns raw Amadeus data in 'flights' for pipeline normalization."""
        origin = (params.get("origin") or "BKK").strip() or "BKK"
        destination = (params.get("destination") or "NRT").strip() or "NRT"
        departure_date = params.get("departure_date") or params.get("date")
        adults = max(1, int(params.get("adults", 1) or params.get("guests", 1)))

        departure_date = self._normalize_flight_date(departure_date)
        if not departure_date:
            departure_date = (datetime.now() + timedelta(days=7)).strftime("%Y-%m-%d")
            logger.info(f"📅 No departure_date provided, using default: {departure_date}")

        # ✅ บินตรง: ใช้ non_stop จาก params (เมื่อผู้ใช้ขอ "บินตรง" / direct)
        non_stop = params.get("non_stop") is True or params.get("direct_flight") is True
        logger.info(f"🔍 Searching flights: {origin} → {destination} on {departure_date} for {adults} adult(s) (non_stop={non_stop})")

        try:
            results = await self.orchestrator.get_flights(
                origin=origin,
                destination=destination,
                departure_date=departure_date,
                adults=adults,
                non_stop=non_stop,
            )
            logger.info(f"📊 Amadeus API returned {len(results) if results else 0} flight results")

            # ✅ Validate: ถ้าขอบินตรง ให้กรองเฉพาะเที่ยวบินที่จริงๆ เป็น non-stop (ป้องกัน API คืนต่อเครื่องมา)
            if non_stop and results:
                def _is_non_stop_offer(offer: dict) -> bool:
                    itins = offer.get("itineraries") or []
                    for itin in itins:
                        if len(itin.get("segments") or []) > 1:
                            return False
                    return True
                before = len(results)
                results = [r for r in results if _is_non_stop_offer(r)]
                if before > len(results):
                    logger.warning(f"✅ Validated non-stop: filtered out {before - len(results)} connecting offers (kept {len(results)} direct)")

            if not results or len(results) == 0:
                try:
                    search_date = datetime.strptime(departure_date, "%Y-%m-%d")
                    today = datetime.now()
                    days_ahead = (search_date - today).days
                    max_days = 330
                    date_warning = ""
                    if days_ahead < 0:
                        date_warning = f"⚠️ Date is in the past ({-days_ahead} days ago)"
                    elif days_ahead > max_days:
                        date_warning = f"⚠️ Date is {days_ahead} days ahead (max: {max_days} days) - Amadeus may not have data"
                except Exception:
                    date_warning = ""

                logger.error(
                    f"❌ No flights found for {origin} → {destination} on {departure_date}\n"
                    f"   {date_warning}"
                )
                return {
                    "success": True,
                    "tool": "search_flights",
                    "results_count": 0,
                    "flights": [],
                    "message": f"No flights found for {origin} → {destination} on {departure_date}. {date_warning or 'Please try different dates or check route availability.'}",
                    "search_params": {
                        "origin": origin,
                        "destination": destination,
                        "date": departure_date,
                        "adults": adults
                    },
                    "diagnostics": {
                        "date_warning": date_warning,
                        "suggestion": "Try dates within 11 months from today or check if route is available",
                    }
                }
            return {
                "success": True,
                "tool": "search_flights",
                "results_count": len(results),
                "flights": results,
                "search_params": {
                    "origin": origin,
                    "destination": destination,
                    "date": departure_date,
                    "adults": adults,
                    "non_stop": non_stop,
                }
            }
        except Exception as e:
            logger.error(f"❌ Error searching flights: {e}", exc_info=True)
            return {
                "success": False,
                "tool": "search_flights",
                "error": str(e),
                "results_count": 0,
                "flights": [],
                "search_params": {"origin": origin, "destination": destination, "date": departure_date, "adults": adults}
            }

    async def search_hotels(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Search hotels using Amadeus API with error handling."""
        try:
            location = params.get("location") or params.get("location_name", "Tokyo")
            check_in = params.get("check_in")
            check_out = params.get("check_out")
            guests = params.get("guests", 1)

            if not location:
                raise AgentException("Location is required")
            if not check_in or not check_out:
                raise AgentException("Check-in and check-out dates are required")
            if guests < 1 or guests > 9:
                raise AgentException("Guests must be between 1 and 9")

            try:
                check_in_date = datetime.fromisoformat(check_in)
                check_out_date = datetime.fromisoformat(check_out)
                if check_out_date <= check_in_date:
                    raise AgentException("Check-out date must be after check-in date")
            except ValueError:
                raise AgentException("Invalid date format. Use YYYY-MM-DD")

            logger.info(f"🔍 Searching hotels: {location} from {check_in} to {check_out} for {guests} guest(s)")

            results = await self.orchestrator.get_hotels(
                location_name=location,
                check_in=check_in,
                check_out=check_out,
                guests=guests
            )
            logger.info(f"📊 Amadeus API returned {len(results) if results else 0} hotel results")

            # Fallback: try ±1 day if no results
            if not results or len(results) == 0:
                try:
                    check_in_dt = datetime.fromisoformat(check_in)
                    check_out_dt = datetime.fromisoformat(check_out)
                    fallback_dates = [
                        ((check_in_dt + timedelta(days=-1)).strftime("%Y-%m-%d"),
                         (check_out_dt + timedelta(days=-1)).strftime("%Y-%m-%d")),
                        ((check_in_dt + timedelta(days=1)).strftime("%Y-%m-%d"),
                         (check_out_dt + timedelta(days=1)).strftime("%Y-%m-%d"))
                    ]
                    for fb_check_in, fb_check_out in fallback_dates[:1]:
                        fb_results = await asyncio.wait_for(
                            self.orchestrator.get_hotels(
                                location_name=location,
                                check_in=fb_check_in,
                                check_out=fb_check_out,
                                guests=guests
                            ),
                            timeout=5.0
                        )
                        if fb_results and len(fb_results) > 0:
                            for item in fb_results:
                                item["_fallback_check_in"] = fb_check_in
                                item["_fallback_check_out"] = fb_check_out
                            results = fb_results[:3]
                            break
                except Exception as e:
                    logger.warning(f"Fallback hotel search failed: {e}")

            if not results or len(results) == 0:
                date_warning = ""
                try:
                    check_in_dt = datetime.fromisoformat(check_in)
                    days_ahead = (check_in_dt - datetime.now()).days
                    if days_ahead < 0:
                        date_warning = f"⚠️ Check-in date is in the past"
                    elif days_ahead > 330:
                        date_warning = f"⚠️ Check-in date is {days_ahead} days ahead - Amadeus may not have data"
                except Exception:
                    pass
                return {
                    "success": True,
                    "tool": "search_hotels",
                    "results_count": 0,
                    "hotels": [],
                    "message": f"No hotels found in {location} for {check_in} to {check_out}. {date_warning or 'Please try different dates.'}",
                    "search_params": {"location": location, "check_in": check_in, "check_out": check_out, "guests": guests},
                    "diagnostics": {"date_warning": date_warning}
                }

            fallback_results = [r for r in results if r.get("_fallback_check_in")]
            original_results = [r for r in results if not r.get("_fallback_check_in")]
            display_results = (original_results[:3] if len(original_results) >= 3 else original_results) + fallback_results[:2]

            formatted = []
            for idx, hotel in enumerate(display_results[:3]):
                try:
                    hotel_data = hotel.get("hotel", {})
                    offers = hotel.get("offers", [])
                    if not offers:
                        continue
                    first_offer = offers[0]
                    price = first_offer.get("price", {})
                    formatted.append({
                        "option_number": idx + 1,
                        "name": hotel_data.get("name", "Unknown Hotel"),
                        "rating": hotel_data.get("rating", 0),
                        "address": hotel_data.get("address", {}).get("lines", [""])[0] if hotel_data.get("address", {}).get("lines") else "",
                        "price": {"total": price.get("total", "0"), "currency": price.get("currency", "THB")},
                        "room_type": first_offer.get("room", {}).get("typeEstimated", {}).get("category", "Standard")
                    })
                except Exception as e:
                    logger.warning(f"Error formatting hotel {idx + 1}: {e}")
                    continue

            return {
                "success": True,
                "tool": "search_hotels",
                "results_count": len(formatted),
                "hotels": formatted,
                "search_params": {"location": location, "check_in": check_in, "check_out": check_out, "guests": guests}
            }
        except AmadeusException as e:
            logger.error(f"Amadeus API error in search_hotels: {e}")
            return {"success": False, "tool": "search_hotels", "error": f"Amadeus API error: {str(e)}", "search_params": params}
        except Exception as e:
            logger.error(f"Unexpected error in search_hotels: {e}", exc_info=True)
            return {"success": False, "tool": "search_hotels", "error": str(e), "search_params": params}

    async def search_transfers(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Search transfers using Amadeus API."""
        origin = params.get("origin", "")
        destination = params.get("destination", "")
        date = params.get("date", "")
        passengers = params.get("passengers", 1)

        airport_code = None
        if isinstance(origin, str) and len(origin) == 3 and origin.isupper():
            airport_code = origin
        else:
            try:
                loc = await self.orchestrator.get_coordinates(origin)
                airport_code = await self.orchestrator.find_nearest_iata(loc["lat"], loc["lng"])
            except Exception as e:
                logger.error(f"Could not resolve transfer origin from '{origin}': {e}")
                return {"success": False, "tool": "search_transfers", "error": f"Could not resolve origin airport from '{origin}'"}

        results = await self.orchestrator.get_transfers(airport_code=airport_code, address=destination)
        formatted = []
        for idx, transfer in enumerate(results[:5]):
            vehicle = transfer.get("vehicle", {})
            price = transfer.get("price", {})
            formatted.append({
                "option_number": idx + 1,
                "vehicle_type": vehicle.get("type", "Car"),
                "category": vehicle.get("category", "Standard"),
                "capacity": vehicle.get("capacity", 0),
                "price": {"total": price.get("total", "0"), "currency": price.get("currency", "THB")}
            })
        return {
            "success": True,
            "tool": "search_transfers",
            "results_count": len(formatted),
            "transfers": formatted,
            "search_params": {"origin": origin, "destination": destination, "date": date, "passengers": passengers}
        }

    async def search_transfers_by_geo(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Search transfers using exact geo coordinates."""
        start_lat = params.get("start_lat")
        start_lng = params.get("start_lng")
        end_lat = params.get("end_lat")
        end_lng = params.get("end_lng")
        start_time = params.get("start_time")
        passengers = params.get("passengers", 1)

        results = await self.orchestrator.get_transfers_by_geo(
            start_lat=start_lat, start_lng=start_lng,
            end_lat=end_lat, end_lng=end_lng,
            start_time=start_time, passengers=passengers
        )
        formatted = []
        for idx, transfer in enumerate(results[:5]):
            vehicle = transfer.get("vehicle", {})
            price = transfer.get("price", {})
            quotation = transfer.get("quotation", {})
            formatted.append({
                "option_number": idx + 1,
                "vehicle_type": vehicle.get("type", "Car"),
                "category": vehicle.get("category", "Standard"),
                "capacity": vehicle.get("capacity", 0),
                "price": {"total": price.get("total", "0"), "currency": price.get("currency", "THB")},
                "provider": transfer.get("transferType", "PRIVATE"),
                "duration": quotation.get("duration", "N/A"),
                "distance": quotation.get("distance", "N/A")
            })
        return {
            "success": True,
            "tool": "search_transfers_by_geo",
            "results_count": len(formatted),
            "transfers": formatted,
            "search_params": {
                "start_coords": f"{start_lat},{start_lng}",
                "end_coords": f"{end_lat},{end_lng}",
                "start_time": start_time,
                "passengers": passengers
            }
        }

    async def search_activities(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Search activities using Amadeus API."""
        location = params.get("location", "Tokyo")
        radius = params.get("radius", 10)
        try:
            loc_info = await self.orchestrator.get_coordinates(location)
            lat, lng = loc_info["lat"], loc_info["lng"]
        except Exception as e:
            logger.warning(f"Could not geocode {location}: {e}")
            lat, lng = 35.6762, 139.6503

        results = await self.orchestrator.get_activities(lat, lng)
        formatted = []
        for idx, activity in enumerate(results[:3]):
            price = activity.get("price", {})
            formatted.append({
                "option_number": idx + 1,
                "name": activity.get("name", "Activity"),
                "description": (activity.get("shortDescription", "") or "")[:200],
                "price": {"amount": price.get("amount", "0"), "currency": price.get("currencyCode", "THB")},
                "rating": activity.get("rating", 0),
                "pictures": (activity.get("pictures", []) or [])[:1]
            })
        return {
            "success": True,
            "tool": "search_activities",
            "results_count": len(formatted),
            "activities": formatted,
            "search_params": {"location": location, "radius": radius}
        }

    async def close(self):
        """Cleanup resources."""
        try:
            if self.orchestrator:
                await self.orchestrator.close()
            logger.info("AmadeusMCP closed successfully")
        except Exception as e:
            logger.warning(f"Error closing AmadeusMCP: {e}")
