"""
Unified Travel Service - TravelOrchestrator
Integrates Amadeus and Google Maps APIs for a seamless travel planning experience.
Production-grade with OAuth2 management, async HTTP, and caching.
"""

from __future__ import annotations
from typing import Optional, Dict, Any, List, Union
import asyncio
import time
import logging
from datetime import datetime, timedelta

import httpx
import googlemaps
from pydantic import BaseModel, Field

from app.core.config import settings
from app.core.logging import get_logger
from app.core.exceptions import AmadeusException, AgentException

logger = get_logger(__name__)

# =============================================================================
# Models for Unified Search
# =============================================================================

class TravelSearchRequest(BaseModel):
    query: str = Field(..., description="User's natural language query")
    user_id: str = Field(default="anonymous")
    context: Optional[Dict[str, Any]] = None

class UnifiedTravelResponse(BaseModel):
    intent: str
    location: Optional[Dict[str, Any]] = None
    flights: Optional[List[Dict[str, Any]]] = None
    hotels: Optional[List[Dict[str, Any]]] = None
    transfers: Optional[List[Dict[str, Any]]] = None
    activities: Optional[List[Dict[str, Any]]] = None
    summary: str

# =============================================================================
# TravelOrchestrator Service
# =============================================================================

class TravelOrchestrator:
    """
    Unified Travel Orchestrator
    Handles:
    - Intent Detection (Natural Language to Travel Categories)
    - Google Maps Integration (Geocoding, Cache)
    - Amadeus Integration (Direct REST API via httpx)
    - Data Aggregation (Bundle Search)
    """
    
    def __init__(self):
        # API Keys
        self.amadeus_client_id = settings.amadeus_api_key
        self.amadeus_client_secret = settings.amadeus_api_secret
        self.amadeus_base_url = "https://test.api.amadeus.com" if settings.amadeus_env == "test" else "https://api.amadeus.com"
        
        # Google Maps
        self.gmaps = googlemaps.Client(key=settings.google_maps_api_key) if settings.google_maps_api_key else None
        
        # Auth & Cache
        self._token: Optional[str] = None
        self._token_expiry: float = 0
        self._geocoding_cache: Dict[str, Dict[str, Any]] = {}
        self._iata_cache: Dict[str, str] = {}
        
        # HTTP Client
        self.client = httpx.AsyncClient(timeout=30.0)

    # -------------------------------------------------------------------------
    # Authentication Management
    # -------------------------------------------------------------------------
    
    async def _get_amadeus_token(self) -> str:
        """
        Get or refresh Amadeus OAuth2 token
        """
        if self._token and time.time() < self._token_expiry:
            return self._token
            
        logger.info("Refreshing Amadeus OAuth2 token...")
        try:
            response = await self.client.post(
                f"{self.amadeus_base_url}/v1/security/oauth2/token",
                data={
                    "grant_type": "client_credentials",
                    "client_id": self.amadeus_client_id,
                    "client_secret": self.amadeus_client_secret
                },
                headers={"Content-Type": "application/x-www-form-urlencoded"}
            )
            response.raise_for_status()
            data = response.json()
            
            self._token = data["access_token"]
            # Set expiry with a small buffer (10 seconds)
            self._token_expiry = time.time() + data["expires_in"] - 10
            
            logger.info("Amadeus token refreshed successfully")
            return self._token
        except Exception as e:
            logger.error(f"Failed to authenticate with Amadeus: {e}")
            raise AmadeusException("Authentication failed with Amadeus API")

    # -------------------------------------------------------------------------
    # Google Maps Integration (The Enabler)
    # -------------------------------------------------------------------------
    
    async def get_coordinates(self, place_name: str) -> Dict[str, Any]:
        """
        Geocoding with Cache Support
        """
        cache_key = place_name.lower().strip()
        if cache_key in self._geocoding_cache:
            logger.debug(f"Cache hit for geocoding: {place_name}")
            return self._geocoding_cache[cache_key]
            
        if not self.gmaps:
            raise AgentException("Google Maps API not configured")
            
        logger.info(f"Geocoding '{place_name}' via Google Maps API...")
        try:
            loop = asyncio.get_event_loop()
            results = await loop.run_in_executor(
                None, lambda: self.gmaps.geocode(place_name, language="th")
            )
            
            if not results:
                raise AgentException(f"Location not found: {place_name}")
                
            loc = results[0]
            info = {
                "lat": loc["geometry"]["location"]["lat"],
                "lng": loc["geometry"]["location"]["lng"],
                "address": loc["formatted_address"],
                "city": next((c["long_name"] for c in loc["address_components"] if "locality" in c["types"] or "administrative_area_level_1" in c["types"]), place_name)
            }
            
            self._geocoding_cache[cache_key] = info
            return info
        except Exception as e:
            logger.error(f"Google Maps geocoding error: {e}")
            raise AgentException(f"Failed to find location for '{place_name}'")

    async def find_nearest_iata(self, lat: float, lng: float) -> str:
        """
        Find nearest airport IATA code using Amadeus Airport & City Search
        """
        cache_key = f"{lat},{lng}"
        if cache_key in self._iata_cache:
            return self._iata_cache[cache_key]
            
        token = await self._get_amadeus_token()
        try:
            response = await self.client.get(
                f"{self.amadeus_base_url}/v1/reference-data/locations/airports",
                params={
                    "latitude": lat,
                    "longitude": lng,
                    "radius": 100,
                    "page[limit]": 1,
                    "sort": "distance"
                },
                headers={"Authorization": f"Bearer {token}"}
            )
            response.raise_for_status()
            data = response.json()
            
            if not data.get("data"):
                # Fallback: search by city keyword if no direct airport nearby
                return "BKK" # Default fallback for demo or logic improvement
                
            iata = data["data"][0]["iataCode"]
            self._iata_cache[cache_key] = iata
            return iata
        except Exception as e:
            logger.warning(f"Failed to find nearest IATA for {lat},{lng}: {e}")
            return "BKK" # Safe fallback

    # -------------------------------------------------------------------------
    # Unified Search Logic
    # -------------------------------------------------------------------------
    
    def detect_intent(self, query: str) -> List[str]:
        """
        Simple Keyword-based Intent Detection
        In a real app, this would use LLM or NLP classifier.
        """
        query = query.lower()
        intents = []
        if any(k in query for k in ["บิน", "ไฟลต์", "ตั๋วเครื่องบิน", "flight"]):
            intents.append("flights")
        if any(k in query for k in ["นอน", "พัก", "โรงแรม", "รีสอร์ท", "hotel"]):
            intents.append("hotels")
        if any(k in query for k in ["รถ", "รับส่ง", "แท็กซี่", "transfer"]):
            intents.append("transfers")
        if any(k in query for k in ["เที่ยว", "ทัวร์", "เรือ", "กิจกรรม", "activities", "cruise"]):
            intents.append("activities")
            
        # Default if no specific intent found but location is mentioned
        if not intents:
            intents = ["bundle"]
            
        return intents

    async def smart_search(self, request: TravelSearchRequest) -> UnifiedTravelResponse:
        """
        Main Endpoint Logic: One call for everything
        """
        logger.info(f"Unified search started: {request.query}")
        
        # 1. Intent Detection
        intents = self.detect_intent(request.query)
        
        # 2. Extract Location (Simple logic for demo, should be improved with LLM)
        # Assuming location is the last part or use LLM to extract
        location_query = request.query.split("ไป")[-1].strip() if "ไป" in request.query else request.query
        
        try:
            loc_info = await self.get_coordinates(location_query)
            iata = await self.find_nearest_iata(loc_info["lat"], loc_info["lng"])
        except Exception:
            # Fallback if geocoding fails but we have a broad query
            loc_info = {"city": "Tokyo", "lat": 35.6762, "lng": 139.6503, "address": "Tokyo, Japan"}
            iata = "HND"

        # 3. Parallel Data Fetching
        tasks = []
        if "flights" in intents or "bundle" in intents:
            tasks.append(self.get_flights(iata))
        else:
            tasks.append(asyncio.sleep(0, result=None))
            
        if "hotels" in intents or "bundle" in intents:
            tasks.append(self.get_hotels(iata))
        else:
            tasks.append(asyncio.sleep(0, result=None))
            
        if "activities" in intents or "bundle" in intents:
            tasks.append(self.get_activities(loc_info["lat"], loc_info["lng"]))
        else:
            tasks.append(asyncio.sleep(0, result=None))
            
        if "transfers" in intents or "bundle" in intents:
            tasks.append(self.get_transfers(iata, loc_info["address"]))
        else:
            tasks.append(asyncio.sleep(0, result=None))

        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # 4. Aggregation
        response = UnifiedTravelResponse(
            intent=", ".join(intents),
            location=loc_info,
            flights=results[0] if isinstance(results[0], list) else None,
            hotels=results[1] if isinstance(results[1], list) else None,
            activities=results[2] if isinstance(results[2], list) else None,
            transfers=results[3] if isinstance(results[3], list) else None,
            summary=f"พบข้อมูลสำหรับการเดินทางไป {loc_info['city']} เรียบร้อยแล้วค่ะ"
        )
        
        return response

    # -------------------------------------------------------------------------
    # Core Data Fetchers (Amadeus REST)
    # -------------------------------------------------------------------------
    
    async def get_flights(self, origin: str = "BKK", destination: str = "NRT", departure_date: str = None, adults: int = 1) -> List[Dict[str, Any]]:
        """Fetch Flight Offers with flexible parameters"""
        token = await self._get_amadeus_token()
        
        # Use provided date or default to 30 days from now
        if not departure_date:
            date = (datetime.now() + timedelta(days=30)).strftime("%Y-%m-%d")
        else:
            date = departure_date
        
        # Ensure origin and destination are IATA codes
        origin_code = origin if len(origin) == 3 and origin.isupper() else await self._city_to_iata_sync(origin)
        dest_code = destination if len(destination) == 3 and destination.isupper() else await self._city_to_iata_sync(destination)
        
        if not origin_code or not dest_code:
            logger.warning(f"Could not resolve IATA codes: origin={origin}, dest={destination}")
            return []
        
        try:
            resp = await self.client.get(
                f"{self.amadeus_base_url}/v2/shopping/flight-offers",
                params={
                    "originLocationCode": origin_code,
                    "destinationLocationCode": dest_code,
                    "departureDate": date,
                    "adults": adults,
                    "max": 10  # Get more options
                },
                headers={"Authorization": f"Bearer {token}"}
            )
            resp.raise_for_status()
            return resp.json().get("data", [])
        except Exception as e:
            logger.error(f"Flight API error: {e}")
            return []
    
    async def _city_to_iata_sync(self, city_name: str) -> Optional[str]:
        """Convert city name to IATA code synchronously"""
        try:
            loc_info = await self.get_coordinates(city_name)
            return await self.find_nearest_iata(loc_info["lat"], loc_info["lng"])
        except Exception as e:
            logger.warning(f"Failed to convert {city_name} to IATA: {e}")
            return None

    async def get_hotels(self, city_code: str = None, location_name: str = None, check_in: str = None, check_out: str = None, guests: int = 1) -> List[Dict[str, Any]]:
        """Fetch Hotel Offers with flexible location input"""
        token = await self._get_amadeus_token()
        
        # If city_code not provided, try to get it from location_name
        if not city_code and location_name:
            try:
                loc_info = await self.get_coordinates(location_name)
                city_code = await self.find_nearest_iata(loc_info["lat"], loc_info["lng"])
            except Exception as e:
                logger.warning(f"Could not resolve city code from {location_name}: {e}")
                city_code = "BKK"  # Fallback
        
        if not city_code:
            city_code = "BKK"  # Default fallback
        
        try:
            # 1. Search Hotels by City
            resp = await self.client.get(
                f"{self.amadeus_base_url}/v1/reference-data/locations/hotels/by-city",
                params={"cityCode": city_code, "radius": 10, "radiusUnit": "KM", "hotelSource": "ALL"},
                headers={"Authorization": f"Bearer {token}"}
            )
            resp.raise_for_status()
            hotels = resp.json().get("data", [])[:15]  # Get more hotels
            hotel_ids = ",".join([h["hotelId"] for h in hotels])
            
            if not hotel_ids:
                logger.warning(f"No hotels found for city code: {city_code}")
                return []
            
            # 2. Get Offers for those Hotels
            offer_params = {"hotelIds": hotel_ids, "adults": guests}
            if check_in:
                offer_params["checkInDate"] = check_in
            if check_out:
                offer_params["checkOutDate"] = check_out
                
            resp = await self.client.get(
                f"{self.amadeus_base_url}/v3/shopping/hotel-offers",
                params=offer_params,
                headers={"Authorization": f"Bearer {token}"}
            )
            resp.raise_for_status()
            return resp.json().get("data", [])
        except Exception as e:
            logger.error(f"Hotel API error: {e}")
            return []

    async def get_activities(self, lat: float, lng: float) -> List[Dict[str, Any]]:
        """Fetch Experiences/Activities"""
        token = await self._get_amadeus_token()
        try:
            resp = await self.client.get(
                f"{self.amadeus_base_url}/v1/shopping/activities",
                params={"latitude": lat, "longitude": lng, "radius": 10},
                headers={"Authorization": f"Bearer {token}"}
            )
            return resp.json().get("data", [])
        except Exception as e:
            logger.error(f"Activities API error: {e}")
            return []

    async def get_transfers(self, airport_code: str, address: str) -> List[Dict[str, Any]]:
        """Fetch Transfer Offers (Legacy: Code to Address)"""
        token = await self._get_amadeus_token()
        date_time = (datetime.now() + timedelta(days=30)).strftime("%Y-%m-%dT10:00:00")
        try:
            resp = await self.client.get(
                f"{self.amadeus_base_url}/v1/shopping/transfer-offers",
                params={
                    "startLocationCode": airport_code,
                    "endAddressLine": address,
                    "startDateTime": date_time,
                    "passengers": 1
                },
                headers={"Authorization": f"Bearer {token}"}
            )
            return resp.json().get("data", [])
        except Exception as e:
            logger.error(f"Transfer API error: {e}")
            return []

    async def get_transfers_by_geo(self, start_lat: float, start_lng: float, end_lat: float, end_lng: float, start_time: str = None, passengers: int = 1) -> List[Dict[str, Any]]:
        """Fetch Transfer Offers using Geo Coordinates"""
        token = await self._get_amadeus_token()
        
        # Default time if not provided
        if not start_time:
            start_time = (datetime.now() + timedelta(days=1)).strftime("%Y-%m-%dT10:00:00")
        
        try:
            resp = await self.client.post(
                f"{self.amadeus_base_url}/v1/shopping/transfer-offers",
                json={
                    "startLocation": {
                        "geoCode": {
                            "latitude": start_lat,
                            "longitude": start_lng
                        }
                    },
                    "endLocation": {
                        "geoCode": {
                            "latitude": end_lat,
                            "longitude": end_lng
                        }
                    },
                    "startDateTime": start_time,
                    "passengers": passengers
                },
                headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
            )
            resp.raise_for_status()
            return resp.json().get("data", [])
        except Exception as e:
            logger.error(f"Transfer Geo API error: {e}")
            return []

    async def close(self):
        """Cleanup resources"""
        await self.client.aclose()

# Global instance
orchestrator = TravelOrchestrator()

