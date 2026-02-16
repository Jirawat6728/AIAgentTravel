"""API สำหรับดู/ทดสอบผลการค้นหา Amadeus (เที่ยวบิน, ที่พัก, รถรับส่ง)."""

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import datetime, timedelta
import asyncio
import json
import math

from app.core.logging import get_logger
from app.services.travel_service import orchestrator
from app.services.llm import LLMService

logger = get_logger(__name__)

router = APIRouter(prefix="/api/amadeus-viewer", tags=["amadeus-viewer"])

class AmadeusSearchRequest(BaseModel):
    origin: str = Field(..., description="Origin location or IATA code")
    destination: str = Field(..., description="Destination location or IATA code")
    departure_date: str = Field(..., description="Departure date (YYYY-MM-DD)")
    return_date: Optional[str] = Field(None, description="Return date for round trip (YYYY-MM-DD)")
    waypoints: Optional[List[str]] = Field(default=[], description="List of waypoints (places to visit along the route)")
    hotel_area: Optional[str] = Field(None, description="Hotel area/neighborhood to search")
    adults: int = Field(1, description="Number of adults")
    check_in: Optional[str] = Field(None, description="Check-in date for hotels (YYYY-MM-DD)")
    check_out: Optional[str] = Field(None, description="Check-out date for hotels (YYYY-MM-DD)")
    guests: Optional[int] = Field(None, description="Number of guests for hotels")


class ExtractTravelInfoRequest(BaseModel):
    query: str = Field(..., description="Natural language travel query")


class ExtractTravelInfoResponse(BaseModel):
    origin: Optional[str] = Field(None, description="Extracted origin")
    destination: Optional[str] = Field(None, description="Extracted destination")
    date: Optional[str] = Field(None, description="Extracted departure date (YYYY-MM-DD)")
    destination_details: Optional[str] = Field(None, description="Additional destination details (e.g., specific places)")


@router.post("/extract-info")
async def extract_travel_info(request: Request, extract_request: ExtractTravelInfoRequest):
    """
    Extract travel information from natural language using LLM
    Admin-only endpoint
    """
    # Check admin access
    await require_admin(request)
    
    try:
        # Initialize LLM service with explicit model name to avoid selection issues
        # Use a model name that is supported by API v1beta
        from app.core.config import settings
        # Try to use a model name that is compatible with v1beta API
        # If gemini_model_name is not supported, use a fallback
        model_name = settings.gemini_model_name
        # Check if model name contains deprecated patterns
        if '-latest' in model_name:
            # Replace deprecated -latest suffix with stable version
            model_name = model_name.replace('-latest', '')
            logger.warning(f"Replaced deprecated -latest suffix. Using model: {model_name}")
        llm_service = LLMService(model_name=model_name)
        
        # Build prompt for LLM
        system_prompt = """You are a travel information extraction assistant. Extract travel details from natural language queries.
        
Return ONLY a valid JSON object with the following structure:
{
  "origin": "origin location or IATA code",
  "destination": "destination location or IATA code",
  "date": "YYYY-MM-DD format",
  "destination_details": "optional specific place or details"
}

If you cannot extract a field, use null for that field.
Always return valid JSON, no explanations, no markdown formatting, just the JSON object."""

        prompt = f"""Extract travel information from this query:

"{extract_request.query}"

Return a JSON object with origin, destination, date (YYYY-MM-DD format), and optional destination_details."""

        # Call LLM (disable auto model selection to use default model)
        llm_response = await llm_service.generate_content(
            prompt=prompt,
            system_prompt=system_prompt,
            temperature=0.3,  # Lower temperature for more consistent extraction
            max_tokens=200,
            auto_select_model=False  # Use default model to avoid model selection issues
        )
        
        # Parse LLM response (should be JSON)
        try:
            # Clean the response (remove markdown code blocks if present)
            cleaned_response = llm_response.strip()
            if cleaned_response.startswith('```'):
                # Remove markdown code block
                lines = cleaned_response.split('\n')
                lines = [line for line in lines if not line.strip().startswith('```')]
                cleaned_response = '\n'.join(lines)
            
            # Extract JSON from response
            extracted_data = json.loads(cleaned_response)
            
            # Validate and return
            return ExtractTravelInfoResponse(
                origin=extracted_data.get('origin'),
                destination=extracted_data.get('destination'),
                date=extracted_data.get('date'),
                destination_details=extracted_data.get('destination_details')
            )
        except json.JSONDecodeError as e:
            logger.warning(f"Failed to parse LLM JSON response: {llm_response}. Error: {e}")
            # Fallback: try simple pattern matching
            return _fallback_extract_info(extract_request.query)
    
    except Exception as e:
        logger.warning(f"Error extracting travel info with LLM: {e}. Falling back to pattern matching.")
        # Fallback to pattern matching if LLM fails
        try:
            return _fallback_extract_info(extract_request.query)
        except Exception as fallback_error:
            logger.error(f"Fallback extraction also failed: {fallback_error}", exc_info=True)
            raise HTTPException(status_code=500, detail=f"Extraction failed: {str(e)}")


