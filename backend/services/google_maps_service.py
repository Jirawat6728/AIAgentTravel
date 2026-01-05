"""
Google Maps API service for route planning and itinerary generation.
Uses async httpx for better performance.
"""
from __future__ import annotations

import os
from typing import Any, Dict, List, Optional

try:
    import httpx
    HTTPX_AVAILABLE = True
except ImportError:
    HTTPX_AVAILABLE = False
    import requests


GOOGLE_MAPS_API_KEY = os.getenv("GOOGLE_MAPS_API_KEY", "")
GOOGLE_MAPS_API_ENABLED = bool(GOOGLE_MAPS_API_KEY)


async def get_route(
    origin: str,
    destination: str,
    mode: str = "driving",  # driving, walking, transit, bicycling
    waypoints: Optional[List[str]] = None,
    alternatives: bool = False,
) -> Dict[str, Any]:
    """
    Get route from origin to destination using Google Maps Directions API.
    
    Args:
        origin: Starting point (address or lat,lng)
        destination: Ending point (address or lat,lng)
        mode: Travel mode (driving, walking, transit, bicycling)
        waypoints: Optional list of intermediate points
        alternatives: Whether to return alternative routes
    
    Returns:
        Dict with route information including:
        - routes: List of route options
        - legs: List of route legs (origin -> waypoint1, waypoint1 -> waypoint2, etc.)
        - distance: Total distance in meters
        - duration: Total duration in seconds
        - polyline: Encoded polyline for map rendering
    """
    if not GOOGLE_MAPS_API_ENABLED:
        return {
            "ok": False,
            "error": "Google Maps API key not configured",
            "routes": [],
        }
    
    base_url = "https://maps.googleapis.com/maps/api/directions/json"
    
    params = {
        "origin": origin,
        "destination": destination,
        "mode": mode,
        "key": GOOGLE_MAPS_API_KEY,
        "language": "th",
        "region": "th",
    }
    
    if waypoints:
        params["waypoints"] = "|".join(waypoints)
    
    if alternatives:
        params["alternatives"] = "true"
    
    try:
        if HTTPX_AVAILABLE:
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.get(base_url, params=params)
                data = response.json()
        else:
            # Fallback to requests (sync) if httpx not available
            import requests
            response = requests.get(base_url, params=params, timeout=10.0)
            data = response.json()
        
        if data.get("status") != "OK":
            return {
                "ok": False,
                "error": data.get("error_message", f"Status: {data.get('status')}"),
                "routes": [],
            }
        
        routes = []
        for route in data.get("routes", []):
            legs = []
            total_distance = 0
            total_duration = 0
            
            for leg in route.get("legs", []):
                leg_info = {
                    "start_address": leg.get("start_address", ""),
                    "end_address": leg.get("end_address", ""),
                    "distance": leg.get("distance", {}).get("value", 0),  # meters
                    "distance_text": leg.get("distance", {}).get("text", ""),
                    "duration": leg.get("duration", {}).get("value", 0),  # seconds
                    "duration_text": leg.get("duration", {}).get("text", ""),
                    "start_location": leg.get("start_location", {}),
                    "end_location": leg.get("end_location", {}),
                    "steps": leg.get("steps", []),
                }
                legs.append(leg_info)
                total_distance += leg_info["distance"]
                total_duration += leg_info["duration"]
            
            route_info = {
                "summary": route.get("summary", ""),
                "legs": legs,
                "distance": total_distance,
                "distance_text": f"{total_distance / 1000:.1f} km",
                "duration": total_duration,
                "duration_text": f"{total_duration // 3600} ชั่วโมง {total_duration % 3600 // 60} นาที",
                "polyline": route.get("overview_polyline", {}).get("points", ""),
                "warnings": route.get("warnings", []),
            }
            routes.append(route_info)
        
        return {
            "ok": True,
            "routes": routes,
            "selected_route": routes[0] if routes else None,
        }
    
    except Exception as e:
        return {
            "ok": False,
            "error": str(e),
            "routes": [],
        }


