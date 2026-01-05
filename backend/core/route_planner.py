"""
Route Planner - Uses Google Maps to plan routes for multi-destination trips.
Helps organize travel segments between multiple cities.
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional
import asyncio

from services.google_maps_service import get_route, geocode_address


async def plan_multi_destination_route(
    origin: str,
    destinations: List[str],
    mode: str = "driving"  # driving, transit, walking
) -> Dict[str, Any]:
    """
    Plan route for multi-destination trip using Google Maps.
    
    Args:
        origin: Starting point
        destinations: List of destinations (e.g., ["Tokyo", "Osaka", "Kyoto"])
        mode: Travel mode (driving, transit, walking)
    
    Returns:
        Dict with route segments, total distance, duration, and route suggestions
    """
    if not destinations:
        return {
            "ok": False,
            "error": "No destinations provided",
            "segments": [],
        }
    
    # Build route segments
    route_segments = []
    total_distance = 0
    total_duration = 0
    
    # Route: origin -> destination[0] -> destination[1] -> ... -> destination[n]
    all_points = [origin] + destinations
    
    for i in range(len(all_points) - 1):
        current_origin = all_points[i]
        current_dest = all_points[i + 1]
        
        # Get route from Google Maps
        route_result = await get_route(
            origin=current_origin,
            destination=current_dest,
            mode=mode,
            alternatives=False,
        )
        
        if route_result.get("ok") and route_result.get("routes"):
            selected_route = route_result["routes"][0]
            segment_distance = selected_route.get("distance", 0)
            segment_duration = selected_route.get("duration", 0)
            
            route_segments.append({
                "segment_number": i + 1,
                "origin": current_origin,
                "destination": current_dest,
                "distance_km": segment_distance / 1000,  # Convert to km
                "duration_hours": segment_duration / 3600,  # Convert to hours
                "distance_text": selected_route.get("distance_text", ""),
                "duration_text": selected_route.get("duration_text", ""),
                "route_data": selected_route,
            })
            
            total_distance += segment_distance
            total_duration += segment_duration
        else:
            # If Google Maps fails, create placeholder segment
            route_segments.append({
                "segment_number": i + 1,
                "origin": current_origin,
                "destination": current_dest,
                "distance_km": None,
                "duration_hours": None,
                "distance_text": "ไม่ทราบระยะทาง",
                "duration_text": "ไม่ทราบเวลา",
                "route_data": None,
            })
    
    # Suggest optimal order if needed (for future enhancement)
    # Could use Traveling Salesman Problem (TSP) optimization here
    
    return {
        "ok": True,
        "segments": route_segments,
        "total_distance_km": total_distance / 1000,
        "total_duration_hours": total_duration / 3600,
        "total_distance_text": f"{total_distance / 1000:.1f} km",
        "total_duration_text": f"{total_duration // 3600} ชั่วโมง {total_duration % 3600 // 60} นาที",
        "mode": mode,
    }


async def suggest_route_order(
    origin: str,
    destinations: List[str],
    mode: str = "driving"
) -> List[str]:
    """
    Suggest optimal order of destinations using Google Maps distance calculation.
    Uses simple nearest-neighbor algorithm.
    
    Args:
        origin: Starting point
        destinations: List of destinations (unordered)
        mode: Travel mode
    
    Returns:
        Ordered list of destinations (optimized route)
    """
    if not destinations or len(destinations) <= 1:
        return destinations
    
    # Get coordinates for all locations
    locations = {}
    all_locations = [origin] + destinations
    
    for loc in all_locations:
        geocode_result = await geocode_address(loc)
        if geocode_result.get("ok"):
            locations[loc] = {
                "lat": geocode_result.get("lat"),
                "lng": geocode_result.get("lng"),
            }
        else:
            # If geocode fails, keep original order
            return destinations
    
    # Simple nearest-neighbor algorithm
    ordered = []
    remaining = destinations.copy()
    current = origin
    
    while remaining:
        # Find nearest destination from current location
        nearest = None
        nearest_distance = float('inf')
        
        for dest in remaining:
            if current in locations and dest in locations:
                # Calculate distance (simple euclidean distance for quick estimate)
                current_loc = locations[current]
                dest_loc = locations[dest]
                
                # Haversine distance (simplified)
                import math
                lat1, lng1 = math.radians(current_loc["lat"]), math.radians(current_loc["lng"])
                lat2, lng2 = math.radians(dest_loc["lat"]), math.radians(dest_loc["lng"])
                
                dlat = lat2 - lat1
                dlng = lng2 - lng1
                a = math.sin(dlat/2)**2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlng/2)**2
                c = 2 * math.asin(math.sqrt(a))
                distance = 6371 * c  # Earth radius in km
                
                if distance < nearest_distance:
                    nearest_distance = distance
                    nearest = dest
        
        if nearest:
            ordered.append(nearest)
            remaining.remove(nearest)
            current = nearest
        else:
            # Fallback: add first remaining
            ordered.append(remaining[0])
            current = remaining[0]
            remaining.remove(remaining[0])
    
    return ordered