def _fallback_extract_info(query: str) -> ExtractTravelInfoResponse:
    """Fallback pattern matching extraction if LLM fails"""
    import re
    
    # Pattern matching (similar to frontend)
    origin_match = re.search(r'(?:จาก|จากเมือง|จากที่|origin|from)[\s:]*([^ไปถึง→]+?)(?:ไป|to|→|->)', query, re.IGNORECASE)
    dest_match = re.search(r'(?:ไป|ไปที่|ไปยัง|destination|to)[\s:]*([^วันที่]+?)(?:วันที่|date|on|วัน|\(|\))', query, re.IGNORECASE)
    date_match = (
        re.search(r'(?:วันที่|date|on|วัน)[\s:]*(\d{4}[-/]\d{1,2}[-/]\d{1,2}|\d{1,2}[-/]\d{1,2}[-/]\d{2,4})', query, re.IGNORECASE) 
        or re.search(r'(\d{4}[-/]\d{1,2}[-/]\d{1,2}|\d{1,2}[-/]\d{1,2}[-/]\d{2,4})', query)
    )
    
    origin = origin_match.group(1).strip() if origin_match else None
    destination = dest_match.group(1).strip() if dest_match else None
    extracted_date = date_match.group(1).strip() if date_match else None
    
    # Try splitting by arrow
    if not origin or not destination:
        parts = query.split('→') or query.split('->') or query.split(' to ')
        if len(parts) >= 2:
            origin = parts[0].replace('from', '').replace('จาก', '').strip() if not origin else origin
            destination = parts[1].split('(')[0].strip() if not destination else destination
    
    # Parse date
    date = None
    if extracted_date:
        date_parts = re.split(r'[/\-]', extracted_date)
        if len(date_parts) == 3:
            if len(date_parts[0]) == 4:  # YYYY-MM-DD
                date = f"{date_parts[0]}-{date_parts[1].zfill(2)}-{date_parts[2].zfill(2)}"
            else:  # DD-MM-YYYY or MM-DD-YYYY
                year = date_parts[2] if len(date_parts[2]) == 4 else f"20{date_parts[2]}"
                date = f"{year}-{date_parts[1].zfill(2)}-{date_parts[0].zfill(2)}"
    
    return ExtractTravelInfoResponse(
        origin=origin,
        destination=destination,
        date=date,
        destination_details=None
    )


async def require_admin(request: Request) -> bool:
    """Check if user is admin@example.com"""
    # Get user from session cookie
    from app.core.config import settings
    from app.storage.mongodb_storage import MongoStorage
    from app.models.database import User
    
    user_id = request.cookies.get(settings.session_cookie_name)
    if not user_id:
        raise HTTPException(status_code=401, detail="Not authenticated")
    
    try:
        storage = MongoStorage()
        await storage.connect()
        users_collection = storage.db["users"]
        user_data = await users_collection.find_one({"user_id": user_id})
        
        if not user_data:
            raise HTTPException(status_code=401, detail="User not found")
        
        user = User(**user_data)
        is_admin = user.is_admin if hasattr(user, 'is_admin') else False
        is_admin_email = user.email == "admin@example.com"
        
        if not (is_admin or is_admin_email):
            raise HTTPException(status_code=403, detail="Access denied. Admin only.")
        
        return True
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error checking admin status: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error")


