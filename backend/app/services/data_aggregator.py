"""
Unified Data Aggregator Service
Handles data normalization, prioritization, and categorization for AI Travel Agent.
Acts as a middleware between raw API responses (Amadeus/Google Maps) and LLM/Frontend.
"""

from __future__ import annotations
from typing import List, Dict, Any, Optional, Union
from enum import Enum
from pydantic import BaseModel, Field
import logging
import asyncio

from app.core.logging import get_logger
from app.core.config import settings
from app.services.travel_service import TravelOrchestrator
from app.models.trip_plan import (
    MergedHotelOption, HotelBookingDetails, HotelPricing, HotelRoom, HotelPolicy,
    HotelAmenities, HotelLocation, HotelVisuals, AIPerspective
)

logger = get_logger(__name__)

# =============================================================================
# Unified Schema Models
# =============================================================================

class ItemCategory(str, Enum):
    FLIGHT = "flight"
    HOTEL = "hotel"
    ACTIVITY = "activity"
    CRUISE = "cruise"
    TRANSFER = "transfer"
    UNKNOWN = "unknown"

class StandardizedItem(BaseModel):
    """
    Unified data structure for all travel items.
    Ensures consistent consumption by LLM and Frontend.
    """
    id: str = Field(..., description="Unique identifier for the item")
    category: ItemCategory = Field(..., description="Item category")
    provider: str = Field(default="Unknown", description="Service provider (e.g., Airline, Hotel Chain)")
    display_name: str = Field(..., description="Human-readable name")
    
    # Pricing
    price_amount: float = Field(default=0.0, description="Price value")
    currency: str = Field(default="THB", description="Currency code")
    is_price_available: bool = Field(default=True, description="True if price is confirmed/available")
    
    # Details
    rating: Optional[float] = Field(default=None, description="Rating (0-5)")
    duration: Optional[str] = Field(default=None, description="Duration string (e.g., '2h 30m')")
    description: Optional[str] = Field(default=None, description="Short description or amenities")
    
    # Location/Timing
    location: Optional[str] = Field(default=None, description="Location name or address")
    start_time: Optional[str] = Field(default=None, description="Departure/Start time (ISO)")
    end_time: Optional[str] = Field(default=None, description="Arrival/End time (ISO)")
    
    # Metadata for booking/linking
    deep_link_url: Optional[str] = Field(default=None, description="Booking URL if available")
    raw_data: Dict[str, Any] = Field(default_factory=dict, description="Original raw data for reference")
    
    # UI Hints
    tags: List[str] = Field(default_factory=list, description="Tags like 'Cheapest', 'Recommended'")
    recommended: bool = Field(default=False, description="True if this is a recommended choice")

# =============================================================================
# Data Aggregator Service
# =============================================================================

