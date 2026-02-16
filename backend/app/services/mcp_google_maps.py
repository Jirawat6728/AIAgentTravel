"""
MCP (Model Context Protocol) - เครื่องมือ Google Maps
นิยามและตัวดำเนินการ: geocoding สถานที่ เส้นทาง การเปรียบเทียบการเดินทาง
"""

from __future__ import annotations
from typing import Any, Dict, Optional
import asyncio
from math import radians, sin, cos, sqrt, atan2

from app.core.logging import get_logger
from app.services.travel_service import TravelOrchestrator
from app.services.google_maps_client import get_google_maps_client

logger = get_logger(__name__)

# -----------------------------------------------------------------------------
# Google Maps MCP Tool Definitions (Function Calling Schema for Gemini)
# -----------------------------------------------------------------------------

GOOGLE_MAPS_TOOLS = [
    {
        "name": "geocode_location",
        "description": "Convert a place name or address to geographic coordinates (latitude, longitude) using Google Maps API.",
        "parameters": {
            "type": "object",
            "properties": {
                "place_name": {
                    "type": "string",
                    "description": "Place name, address, or landmark (e.g., 'Eiffel Tower', 'Tokyo Station', '123 Main St, Bangkok')"
                }
            },
            "required": ["place_name"]
        }
    },
    {
        "name": "find_nearest_airport",
        "description": "Find the nearest airport IATA code for a given location using Google Maps and Amadeus APIs.",
        "parameters": {
            "type": "object",
            "properties": {
                "location": {
                    "type": "string",
                    "description": "City name or place (e.g., 'Chiang Mai', 'Phuket')"
                }
            },
            "required": ["location"]
        }
    },
    {
        "name": "search_nearby_places",
        "description": "Search for nearby places (attractions, restaurants, etc.) using Google Maps Places API. Returns top 5 results with name, place_id, rating, user_ratings_total, vicinity, and types.",
        "parameters": {
            "type": "object",
            "properties": {
                "keyword": {
                    "type": "string",
                    "description": "Search keyword (e.g., 'restaurant', 'tourist attraction', 'museum', 'hotel')"
                },
                "lat": {"type": "number", "description": "Latitude of the center point"},
                "lng": {"type": "number", "description": "Longitude of the center point"},
                "radius": {
                    "type": "integer",
                    "description": "Search radius in meters (default: 1000, max: 50000)",
                    "default": 1000
                }
            },
            "required": ["keyword", "lat", "lng"]
        }
    },
    {
        "name": "get_place_details",
        "description": "Get detailed information about a place using Google Maps API. Requires place_id from search_nearby_places or geocode_location. Returns formatted_address, opening_hours, photo_reference (1 photo), and review_summary (top 1 review).",
        "parameters": {
            "type": "object",
            "properties": {
                "place_id": {
                    "type": "string",
                    "description": "Google Place ID (obtained from search_nearby_places or geocode_location)"
                }
            },
            "required": ["place_id"]
        }
    },
    {
        "name": "plan_route",
        "description": "Plan a route from origin to destination using Google Maps Directions API. Returns detailed route information including distance, duration, and recommended transportation methods (flight, car, train, bus). Use this to determine which airports to use and optimal transportation methods.",
        "parameters": {
            "type": "object",
            "properties": {
                "origin": {
                    "type": "string",
                    "description": "Origin location (place name, address, or coordinates like 'lat,lng')"
                },
                "destination": {
                    "type": "string",
                    "description": "Destination location (place name, address, or coordinates like 'lat,lng')"
                },
                "travel_mode": {
                    "type": "string",
                    "description": "Preferred travel mode: 'driving', 'walking', 'transit', 'bicycling'. Default is 'driving' for road routes. Use 'transit' to check train/bus availability.",
                    "enum": ["driving", "walking", "transit", "bicycling"],
                    "default": "driving"
                }
            },
            "required": ["origin", "destination"]
        }
    },
    {
        "name": "plan_route_with_waypoints",
        "description": "Plan a route from origin to destination passing through waypoints (จุดแวะ) using Google Maps Directions API. Use for multi-city or multi-stop trips. Returns legs (origin→waypoint1→waypoint2→destination), total distance, duration, and coordinates for each stop. Waypoints can be place names, addresses, or 'lat,lng'.",
        "parameters": {
            "type": "object",
            "properties": {
                "origin": {
                    "type": "string",
                    "description": "Origin location (place name, address, or 'lat,lng')"
                },
                "destination": {
                    "type": "string",
                    "description": "Final destination (place name, address, or 'lat,lng')"
                },
                "waypoints": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "List of intermediate stops (จุดแวะ), e.g. [\"Kyoto\", \"Osaka\"] for Origin → Kyoto → Osaka → Destination"
                },
                "travel_mode": {
                    "type": "string",
                    "description": "Travel mode: 'driving', 'walking', 'transit', 'bicycling'",
                    "enum": ["driving", "walking", "transit", "bicycling"],
                    "default": "driving"
                }
            },
            "required": ["origin", "destination"]
        }
    },
    {
        "name": "compare_transport_modes",
        "description": "Compare different transport modes (driving, transit, walking) between two local places. Use this to decide whether to take a taxi, public transport, or walk between two local places. Returns duration, distance, and cost information for each available mode.",
        "parameters": {
            "type": "object",
            "properties": {
                "origin": {
                    "type": "string",
                    "description": "Origin location (place name, address, or coordinates like 'lat,lng')"
                },
                "destination": {
                    "type": "string",
                    "description": "Destination location (place name, address, or coordinates like 'lat,lng')"
                }
            },
            "required": ["origin", "destination"]
        }
    }
]