async def search_flights_task(origin: str, destination: str, departure_date: str, adults: int) -> List[Dict[str, Any]]:
    """Search flights from Amadeus (matching amadeus_data_viewer.py - max=20)"""
    try:
        # Call Amadeus API directly with max=20 (same as amadeus_data_viewer.py)
        # Use orchestrator's token and client, but override max parameter
        token = await orchestrator._get_amadeus_token()
        
        params = {
            "originLocationCode": origin,
            "destinationLocationCode": destination,
            "departureDate": departure_date,
            "adults": adults,
            "max": 20,  # Match amadeus_data_viewer.py (max=20, not 10)
            "currencyCode": "THB"
        }
        
        # ✅ Search: ใช้ production environment
        resp = await orchestrator.client.get(
            f"{orchestrator.amadeus_search_base_url}/v2/shopping/flight-offers",
            params=params,
            headers={"Authorization": f"Bearer {token}"}
        )
        resp.raise_for_status()
        flights = resp.json().get("data", [])
        logger.info(f"Found {len(flights)} flights (max=20, matching amadeus_data_viewer.py)")
        return flights  # Return all without additional limit
    except Exception as e:
        logger.error(f"Error fetching flights: {e}", exc_info=True)
        return []


async def search_hotels_task(location_name: str, check_in: str, check_out: str, guests: int) -> List[Dict[str, Any]]:
    """Search hotels from Amadeus (matching amadeus_data_viewer.py - limit=10)"""
    try:
        # Get city code for hotels (same logic as amadeus_data_viewer.py)
        city_code = location_name.upper()[:3] if len(location_name) == 3 and location_name.isupper() else await orchestrator.find_city_iata(location_name) or location_name
        
        # Call Amadeus API directly (matching amadeus_data_viewer.py)
        token = await orchestrator._get_amadeus_token()
        
        # ✅ Search: ใช้ production environment
        # Step 1: Search for hotels by city (same as amadeus_data_viewer.py)
        search_url = f"{orchestrator.amadeus_search_base_url}/v1/reference-data/locations/hotels/by-city"
        search_params = {"cityCode": city_code}
        
        search_resp = await orchestrator.client.get(
            search_url,
            params=search_params,
            headers={"Authorization": f"Bearer {token}"}
        )
        search_resp.raise_for_status()
        hotel_data = search_resp.json().get("data", [])
        hotel_ids = [h["hotelId"] for h in hotel_data[:10]]  # Limit to 10 hotels (same as amadeus_data_viewer.py)
        
        if not hotel_ids:
            logger.warning(f"No hotels found in city {city_code}")
            return []
        
        # ✅ Search: ใช้ production environment
        # Step 2: Get hotel offers (same as amadeus_data_viewer.py)
        offers_url = f"{orchestrator.amadeus_search_base_url}/v3/shopping/hotel-offers"
        hotel_ids_list = hotel_ids[:10]  # Limit to 10 hotels (same as amadeus_data_viewer.py)
        
        # Try POST first, then GET as fallback (same as amadeus_data_viewer.py)
        try:
            offers_data = {
                "hotelIds": hotel_ids_list,
                "checkInDate": check_in,
                "checkOutDate": check_out,
                "adults": guests
            }
            
            offers_resp = await orchestrator.client.post(
                offers_url,
                json=offers_data,
                headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
            )
            offers_resp.raise_for_status()
        except Exception:
            # Fallback: Try GET method with hotelIds as query param
            hotel_ids_str = ",".join(hotel_ids_list)
            offers_params = {
                "hotelIds": hotel_ids_str,
                "checkInDate": check_in,
                "checkOutDate": check_out,
                "adults": guests
            }
            
            offers_resp = await orchestrator.client.get(
                offers_url,
                params=offers_params,
                headers={"Authorization": f"Bearer {token}"}
            )
            offers_resp.raise_for_status()
        
        hotels = offers_resp.json().get("data", [])
        logger.info(f"Found {len(hotels)} hotels (limit=10, matching amadeus_data_viewer.py)")
        return hotels  # Return all without additional limit
    except Exception as e:
        logger.error(f"Error fetching hotels: {e}", exc_info=True)
        return []


async def search_return_flights_task(origin: str, destination: str, return_date: str, adults: int) -> List[Dict[str, Any]]:
    """Search return flights (ขากลับ) from Amadeus"""
    try:
        token = await orchestrator._get_amadeus_token()
        
        params = {
            "originLocationCode": destination,  # Reverse origin/destination for return
            "destinationLocationCode": origin,
            "departureDate": return_date,
            "adults": adults,
            "max": 20,
            "currencyCode": "THB"
        }
        
        # ✅ Search: ใช้ production environment
        resp = await orchestrator.client.get(
            f"{orchestrator.amadeus_search_base_url}/v2/shopping/flight-offers",
            params=params,
            headers={"Authorization": f"Bearer {token}"}
        )
        resp.raise_for_status()
        flights = resp.json().get("data", [])
        logger.info(f"Found {len(flights)} return flights (max=20)")
        return flights
    except Exception as e:
        logger.error(f"Error fetching return flights: {e}", exc_info=True)
        return []


