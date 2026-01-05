"""
Google Maps API endpoints for geocoding and places search.
"""
from fastapi import APIRouter
from pydantic import BaseModel
from typing import Optional, List, Dict, Any

from services.google_maps_service import (
    geocode_address,
    get_place_details,
    get_route,
    search_nearby_places,
)

router = APIRouter()


class GeocodeRequest(BaseModel):
    location: str


class NearbyPlacesRequest(BaseModel):
    lat: float
    lng: float
    radius: Optional[int] = 5000
    place_type: Optional[str] = "tourist_attraction"
    max_results: Optional[int] = 10


class DirectionsRequest(BaseModel):
    origin: str
    destination: str
    mode: Optional[str] = "driving"  # driving, walking, transit, bicycling


@router.post("/api/maps/geocode")
async def geocode(request: GeocodeRequest):
    """Convert location name to coordinates."""
    result = await geocode_address(request.location)
    if result.get("ok"):
        return {"ok": True, "data": result}
    return {"ok": False, "data": None, "message": result.get("error", "ไม่พบตำแหน่ง")}


@router.post("/api/maps/nearby")
async def nearby_places(request: NearbyPlacesRequest):
    """Search for nearby places (tourist attractions, restaurants, etc.)."""
    places = await search_nearby_places(
        lat=request.lat,
        lng=request.lng,
        radius=request.radius,
        place_type=request.place_type,
        max_results=request.max_results,
    )
    return {"ok": True, "data": places, "count": len(places)}


@router.get("/api/maps/place/{place_id}")
async def place_details(place_id: str):
    """Get detailed information about a place."""
    details = await get_place_details(place_id)
    if details.get("ok"):
        return {"ok": True, "data": details}
    return {"ok": False, "data": None, "message": details.get("error", "ไม่พบข้อมูลสถานที่")}


@router.post("/api/maps/directions")
async def directions(request: DirectionsRequest):
    """Get directions between two locations."""
    result = await get_route(
        origin=request.origin,
        destination=request.destination,
        mode=request.mode or "driving",
    )
    if result.get("ok"):
        return {"ok": True, "data": result}
    return {"ok": False, "data": None, "message": result.get("error", "ไม่สามารถหาเส้นทางได้")}