class GoogleMapsMCP:
    """
    Google Maps MCP executor: geocoding, places, routes, transport comparison.
    Uses Google Maps client and TravelOrchestrator (for coordinates + nearest airport).
    """

    def __init__(
        self,
        google_maps_client=None,
        orchestrator: Optional[TravelOrchestrator] = None
    ):
        self.google_maps_client = google_maps_client or get_google_maps_client()
        self.orchestrator = orchestrator or TravelOrchestrator()
        logger.info("GoogleMapsMCP initialized with GoogleMapsClient and TravelOrchestrator")

    async def geocode_location(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Geocode a location using Google Maps API."""
        place_name = params.get("place_name", "")
        try:
            result = await self.google_maps_client.geocode_location(place_name)
            return {
                "success": True,
                "tool": "geocode_location",
                "location": {
                    "place_name": place_name,
                    "latitude": result["lat"],
                    "longitude": result["lng"],
                    "formatted_address": result["address"]
                }
            }
        except Exception as e:
            logger.error(f"Geocode location failed: {e}", exc_info=True)
            return {"success": False, "tool": "geocode_location", "error": f"Could not geocode '{place_name}': {str(e)}"}

    async def find_nearest_airport(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Find nearest airport IATA code using orchestrator (coordinates + Amadeus IATA)."""
        location = params.get("location", "")
        try:
            loc_info = await self.orchestrator.get_coordinates(location)
            iata = await self.orchestrator.find_nearest_iata(loc_info["lat"], loc_info["lng"])
            return {
                "success": True,
                "tool": "find_nearest_airport",
                "location": location,
                "nearest_airport": {
                    "iata_code": iata,
                    "coordinates": {"latitude": loc_info["lat"], "longitude": loc_info["lng"]}
                }
            }
        except Exception as e:
            return {"success": False, "tool": "find_nearest_airport", "error": f"Could not find airport for '{location}': {str(e)}"}

    async def search_nearby_places(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Search for nearby places using Google Maps API."""
        keyword = params.get("keyword", "")
        lat = params.get("lat")
        lng = params.get("lng")
        radius = params.get("radius", 1000)
        try:
            results = await self.google_maps_client.search_nearby_places(
                keyword=keyword, lat=lat, lng=lng, radius=radius
            )
            return {
                "success": True,
                "tool": "search_nearby_places",
                "results_count": len(results),
                "places": results,
                "search_params": {"keyword": keyword, "location": f"{lat},{lng}", "radius": radius}
            }
        except Exception as e:
            logger.error(f"Search nearby places failed: {e}", exc_info=True)
            return {"success": False, "tool": "search_nearby_places", "error": str(e)}

    async def get_place_details(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Get place details using Google Maps API."""
        place_id = params.get("place_id", "")
        try:
            result = await self.google_maps_client.get_place_details(place_id)
            return {
                "success": True,
                "tool": "get_place_details",
                "place": {
                    "place_id": place_id,
                    "formatted_address": result["formatted_address"],
                    "opening_hours": result["opening_hours"],
                    "photo_reference": result["photo_reference"],
                    "review_summary": result["review_summary"],
                    "rating": result["rating"],
                    "user_ratings_total": result["user_ratings_total"]
                }
            }
        except Exception as e:
            logger.error(f"Get place details failed: {e}", exc_info=True)
            return {"success": False, "tool": "get_place_details", "error": f"Could not get details for place_id '{place_id}': {str(e)}"}

    async def plan_route(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Plan a route using Google Maps Directions API and orchestrator for airports."""
        origin = params.get("origin", "")
        destination = params.get("destination", "")
        travel_mode = params.get("travel_mode", "driving")
        try:
            origin_info = await self.orchestrator.get_coordinates(origin)
            dest_info = await self.orchestrator.get_coordinates(destination)

            lat1, lon1 = radians(origin_info["lat"]), radians(origin_info["lng"])
            lat2, lon2 = radians(dest_info["lat"]), radians(dest_info["lng"])
            dlon = lon2 - lon1
            dlat = lat2 - lat1
            a = sin(dlat/2)**2 + cos(lat1) * cos(lat2) * sin(dlon/2)**2
            c = 2 * atan2(sqrt(a), sqrt(1-a))
            distance_km = 6371 * c

            recommended_transport = []
            if distance_km > 500:
                recommended_transport.append("flight")
            if distance_km < 100:
                recommended_transport.extend(["car", "bus"])
            if 100 <= distance_km <= 500:
                recommended_transport.extend(["train", "bus", "car"])
            recommended_transport.append("boat")

            origin_airport = None
            dest_airport = None
            try:
                origin_airport = await self.orchestrator.find_nearest_iata(origin_info["lat"], origin_info["lng"])
            except Exception:
                pass
            try:
                dest_airport = await self.orchestrator.find_nearest_iata(dest_info["lat"], dest_info["lng"])
            except Exception:
                pass

            route_info = None
            if self.orchestrator.gmaps:
                try:
                    loop = asyncio.get_event_loop()
                    directions_result = await loop.run_in_executor(
                        None,
                        lambda: self.orchestrator.gmaps.directions(
                            origin=f"{origin_info['lat']},{origin_info['lng']}",
                            destination=f"{dest_info['lat']},{dest_info['lng']}",
                            mode=travel_mode
                        )
                    )
                    if directions_result:
                        route = directions_result[0]
                        leg = route["legs"][0]
                        route_info = {
                            "distance_text": leg["distance"]["text"],
                            "distance_meters": leg["distance"]["value"],
                            "duration_text": leg["duration"]["text"],
                            "duration_seconds": leg["duration"]["value"],
                            "steps": len(route["legs"][0].get("steps", [])),
                            "polyline": route.get("overview_polyline", {}).get("points") if "overview_polyline" in route else None
                        }
                except Exception as e:
                    logger.warning(f"Google Maps Directions API call failed: {e}")

            return {
                "success": True,
                "tool": "plan_route",
                "route": {
                    "origin": {
                        "location": origin,
                        "coordinates": {"latitude": origin_info["lat"], "longitude": origin_info["lng"]},
                        "nearest_airport": origin_airport
                    },
                    "destination": {
                        "location": destination,
                        "coordinates": {"latitude": dest_info["lat"], "longitude": dest_info["lng"]},
                        "nearest_airport": dest_airport
                    },
                    "distance_km": round(distance_km, 2),
                    "recommended_transportation": recommended_transport,
                    "route_details": route_info
                }
            }
        except Exception as e:
            return {"success": False, "tool": "plan_route", "error": f"Could not plan route: {str(e)}"}

    async def plan_route_with_waypoints(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Plan a route from origin to destination via waypoints (จุดแวะ) using Google Maps Directions API."""
        origin = params.get("origin", "")
        destination = params.get("destination", "")
        waypoints_raw = params.get("waypoints") or []
        travel_mode = params.get("travel_mode", "driving")
        waypoints_list = [w for w in waypoints_raw if isinstance(w, str) and w.strip()]
        try:
            origin_info = await self.orchestrator.get_coordinates(origin)
            dest_info = await self.orchestrator.get_coordinates(destination)
            waypoint_infos = []
            for wp in waypoints_list:
                try:
                    wi = await self.orchestrator.get_coordinates(wp)
                    waypoint_infos.append({"location": wp, "lat": wi["lat"], "lng": wi["lng"]})
                except Exception:
                    waypoint_infos.append({"location": wp, "lat": None, "lng": None})
            lat1, lon1 = radians(origin_info["lat"]), radians(origin_info["lng"])
            lat2, lon2 = radians(dest_info["lat"]), radians(dest_info["lng"])
            dlon = lon2 - lon1
            dlat = lat2 - lat1
            a = sin(dlat/2)**2 + cos(lat1) * cos(lat2) * sin(dlon/2)**2
            c = 2 * atan2(sqrt(a), sqrt(1-a))
            distance_km = round(6371 * c, 2)
            route_info = None
            legs_summary = []
            if self.orchestrator.gmaps:
                waypoints_str = [f"{wi['lat']},{wi['lng']}" for wi in waypoint_infos if wi.get("lat") is not None and wi.get("lng") is not None]
                if waypoints_list and len(waypoints_str) != len(waypoints_list):
                    waypoints_str = []
                if waypoints_list and waypoints_str:
                    try:
                        loop = asyncio.get_event_loop()
                        directions_result = await loop.run_in_executor(
                            None,
                            lambda: self.orchestrator.gmaps.directions(
                                origin=f"{origin_info['lat']},{origin_info['lng']}",
                                destination=f"{dest_info['lat']},{dest_info['lng']}",
                                waypoints=waypoints_str,
                                mode=travel_mode
                            )
                        )
                        if directions_result:
                            route = directions_result[0]
                            total_dist_m = 0
                            total_dur_s = 0
                            for idx, leg in enumerate(route.get("legs", [])):
                                d = leg.get("distance", {}).get("value", 0)
                                t = leg.get("duration", {}).get("value", 0)
                                total_dist_m += d
                                total_dur_s += t
                                legs_summary.append({
                                    "from": waypoints_list[idx - 1] if idx > 0 else origin,
                                    "to": waypoints_list[idx] if idx < len(waypoints_list) else destination,
                                    "distance_text": leg.get("distance", {}).get("text", ""),
                                    "duration_text": leg.get("duration", {}).get("text", ""),
                                })
                            route_info = {
                                "distance_text": f"{total_dist_m/1000:.1f} km",
                                "distance_meters": total_dist_m,
                                "duration_seconds": total_dur_s,
                                "legs": legs_summary,
                            }
                    except Exception as e:
                        logger.warning(f"Google Maps Directions with waypoints failed: {e}")
                elif not waypoints_list:
                    try:
                        loop = asyncio.get_event_loop()
                        directions_result = await loop.run_in_executor(
                            None,
                            lambda: self.orchestrator.gmaps.directions(
                                origin=f"{origin_info['lat']},{origin_info['lng']}",
                                destination=f"{dest_info['lat']},{dest_info['lng']}",
                                mode=travel_mode
                            )
                        )
                        if directions_result:
                            route = directions_result[0]
                            leg = route["legs"][0]
                            route_info = {
                                "distance_text": leg.get("distance", {}).get("text", ""),
                                "distance_meters": leg.get("distance", {}).get("value", 0),
                                "duration_seconds": leg.get("duration", {}).get("value", 0),
                                "legs": [{"from": origin, "to": destination, "distance_text": leg.get("distance", {}).get("text", ""), "duration_text": leg.get("duration", {}).get("text", "")}],
                            }
                    except Exception as e:
                        logger.warning(f"Google Maps Directions failed: {e}")
            return {
                "success": True,
                "tool": "plan_route_with_waypoints",
                "route": {
                    "origin": {"location": origin, "coordinates": {"latitude": origin_info["lat"], "longitude": origin_info["lng"]}},
                    "destination": {"location": destination, "coordinates": {"latitude": dest_info["lat"], "longitude": dest_info["lng"]}},
                    "waypoints": [{"location": wp, "coordinates": {"latitude": wi["lat"], "longitude": wi["lng"]}} for wp, wi in zip(waypoints_list, waypoint_infos)],
                    "distance_km": distance_km,
                    "route_details": route_info,
                },
            }
        except Exception as e:
            return {"success": False, "tool": "plan_route_with_waypoints", "error": str(e)}

    async def compare_transport_modes(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Compare transport modes using Google Maps API."""
        origin = params.get("origin", "")
        destination = params.get("destination", "")
        try:
            route_options = await self.google_maps_client.get_route_options(origin, destination)
            return {
                "success": True,
                "tool": "compare_transport_modes",
                "route_options": route_options,
                "origin": origin,
                "destination": destination
            }
        except Exception as e:
            logger.error(f"Compare transport modes failed: {e}", exc_info=True)
            return {"success": False, "tool": "compare_transport_modes", "error": str(e)}

    async def close(self):
        """Cleanup resources."""
        try:
            if self.orchestrator:
                await self.orchestrator.close()
            logger.info("GoogleMapsMCP closed successfully")
        except Exception as e:
            logger.warning(f"Error closing GoogleMapsMCP: {e}")
