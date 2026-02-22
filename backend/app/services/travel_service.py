"""
เซอร์วิสการเดินทางแบบรวม - TravelOrchestrator
รวม Amadeus และ Google Maps APIs สำหรับการวางแผนการเดินทาง
ระดับ production พร้อม OAuth2 การเรียก HTTP แบบ async และแคช
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
    """Test-validated: use natural-language query, not structured fields (origin/destination etc.)."""
    query: str = Field(
        ...,
        description="Natural language query, e.g. 'เที่ยวบินจากกรุงเทพไปภูเก็ต 1 กรกฎาคม 2026 กลับ 10 กรกฎาคม 2 ผู้ใหญ่'. Do not use origin/destination/departure_date."
    )
    user_id: str = Field(default="anonymous", description="Optional user ID for context")
    context: Optional[Dict[str, Any]] = None

class UnifiedTravelResponse(BaseModel):
    """Test-validated: intent, flights, hotels, rentals, transfers, activities, popular_destinations, summary; lists may be null/empty."""
    intent: str
    location: Optional[Dict[str, Any]] = None
    flights: Optional[List[Dict[str, Any]]] = None
    hotels: Optional[List[Dict[str, Any]]] = None
    rentals: Optional[List[Dict[str, Any]]] = None  # ที่พักให้เช่า (same source as hotels, labeled for UI)
    transfers: Optional[List[Dict[str, Any]]] = None
    activities: Optional[List[Dict[str, Any]]] = None
    popular_destinations: Optional[List[Dict[str, Any]]] = None  # จุดหมายยอดนิยม
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
        # ✅ แยก API Keys สำหรับ Search และ Booking เพื่อความปลอดภัย
        # Search API Keys
        self.amadeus_search_client_id = settings.amadeus_search_api_key
        self.amadeus_search_client_secret = settings.amadeus_search_api_secret
        
        # Booking API Keys
        self.amadeus_booking_client_id = settings.amadeus_booking_api_key
        self.amadeus_booking_client_secret = settings.amadeus_booking_api_secret
        
        # Legacy: สำหรับ backward compatibility
        self.amadeus_client_id = self.amadeus_search_client_id
        self.amadeus_client_secret = self.amadeus_search_client_secret
        
        # ✅ แยก Search และ Booking Environment
        # Search: ใช้ production สำหรับข้อมูลจริง
        search_env = settings.amadeus_search_env.lower()
        self.amadeus_search_base_url = "https://api.amadeus.com" if search_env == "production" else "https://test.api.amadeus.com"
        
        # Booking: ใช้ sandbox เท่านั้น (ห้ามใช้ production)
        booking_env = settings.amadeus_booking_env.lower()
        if booking_env == "production":
            logger.error("🚨 SECURITY: AMADEUS_BOOKING_ENV=production is NOT ALLOWED! Using sandbox instead.")
            booking_env = "test"
        self.amadeus_booking_base_url = "https://test.api.amadeus.com"  # Always sandbox for booking
        
        # Legacy: สำหรับ backward compatibility
        self.amadeus_base_url = self.amadeus_search_base_url  # Default to search URL
        
        # Log key usage (masked for security)
        search_key_preview = f"{self.amadeus_search_client_id[:6]}...{self.amadeus_search_client_id[-4:]}" if len(self.amadeus_search_client_id) > 10 else "***"
        booking_key_preview = f"{self.amadeus_booking_client_id[:6]}...{self.amadeus_booking_client_id[-4:]}" if len(self.amadeus_booking_client_id) > 10 else "***"
        logger.info(f"Amadeus Configuration - Search: {self.amadeus_search_base_url} (env: {search_env}, key: {search_key_preview}), Booking: {self.amadeus_booking_base_url} (env: {booking_env}, key: {booking_key_preview})")
        
        # Google Maps
        self.gmaps = googlemaps.Client(key=settings.google_maps_api_key) if settings.google_maps_api_key else None
        
        # Auth & Cache
        self._token: Optional[str] = None
        self._token_expiry: float = 0
        self._geocoding_cache: Dict[str, Dict[str, Any]] = {}
        self._iata_cache: Dict[str, str] = {}
        # เมื่อ Production auth ล้มเหลว (401) ใช้ Test แทนเพื่อให้ค้นหาทำงานได้
        self._search_fallback_to_test: bool = False
        
        # ✅ HTTP Client with optimized timeout for 1.5-minute search completion
        self.client = httpx.AsyncClient(timeout=12.0)  # ✅ Reduced from 15s to 12s for faster responses

    async def _amadeus_get(
        self,
        url: str,
        token: str,
        params: Dict[str, Any],
        retries: int = 3,
        use_booking_env: Optional[bool] = None,
    ) -> httpx.Response:
        """GET with basic retry/backoff for 429/5xx to reduce flaky empty results. use_booking_env is ignored (search always uses search base URL)."""
        last_exc: Optional[Exception] = None
        for attempt in range(retries):
            try:
                resp = await self.client.get(url, params=params, headers={"Authorization": f"Bearer {token}"})
                # Retry on rate limit / transient errors
                if resp.status_code in (429, 500, 502, 503, 504):
                    wait = 0.8 * (2 ** attempt)
                    logger.warning(f"Amadeus GET retryable status={resp.status_code} attempt={attempt+1}/{retries} wait={wait:.1f}s url={url}")
                    await asyncio.sleep(wait)
                    continue
                resp.raise_for_status()
                return resp
            except Exception as e:
                last_exc = e
                wait = 0.8 * (2 ** attempt)
                logger.warning(f"Amadeus GET failed attempt={attempt+1}/{retries} wait={wait:.1f}s url={url} err={e}")
                await asyncio.sleep(wait)
                continue
        raise last_exc if last_exc else AmadeusException("Amadeus GET failed")

    # -------------------------------------------------------------------------
    # Authentication Management
    # -------------------------------------------------------------------------
    
    async def _get_amadeus_token(self) -> str:
        """
        Get or refresh Amadeus OAuth2 token for search operations.
        Uses search API keys; if production returns 401, falls back to test environment so search still works.
        """
        if self._token and time.time() < self._token_expiry:
            return self._token

        base_url = self.amadeus_search_base_url
        client_id = self.amadeus_search_client_id
        client_secret = self.amadeus_search_client_secret
        logger.info("Refreshing Amadeus OAuth2 token for search environment...")
        try:
            response = await self.client.post(
                f"{base_url}/v1/security/oauth2/token",
                data={
                    "grant_type": "client_credentials",
                    "client_id": client_id,
                    "client_secret": client_secret
                },
                headers={"Content-Type": "application/x-www-form-urlencoded"}
            )
            response.raise_for_status()
            data = response.json()
            self._token = data["access_token"]
            self._token_expiry = time.time() + data["expires_in"] - 10
            env_type = "production" if "api.amadeus.com" in base_url and "test." not in base_url else "test"
            logger.info(f"Amadeus token refreshed successfully for {env_type} environment")
            return self._token
        except Exception as e:
            resp = getattr(e, "response", None)
            is_401 = resp is not None and getattr(resp, "status_code", None) == 401
            if not is_401:
                is_401 = "401" in str(e) or "Unauthorized" in str(e).lower()
            # ถ้า Production คืน 401 และยังไม่เคย fallback ให้ลองใช้ Test
            if is_401 and not self._search_fallback_to_test and "api.amadeus.com" in base_url and "test." not in base_url:
                test_url = "https://test.api.amadeus.com"
                test_id = settings.amadeus_booking_api_key or client_id
                test_secret = settings.amadeus_booking_api_secret or client_secret
                if test_id and test_secret:
                    logger.warning(
                        "Amadeus production auth failed (401). Falling back to test environment for search. "
                        "To use production, set valid AMADEUS_SEARCH_API_KEY and AMADEUS_SEARCH_API_SECRET in .env"
                    )
                    self._search_fallback_to_test = True
                    self.amadeus_search_base_url = test_url
                    self.amadeus_search_client_id = test_id
                    self.amadeus_search_client_secret = test_secret
                    self._token = None
                    self._token_expiry = 0
                    return await self._get_amadeus_token()
            env_type = "production" if "api.amadeus.com" in base_url and "test." not in base_url else "test"
            logger.error(f"Failed to authenticate with Amadeus ({env_type}): {e}", exc_info=True)
            raise AmadeusException(
                f"Authentication failed with Amadeus API ({env_type}). "
                "Check AMADEUS_SEARCH_API_KEY and AMADEUS_SEARCH_API_SECRET in .env (production keys from api.amadeus.com)."
            )

    # -------------------------------------------------------------------------
    # Google Maps Integration (The Enabler)
    # -------------------------------------------------------------------------
    
    async def get_coordinates(self, place_name: str, language: str = "th") -> Dict[str, Any]:
        """
        Geocoding with Cache Support
        Handles IATA codes gracefully (skips geocoding for known airport codes)
        """
        cache_key = f"{language}:{place_name.lower().strip()}"
        if cache_key in self._geocoding_cache:
            logger.debug(f"Cache hit for geocoding: {place_name}")
            return self._geocoding_cache[cache_key]
        
        # ✅ Check if place_name is an IATA code (3 uppercase letters)
        # If it's an IATA code, try to find coordinates via Amadeus Airport Search first
        if isinstance(place_name, str) and len(place_name) == 3 and place_name.isupper() and place_name.isalpha():
            logger.debug(f"'{place_name}' looks like an IATA code, trying Amadeus airport lookup first...")
            try:
                # Try Amadeus Airport Search API to get airport coordinates
                token = await self._get_amadeus_token()
                # ✅ Search: ใช้ production environment
                resp = await self._amadeus_get(
                    f"{self.amadeus_search_base_url}/v1/reference-data/locations",
                    token=token,
                    params={"subType": "AIRPORT", "keyword": place_name, "page[limit]": 1},
                    retries=2,
                    use_booking_env=False,  # Search uses production
                )
                data = resp.json().get("data", [])
                if data and len(data) > 0:
                    airport = data[0]
                    geo_code = airport.get("geoCode", {})
                    if geo_code.get("latitude") and geo_code.get("longitude"):
                        lat = geo_code["latitude"]
                        lng = geo_code["longitude"]
                        address = airport.get("name", f"{place_name} Airport")
                        city = airport.get("address", {}).get("cityName", place_name)
                        country_code = airport.get("address", {}).get("countryCode")
                        
                        info = {
                            "lat": lat,
                            "lng": lng,
                            "address": address,
                            "city": city,
                            "country_code": country_code,
                        }
                        self._geocoding_cache[cache_key] = info
                        logger.info(f"Found airport coordinates for IATA '{place_name}' via Amadeus: {lat},{lng}")
                        return info
            except Exception as e:
                logger.debug(f"Amadeus airport lookup for IATA '{place_name}' failed, trying Google Maps with 'airport' suffix: {e}")
            
            # Fallback: Try geocoding with "airport" suffix
            if self.gmaps:
                try:
                    airport_query = f"{place_name} airport"
                    logger.info(f"Trying geocoding with airport suffix: '{airport_query}'")
                    loop = asyncio.get_event_loop()
                    results = await loop.run_in_executor(
                        None, lambda: self.gmaps.geocode(airport_query, language=language)
                    )
                    if results:
                        loc = results[0]
                        country_code = None
                        for comp in loc.get("address_components", []):
                            if "country" in comp.get("types", []):
                                country_code = comp.get("short_name")
                                break
                        info = {
                            "lat": loc["geometry"]["location"]["lat"],
                            "lng": loc["geometry"]["location"]["lng"],
                            "address": loc["formatted_address"],
                            "city": next((c["long_name"] for c in loc["address_components"] if "locality" in c["types"] or "administrative_area_level_1" in c["types"]), place_name),
                            "country_code": country_code,
                        }
                        self._geocoding_cache[cache_key] = info
                        logger.info(f"Found airport coordinates for IATA '{place_name}' via Google Maps: {info['lat']},{info['lng']}")
                        return info
                except Exception as e:
                    logger.debug(f"Google Maps airport lookup for IATA '{place_name}' failed: {e}")
            
        if not self.gmaps:
            raise AgentException("Google Maps API not configured")
            
        logger.info(f"Geocoding '{place_name}' via Google Maps API...")
        try:
            loop = asyncio.get_event_loop()
            results = await loop.run_in_executor(
                None, lambda: self.gmaps.geocode(place_name, language=language)
            )
            
            if not results:
                # ✅ For IATA codes, provide a more helpful error message
                if isinstance(place_name, str) and len(place_name) == 3 and place_name.isupper():
                    raise AgentException(f"IATA code '{place_name}' not found via geocoding. Please use city name or try with 'airport' suffix.")
                raise AgentException(f"Location not found: {place_name}")
                
            loc = results[0]
            country_code = None
            for comp in loc.get("address_components", []):
                if "country" in comp.get("types", []):
                    country_code = comp.get("short_name")
                    break

            info = {
                "lat": loc["geometry"]["location"]["lat"],
                "lng": loc["geometry"]["location"]["lng"],
                "address": loc["formatted_address"],
                "city": next((c["long_name"] for c in loc["address_components"] if "locality" in c["types"] or "administrative_area_level_1" in c["types"]), place_name),
                "country_code": country_code,
            }
            
            self._geocoding_cache[cache_key] = info
            return info
        except AgentException:
            raise
        except Exception as e:
            logger.error(f"Google Maps geocoding error: {e}")
            raise AgentException(f"Failed to find location for '{place_name}'")

    async def find_city_iata(self, city_name: str) -> str:
        """
        Resolve a city code suitable for Amadeus hotel-by-city queries.
        Returns a CITY code (e.g. Seoul -> SEL, Tokyo -> TYO).
        Uses hardcoded map first, then Amadeus locations search.
        """
        # ✅ If already an IATA code (3 uppercase letters), return it directly
        if isinstance(city_name, str) and len(city_name) == 3 and city_name.isupper() and city_name.isalpha():
            logger.debug(f"'{city_name}' is already an IATA code, returning as-is")
            return city_name
        
        cache_key = f"city:{city_name.lower().strip()}"
        if cache_key in self._iata_cache:
            return self._iata_cache[cache_key]
            
        # 1. Try Hardcoded Major Cities Map first for speed and reliability
        from app.engine.agent import LocationIntelligence
        text_lower = city_name.lower().strip()
        
        # Check MAJOR_CITIES in agent_intelligence
        from app.engine.agent import MAJOR_CITIES
        if text_lower in MAJOR_CITIES:
            code = MAJOR_CITIES[text_lower]
            self._iata_cache[cache_key] = code
            logger.info(f"Resolved '{city_name}' to '{code}' via MAJOR_CITIES map")
            return code

        # 2. Try Landmark resolution (in case it's a landmark)
        loc_res = LocationIntelligence.resolve_location(city_name, context="flight")
        if loc_res.get("airport_code"):
            code = loc_res["airport_code"]
            self._iata_cache[cache_key] = code
            logger.info(f"Resolved '{city_name}' to '{code}' via Landmark resolution")
            return code
            
        token = await self._get_amadeus_token()
        try:
            # Use Google geocode as a strong prior for country and canonical city name.
            # IMPORTANT: Use English here so we don't send Thai keywords to Amadeus (would 400).
            loc_info = None
            try:
                loc_info = await self.get_coordinates(city_name, language="en")
            except Exception:
                loc_info = None

            target_country = (loc_info or {}).get("country_code")
            target_city = ((loc_info or {}).get("city") or city_name or "").strip()
            target_city_l = target_city.lower()

            # Build keywords to query Amadeus locations
            candidates = []
            raw = (city_name or "").strip()
            if raw:
                candidates.append(raw)
            if target_city and target_city.lower() != raw.lower():
                candidates.append(target_city)
            # Prefixes sometimes help, but must be filtered by country/city match to avoid wrong codes
            for base in [target_city, raw]:
                if base and len(base) >= 3:
                    candidates.append(base[:3].upper())

            seen = set()
            keywords: List[str] = []
            for k in candidates:
                if k and k not in seen:
                    seen.add(k)
                    keywords.append(k)

            best_item = None
            best_score = -1

            def score_item(it: Dict[str, Any]) -> int:
                score = 0
                sub = it.get("subType")
                addr = it.get("address") or {}
                name = (it.get("name") or "").lower()
                city_name_resp = (addr.get("cityName") or "").lower()
                country_resp = (addr.get("countryCode") or "").upper()

                # Hard filter: if we know the country, reject mismatches (prevents TOK->US, SEO->ES, etc.)
                if target_country and country_resp and country_resp != str(target_country).upper():
                    return -1
                if target_country and not country_resp:
                    return -1

                if sub == "CITY":
                    score += 50
                if target_country and country_resp == str(target_country).upper():
                    score += 40
                if target_city_l and (target_city_l in name or target_city_l in city_name_resp):
                    score += 30
                # Prefer exact-ish matches
                if name == target_city_l or city_name_resp == target_city_l:
                    score += 20
                return score

            for kw in keywords:
                # Amadeus keyword must be ASCII/Latin; skip non-ascii keywords
                if isinstance(kw, str) and not kw.isascii():
                    continue
                # ✅ Search: ใช้ production environment
                response = await self._amadeus_get(
                    f"{self.amadeus_search_base_url}/v1/reference-data/locations",
                    token=token,
                    params={"subType": "CITY,AIRPORT", "keyword": kw, "page[limit]": 10},
                    retries=3,
                    use_booking_env=False,  # Search uses production
                )
                data = response.json()
                items = data.get("data") or []
                for it in items:
                    s = score_item(it)
                    if s > best_score:
                        best_score = s
                        best_item = it

                # Early stop if we found a very good match
                if best_score >= 100:
                    break

            if best_item and best_score > 0:
                sub = best_item.get("subType")
                if sub == "CITY" and best_item.get("iataCode"):
                    code = best_item["iataCode"]
                    self._iata_cache[cache_key] = code
                    return code
                if sub == "AIRPORT":
                    addr = best_item.get("address") or {}
                    code = addr.get("cityCode") or best_item.get("iataCode")
                    if code:
                        self._iata_cache[cache_key] = code
                        return code

            logger.warning(
                f"Amadeus locations returned no good match for '{city_name}' "
                f"(country={target_country}, city={target_city}, tried={keywords}, best_score={best_score})"
            )
        except Exception as e:
            logger.warning(f"Amadeus City Search failed for {city_name}: {e}")

        # 2. Fallback to Geocoding + Nearest Airport logic if name search fails
        try:
            loc_info = await self.get_coordinates(city_name)
            iata = await self.find_nearest_iata(loc_info["lat"], loc_info["lng"])
            if not iata:
                return None

            # Map airport -> cityCode via Amadeus locations search
            try:
                # ✅ Search: ใช้ production environment
                resp2 = await self._amadeus_get(
                    f"{self.amadeus_search_base_url}/v1/reference-data/locations",
                    token=token,
                    params={"subType": "AIRPORT", "keyword": iata, "page[limit]": 1},
                    retries=3,
                    use_booking_env=False,  # Search uses production
                )
                d2 = resp2.json()
                if d2.get("data"):
                    addr = (d2["data"][0].get("address") or {})
                    city_code = addr.get("cityCode") or d2["data"][0].get("iataCode")
                    if city_code:
                        self._iata_cache[cache_key] = city_code
                        return city_code
            except Exception as e:
                logger.warning(f"Airport->City mapping failed for {iata}: {e}")

            # If mapping fails, return airport IATA as last resort (better than wrong city)
            self._iata_cache[cache_key] = iata
            return iata
        except Exception as e:
            logger.error(f"All IATA resolution strategies failed for {city_name}: {e}")
            return None # Don't return BKK blindly

    async def find_nearest_iata(self, lat: float, lng: float) -> str:
        """
        Find nearest airport IATA code using Amadeus Airport & City Search
        """
        cache_key = f"{lat},{lng}"
        if cache_key in self._iata_cache:
            return self._iata_cache[cache_key]
            
        token = await self._get_amadeus_token()
        try:
            # ✅ Search: ใช้ production environment
            response = await self._amadeus_get(
                f"{self.amadeus_search_base_url}/v1/reference-data/locations/airports",
                token=token,
                params={
                    "latitude": lat,
                    "longitude": lng,
                    "radius": 100,
                    "page[limit]": 1,
                    "sort": "distance"
                },
                retries=3,
                use_booking_env=False,  # Search uses production
            )
            data = response.json()
            
            if not data.get("data"):
                return None # No airport found near coordinates
                
            iata = data["data"][0]["iataCode"]
            self._iata_cache[cache_key] = iata
            return iata
        except Exception as e:
            logger.warning(f"Failed to find nearest IATA for {lat},{lng}: {e}")
            return None


    # -------------------------------------------------------------------------
    # Unified Search Logic
    # -------------------------------------------------------------------------
    
    def detect_intent(self, query: str) -> List[str]:
        """
        Keyword-based Intent Detection for AI Agent.
        Supports: เที่ยวบิน, โรงแรม, ที่พักให้เช่า, transfer, กิจกรรม, สำรวจ/จุดหมายยอดนิยม.
        """
        query_lower = query.lower().strip()
        intents = []
        # เที่ยวบิน
        if any(k in query_lower for k in ["บิน", "ไฟลต์", "ตั๋วเครื่องบิน", "flight", "เที่ยวบิน"]):
            intents.append("flights")
        # โรงแรม
        if any(k in query_lower for k in ["นอน", "พัก", "โรงแรม", "รีสอร์ท", "hotel"]) and "ที่พักให้เช่า" not in query and "rental" not in query_lower:
            intents.append("hotels")
        # ที่พักให้เช่า (rental accommodation)
        if any(k in query_lower for k in ["ที่พักให้เช่า", "ให้เช่า", "rental", "accommodation", "ที่พักให้เช่าทั้งหมด"]):
            intents.append("rentals")
        # Transfer
        if any(k in query_lower for k in ["รถ", "รับส่ง", "แท็กซี่", "transfer", "รถรับส่ง"]):
            intents.append("transfers")
        # กิจกรรม / ท่องเที่ยว
        if any(k in query_lower for k in ["เที่ยว", "ทัวร์", "เรือ", "กิจกรรม", "activities", "cruise", "สถานที่ท่องเที่ยว"]):
            intents.append("activities")
        # สำรวจ / จุดหมายยอดนิยม / ทั้งหมด (popular destinations - no frontend, data only)
        if any(k in query_lower for k in ["สำรวจ", "explore", "จุดหมายยอดนิยม", "popular", "แนะนำที่เที่ยว", "ไปไหนดี", "ทั้งหมด", "all", "ทุกที่", "ทุกแห่ง", "ทุกแห่งหน"]):
            intents.append("popular_destinations")

        if not intents:
            intents = ["bundle"]
        return intents

    async def get_popular_destinations(self, user_lat: Optional[float] = None, user_lng: Optional[float] = None) -> List[Dict[str, Any]]:
        """
        Return popular destinations for AI Agent (จุดหมายยอดนิยม).
        No frontend required - structured data only. Optional: based on user location.
        """
        # Curated popular destinations with sample dates and descriptions (like the reference UI)
        base = datetime.now()
        popular = [
            {
                "id": "popular-seoul",
                "name": "Seoul",
                "name_th": "โซล",
                "dates": f"{(base + timedelta(days=36)).strftime('%d')} - {(base + timedelta(days=45)).strftime('%d')} {(base + timedelta(days=36)).strftime('%b')}",
                "description": "พระราชวัง Gyeongbokgung และหอคอย N Seoul",
                "description_en": "Gyeongbokgung Palace and N Seoul Tower",
                "iata_code": "SEL",
                "country_code": "KR",
                "hotel_price_estimate_thb": 1984,
                "flight_price_estimate_thb": None,
            },
            {
                "id": "popular-tokyo",
                "name": "Tokyo",
                "name_th": "โตเกียว",
                "dates": f"{(base + timedelta(days=59)).strftime('%d')} - {(base + timedelta(days=66)).strftime('%d')} {(base + timedelta(days=59)).strftime('%b')}",
                "description": "ศาลเจ้า Meiji, วังอิมพีเรียล, พิพิธภัณฑ์",
                "description_en": "Meiji Shrine, Imperial Palace, Museum",
                "iata_code": "TYO",
                "country_code": "JP",
                "flight_price_estimate_thb": 9300,
                "hotel_price_estimate_thb": 3348,
            },
            {
                "id": "popular-koh-samui",
                "name": "Koh Samui",
                "name_th": "เกาะสมุย",
                "dates": f"{(base + timedelta(days=100)).strftime('%d')} - {(base + timedelta(days=108)).strftime('%d')} {(base + timedelta(days=100)).strftime('%b')}",
                "description": "ชายหาด สถานบันเทิงยามค่ำคืนและวัดพระใหญ่",
                "description_en": "Beach, nightlife and Big Buddha Temple",
                "iata_code": "USM",
                "country_code": "TH",
                "flight_price_estimate_thb": 4530,
                "hotel_price_estimate_thb": 1656,
            },
        ]
        logger.info(f"Returning {len(popular)} popular destinations for AI Agent")
        return popular

    async def smart_search(self, request: TravelSearchRequest) -> UnifiedTravelResponse:
        """
        Main Endpoint Logic: One call for everything.
        Supports: flights, hotels, rentals (ที่พักให้เช่า), transfers, activities, popular_destinations (จุดหมายยอดนิยม).
        """
        logger.info(f"Unified search started: {request.query}")
        intents = self.detect_intent(request.query)

        # Popular destinations only: no location needed
        if "popular_destinations" in intents and len(intents) == 1:
            destinations = await self.get_popular_destinations()
            return UnifiedTravelResponse(
                intent="popular_destinations",
                location=None,
                flights=None,
                hotels=None,
                rentals=None,
                transfers=None,
                activities=None,
                popular_destinations=destinations,
                summary="จุดหมายยอดนิยมสำหรับวางแผนการเดินทางค่ะ",
            )

        # 2. Extract Location
        location_query = request.query.split("ไป")[-1].strip() if "ไป" in request.query else request.query
        try:
            loc_info = await self.get_coordinates(location_query)
            iata = await self.find_nearest_iata(loc_info["lat"], loc_info["lng"])
        except Exception:
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

        # ที่พักให้เช่า: use same hotel API, label as rentals
        if "rentals" in intents:
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

        # Popular destinations (with location context)
        if "popular_destinations" in intents:
            tasks.append(self.get_popular_destinations(loc_info.get("lat"), loc_info.get("lng")))
        else:
            tasks.append(asyncio.sleep(0, result=None))

        results = await asyncio.gather(*tasks, return_exceptions=True)

        flights = results[0] if isinstance(results[0], list) else None
        hotels = results[1] if isinstance(results[1], list) else None
        rentals = results[2] if isinstance(results[2], list) else None
        activities = results[3] if isinstance(results[3], list) else None
        transfers = results[4] if isinstance(results[4], list) else None
        popular_destinations = results[5] if isinstance(results[5], list) else None

        # If bundle requested hotels but not rentals, rentals stays None
        if "rentals" not in intents:
            rentals = None

        response = UnifiedTravelResponse(
            intent=", ".join(intents),
            location=loc_info,
            flights=flights,
            hotels=hotels,
            rentals=rentals,
            activities=activities,
            transfers=transfers,
            popular_destinations=popular_destinations,
            summary=f"พบข้อมูลสำหรับการเดินทางไป {loc_info['city']} เรียบร้อยแล้วค่ะ",
        )
        return response

    # -------------------------------------------------------------------------
    # Core Data Fetchers (Amadeus REST)
    # -------------------------------------------------------------------------
    
    async def get_flights(self, origin: str = "BKK", destination: str = "NRT", departure_date: str = None, adults: int = 1, non_stop: bool = False, cabin_class: Optional[str] = None) -> List[Dict[str, Any]]:
        """Fetch Flight Offers with flexible parameters
        
        Args:
            origin: Origin city name or IATA code
            destination: Destination city name or IATA code
            departure_date: Departure date in YYYY-MM-DD format
            adults: Number of adult passengers
            non_stop: If True, only return non-stop flights
            cabin_class: Cabin class (ECONOMY, PREMIUM_ECONOMY, BUSINESS, FIRST)
        """
        token = await self._get_amadeus_token()
        
        # Use provided date or default to 30 days from now; normalize Buddhist year (พ.ศ.) to Christian
        if not departure_date:
            date = (datetime.now() + timedelta(days=30)).strftime("%Y-%m-%d")
        else:
            date = str(departure_date).strip()
            try:
                parts = date.split("-")
                if len(parts) == 3:
                    y, m, d = int(parts[0]), int(parts[1]), int(parts[2])
                    if y > 2100:  # Buddhist Era (พ.ศ.) -> subtract 543
                        y = y - 543
                        date = f"{y:04d}-{m:02d}-{d:02d}"
                        logger.info(f"📅 Normalized Buddhist date to Christian: {date}")
            except (ValueError, IndexError):
                pass
        
        # Ensure origin and destination are IATA codes
        origin_code = origin if len(origin) == 3 and origin.isupper() else await self._city_to_iata_sync(origin)
        dest_code = destination if len(destination) == 3 and destination.isupper() else await self._city_to_iata_sync(destination)
        
        # ✅ Log IATA code resolution with detailed info
        logger.info(f"📍 IATA Resolution: '{origin}' → '{origin_code}', '{destination}' → '{dest_code}'")
        
        if not origin_code or not dest_code:
            logger.error(
                f"❌ CRITICAL: Could not resolve IATA codes - Search will fail!\n"
                f"   Origin: '{origin}' → {origin_code or 'FAILED'}\n"
                f"   Destination: '{destination}' → {dest_code or 'FAILED'}\n"
                f"   Please check:\n"
                f"   1. City names are correct and spelled properly\n"
                f"   2. Google Maps API is configured (GOOGLE_MAPS_API_KEY)\n"
                f"   3. Amadeus API is accessible"
            )
            return []
        
        params = {
            "originLocationCode": origin_code,
            "destinationLocationCode": dest_code,
            "departureDate": date,
            "adults": adults,
            "max": 10,
            "nonStop": "true" if non_stop else "false",
            "currencyCode": "THB"
        }
        
        # Add cabin class if specified
        if cabin_class:
            # Map cabin class names to Amadeus format
            cabin_map = {
                "ECONOMY": "ECONOMY",
                "PREMIUM_ECONOMY": "PREMIUM_ECONOMY",
                "BUSINESS": "BUSINESS",
                "FIRST": "FIRST"
            }
            amadeus_cabin = cabin_map.get(cabin_class.upper())
            if amadeus_cabin:
                params["travelClass"] = amadeus_cabin
                logger.info(f"Filtering flights by cabin class: {amadeus_cabin}")

        try:
            # ✅ Validate date range (Amadeus typically supports up to 11 months ahead)
            from datetime import datetime, timedelta
            try:
                search_date = datetime.strptime(date, "%Y-%m-%d")
                today = datetime.now()
                days_ahead = (search_date - today).days
                max_days_ahead = 330  # ~11 months
                
                if days_ahead < 0:
                    logger.warning(f"⚠️ Search date {date} is in the past ({-days_ahead} days ago)")
                elif days_ahead > max_days_ahead:
                    logger.warning(
                        f"⚠️ Search date {date} is {days_ahead} days ahead (max: {max_days_ahead} days). "
                        f"Amadeus may not have data for dates this far in the future."
                    )
            except ValueError:
                logger.warning(f"⚠️ Invalid date format: {date}")
            
            # ✅ Log search parameters and confirm production URL
            env_label = "production" if "api.amadeus.com" in self.amadeus_search_base_url and "test." not in self.amadeus_search_base_url else "test"
            logger.info(f"🔍 Amadeus Flight Search ({env_label}): {self.amadeus_search_base_url} | {origin_code} → {dest_code} on {date} ({adults} adult(s))")
            
            # ✅ Search: ใช้ production environment
            resp = await self.client.get(
                f"{self.amadeus_search_base_url}/v2/shopping/flight-offers",
                params=params,
                headers={"Authorization": f"Bearer {token}"}
            )
            resp.raise_for_status()
            
            # ✅ Validate response structure
            response_json = resp.json()
            if not isinstance(response_json, dict):
                logger.error(f"❌ Invalid Amadeus response structure: expected dict, got {type(response_json)}")
                return []
            
            data = response_json.get("data", [])
            meta = response_json.get("meta", {})

            # ✅ Check for warnings/errors in response (log clearly when using production)
            if "warnings" in response_json:
                logger.warning(f"⚠️ Amadeus API warnings: {response_json['warnings']}")
            if "errors" in response_json:
                err_list = response_json["errors"]
                logger.error(f"❌ Amadeus API errors (status={resp.status_code}): {err_list}")
                for err in (err_list if isinstance(err_list, list) else [err_list]):
                    logger.error(f"   Amadeus error: code={err.get('code')} title={err.get('title')} detail={err.get('detail')}")

            # ✅ บินตรง: กรองเฉพาะเที่ยวบินตรง (ทุก itinerary ต้องมี 1 segment) แม้ API ส่งต่อเครื่องมา
            if data and non_stop:
                def _is_non_stop_offer(offer: dict) -> bool:
                    for itin in (offer.get("itineraries") or []):
                        if len(itin.get("segments") or []) > 1:
                            return False
                    return True
                before = len(data)
                data = [o for o in data if _is_non_stop_offer(o)]
                if before > len(data):
                    logger.warning(f"✅ Non-stop filter: removed {before - len(data)} connecting offers (kept {len(data)} direct)")

            # ✅ Log results with detailed information
            if data:
                logger.info(f"✅ Found {len(data)} flight options for {origin_code} → {dest_code} on {date}")
                return data
            
            # ✅ When 0 results: log meta/errors for debugging (especially with production key)
            logger.info(
                f"📋 Amadeus returned 0 flights for {origin_code}→{dest_code} on {date} | "
                f"meta.count={meta.get('count')} meta={meta} | errors={response_json.get('errors')}"
            )
            
            # ✅ FALLBACK: Try alternate airport for Osaka (KIX vs ITM)
            if dest_code == "KIX" and not data:
                logger.info(f"🔄 Trying alternate airport ITM (Osaka Itami) for {origin_code} → Osaka")
                params_itm = {**params, "destinationLocationCode": "ITM"}
                try:
                    resp_itm = await self.client.get(
                        f"{self.amadeus_search_base_url}/v2/shopping/flight-offers",
                        params=params_itm,
                        headers={"Authorization": f"Bearer {token}"}
                    )
                    if resp_itm.status_code == 200:
                        data_itm = resp_itm.json().get("data", [])
                        if data_itm:
                            if non_stop:
                                data_itm = [o for o in data_itm if all(len(itin.get("segments") or []) <= 1 for itin in (o.get("itineraries") or []))]
                            logger.info(f"✅ Found {len(data_itm)} flights via ITM (Osaka Itami)")
                            return data_itm[:10]
                except Exception as e_itm:
                    logger.debug(f"ITM fallback failed: {e_itm}")
            
            # ✅ FALLBACK: Try nearby dates (±1..±5 days) to increase chance of finding data (e.g. when Google has results)
            logger.info(f"⚠️ No flights found for {date}, trying fallback dates (±1..±5 days)...")
            fallback_dates = []
            try:
                from datetime import datetime, timedelta
                base_date = datetime.strptime(date, "%Y-%m-%d")
                for offset in [-3, -2, -1, 1, 2, 3, 5]:  # Wider range to match availability
                    fallback_date = (base_date + timedelta(days=offset)).strftime("%Y-%m-%d")
                    fallback_dates.append(fallback_date)
            except Exception:
                pass
            
            # ✅ Parallel fallback searches (try up to 4 dates, 10s timeout)
            if fallback_dates:
                import asyncio
                fallback_tasks = []
                for fallback_date in fallback_dates[:4]:  # Try 4 fallback dates for better hit rate
                    fallback_params = params.copy()
                    fallback_params["departureDate"] = fallback_date
                    task = self.client.get(
                        f"{self.amadeus_search_base_url}/v2/shopping/flight-offers",
                        params=fallback_params,
                        headers={"Authorization": f"Bearer {token}"}
                    )
                    fallback_tasks.append((fallback_date, task))
                
                try:
                    results_list = await asyncio.wait_for(
                        asyncio.gather(*[task for _, task in fallback_tasks], return_exceptions=True),
                        timeout=10.0
                    )
                    
                    for (fallback_date, _), result in zip(fallback_tasks, results_list):
                        if isinstance(result, Exception):
                            continue
                        try:
                            if hasattr(result, 'json'):
                                fallback_data = result.json().get("data", [])
                            else:
                                continue
                            if fallback_data:
                                logger.info(f"✅ Fallback success: Found {len(fallback_data)} flights for {fallback_date}")
                                for item in fallback_data:
                                    item["_fallback_date"] = fallback_date
                                    item["_original_date"] = date
                                data.extend(fallback_data[:3])
                                if len(data) >= 3:
                                    break
                        except Exception as e:
                            logger.debug(f"Error processing fallback result for {fallback_date}: {e}")
                            continue
                    
                    if data:
                        if non_stop:
                            data = [o for o in data if all(len(itin.get("segments") or []) <= 1 for itin in (o.get("itineraries") or []))]
                        logger.info(f"✅ Found {len(data)} total flight options (including fallback dates) → will show PlanChoiceCard")
                        return data[:10]
                except asyncio.TimeoutError:
                    logger.warning(f"⚠️ Fallback date searches timed out after 10s")
            
            # If still no results, log detailed diagnostic information
            full_response = response_json
            meta = full_response.get('meta', {})
            count = meta.get('count', 0)
            
            logger.warning(
                f"⚠️ No flights found for {origin_code} → {dest_code} on {date} (including fallback dates).\n"
                f"   URL: {self.amadeus_search_base_url} (production={('test' not in self.amadeus_search_base_url)})\n"
                f"   Response status: {resp.status_code}\n"
                f"   Response keys: {list(full_response.keys())}\n"
                f"   Meta count: {count}\n"
                f"   Meta: {meta}\n"
                f"   Errors: {full_response.get('errors')}\n"
                f"   Possible causes:\n"
                f"   1. Date too far in future (Amadeus supports ~11 months ahead)\n"
                f"   2. No flights available for this route/date\n"
                f"   3. IATA codes may be incorrect: {origin_code} or {dest_code}\n"
                f"   4. Route not serviced by airlines in Amadeus database\n"
                f"   5. If production: ensure AMADEUS_SEARCH_API_KEY + AMADEUS_SEARCH_API_SECRET are production keys (not test)"
            )
            logger.info(f"Full Amadeus response (first 1500 chars): {str(full_response)[:1500]}")
            
            return data
        except Exception as e:
            # ✅ Log HTTP response body when request fails (e.g. 401/403/429 with production key)
            err_detail = str(e)
            if hasattr(e, "response") and e.response is not None:
                try:
                    body = e.response.text if hasattr(e.response, "text") else getattr(e.response, "content", b"")
                    if body:
                        err_detail = f"{e} | response: {body[:500] if isinstance(body, str) else body[:500].decode('utf-8', errors='replace')}"
                except Exception:
                    pass
            logger.error(f"❌ Flight API error for {origin_code} → {dest_code} on {date}: {err_detail}", exc_info=True)
            return []
    
    async def _city_to_iata_sync(self, city_name: str) -> Optional[str]:
        """Convert city name to IATA code synchronously (using smart resolver with fallbacks)"""
        try:
            # ✅ Strategy 1: Prefer the smart 'find_city_iata' which uses Amadeus City Search first
            iata = await self.find_city_iata(city_name)
            if iata:
                return iata
            
            # ✅ Strategy 2: Fallback to Geo method (geocode -> nearest airport)
            try:
                loc_info = await self.get_coordinates(city_name)
                iata = await self.find_nearest_iata(loc_info["lat"], loc_info["lng"])
                if iata:
                    return iata
            except Exception as geo_e:
                logger.debug(f"Geo method failed for {city_name}: {geo_e}")
            
            # ✅ Strategy 3: Try with "airport" suffix
            try:
                airport_query = f"{city_name} airport"
                loc_info = await self.get_coordinates(airport_query)
                iata = await self.find_nearest_iata(loc_info["lat"], loc_info["lng"])
                if iata:
                    logger.info(f"✅ Found IATA via airport suffix: {city_name} → {iata}")
                    return iata
            except Exception as airport_e:
                logger.debug(f"Airport suffix method failed for {city_name}: {airport_e}")
            
            logger.warning(f"⚠️ All IATA resolution strategies failed for: {city_name}")
            return None
        except Exception as e:
            logger.warning(f"Failed to convert {city_name} to IATA: {e}")
            return None

    async def get_hotels(self, city_code: str = None, location_name: str = None, check_in: str = None, check_out: str = None, guests: int = 1) -> List[Dict[str, Any]]:
        """Fetch Hotel Offers with flexible location input"""
        token = await self._get_amadeus_token()

        # 1) Build a list of cityCode candidates.
        # In Amadeus sandbox, /reference-data/locations keyword search does NOT reliably return
        # Tokyo/Seoul/Osaka city codes. So we must also try nearest AIRPORT IATA as a candidate.
        codes_to_try: List[str] = []

        if isinstance(city_code, str) and city_code.strip():
            codes_to_try.append(city_code.strip())

        if isinstance(location_name, str) and location_name.strip():
            loc = location_name.strip()
            if len(loc) == 3 and loc.isupper():
                codes_to_try.append(loc)
            else:
                # Best-effort city resolver (works for some cities like BKK/PAR)
                try:
                    cc = await self.find_city_iata(loc)
                    if cc:
                        codes_to_try.append(cc)
                except Exception:
                    pass

                # Robust fallback: geocode -> nearest airport
                try:
                    loc_info = await self.get_coordinates(loc, language="en")
                    airport_iata = await self.find_nearest_iata(loc_info["lat"], loc_info["lng"])
                    if airport_iata:
                        codes_to_try.append(airport_iata)
                except Exception as e:
                    logger.warning(f"Hotel city resolution via nearest airport failed for '{loc}': {e}")

        # De-dup preserve order
        seen = set()
        deduped: List[str] = []
        for c in codes_to_try:
            if c and c not in seen:
                seen.add(c)
                deduped.append(c)
        codes_to_try = deduped

        if not codes_to_try:
            logger.error(f"Could not resolve any code for hotel search: location_name={location_name} city_code={city_code}")
            return []

        try:
            # 2) Search Hotels (try candidates by-city first, then by-geocode as fallback)
            hotels = []
            target_used = None
            
            # 2a) Try by-city first
            for code in codes_to_try:
                try:
                    logger.info(f"Searching hotels with cityCode candidate: {code} (from {location_name or city_code})")
                    # ✅ Search: ใช้ production environment
                    resp = await self._amadeus_get(
                        f"{self.amadeus_search_base_url}/v1/reference-data/locations/hotels/by-city",
                        token=token,
                        params={"cityCode": code, "radius": 5, "radiusUnit": "KM", "hotelSource": "ALL"},
                        retries=3,
                        use_booking_env=False,  # Search uses production
                    )
                    hotels = (resp.json().get("data") or [])[:15]
                    if hotels:
                        target_used = f"city:{code}"
                        break
                except Exception as e:
                    logger.warning(f"Hotel by-city failed for code={code}: {e}")
                    continue

            # 2b) Fallback: Try by-geocode (Radius search) if by-city failed or not available
            if not hotels and location_name:
                try:
                    loc_info = await self.get_coordinates(location_name)
                    lat, lng = loc_info["lat"], loc_info["lng"]
                    logger.info(f"Searching hotels by geocode: {lat},{lng} (radius 5km)")
                    # ✅ Search: ใช้ production environment
                    resp = await self._amadeus_get(
                        f"{self.amadeus_search_base_url}/v1/reference-data/locations/hotels/by-geocode",
                        token=token,
                        use_booking_env=False,  # Search uses production
                        params={
                            "latitude": lat,
                            "longitude": lng,
                            "radius": 5,
                            "radiusUnit": "KM",
                            "hotelSource": "ALL"
                        },
                        retries=3
                    )
                    hotels = (resp.json().get("data") or [])[:15]
                    if hotels:
                        target_used = f"geo:{lat},{lng}"
                except Exception as e:
                    logger.warning(f"Hotel by-geocode failed for {location_name}: {e}")

            if not hotels:
                logger.warning(
                    f"⚠️ No hotels found for any candidates or geocode fallback: {codes_to_try}\n"
                    f"   Location searched: {location_name or city_code}\n"
                    f"   Possible causes:\n"
                    f"   1. Location name may be incorrect or too specific\n"
                    f"   2. No hotels in Amadeus database for this location\n"
                    f"   3. IATA/city codes could not be resolved\n"
                    f"   4. Google Maps geocoding may have failed"
                )
                return []

            hotel_ids = ",".join([h["hotelId"] for h in hotels if h.get("hotelId")])
            if not hotel_ids:
                logger.warning(f"No hotelIds returned for candidates {codes_to_try}")
                # ✅ Fallback: Try using cityCode directly if no hotelIds found
                if codes_to_try:
                    logger.info(f"Falling back to cityCode-based hotel search for: {codes_to_try[0]}")
                    try:
                        # Try hotel search by cityCode instead of hotelIds
                        # ✅ Search: ใช้ production environment
                        resp = await self._amadeus_get(
                            f"{self.amadeus_search_base_url}/v3/shopping/hotel-offers",
                            token=token,
                            params={
                                "cityCode": codes_to_try[0],
                                "adults": guests,
                                "currency": "THB",
                                **({"checkInDate": check_in} if check_in else {}),
                                **({"checkOutDate": check_out} if check_out else {})
                            },
                            retries=2,
                            use_booking_env=False,  # Search uses production
                        )
                        data = resp.json().get("data", []) or []
                        if data:
                            logger.info(f"Successfully found {len(data)} hotels using cityCode fallback")
                            for item in data:
                                item.setdefault("_debug", {})
                                item["_debug"]["city_code_used"] = f"cityCode:{codes_to_try[0]}"
                                item["_debug"]["candidates_tried"] = codes_to_try
                            return data
                    except Exception as fallback_error:
                        logger.warning(f"CityCode fallback also failed: {fallback_error}")
                return []

            # ✅ Log hotel search summary
            logger.info(f"🔍 Found {len(hotels)} hotel references, extracting {len(hotel_ids.split(','))} hotelIds for offers search")
            
            # 3) Get Offers for those Hotels
            offer_params = {"hotelIds": hotel_ids, "adults": guests, "currency": "THB"}
            if check_in:
                offer_params["checkInDate"] = check_in
            if check_out:
                offer_params["checkOutDate"] = check_out

            try:
                # ✅ Search: ใช้ production environment
                resp = await self._amadeus_get(
                    f"{self.amadeus_search_base_url}/v3/shopping/hotel-offers",
                    token=token,
                    params=offer_params,
                    retries=3,
                    use_booking_env=False,  # Search uses production
                )
                data = resp.json().get("data", []) or []
                
                # ✅ Log hotel offers results
                if data:
                    logger.info(f"✅ Found {len(data)} hotel offers for {len(hotel_ids.split(','))} hotels (check_in={check_in}, check_out={check_out}, guests={guests})")
                else:
                    # ✅ FALLBACK: Try date range search if no offers found
                    logger.info(f"⚠️ No hotel offers found for {check_in} to {check_out}, trying fallback dates...")
                    try:
                        check_in_dt = datetime.strptime(check_in, "%Y-%m-%d")
                        check_out_dt = datetime.strptime(check_out, "%Y-%m-%d")
                        
                        # Try ±1 day for check-in (keep same duration)
                        fallback_dates = [
                            ((check_in_dt + timedelta(days=-1)).strftime("%Y-%m-%d"), 
                             (check_out_dt + timedelta(days=-1)).strftime("%Y-%m-%d")),
                            ((check_in_dt + timedelta(days=1)).strftime("%Y-%m-%d"), 
                             (check_out_dt + timedelta(days=1)).strftime("%Y-%m-%d"))
                        ]
                        
                        # ✅ Try fallback dates (limit to 1 for speed)
                        for fb_check_in, fb_check_out in fallback_dates[:1]:
                            try:
                                fb_offer_params = offer_params.copy()
                                fb_offer_params["checkInDate"] = fb_check_in
                                fb_offer_params["checkOutDate"] = fb_check_out
                                
                                fb_resp = await self._amadeus_get(
                                    f"{self.amadeus_search_base_url}/v3/shopping/hotel-offers",
                                    token=token,
                                    params=fb_offer_params,
                                    retries=1,
                                    use_booking_env=False,
                                )
                                fb_data = fb_resp.json().get("data", []) or []
                                if fb_data:
                                    logger.info(f"✅ Fallback success: Found {len(fb_data)} hotel offers for {fb_check_in} to {fb_check_out}")
                                    # Mark as fallback results
                                    for item in fb_data:
                                        item["_fallback_check_in"] = fb_check_in
                                        item["_fallback_check_out"] = fb_check_out
                                    data.extend(fb_data[:3])  # Limit to top 3
                                    break
                            except Exception as fb_e:
                                logger.debug(f"Fallback date search failed for {fb_check_in}: {fb_e}")
                                continue
                    except Exception as e:
                        logger.warning(f"⚠️ Fallback date search setup failed: {e}")
                    
                    if not data:
                        # ✅ Check date range for better warning
                        try:
                            from datetime import datetime
                            check_in_dt = datetime.strptime(check_in, "%Y-%m-%d")
                            today = datetime.now()
                            days_ahead = (check_in_dt - today).days
                            max_days = 330
                            
                            date_info = ""
                            if days_ahead < 0:
                                date_info = f" (date is {-days_ahead} days in the past)"
                            elif days_ahead > max_days:
                                date_info = f" (date is {days_ahead} days ahead, max: {max_days} days)"
                        except Exception:
                            date_info = ""
                        
                        logger.warning(
                            f"⚠️ No hotel offers found for hotelIds={hotel_ids} (check_in={check_in}, check_out={check_out}, guests={guests}){date_info}\n"
                            f"   Possible causes:\n"
                            f"   1. Date too far in future (Amadeus supports ~11 months ahead)\n"
                            f"   2. No availability for these dates\n"
                            f"   3. Hotels may not have offers loaded in Amadeus for this period"
                        )
            except Exception as offers_error:
                # ✅ If hotelIds approach fails, try cityCode fallback
                error_msg = str(offers_error).lower()
                if "400" in error_msg or "bad request" in error_msg:
                    logger.warning(f"Hotel offers API failed with hotelIds, trying cityCode fallback: {offers_error}")
                    if codes_to_try:
                        try:
                            # ✅ Search: ใช้ production environment
                            resp = await self._amadeus_get(
                                f"{self.amadeus_search_base_url}/v3/shopping/hotel-offers",
                                token=token,
                                use_booking_env=False,  # Search uses production
                                params={
                                    "cityCode": codes_to_try[0],
                                    "adults": guests,
                                    "currency": "THB",
                                    **({"checkInDate": check_in} if check_in else {}),
                                    **({"checkOutDate": check_out} if check_out else {})
                                },
                                retries=2,
                            )
                            data = resp.json().get("data", []) or []
                            logger.info(f"Successfully found {len(data)} hotels using cityCode fallback after hotelIds failure")
                            for item in data:
                                item.setdefault("_debug", {})
                                item["_debug"]["city_code_used"] = f"cityCode:{codes_to_try[0]} (fallback)"
                                item["_debug"]["candidates_tried"] = codes_to_try
                            return data
                        except Exception as fallback_error:
                            logger.error(f"CityCode fallback also failed: {fallback_error}")
                            return []
                raise
            for item in data:
                item.setdefault("_debug", {})
                item["_debug"]["city_code_used"] = target_used
                item["_debug"]["candidates_tried"] = codes_to_try
            
            # ✅ Final logging
            if data:
                logger.info(f"✅ Returning {len(data)} hotel offers for {location_name or city_code}")
            else:
                hotel_ids_count = len(hotel_ids.split(',')) if hotel_ids else 0
                logger.warning(
                    f"⚠️ No hotel offers returned for {location_name or city_code} "
                    f"(check_in={check_in}, check_out={check_out}). "
                    f"Tried city codes: {codes_to_try if 'codes_to_try' in locals() else 'N/A'}, "
                    f"Hotel IDs searched: {hotel_ids_count}"
                )
            
            return data
        except Exception as e:
            logger.error(f"❌ Hotel API error for {location_name or city_code}: {e}", exc_info=True)
            return []

    async def get_activities(self, lat: float, lng: float) -> List[Dict[str, Any]]:
        """Fetch Experiences/Activities"""
        token = await self._get_amadeus_token()
        try:
            # ✅ Search: ใช้ production environment
            resp = await self.client.get(
                f"{self.amadeus_search_base_url}/v1/shopping/activities",
                params={"latitude": lat, "longitude": lng, "radius": 10},
                headers={"Authorization": f"Bearer {token}"}
            )
            return resp.json().get("data", [])
        except Exception as e:
            logger.error(f"Activities API error: {e}")
            return []

    async def get_hotels_google(self, location_name: str, limit: int = 10, radius_m: int = 8000) -> List[Dict[str, Any]]:
        """
        Fallback hotel discovery using Google Places (not bookable via Amadeus).
        Returns rich place details to be shown when Amadeus sandbox can't provide results.
        """
        if not self.gmaps:
            raise AgentException("Google Maps API not configured")

        loc = await self.get_coordinates(location_name, language="en")
        lat, lng = loc["lat"], loc["lng"]

        loop = asyncio.get_event_loop()

        def _nearby():
            return self.gmaps.places_nearby(location=(lat, lng), radius=radius_m, type="lodging")

        nearby = await loop.run_in_executor(None, _nearby)
        results = (nearby or {}).get("results", [])[:limit]

        # NOTE: To keep this robust (and avoid Places Details field mismatches),
        # we rely on Nearby Search results which already include name/rating/photos/vicinity.
        places: List[Dict[str, Any]] = []
        for r in results:
            place = dict(r)
            place["_resolved_city"] = loc.get("city")
            place["_resolved_country"] = loc.get("country_code")
            # Normalize address key for downstream
            if "formatted_address" not in place and place.get("vicinity"):
                place["formatted_address"] = place.get("vicinity")
            places.append(place)

        return places

    async def get_transfers(self, airport_code: str, address: str) -> List[Dict[str, Any]]:
        """Fetch Transfer Offers (Legacy: Code to Address)"""
        token = await self._get_amadeus_token()
        date_time = (datetime.now() + timedelta(days=30)).strftime("%Y-%m-%dT10:00:00")
        try:
            # ✅ Search: ใช้ production environment
            resp = await self.client.get(
                f"{self.amadeus_search_base_url}/v1/shopping/transfer-offers",
                params={
                    "startLocationCode": airport_code,
                    "endAddressLine": address,
                    "startDateTime": date_time,
                    "passengers": 1,
                    "currency": "THB"
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
            # ✅ Search: ใช้ production environment
            resp = await self.client.post(
                f"{self.amadeus_search_base_url}/v1/shopping/transfer-offers",
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
                    "passengers": passengers,
                    "currency": "THB"
                },
                headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
            )
            resp.raise_for_status()
            return resp.json().get("data", [])
        except Exception as e:
            logger.error(f"Transfer Geo API error: {e}")
            return []
    
    # =============================================================================
    # 🔒 Booking Operations (Sandbox Only - Production Blocked)
    # =============================================================================
    
    async def _get_amadeus_booking_token(self) -> str:
        """
        Get Amadeus OAuth2 token for booking operations (sandbox only)
        ✅ SECURITY: Always uses sandbox environment and separate booking API keys
        """
        # ✅ SECURITY: Force sandbox for booking
        booking_env = settings.amadeus_booking_env.lower()
        if booking_env == "production":
            logger.error("🚨 SECURITY: AMADEUS_BOOKING_ENV=production is NOT ALLOWED! Using sandbox instead.")
            booking_env = "test"
        
        base_url = self.amadeus_booking_base_url  # Always sandbox
        
        # Check if token is still valid (with 5 minute buffer)
        # Note: We should use separate token cache for booking, but for simplicity using same cache
        if self._token and time.time() < self._token_expiry - 300:
            return self._token
        
        logger.info("Refreshing Amadeus OAuth2 token for booking (sandbox only)...")
        try:
            # ✅ Use separate booking API keys for security
            response = await self.client.post(
                f"{base_url}/v1/security/oauth2/token",
                data={
                    "grant_type": "client_credentials",
                    "client_id": self.amadeus_booking_client_id,
                    "client_secret": self.amadeus_booking_client_secret
                },
                headers={"Content-Type": "application/x-www-form-urlencoded"}
            )
            response.raise_for_status()
            data = response.json()
            
            self._token = data["access_token"]
            # Set expiry with a small buffer (10 seconds)
            self._token_expiry = time.time() + data["expires_in"] - 10
            
            logger.info("Amadeus booking token refreshed successfully (sandbox)")
            return self._token
        except Exception as e:
            logger.error(f"Failed to authenticate with Amadeus (booking/sandbox): {e}")
            raise AmadeusException("Authentication failed with Amadeus API (booking/sandbox)")
    
    async def create_flight_order(self, flight_offer: Dict[str, Any], travelers: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Create flight order via Amadeus API
        ✅ SECURITY: Only works in sandbox, production is blocked
        
        Args:
            flight_offer: Flight offer data from search
            travelers: List of traveler information
            
        Returns:
            Order confirmation data
            
        Raises:
            AmadeusException: If booking environment is production or API call fails
        """
        # ✅ SECURITY: Block production booking
        booking_env = settings.amadeus_booking_env.lower()
        if booking_env == "production":
            error_msg = "🚨 SECURITY: Flight booking in production is NOT ALLOWED! Use sandbox environment only."
            logger.error(error_msg)
            raise AmadeusException(error_msg)
        
        token = await self._get_amadeus_booking_token()
        
        try:
            # Use booking base URL (sandbox)
            response = await self.client.post(
                f"{self.amadeus_booking_base_url}/v1/booking/flight-orders",
                json={
                    "data": {
                        "type": "flight-order",
                        "flightOffers": [flight_offer],
                        "travelers": travelers
                    }
                },
                headers={
                    "Authorization": f"Bearer {token}",
                    "Content-Type": "application/json"
                },
                timeout=30.0
            )
            response.raise_for_status()
            return response.json()
        except Exception as e:
            logger.error(f"Failed to create flight order (sandbox): {e}")
            raise AmadeusException(f"Failed to create flight order: {str(e)}")
    
    async def create_hotel_booking(self, hotel_offer: Dict[str, Any], guests: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Create hotel booking via Amadeus API
        ✅ SECURITY: Only works in sandbox, production is blocked
        
        Args:
            hotel_offer: Hotel offer data from search
            guests: List of guest information
            
        Returns:
            Booking confirmation data
            
        Raises:
            AmadeusException: If booking environment is production or API call fails
        """
        # ✅ SECURITY: Block production booking
        booking_env = settings.amadeus_booking_env.lower()
        if booking_env == "production":
            error_msg = "🚨 SECURITY: Hotel booking in production is NOT ALLOWED! Use sandbox environment only."
            logger.error(error_msg)
            raise AmadeusException(error_msg)
        
        token = await self._get_amadeus_booking_token()
        
        try:
            # Use booking base URL (sandbox)
            response = await self.client.post(
                f"{self.amadeus_booking_base_url}/v3/booking/hotel-bookings",
                json={
                    "data": {
                        "offerId": hotel_offer.get("id"),
                        "guests": guests,
                        "payments": [{
                            "method": "CREDIT_CARD",
                            "card": {
                                "vendorCode": "VI",
                                "cardNumber": "4111111111111111",  # Test card
                                "expiryDate": "12/25"
                            }
                        }]
                    }
                },
                headers={
                    "Authorization": f"Bearer {token}",
                    "Content-Type": "application/json"
                },
                timeout=30.0
            )
            response.raise_for_status()
            return response.json()
        except Exception as e:
            logger.error(f"Failed to create hotel booking (sandbox): {e}")
            raise AmadeusException(f"Failed to create hotel booking: {str(e)}")

    async def delete_flight_order(self, flight_order_id: str) -> None:
        """
        Cancel/delete a flight order in Amadeus sandbox (sync เมื่อยกเลิกการจอง)
        DELETE /v1/booking/flight-orders/{id}
        """
        booking_env = settings.amadeus_booking_env.lower()
        if booking_env == "production":
            logger.warning("Amadeus booking env is production — skip delete flight order")
            return
        token = await self._get_amadeus_booking_token()
        from urllib.parse import quote
        safe_id = quote(flight_order_id, safe="")
        try:
            response = await self.client.delete(
                f"{self.amadeus_booking_base_url}/v1/booking/flight-orders/{safe_id}",
                headers={"Authorization": f"Bearer {token}"},
                timeout=30.0
            )
            response.raise_for_status()
            logger.info(f"Amadeus sandbox flight order deleted: {flight_order_id}")
        except Exception as e:
            logger.warning(f"Amadeus delete flight order failed: {flight_order_id} — {e}")
            raise AmadeusException(f"Failed to cancel flight order: {str(e)}")

    async def close(self):
        """Cleanup resources"""
        await self.client.aclose()

# Global instance
orchestrator = TravelOrchestrator()