async def search_transfers_task(start_lat: float, start_lng: float, end_lat: float, end_lng: float, start_time: str, passengers: int) -> List[Dict[str, Any]]:
    """Search all transfer types (รถ, รถโดยสาร, รถไฟ, เรือ) from Amadeus"""
    try:
        token = await orchestrator._get_amadeus_token()
        
        # Use Activities API to find all transportation services
        # ✅ Search: ใช้ production environment
        url = f"{orchestrator.amadeus_search_base_url}/v1/shopping/activities"
        params = {
            "latitude": start_lat,
            "longitude": start_lng,
            "radius": 50,  # 50km radius
        }
        
        resp = await orchestrator.client.get(
            url,
            params=params,
            headers={"Authorization": f"Bearer {token}"}
        )
        resp.raise_for_status()
        data = resp.json()
        
        # Filter for all transportation types
        transfers = []
        for activity in data.get("data", []):
            name = activity.get("name", "").lower()
            description = activity.get("shortDescription", "").lower() if activity.get("shortDescription") else ""
            combined_text = f"{name} {description}"
            
            # Include all transportation types
            if any(keyword in combined_text for keyword in [
                "transfer", "shuttle", "car", "taxi", "private", 
                "bus", "รถโดยสาร", "coach", "รถบัส",
                "train", "รถไฟ", "rail", "railway",
                "ferry", "เรือ", "cruise", "boat", "ship"
            ]):
                transfers.append(activity)
        
        logger.info(f"Found {len(transfers)} transfers (all types, limit=20)")
        return transfers[:20]  # Increased limit for all transfer types
    except Exception as e:
        logger.error(f"Error fetching transfers: {e}", exc_info=True)
        return []


