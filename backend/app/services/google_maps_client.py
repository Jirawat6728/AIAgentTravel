"""
ไคลเอนต์ Google Maps สำหรับ Travel Agent
ให้ geocoding การค้นหาสถานที่ใกล้เคียง และรายละเอียดสถานที่ ผ่าน Google Maps API
"""

from __future__ import annotations
from typing import Optional, Dict, Any, List
import asyncio
import logging
from math import radians, sin, cos, sqrt, atan2

import googlemaps
from googlemaps.exceptions import ApiError, HTTPError, Timeout

from app.core.config import settings
from app.core.logging import get_logger
from app.core.exceptions import AgentException

logger = get_logger(__name__)


class GoogleMapsClient:
    """
    Google Maps API Client
    Provides methods for geocoding, nearby places search, and place details
    """
    
    def __init__(self, api_key: Optional[str] = None):
        """
        Initialize Google Maps client
        
        Args:
            api_key: Google Maps API key (defaults to settings.google_maps_api_key)
        """
        self.api_key = api_key or settings.google_maps_api_key
        
        if not self.api_key:
            logger.warning("Google Maps API key not configured")
            self.client = None
        else:
            try:
                self.client = googlemaps.Client(key=self.api_key)
                logger.info("GoogleMapsClient initialized successfully")
            except Exception as e:
                logger.error(f"Failed to initialize Google Maps client: {e}", exc_info=True)
                self.client = None
    
    def _check_client(self) -> None:
        """Check if client is initialized"""
        if not self.client:
            raise AgentException("Google Maps API key not configured")
    
    async def geocode_location(self, query: str) -> Dict[str, Any]:
        """
        Convert a place name or address to geographic coordinates
        
        Args:
            query: Place name or address (e.g., "Iconsiam", "Bangkok, Thailand")
            
        Returns:
            Dictionary with:
            - "lat": float - Latitude
            - "lng": float - Longitude
            - "address": str - Formatted address
            
        Raises:
            AgentException: If geocoding fails
        """
        self._check_client()
        
        if not query or not query.strip():
            raise AgentException("Query cannot be empty")
        
        try:
            loop = asyncio.get_event_loop()
            
            def _geocode():
                try:
                    return self.client.geocode(query)
                except ApiError as e:
                    logger.error(f"Google Maps API error during geocoding: {e}")
                    raise AgentException(f"Google Maps API error: {str(e)}")
                except HTTPError as e:
                    logger.error(f"HTTP error during geocoding: {e}")
                    raise AgentException(f"HTTP error: {str(e)}")
                except Timeout as e:
                    logger.error(f"Timeout during geocoding: {e}")
                    raise AgentException(f"Request timeout: {str(e)}")
                except Exception as e:
                    logger.error(f"Unexpected error during geocoding: {e}", exc_info=True)
                    raise AgentException(f"Geocoding failed: {str(e)}")
            
            geocode_results = await loop.run_in_executor(None, _geocode)
            
            if not geocode_results or len(geocode_results) == 0:
                logger.warning(f"No results found for query: {query}")
                raise AgentException(f"No results found for '{query}'")
            
            # Get first result
            result = geocode_results[0]
            geometry = result.get("geometry", {})
            location = geometry.get("location", {})
            
            lat = location.get("lat")
            lng = location.get("lng")
            formatted_address = result.get("formatted_address", query)
            
            if lat is None or lng is None:
                raise AgentException(f"Invalid coordinates returned for '{query}'")
            
            logger.info(f"Geocoded '{query}' -> {lat},{lng} ({formatted_address})")
            
            return {
                "lat": lat,
                "lng": lng,
                "address": formatted_address
            }
            
        except AgentException:
            raise
        except Exception as e:
            logger.error(f"Unexpected error in geocode_location: {e}", exc_info=True)
            raise AgentException(f"Geocoding failed: {str(e)}")
    
    async def search_nearby_places(
        self,
        keyword: str,
        lat: float,
        lng: float,
        radius: int = 1000
    ) -> List[Dict[str, Any]]:
        """
        Search for nearby places (attractions, restaurants, etc.) using Places API
        
        Args:
            keyword: Search keyword (e.g., "restaurant", "tourist attraction", "museum")
            lat: Latitude of the center point
            lng: Longitude of the center point
            radius: Search radius in meters (default: 1000)
            
        Returns:
            List of dictionaries, each containing:
            - "name": str - Place name
            - "place_id": str - Google Place ID
            - "rating": float - Rating (0-5)
            - "user_ratings_total": int - Number of ratings
            - "vicinity": str - Address/vicinity
            - "types": List[str] - Place types
            
        Raises:
            AgentException: If search fails
        """
        self._check_client()
        
        if not keyword or not keyword.strip():
            raise AgentException("Keyword cannot be empty")
        
        if not isinstance(lat, (int, float)) or not isinstance(lng, (int, float)):
            raise AgentException("Latitude and longitude must be numbers")
        
        if radius < 1 or radius > 50000:
            raise AgentException("Radius must be between 1 and 50000 meters")
        
        try:
            loop = asyncio.get_event_loop()
            
            def _search_nearby():
                try:
                    # Note: Legacy googlemaps library doesn't support field masking for places_nearby
                    # We'll manually extract only the required fields after the API call
                    result = self.client.places_nearby(
                        location=(lat, lng),
                        radius=radius,
                        keyword=keyword
                    )
                    return result.get("results", [])
                except ApiError as e:
                    logger.error(f"Google Maps API error during nearby search: {e}")
                    raise AgentException(f"Google Maps API error: {str(e)}")
                except HTTPError as e:
                    logger.error(f"HTTP error during nearby search: {e}")
                    raise AgentException(f"HTTP error: {str(e)}")
                except Timeout as e:
                    logger.error(f"Timeout during nearby search: {e}")
                    raise AgentException(f"Request timeout: {str(e)}")
                except Exception as e:
                    logger.error(f"Unexpected error during nearby search: {e}", exc_info=True)
                    raise AgentException(f"Nearby search failed: {str(e)}")
            
            results = await loop.run_in_executor(None, _search_nearby)
            
            if not results:
                logger.info(f"No nearby places found for keyword '{keyword}' at {lat},{lng}")
                return []
            
            # Format results and limit to top 5
            # Extract only required fields: name, place_id, rating, user_ratings_total, vicinity, types
            formatted_results = []
            for place in results[:5]:  # Limit to top 5 to save LLM context window
                formatted_place = {
                    "name": place.get("name", "Unknown"),
                    "place_id": place.get("place_id", ""),
                    "rating": place.get("rating", 0.0),
                    "user_ratings_total": place.get("user_ratings_total", 0),
                    "vicinity": place.get("vicinity", ""),
                    "types": place.get("types", [])
                }
                formatted_results.append(formatted_place)
            
            logger.info(f"Found {len(formatted_results)} nearby places for keyword '{keyword}'")
            
            return formatted_results
            
        except AgentException:
            raise
        except Exception as e:
            logger.error(f"Unexpected error in search_nearby_places: {e}", exc_info=True)
            raise AgentException(f"Nearby search failed: {str(e)}")
    
    async def get_place_details(self, place_id: str) -> Dict[str, Any]:
        """
        Get detailed information about a place
        
        Args:
            place_id: Google Place ID
            
        Returns:
            Dictionary with:
            - "formatted_address": str - Full formatted address
            - "opening_hours": Dict[str, Any] - Opening hours information
            - "photo_reference": Optional[str] - Photo reference (first photo only)
            - "review_summary": Optional[str] - Top review summary (first review only)
            - "rating": float - Rating (0-5)
            - "user_ratings_total": int - Number of ratings
            
        Raises:
            AgentException: If place details fetch fails
        """
        self._check_client()
        
        if not place_id or not place_id.strip():
            raise AgentException("Place ID cannot be empty")
        
        try:
            loop = asyncio.get_event_loop()
            
            def _get_details():
                try:
                    # Note: Legacy googlemaps library supports fields parameter for place() method
                    # Extract only required fields: formatted_address, opening_hours, photos (1), reviews (1), rating, user_ratings_total
                    result = self.client.place(
                        place_id=place_id,
                        fields=['formatted_address', 'opening_hours', 'photos', 'reviews', 'rating', 'user_ratings_total']
                    )
                    return result.get("result", {})
                except ApiError as e:
                    logger.error(f"Google Maps API error during place details: {e}")
                    raise AgentException(f"Google Maps API error: {str(e)}")
                except HTTPError as e:
                    logger.error(f"HTTP error during place details: {e}")
                    raise AgentException(f"HTTP error: {str(e)}")
                except Timeout as e:
                    logger.error(f"Timeout during place details: {e}")
                    raise AgentException(f"Request timeout: {str(e)}")
                except Exception as e:
                    logger.error(f"Unexpected error during place details: {e}", exc_info=True)
                    raise AgentException(f"Place details fetch failed: {str(e)}")
            
            place_data = await loop.run_in_executor(None, _get_details)
            
            if not place_data:
                raise AgentException(f"No details found for place_id: {place_id}")
            
            # Extract formatted address
            formatted_address = place_data.get("formatted_address", "")
            
            # Extract opening hours
            opening_hours = place_data.get("opening_hours", {})
            opening_hours_info = {
                "open_now": opening_hours.get("open_now", False),
                "weekday_text": opening_hours.get("weekday_text", [])
            }
            
            # Extract first photo reference only
            photos = place_data.get("photos", [])
            photo_reference = None
            if photos and len(photos) > 0:
                photo_reference = photos[0].get("photo_reference")
            
            # Extract top review summary (first review only)
            reviews = place_data.get("reviews", [])
            review_summary = None
            if reviews and len(reviews) > 0:
                first_review = reviews[0]
                review_summary = first_review.get("text", "")[:500]  # Limit to 500 chars
            
            # Extract rating info
            rating = place_data.get("rating", 0.0)
            user_ratings_total = place_data.get("user_ratings_total", 0)
            
            result = {
                "formatted_address": formatted_address,
                "opening_hours": opening_hours_info,
                "photo_reference": photo_reference,
                "review_summary": review_summary,
                "rating": rating,
                "user_ratings_total": user_ratings_total
            }
            
            logger.info(f"Retrieved place details for place_id: {place_id}")
            
            return result
            
        except AgentException:
            raise
        except Exception as e:
            logger.error(f"Unexpected error in get_place_details: {e}", exc_info=True)
            raise AgentException(f"Place details fetch failed: {str(e)}")
    
    async def get_route_options(self, origin: str, destination: str) -> Dict[str, Any]:
        """
        Get route options comparing different transport modes (driving, transit, walking)
        
        This function calls Google Maps Directions API in parallel for multiple modes:
        - Always: driving, transit
        - Conditionally: walking (if distance < 2 km)
        
        Args:
            origin: Origin location (place name, address, or coordinates)
            destination: Destination location (place name, address, or coordinates)
            
        Returns:
            Dictionary with route options for each available mode:
            {
                "driving": {
                    "duration_text": "20 mins",
                    "duration_value": 1200,  # seconds
                    "distance": "10 km",
                    "distance_value": 10000  # meters
                },
                "transit": {
                    "duration_text": "45 mins",
                    "duration_value": 2700,
                    "steps": ["BTS", "Walk"],
                    "fare": "approx 50 THB",
                    "available": True
                },
                "walking": {
                    "duration_text": "2 hours",
                    "duration_value": 7200,
                    "distance": "8 km",
                    "available": True
                }
            }
            
        Raises:
            AgentException: If route calculation fails
        """
        self._check_client()
        
        if not origin or not origin.strip():
            raise AgentException("Origin cannot be empty")
        if not destination or not destination.strip():
            raise AgentException("Destination cannot be empty")
        
        try:
            # First, geocode origin and destination if they're place names
            # Check if they're already coordinates (lat,lng format)
            origin_coords = None
            dest_coords = None
            
            # Try to parse as coordinates first
            try:
                if ',' in origin.strip():
                    lat, lng = origin.strip().split(',')
                    origin_coords = (float(lat.strip()), float(lng.strip()))
            except (ValueError, AttributeError):
                pass
            
            try:
                if ',' in destination.strip():
                    lat, lng = destination.strip().split(',')
                    dest_coords = (float(lat.strip()), float(lng.strip()))
            except (ValueError, AttributeError):
                pass
            
            # If not coordinates, geocode them
            if not origin_coords:
                origin_geocode = await self.geocode_location(origin)
                origin_coords = (origin_geocode["lat"], origin_geocode["lng"])
            
            if not dest_coords:
                dest_geocode = await self.geocode_location(destination)
                dest_coords = (dest_geocode["lat"], dest_geocode["lng"])
            
            loop = asyncio.get_event_loop()
            
            # Helper function to get directions for a specific mode
            def _get_directions(mode: str):
                try:
                    return self.client.directions(
                        origin=origin_coords,
                        destination=dest_coords,
                        mode=mode
                    )
                except ApiError as e:
                    logger.warning(f"Google Maps API error for {mode} mode: {e}")
                    return None
                except HTTPError as e:
                    logger.warning(f"HTTP error for {mode} mode: {e}")
                    return None
                except Timeout as e:
                    logger.warning(f"Timeout for {mode} mode: {e}")
                    return None
                except Exception as e:
                    logger.warning(f"Unexpected error for {mode} mode: {e}")
                    return None
            
            # Calculate straight-line distance to decide if we should check walking
            lat1, lon1 = radians(origin_coords[0]), radians(origin_coords[1])
            lat2, lon2 = radians(dest_coords[0]), radians(dest_coords[1])
            dlon = lon2 - lon1
            dlat = lat2 - lat1
            a = sin(dlat/2)**2 + cos(lat1) * cos(lat2) * sin(dlon/2)**2
            c = 2 * atan2(sqrt(a), sqrt(1-a))
            straight_distance_km = 6371 * c  # Earth radius in km
            
            # Prepare tasks for parallel execution
            tasks = []
            modes_to_check = ["driving", "transit"]
            
            # Add walking if distance is short (< 2 km)
            if straight_distance_km < 2:
                modes_to_check.append("walking")
            
            # Execute all direction requests in parallel
            async def _get_directions_async(mode: str):
                return await loop.run_in_executor(None, lambda: _get_directions(mode))
            
            results = await asyncio.gather(
                *[_get_directions_async(mode) for mode in modes_to_check],
                return_exceptions=True
            )
            
            # Process results
            route_options = {}
            
            for idx, mode in enumerate(modes_to_check):
                result = results[idx]
                
                if isinstance(result, Exception):
                    logger.warning(f"Exception for {mode} mode: {result}")
                    route_options[mode] = {"available": False, "error": str(result)}
                    continue
                
                if not result or len(result) == 0:
                    if mode == "transit":
                        route_options[mode] = {"available": False, "message": "Not available"}
                    else:
                        route_options[mode] = {"available": False, "message": "No route found"}
                    continue
                
                # Extract route information
                route = result[0]
                leg = route["legs"][0]
                
                duration_text = leg["duration"]["text"]
                duration_value = leg["duration"]["value"]
                distance_text = leg["distance"]["text"]
                distance_value = leg["distance"]["value"]
                
                mode_info = {
                    "duration_text": duration_text,
                    "duration_value": duration_value,
                    "distance": distance_text,
                    "distance_value": distance_value,
                    "available": True
                }
                
                # For transit, extract steps and fare information
                if mode == "transit":
                    steps = []
                    fare_info = None
                    
                    for step in leg.get("steps", []):
                        travel_mode = step.get("travel_mode", "")
                        if travel_mode == "TRANSIT":
                            transit_details = step.get("transit_details", {})
                            line = transit_details.get("line", {})
                            vehicle = line.get("vehicle", {})
                            vehicle_type = vehicle.get("type", "").upper()
                            if vehicle_type:
                                steps.append(vehicle_type)
                            elif line.get("short_name"):
                                steps.append(line.get("short_name"))
                            elif line.get("name"):
                                steps.append(line.get("name"))
                        elif travel_mode == "WALKING":
                            steps.append("Walk")
                    
                    # Try to extract fare information
                    fare = leg.get("fare", {})
                    if fare:
                        currency = fare.get("currency", "THB")
                        value = fare.get("value", 0)
                        if value > 0:
                            fare_info = f"approx {value} {currency}"
                    
                    mode_info["steps"] = steps if steps else ["Transit"]
                    if fare_info:
                        mode_info["fare"] = fare_info
                
                route_options[mode] = mode_info
            
            logger.info(f"Route options calculated: {list(route_options.keys())}")
            
            return route_options
            
        except AgentException:
            raise
        except Exception as e:
            logger.error(f"Unexpected error in get_route_options: {e}", exc_info=True)
            raise AgentException(f"Route options calculation failed: {str(e)}")


# Global instance (lazy initialization)
_google_maps_client: Optional[GoogleMapsClient] = None


def get_google_maps_client() -> GoogleMapsClient:
    """
    Get or create global Google Maps client instance
    
    Returns:
        GoogleMapsClient instance
    """
    global _google_maps_client
    if _google_maps_client is None:
        _google_maps_client = GoogleMapsClient()
    return _google_maps_client