async def geocode_address(address: str) -> Dict[str, Any]:
    """
    Geocode an address to get coordinates.
    
    Returns:
        Dict with lat, lng, formatted_address, place_id, etc.
    """
    if not GOOGLE_MAPS_API_ENABLED:
        return {
            "ok": False,
            "error": "Google Maps API key not configured",
        }
    
    base_url = "https://maps.googleapis.com/maps/api/geocode/json"
    
    params = {
        "address": address,
        "key": GOOGLE_MAPS_API_KEY,
        "language": "th",
        "region": "th",
    }
    
    try:
        if HTTPX_AVAILABLE:
            async with httpx.AsyncClient(timeout=5.0) as client:
                response = await client.get(base_url, params=params)
                data = response.json()
        else:
            import requests
            response = requests.get(base_url, params=params, timeout=5.0)
            data = response.json()
        
        if data.get("status") != "OK":
            return {
                "ok": False,
                "error": data.get("error_message", f"Status: {data.get('status')}"),
            }
        
        results = data.get("results", [])
        if not results:
            return {
                "ok": False,
                "error": "No results found",
            }
        
        location = results[0]
        geometry = location.get("geometry", {})
        location_coords = geometry.get("location", {})
        
        return {
            "ok": True,
            "lat": location_coords.get("lat"),
            "lng": location_coords.get("lng"),
            "formatted_address": location.get("formatted_address", ""),
            "place_id": location.get("place_id", ""),
            "types": location.get("types", []),
            "address_components": location.get("address_components", []),
        }
    
    except Exception as e:
        return {
            "ok": False,
            "error": str(e),
        }


async def get_place_details(place_id: str) -> Dict[str, Any]:
    """
    Get detailed information about a place using Place ID.
    """
    if not GOOGLE_MAPS_API_ENABLED:
        return {
            "ok": False,
            "error": "Google Maps API key not configured",
        }
    
    base_url = "https://maps.googleapis.com/maps/api/place/details/json"
    
    params = {
        "place_id": place_id,
        "key": GOOGLE_MAPS_API_KEY,
        "language": "th",
        "fields": "name,formatted_address,geometry,rating,user_ratings_total,photos,opening_hours,types",
    }
    
    try:
        if HTTPX_AVAILABLE:
            async with httpx.AsyncClient(timeout=5.0) as client:
                response = await client.get(base_url, params=params)
                data = response.json()
        else:
            import requests
            response = requests.get(base_url, params=params, timeout=5.0)
            data = response.json()
        
        if data.get("status") != "OK":
            return {
                "ok": False,
                "error": data.get("error_message", f"Status: {data.get('status')}"),
            }
        
        result = data.get("result", {})
        result = data.get("result", {})
        return {
            "ok": True,
            "name": result.get("name", ""),
            "formatted_address": result.get("formatted_address", ""),
            "rating": result.get("rating"),
            "user_ratings_total": result.get("user_ratings_total"),
            "geometry": result.get("geometry", {}),
            "types": result.get("types", []),
            "opening_hours": result.get("opening_hours", {}),
        }
    
    except Exception as e:
        return {
            "ok": False,
            "error": str(e),
        }


async def search_nearby_places(
    lat: float,
    lng: float,
    radius: int = 5000,
    place_type: str = "tourist_attraction",
    max_results: int = 10,
) -> List[Dict[str, Any]]:
    """
    Search for nearby places using Google Places API (Nearby Search).
    
    Args:
        lat: Latitude
        lng: Longitude
        radius: Search radius in meters (default 5000)
        place_type: Type of place to search (tourist_attraction, restaurant, etc.)
        max_results: Maximum number of results to return
    
    Returns:
        List of place dictionaries with name, rating, location, etc.
    """
    if not GOOGLE_MAPS_API_ENABLED:
        return []
    
    base_url = "https://maps.googleapis.com/maps/api/place/nearbysearch/json"
    
    params = {
        "location": f"{lat},{lng}",
        "radius": radius,
        "type": place_type,
        "key": GOOGLE_MAPS_API_KEY,
        "language": "th",
    }
    
    try:
        if HTTPX_AVAILABLE:
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.get(base_url, params=params)
                data = response.json()
        else:
            import requests
            response = requests.get(base_url, params=params, timeout=10.0)
            data = response.json()
        
        if data.get("status") != "OK":
            return []
        
        results = data.get("results", [])[:max_results]
        places = []
        
        for place in results:
            geometry = place.get("geometry", {})
            location = geometry.get("location", {})
            
            places.append({
                "place_id": place.get("place_id", ""),
                "name": place.get("name", ""),
                "rating": place.get("rating"),
                "user_ratings_total": place.get("user_ratings_total", 0),
                "vicinity": place.get("vicinity", ""),
                "formatted_address": place.get("formatted_address", ""),
                "lat": location.get("lat"),
                "lng": location.get("lng"),
                "types": place.get("types", []),
                "price_level": place.get("price_level"),
            })
        
        return places
    
    except Exception as e:
        return []
