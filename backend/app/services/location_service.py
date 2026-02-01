"""
โมดูลเซอร์วิสสถานที่
รวม Google Maps และ Amadeus APIs ระดับ production
รองรับ geocoding การค้นหากิจกรรม การรับส่ง และการแปลงรหัส IATA
"""

from __future__ import annotations
from typing import Optional, Dict, Any, List, Tuple
import asyncio
import logging
from dataclasses import dataclass

import googlemaps
from amadeus import Client, ResponseError

from app.core.config import settings
from app.core.logging import get_logger
from app.core.exceptions import AgentException

logger = get_logger(__name__)


@dataclass
class LocationInfo:
    """Structured location information"""
    lat: float
    lng: float
    formatted_address: str
    place_id: Optional[str] = None
    city_name: Optional[str] = None
    country_code: Optional[str] = None


@dataclass
class ActivityResult:
    """Activity search result from Amadeus"""
    id: str
    name: str
    description: Optional[str] = None
    rating: Optional[float] = None
    price: Optional[Dict[str, Any]] = None
    location: Optional[Dict[str, float]] = None


@dataclass
class TransferResult:
    """Transfer search result from Amadeus"""
    id: str
    name: str
    vehicle_type: Optional[str] = None
    price: Optional[Dict[str, Any]] = None
    duration: Optional[str] = None


