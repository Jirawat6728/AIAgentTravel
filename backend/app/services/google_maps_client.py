"""
Google Maps Client for Transfer Integration
Provides location resolution for Amadeus Transfer Service
"""

from __future__ import annotations
from typing import Optional, Dict, Any
import asyncio
import logging

import googlemaps

from app.core.config import settings
from app.core.logging import get_logger
from app.core.exceptions import AgentException

logger = get_logger(__name__)


async def get_location_for_transfer(
    address_string: str,
    language: str = "th"
) -> Dict[str, Any]:
    """
    Get location information for transfer booking
    
    This function:
    1. Geocodes the address to get lat/lng and formatted address
    2. Finds the nearest airport (IATA code) using Google Places API
    
    Args:
        address_string: Address or place name from user (e.g., "Grand Palace Bangkok")
        language: Language code for formatted address (default: "th")
        
    Returns:
        Dictionary with:
        - 'latitude': float
        - 'longitude': float
        - 'formatted_address': str
        - 'iata_code': str (nearest airport IATA code, e.g., "BKK")
        - 'airport_name': str (name of nearest airport)
        - 'airport_distance': float (distance in meters)
        - 'place_id': str (Google Place ID)
        - 'city_name': str
        - 'country_code': str
        
    Raises:
        AgentException: If geocoding fails or no airport found
    """
    if not settings.google_maps_api_key:
        raise AgentException("Google Maps API key not configured")
    
    gmaps = googlemaps.Client(key=settings.google_maps_api_key)
    
    try:
        # Step 1: Geocode the address
        loop = asyncio.get_event_loop()
        
        def _geocode():
            return gmaps.geocode(address_string, language=language)
        
        geocode_results = await loop.run_in_executor(None, _geocode)
        
        if not geocode_results or len(geocode_results) == 0:
            raise AgentException(f"Address not found: {address_string}")
        
        # Get first result
        result = geocode_results[0]
        geometry = result.get("geometry", {})
        location = geometry.get("location", {})
        
        lat = location.get("lat")
        lng = location.get("lng")
        
        if lat is None or lng is None:
            raise AgentException(f"Invalid coordinates for: {address_string}")
        
        formatted_address = result.get("formatted_address", address_string)
        place_id = result.get("place_id")
        
        # Extract city and country
        city_name = None
        country_code = None
        for component in result.get("address_components", []):
            types = component.get("types", [])
            if "locality" in types or "administrative_area_level_1" in types:
                city_name = component.get("long_name")
            if "country" in types:
                country_code = component.get("short_name")
        
        logger.info(f"Geocoded '{address_string}' -> {lat},{lng} ({formatted_address})")
        
        # Step 2: Find nearest airport using Places API
        def _find_airport():
            # Search for airports near the location
            places_result = gmaps.places_nearby(
                location=(lat, lng),
                radius=50000,  # 50km radius
                type="airport"
            )
            return places_result.get("results", [])
        
        airport_results = await loop.run_in_executor(None, _find_airport)
        
        # If no results, try a broader search
        if not airport_results:
            def _find_airport_broad():
                # Try text search for airports
                text_result = gmaps.places(
                    query=f"airport near {city_name or address_string}",
                    location=(lat, lng),
                    radius=50000
                )
                return text_result.get("results", [])
            
            airport_results = await loop.run_in_executor(None, _find_airport_broad)
        
        # Find the nearest airport
        nearest_airport = None
        nearest_distance = float('inf')
        iata_code = None
        airport_name = None
        
        for airport in airport_results:
            airport_geometry = airport.get("geometry", {})
            airport_location = airport_geometry.get("location", {})
            airport_lat = airport_location.get("lat")
            airport_lng = airport_location.get("lng")
            
            if airport_lat and airport_lng:
                # Calculate distance (simple haversine approximation)
                distance = _calculate_distance(lat, lng, airport_lat, airport_lng)
                
                if distance < nearest_distance:
                    nearest_distance = distance
                    nearest_airport = airport
                    airport_name = airport.get("name", "Unknown Airport")
                    
                    # Try to extract IATA code from place details
                    airport_place_id = airport.get("place_id")
                    if airport_place_id:
                        try:
                            place_details = gmaps.place(place_id=airport_place_id)
                            details_result = place_details.get("result", {})
                            
                            # Check address components for IATA code
                            for component in details_result.get("address_components", []):
                                short_name = component.get("short_name", "")
                                # IATA codes are typically 3 uppercase letters
                                if len(short_name) == 3 and short_name.isalpha() and short_name.isupper():
                                    iata_code = short_name
                                    break
                            
                            # If not found in address, check name
                            if not iata_code:
                                airport_name_full = details_result.get("name", "")
                                # Sometimes IATA code is in parentheses: "Suvarnabhumi Airport (BKK)"
                                import re
                                match = re.search(r'\(([A-Z]{3})\)', airport_name_full)
                                if match:
                                    iata_code = match.group(1)
                        except Exception as e:
                            logger.warning(f"Failed to get airport details: {e}")
        
        # If still no IATA code, try to extract from airport name
        if not iata_code and nearest_airport:
            airport_name_full = nearest_airport.get("name", "")
            import re
            match = re.search(r'\(([A-Z]{3})\)', airport_name_full)
            if match:
                iata_code = match.group(1)
        
        # If still no IATA code, use a fallback mapping for common airports
        if not iata_code:
            iata_code = _get_iata_fallback(airport_name or city_name)
        
        if not iata_code:
            logger.warning(f"Could not determine IATA code for airport near {address_string}")
            # Don't raise exception, just log warning - the transfer might still work with address
        
        logger.info(f"Nearest airport: {airport_name} ({iata_code}) at {nearest_distance:.0f}m")
        
        return {
            "latitude": lat,
            "longitude": lng,
            "formatted_address": formatted_address,
            "iata_code": iata_code,
            "airport_name": airport_name,
            "airport_distance": nearest_distance if nearest_airport else None,
            "place_id": place_id,
            "city_name": city_name,
            "country_code": country_code
        }
    
    except AgentException:
        raise
    except Exception as e:
        logger.error(f"Location resolution error for '{address_string}': {e}", exc_info=True)
        raise AgentException(f"Failed to resolve location: {str(e)}") from e