async def search_places_along_route_task(origin_geo: Dict[str, Any], dest_geo: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Search places of interest along the route using Google Maps"""
    try:
        if not orchestrator.gmaps:
            logger.warning("Google Maps API not configured for places search")
            return []
        
        # Calculate waypoints along the route (great circle path)
        import math
        
        def calculate_waypoints(start_lat: float, start_lng: float, end_lat: float, end_lng: float, num_points: int = 5) -> List[Dict[str, float]]:
            """Calculate waypoints along great circle path"""
            waypoints = []
            for i in range(num_points + 1):
                fraction = i / num_points
                
                # Convert to radians
                lat1_rad = math.radians(start_lat)
                lng1_rad = math.radians(start_lng)
                lat2_rad = math.radians(end_lat)
                lng2_rad = math.radians(end_lng)
                
                # Calculate great circle distance
                d = math.acos(
                    math.sin(lat1_rad) * math.sin(lat2_rad) +
                    math.cos(lat1_rad) * math.cos(lat2_rad) * math.cos(lng2_rad - lng1_rad)
                )
                
                if abs(d) < 0.001:
                    lat = start_lat + (end_lat - start_lat) * fraction
                    lng = start_lng + (end_lng - start_lng) * fraction
                else:
                    a = math.sin((1 - fraction) * d) / math.sin(d)
                    b = math.sin(fraction * d) / math.sin(d)
                    x = a * math.cos(lat1_rad) * math.cos(lng1_rad) + b * math.cos(lat2_rad) * math.cos(lng2_rad)
                    y = a * math.cos(lat1_rad) * math.sin(lng1_rad) + b * math.cos(lat2_rad) * math.sin(lng2_rad)
                    z = a * math.sin(lat1_rad) + b * math.sin(lat2_rad)
                    
                    lat = math.atan2(z, math.sqrt(x * x + y * y)) * 180 / math.PI
                    lng = math.atan2(y, x) * 180 / math.PI
                
                waypoints.append({"lat": lat, "lng": lng})
            
            return waypoints
        
        if not origin_geo or not dest_geo:
            return []
        
        waypoints = calculate_waypoints(
            origin_geo["lat"], origin_geo["lng"],
            dest_geo["lat"], dest_geo["lng"],
            num_points=5
        )
        
        # Search for places near each waypoint
        place_types = [
            "tourist_attraction", "restaurant", "lodging",
            "shopping_mall", "park", "museum", "zoo", "aquarium"
        ]
        
        places = []
        seen_places = set()  # Avoid duplicates
        
        for waypoint in waypoints[1:-1]:  # Skip origin and destination
            lat, lng = waypoint["lat"], waypoint["lng"]
            
            for place_type in place_types[:4]:  # Limit to 4 types per waypoint
                try:
                    places_result = orchestrator.gmaps.places_nearby(
                        location=(lat, lng),
                        radius=10000,  # 10km radius
                        type=place_type,
                        language="th"
                    )
                    
                    if places_result.get("results"):
                        for place in places_result["results"][:2]:  # 2 places per type
                            place_id = place.get("place_id")
                            if place_id and place_id not in seen_places:
                                seen_places.add(place_id)
                                places.append({
                                    "name": place.get("name", "N/A"),
                                    "type": place_type,
                                    "lat": place["geometry"]["location"]["lat"],
                                    "lng": place["geometry"]["location"]["lng"],
                                    "rating": place.get("rating", 0),
                                    "vicinity": place.get("vicinity", "N/A"),
                                    "place_id": place_id
                                })
                except Exception as e:
                    logger.debug(f"Error searching {place_type} at {lat},{lng}: {e}")
                    continue
        
        logger.info(f"Found {len(places)} places along route")
        return places[:30]  # Limit to 30 results
    except Exception as e:
        logger.error(f"Error fetching places along route: {e}", exc_info=True)
        return []


@router.post("/search")
async def search_amadeus(request: Request, search: AmadeusSearchRequest):
    """
    Search Amadeus for flights, hotels, and transfers
    Admin-only endpoint
    Based on amadeus_data_viewer.py logic with concurrent fetching
    """
    # Check admin access
    await require_admin(request)
    
    try:
        # Parse dates (from amadeus_data_viewer.py)
        dep_date = datetime.strptime(search.departure_date, "%Y-%m-%d")
        check_in = search.check_in or search.departure_date
        check_out = search.check_out or (dep_date + timedelta(days=4)).strftime("%Y-%m-%d")
        guests = search.guests or search.adults
        
        # Convert location names to IATA codes concurrently (optimized for speed)
        async def get_iata_codes():
            origin_res = search.origin.upper()[:3] if len(search.origin) == 3 and search.origin.isupper() else None
            dest_res = search.destination.upper()[:3] if len(search.destination) == 3 and search.destination.isupper() else None
            
            tasks = []
            if not origin_res:
                tasks.append(orchestrator.find_city_iata(search.origin))
            else:
                async def return_origin(): return origin_res
                tasks.append(return_origin())
            
            if not dest_res:
                tasks.append(orchestrator.find_city_iata(search.destination))
            else:
                async def return_dest(): return dest_res
                tasks.append(return_dest())
            
            codes = await asyncio.gather(*tasks, return_exceptions=True)
            origin_code = codes[0] if not isinstance(codes[0], Exception) else search.origin
            dest_code = codes[1] if not isinstance(codes[1], Exception) else search.destination
            return origin_code or search.origin, dest_code or search.destination
        
        try:
            origin_code, dest_code = await asyncio.wait_for(get_iata_codes(), timeout=10.0)
        except asyncio.TimeoutError:
            logger.warning("IATA code lookup timeout, using original values")
            origin_code = search.origin.upper()[:3] if len(search.origin) == 3 and search.origin.isupper() else search.origin
            dest_code = search.destination.upper()[:3] if len(search.destination) == 3 and search.destination.isupper() else search.destination
        
        # Geocode airports concurrently with timeout (optimized for speed - skip if timeout)
        async def get_geocodes():
            tasks = []
            tasks.append(orchestrator.get_coordinates(origin_code))
            tasks.append(orchestrator.get_coordinates(dest_code))
            geos = await asyncio.gather(*tasks, return_exceptions=True)
            return geos[0] if not isinstance(geos[0], Exception) else None, geos[1] if not isinstance(geos[1], Exception) else None
        
        try:
            origin_geo, dest_geo = await asyncio.wait_for(get_geocodes(), timeout=10.0)
        except asyncio.TimeoutError:
            logger.warning("Geocoding timeout, skipping coordinates for transfers")
            origin_geo, dest_geo = None, None
        
        # Use hotel_area if provided, otherwise use destination
        hotel_location = search.hotel_area or search.destination
        
        # Fetch data concurrently with timeout (optimized for speed - must complete in < 50 seconds)
        flights_task = asyncio.create_task(search_flights_task(origin_code, dest_code, search.departure_date, search.adults))
        hotels_task = asyncio.create_task(search_hotels_task(hotel_location, check_in, check_out, guests))
        
        # Geocode waypoints if provided
        waypoints_geo = []
        if search.waypoints and len(search.waypoints) > 0:
            async def geocode_waypoints():
                tasks = [orchestrator.get_coordinates(wp) for wp in search.waypoints]
                geos = await asyncio.gather(*tasks, return_exceptions=True)
                return [g if not isinstance(g, Exception) else None for g in geos]
            
            try:
                waypoints_geo = await asyncio.wait_for(geocode_waypoints(), timeout=10.0)
            except asyncio.TimeoutError:
                logger.warning("Waypoint geocoding timeout")
                waypoints_geo = []
        
        # Return flights (ขากลับ) if return_date is provided
        return_flights_task = None
        if search.return_date:
            return_flights_task = asyncio.create_task(search_return_flights_task(origin_code, dest_code, search.return_date, search.adults))
        else:
            async def empty_return_flights(): return []
            return_flights_task = asyncio.create_task(empty_return_flights())
        
        # Prepare transfers task if we have geo coordinates (รถ, รถโดยสาร, รถไฟ, เรือ)
        transfers_task = None
        if origin_geo and dest_geo:
            start_time = f"{search.departure_date}T10:00:00"
            transfers_task = asyncio.create_task(search_transfers_task(
                origin_geo["lat"], origin_geo["lng"],
                dest_geo["lat"], dest_geo["lng"],
                start_time,
                search.adults
            ))
        else:
            async def empty_transfers(): return []
            transfers_task = asyncio.create_task(empty_transfers())
        
        # Places along route (สถานที่น่าสนใจตามเส้นทาง)
        places_task = None
        if origin_geo and dest_geo:
            places_task = asyncio.create_task(search_places_along_route_task(origin_geo, dest_geo))
        else:
            async def empty_places(): return []
            places_task = asyncio.create_task(empty_places())
        
        # Wait for all tasks concurrently with timeout (50 seconds max for API calls)
        results = await asyncio.wait_for(
            asyncio.gather(
                flights_task,
                hotels_task,
                return_flights_task,
                transfers_task,
                places_task,
                return_exceptions=True
            ),
            timeout=50.0
        )
        
        # Extract results, handle exceptions
        flights = results[0] if not isinstance(results[0], Exception) else []
        hotels = results[1] if not isinstance(results[1], Exception) else []
        return_flights = results[2] if not isinstance(results[2], Exception) and search.return_date else []
        transfers = results[3] if not isinstance(results[3], Exception) and origin_geo and dest_geo else []
        places = results[4] if not isinstance(results[4], Exception) and origin_geo and dest_geo else []
        
        # Log exceptions
        if isinstance(results[0], Exception):
            logger.error(f"Flight search error: {results[0]}")
        if isinstance(results[1], Exception):
            logger.error(f"Hotel search error: {results[1]}")
        if isinstance(results[2], Exception):
            logger.error(f"Return flight search error: {results[2]}")
        if isinstance(results[3], Exception):
            logger.error(f"Transfer search error: {results[3]}")
        if isinstance(results[4], Exception):
            logger.error(f"Places search error: {results[4]}")
        
        return {
            "ok": True,
            "flights": flights,
            "return_flights": return_flights,
            "hotels": hotels,
            "transfers": transfers,
            "places": places,
            "origin": {
                "name": search.origin,
                "code": origin_code,
                "geo": origin_geo
            },
            "destination": {
                "name": search.destination,
                "code": dest_code,
                "geo": dest_geo
            },
            "waypoints": [
                {
                    "name": search.waypoints[i] if i < len(search.waypoints) else f"Waypoint {i+1}",
                    "geo": waypoints_geo[i] if i < len(waypoints_geo) else None
                }
                for i in range(len(search.waypoints))
            ] if search.waypoints else [],
            "summary": {
                "flights_count": len(flights),
                "return_flights_count": len(return_flights),
                "hotels_count": len(hotels),
                "transfers_count": len(transfers),
                "places_count": len(places),
                "waypoints_count": len(search.waypoints) if search.waypoints else 0
            }
        }
    
    except Exception as e:
        logger.error(f"Error in Amadeus viewer search: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Search failed: {str(e)}")