class LocationService:
    """
    Production-Grade Location Service
    Integrates Google Maps Geocoding with Amadeus Activities & Transfers
    """
    
    def __init__(self):
        """Initialize Location Service with API clients"""
        # Google Maps Client
        if not settings.google_maps_api_key:
            logger.warning("GOOGLE_MAPS_API_KEY not set, geocoding will fail")
        self.gmaps = googlemaps.Client(key=settings.google_maps_api_key) if settings.google_maps_api_key else None
        
        # Amadeus Client
        # ✅ Use separate search API keys for security
        if not settings.amadeus_search_api_key or not settings.amadeus_search_api_secret:
            logger.warning("AMADEUS_SEARCH_API_KEY or AMADEUS_SEARCH_API_SECRET not set, Amadeus features will fail")
            self.amadeus = None
        else:
            try:
                # ✅ Search: ใช้ production environment
                search_env = settings.amadeus_search_env.lower()
                self.amadeus = Client(
                    client_id=settings.amadeus_search_api_key,
                    client_secret=settings.amadeus_search_api_secret,
                    hostname=search_env  # Use search environment (production)
                )
                logger.info(f"LocationService initialized with search environment: {search_env}")
                logger.info("LocationService initialized with Google Maps and Amadeus")
            except Exception as e:
                logger.error(f"Failed to initialize Amadeus client: {e}")
                self.amadeus = None
    
    async def geocode(
        self,
        place_name: str,
        language: str = "th"
    ) -> LocationInfo:
        """
        Geocode a place name to coordinates and formatted address
        
        Args:
            place_name: Name of the place (e.g., "Eiffel Tower", "Bangkok")
            language: Language code for formatted address (default: "th")
            
        Returns:
            LocationInfo with lat, lng, formatted_address
            
        Raises:
            AgentException: If geocoding fails or place not found
        """
        if not self.gmaps:
            raise AgentException("Google Maps API key not configured")
        
        try:
            # Run geocoding in thread pool (googlemaps is sync)
            loop = asyncio.get_event_loop()
            results = await loop.run_in_executor(
                None,
                lambda: self.gmaps.geocode(place_name, language=language)
            )
            
            if not results or len(results) == 0:
                raise AgentException(f"Place not found: {place_name}")
            
            # Get first result
            result = results[0]
            geometry = result.get("geometry", {})
            location = geometry.get("location", {})
            
            lat = location.get("lat")
            lng = location.get("lng")
            
            if lat is None or lng is None:
                raise AgentException(f"Invalid coordinates for: {place_name}")
            
            formatted_address = result.get("formatted_address", place_name)
            place_id = result.get("place_id")
            
            # Extract city and country from address components
            city_name = None
            country_code = None
            for component in result.get("address_components", []):
                types = component.get("types", [])
                if "locality" in types or "administrative_area_level_1" in types:
                    city_name = component.get("long_name")
                if "country" in types:
                    country_code = component.get("short_name")
            
            logger.info(f"Geocoded '{place_name}' -> {lat},{lng} ({formatted_address})")
            
            return LocationInfo(
                lat=lat,
                lng=lng,
                formatted_address=formatted_address,
                place_id=place_id,
                city_name=city_name,
                country_code=country_code
            )
        
        except Exception as e:
            logger.error(f"Geocoding error for '{place_name}': {e}", exc_info=True)
            if isinstance(e, AgentException):
                raise
            raise AgentException(f"Geocoding failed for '{place_name}': {str(e)}") from e
    
    async def search_activities(
        self,
        location: LocationInfo,
        radius: int = 5000,
        max_results: int = 10
    ) -> List[ActivityResult]:
        """
        Search for activities/tours near a location using Amadeus Activities API
        
        Args:
            location: LocationInfo with lat/lng coordinates
            radius: Search radius in meters (default: 5000m = 5km)
            max_results: Maximum number of results (default: 10)
            
        Returns:
            List of ActivityResult objects
            
        Raises:
            AgentException: If search fails
        """
        if not self.amadeus:
            raise AgentException("Amadeus API not configured")
        
        try:
            # Run Amadeus API call in thread pool
            loop = asyncio.get_event_loop()
            
            def _search():
                try:
                    # Try different Amadeus API methods based on SDK version
                    # Method 1: shopping.activities (if available)
                    if hasattr(self.amadeus, 'shopping') and hasattr(self.amadeus.shopping, 'activities'):
                        response = self.amadeus.shopping.activities.get(
                            latitude=location.lat,
                            longitude=location.lng,
                            radius=radius
                        )
                        return response.data if hasattr(response, 'data') else []
                    
                    # Method 2: reference_data.locations.activities (alternative)
                    elif hasattr(self.amadeus, 'reference_data') and hasattr(self.amadeus.reference_data.locations, 'activities'):
                        response = self.amadeus.reference_data.locations.activities.get(
                            latitude=location.lat,
                            longitude=location.lng,
                            radius=radius
                        )
                        return response.data if hasattr(response, 'data') else []
                    
                    # Fallback: Return empty list if API not available
                    logger.warning("Amadeus Activities API not available in this SDK version")
                    return []
                    
                except ResponseError as e:
                    logger.error(f"Amadeus Activities API error: {e}")
                    return []
                except AttributeError as e:
                    logger.warning(f"Amadeus Activities API method not found: {e}")
                    return []
            
            activities_data = await loop.run_in_executor(None, _search)
            
            if not activities_data:
                logger.warning(f"No activities found near {location.formatted_address}")
                return []
            
            # Convert to ActivityResult objects
            results = []
            for activity in activities_data[:max_results]:
                try:
                    # Handle both dict and object responses
                    if isinstance(activity, dict):
                        activity_dict = activity
                    else:
                        activity_dict = activity.__dict__ if hasattr(activity, '__dict__') else {}
                    
                    result = ActivityResult(
                        id=activity_dict.get("id", ""),
                        name=activity_dict.get("name", "Unknown Activity"),
                        description=activity_dict.get("description", {}).get("short", "") if isinstance(activity_dict.get("description"), dict) else "",
                        rating=activity_dict.get("rating"),
                        price=activity_dict.get("price"),
                        location=activity_dict.get("geoCode")
                    )
                    results.append(result)
                except Exception as e:
                    logger.warning(f"Failed to parse activity: {e}")
                    continue
            
            logger.info(f"Found {len(results)} activities near {location.formatted_address}")
            return results
        
        except Exception as e:
            logger.error(f"Activities search error: {e}", exc_info=True)
            raise AgentException(f"Failed to search activities: {str(e)}") from e
    
    async def search_transfers(
        self,
        start_location: str,
        end_location: str,
        date: Optional[str] = None
    ) -> List[TransferResult]:
        """
        Search for transfer options using Amadeus Transfer API
        
        Args:
            start_location: Formatted address or location name for pickup
            end_location: Formatted address or location name for dropoff
            date: Transfer date in YYYY-MM-DD format (optional)
            
        Returns:
            List of TransferResult objects
            
        Raises:
            AgentException: If search fails
        """
        if not self.amadeus:
            raise AgentException("Amadeus API not configured")
        
        try:
            # Run Amadeus API call in thread pool
            loop = asyncio.get_event_loop()
            
            def _search():
                try:
                    params = {
                        "startLocation": start_location,
                        "endLocation": end_location
                    }
                    if date:
                        params["date"] = date
                    
                    # Try different Amadeus API methods based on SDK version
                    # Method 1: shopping.transfers (if available)
                    if hasattr(self.amadeus, 'shopping') and hasattr(self.amadeus.shopping, 'transfers'):
                        response = self.amadeus.shopping.transfers.get(**params)
                        return response.data if hasattr(response, 'data') else []
                    
                    # Method 2: shopping.transfer_offers (alternative)
                    elif hasattr(self.amadeus, 'shopping') and hasattr(self.amadeus.shopping, 'transfer_offers'):
                        response = self.amadeus.shopping.transfer_offers.get(**params)
                        return response.data if hasattr(response, 'data') else []
                    
                    # Fallback: Return empty list if API not available
                    logger.warning("Amadeus Transfer API not available in this SDK version")
                    return []
                    
                except ResponseError as e:
                    logger.error(f"Amadeus Transfer API error: {e}")
                    return []
                except AttributeError as e:
                    logger.warning(f"Amadeus Transfer API method not found: {e}")
                    return []
            
            transfers_data = await loop.run_in_executor(None, _search)
            
            if not transfers_data:
                logger.warning(f"No transfers found from {start_location} to {end_location}")
                return []
            
            # Convert to TransferResult objects
            results = []
            for transfer in transfers_data:
                try:
                    # Handle both dict and object responses
                    if isinstance(transfer, dict):
                        transfer_dict = transfer
                    else:
                        transfer_dict = transfer.__dict__ if hasattr(transfer, '__dict__') else {}
                    
                    result = TransferResult(
                        id=transfer_dict.get("id", ""),
                        name=transfer_dict.get("name", "Unknown Transfer"),
                        vehicle_type=transfer_dict.get("vehicleType"),
                        price=transfer_dict.get("price"),
                        duration=transfer_dict.get("duration")
                    )
                    results.append(result)
                except Exception as e:
                    logger.warning(f"Failed to parse transfer: {e}")
                    continue
            
            logger.info(f"Found {len(results)} transfers from {start_location} to {end_location}")
            return results
        
        except Exception as e:
            logger.error(f"Transfer search error: {e}", exc_info=True)
            raise AgentException(f"Failed to search transfers: {str(e)}") from e
    
    async def city_to_iata(
        self,
        city_name: str
    ) -> Optional[str]:
        """
        Convert city name to IATA airport code using Amadeus Airport & City Search
        
        Args:
            city_name: Name of the city (e.g., "Bangkok", "Paris")
            
        Returns:
            IATA code (e.g., "BKK", "CDG") or None if not found
            
        Raises:
            AgentException: If search fails
        """
        if not self.amadeus:
            raise AgentException("Amadeus API not configured")
        
        try:
            # Run Amadeus API call in thread pool
            loop = asyncio.get_event_loop()
            
            def _search():
                try:
                    response = self.amadeus.reference_data.locations.cities.get(
                        keyword=city_name
                    )
                    return response.data if hasattr(response, 'data') else []
                except ResponseError as e:
                    logger.error(f"Amadeus Airport & City Search API error: {e}")
                    return []
            
            cities_data = await loop.run_in_executor(None, _search)
            
            if not cities_data:
                logger.warning(f"No IATA code found for city: {city_name}")
                return None
            
            # Get first result's IATA code
            first_result = cities_data[0]
            iata_code = first_result.get("iataCode")
            
            if iata_code:
                logger.info(f"Converted '{city_name}' -> IATA: {iata_code}")
                return iata_code
            
            return None
        
        except Exception as e:
            logger.error(f"IATA conversion error for '{city_name}': {e}", exc_info=True)
            raise AgentException(f"Failed to convert city to IATA: {str(e)}") from e
    
    async def get_location_with_activities(
        self,
        place_name: str,
        radius: int = 5000,
        max_activities: int = 10
    ) -> Tuple[LocationInfo, List[ActivityResult]]:
        """
        Convenience method: Geocode + Search Activities in one call
        
        Args:
            place_name: Name of the place
            radius: Search radius in meters
            max_activities: Maximum activities to return
            
        Returns:
            Tuple of (LocationInfo, List[ActivityResult])
        """
        location = await self.geocode(place_name)
        activities = await self.search_activities(location, radius, max_activities)
        return location, activities
    
    async def get_transfer_options(
        self,
        start_place: str,
        end_place: str,
        date: Optional[str] = None
    ) -> Tuple[LocationInfo, LocationInfo, List[TransferResult]]:
        """
        Convenience method: Geocode both places + Search Transfers in one call
        
        Args:
            start_place: Name of pickup location
            end_place: Name of dropoff location
            date: Transfer date (optional)
            
        Returns:
            Tuple of (start_location, end_location, List[TransferResult])
        """
        start_location = await self.geocode(start_place)
        end_location = await self.geocode(end_place)
        transfers = await self.search_transfers(
            start_location.formatted_address,
            end_location.formatted_address,
            date
        )
        return start_location, end_location, transfers


# Global instance
_location_service: Optional[LocationService] = None


def get_location_service() -> LocationService:
    """Get or create global LocationService instance"""
    global _location_service
    if _location_service is None:
        _location_service = LocationService()
    return _location_service