def _calculate_distance(lat1: float, lng1: float, lat2: float, lng2: float) -> float:
    """
    Calculate distance between two coordinates using Haversine formula
    
    Returns:
        Distance in meters
    """
    from math import radians, sin, cos, sqrt, atan2
    
    # Convert to radians
    lat1_rad = radians(lat1)
    lng1_rad = radians(lng1)
    lat2_rad = radians(lat2)
    lng2_rad = radians(lng2)
    
    # Haversine formula
    dlat = lat2_rad - lat1_rad
    dlng = lng2_rad - lng1_rad
    
    a = sin(dlat / 2) ** 2 + cos(lat1_rad) * cos(lat2_rad) * sin(dlng / 2) ** 2
    c = 2 * atan2(sqrt(a), sqrt(1 - a))
    
    # Earth radius in meters
    R = 6371000
    
    return R * c


def _get_iata_fallback(location_name: Optional[str]) -> Optional[str]:
    """
    Fallback IATA code mapping for common locations
    
    Args:
        location_name: Name of location or airport
        
    Returns:
        IATA code or None
    """
    if not location_name:
        return None
    
    location_lower = location_name.lower()
    
    # Common airport mappings
    mappings = {
        "bangkok": "BKK",
        "suvarnabhumi": "BKK",
        "don mueang": "DMK",
        "paris": "CDG",
        "charles de gaulle": "CDG",
        "orly": "ORY",
        "tokyo": "NRT",
        "narita": "NRT",
        "haneda": "HND",
        "london": "LHR",
        "heathrow": "LHR",
        "gatwick": "LGW",
        "new york": "JFK",
        "jfk": "JFK",
        "los angeles": "LAX",
        "lax": "LAX",
        "singapore": "SIN",
        "changi": "SIN",
        "dubai": "DXB",
        "hong kong": "HKG",
        "sydney": "SYD",
        "melbourne": "MEL",
        "seoul": "ICN",
        "incheon": "ICN",
        "taipei": "TPE",
        "taoyuan": "TPE",
        "kuala lumpur": "KUL",
        "jakarta": "CGK",
        "manila": "MNL",
        "ho chi minh": "SGN",
        "hanoi": "HAN",
        "phuket": "HKT",
        "chiang mai": "CNX",
        "krabi": "KBV",
        "pattaya": "UTP",
        "koh samui": "USM"
    }
    
    for key, iata in mappings.items():
        if key in location_lower:
            return iata
    
    return None