class DataAggregator:
    """
    Service to aggregate, normalize, and prioritize travel data.
    """
    
    def __init__(self):
        self.orchestrator = TravelOrchestrator()
        
    async def normalize_mcp_results(
        self,
        request_type: str,
        raw_results: List[Dict[str, Any]],
        requirements: Dict[str, Any]
    ) -> List[StandardizedItem]:
        """
        Normalize MCP tool results to StandardizedItem format
        
        Args:
            request_type: 'flight', 'hotel', 'transfer'
            raw_results: Raw results from MCP tools
            requirements: Original requirements for context
            
        Returns:
            List of StandardizedItem objects
        """
        standardized = []
        
        try:
            if request_type == "flight":
                for idx, flight in enumerate(raw_results):
                    try:
                        # Extract flight information
                        itineraries = flight.get("itineraries", [])
                        price = flight.get("price", {})
                        
                        if not itineraries:
                            continue
                        
                        # Get first itinerary
                        itinerary = itineraries[0]
                        segments = itinerary.get("segments", [])
                        if not segments:
                            continue
                        
                        first_seg = segments[0]
                        last_seg = segments[-1]
                        
                        # Build display name
                        origin_code = first_seg.get("departure", {}).get("iataCode", "")
                        dest_code = last_seg.get("arrival", {}).get("iataCode", "")
                        carrier = first_seg.get("carrierCode", "")
                        display_name = f"{carrier} {origin_code} → {dest_code}"
                        
                        # Calculate duration
                        duration = itinerary.get("duration", "")
                        
                        # Price
                        price_amount = float(price.get("total", 0)) if price.get("total") else 0.0
                        currency = price.get("currency", "THB")
                        
                        item = StandardizedItem(
                            id=f"mcp_flight_{idx}",
                            category=ItemCategory.FLIGHT,
                            provider=carrier,
                            display_name=display_name,
                            price_amount=price_amount,
                            currency=currency,
                            duration=duration,
                            start_time=first_seg.get("departure", {}).get("at"),
                            end_time=last_seg.get("arrival", {}).get("at"),
                            location=f"{origin_code} → {dest_code}",
                            raw_data=flight
                        )
                        standardized.append(item)
                    except Exception as e:
                        logger.warning(f"Failed to normalize flight {idx}: {e}")
                        continue
            
            elif request_type == "hotel":
                for idx, hotel in enumerate(raw_results):
                    try:
                        hotel_name = hotel.get("name", "Unknown Hotel")
                        address = hotel.get("address", {}).get("lines", [])
                        address_str = ", ".join(address) if address else ""
                        
                        # Price
                        price_info = hotel.get("price", {})
                        price_amount = float(price_info.get("total", 0)) if price_info.get("total") else 0.0
                        currency = price_info.get("currency", "THB")
                        
                        # Rating
                        rating = hotel.get("rating", 0)
                        
                        item = StandardizedItem(
                            id=f"mcp_hotel_{idx}",
                            category=ItemCategory.HOTEL,
                            provider=hotel.get("chainCode", "Unknown"),
                            display_name=hotel_name,
                            price_amount=price_amount,
                            currency=currency,
                            rating=rating,
                            location=address_str,
                            description=hotel.get("description", {}).get("text", ""),
                            raw_data=hotel
                        )
                        standardized.append(item)
                    except Exception as e:
                        logger.warning(f"Failed to normalize hotel {idx}: {e}")
                        continue
            
            elif request_type == "transfer":
                for idx, transfer in enumerate(raw_results):
                    try:
                        transfer_type = transfer.get("category", "car")
                        price_info = transfer.get("price", {})
                        price_amount = float(price_info.get("total", 0)) if price_info.get("total") else 0.0
                        currency = price_info.get("currency", "THB")
                        
                        display_name = f"{transfer_type.capitalize()} Transfer"
                        
                        item = StandardizedItem(
                            id=f"mcp_transfer_{idx}",
                            category=ItemCategory.TRANSFER,
                            provider=transfer.get("companyName", "Unknown"),
                            display_name=display_name,
                            price_amount=price_amount,
                            currency=currency,
                            raw_data=transfer
                        )
                        standardized.append(item)
                    except Exception as e:
                        logger.warning(f"Failed to normalize transfer {idx}: {e}")
                        continue
            
            logger.info(f"✅ Normalized {len(standardized)} {request_type} items from MCP results")
            return standardized
            
        except Exception as e:
            logger.error(f"Error normalizing MCP results: {e}", exc_info=True)
            return []
    
    async def search_and_normalize(self, request_type: str, **kwargs) -> List[StandardizedItem]:
        """
        Main entry point for searching and normalizing data based on request type.
        
        Args:
            request_type: 'flight', 'hotel', 'transfer', 'activity'
            **kwargs: Arguments passed to underlying search methods
        """
        # Remove parameters not needed by underlying methods
        kwargs.pop('mode', None)  # Remove mode parameter (no longer used)
        kwargs.pop('user_id', None)
        allow_transit_visa = kwargs.pop('allow_transit_visa', True) # Default to True if not specified
        
        results = []
        try:
            if request_type == "flight":
                # Map 'departure_date' to 'date'
                if "departure_date" in kwargs:
                    kwargs["date"] = kwargs.pop("departure_date")
                
                # Check for "visa-free" requirement logic
                if not allow_transit_visa:
                    # Logic 1: Filter out transit requiring visa - For now, we can try to force non-stop if possible
                    # or filter results later. Amadeus nonStop param is useful here.
                    # But if user accepts stops but NO VISA, it's harder. 
                    # Simplified strategy: If NO VISA allowed, prefer non-stop first.
                    # We can try fetching non-stop first
                    kwargs["non_stop"] = True
                    results = await self._get_flights(**kwargs)
                    
                    # If no non-stop found, try normal search but we'll need to filter/warn later
                    if not results:
                        kwargs["non_stop"] = False
                        # Retry without non-stop constraint, but we will tag them as warning
                        logger.info("No non-stop flights found for visa-free preference, fallback to normal search with warnings")
                        results = await self._get_flights(**kwargs)
                else:
                    results = await self._get_flights(**kwargs)
                
                # ✅ FALLBACK: If no results, try removing cabin_class constraint (if specified)
                if not results and kwargs.get("cabin_class"):
                    logger.info(f"⚠️ No flights found with cabin_class={kwargs.get('cabin_class')}, trying without cabin class constraint...")
                    try:
                        fallback_kwargs = kwargs.copy()
                        fallback_kwargs.pop("cabin_class", None)
                        fallback_results = await self._get_flights(**fallback_kwargs)
                        if fallback_results:
                            logger.info(f"✅ Fallback success: Found {len(fallback_results)} flights without cabin class constraint")
                            # Mark as fallback results in raw_data
                            for item in fallback_results:
                                if hasattr(item, 'raw_data'):
                                    item.raw_data["_fallback_cabin_class"] = kwargs.get("cabin_class")
                            results.extend(fallback_results[:3])  # Limit to top 3
                    except Exception as fb_e:
                        logger.debug(f"Fallback cabin class search failed: {fb_e}")
            
            elif request_type == "hotel":
                # ✅ Send mode to _get_hotels for test mode unlimited results (if provided)
                # mode parameter is optional and removed earlier if not needed
                results = await self._get_hotels(**kwargs)
                
                # ✅ FALLBACK: If no results, try with simplified location (remove area/attraction suffixes)
                if not results and "location" in kwargs:
                    original_location = kwargs["location"]
                    # Try removing common suffixes like ", area", ", district", etc.
                    simplified_locations = [
                        original_location.split(",")[0].strip(),  # Just city name
                        original_location.split(" ")[0] if " " in original_location else original_location,  # First word
                    ]
                    
                    for simplified_loc in simplified_locations[:1]:  # Limit to 1 fallback for speed
                        if simplified_loc != original_location and len(simplified_loc) > 2:
                            logger.info(f"⚠️ No hotels found for '{original_location}', trying simplified location: '{simplified_loc}'")
                            try:
                                fallback_kwargs = kwargs.copy()
                                fallback_kwargs["location"] = simplified_loc
                                fallback_results = await self._get_hotels(**fallback_kwargs)
                                if fallback_results:
                                    logger.info(f"✅ Fallback success: Found {len(fallback_results)} hotels for '{simplified_loc}'")
                                    # Mark as fallback results in raw_data
                                    for item in fallback_results:
                                        if not hasattr(item, 'raw_data'):
                                            continue
                                        item.raw_data["_fallback_location"] = simplified_loc
                                        item.raw_data["_original_location"] = original_location
                                    results.extend(fallback_results[:3])  # Limit to top 3
                                    break
                            except Exception as fb_e:
                                logger.debug(f"Fallback location search failed for '{simplified_loc}': {fb_e}")
                                continue
            
            elif request_type == "transfer":
                # Handle Geocoding for Transfers if lat/lng not provided
                if "start_lat" not in kwargs and "origin" in kwargs:
                    start_loc = await self.orchestrator.get_coordinates(kwargs["origin"])
                    kwargs["start_lat"] = start_loc["lat"]
                    kwargs["start_lng"] = start_loc["lng"]
                
                if "end_lat" not in kwargs and "destination" in kwargs:
                    end_loc = await self.orchestrator.get_coordinates(kwargs["destination"])
                    kwargs["end_lat"] = end_loc["lat"]
                    kwargs["end_lng"] = end_loc["lng"]
                
                # Map 'date' or 'departure_date' to 'start_time'
                if "departure_date" in kwargs:
                    kwargs["start_time"] = kwargs.pop("departure_date")
                elif "date" in kwargs:
                    kwargs["start_time"] = kwargs.pop("date")

                if "start_time" in kwargs and kwargs["start_time"] and len(kwargs["start_time"]) == 10:
                    kwargs["start_time"] += "T10:00:00" # Default to 10 AM
                
                kwargs.pop("origin", None)
                kwargs.pop("destination", None)
                
                results = await self._get_transfers_smart(**kwargs)
            
            elif request_type == "activity":
                results = await self._get_activities(**kwargs)
            else:
                logger.warning(f"Unknown request type: {request_type}")
                return []

            # -------------------------------------------------------------------------
            # Unified Sorting, Filtering, and Tagging
            # -------------------------------------------------------------------------
            if results:
                # 0. Filter by max_price if provided
                if "max_price" in kwargs:
                    try:
                        max_price = float(kwargs["max_price"])
                        original_count = len(results)
                        results = [item for item in results if not item.is_price_available or item.price_amount <= max_price]
                        if len(results) < original_count:
                            logger.info(f"Filtered {original_count - len(results)} items exceeding budget {max_price}")
                    except (ValueError, TypeError):
                        logger.warning(f"Invalid max_price format: {kwargs['max_price']}")

                # Sort: Items with price first
                results.sort(key=lambda x: (not x.is_price_available, x.price_amount))
                
                # 1. Tag the cheapest
                if results[0].is_price_available:
                    results[0].tags.append("ถูกสุด")
                    results[0].recommended = True
                
                # 2. Special tags for flights
                if request_type == "flight":
                    def parse_dur(d):
                        if not d or not d.startswith("PT"): return 999999
                        try:
                            h = int(d.split('H')[0].replace('PT', '')) if 'H' in d else 0
                            m_part = d.split('H')[1] if 'H' in d else d.replace('PT', '')
                            m = int(m_part.replace('M', '')) if 'M' in m_part else 0
                            return h * 60 + m
                        except: return 999999
                    
                    fastest = min(results, key=lambda x: parse_dur(x.duration))
                    if "เร็วที่สุด" not in fastest.tags:
                        fastest.tags.append("เร็วที่สุด")
                        if not fastest.recommended:
                            fastest.recommended = True
                            
                    # Visa Logic Handling
                    for item in results:
                        # Logic 2: Self-Transfer Warning (Checking for 'Self Transfer' flag usually from aggregators like Kiwi, but here we can check carriers)
                        # Simplified: If multiple carriers in one itinerary, potential self-transfer risk (though Amadeus usually tickets together)
                        # We'll use segment logic in normalization to flag warnings
                        pass
                
                # 3. Add "แนะนำ" tag to the best overall (for now, same as cheapest or fastest)
                for item in results:
                    if item.recommended and "แนะนำ" not in item.tags:
                        item.tags.append("แนะนำ")

            return results
        except Exception as e:
            logger.error(f"Error in search_and_normalize for {request_type}: {e}", exc_info=True)
            return []

    # -------------------------------------------------------------------------
    # 1. Price-First Logic for Transfers
    # -------------------------------------------------------------------------
    
    async def _get_transfers_smart(self, 
                                 start_lat: float, start_lng: float, 
                                 end_lat: float, end_lng: float, 
                                 start_time: str = None, 
                                 passengers: int = 1) -> List[StandardizedItem]:
        """
        Smart Transfer Search:
        1. Try Activities API first (often has priced tours/transfers).
        2. If no result or low confidence, fallback to Transfer API.
        3. Combine and normalize.
        """
        results = []
        
        # 0. Inject Static/Hybrid Knowledge Base (Seoul, Bangkok, Tokyo, etc.)
        # This fulfills the "Hybrid PlanChoiceCard" requirement for common routes
        # We try to detect city context from coordinates (simplified)
        
        is_seoul = (37.0 < start_lat < 38.0 and 126.0 < start_lng < 127.0) or (37.0 < end_lat < 38.0 and 126.0 < end_lng < 127.0)
        is_bangkok = (13.0 < start_lat < 14.5 and 100.0 < start_lng < 101.0) or (13.0 < end_lat < 14.5 and 100.0 < end_lng < 101.0)
        
        if is_seoul:
            results.append(StandardizedItem(
                id="static_arex_icn",
                category=ItemCategory.TRANSFER,
                provider="AREX Express Train",
                display_name="รถไฟด่วน AREX (Incheon ⇄ Seoul Station)",
                price_amount=250.0,
                currency="THB",
                is_price_available=True,
                description="รถไฟด่วนความเร็วสูงตรงสู่ Seoul Station ใช้เวลา 43 นาที ไม่รถติด ประหยัดเวลาและค่าใช้จ่าย",
                duration="PT43M",
                tags=["ประหยัด", "แนะนำ", "ยอดนิยม"],
                recommended=True,
                raw_data={"static": True, "type": "train"}
            ))
            results.append(StandardizedItem(
                id="static_private_van_icn",
                category=ItemCategory.TRANSFER,
                provider="Private Transfer",
                display_name="รถรับส่งส่วนตัว (Private Van)",
                price_amount=2500.0,
                currency="THB",
                is_price_available=True, # Estimate
                description="รถตู้ส่วนตัวรับ-ส่งถึงหน้าโรงแรม สะดวกสบายที่สุด ไม่ต้องลากกระเป๋า เหมาะสำหรับมากันหลายคน",
                duration="PT1H30M",
                tags=["สะดวกสบาย", "ส่วนตัว"],
                recommended=False,
                raw_data={"static": True, "type": "private_car"}
            ))
            
        elif is_bangkok:
             results.append(StandardizedItem(
                id="static_arl_bkk",
                category=ItemCategory.TRANSFER,
                provider="Airport Rail Link",
                display_name="Airport Rail Link (City Line)",
                price_amount=45.0,
                currency="THB",
                is_price_available=True,
                description="รถไฟฟ้าเชื่อมท่าอากาศยานสุวรรณภูมิ เข้าสู่ตัวเมือง (พญาไท/มักกะสัน)",
                duration="PT30M",
                tags=["ประหยัด", "เลี่ยงรถติด"],
                recommended=True,
                raw_data={"static": True, "type": "train"}
            ))
             results.append(StandardizedItem(
                id="static_grab_bkk",
                category=ItemCategory.TRANSFER,
                provider="Grab / Taxi",
                display_name="Grab / Taxi (Public)",
                price_amount=400.0,
                currency="THB",
                is_price_available=True, # Estimate
                description="รถแท็กซี่หรือ Grab รับส่งถึงที่ (ราคาโดยประมาณไม่รวมค่าทางด่วน)",
                duration="PT1H",
                tags=["สะดวก", "24 ชม."],
                recommended=False,
                raw_data={"static": True, "type": "taxi"}
            ))

        # 1. Try fetching via Activities API (looking for "Transfer", "Pick-up", "Private Car")
        # We search near the start location
        logger.info(f"Smart Transfer: Checking Activities API for priced options at {start_lat},{start_lng}")
        try:
            activities_raw = await self.orchestrator.get_activities(lat=start_lat, lng=start_lng)
            
            transfer_keywords = ["transfer", "private car", "shuttle", "pick-up", "airport ride"]
            priced_transfers = []
            
            for act in activities_raw:
                name = act.get("name", "").lower()
                if any(kw in name for kw in transfer_keywords):
                    norm_item = self._normalize_activity(act)
                    # Override category to TRANSFER
                    norm_item.category = ItemCategory.TRANSFER
                    priced_transfers.append(norm_item)
            
            if priced_transfers:
                logger.info(f"Smart Transfer: Found {len(priced_transfers)} priced options via Activities API")
                results.extend(priced_transfers)
        except Exception as e:
            logger.warning(f"Activities API failed for transfer search: {e}")
        
        # 2. Always fetch from Transfer API to ensure variety (even if price is sometimes missing/estimate)
        logger.info("Smart Transfer: Fetching from dedicated Transfer API")
        try:
            transfers_raw = await self.orchestrator.get_transfers_by_geo(
                start_lat=start_lat, start_lng=start_lng,
                end_lat=end_lat, end_lng=end_lng,
                start_time=start_time, passengers=passengers
            )
            
            dedicated_transfers = [self._normalize_transfer(t) for t in transfers_raw]
            results.extend(dedicated_transfers)
        except Exception as e:
            logger.warning(f"Transfer API failed: {e}")
        
        return results

    # -------------------------------------------------------------------------
    # 2. Specific Data Fetchers & Categorization
    # -------------------------------------------------------------------------

    async def _get_flights(self, origin: str, destination: str, date: str, adults: int = 1, non_stop: bool = False, cabin_class: Optional[str] = None, direct_flight: Optional[bool] = None, **kwargs) -> List[StandardizedItem]:
        """
        Get flights
        
        Args:
            origin: Origin airport code
            destination: Destination airport code
            date: Departure date
            adults: Number of adult passengers
        """
        # Note: Amadeus API may have its own limits
        # Use direct_flight if provided, otherwise use non_stop
        use_non_stop = direct_flight if direct_flight is not None else non_stop
        
        # Map cabin class names to standard format
        cabin_mapping = {
            "PREMIUM_ECONOMY": "PREMIUM_ECONOMY",
            "premium economy": "PREMIUM_ECONOMY",
            "premium_economy": "PREMIUM_ECONOMY",
            "ECONOMY": "ECONOMY",
            "economy": "ECONOMY",
            "BUSINESS": "BUSINESS",
            "business": "BUSINESS",
            "FIRST": "FIRST",
            "first": "FIRST"
        }
        mapped_cabin = cabin_mapping.get(cabin_class, cabin_class) if cabin_class else None
        
        raw_data = await self.orchestrator.get_flights(
            origin=origin, 
            destination=destination, 
            departure_date=date, 
            adults=adults,
            non_stop=use_non_stop,
            cabin_class=mapped_cabin
        )
        return [self._normalize_flight(item) for item in raw_data]

    async def _get_hotels(self, location: str, check_in: str, check_out: str, guests: int = 1, **kwargs) -> List[StandardizedItem]:
        """
        Get hotels
        
        Args:
            location: Hotel location
            check_in: Check-in date
            check_out: Check-out date
            guests: Number of guests
            attractions: Optional list of attractions/tourist spots (for more accurate location search)
            near_attractions: Alternative field name for attractions
        """
        # Extract attractions from kwargs for enhanced location accuracy
        attractions = kwargs.pop('attractions', None) or kwargs.pop('near_attractions', None)
        if attractions:
            # Convert to list if string
            if isinstance(attractions, str):
                attractions = [attractions]
            
            # Enhance location with attractions for better search accuracy
            # Format: "City Name, Attraction1, Attraction2" or use attraction as primary location
            if attractions and len(attractions) > 0:
                # Use the first attraction or combine with location
                # Example: "Seoul, Myeongdong" or just "Myeongdong" if it's a well-known area
                enhanced_location = f"{location}, {attractions[0]}" if location else attractions[0]
                logger.info(f"Enhanced hotel search location with attractions: {enhanced_location} (original: {location}, attractions: {attractions})")
                location = enhanced_location
        
        # 1. Fetch from Amadeus (Source of truth for booking/pricing)
        raw_data = await self.orchestrator.get_hotels(location_name=location, check_in=check_in, check_out=check_out, guests=guests)
        
        if raw_data:
            logger.info(f"Found {len(raw_data)} hotels in Amadeus for {location}. Syncing with Google...")
            # For each Amadeus hotel, try to sync with Google Place data
            results = []
            # Process top 5 hotels for speed
            max_hotels = 5
            sync_tasks = [self._normalize_and_sync_hotel(item) for item in raw_data[:max_hotels]]
            results = await asyncio.gather(*sync_tasks)
            return [r for r in results if r]

        # 2. Fallback: Google Places (Only if Amadeus fails - NO real price/booking)
        try:
            logger.warning(f"Amadeus returned NO hotels for {location}. Falling back to Google discovery.")
            # Limit to 10 results
            google_limit = 10
            google_places = await self.orchestrator.get_hotels_google(location_name=location, limit=google_limit)
            if google_places:
                return [self._normalize_hotel_google(p) for p in google_places]
        except Exception as e:
            logger.warning(f"Google hotel fallback failed for {location}: {e}")
        return []

    async def _normalize_and_sync_hotel(self, amadeus_raw: Dict[str, Any]) -> Optional[StandardizedItem]:
        """
        Normalize Amadeus hotel and enrich with Google Place data.
        """
        from app.engine.agent import LocationIntelligence
        
        hotel_meta = amadeus_raw.get("hotel", {})
        hotel_name = hotel_meta.get("name", "Unknown Hotel")
        city_code = amadeus_raw.get("_debug", {}).get("city_code_used", "")
        
        # 1. Try to find the matching Google Place
        google_place_details = {}
        try:
            # Search for this specific hotel on Google
            search_query = f"{hotel_name} {city_code or ''}".strip()
            nearby = await LocationIntelligence.search_nearby_google(search_query, radius=500)
            if nearby:
                # Get details for the first match
                place_id = nearby[0]["place_id"]
                details = await LocationIntelligence.get_place_details_google(place_id)
                if details:
                    google_place_details = details
        except Exception as e:
            logger.warning(f"Failed to sync hotel '{hotel_name}' with Google: {e}")

        # 2. Use sync_hotel_data to merge
        try:
            merged = self.sync_hotel_data(amadeus_raw, google_place_details)
            
            # 3. Wrap in StandardizedItem for UI
            return StandardizedItem(
                id=merged.hotel_id,
                category=ItemCategory.HOTEL,
                provider=merged.chain_code or "Independent",
                display_name=merged.hotel_name,
                price_amount=merged.booking.pricing.total_amount,
                currency=merged.booking.pricing.currency,
                is_price_available=True,
                rating=merged.visuals.review_score or merged.star_rating,
                location=merged.location.address,
                description=merged.booking.room.description,
                raw_data=merged.model_dump(), # Store the full MergedHotelOption
                tags=["Amadeus", "ราคาจริง", "จองได้ทันที"],
                recommended=merged.visuals.review_score and merged.visuals.review_score >= 4.0
            )
        except Exception as e:
            logger.error(f"Error merging hotel data for {hotel_name}: {e}")
            # Fallback to simple normalization if merge fails
            return self._normalize_hotel(amadeus_raw)

    def _normalize_hotel_google(self, place: Dict[str, Any]) -> StandardizedItem:
        """Normalize Google Place (lodging) to StandardizedItem for UI fallback."""
        place_id = place.get("place_id", "unknown_place")
        name = place.get("name", "Unknown Hotel")
        addr = place.get("formatted_address") or ""
        rating = place.get("rating")
        user_ratings_total = place.get("user_ratings_total")

        # Keep raw google data under 'google_place' so chat mapper can detect
        return StandardizedItem(
            id=str(place_id),
            category=ItemCategory.HOTEL,
            provider="Google",
            display_name=name,
            price_amount=0.0,
            currency="THB",
            is_price_available=False,
            rating=float(rating) if rating is not None else None,
            location=addr,
            description="Google Places (no booking price in sandbox)",
            raw_data={"google_place": place, "note": "fallback_google"},
            tags=["Google", "ไม่ใช่ราคาจริง"],
            recommended=False,
        )

    async def _get_activities(self, lat: float, lng: float) -> List[StandardizedItem]:
        raw_data = await self.orchestrator.get_activities(lat, lng)
        normalized = []
        for item in raw_data:
            norm_item = self._normalize_activity(item)
            
            # Special Cruise/Boat Filter
            name_lower = norm_item.display_name.lower()
            if any(kw in name_lower for kw in ["cruise", "boat", "sailing", "yacht"]):
                norm_item.category = ItemCategory.CRUISE
            
            normalized.append(norm_item)
        return normalized

    # -------------------------------------------------------------------------
    # 3. Normalization Logic (Raw -> Unified Schema)
    # -------------------------------------------------------------------------

    def _normalize_flight(self, raw: Dict[str, Any]) -> StandardizedItem:
        """Normalize Flight Data"""
        itineraries = raw.get("itineraries", [])
        # Get first itinerary (assuming one-way or first leg of bound)
        main_itinerary = itineraries[0] if itineraries else {}
        segments = main_itinerary.get("segments", [])
        
        first_segment = segments[0] if segments else {}
        last_segment = segments[-1] if segments else {}
        
        price_dict = raw.get("price", {})
        
        # Logic 2 & 3 support: Analyze segments for transit/self-transfer
        is_self_transfer = False
        transit_warning = None
        
        if len(segments) > 1:
            # Check for multiple carriers (potential self-transfer indicator if not code-share)
            carriers = set(s.get("carrierCode") for s in segments)
            if len(carriers) > 1:
                # This is a heuristic. In real Amadeus responses, 'ticketing' info confirms if it's one ticket.
                # Here we flag it as a warning if mixed carriers.
                is_self_transfer = True 
                transit_warning = "ตรวจสอบเงื่อนไขการต่อเครื่อง (อาจต้องใช้วีซ่า)"

        # Enhanced Data Extraction for Production Checklist
        
        # 1. Traveler Pricings (Cabin, Baggage, Fare Rules)
        traveler_pricings = raw.get("travelerPricings", [{}])
        first_traveler = traveler_pricings[0] if traveler_pricings else {}
        fare_details = first_traveler.get("fareDetailsBySegment", [])
        
        # Cabin Class (e.g., ECONOMY, BUSINESS)
        cabin_class = fare_details[0].get("cabin") if fare_details else None
        
        # Baggage Allowance (Checked Bags)
        # Amadeus usually returns 'includedCheckedBags': {'weight': 20, 'weightUnit': 'KG'} or {'quantity': 1}
        baggage_info = first_traveler.get("fareDetailsBySegment", [{}])[0].get("includedCheckedBags", {})
        baggage_text = "N/A"
        if "weight" in baggage_info:
            baggage_text = f"{baggage_info['weight']} {baggage_info.get('weightUnit', 'KG')}"
        elif "quantity" in baggage_info:
            baggage_text = f"{baggage_info['quantity']} Piece(s)"
            
        # 2. Fare Rules (Refund/Change) - Simplified mapping
        # Ideally, we need 'fareRules' from a separate pricing API, but sometimes basic flags exist
        # raw['pricingOptions']['refundableFare'] is sometimes available
        pricing_opts = raw.get("pricingOptions", {})
        is_refundable = pricing_opts.get("refundableFare", False)
        is_changeable = not pricing_opts.get("noRestrictionFare", False) # Rough proxy

        norm_item = StandardizedItem(
            id=raw.get("id", "unknown_flight"),
            category=ItemCategory.FLIGHT,
            provider=first_segment.get("carrierCode", "Unknown Airline"),
            display_name=f"{first_segment.get('carrierCode')} {first_segment.get('number')} ({first_segment.get('departure', {}).get('iataCode')}->{last_segment.get('arrival', {}).get('iataCode')})",
            price_amount=float(price_dict.get("total", 0.0)),
            currency=price_dict.get("currency", "THB"),
            is_price_available=True,
            duration=main_itinerary.get("duration"),
            start_time=first_segment.get("departure", {}).get("at"),
            end_time=last_segment.get("arrival", {}).get("at"),
            raw_data=raw
        )
        
        # Inject extracted data into raw_data for Frontend mapping
        norm_item.raw_data["enhanced_info"] = {
            "cabin": cabin_class,
            "baggage": baggage_text,
            "refundable": is_refundable,
            "changeable": is_changeable,
            "transit_warning": transit_warning
        }
        
        # Inject warning into tags or raw_data for Frontend to pick up
        if is_self_transfer:
            norm_item.tags.append("Self-Transfer")
            
        return norm_item

    def _normalize_hotel(self, raw: Dict[str, Any]) -> StandardizedItem:
        """Normalize Hotel Data"""
        hotel = raw.get("hotel", {})
        offers = raw.get("offers", [])
        first_offer = offers[0] if offers else {}
        price_dict = first_offer.get("price", {})
        
        # Amenities extraction (if available)
        amenities = hotel.get("amenities", [])
        desc = ", ".join(amenities[:5]) if amenities else "No amenities listed"

        return StandardizedItem(
            id=hotel.get("hotelId", "unknown_hotel"),
            category=ItemCategory.HOTEL,
            provider=hotel.get("chainCode", "Independent"),
            display_name=hotel.get("name", "Unknown Hotel"),
            price_amount=float(price_dict.get("total", 0.0)),
            currency=price_dict.get("currency", "THB"),
            is_price_available=True,
            rating=float(hotel.get("rating", 0.0)) if hotel.get("rating") else None,
            location=hotel.get("address", {}).get("lines", [""])[0],
            description=desc,
            raw_data=raw
        )

    def _normalize_activity(self, raw: Dict[str, Any]) -> StandardizedItem:
        """Normalize Activity/Cruise Data"""
        price_dict = raw.get("price", {})
        
        return StandardizedItem(
            id=raw.get("id", "unknown_activity"),
            category=ItemCategory.ACTIVITY, # Can be overridden later
            provider=raw.get("bookingLink", "").split('/')[2] if raw.get("bookingLink") else "Amadeus",
            display_name=raw.get("name", "Unknown Activity"),
            price_amount=float(price_dict.get("amount", 0.0)),
            currency=price_dict.get("currencyCode", "THB"),
            is_price_available=bool(price_dict.get("amount")),
            rating=float(raw.get("rating", 0.0)) if raw.get("rating") else None,
            description=raw.get("shortDescription", "")[:200],
            deep_link_url=raw.get("bookingLink"),
            raw_data=raw
        )

    def _normalize_transfer(self, raw: Dict[str, Any]) -> StandardizedItem:
        """Normalize Ground Transport Data"""
        vehicle = raw.get("vehicle", {})
        price_dict = raw.get("price", {})
        quotation = raw.get("quotation", {})
        
        price_val = float(price_dict.get("total", 0.0))
        
        return StandardizedItem(
            id=raw.get("id", "unknown_transfer"),
            category=ItemCategory.TRANSFER,
            provider=raw.get("transferType", "Private Transfer"),
            display_name=f"{vehicle.get('category', 'Standard')} {vehicle.get('type', 'Car')}",
            price_amount=price_val,
            currency=price_dict.get("currency", "THB"),
            is_price_available=price_val > 0, # Important: Check if price is real
            description=f"Capacity: {vehicle.get('capacity', 1)} pax, Luggage: {vehicle.get('baggage', 0)}",
            duration=quotation.get("duration"), # ISO duration
            raw_data=raw
        )

    async def close(self):
        await self.orchestrator.close()

    # =============================================================================
    # 4. Hotel Data Synchronization (Amadeus + Google)
    # =============================================================================

    def sync_hotel_data(self, amadeus_offer: Dict[str, Any], google_place_details: Dict[str, Any]) -> MergedHotelOption:
        """
        Production-Grade Data Merger
        """
        # --- 1. Amadeus Extraction (Booking Core) ---
        hotel_meta = amadeus_offer.get("hotel", {})
        offer = amadeus_offer.get("offers", [{}])[0]
        
        # 1.1 Pricing
        price_data = offer.get("price", {})
        total = float(price_data.get("total", 0.0))
        currency = price_data.get("currency", "THB")
        
        # Calculate Base & Tax (if separate tax info is scarce, assume included or calculate diff)
        # Amadeus usually gives 'total' and sometimes 'base'.
        base = float(price_data.get("base")) if price_data.get("base") else total # Fallback
        # Some providers give taxes list
        taxes_val = 0.0
        if "taxes" in price_data:
            for t in price_data["taxes"]:
                taxes_val += float(t.get("amount", 0))
        else:
            taxes_val = total - base

        # Price per night calculation
        check_in_date = offer.get("checkInDate")
        check_out_date = offer.get("checkOutDate")
        nights = 1
        try:
            from datetime import datetime
            d1 = datetime.strptime(check_in_date, "%Y-%m-%d")
            d2 = datetime.strptime(check_out_date, "%Y-%m-%d")
            nights = (d2 - d1).days or 1
        except:
            pass
        
        pricing_obj = HotelPricing(
            total_amount=total,
            base_amount=base,
            taxes_and_fees=round(taxes_val, 2),
            currency=currency,
            price_per_night=round(total / nights, 2)
        )

        # 1.2 Room & Bed
        room_data = offer.get("room", {})
        type_est = room_data.get("typeEstimated", {})
        desc_text = room_data.get("description", {}).get("text") or type_est.get("category", "Standard")
        
        room_obj = HotelRoom(
            room_type=type_est.get("category", "STANDARD").title(),
            description=desc_text[:100] + "..." if desc_text and len(desc_text)>100 else desc_text,
            bed_type=type_est.get("bedType"),
            bed_quantity=type_est.get("beds", 1),
            occupancy=offer.get("guests", {}).get("adults", 2)
        )

        # 1.3 Policies
        policies = offer.get("policies", {})
        # Refundable?
        # Often in 'policies.cancellation' or top level 'rateFamilyEstimated'
        is_refundable = False
        cancel_deadline = None
        if "cancellations" in policies and len(policies["cancellations"]) > 0:
            # Check first rule
            rule = policies["cancellations"][0]
            if "deadline" in rule:
                is_refundable = True
                cancel_deadline = rule["deadline"] # ISO Format
            elif "description" in rule and "NON REFUNDABLE" not in rule["description"].get("text", "").upper():
                is_refundable = True
        
        # Meal Plan? (Usually in description or 'boardType' if available, otherwise heuristics)
        meal_plan = "Room Only"
        desc_full = (desc_text or "").upper()
        if "BREAKFAST" in desc_full or "BFST" in desc_full:
            meal_plan = "Breakfast Included"

        policy_obj = HotelPolicy(
            is_refundable=is_refundable,
            cancellation_deadline=cancel_deadline,
            check_in_time=policies.get("checkInOut", {}).get("checkIn"),
            check_out_time=policies.get("checkInOut", {}).get("checkOut"),
            meal_plan=meal_plan
        )

        booking_obj = HotelBookingDetails(
            offer_id=offer.get("id", "unknown"),
            check_in_date=check_in_date,
            check_out_date=check_out_date,
            guests=offer.get("guests", {}).get("adults", 2),
            pricing=pricing_obj,
            room=room_obj,
            policies=policy_obj
        )

        # --- 2. Google Extraction (Context) ---
        
        # 2.1 Amenities (Merge Amadeus + Google types)
        # Amadeus
        raw_amenities = hotel_meta.get("amenities", [])
        # Google
        google_types = google_place_details.get("types", [])
        combined_tags = [str(a).upper() for a in raw_amenities] + [str(t).upper().replace("_", " ") for t in google_types]
        
        # Logic for booleans
        amenities_obj = HotelAmenities(
            has_wifi=any("WIFI" in t for t in combined_tags),
            has_parking=any("PARKING" in t for t in combined_tags),
            has_air_conditioning=any("AIR" in t and "CONDITION" in t for t in combined_tags),
            has_fitness=any("GYM" in t or "FITNESS" in t for t in combined_tags),
            has_pool=any("POOL" in t or "SWIMMING" in t for t in combined_tags),
            has_spa=any("SPA" in t or "SAUNA" in t for t in combined_tags),
            original_list=raw_amenities[:10] # Keep top 10 raw ones
        )

        # 2.2 Location
        loc_geo = google_place_details.get("geometry", {}).get("location", {})
        
        # User Request: Data from Amadeus Only (except images)
        amadeus_addr = ", ".join(hotel_meta.get("address", {}).get("lines", []))
        final_addr = amadeus_addr if amadeus_addr else (google_place_details.get("formatted_address") or "")

        location_obj = HotelLocation(
            place_id=google_place_details.get("place_id"),
            address=final_addr,
            latitude=hotel_meta.get("latitude") or loc_geo.get("lat"),
            longitude=hotel_meta.get("longitude") or loc_geo.get("lng"),
            # Distance logic would require calculation service, leaving None for now
            distance_to_airport=None 
        )

        # 2.3 Visuals
        photos = []
        if "photos" in google_place_details:
             for p in google_place_details["photos"][:5]:
                 ref = p.get("photo_reference")
                 if ref and settings.google_maps_api_key:
                     # Using Google Places Photo API with Key
                     url = f"https://maps.googleapis.com/maps/api/place/photo?maxwidth=400&photoreference={ref}&key={settings.google_maps_api_key}"
                     photos.append(url)
        
        visuals_obj = HotelVisuals(
            image_urls=photos,
            review_score=google_place_details.get("rating"),
            review_count=google_place_details.get("user_ratings_total")
        )

        # --- 3. AI Placeholder ---
        # (This will be filled by the LLM in a later pass)
        ai_obj = AIPerspective(
            vibe_check=None,
            value_reasoning=None
        )

        # --- 4. Final Merge ---
        return MergedHotelOption(
            hotel_id=hotel_meta.get("hotelId", "unknown"),
            hotel_name=hotel_meta.get("name") or google_place_details.get("name"), # Prefer Amadeus Name
            chain_code=hotel_meta.get("chainCode"),
            star_rating=hotel_meta.get("rating"), # Amadeus rating (1-5)
            booking=booking_obj,
            amenities=amenities_obj,
            location=location_obj,
            visuals=visuals_obj,
            ai=ai_obj
        )

# Global instance
aggregator = DataAggregator()

